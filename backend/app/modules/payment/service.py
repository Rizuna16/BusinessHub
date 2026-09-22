from typing import List, Optional
from decimal import Decimal
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.payment.schemas import (
    PaymentInDB,
    PaymentResponse,
    PaymentListResponse,
    PaymentCreate,
    PaymentDirection,
    PaymentTargetType,
    PaymentStatus,
    PaymentMethod,
    PaymentAnalyticsSummaryResponse,
    PaymentAnalyticsByDirectionResponse,
    PaymentAnalyticsByMethodResponse,
    PaymentDirectionBreakdownItem,
    PaymentMethodBreakdownItem,
)
from app.modules.payment.repository import (
    AbstractPaymentRepository,
    payment_repository,
)
from app.modules.cash_account.repository import cash_account_repository
from app.modules.cash_account.schemas import CashMovementType, MovementDirection, CashAccountStatus, CashAccountType
from app.modules.sales.repository import sales_repository
from app.modules.sales.schemas import SalesStatus
from app.modules.purchase.repository import purchase_repository
from app.modules.purchase.schemas import PurchaseStatus
from app.modules.purchase_return.repository import purchase_return_repository
from app.modules.purchase_return.schemas import PurchaseReturnStatus
from app.modules.supplier.repository import supplier_repository
from app.modules.customer.repository import customer_repository
from app.modules.branch.repository import branch_repository
from app.modules.business_membership.service import BusinessMembershipService, business_membership_service
from app.modules.business_membership.schemas import BusinessMembershipRole
from app.modules.accounting.integration import accounting_integration_service
from app.modules.cashier_shift.schemas import ShiftStatus
from app.modules.cashier_shift.service import cashier_shift_service


class PaymentService:
    def __init__(
        self,
        payment_repo: AbstractPaymentRepository = payment_repository,
        membership_service: BusinessMembershipService = business_membership_service,
        session: Optional[AsyncSession] = None,
    ):
        self.payment_repo = payment_repo
        self.membership_service = membership_service
        self.session = session

    async def _validate_access(
        self,
        business_id: str,
        user_id: str,
        required_roles: Optional[tuple[BusinessMembershipRole, ...]] = None,
    ):
        membership = await self.membership_service.require_active_membership(business_id, user_id)
        if required_roles and membership.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of roles: {[r.value for r in required_roles]}",
            )
        return membership

    async def create_payment(
        self, business_id: str, user_id: str, payload: PaymentCreate
    ) -> PaymentResponse:
        if self.session is not None:
            async with self.session.begin():
                return await self._create_payment_with_retry(business_id, user_id, payload)
        else:
            return await self._create_payment_with_retry(business_id, user_id, payload)

    async def _create_payment_with_retry(self, business_id: str, user_id: str, payload: PaymentCreate) -> PaymentResponse:
        for attempt in range(3):
            try:
                if self.session is not None:
                    async with self.session.begin_nested():
                        return await self._create_payment_impl(business_id, user_id, payload)
                else:
                    return await self._create_payment_impl(business_id, user_id, payload)
            except Exception as e:
                err_str = str(e).lower()
                if ("unique" in err_str and ("payment_number" in err_str or "uq_payment" in err_str)) and attempt < 2:
                    continue
                raise
        raise HTTPException(status_code=409, detail="Document number collision; please retry")

    async def _create_payment_impl(
        self, business_id: str, user_id: str, payload: PaymentCreate
    ) -> PaymentResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )

        if payload.idempotency_key:
            existing = await self.payment_repo.get_payment_by_idempotency_key(payload.idempotency_key, business_id)
            if existing:
                return PaymentResponse(**existing.model_dump())

        # Store Credit does not require cash account
        is_store_credit = payload.payment_method == PaymentMethod.STORE_CREDIT

        if is_store_credit:
            if not payload.customer_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="customer_id is required for STORE_CREDIT payments.",
                )
            cust = await customer_repository.get_by_id(payload.customer_id, business_id)
            if not cust:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Customer not found for STORE_CREDIT payment.",
                )
            if cust.store_credit_balance < payload.amount:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient store credit balance. Available: {cust.store_credit_balance}, requested: {payload.amount}.",
                )
        else:
            # Validate Cash Account
            if not payload.cash_account_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="cash_account_id is required for non-STORE_CREDIT payments.",
                )
            cash_account = await cash_account_repository.get_account_by_id(payload.cash_account_id, business_id)
            if not cash_account or cash_account.status != CashAccountStatus.ACTIVE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cash account is inactive or not found.",
                )

        # Direction and target validation
        target_currency = None
        target_branch_id = None
        target_business_id = None

        if payload.direction == PaymentDirection.CUSTOMER_IN:
            if payload.target_type != PaymentTargetType.SALES:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Customer payment must target SALES.")
            
            sales = await sales_repository.get_sales_by_id(payload.target_id, business_id)
            if not sales or sales.business_id != business_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales not found.")
            
            if sales.status != SalesStatus.FINALIZED:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sales must be FINALIZED to receive payment.")

            target_currency = "IDR" # Assuming IDR for now, but sales doesn't store currency? Wait, let's check sales schema.
            target_branch_id = sales.branch_id
            target_business_id = sales.business_id

        elif payload.direction == PaymentDirection.SUPPLIER_OUT:
            if payload.target_type != PaymentTargetType.PURCHASE:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Supplier payment must target PURCHASE.")
            
            purchase = await purchase_repository.get_purchase_by_id(payload.target_id, business_id)
            if not purchase or purchase.business_id != business_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase not found.")
            
            if purchase.status != PurchaseStatus.FINALIZED:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Purchase must be FINALIZED to receive payment.")

            target_currency = "IDR"
            target_branch_id = purchase.branch_id
            target_business_id = purchase.business_id

        if not is_store_credit and cash_account.currency != payload.currency:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment currency does not match cash account currency.")

        # Check outstanding / overpayment (Policy: Reject payment > outstanding)
        outstanding = Decimal("0")
        if payload.direction == PaymentDirection.CUSTOMER_IN:
            # In real receivable, it's sales.grand_total - valid payments. 
            # We'll delegate the check to a simplified version or just allow it for now since it's a derived engine.
            # Wait, the prompt says: "Policy A: Reject payment > outstanding."
            sales = await sales_repository.get_sales_by_id(payload.target_id, business_id)
            active_paid = await self.payment_repo.get_active_payments_total_for_target(business_id, payload.target_type, payload.target_id)
            outstanding = sales.grand_total - active_paid
        elif payload.direction == PaymentDirection.SUPPLIER_OUT:
            purchase = await purchase_repository.get_purchase_by_id(payload.target_id, business_id)
            active_paid = await self.payment_repo.get_active_payments_total_for_target(business_id, payload.target_type, payload.target_id)
            
            # Calculate return adjustment
            returns, _ = await purchase_return_repository.list_returns(
                business_id=business_id, purchase_id=purchase.id, page=1, page_size=1000
            )
            return_adj = Decimal("0")
            for r in returns:
                if r.status == PurchaseReturnStatus.FINALIZED:
                    return_adj += r.grand_total

            net_payable = purchase.grand_total - return_adj
            if net_payable < Decimal("0"):
                net_payable = Decimal("0")

            outstanding = net_payable - active_paid

        if payload.amount > outstanding:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment amount ({payload.amount}) exceeds remaining outstanding ({outstanding}).",
            )

        # Create Payment
        seq = await self.payment_repo.get_next_payment_sequence(business_id)
        payment_number = f"PMT-{seq:06d}"
        payment_date = payload.payment_date or datetime.now(timezone.utc)

        payment_data = {
            "business_id": business_id,
            "branch_id": target_branch_id,
            "direction": payload.direction,
            "target_type": payload.target_type,
            "target_id": payload.target_id,
            "payment_number": payment_number,
            "payment_date": payment_date,
            "payment_method": payload.payment_method,
            "amount": payload.amount,
            "currency": payload.currency,
            "cash_account_id": payload.cash_account_id,
            "reference_number": payload.reference_number,
            "notes": payload.notes,
            "status": PaymentStatus.RECORDED,
            "created_by_user_id": user_id,
            "idempotency_key": payload.idempotency_key,
        }

# Payment shift context validation — CASH on CASH account requires shift_id
        if payload.payment_method == PaymentMethod.CASH and payload.cash_account_id:
            acc = await cash_account_repository.get_account_by_id(payload.cash_account_id, business_id)
            if not acc or acc.status != CashAccountStatus.ACTIVE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cash account is inactive or not found.",
                )
            if acc.account_type != CashAccountType.CASH:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="CASH payment requires a CASH type cash account.",
                )
            # shift_id is REQUIRED for CASH payments on CASH accounts
            if not payload.shift_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="CASH payment on a CASH account requires an active shift. shift_id is required.",
                )
            shift = await cashier_shift_service.shift_repo.get_shift_by_id(
                payload.shift_id, business_id
            )
            if not shift or shift.status != ShiftStatus.OPEN:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="CASH payment shift_id must reference an open shift.",
                )
            if shift.cash_account_id != payload.cash_account_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="CASH payment shift_id cash_account mismatch.",
                )
            if shift.cashier_user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="CASH payment shift does not belong to current user.",
                )

        # ATOMIC POSTING SIMULATION
        try:
            payment = await self.payment_repo.create_payment(payment_data)

            if is_store_credit:
                # Debit store credit balance
                from app.modules.customer_credit.service import customer_credit_service
                await customer_credit_service.redeem_store_credit(
                    business_id=business_id,
                    user_id=user_id,
                    customer_id=payload.customer_id,
                    amount=payload.amount,
                    reference_type="PAYMENT",
                    reference_id=payment.id,
                )
            else:
                # Create Cash Movement
                movement_type = CashMovementType.SALES_PAYMENT if payload.direction == PaymentDirection.CUSTOMER_IN else CashMovementType.EXPENSE
                direction = MovementDirection.IN if payload.direction == PaymentDirection.CUSTOMER_IN else MovementDirection.OUT

                # Check cash balance for OUT
                if direction == MovementDirection.OUT:
                    balance = await self._calculate_balance(business_id, cash_account)
                    if balance < payload.amount:
                        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient cash balance.")

                await cash_account_repository.create_movement(
                    business_id=business_id,
                    cash_account_id=payload.cash_account_id,
                    movement_type=movement_type,
                    amount=payload.amount,
                    direction=direction,
                    performed_by_user_id=user_id,
                    reference_type="PAYMENT",
                    reference_id=payment.id,
                    description=f"Payment {payment.payment_number}",
                    shift_id=payload.shift_id,
                )

            # Accounting Integration within safe_post lock (last step)
            idem_key = f"PAYMENT:{payment.id}:RECORDED"
            await accounting_integration_service.safe_post(
                idem_key,
                lambda: accounting_integration_service.post_payment_recorded(
                    business_id=business_id,
                    user_id=user_id,
                    payment_id=payment.id,
                    amount=payment.amount,
                    direction=payment.direction.value,
                    payment_date=payment.payment_date,
                    branch_id=payment.branch_id,
                    payment_method=payment.payment_method.value,
                )
            )

            return PaymentResponse(**payment.model_dump())
        except Exception as e:
            # Compensating rollback: delete created payment and cash movement on failure
            if 'payment' in locals() and payment:
                await self.payment_repo.delete_payment(payment.id, business_id)
                if not is_store_credit:
                    await cash_account_repository.delete_movement_by_reference(
                        business_id=business_id, reference_type="PAYMENT", reference_id=payment.id
                    )
                else:
                    # Rollback store credit redemption by reissuing
                    if payload.customer_id:
                        cust_rollback = await customer_repository.get_by_id(payload.customer_id, business_id)
                        if cust_rollback:
                            from app.modules.customer_credit.service import customer_credit_service
                            new_bal = cust_rollback.store_credit_balance + payload.amount
                            await customer_repository.update_credit_fields(
                                payload.customer_id, business_id, store_credit_balance=new_bal
                            )
            raise e

    async def _calculate_balance(self, business_id: str, account) -> Decimal:
        movements = await cash_account_repository.list_all_movements_for_account(business_id, account.id)
        balance = account.opening_balance
        for m in movements:
            if m.direction == MovementDirection.IN:
                balance += m.amount
            elif m.direction == MovementDirection.OUT:
                balance -= m.amount
        return balance

    async def list_payments(
        self, business_id: str, user_id: str, direction: Optional[PaymentDirection] = None,
        target_type: Optional[PaymentTargetType] = None, target_id: Optional[str] = None,
        page: int = 1, page_size: int = 20
    ) -> PaymentListResponse:
        await self._validate_access(business_id, user_id)
        if page < 1: page = 1
        if page_size < 1 or page_size > 100: page_size = 20
        
        payments, total = await self.payment_repo.list_payments(business_id, direction, target_type, target_id, page, page_size)
        items = [PaymentResponse(**p.model_dump()) for p in payments]
        return PaymentListResponse(items=items, page=page, page_size=page_size, total=total)

    async def get_payment(self, business_id: str, payment_id: str, user_id: str) -> PaymentResponse:
        await self._validate_access(business_id, user_id)
        p = await self.payment_repo.get_payment_by_id(payment_id, business_id)
        if not p: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found.")
        return PaymentResponse(**p.model_dump())

    async def void_payment(self, business_id: str, payment_id: str, user_id: str) -> PaymentResponse:
        if self.session is not None:
            async with self.session.begin():
                return await self._void_payment_impl(business_id, payment_id, user_id)
        else:
            return await self._void_payment_impl(business_id, payment_id, user_id)

    async def _void_payment_impl(self, business_id: str, payment_id: str, user_id: str) -> PaymentResponse:
        await self._validate_access(business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN))
        
        p = await self.payment_repo.get_payment_by_id(payment_id, business_id)
        if not p: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found.")
        if p.status == PaymentStatus.VOIDED: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment already VOIDED.")

        # Accounting Integration FIRST within safe_post lock
        idem_key = f"PAYMENT:{payment_id}:VOIDED"
        await accounting_integration_service.safe_post(
            idem_key,
            lambda: accounting_integration_service.post_payment_voided(
                business_id=business_id,
                user_id=user_id,
                payment_id=payment_id,
                amount=p.amount,
                direction=p.direction.value,
                voided_date=datetime.now(timezone.utc),
                branch_id=p.branch_id,
            )
        )

        # Void Cash Movement
        movements = await cash_account_repository.list_all_movements_for_account(business_id, p.cash_account_id)
        for m in movements:
            if m.reference_type == "PAYMENT" and m.reference_id == p.id:
                reversal_direction = MovementDirection.OUT if m.direction == MovementDirection.IN else MovementDirection.IN
                
                # Shift attribution for reversal: only if original shift is still OPEN
                reversal_shift_id = None
                if m.shift_id:
                    shift_repo = cashier_shift_service.shift_repo
                    original_shift = await shift_repo.get_shift_by_id(m.shift_id, business_id)
                    if original_shift and original_shift.status == ShiftStatus.OPEN:
                        reversal_shift_id = m.shift_id
                
                await cash_account_repository.create_movement(
                    business_id=business_id,
                    cash_account_id=p.cash_account_id,
                    movement_type=m.movement_type,
                    amount=m.amount,
                    direction=reversal_direction,
                    performed_by_user_id=user_id,
                    reference_type="PAYMENT_VOID",
                    reference_id=p.id,
                    description=f"Reversal for {p.payment_number}",
                    shift_id=reversal_shift_id,
                )

        voided = await self.payment_repo.void_payment(payment_id, business_id, user_id)
        return PaymentResponse(**voided.model_dump())


# --- Payment Analytics ---

    async def _validate_analytics_entities(
        self,
        business_id: str,
        branch_id: Optional[str] = None,
    ):
        if branch_id:
            br = await branch_repository.get_by_id(branch_id)
            if not br or br.business_id != business_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found in this business.")

    async def get_payment_analytics_summary(
        self,
        business_id: str,
        user_id: str,
        date_from: datetime,
        date_to: datetime,
        branch_id: Optional[str] = None,
        direction: Optional[PaymentDirection] = None,
        payment_method: Optional[PaymentMethod] = None,
    ) -> PaymentAnalyticsSummaryResponse:
        await self._validate_access(business_id, user_id)
        if date_from > date_to:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="date_from must be before or equal to date_to.")
        await self._validate_analytics_entities(business_id, branch_id)

        payments, _ = await self.payment_repo.list_payments(
            business_id=business_id, page=1, page_size=10000,
        )

        # Filter by payment_date range, status, branch, direction, method
        filtered = [
            p for p in payments
            if p.payment_date >= date_from and p.payment_date <= date_to
            and p.status == PaymentStatus.RECORDED
            and (branch_id is None or p.branch_id == branch_id)
            and (direction is None or p.direction == direction)
            and (payment_method is None or p.payment_method == payment_method)
        ]

        # Separate voided for operational stats (same date/status/branch filter but VOIDED)
        voided = [
            p for p in payments
            if p.payment_date >= date_from and p.payment_date <= date_to
            and p.status == PaymentStatus.VOIDED
            and (branch_id is None or p.branch_id == branch_id)
            and (direction is None or p.direction == direction)
            and (payment_method is None or p.payment_method == payment_method)
        ]

        gross_recorded = sum((p.amount for p in filtered), Decimal("0"))
        customer_in = sum((p.amount for p in filtered if p.direction == PaymentDirection.CUSTOMER_IN), Decimal("0"))
        supplier_out = sum((p.amount for p in filtered if p.direction == PaymentDirection.SUPPLIER_OUT), Decimal("0"))
        payment_count = len(filtered)
        voided_count = len(voided)
        voided_amount = sum((p.amount for p in voided), Decimal("0"))

        average = gross_recorded / payment_count if payment_count > 0 else Decimal("0")

        return PaymentAnalyticsSummaryResponse(
            date_from=date_from,
            date_to=date_to,
            gross_recorded=gross_recorded,
            customer_in_total=customer_in,
            supplier_out_total=supplier_out,
            net_payment_flow=customer_in - supplier_out,
            voided_count=voided_count,
            voided_amount=voided_amount,
            payment_count=payment_count,
            average_payment_value=average,
        )

    async def get_payment_analytics_by_direction(
        self,
        business_id: str,
        user_id: str,
        date_from: datetime,
        date_to: datetime,
        branch_id: Optional[str] = None,
        direction: Optional[PaymentDirection] = None,
        payment_method: Optional[PaymentMethod] = None,
    ) -> PaymentAnalyticsByDirectionResponse:
        await self._validate_access(business_id, user_id)
        if date_from > date_to:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="date_from must be before or equal to date_to.")
        await self._validate_analytics_entities(business_id, branch_id)

        payments, _ = await self.payment_repo.list_payments(
            business_id=business_id, page=1, page_size=10000,
        )

        filtered = [
            p for p in payments
            if p.payment_date >= date_from and p.payment_date <= date_to
            and p.status == PaymentStatus.RECORDED
            and (branch_id is None or p.branch_id == branch_id)
            and (direction is None or p.direction == direction)
            and (payment_method is None or p.payment_method == payment_method)
        ]

        dir_map: dict[str, dict] = {}
        for p in filtered:
            d = p.direction.value
            if d not in dir_map:
                dir_map[d] = {"direction": d, "amount": Decimal("0"), "payment_count": 0}
            dir_map[d]["amount"] += p.amount
            dir_map[d]["payment_count"] += 1

        directions = [
            PaymentDirectionBreakdownItem(**v) for v in dir_map.values()
        ]
        directions.sort(key=lambda x: (-x.amount, x.direction))

        gross = sum((d.amount for d in directions), Decimal("0"))
        count = sum(d.payment_count for d in directions)

        return PaymentAnalyticsByDirectionResponse(
            date_from=date_from,
            date_to=date_to,
            gross_recorded=gross,
            payment_count=count,
            directions=directions,
        )

    async def get_payment_analytics_by_method(
        self,
        business_id: str,
        user_id: str,
        date_from: datetime,
        date_to: datetime,
        branch_id: Optional[str] = None,
        direction: Optional[PaymentDirection] = None,
        payment_method: Optional[PaymentMethod] = None,
    ) -> PaymentAnalyticsByMethodResponse:
        await self._validate_access(business_id, user_id)
        if date_from > date_to:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="date_from must be before or equal to date_to.")
        await self._validate_analytics_entities(business_id, branch_id)

        payments, _ = await self.payment_repo.list_payments(
            business_id=business_id, page=1, page_size=10000,
        )

        filtered = [
            p for p in payments
            if p.payment_date >= date_from and p.payment_date <= date_to
            and p.status == PaymentStatus.RECORDED
            and (branch_id is None or p.branch_id == branch_id)
            and (direction is None or p.direction == direction)
            and (payment_method is None or p.payment_method == payment_method)
        ]

        method_map: dict[str, dict] = {}
        for p in filtered:
            m = p.payment_method.value
            if m not in method_map:
                method_map[m] = {"payment_method": m, "amount": Decimal("0"), "payment_count": 0}
            method_map[m]["amount"] += p.amount
            method_map[m]["payment_count"] += 1

        methods = [
            PaymentMethodBreakdownItem(**v) for v in method_map.values()
        ]
        methods.sort(key=lambda x: (-x.amount, x.payment_method))

        gross = sum((m.amount for m in methods), Decimal("0"))
        count = sum(m.payment_count for m in methods)

        return PaymentAnalyticsByMethodResponse(
            date_from=date_from,
            date_to=date_to,
            gross_recorded=gross,
            payment_count=count,
            methods=methods,
        )


payment_service = PaymentService()

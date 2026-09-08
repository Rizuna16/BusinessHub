from typing import List, Optional
from decimal import Decimal
from datetime import datetime, timezone
from fastapi import HTTPException, status

from app.modules.payment.schemas import (
    PaymentInDB,
    PaymentResponse,
    PaymentListResponse,
    PaymentCreate,
    PaymentDirection,
    PaymentTargetType,
    PaymentStatus,
)
from app.modules.payment.repository import (
    AbstractPaymentRepository,
    payment_repository,
)
from app.modules.cash_account.repository import cash_account_repository
from app.modules.cash_account.schemas import CashMovementType, MovementDirection, CashAccountStatus
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


class PaymentService:
    def __init__(
        self,
        payment_repo: AbstractPaymentRepository = payment_repository,
        membership_service: BusinessMembershipService = business_membership_service,
    ):
        self.payment_repo = payment_repo
        self.membership_service = membership_service

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
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )

        if payload.idempotency_key:
            existing = await self.payment_repo.get_payment_by_idempotency_key(payload.idempotency_key, business_id)
            if existing:
                return PaymentResponse(**existing.model_dump())

        # Validate Cash Account
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

        if cash_account.currency != payload.currency:
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

        # ATOMIC POSTING SIMULATION
        # In real DB, we would use a transaction here.
        # Since we are in-memory, we attempt to create payment, then cash movement, then accounting.
        try:
            payment = await self.payment_repo.create_payment(payment_data)

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
                )
            )

            return PaymentResponse(**payment.model_dump())
        except Exception as e:
            # Compensating rollback: delete created payment and cash movement on failure
            if 'payment' in locals() and payment:
                await self.payment_repo.delete_payment(payment.id, business_id)
                await cash_account_repository.delete_movement_by_reference(
                    business_id=business_id, reference_type="PAYMENT", reference_id=payment.id
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
                )

        voided = await self.payment_repo.void_payment(payment_id, business_id, user_id)
        return PaymentResponse(**voided.model_dump())


payment_service = PaymentService()

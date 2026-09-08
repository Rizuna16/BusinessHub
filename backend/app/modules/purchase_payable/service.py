from typing import List, Optional
from decimal import Decimal
from datetime import datetime, timezone, date, timedelta
from fastapi import HTTPException, status

from app.modules.purchase_payable.schemas import (
    PurchasePayableResponse,
    PurchasePayableListResponse,
    PurchasePayableSummaryResponse,
    SupplierPayableSummaryItem,
    SupplierPayableSummaryListResponse,
    PayableStatus,
    PayableReturnItem,
    SupplierStatementResponse,
    StatementDateRange,
    StatementLineResponse,
)
from app.modules.purchase.repository import (
    AbstractPurchaseRepository,
    purchase_repository,
)
from app.modules.purchase.schemas import PurchaseStatus
from app.modules.purchase_return.repository import (
    AbstractPurchaseReturnRepository,
    purchase_return_repository,
)
from app.modules.purchase_return.schemas import PurchaseReturnStatus
from app.modules.supplier.repository import supplier_repository, AbstractSupplierRepository
from app.modules.branch.repository import branch_repository
from app.modules.business_membership.service import (
    BusinessMembershipService,
    business_membership_service,
)
from app.modules.business_membership.schemas import BusinessMembershipRole
from app.modules.payment.schemas import PaymentTargetType, PaymentDirection, PaymentStatus as NewPaymentStatus
from app.modules.payment.repository import payment_repository, AbstractPaymentRepository


class PurchasePayableService:
    def __init__(
        self,
        purchase_repo: AbstractPurchaseRepository = purchase_repository,
        return_repo: AbstractPurchaseReturnRepository = purchase_return_repository,
        payment_repo: AbstractPaymentRepository = payment_repository,
        membership_service: BusinessMembershipService = business_membership_service,
    ):
        self.purchase_repo = purchase_repo
        self.return_repo = return_repo
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

    async def _calculate_payable_for_purchase(
        self, business_id: str, purchase_obj
    ) -> PurchasePayableResponse:
        # Gross payable comes authoritatively from purchase grand_total
        gross_payable = purchase_obj.grand_total if purchase_obj.grand_total >= Decimal("0") else Decimal("0")

        # Get all returns for this purchase
        # Only FINALIZED non-deleted returns reduce payable amount!
        raw_returns, _ = await self.return_repo.list_returns(
            business_id=business_id,
            purchase_id=purchase_obj.id,
            page=1,
            page_size=1000,
        )

        return_adjustment = Decimal("0")
        return_items = []
        finalized_return_count = 0

        for r in raw_returns:
            if r.status == PurchaseReturnStatus.FINALIZED:
                finalized_return_count += 1
                return_adjustment += r.grand_total

            return_items.append(
                PayableReturnItem(
                    id=r.id,
                    return_number=r.return_number,
                    return_date=r.created_at,
                    grand_total=r.grand_total,
                    status=r.status.value if hasattr(r.status, "value") else str(r.status),
                    created_at=r.created_at,
                )
            )

        # Invariant: return_adjustment cannot exceed gross_payable in net calculation
        if return_adjustment < Decimal("0"):
            return_adjustment = Decimal("0")

        net_payable = gross_payable - return_adjustment
        if net_payable < Decimal("0"):
            net_payable = Decimal("0")

        # Paid amount comes from Payment Engine
        paid_amount = await self.payment_repo.get_active_payments_total_for_target(
            business_id=business_id, target_type=PaymentTargetType.PURCHASE, target_id=purchase_obj.id
        )

        outstanding = net_payable - paid_amount
        if outstanding < Decimal("0"):
            outstanding = Decimal("0")

        # Determine Payable Status
        if net_payable == Decimal("0") or paid_amount >= net_payable:
            pay_status = PayableStatus.PAID
        elif paid_amount == Decimal("0"):
            pay_status = PayableStatus.UNPAID
        else:
            pay_status = PayableStatus.PARTIALLY_PAID

        # Supplier lookup
        sup_name = None
        sup_code = None
        if purchase_obj.supplier_id:
            sup = await supplier_repository.get_by_id(purchase_obj.supplier_id, business_id)
            if sup:
                sup_name = sup.name
                sup_code = sup.code

        # Branch lookup
        br_name = None
        if purchase_obj.branch_id:
            br = await branch_repository.get_by_id(purchase_obj.branch_id)
            if br and br.business_id == business_id:
                br_name = br.name

        return PurchasePayableResponse(
            purchase_id=purchase_obj.id,
            business_id=business_id,
            purchase_number=purchase_obj.purchase_number,
            purchase_date=purchase_obj.purchase_date,
            supplier_id=purchase_obj.supplier_id,
            supplier_name=sup_name,
            supplier_code=sup_code,
            branch_id=purchase_obj.branch_id,
            branch_name=br_name,
            currency="IDR",
            gross_payable=gross_payable,
            return_adjustment=return_adjustment,
            net_payable=net_payable,
            paid_amount=paid_amount,
            outstanding_amount=outstanding,
            status=pay_status,
            return_count=finalized_return_count,
            returns=return_items,
        )

    async def list_payables(
        self,
        business_id: str,
        user_id: str,
        status_filter: Optional[PayableStatus] = None,
        supplier_id: Optional[str] = None,
        branch_id: Optional[str] = None,
        search: Optional[str] = None,
        currency: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PurchasePayableListResponse:
        await self._validate_access(business_id, user_id)

        # Cross-tenant supplier check if supplier_id filter provided
        if supplier_id:
            sup = await supplier_repository.get_by_id(supplier_id, business_id)
            if not sup:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Supplier not found in this business.",
                )

        # Only FINALIZED purchases create payables! DRAFT and CANCELLED excluded.
        all_purchases, _ = await self.purchase_repo.list_purchases(
            business_id=business_id,
            status=PurchaseStatus.FINALIZED,
            supplier_id=supplier_id,
            branch_id=branch_id,
            search=None,
            page=1,
            page_size=10000,
        )

        results = []
        for p in all_purchases:
            if date_from and p.purchase_date < date_from:
                continue
            if date_to and p.purchase_date > date_to:
                continue

            payable = await self._calculate_payable_for_purchase(business_id, p)

            if currency and payable.currency.upper() != currency.upper():
                continue

            if status_filter and payable.status != status_filter:
                continue

            if search:
                s_lower = search.lower()
                num_match = s_lower in p.purchase_number.lower()
                sup_match = payable.supplier_name and s_lower in payable.supplier_name.lower()
                sup_code_match = payable.supplier_code and s_lower in payable.supplier_code.lower()
                if not num_match and not sup_match and not sup_code_match:
                    continue

            results.append(payable)

        results.sort(key=lambda x: (x.purchase_date, x.purchase_id), reverse=True)
        total = len(results)

        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        start = (page - 1) * page_size
        end = start + page_size
        paginated = results[start:end]

        return PurchasePayableListResponse(items=paginated, page=page, page_size=page_size, total=total)

    async def get_payable_by_purchase_id(
        self, business_id: str, purchase_id: str, user_id: str
    ) -> PurchasePayableResponse:
        await self._validate_access(business_id, user_id)
        p = await self.purchase_repo.get_purchase_by_id(purchase_id, business_id)
        if not p or p.status != PurchaseStatus.FINALIZED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Finalized purchase not found.",
            )

        return await self._calculate_payable_for_purchase(business_id, p)

    async def get_summary(
        self,
        business_id: str,
        user_id: str,
        supplier_id: Optional[str] = None,
        branch_id: Optional[str] = None,
        currency: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> PurchasePayableSummaryResponse:
        await self._validate_access(business_id, user_id)

        all_purchases, _ = await self.purchase_repo.list_purchases(
            business_id=business_id,
            status=PurchaseStatus.FINALIZED,
            supplier_id=supplier_id,
            branch_id=branch_id,
            search=None,
            page=1,
            page_size=10000,
        )

        total_gross = Decimal("0")
        total_ret = Decimal("0")
        total_net = Decimal("0")
        total_paid = Decimal("0")
        total_out = Decimal("0")
        unpaid_count = 0
        partially_paid_count = 0
        paid_count = 0
        suppliers_set = set()

        for p in all_purchases:
            if date_from and p.purchase_date < date_from:
                continue
            if date_to and p.purchase_date > date_to:
                continue

            payable = await self._calculate_payable_for_purchase(business_id, p)

            if currency and payable.currency.upper() != currency.upper():
                continue

            total_gross += payable.gross_payable
            total_ret += payable.return_adjustment
            total_net += payable.net_payable
            total_paid += payable.paid_amount
            total_out += payable.outstanding_amount

            if payable.supplier_id:
                suppliers_set.add(payable.supplier_id)

            if payable.status == PayableStatus.UNPAID:
                unpaid_count += 1
            elif payable.status == PayableStatus.PARTIALLY_PAID:
                partially_paid_count += 1
            elif payable.status == PayableStatus.PAID:
                paid_count += 1

        return PurchasePayableSummaryResponse(
            currency="IDR",
            total_gross_payable=total_gross,
            total_return_adjustment=total_ret,
            total_net_payable=total_net,
            total_paid_amount=total_paid,
            total_outstanding_amount=total_out,
            unpaid_count=unpaid_count,
            partially_paid_count=partially_paid_count,
            paid_count=paid_count,
            supplier_count=len(suppliers_set),
        )

    async def get_supplier_summaries(
        self,
        business_id: str,
        user_id: str,
        currency: Optional[str] = None,
    ) -> SupplierPayableSummaryListResponse:
        await self._validate_access(business_id, user_id)

        all_purchases, _ = await self.purchase_repo.list_purchases(
            business_id=business_id,
            status=PurchaseStatus.FINALIZED,
            page=1,
            page_size=10000,
        )

        supplier_map: dict[str, dict] = {}

        for p in all_purchases:
            payable = await self._calculate_payable_for_purchase(business_id, p)

            if currency and payable.currency.upper() != currency.upper():
                continue

            sup_id = p.supplier_id
            if sup_id not in supplier_map:
                supplier_map[sup_id] = {
                    "supplier_id": sup_id,
                    "supplier_name": payable.supplier_name,
                    "supplier_code": payable.supplier_code,
                    "currency": payable.currency,
                    "total_gross_payable": Decimal("0"),
                    "total_return_adjustment": Decimal("0"),
                    "total_net_payable": Decimal("0"),
                    "total_paid_amount": Decimal("0"),
                    "total_outstanding_amount": Decimal("0"),
                    "purchase_count": 0,
                }

            supplier_map[sup_id]["total_gross_payable"] += payable.gross_payable
            supplier_map[sup_id]["total_return_adjustment"] += payable.return_adjustment
            supplier_map[sup_id]["total_net_payable"] += payable.net_payable
            supplier_map[sup_id]["total_paid_amount"] += payable.paid_amount
            supplier_map[sup_id]["total_outstanding_amount"] += payable.outstanding_amount
            supplier_map[sup_id]["purchase_count"] += 1

        items = []
        for s_data in supplier_map.values():
            net = s_data["total_net_payable"]
            paid = s_data["total_paid_amount"]
            if net == Decimal("0") or paid >= net:
                status_calc = PayableStatus.PAID
            elif paid == Decimal("0"):
                status_calc = PayableStatus.UNPAID
            else:
                status_calc = PayableStatus.PARTIALLY_PAID

            items.append(
                SupplierPayableSummaryItem(
                    supplier_id=s_data["supplier_id"],
                    supplier_name=s_data["supplier_name"],
                    supplier_code=s_data["supplier_code"],
                    currency=s_data["currency"],
                    total_gross_payable=s_data["total_gross_payable"],
                    total_return_adjustment=s_data["total_return_adjustment"],
                    total_net_payable=s_data["total_net_payable"],
                    total_paid_amount=s_data["total_paid_amount"],
                    total_outstanding_amount=s_data["total_outstanding_amount"],
                    purchase_count=s_data["purchase_count"],
                    status=status_calc,
                )
            )

        items.sort(key=lambda x: x.total_outstanding_amount, reverse=True)
        return SupplierPayableSummaryListResponse(items=items)

    # --- Supplier Statement of Account (Feature #41) ---

    async def get_supplier_statement(
        self,
        business_id: str,
        user_id: str,
        supplier_id: str,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> SupplierStatementResponse:
        await self._validate_access(
            business_id,
            user_id,
            required_roles=(
                BusinessMembershipRole.OWNER,
                BusinessMembershipRole.ADMIN,
                BusinessMembershipRole.MEMBER,
            ),
        )

        supplier = await supplier_repository.get_by_id(supplier_id, business_id)
        if not supplier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier not found.",
            )

        if date_from is None:
            date_from = date(2000, 1, 1)
        if date_to is None:
            date_to = date.today()

        if date_from > date_to:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="date_from must be less than or equal to date_to.",
            )

        start_dt = datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc)
        end_dt_exclusive = datetime.combine(
            date_to + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc
        )

        def _normalize_dt(dt: datetime) -> datetime:
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)

        all_purchases, _ = await self.purchase_repo.list_purchases(
            business_id=business_id,
            supplier_id=supplier_id,
            status=PurchaseStatus.FINALIZED,
            page=1,
            page_size=10000,
        )

        supplier_purchase_ids = {p.id for p in all_purchases}

        all_purchase_returns, _ = await self.return_repo.list_returns(
            business_id=business_id,
            status=PurchaseReturnStatus.FINALIZED,
            page=1,
            page_size=10000,
        )
        all_purchase_returns = [
            r for r in all_purchase_returns if r.purchase_id in supplier_purchase_ids
        ]

        all_payments, _ = await self.payment_repo.list_payments(
            business_id=business_id,
            direction=PaymentDirection.SUPPLIER_OUT,
            target_type=PaymentTargetType.PURCHASE,
            page=1,
            page_size=10000,
        )
        all_payments = [p for p in all_payments if p.target_id in supplier_purchase_ids]

        opening_balance = Decimal("0.00")
        for pur in all_purchases:
            dt = _normalize_dt(pur.purchase_date)
            if dt < start_dt:
                opening_balance += pur.grand_total

        for ret in all_purchase_returns:
            if ret.finalized_at is not None:
                dt = _normalize_dt(ret.finalized_at)
                if dt < start_dt:
                    opening_balance -= ret.grand_total

        for pay in all_payments:
            if pay.status != NewPaymentStatus.RECORDED:
                continue
            dt = _normalize_dt(pay.payment_date)
            if dt < start_dt:
                opening_balance -= pay.amount

        lines: List[StatementLineResponse] = []

        for pur in all_purchases:
            dt = _normalize_dt(pur.purchase_date)
            if start_dt <= dt < end_dt_exclusive:
                lines.append(
                    StatementLineResponse(
                        transaction_date=dt,
                        transaction_type="PURCHASE",
                        reference_id=pur.id,
                        reference_number=pur.purchase_number,
                        description=None,
                        debit=Decimal("0.00"),
                        credit=pur.grand_total,
                        running_balance=Decimal("0.00"),
                    )
                )

        for ret in all_purchase_returns:
            if ret.finalized_at is not None:
                dt = _normalize_dt(ret.finalized_at)
                if start_dt <= dt < end_dt_exclusive:
                    lines.append(
                        StatementLineResponse(
                            transaction_date=dt,
                            transaction_type="PURCHASE_RETURN",
                            reference_id=ret.id,
                            reference_number=ret.return_number,
                            description=ret.notes,
                            debit=ret.grand_total,
                            credit=Decimal("0.00"),
                            running_balance=Decimal("0.00"),
                        )
                    )

        for pay in all_payments:
            if pay.status != NewPaymentStatus.RECORDED:
                continue
            dt = _normalize_dt(pay.payment_date)
            if start_dt <= dt < end_dt_exclusive:
                lines.append(
                    StatementLineResponse(
                        transaction_date=dt,
                        transaction_type="SUPPLIER_PAYMENT",
                        reference_id=pay.id,
                        reference_number=pay.payment_number,
                        description=pay.notes,
                        debit=pay.amount,
                        credit=Decimal("0.00"),
                        running_balance=Decimal("0.00"),
                    )
                )

        type_priority = {"PURCHASE": 1, "SUPPLIER_PAYMENT": 2, "PURCHASE_RETURN": 3}
        lines.sort(
            key=lambda x: (
                x.transaction_date,
                type_priority[x.transaction_type],
                x.reference_id,
            )
        )

        running = opening_balance
        total_debit = Decimal("0.00")
        total_credit = Decimal("0.00")

        for line in lines:
            total_debit += line.debit
            total_credit += line.credit
            running += line.credit - line.debit
            line.running_balance = running

        closing_balance = opening_balance + total_credit - total_debit

        total_items = len(lines)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paged_lines = lines[start_idx:end_idx]

        return SupplierStatementResponse(
            entity_id=supplier_id,
            entity_name=supplier.name,
            date_range=StatementDateRange(start_date=date_from, end_date=date_to),
            opening_balance=opening_balance,
            lines=paged_lines,
            closing_balance=closing_balance,
            total_debit=total_debit,
            total_credit=total_credit,
            page=page,
            page_size=page_size,
            total_items=total_items,
        )


purchase_payable_service = PurchasePayableService()

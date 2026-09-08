from typing import List, Optional
from decimal import Decimal
from datetime import datetime, timezone, date, timedelta
from fastapi import HTTPException, status

from app.modules.sales_receivable.schemas import (
    SalesReceivableResponse,
    SalesReceivableListResponse,
    SalesReceivableSummaryResponse,
    CustomerReceivableSummaryItem,
    CustomerReceivableSummaryListResponse,
    ReceivableStatus,
    ReceivablePaymentItem,
    CustomerStatementResponse,
    StatementDateRange,
    StatementLineResponse,
)
from app.modules.sales.repository import (
    AbstractSalesRepository,
    sales_repository,
)
from app.modules.sales.schemas import SalesStatus
from app.modules.sales_return.repository import (
    sales_return_repository,
    AbstractSalesReturnRepository,
)
from app.modules.sales_return.schemas import SalesReturnStatus
from app.modules.payment.schemas import (
    PaymentTargetType,
    PaymentDirection,
    PaymentStatus as NewPaymentStatus,
)
from app.modules.payment.repository import payment_repository, AbstractPaymentRepository
from app.modules.customer.repository import customer_repository
from app.modules.branch.repository import branch_repository
from app.modules.business_membership.service import (
    BusinessMembershipService,
    business_membership_service,
)
from app.modules.business_membership.schemas import BusinessMembershipRole


class SalesReceivableService:
    def __init__(
        self,
        sales_repo: AbstractSalesRepository = sales_repository,
        payment_repo: AbstractPaymentRepository = payment_repository,
        membership_service: BusinessMembershipService = business_membership_service,
        sales_return_repo: AbstractSalesReturnRepository = sales_return_repository,
    ):
        self.sales_repo = sales_repo
        self.payment_repo = payment_repo
        self.membership_service = membership_service
        self.sales_return_repo = sales_return_repo

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

    async def _calculate_receivable_for_sales(
        self, business_id: str, sales_obj
    ) -> SalesReceivableResponse:
        # Get active payments total
        active_paid = await self.payment_repo.get_active_payments_total_for_target(
            business_id=business_id, target_type=PaymentTargetType.SALES, target_id=sales_obj.id
        )
        outstanding = sales_obj.grand_total - active_paid
        if outstanding < Decimal("0"):
            outstanding = Decimal("0")

        # Determine status
        if sales_obj.grand_total == Decimal("0") or active_paid >= sales_obj.grand_total:
            rec_status = ReceivableStatus.PAID
        elif active_paid == Decimal("0"):
            rec_status = ReceivableStatus.UNPAID
        else:
            rec_status = ReceivableStatus.PARTIALLY_PAID

        # List all payments for history
        raw_payments, _ = await self.payment_repo.list_payments(
            business_id=business_id, target_type=PaymentTargetType.SALES, target_id=sales_obj.id, page=1, page_size=100
        )

        payment_items = []
        last_payment_date = None
        active_count = 0

        for p in raw_payments:
            if p.status == NewPaymentStatus.RECORDED:
                active_count += 1
                if last_payment_date is None or p.payment_date > last_payment_date:
                    last_payment_date = p.payment_date

            payment_items.append(
                ReceivablePaymentItem(
                    id=p.id,
                    payment_number=p.payment_number,
                    payment_date=p.payment_date,
                    payment_method=p.payment_method.value if hasattr(p.payment_method, 'value') else str(p.payment_method),
                    amount=p.amount,
                    reference_number=p.reference_number,
                    notes=p.notes,
                    status=p.status.value if hasattr(p.status, 'value') else str(p.status),
                    created_by_user_id=p.created_by_user_id,
                    created_at=p.created_at,
                )
            )

        # Customer name
        cust_name = None
        if sales_obj.customer_id:
            c = await customer_repository.get_by_id(sales_obj.customer_id, business_id)
            if c:
                cust_name = c.name

        # Branch name
        br_name = None
        if sales_obj.branch_id:
            br = await branch_repository.get_by_id(sales_obj.branch_id)
            if br:
                br_name = br.name

        return SalesReceivableResponse(
            sales_id=sales_obj.id,
            business_id=business_id,
            sales_number=sales_obj.sales_number,
            sales_date=sales_obj.sales_date,
            customer_id=sales_obj.customer_id,
            customer_name=cust_name,
            branch_id=sales_obj.branch_id,
            branch_name=br_name,
            sales_total=sales_obj.grand_total,
            paid_amount=active_paid,
            outstanding_amount=outstanding,
            status=rec_status,
            payment_count=active_count,
            last_payment_date=last_payment_date,
            payments=payment_items,
        )

    async def list_receivables(
        self,
        business_id: str,
        user_id: str,
        status_filter: Optional[ReceivableStatus] = None,
        customer_id: Optional[str] = None,
        branch_id: Optional[str] = None,
        search: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> SalesReceivableListResponse:
        await self._validate_access(business_id, user_id)

        # Get all FINALIZED sales for this business
        all_sales, _ = await self.sales_repo.list_sales(
            business_id=business_id,
            status=SalesStatus.FINALIZED,
            customer_id=customer_id,
            branch_id=branch_id,
            search=None,
            page=1,
            page_size=10000,
        )

        results = []
        for s in all_sales:
            if date_from and s.sales_date < date_from:
                continue
            if date_to and s.sales_date > date_to:
                continue

            rec = await self._calculate_receivable_for_sales(business_id, s)

            if status_filter and rec.status != status_filter:
                continue

            if search:
                s_lower = search.lower()
                num_match = s_lower in s.sales_number.lower()
                cust_match = rec.customer_name and s_lower in rec.customer_name.lower()
                if not num_match and not cust_match:
                    continue

            results.append(rec)

        results.sort(key=lambda x: (x.sales_date, x.sales_id), reverse=True)
        total = len(results)

        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        start = (page - 1) * page_size
        end = start + page_size
        paginated = results[start:end]

        return SalesReceivableListResponse(items=paginated, page=page, page_size=page_size, total=total)

    async def get_receivable_by_sales_id(
        self, business_id: str, sales_id: str, user_id: str
    ) -> SalesReceivableResponse:
        await self._validate_access(business_id, user_id)
        s = await self.sales_repo.get_sales_by_id(sales_id, business_id)
        if not s:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sales not found.",
            )
        if s.status != SalesStatus.FINALIZED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Receivable view is only available for FINALIZED sales.",
            )
        return await self._calculate_receivable_for_sales(business_id, s)

    async def get_summary(
        self, business_id: str, user_id: str
    ) -> SalesReceivableSummaryResponse:
        await self._validate_access(business_id, user_id)

        all_sales, _ = await self.sales_repo.list_sales(
            business_id=business_id,
            status=SalesStatus.FINALIZED,
            page=1,
            page_size=10000,
        )

        total_sales_amount = Decimal("0")
        total_paid_amount = Decimal("0")
        total_outstanding_amount = Decimal("0")
        unpaid_count = 0
        partially_paid_count = 0
        paid_count = 0

        for s in all_sales:
            rec = await self._calculate_receivable_for_sales(business_id, s)
            total_sales_amount += rec.sales_total
            total_paid_amount += rec.paid_amount
            total_outstanding_amount += rec.outstanding_amount

            if rec.status == ReceivableStatus.UNPAID:
                unpaid_count += 1
            elif rec.status == ReceivableStatus.PARTIALLY_PAID:
                partially_paid_count += 1
            elif rec.status == ReceivableStatus.PAID:
                paid_count += 1

        return SalesReceivableSummaryResponse(
            total_sales_amount=total_sales_amount,
            total_paid_amount=total_paid_amount,
            total_outstanding_amount=total_outstanding_amount,
            unpaid_count=unpaid_count,
            partially_paid_count=partially_paid_count,
            paid_count=paid_count,
        )

    async def get_customer_summary(
        self, business_id: str, user_id: str
    ) -> CustomerReceivableSummaryListResponse:
        await self._validate_access(business_id, user_id)

        all_sales, _ = await self.sales_repo.list_sales(
            business_id=business_id,
            status=SalesStatus.FINALIZED,
            page=1,
            page_size=10000,
        )

        cust_map = {}

        for s in all_sales:
            rec = await self._calculate_receivable_for_sales(business_id, s)
            cid = s.customer_id or "WALK_IN"

            if cid not in cust_map:
                cust_map[cid] = {
                    "customer_id": s.customer_id,
                    "customer_name": rec.customer_name if s.customer_id else "Walk-in Customer",
                    "total_sales": Decimal("0"),
                    "total_paid": Decimal("0"),
                    "total_outstanding": Decimal("0"),
                    "sales_count": 0,
                }

            cust_map[cid]["total_sales"] += rec.sales_total
            cust_map[cid]["total_paid"] += rec.paid_amount
            cust_map[cid]["total_outstanding"] += rec.outstanding_amount
            cust_map[cid]["sales_count"] += 1

        items = [
            CustomerReceivableSummaryItem(**v)
            for v in cust_map.values()
        ]
        items.sort(key=lambda x: x.total_outstanding, reverse=True)

        return CustomerReceivableSummaryListResponse(items=items)

    # --- Customer Statement of Account (Feature #41) ---

    async def get_customer_statement(
        self,
        business_id: str,
        user_id: str,
        customer_id: str,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> CustomerStatementResponse:
        await self._validate_access(
            business_id,
            user_id,
            required_roles=(
                BusinessMembershipRole.OWNER,
                BusinessMembershipRole.ADMIN,
                BusinessMembershipRole.MEMBER,
            ),
        )

        customer = await customer_repository.get_by_id(customer_id, business_id)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found.",
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

        all_sales, _ = await self.sales_repo.list_sales(
            business_id=business_id,
            customer_id=customer_id,
            status=SalesStatus.FINALIZED,
            page=1,
            page_size=10000,
        )

        customer_sales_ids = {s.id for s in all_sales}

        all_sales_returns, _ = await self.sales_return_repo.list_returns(
            business_id=business_id,
            status=SalesReturnStatus.FINALIZED,
            page=1,
            page_size=10000,
        )
        all_sales_returns = [r for r in all_sales_returns if r.sales_id in customer_sales_ids]

        all_payments, _ = await self.payment_repo.list_payments(
            business_id=business_id,
            direction=PaymentDirection.CUSTOMER_IN,
            target_type=PaymentTargetType.SALES,
            page=1,
            page_size=10000,
        )
        all_payments = [p for p in all_payments if p.target_id in customer_sales_ids]

        opening_balance = Decimal("0.00")
        for s in all_sales:
            dt = _normalize_dt(s.sales_date)
            if dt < start_dt:
                opening_balance += s.grand_total
        for r in all_sales_returns:
            dt = _normalize_dt(r.return_date)
            if dt < start_dt:
                opening_balance -= r.grand_total
        for p in all_payments:
            if p.status != NewPaymentStatus.RECORDED:
                continue
            dt = _normalize_dt(p.payment_date)
            if dt < start_dt:
                opening_balance -= p.amount

        lines: List[StatementLineResponse] = []

        for s in all_sales:
            dt = _normalize_dt(s.sales_date)
            if start_dt <= dt < end_dt_exclusive:
                lines.append(StatementLineResponse(
                    transaction_date=dt,
                    transaction_type="SALE",
                    reference_id=s.id,
                    reference_number=s.sales_number,
                    description=None,
                    debit=s.grand_total,
                    credit=Decimal("0.00"),
                    running_balance=Decimal("0.00"),
                ))

        for r in all_sales_returns:
            dt = _normalize_dt(r.return_date)
            if start_dt <= dt < end_dt_exclusive:
                lines.append(StatementLineResponse(
                    transaction_date=dt,
                    transaction_type="SALES_RETURN",
                    reference_id=r.id,
                    reference_number=r.return_number,
                    description=r.notes,
                    debit=Decimal("0.00"),
                    credit=r.grand_total,
                    running_balance=Decimal("0.00"),
                ))

        for p in all_payments:
            if p.status != NewPaymentStatus.RECORDED:
                continue
            dt = _normalize_dt(p.payment_date)
            if start_dt <= dt < end_dt_exclusive:
                lines.append(StatementLineResponse(
                    transaction_date=dt,
                    transaction_type="CUSTOMER_PAYMENT",
                    reference_id=p.id,
                    reference_number=p.payment_number,
                    description=p.notes,
                    debit=Decimal("0.00"),
                    credit=p.amount,
                    running_balance=Decimal("0.00"),
                ))

        type_priority = {"SALE": 1, "CUSTOMER_PAYMENT": 2, "SALES_RETURN": 3}
        lines.sort(key=lambda x: (x.transaction_date, type_priority[x.transaction_type], x.reference_id))

        running = opening_balance
        total_debit = Decimal("0.00")
        total_credit = Decimal("0.00")

        for line in lines:
            total_debit += line.debit
            total_credit += line.credit
            running += line.debit - line.credit
            line.running_balance = running

        closing_balance = opening_balance + total_debit - total_credit

        total_items = len(lines)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paged_lines = lines[start_idx:end_idx]

        return CustomerStatementResponse(
            entity_id=customer_id,
            entity_name=customer.name,
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


sales_receivable_service = SalesReceivableService()

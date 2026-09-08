from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict
from fastapi import HTTPException, status

from app.modules.aging.schemas import (
    ARAgingResponse,
    ARAgingSummary,
    ARCustomerAgingSummaryItem,
    ARInvoiceAgingItem,
    APAgingResponse,
    APAgingSummary,
    APSupplierAgingSummaryItem,
    APInvoiceAgingItem,
)
from app.modules.aging.utils import (
    AgingBucket,
    compute_aging_days,
    compute_aging_bucket,
    bucket_field_name,
    now_utc,
)
from app.modules.sales.repository import sales_repository, AbstractSalesRepository
from app.modules.sales.schemas import SalesStatus
from app.modules.sales_return.repository import sales_return_repository, AbstractSalesReturnRepository
from app.modules.sales_return.schemas import SalesReturnStatus
from app.modules.purchase.repository import purchase_repository, AbstractPurchaseRepository
from app.modules.purchase.schemas import PurchaseStatus
from app.modules.purchase_return.repository import purchase_return_repository, AbstractPurchaseReturnRepository
from app.modules.purchase_return.schemas import PurchaseReturnStatus
from app.modules.payment.repository import payment_repository, AbstractPaymentRepository
from app.modules.payment.schemas import PaymentTargetType, PaymentStatus as NewPaymentStatus
from app.modules.customer.repository import customer_repository
from app.modules.supplier.repository import supplier_repository
from app.modules.branch.repository import branch_repository
from app.modules.business_membership.service import business_membership_service, BusinessMembershipService


class AgingService:
    def __init__(
        self,
        sales_repo: AbstractSalesRepository = sales_repository,
        sales_return_repo: AbstractSalesReturnRepository = sales_return_repository,
        purchase_repo: AbstractPurchaseRepository = purchase_repository,
        purchase_return_repo: AbstractPurchaseReturnRepository = purchase_return_repository,
        payment_repo: AbstractPaymentRepository = payment_repository,
        membership_service: BusinessMembershipService = business_membership_service,
    ):
        self.sales_repo = sales_repo
        self.sales_return_repo = sales_return_repo
        self.purchase_repo = purchase_repo
        self.purchase_return_repo = purchase_return_repo
        self.payment_repo = payment_repo
        self.membership_service = membership_service

    async def _validate_access(self, business_id: str, user_id: str):
        return await self.membership_service.require_active_membership(business_id, user_id)

    async def get_ar_aging(
        self,
        business_id: str,
        user_id: str,
        as_of_date: Optional[datetime] = None,
        customer_id: Optional[str] = None,
        branch_id: Optional[str] = None,
        bucket_filter: Optional[AgingBucket] = None,
    ) -> ARAgingResponse:
        await self._validate_access(business_id, user_id)

        # Validate customer belong to business if customer_id filter provided
        if customer_id and customer_id != "WALK_IN":
            cust = await customer_repository.get_by_id(customer_id, business_id)
            if not cust:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Customer not found in this business.",
                )

        # Validate branch belong to business if branch_id filter provided
        if branch_id:
            br = await branch_repository.get_by_id(branch_id)
            if not br or br.business_id != business_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Branch not found in this business.",
                )

        effective_as_of = as_of_date if as_of_date is not None else now_utc()

        # Retrieve all FINALIZED sales for this business
        all_sales, _ = await self.sales_repo.list_sales(
            business_id=business_id,
            status=SalesStatus.FINALIZED,
            customer_id=customer_id if customer_id != "WALK_IN" else None,
            branch_id=branch_id,
            page=1,
            page_size=10000,
        )

        invoices: List[ARInvoiceAgingItem] = []

        for s in all_sales:
            # Document economic date must be <= as_of_date
            if s.sales_date > effective_as_of:
                continue

            if customer_id == "WALK_IN" and s.customer_id is not None:
                continue

            # Original amount
            original_amount = s.grand_total if s.grand_total >= Decimal("0") else Decimal("0")

            # Active payments <= as_of_date
            raw_payments, _ = await self.payment_repo.list_payments(
                business_id=business_id,
                target_type=PaymentTargetType.SALES,
                target_id=s.id,
                page=1,
                page_size=1000,
            )
            active_paid = Decimal("0")
            for p in raw_payments:
                if p.status == NewPaymentStatus.RECORDED and p.payment_date <= effective_as_of:
                    active_paid += p.amount

            # Finalized sales returns <= as_of_date
            raw_returns, _ = await self.sales_return_repo.list_returns(
                business_id=business_id,
                sales_id=s.id,
                page=1,
                page_size=1000,
            )
            sales_return_adj = Decimal("0")
            for r in raw_returns:
                # Check economic return date or finalized_at <= as_of_date
                ret_date = r.finalized_at or r.return_date or r.created_at
                if r.status == SalesReturnStatus.FINALIZED and ret_date <= effective_as_of:
                    sales_return_adj += r.grand_total

            # Outstanding calculation
            outstanding = original_amount - sales_return_adj - active_paid
            if outstanding < Decimal("0"):
                outstanding = Decimal("0")

            # Exclude zero outstanding
            if outstanding == Decimal("0"):
                continue

            # Compute aging
            aging_days = compute_aging_days(s.sales_date, effective_as_of)
            aging_bucket = compute_aging_bucket(aging_days)

            # If age < 0 or bucket is None, excluded
            if aging_bucket is None:
                continue

            # Apply bucket filter
            if bucket_filter and aging_bucket != bucket_filter:
                continue

            # Resolve customer name
            cust_name = None
            if s.customer_id:
                c = await customer_repository.get_by_id(s.customer_id, business_id)
                if c:
                    cust_name = c.name
            else:
                cust_name = "Walk-in Customer"

            # Resolve branch name
            br_name = None
            if s.branch_id:
                br = await branch_repository.get_by_id(s.branch_id)
                if br and br.business_id == business_id:
                    br_name = br.name

            invoices.append(
                ARInvoiceAgingItem(
                    sales_id=s.id,
                    sales_number=s.sales_number,
                    sales_date=s.sales_date,
                    customer_id=s.customer_id,
                    customer_name=cust_name,
                    branch_id=s.branch_id,
                    branch_name=br_name,
                    original_amount=original_amount,
                    return_adjustment=sales_return_adj,
                    paid_amount=active_paid,
                    outstanding_amount=outstanding,
                    aging_days=aging_days,
                    aging_bucket=aging_bucket,
                )
            )

        # Sort invoice items deterministically: aging_days DESC, sales_date DESC, sales_id DESC
        invoices.sort(key=lambda x: (x.aging_days, x.sales_date, x.sales_id), reverse=True)

        # Build Customer Aggregation
        customer_map: Dict[str, Dict] = {}

        tot_orig = Decimal("0")
        tot_ret = Decimal("0")
        tot_paid = Decimal("0")
        tot_out = Decimal("0")

        sum_buckets = {
            "current": Decimal("0"),
            "bucket_1_30": Decimal("0"),
            "bucket_31_60": Decimal("0"),
            "bucket_61_90": Decimal("0"),
            "bucket_91_120": Decimal("0"),
            "bucket_over_120": Decimal("0"),
        }

        for inv in invoices:
            cid = inv.customer_id or "WALK_IN"
            cname = inv.customer_name or "Walk-in Customer"

            if cid not in customer_map:
                customer_map[cid] = {
                    "customer_id": inv.customer_id,
                    "customer_name": cname,
                    "total_original": Decimal("0"),
                    "total_return_adjustment": Decimal("0"),
                    "total_paid": Decimal("0"),
                    "total_outstanding": Decimal("0"),
                    "invoice_count": 0,
                    "current": Decimal("0"),
                    "bucket_1_30": Decimal("0"),
                    "bucket_31_60": Decimal("0"),
                    "bucket_61_90": Decimal("0"),
                    "bucket_91_120": Decimal("0"),
                    "bucket_over_120": Decimal("0"),
                }

            c_entry = customer_map[cid]
            c_entry["total_original"] += inv.original_amount
            c_entry["total_return_adjustment"] += inv.return_adjustment
            c_entry["total_paid"] += inv.paid_amount
            c_entry["total_outstanding"] += inv.outstanding_amount
            c_entry["invoice_count"] += 1

            fname = bucket_field_name(inv.aging_bucket)
            c_entry[fname] += inv.outstanding_amount

            tot_orig += inv.original_amount
            tot_ret += inv.return_adjustment
            tot_paid += inv.paid_amount
            tot_out += inv.outstanding_amount
            sum_buckets[fname] += inv.outstanding_amount

        customers = [
            ARCustomerAgingSummaryItem(**v)
            for v in customer_map.values()
        ]
        customers.sort(key=lambda x: x.total_outstanding, reverse=True)

        summary = ARAgingSummary(
            total_original=tot_orig,
            total_return_adjustment=tot_ret,
            total_paid=tot_paid,
            total_outstanding=tot_out,
            current=sum_buckets["current"],
            bucket_1_30=sum_buckets["bucket_1_30"],
            bucket_31_60=sum_buckets["bucket_31_60"],
            bucket_61_90=sum_buckets["bucket_61_90"],
            bucket_91_120=sum_buckets["bucket_91_120"],
            bucket_over_120=sum_buckets["bucket_over_120"],
        )

        return ARAgingResponse(
            as_of_date=effective_as_of,
            summary=summary,
            customers=customers,
            invoices=invoices,
        )

    async def get_ap_aging(
        self,
        business_id: str,
        user_id: str,
        as_of_date: Optional[datetime] = None,
        supplier_id: Optional[str] = None,
        branch_id: Optional[str] = None,
        bucket_filter: Optional[AgingBucket] = None,
    ) -> APAgingResponse:
        await self._validate_access(business_id, user_id)

        # Validate supplier belong to business if supplier_id filter provided
        if supplier_id:
            sup = await supplier_repository.get_by_id(supplier_id, business_id)
            if not sup:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Supplier not found in this business.",
                )

        # Validate branch belong to business if branch_id filter provided
        if branch_id:
            br = await branch_repository.get_by_id(branch_id)
            if not br or br.business_id != business_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Branch not found in this business.",
                )

        effective_as_of = as_of_date if as_of_date is not None else now_utc()

        # Retrieve all FINALIZED purchases for this business
        all_purchases, _ = await self.purchase_repo.list_purchases(
            business_id=business_id,
            status=PurchaseStatus.FINALIZED,
            supplier_id=supplier_id,
            branch_id=branch_id,
            page=1,
            page_size=10000,
        )

        purchases: List[APInvoiceAgingItem] = []

        for p in all_purchases:
            # Document economic date must be <= as_of_date
            if p.purchase_date > effective_as_of:
                continue

            # Gross payable
            gross_payable = p.grand_total if p.grand_total >= Decimal("0") else Decimal("0")

            # Finalized purchase returns <= as_of_date
            raw_returns, _ = await self.purchase_return_repo.list_returns(
                business_id=business_id,
                purchase_id=p.id,
                page=1,
                page_size=1000,
            )
            purchase_return_adj = Decimal("0")
            for r in raw_returns:
                ret_date = r.finalized_at or r.created_at
                if r.status == PurchaseReturnStatus.FINALIZED and ret_date <= effective_as_of:
                    purchase_return_adj += r.grand_total

            net_payable = gross_payable - purchase_return_adj
            if net_payable < Decimal("0"):
                net_payable = Decimal("0")

            # Active payments <= as_of_date
            raw_payments, _ = await self.payment_repo.list_payments(
                business_id=business_id,
                target_type=PaymentTargetType.PURCHASE,
                target_id=p.id,
                page=1,
                page_size=1000,
            )
            active_paid = Decimal("0")
            for pay in raw_payments:
                if pay.status == NewPaymentStatus.RECORDED and pay.payment_date <= effective_as_of:
                    active_paid += pay.amount

            # Outstanding calculation
            outstanding = net_payable - active_paid
            if outstanding < Decimal("0"):
                outstanding = Decimal("0")

            # Exclude zero outstanding
            if outstanding == Decimal("0"):
                continue

            # Compute aging
            aging_days = compute_aging_days(p.purchase_date, effective_as_of)
            aging_bucket = compute_aging_bucket(aging_days)

            # If age < 0 or bucket is None, excluded
            if aging_bucket is None:
                continue

            # Apply bucket filter
            if bucket_filter and aging_bucket != bucket_filter:
                continue

            # Resolve supplier name & code
            sup_name = None
            sup_code = None
            if p.supplier_id:
                sup = await supplier_repository.get_by_id(p.supplier_id, business_id)
                if sup:
                    sup_name = sup.name
                    sup_code = sup.code

            # Resolve branch name
            br_name = None
            if p.branch_id:
                br = await branch_repository.get_by_id(p.branch_id)
                if br and br.business_id == business_id:
                    br_name = br.name

            purchases.append(
                APInvoiceAgingItem(
                    purchase_id=p.id,
                    purchase_number=p.purchase_number,
                    purchase_date=p.purchase_date,
                    supplier_id=p.supplier_id,
                    supplier_name=sup_name,
                    supplier_code=sup_code,
                    branch_id=p.branch_id,
                    branch_name=br_name,
                    gross_payable=gross_payable,
                    return_adjustment=purchase_return_adj,
                    paid_amount=active_paid,
                    outstanding_amount=outstanding,
                    aging_days=aging_days,
                    aging_bucket=aging_bucket,
                )
            )

        # Sort purchase items deterministically: aging_days DESC, purchase_date DESC, purchase_id DESC
        purchases.sort(key=lambda x: (x.aging_days, x.purchase_date, x.purchase_id), reverse=True)

        # Build Supplier Aggregation
        supplier_map: Dict[str, Dict] = {}

        tot_gross = Decimal("0")
        tot_ret = Decimal("0")
        tot_paid = Decimal("0")
        tot_out = Decimal("0")

        sum_buckets = {
            "current": Decimal("0"),
            "bucket_1_30": Decimal("0"),
            "bucket_31_60": Decimal("0"),
            "bucket_61_90": Decimal("0"),
            "bucket_91_120": Decimal("0"),
            "bucket_over_120": Decimal("0"),
        }

        for pur in purchases:
            sid = pur.supplier_id

            if sid not in supplier_map:
                supplier_map[sid] = {
                    "supplier_id": sid,
                    "supplier_name": pur.supplier_name,
                    "supplier_code": pur.supplier_code,
                    "total_gross": Decimal("0"),
                    "total_return_adjustment": Decimal("0"),
                    "total_paid": Decimal("0"),
                    "total_outstanding": Decimal("0"),
                    "purchase_count": 0,
                    "current": Decimal("0"),
                    "bucket_1_30": Decimal("0"),
                    "bucket_31_60": Decimal("0"),
                    "bucket_61_90": Decimal("0"),
                    "bucket_91_120": Decimal("0"),
                    "bucket_over_120": Decimal("0"),
                }

            s_entry = supplier_map[sid]
            s_entry["total_gross"] += pur.gross_payable
            s_entry["total_return_adjustment"] += pur.return_adjustment
            s_entry["total_paid"] += pur.paid_amount
            s_entry["total_outstanding"] += pur.outstanding_amount
            s_entry["purchase_count"] += 1

            fname = bucket_field_name(pur.aging_bucket)
            s_entry[fname] += pur.outstanding_amount

            tot_gross += pur.gross_payable
            tot_ret += pur.return_adjustment
            tot_paid += pur.paid_amount
            tot_out += pur.outstanding_amount
            sum_buckets[fname] += pur.outstanding_amount

        suppliers = [
            APSupplierAgingSummaryItem(**v)
            for v in supplier_map.values()
        ]
        suppliers.sort(key=lambda x: x.total_outstanding, reverse=True)

        summary = APAgingSummary(
            total_gross=tot_gross,
            total_return_adjustment=tot_ret,
            total_paid=tot_paid,
            total_outstanding=tot_out,
            current=sum_buckets["current"],
            bucket_1_30=sum_buckets["bucket_1_30"],
            bucket_31_60=sum_buckets["bucket_31_60"],
            bucket_61_90=sum_buckets["bucket_61_90"],
            bucket_91_120=sum_buckets["bucket_91_120"],
            bucket_over_120=sum_buckets["bucket_over_120"],
        )

        return APAgingResponse(
            as_of_date=effective_as_of,
            summary=summary,
            suppliers=suppliers,
            purchases=purchases,
        )


aging_service = AgingService()

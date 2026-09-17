from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from typing import Optional, Dict, Tuple, List, Set
from enum import Enum

from fastapi import HTTPException, status

from app.modules.profitability.schemas import (
    ProductProfitabilityItem,
    ProductProfitabilitySummary,
    ProductProfitabilityPeriodInfo,
    ProductProfitabilityResponse,
)
from app.modules.sales.repository import sales_repository
from app.modules.sales.schemas import SalesStatus, SalesLineInDB
from app.modules.sales_return.repository import sales_return_repository
from app.modules.sales_return.schemas import SalesReturnStatus
from app.modules.product.repository import product_repository
from app.modules.category.repository import category_repository
from app.modules.customer.repository import customer_repository
from app.modules.branch.repository import branch_repository
from app.modules.product_variant.repository import product_variant_repository
from app.modules.accounting.repository import accounting_repository
from app.modules.business_membership.service import business_membership_service


class GroupBy(str, Enum):
    PRODUCT = "product"
    VARIANT = "variant"
    CATEGORY = "category"
    CUSTOMER = "customer"


class ProfitabilityService:
    async def _validate_access(self, business_id: str, user_id: str):
        await business_membership_service.require_active_membership(business_id, user_id)

    async def _resolve_period(
        self, business_id: str, period_id: str, user_id: str
    ) -> Tuple[date, date, Optional[str]]:
        period = await accounting_repository.get_period_by_id(period_id, business_id)
        if not period:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Accounting period not found.",
            )
        return period.start_date, period.end_date, period.period_name

    def _resolve_date_range(
        self,
        period_id: Optional[str],
        date_from: Optional[date],
        date_to: Optional[date],
    ) -> Tuple[date, date]:
        if date_from is not None and date_to is not None:
            if date_from > date_to:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="date_from must be less than or equal to date_to",
                )
            return date_from, date_to
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either period_id or both date_from and date_to must be provided.",
        )

    def _to_half_open_utc(
        self, start_date: date, end_date: date
    ) -> Tuple[datetime, datetime]:
        start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
        end_dt_exclusive = datetime.combine(
            end_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc
        )
        return start_dt, end_dt_exclusive

    def _resolve_group(
        self,
        group_by: GroupBy,
        product_id: str,
        variant_id: Optional[str],
        customer_id: Optional[str],
        product_cat_id: Optional[str],
    ) -> Tuple[str, str, Optional[str], Optional[str], Optional[str], Optional[str]]:
        if group_by == GroupBy.PRODUCT:
            return product_id, product_id, None, None, product_cat_id, None
        if group_by == GroupBy.VARIANT:
            gid = variant_id or f"standard:{product_id}"
            gname = variant_id or "Standard / No Variant"
            return gid, gname, None, None, product_cat_id, None
        if group_by == GroupBy.CATEGORY:
            gid = product_cat_id or "uncategorized"
            gname = product_cat_id or "Uncategorized"
            return gid, gname, None, None, product_cat_id, None
        if group_by == GroupBy.CUSTOMER:
            if customer_id is None:
                return "walk-in", "Walk-in / Cash Sales", None, None, None, None
            return customer_id, customer_id, None, customer_id, None, None
        raise ValueError(f"Unsupported group_by: {group_by}")

    async def _build_report(
        self,
        business_id: str,
        start_date: date,
        end_date: date,
        period_name: Optional[str],
        group_by: GroupBy,
        branch_id: Optional[str],
        product_id: Optional[str],
        variant_id: Optional[str],
        category_id: Optional[str],
        customer_id: Optional[str],
    ) -> ProductProfitabilityResponse:
        start_dt, end_dt_exclusive = self._to_half_open_utc(start_date, end_date)

        sales_items, _ = await sales_repository.list_sales(
            business_id=business_id,
            status=SalesStatus.FINALIZED,
            page=1,
            page_size=100000,
        )

        return_items, _ = await sales_return_repository.list_returns(
            business_id=business_id,
            status=SalesReturnStatus.FINALIZED,
            page=1,
            page_size=100000,
        )

        product_cache: Dict[str, object] = {}
        category_cache: Dict[str, object] = {}
        variant_cache: Dict[str, object] = {}
        customer_cache: Dict[str, object] = {}
        branch_cache: Dict[str, object] = {}

        async def get_product(pid: str):
            if pid not in product_cache:
                product_cache[pid] = await product_repository.get_by_id(pid, business_id)
            return product_cache[pid]

        async def get_category(cid: str):
            if cid not in category_cache:
                category_cache[cid] = await category_repository.get_by_id(cid, business_id)
            return category_cache[cid]

        async def get_variant(vid: str):
            if vid not in variant_cache:
                variant_cache[vid] = await product_variant_repository.get_by_id(vid, business_id)
            return variant_cache[vid]

        async def get_customer(cid: str):
            if cid not in customer_cache:
                customer_cache[cid] = await customer_repository.get_by_id(cid, business_id)
            return customer_cache[cid]

        async def get_branch(bid: str):
            if bid not in branch_cache:
                branch_cache[bid] = await branch_repository.get_by_id(bid)
            return branch_cache[bid]

        class GroupBucket:
            __slots__ = (
                "group_id", "group_name", "group_code", "category_name",
                "customer_name", "branch_name", "net_revenue", "total_discount",
                "total_tax", "gross_sales", "cogs", "units_sold", "units_returned",
                "sales_ids", "return_header_ids",
            )

            def __init__(self, group_id: str, group_name: str, group_code: Optional[str],
                         category_name: Optional[str], customer_name: Optional[str],
                         branch_name: Optional[str]):
                self.group_id = group_id
                self.group_name = group_name
                self.group_code = group_code
                self.category_name = category_name
                self.customer_name = customer_name
                self.branch_name = branch_name
                self.net_revenue = Decimal("0")
                self.total_discount = Decimal("0")
                self.total_tax = Decimal("0")
                self.gross_sales = Decimal("0")
                self.cogs = Decimal("0")
                self.units_sold = Decimal("0")
                self.units_returned = Decimal("0")
                self.sales_ids: Set[str] = set()
                self.return_header_ids: Set[str] = set()

        buckets: Dict[str, GroupBucket] = {}

        def matches_filters(
            s_branch_id: Optional[str],
            s_customer_id: Optional[str],
            l_product_id: str,
            l_variant_id: Optional[str],
            p_category_id: Optional[str],
        ) -> bool:
            if branch_id and s_branch_id != branch_id:
                return False
            if customer_id is not None:
                if customer_id == "walk-in":
                    if s_customer_id is not None:
                        return False
                elif s_customer_id != customer_id:
                    return False
            if product_id and l_product_id != product_id:
                return False
            if variant_id and l_variant_id != variant_id:
                return False
            if category_id and p_category_id != category_id:
                return False
            return True

        async def resolve_return_group(
            orig_sale, orig_line: SalesLineInDB
        ) -> Optional[Tuple[str, str, Optional[str], Optional[str], Optional[str], Optional[str]]]:
            prod = await get_product(orig_line.product_id)
            cat_id = prod.category_id if prod else None
            return self._resolve_group(
                group_by,
                orig_line.product_id,
                orig_line.variant_id,
                orig_sale.customer_id,
                cat_id,
            )

        async def ensure_bucket(
            group_id: str, group_name: str, group_code: Optional[str],
            category_name: Optional[str], customer_name: Optional[str],
            branch_name: Optional[str],
        ) -> GroupBucket:
            if group_id not in buckets:
                buckets[group_id] = GroupBucket(
                    group_id, group_name, group_code,
                    category_name, customer_name, branch_name,
                )
            return buckets[group_id]

        for sale in sales_items:
            if sale.status != SalesStatus.FINALIZED:
                continue
            if sale.is_deleted:
                continue
            if sale.sales_date < start_dt or sale.sales_date >= end_dt_exclusive:
                continue

            s_branch = sale.branch_id
            s_customer = sale.customer_id

            lines = await sales_repository.list_lines_for_sales(sale.id)
            for line in lines:
                prod = await get_product(line.product_id)
                cat_id = prod.category_id if prod else None

                if not matches_filters(s_branch, s_customer, line.product_id, line.variant_id, cat_id):
                    continue

                g_id, g_name, g_code, cat_name, cust_name, br_name = self._resolve_group(
                    group_by, line.product_id, line.variant_id, s_customer, cat_id,
                )

                if group_by == GroupBy.CUSTOMER:
                    if s_customer is not None:
                        cust_obj = await get_customer(s_customer)
                        if cust_obj:
                            g_name = cust_obj.name
                            g_code = cust_obj.code
                            cust_name = cust_obj.name
                    else:
                        g_name = "Walk-in / Cash Sales"
                        g_code = None
                        cust_name = "Walk-in / Cash Sales"

                cat_obj_name = None
                if group_by in (GroupBy.PRODUCT, GroupBy.VARIANT):
                    cat_obj = await get_category(cat_id) if cat_id else None
                    cat_obj_name = cat_obj.name if cat_obj else None
                elif group_by == GroupBy.CATEGORY:
                    cat_obj = await get_category(cat_id) if cat_id else None
                    g_name = cat_obj.name if cat_obj else "Uncategorized"
                    g_code = cat_obj.code if cat_obj else None
                    cat_obj_name = g_name

                br_obj = await get_branch(s_branch)
                br_obj_name = br_obj.name if br_obj else s_branch

                prod_name = prod.name if prod else line.product_id
                prod_code = prod.code if prod else None
                if group_by == GroupBy.PRODUCT:
                    g_name = prod_name
                    g_code = prod_code
                    cat_name = cat_obj_name
                elif group_by == GroupBy.VARIANT:
                    if line.variant_id:
                        var_obj = await get_variant(line.variant_id)
                        g_name = var_obj.name if var_obj else line.variant_id
                        g_code = var_obj.code if var_obj else None
                    else:
                        g_name = "Standard / No Variant"
                        g_code = None
                    cat_name = cat_obj_name

                bucket = await ensure_bucket(
                    g_id, g_name, g_code, cat_obj_name or cat_name,
                    cust_name or (g_name if group_by == GroupBy.CUSTOMER else None),
                    br_obj_name,
                )

                net_rev = line.line_total - line.tax_amount
                cogs = line.cost_total_snapshot if line.cost_total_snapshot is not None else Decimal("0")

                bucket.net_revenue += net_rev
                bucket.total_discount += line.discount_amount
                bucket.total_tax += line.tax_amount
                bucket.gross_sales += line.line_subtotal
                bucket.cogs += cogs
                bucket.units_sold += line.quantity
                bucket.sales_ids.add(sale.id)

        for ret in return_items:
            if ret.status != SalesReturnStatus.FINALIZED:
                continue
            ret_lines = await sales_return_repository.list_lines_for_return(ret.id)
            for rline in ret_lines:
                orig_sale = await sales_repository.get_sales_by_id(ret.sales_id, business_id)
                if not orig_sale:
                    continue
                orig_line = await sales_repository.get_line_by_id(rline.sales_line_id, ret.sales_id)
                if not orig_line:
                    continue

                prod = await get_product(orig_line.product_id)
                cat_id = prod.category_id if prod else None

                if not matches_filters(
                    orig_sale.branch_id, orig_sale.customer_id,
                    orig_line.product_id, orig_line.variant_id, cat_id,
                ):
                    continue

                g_id, g_name, g_code, cat_name, cust_name, br_name = await resolve_return_group(
                    orig_sale, orig_line,
                )

                if group_by == GroupBy.CUSTOMER:
                    if orig_sale.customer_id is not None:
                        cust_obj = await get_customer(orig_sale.customer_id)
                        if cust_obj:
                            g_name = cust_obj.name
                            g_code = cust_obj.code
                    else:
                        g_name = "Walk-in / Cash Sales"
                        g_code = None
                        cust_name = "Walk-in / Cash Sales"
                elif group_by == GroupBy.CATEGORY:
                    cat_obj = await get_category(cat_id) if cat_id else None
                    g_name = cat_obj.name if cat_obj else "Uncategorized"
                    g_code = cat_obj.code if cat_obj else None
                    cat_name = g_name
                elif group_by == GroupBy.PRODUCT:
                    prod_obj = prod
                    g_name = prod_obj.name if prod_obj else orig_line.product_id
                    g_code = prod_obj.code if prod_obj else None
                    cat_obj = await get_category(cat_id) if cat_id else None
                    cat_name = cat_obj.name if cat_obj else None
                elif group_by == GroupBy.VARIANT:
                    if orig_line.variant_id:
                        var_obj = await get_variant(orig_line.variant_id)
                        g_name = var_obj.name if var_obj else orig_line.variant_id
                        g_code = var_obj.code if var_obj else None
                    else:
                        g_name = "Standard / No Variant"
                        g_code = None
                    cat_obj = await get_category(cat_id) if cat_id else None
                    cat_name = cat_obj.name if cat_obj else None

                if group_by in (GroupBy.PRODUCT, GroupBy.VARIANT, GroupBy.CATEGORY):
                    br_obj = await get_branch(orig_sale.branch_id)
                    br_name = br_obj.name if br_obj else orig_sale.branch_id

                bucket = await ensure_bucket(
                    g_id, g_name, g_code, cat_name,
                    cust_name or (g_name if group_by == GroupBy.CUSTOMER else None),
                    br_name,
                )

                sold_qty = orig_line.quantity
                if sold_qty <= Decimal("0"):
                    continue
                ratio = rline.quantity / sold_qty

                ret_net = (orig_line.line_total - orig_line.tax_amount) * ratio
                ret_disc = orig_line.discount_amount * ratio
                ret_tax = orig_line.tax_amount * ratio
                ret_sub = orig_line.line_subtotal * ratio
                hist_cost = orig_line.unit_cost_snapshot if orig_line.unit_cost_snapshot is not None else Decimal("0")
                ret_cogs = rline.quantity * hist_cost

                bucket.net_revenue -= ret_net
                bucket.total_discount -= ret_disc
                bucket.total_tax -= ret_tax
                bucket.gross_sales -= ret_sub
                bucket.cogs -= ret_cogs
                bucket.units_returned += rline.quantity
                bucket.return_header_ids.add(ret.id)

        items: List[ProductProfitabilityItem] = []
        for b in buckets.values():
            net_rev = b.net_revenue
            cogs_val = b.cogs
            gp = net_rev - cogs_val
            margin = (gp / net_rev * Decimal("100")) if net_rev > Decimal("0") else None

            items.append(ProductProfitabilityItem(
                group_id=b.group_id,
                group_name=b.group_name,
                group_code=b.group_code,
                category_name=b.category_name,
                customer_name=b.customer_name,
                branch_name=b.branch_name,
                net_revenue=net_rev.quantize(Decimal("0.01")),
                total_discount=b.total_discount.quantize(Decimal("0.01")),
                total_tax=b.total_tax.quantize(Decimal("0.01")),
                gross_sales=b.gross_sales.quantize(Decimal("0.01")),
                cogs=cogs_val.quantize(Decimal("0.01")),
                gross_profit=gp.quantize(Decimal("0.01")),
                gross_margin_percentage=margin.quantize(Decimal("0.01")) if margin is not None else None,
                units_sold=b.units_sold,
                units_returned=b.units_returned,
                sales_count=len(b.sales_ids),
                return_count=len(b.return_header_ids),
            ))

        items.sort(key=lambda x: (x.group_name.lower(), x.group_id))

        total_net = sum(i.net_revenue for i in items) if items else Decimal("0")
        total_cogs = sum(i.cogs for i in items) if items else Decimal("0")
        total_gp = total_net - total_cogs
        overall_margin = (total_gp / total_net * Decimal("100")) if total_net > Decimal("0") else None
        total_sales = sum(i.sales_count for i in items) if items else 0
        total_rets = sum(i.return_count for i in items) if items else 0
        total_units_sold = sum(i.units_sold for i in items) if items else Decimal("0")
        total_units_ret = sum(i.units_returned for i in items) if items else Decimal("0")

        summary = ProductProfitabilitySummary(
            total_net_revenue=total_net.quantize(Decimal("0.01")),
            total_cogs=total_cogs.quantize(Decimal("0.01")),
            total_gross_profit=total_gp.quantize(Decimal("0.01")),
            overall_gross_margin_percentage=overall_margin.quantize(Decimal("0.01")) if overall_margin is not None else None,
            total_sales_count=total_sales,
            total_return_count=total_rets,
            total_units_sold=total_units_sold,
            total_units_returned=total_units_ret,
        )

        period_info = ProductProfitabilityPeriodInfo(
            date_from=start_date,
            date_to=end_date,
            period_name=period_name,
        )

        return ProductProfitabilityResponse(
            period=period_info,
            summary=summary,
            items=items,
        )

    async def get_profitability_report(
        self,
        business_id: str,
        user_id: str,
        period_id: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        group_by: str = "product",
        branch_id: Optional[str] = None,
        product_id: Optional[str] = None,
        variant_id: Optional[str] = None,
        category_id: Optional[str] = None,
        customer_id: Optional[str] = None,
    ) -> ProductProfitabilityResponse:
        await self._validate_access(business_id, user_id)

        try:
            gb = GroupBy(group_by)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid group_by value: {group_by}. Must be one of: product, variant, category, customer.",
            )

        if period_id:
            start_date, end_date, period_name = await self._resolve_period(business_id, period_id, user_id)
        else:
            start_date, end_date = self._resolve_date_range(period_id, date_from, date_to)
            period_name = None

        return await self._build_report(
            business_id=business_id,
            start_date=start_date,
            end_date=end_date,
            period_name=period_name,
            group_by=gb,
            branch_id=branch_id,
            product_id=product_id,
            variant_id=variant_id,
            category_id=category_id,
            customer_id=customer_id,
        )


profitability_service = ProfitabilityService()

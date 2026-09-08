from typing import List, Optional
from decimal import Decimal
from datetime import datetime, timezone
from fastapi import HTTPException, status

from app.modules.sales_return.schemas import (
    SalesReturnInDB,
    SalesReturnLineInDB,
    SalesReturnResponse,
    SalesReturnLineResponse,
    SalesReturnListResponse,
    SalesReturnCreate,
    SalesReturnUpdate,
    SalesReturnLineCreate,
    SalesReturnLineUpdate,
    SalesReturnStatus,
)
from app.modules.sales_return.repository import (
    AbstractSalesReturnRepository,
    sales_return_repository,
)
from app.modules.business_membership.service import (
    BusinessMembershipService,
    business_membership_service,
)
from app.modules.business_membership.schemas import BusinessMembershipRole
from app.modules.sales.repository import sales_repository
from app.modules.sales.schemas import SalesStatus
from app.modules.product.repository import product_repository
from app.modules.product.schemas import ProductType
from app.modules.inventory.service import inventory_service
from app.modules.inventory.schemas import InventoryCostMovementType
from app.modules.warehouse.repository import inventory_location_repository, warehouse_repository
from app.modules.warehouse.schemas import InventoryLocationStatus, WarehouseStatus
from app.modules.accounting.integration import accounting_integration_service


class SalesReturnService:
    def __init__(
        self,
        return_repo: AbstractSalesReturnRepository = sales_return_repository,
        membership_service: BusinessMembershipService = business_membership_service,
    ):
        self.return_repo = return_repo
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

    async def _validate_sales_finalized(self, business_id: str, sales_id: str):
        sales = await sales_repository.get_sales_by_id(sales_id, business_id)
        if not sales:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sales not found in this business.",
            )
        if sales.status != SalesStatus.FINALIZED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sales is not FINALIZED (current: {sales.status}). Sales Return is only allowed for FINALIZED sales.",
            )
        return sales

    async def _resolve_location(
        self,
        business_id: str,
        explicit_location_id: Optional[str],
        branch_id: str,
    ) -> str:
        """
        Priority:
        1. Explicit location_id provided -> validate ownership/business/active.
        2. Branch-scoped default warehouse + default location.
        3. Business-level default warehouse + default location.
        4. Fail 400.
        """
        if explicit_location_id is not None:
            loc = await inventory_location_repository.get_by_id(explicit_location_id)
            if not loc or loc.business_id != business_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Inventory location not found in this business.",
                )
            wh = await warehouse_repository.get_by_id(loc.warehouse_id)
            if not wh or wh.business_id != business_id or wh.status != WarehouseStatus.ACTIVE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Warehouse for this inventory location is invalid, inactive, or belongs to another business.",
                )
            if loc.status != InventoryLocationStatus.ACTIVE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Inventory location is not ACTIVE (current: {loc.status}).",
                )
            return loc.id

        wh = None
        if branch_id:
            branch_whs = await warehouse_repository.list_by_branch(business_id, branch_id)
            for w in branch_whs:
                if w.status == WarehouseStatus.ACTIVE and w.is_default:
                    wh = w
                    break

        if wh is None:
            wh = await warehouse_repository.get_default(business_id)
            if wh is not None and wh.status != WarehouseStatus.ACTIVE:
                wh = None

        if wh is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active default warehouse available for inventory location resolution.",
            )

        location = await inventory_location_repository.get_default(wh.id)
        if location is None or location.status != InventoryLocationStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active default inventory location in the resolved warehouse.",
            )
        return location.id

    async def _recalculate_totals(self, business_id: str, return_id: str):
        lines = await self.return_repo.list_lines_for_return(return_id)
        subtotal = Decimal("0")
        discount_total = Decimal("0")
        tax_total = Decimal("0")

        for l in lines:
            subtotal += l.line_subtotal
            discount_total += l.discount_amount
            tax_total += l.tax_amount

        grand_total = subtotal - discount_total + tax_total

        await self.return_repo.update_return(
            return_id=return_id,
            business_id=business_id,
            subtotal=subtotal,
            discount_total=discount_total,
            tax_total=tax_total,
            grand_total=grand_total,
        )

    async def create_return(
        self, business_id: str, user_id: str, payload: SalesReturnCreate
    ) -> SalesReturnResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        sales = await self._validate_sales_finalized(business_id, payload.sales_id)
        location_id = await self._resolve_location(business_id, payload.inventory_location_id, sales.branch_id)

        seq = await self.return_repo.get_next_return_sequence(business_id)
        return_number = f"SRT-{seq:06d}"

        ret = await self.return_repo.create_return(
            business_id=business_id,
            sales_id=payload.sales_id,
            inventory_location_id=location_id,
            return_number=return_number,
            return_date=sales.sales_date, # Use sales date as return date context
            created_by_user_id=user_id,
            notes=payload.notes,
        )

        return SalesReturnResponse(**ret.model_dump(), lines=[])

    async def list_returns(
        self,
        business_id: str,
        user_id: str,
        status_filter: Optional[SalesReturnStatus] = None,
        sales_id: Optional[str] = None,
        inventory_location_id: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> SalesReturnListResponse:
        await self._validate_access(business_id, user_id)

        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        returns, total = await self.return_repo.list_returns(
            business_id=business_id,
            status=status_filter,
            sales_id=sales_id,
            inventory_location_id=inventory_location_id,
            search=search,
            page=page,
            page_size=page_size,
        )

        items = []
        for r in returns:
            lines = await self.return_repo.list_lines_for_return(r.id)
            line_resp = [SalesReturnLineResponse.model_validate(l) for l in lines]
            items.append(SalesReturnResponse(**r.model_dump(), lines=line_resp))

        return SalesReturnListResponse(items=items, page=page, page_size=page_size, total=total)

    async def get_return(
        self, business_id: str, return_id: str, user_id: str
    ) -> SalesReturnResponse:
        await self._validate_access(business_id, user_id)
        r = await self.return_repo.get_return_by_id(return_id, business_id)
        if not r:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sales return not found.",
            )

        lines = await self.return_repo.list_lines_for_return(r.id)
        line_resp = [SalesReturnLineResponse.model_validate(l) for l in lines]
        return SalesReturnResponse(**r.model_dump(), lines=line_resp)

    async def update_return(
        self,
        business_id: str,
        return_id: str,
        user_id: str,
        payload: SalesReturnUpdate,
    ) -> SalesReturnResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        r = await self.return_repo.get_return_by_id(return_id, business_id)
        if not r:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sales return not found.",
            )

        if r.status != SalesReturnStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only DRAFT sales returns can be updated.",
            )

        updated = await self.return_repo.update_return(
            return_id=return_id,
            business_id=business_id,
            notes=payload.notes,
        )

        lines = await self.return_repo.list_lines_for_return(r.id)
        line_resp = [SalesReturnLineResponse.model_validate(l) for l in lines]
        return SalesReturnResponse(**updated.model_dump(), lines=line_resp)

    async def add_line(
        self,
        business_id: str,
        return_id: str,
        user_id: str,
        payload: SalesReturnLineCreate,
    ) -> SalesReturnLineResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        r = await self.return_repo.get_return_by_id(return_id, business_id)
        if not r:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sales return not found.",
            )

        if r.status != SalesReturnStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify lines of a non-draft sales return.",
            )

        # 1. Validate sales_line_id belongs to Sales and Business
        sales_line = await sales_repository.get_line_by_id(payload.sales_line_id, r.sales_id)
        if not sales_line:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sales line not found or does not belong to the source sales order.",
            )

        # 2. Check duplicate sales_line_id in this return
        existing_lines = await self.return_repo.list_lines_for_return(return_id)
        for el in existing_lines:
            if el.sales_line_id == payload.sales_line_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This sales line is already included in this sales return.",
                )

        # 3. Check Product Type must be GOODS
        product = await product_repository.get_by_id(sales_line.product_id, business_id)
        if not product or product.product_type != ProductType.GOODS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sales return is only allowed for GOODS products. SERVICE products cannot be returned.",
            )

        # 4. Capacity validation: sold_quantity - sum(non-cancelled returns)
        sold_qty = sales_line.quantity
        already_returned = await self.return_repo.sum_returned_quantity_for_sales_line(payload.sales_line_id)
        remaining_capacity = sold_qty - already_returned

        if payload.quantity > remaining_capacity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Requested return quantity ({payload.quantity}) exceeds remaining returnable capacity ({remaining_capacity}). Sold: {sold_qty}, already returned: {already_returned}.",
            )

        # 5. Snapshot pricing / amounts proportional to quantity ratio
        # unit_price = sales_line.unit_price
        # Proportional discount and tax allocation based on quantity
        ratio = payload.quantity / sales_line.quantity
        unit_price = sales_line.unit_price
        discount_amount = sales_line.discount_amount * ratio
        tax_amount = sales_line.tax_amount * ratio
        line_subtotal = payload.quantity * unit_price
        line_total = line_subtotal - discount_amount + tax_amount

        line = await self.return_repo.create_line(
            sales_return_id=return_id,
            sales_line_id=payload.sales_line_id,
            product_id=sales_line.product_id,
            variant_id=sales_line.variant_id,
            quantity=payload.quantity,
            unit_price=unit_price,
            discount_amount=discount_amount,
            tax_amount=tax_amount,
            line_subtotal=line_subtotal,
            line_total=line_total,
        )

        await self._recalculate_totals(business_id, return_id)
        return SalesReturnLineResponse.model_validate(line)

    async def update_line(
        self,
        business_id: str,
        return_id: str,
        line_id: str,
        user_id: str,
        payload: SalesReturnLineUpdate,
    ) -> SalesReturnLineResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        r = await self.return_repo.get_return_by_id(return_id, business_id)
        if not r:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sales return not found.",
            )

        if r.status != SalesReturnStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify lines of a non-draft sales return.",
            )

        line = await self.return_repo.get_line_by_id(line_id, return_id)
        if not line:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sales return line not found.",
            )

        sales_line = await sales_repository.get_line_by_id(line.sales_line_id, r.sales_id)
        if not sales_line:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source sales line not found.",
            )

        sold_qty = sales_line.quantity
        already_returned = await self.return_repo.sum_returned_quantity_for_sales_line(line.sales_line_id)
        # Exclude current line's old quantity from already_returned for capacity check
        other_returned = already_returned - line.quantity
        remaining_capacity = sold_qty - other_returned

        if payload.quantity > remaining_capacity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Requested return quantity ({payload.quantity}) exceeds remaining returnable capacity ({remaining_capacity}).",
            )

        ratio = payload.quantity / sales_line.quantity
        unit_price = sales_line.unit_price
        discount_amount = sales_line.discount_amount * ratio
        tax_amount = sales_line.tax_amount * ratio
        line_subtotal = payload.quantity * unit_price
        line_total = line_subtotal - discount_amount + tax_amount

        updated_line = await self.return_repo.update_line(
            line_id=line_id,
            sales_return_id=return_id,
            quantity=payload.quantity,
            unit_price=unit_price,
            discount_amount=discount_amount,
            tax_amount=tax_amount,
            line_subtotal=line_subtotal,
            line_total=line_total,
        )

        await self._recalculate_totals(business_id, return_id)
        return SalesReturnLineResponse.model_validate(updated_line)

    async def delete_line(
        self, business_id: str, return_id: str, line_id: str, user_id: str
    ) -> dict:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        r = await self.return_repo.get_return_by_id(return_id, business_id)
        if not r:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sales return not found.",
            )

        if r.status != SalesReturnStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify lines of a non-draft sales return.",
            )

        success = await self.return_repo.delete_line(line_id, return_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sales return line not found.",
            )

        await self._recalculate_totals(business_id, return_id)
        return {"message": "Sales return line successfully deleted."}

    async def finalize_return(
        self, business_id: str, return_id: str, user_id: str
    ) -> SalesReturnResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        r = await self.return_repo.get_return_by_id(return_id, business_id)
        if not r:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sales return not found.",
            )

        if r.status != SalesReturnStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sales return is not in DRAFT status.",
            )

        # 1. Re-validate source sales is FINALIZED
        await self._validate_sales_finalized(business_id, r.sales_id)

        # 2. Lines must exist
        lines = await self.return_repo.list_lines_for_return(return_id)
        if not lines:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot finalize a sales return without any lines.",
            )

        # 3. Final capacity recheck for all lines
        for l in lines:
            sales_line = await sales_repository.get_line_by_id(l.sales_line_id, r.sales_id)
            if not sales_line:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Source sales line no longer valid.",
                )
            sold_qty = sales_line.quantity
            already_returned = await self.return_repo.sum_returned_quantity_for_sales_line(l.sales_line_id)
            # Since this return is still DRAFT, its lines are included in sum_returned_quantity_for_sales_line.
            # But let's verify if total returned for this sales_line exceeds sold_qty.
            if already_returned > sold_qty:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Over-return detected at finalization for sales line {l.sales_line_id}.",
                )

        await self._recalculate_totals(business_id, return_id)

        # Re-fetch after recalculation to get accurate tax_total
        r_updated = await self.return_repo.get_return_by_id(return_id, business_id)
        return_tax_total = r_updated.tax_total if r_updated else Decimal("0")

        # 4. Prepare goods lines for inventory stock return and COGS reversal
        goods_lines = []
        total_reversal_cogs = Decimal("0")
        for l in lines:
            goods_lines.append({
                "product_id": l.product_id,
                "variant_id": l.variant_id,
                "quantity": l.quantity,
            })

            # Historical snapshot retrieval and reversal COGS calculation
            sales_line = await sales_repository.get_line_by_id(l.sales_line_id, r.sales_id)
            hist_unit_cost = sales_line.unit_cost_snapshot if sales_line and sales_line.unit_cost_snapshot is not None else Decimal("0")
            reversal_cogs = l.quantity * hist_unit_cost
            total_reversal_cogs += reversal_cogs

        now = datetime.now(timezone.utc)

        # ── ATOMIC BOUNDARY START ──
        # Accounting posting FIRST (idempotent, safe to retry).
        # If this fails, NO operational status change or inventory return occurs.
        idem_key = f"SALES_RETURN:{return_id}:FINALIZED"
        await accounting_integration_service.safe_post(
            idem_key,
            lambda: accounting_integration_service.post_sales_return_finalized(
                business_id=business_id,
                user_id=user_id,
                sales_return_id=return_id,
                grand_total=r.grand_total,
                tax_total=return_tax_total,
                reversal_cogs=total_reversal_cogs,
                return_date=r.return_date,
            )
        )

        # Then stock return + cost state restoration + status update
        await inventory_service.return_sales_stock(
            business_id=business_id,
            user_id=user_id,
            sales_return_id=return_id,
            return_number=r.return_number,
            location_id=r.inventory_location_id,
            goods_lines=goods_lines,
        )

        # Restore cost state
        for l in lines:
            sales_line = await sales_repository.get_line_by_id(l.sales_line_id, r.sales_id)
            hist_unit_cost = sales_line.unit_cost_snapshot if sales_line and sales_line.unit_cost_snapshot is not None else Decimal("0")

            await inventory_service.record_cost_inbound(
                business_id=business_id,
                product_id=l.product_id,
                variant_id=l.variant_id,
                inbound_qty=l.quantity,
                inbound_unit_cost=hist_unit_cost,
                movement_type=InventoryCostMovementType.SALE_RETURN_IN,
                reference_type="SALES_RETURN",
                reference_id=return_id,
            )

        updated = await self.return_repo.update_return(
            return_id=return_id,
            business_id=business_id,
            status=SalesReturnStatus.FINALIZED,
            finalized_by_user_id=user_id,
            finalized_at=now,
        )
        # ── ATOMIC BOUNDARY END ──

        line_resp = [SalesReturnLineResponse.model_validate(l) for l in lines]
        return SalesReturnResponse(**updated.model_dump(), lines=line_resp)

    async def cancel_return(
        self, business_id: str, return_id: str, user_id: str
    ) -> SalesReturnResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        r = await self.return_repo.get_return_by_id(return_id, business_id)
        if not r:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sales return not found.",
            )

        if r.status != SalesReturnStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only DRAFT sales returns can be cancelled.",
            )

        now = datetime.now(timezone.utc)
        updated = await self.return_repo.update_return(
            return_id=return_id,
            business_id=business_id,
            status=SalesReturnStatus.CANCELLED,
            cancelled_by_user_id=user_id,
            cancelled_at=now,
        )

        lines = await self.return_repo.list_lines_for_return(return_id)
        line_resp = [SalesReturnLineResponse.model_validate(l) for l in lines]
        return SalesReturnResponse(**updated.model_dump(), lines=line_resp)


sales_return_service = SalesReturnService()

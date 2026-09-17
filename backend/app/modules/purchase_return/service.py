from typing import List, Optional
from decimal import Decimal
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.purchase_return.schemas import (
    PurchaseReturnInDB,
    PurchaseReturnLineInDB,
    PurchaseReturnResponse,
    PurchaseReturnLineResponse,
    PurchaseReturnListResponse,
    PurchaseReturnCreate,
    PurchaseReturnUpdate,
    PurchaseReturnLineCreate,
    PurchaseReturnLineUpdate,
    PurchaseReturnStatus,
)
from app.modules.purchase_return.repository import (
    AbstractPurchaseReturnRepository,
    purchase_return_repository,
)
from app.modules.business_membership.service import (
    BusinessMembershipService,
    business_membership_service,
)
from app.modules.business_membership.schemas import BusinessMembershipRole
from app.modules.purchase.repository import purchase_repository
from app.modules.receiving.repository import receiving_repository
from app.modules.warehouse.repository import inventory_location_repository
from app.modules.purchase.schemas import PurchaseStatus
from app.modules.receiving.schemas import ReceivingStatus
from app.modules.warehouse.schemas import InventoryLocationStatus
from app.modules.accounting.integration import accounting_integration_service
from app.modules.inventory.service import inventory_service
from app.modules.inventory.schemas import InventoryCostMovementType


class PurchaseReturnService:
    def __init__(
        self,
        return_repo: AbstractPurchaseReturnRepository = purchase_return_repository,
        membership_service: BusinessMembershipService = business_membership_service,
        purchase_repo=None,
        receiving_repo=None,
        location_repo=None,
        accounting_integration=None,
        inv_service=None,
        session: Optional[AsyncSession] = None,
    ):
        self.return_repo = return_repo
        self.membership_service = membership_service
        self.purchase_repo = purchase_repo or purchase_repository
        self.receiving_repo = receiving_repo or receiving_repository
        self.location_repo = location_repo or inventory_location_repository
        self.accounting_integration = accounting_integration or accounting_integration_service
        self.inv_service = inv_service or inventory_service
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

    async def _validate_purchase_finalized(self, business_id: str, purchase_id: str):
        purchase = await self.purchase_repo.get_purchase_by_id(purchase_id, business_id)
        if not purchase:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase not found.",
            )
        if purchase.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Purchase has been deleted.",
            )
        if purchase.status != PurchaseStatus.FINALIZED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Purchase is not FINALIZED (current: {purchase.status}). Purchase Return is only allowed for FINALIZED purchases.",
            )
        return purchase

    async def _validate_location(self, business_id: str, inventory_location_id: str):
        loc = await self.location_repo.get_by_id(inventory_location_id)
        if not loc or loc.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inventory location not found in this business.",
            )
        if loc.status != InventoryLocationStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Inventory location is not ACTIVE (current: {loc.status}).",
            )
        return loc

    async def _calculate_effective_finalized_received_quantity(self, purchase_line_id: str) -> Decimal:
        """
        Calculate total received quantity from FINALIZED & non-deleted Receivings only for a given purchase_line_id.
        DRAFT, CANCELLED, and deleted Receivings DO NOT contribute to received quantity.
        """
        return await self.receiving_repo.sum_finalized_received_quantity_for_purchase_line(purchase_line_id)

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
        self, business_id: str, user_id: str, payload: PurchaseReturnCreate
    ) -> PurchaseReturnResponse:
        if self.session is not None:
            async with self.session.begin():
                return await self._create_return_impl(business_id, user_id, payload)
        return await self._create_return_impl(business_id, user_id, payload)

    async def _create_return_impl(
        self, business_id: str, user_id: str, payload: PurchaseReturnCreate
    ) -> PurchaseReturnResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        await self._validate_purchase_finalized(business_id, payload.purchase_id)
        await self._validate_location(business_id, payload.inventory_location_id)

        seq = await self.return_repo.get_next_return_sequence(business_id)
        return_number = f"PRT-{seq:06d}"

        ret = await self.return_repo.create_return(
            business_id=business_id,
            purchase_id=payload.purchase_id,
            inventory_location_id=payload.inventory_location_id,
            return_number=return_number,
            created_by_user_id=user_id,
            notes=payload.notes,
        )

        return PurchaseReturnResponse(**ret.model_dump(), lines=[])

    async def list_returns(
        self,
        business_id: str,
        user_id: str,
        status_filter: Optional[PurchaseReturnStatus] = None,
        purchase_id: Optional[str] = None,
        inventory_location_id: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PurchaseReturnListResponse:
        await self._validate_access(business_id, user_id)

        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        returns, total = await self.return_repo.list_returns(
            business_id=business_id,
            status=status_filter,
            purchase_id=purchase_id,
            inventory_location_id=inventory_location_id,
            search=search,
            page=page,
            page_size=page_size,
        )

        items = []
        for r in returns:
            lines = await self.return_repo.list_lines_for_return(r.id)
            line_resp = [PurchaseReturnLineResponse.model_validate(l) for l in lines]
            items.append(PurchaseReturnResponse(**r.model_dump(), lines=line_resp))

        return PurchaseReturnListResponse(items=items, page=page, page_size=page_size, total=total)

    async def get_return(
        self, business_id: str, return_id: str, user_id: str
    ) -> PurchaseReturnResponse:
        await self._validate_access(business_id, user_id)
        r = await self.return_repo.get_return_by_id(return_id, business_id)
        if not r:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase return not found.",
            )

        lines = await self.return_repo.list_lines_for_return(r.id)
        line_resp = [PurchaseReturnLineResponse.model_validate(l) for l in lines]
        return PurchaseReturnResponse(**r.model_dump(), lines=line_resp)

    async def update_return(
        self,
        business_id: str,
        return_id: str,
        user_id: str,
        payload: PurchaseReturnUpdate,
    ) -> PurchaseReturnResponse:
        if self.session is not None:
            async with self.session.begin():
                return await self._update_return_impl(business_id, return_id, user_id, payload)
        return await self._update_return_impl(business_id, return_id, user_id, payload)

    async def _update_return_impl(
        self,
        business_id: str,
        return_id: str,
        user_id: str,
        payload: PurchaseReturnUpdate,
    ) -> PurchaseReturnResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        r = await self.return_repo.get_return_by_id(return_id, business_id)
        if not r:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase return not found.",
            )

        if r.status != PurchaseReturnStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only DRAFT purchase returns can be updated.",
            )

        updated = await self.return_repo.update_return(
            return_id=return_id,
            business_id=business_id,
            notes=payload.notes,
        )

        lines = await self.return_repo.list_lines_for_return(r.id)
        line_resp = [PurchaseReturnLineResponse.model_validate(l) for l in lines]
        return PurchaseReturnResponse(**updated.model_dump(), lines=line_resp)

    async def delete_return(
        self, business_id: str, return_id: str, user_id: str
    ) -> dict:
        if self.session is not None:
            async with self.session.begin():
                return await self._delete_return_impl(business_id, return_id, user_id)
        return await self._delete_return_impl(business_id, return_id, user_id)

    async def _delete_return_impl(
        self, business_id: str, return_id: str, user_id: str
    ) -> dict:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        r = await self.return_repo.get_return_by_id(return_id, business_id)
        if not r:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase return not found.",
            )

        if r.status != PurchaseReturnStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only DRAFT purchase returns can be deleted.",
            )

        await self.return_repo.update_return(
            return_id=return_id,
            business_id=business_id,
            is_deleted=True,
        )

        return {"message": "Purchase return draft successfully deleted."}

    async def add_line(
        self,
        business_id: str,
        return_id: str,
        user_id: str,
        payload: PurchaseReturnLineCreate,
    ) -> PurchaseReturnLineResponse:
        if self.session is not None:
            async with self.session.begin():
                return await self._add_line_impl(business_id, return_id, user_id, payload)
        return await self._add_line_impl(business_id, return_id, user_id, payload)

    async def _add_line_impl(
        self,
        business_id: str,
        return_id: str,
        user_id: str,
        payload: PurchaseReturnLineCreate,
    ) -> PurchaseReturnLineResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        r = await self.return_repo.get_return_by_id(return_id, business_id)
        if not r:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase return not found.",
            )

        if r.status != PurchaseReturnStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify lines of a non-draft purchase return.",
            )

        # Validate purchase_line_id belongs to the purchase
        purchase_line = await self.purchase_repo.get_line_by_id(payload.purchase_line_id, r.purchase_id)
        if not purchase_line:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Purchase line not found or does not belong to this purchase.",
            )

        # 1. Effective received quantity (from FINALIZED non-deleted Receivings ONLY)
        finalized_received = await self._calculate_effective_finalized_received_quantity(payload.purchase_line_id)
        if finalized_received <= Decimal("0"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot return items for purchase line {payload.purchase_line_id} because no goods have been FINALIZED received yet.",
            )

        # 2. Effective returned quantity (from DRAFT and FINALIZED non-deleted Returns)
        already_returned = await self.return_repo.sum_returned_quantity_for_purchase_line(payload.purchase_line_id)

        if already_returned + payload.quantity > finalized_received:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Over-return error: finalized_received={finalized_received}, already_returned={already_returned}, requested={payload.quantity}, would_exceed_by={(already_returned + payload.quantity) - finalized_received}.",
            )

        # Inherit unit_price, discount from original purchase line
        # Tax: proportional from original if not explicitly provided by caller
        unit_price = payload.unit_price if payload.unit_price is not None else purchase_line.unit_price
        discount_amount = payload.discount_amount if payload.discount_amount is not None else Decimal("0")

        if payload.tax_amount is not None:
            tax_amount = payload.tax_amount
        elif purchase_line.tax_amount and purchase_line.tax_amount > Decimal("0") and purchase_line.quantity > Decimal("0"):
            ratio = payload.quantity / purchase_line.quantity
            tax_amount = purchase_line.tax_amount * ratio
        else:
            tax_amount = Decimal("0")

        line_subtotal = payload.quantity * unit_price
        if discount_amount > line_subtotal:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Discount amount cannot exceed line subtotal.",
            )

        line_total = line_subtotal - discount_amount + tax_amount

        line = await self.return_repo.create_line(
            return_id=return_id,
            purchase_line_id=payload.purchase_line_id,
            product_id=purchase_line.product_id,
            variant_id=purchase_line.variant_id,
            quantity=payload.quantity,
            unit_price=unit_price,
            discount_amount=discount_amount,
            tax_amount=tax_amount,
            line_subtotal=line_subtotal,
            line_total=line_total,
        )

        await self._recalculate_totals(business_id, return_id)

        return PurchaseReturnLineResponse.model_validate(line)

    async def update_line(
        self,
        business_id: str,
        return_id: str,
        line_id: str,
        user_id: str,
        payload: PurchaseReturnLineUpdate,
    ) -> PurchaseReturnLineResponse:
        if self.session is not None:
            async with self.session.begin():
                return await self._update_line_impl(business_id, return_id, line_id, user_id, payload)
        return await self._update_line_impl(business_id, return_id, line_id, user_id, payload)

    async def _update_line_impl(
        self,
        business_id: str,
        return_id: str,
        line_id: str,
        user_id: str,
        payload: PurchaseReturnLineUpdate,
    ) -> PurchaseReturnLineResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        r = await self.return_repo.get_return_by_id(return_id, business_id)
        if not r:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase return not found.",
            )

        if r.status != PurchaseReturnStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify lines of a non-draft purchase return.",
            )

        line = await self.return_repo.get_line_by_id(line_id, return_id)
        if not line:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase return line not found.",
            )

        purchase_line = await self.purchase_repo.get_line_by_id(line.purchase_line_id, r.purchase_id)
        if not purchase_line:
            purchase_lines = await self.purchase_repo.list_lines_for_purchase(r.purchase_id)
            for pl in purchase_lines:
                if pl.id == line.purchase_line_id:
                    purchase_line = pl
                    break

        target_qty = payload.quantity if payload.quantity is not None else line.quantity
        target_price = payload.unit_price if payload.unit_price is not None else line.unit_price
        target_disc = payload.discount_amount if payload.discount_amount is not None else line.discount_amount
        target_tax = payload.tax_amount if payload.tax_amount is not None else line.tax_amount

        finalized_received = await self._calculate_effective_finalized_received_quantity(line.purchase_line_id)
        already_returned = await self.return_repo.sum_returned_quantity_for_purchase_line(line.purchase_line_id)
        adjusted_returned = already_returned - line.quantity + target_qty

        if adjusted_returned > finalized_received:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Over-return error: finalized_received={finalized_received}, already_returned={already_returned}, current_line={line.quantity}, requested={target_qty}, would_exceed_by={adjusted_returned - finalized_received}.",
            )

        line_subtotal = target_qty * target_price
        if target_disc > line_subtotal:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Discount amount cannot exceed line subtotal.",
            )

        line_total = line_subtotal - target_disc + target_tax

        updated_line = await self.return_repo.update_line(
            line_id=line_id,
            return_id=return_id,
            quantity=payload.quantity,
            unit_price=payload.unit_price,
            discount_amount=payload.discount_amount,
            tax_amount=payload.tax_amount,
            line_subtotal=line_subtotal,
            line_total=line_total,
        )

        await self._recalculate_totals(business_id, return_id)

        return PurchaseReturnLineResponse.model_validate(updated_line)

    async def delete_line(
        self, business_id: str, return_id: str, line_id: str, user_id: str
    ) -> dict:
        if self.session is not None:
            async with self.session.begin():
                return await self._delete_line_impl(business_id, return_id, line_id, user_id)
        return await self._delete_line_impl(business_id, return_id, line_id, user_id)

    async def _delete_line_impl(
        self, business_id: str, return_id: str, line_id: str, user_id: str
    ) -> dict:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        r = await self.return_repo.get_return_by_id(return_id, business_id)
        if not r:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase return not found.",
            )

        if r.status != PurchaseReturnStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify lines of a non-draft purchase return.",
            )

        success = await self.return_repo.delete_line(line_id, return_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase return line not found.",
            )

        await self._recalculate_totals(business_id, return_id)
        return {"message": "Purchase return line successfully deleted."}

    async def finalize_return(
        self, business_id: str, return_id: str, user_id: str
    ) -> PurchaseReturnResponse:
        if self.session is not None:
            async with self.session.begin():
                return await self._finalize_return_impl(business_id, return_id, user_id)
        return await self._finalize_return_impl(business_id, return_id, user_id)

    async def _finalize_return_impl(
        self, business_id: str, return_id: str, user_id: str
    ) -> PurchaseReturnResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        r = await self.return_repo.get_return_by_id(return_id, business_id)
        if not r:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase return not found.",
            )

        if r.status != PurchaseReturnStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Purchase return is not in DRAFT status.",
            )

        # 1. Purchase still valid & FINALIZED
        await self._validate_purchase_finalized(business_id, r.purchase_id)

        # 2. Location still valid
        await self._validate_location(business_id, r.inventory_location_id)

        # 3. Lines must exist
        lines = await self.return_repo.list_lines_for_return(return_id)
        if not lines:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot finalize a purchase return without any lines.",
            )

        # 4. Revalidate all return quantities against current finalized received quantities
        from collections import defaultdict
        qty_by_pline: dict[str, Decimal] = defaultdict(Decimal)
        for line in lines:
            qty_by_pline[line.purchase_line_id] += line.quantity

        for pline_id, qty_in_this_return in qty_by_pline.items():
            finalized_received = await self._calculate_effective_finalized_received_quantity(pline_id)

            total_returned_for_pline = await self.return_repo.sum_returned_quantity_for_purchase_line(pline_id)

            if total_returned_for_pline > finalized_received:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Over-return at finalization: purchase_line={pline_id} finalized_received={finalized_received}, total_returned={total_returned_for_pline}.",
                )

        await self._recalculate_totals(business_id, return_id)

        now = datetime.now(timezone.utc)
        r_updated = await self.return_repo.get_return_by_id(return_id, business_id)
        grand_total = r_updated.grand_total if r_updated else Decimal("0")
        return_tax_total = r_updated.tax_total if r_updated else Decimal("0")

        # Resolve historical input_vat_creditable from original purchase
        original_purchase = await self.purchase_repo.get_purchase_by_id(r.purchase_id, business_id)
        input_vat_creditable = original_purchase.input_vat_creditable if original_purchase else False

        # ── ATOMIC BOUNDARY START ──
        # Accounting posting FIRST (idempotent, safe to retry).
        # If this fails, NO operational status change occurs.
        idem_key = f"PURCHASE_RETURN:{return_id}:FINALIZED"
        await self.accounting_integration.safe_post(
            idem_key,
            lambda: self.accounting_integration.post_purchase_return_finalized(
                business_id=business_id,
                user_id=user_id,
                purchase_return_id=return_id,
                grand_total=grand_total,
                tax_total=return_tax_total,
                input_vat_creditable=input_vat_creditable,
                return_date=r_updated.created_at if r_updated else now,
            )
        )

        # Physical stock reduction & cost pool reduction
        # ── AVAILABILITY + LOCK BOUNDARY ──
        from app.modules.sales_order.availability import availability_service, _inventory_lock
        _inventory_lock.acquire()
        try:
            # Check available_to_sell for each return line under reservation
            for line in lines:
                purchase_line = await self.purchase_repo.get_line_by_id(line.purchase_line_id, r.purchase_id)
                if not purchase_line:
                    continue
                physical_qty = await self.inv_service.get_physical_quantity(business_id, line.product_id, line.variant_id)
                reserved_qty = await availability_service.get_all_reservations_for_product(business_id, line.product_id, line.variant_id)
                available_qty = physical_qty - reserved_qty
                if available_qty < Decimal("0"):
                    available_qty = Decimal("0")
                if available_qty < line.quantity:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Insufficient available stock for purchase return. Product {line.product_id}: available {available_qty}, return quantity {line.quantity}.",
                    )

            for line in lines:
                purchase_line = await self.purchase_repo.get_line_by_id(line.purchase_line_id, r.purchase_id)
                if not purchase_line:
                    continue

                # Historical acquisition cost
                if line.unit_price is not None and line.unit_price != purchase_line.unit_price:
                    hist_unit_cost = line.unit_price
                else:
                    # Reconstruct original acquisition unit cost
                    if creditable_if := original_purchase.input_vat_creditable if original_purchase else False:
                        orig_net_cost = purchase_line.line_subtotal - purchase_line.discount_amount
                    else:
                        orig_net_cost = purchase_line.line_total
                    hist_unit_cost = orig_net_cost / purchase_line.quantity if purchase_line.quantity > Decimal("0") else Decimal("0")

                # Physical stock decrement
                await self.inv_service.upsert_balance(
                    business_id=business_id,
                    inventory_location_id=r.inventory_location_id,
                    product_id=line.product_id,
                    variant_id=line.variant_id,
                    delta=-line.quantity,
                )

                # Cost pool reduction
                await self.inv_service.record_cost_outbound(
                    business_id=business_id,
                    product_id=line.product_id,
                    variant_id=line.variant_id,
                    outbound_qty=line.quantity,
                    unit_cost=hist_unit_cost,
                    movement_type=InventoryCostMovementType.PURCHASE_RETURN_OUT,
                    reference_type="PURCHASE_RETURN",
                    reference_id=return_id,
                )
        finally:
            _inventory_lock.release()

        updated = await self.return_repo.update_return(
            return_id=return_id,
            business_id=business_id,
            status=PurchaseReturnStatus.FINALIZED,
            finalized_by_user_id=user_id,
            finalized_at=now,
        )
        # ── ATOMIC BOUNDARY END ──

        line_resp = [PurchaseReturnLineResponse.model_validate(l) for l in lines]
        return PurchaseReturnResponse(**updated.model_dump(), lines=line_resp)

    async def cancel_return(
        self, business_id: str, return_id: str, user_id: str
    ) -> PurchaseReturnResponse:
        if self.session is not None:
            async with self.session.begin():
                return await self._cancel_return_impl(business_id, return_id, user_id)
        return await self._cancel_return_impl(business_id, return_id, user_id)

    async def _cancel_return_impl(
        self, business_id: str, return_id: str, user_id: str
    ) -> PurchaseReturnResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        r = await self.return_repo.get_return_by_id(return_id, business_id)
        if not r:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase return not found.",
            )

        if r.status != PurchaseReturnStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only DRAFT purchase returns can be cancelled.",
            )

        now = datetime.now(timezone.utc)
        updated = await self.return_repo.update_return(
            return_id=return_id,
            business_id=business_id,
            status=PurchaseReturnStatus.CANCELLED,
            cancelled_by_user_id=user_id,
            cancelled_at=now,
        )

        lines = await self.return_repo.list_lines_for_return(return_id)
        line_resp = [PurchaseReturnLineResponse.model_validate(l) for l in lines]
        return PurchaseReturnResponse(**updated.model_dump(), lines=line_resp)


purchase_return_service = PurchaseReturnService()

from typing import List, Optional
from decimal import Decimal
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.receiving.schemas import (
    ReceivingInDB,
    ReceivingLineInDB,
    ReceivingResponse,
    ReceivingLineResponse,
    ReceivingListResponse,
    ReceivingCreate,
    ReceivingUpdate,
    ReceivingLineCreate,
    ReceivingLineUpdate,
    ReceivingStatus,
)
from app.modules.receiving.repository import (
    AbstractReceivingRepository,
    receiving_repository,
)
from app.modules.business_membership.service import (
    BusinessMembershipService,
    business_membership_service,
)
from app.modules.business_membership.schemas import BusinessMembershipRole
from app.modules.purchase.repository import purchase_repository
from app.modules.warehouse.repository import inventory_location_repository
from app.modules.purchase.schemas import PurchaseStatus
from app.modules.warehouse.schemas import InventoryLocationStatus
from app.modules.inventory_batch.service import inventory_batch_service


class ReceivingService:
    def __init__(
        self,
        receiving_repo: AbstractReceivingRepository = receiving_repository,
        membership_service: BusinessMembershipService = business_membership_service,
        purchase_repo=None,
        location_repo=None,
        session: Optional[AsyncSession] = None,
    ):
        self.receiving_repo = receiving_repo
        self.membership_service = membership_service
        self.purchase_repo = purchase_repo or purchase_repository
        self.location_repo = location_repo or inventory_location_repository
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
                detail=f"Purchase is not FINALIZED (current: {purchase.status}). Receiving is only allowed for FINALIZED purchases.",
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

    async def _validate_over_receiving(
        self,
        purchase_line_id: str,
        proposed_quantity: Decimal,
        ordered_quantity: Decimal,
        exclude_line_id: Optional[str] = None,
    ):
        existing_total = await self.receiving_repo.sum_received_quantity_for_purchase_line(purchase_line_id)
        if exclude_line_id:
            pass
        if existing_total + proposed_quantity > ordered_quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Over-receiving: ordered={ordered_quantity}, already_received={existing_total}, requested={proposed_quantity}, would_exceed_by={(existing_total + proposed_quantity) - ordered_quantity}.",
            )

    async def _validate_over_receiving_for_update(
        self,
        purchase_line_id: str,
        old_quantity: Decimal,
        new_quantity: Decimal,
        ordered_quantity: Decimal,
    ):
        existing_total = await self.receiving_repo.sum_received_quantity_for_purchase_line(purchase_line_id)
        adjusted_total = existing_total - old_quantity + new_quantity
        if adjusted_total > ordered_quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Over-receiving: ordered={ordered_quantity}, already_received={existing_total}, current_line={old_quantity}, requested={new_quantity}, would_exceed_by={adjusted_total - ordered_quantity}.",
            )

    async def _validate_all_lines_for_finalize(self, receiving_id: str):
        lines = await self.receiving_repo.list_lines_for_receiving(receiving_id)
        receiving = self._receiving_cache if hasattr(self, '_receiving_cache') else None
        for line in lines:
            pline = await purchase_repository.get_line_by_id(line.purchase_line_id, "")
            found_pline = None
            for pid_store, pval in purchase_repository._lines.items():
                pass
            purchase_line = await purchase_repository.get_line_by_id(line.purchase_line_id, line.product_id)
            if not purchase_line:
                actual_line = None
                for lid, lval in purchase_repository._lines.items():
                    if lval.id == line.purchase_line_id:
                        actual_line = lval
                        break
                if not actual_line:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Purchase line {line.purchase_line_id} not found.",
                    )
                purchase_line = actual_line

            total_for_line = Decimal("0")
            for rl in self.receiving_repo._lines.values():
                if rl.purchase_line_id != line.purchase_line_id:
                    continue
                r = self.receiving_repo._receivings.get(rl.receiving_id)
                if not r or r.is_deleted:
                    continue
                if r.status == ReceivingStatus.CANCELLED:
                    continue
                total_for_line += rl.quantity

            if total_for_line > purchase_line.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Over-receiving at finalization: purchase_line={line.purchase_line_id} ordered={purchase_line.quantity}, total_received={total_for_line}.",
                )

    async def create_receiving(
        self, business_id: str, user_id: str, payload: ReceivingCreate
    ) -> ReceivingResponse:
        if self.session is not None:
            async with self.session.begin():
                return await self._create_receiving_with_retry(business_id, user_id, payload)
        return await self._create_receiving_with_retry(business_id, user_id, payload)

    async def _create_receiving_with_retry(self, business_id: str, user_id: str, payload: ReceivingCreate) -> ReceivingResponse:
        for attempt in range(3):
            try:
                if self.session is not None:
                    async with self.session.begin_nested():
                        return await self._create_receiving_impl(business_id, user_id, payload)
                else:
                    return await self._create_receiving_impl(business_id, user_id, payload)
            except Exception as e:
                err_str = str(e).lower()
                if ("unique" in err_str and ("receiving_number" in err_str or "uq_receiving" in err_str)) and attempt < 2:
                    continue
                raise
        raise HTTPException(status_code=409, detail="Document number collision; please retry")

    async def _create_receiving_impl(
        self, business_id: str, user_id: str, payload: ReceivingCreate
    ) -> ReceivingResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        await self._validate_purchase_finalized(business_id, payload.purchase_id)
        await self._validate_location(business_id, payload.inventory_location_id)

        seq = await self.receiving_repo.get_next_receiving_sequence(business_id)
        receiving_number = f"RCV-{seq:06d}"

        receiving = await self.receiving_repo.create_receiving(
            business_id=business_id,
            purchase_id=payload.purchase_id,
            inventory_location_id=payload.inventory_location_id,
            receiving_number=receiving_number,
            created_by_user_id=user_id,
            notes=payload.notes,
        )

        return ReceivingResponse(**receiving.model_dump(), lines=[])

    async def list_receivings(
        self,
        business_id: str,
        user_id: str,
        status_filter: Optional[ReceivingStatus] = None,
        purchase_id: Optional[str] = None,
        inventory_location_id: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> ReceivingListResponse:
        await self._validate_access(business_id, user_id)

        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        receivings, total = await self.receiving_repo.list_receivings(
            business_id=business_id,
            status=status_filter,
            purchase_id=purchase_id,
            inventory_location_id=inventory_location_id,
            search=search,
            page=page,
            page_size=page_size,
        )

        items = []
        for r in receivings:
            lines = await self.receiving_repo.list_lines_for_receiving(r.id)
            line_resp = [ReceivingLineResponse.model_validate(l) for l in lines]
            items.append(ReceivingResponse(**r.model_dump(), lines=line_resp))

        return ReceivingListResponse(items=items, page=page, page_size=page_size, total=total)

    async def get_receiving(
        self, business_id: str, receiving_id: str, user_id: str
    ) -> ReceivingResponse:
        await self._validate_access(business_id, user_id)
        r = await self.receiving_repo.get_receiving_by_id(receiving_id, business_id)
        if not r:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Receiving not found.",
            )

        lines = await self.receiving_repo.list_lines_for_receiving(r.id)
        line_resp = [ReceivingLineResponse.model_validate(l) for l in lines]
        return ReceivingResponse(**r.model_dump(), lines=line_resp)

    async def update_receiving(
        self,
        business_id: str,
        receiving_id: str,
        user_id: str,
        payload: ReceivingUpdate,
    ) -> ReceivingResponse:
        if self.session is not None:
            async with self.session.begin():
                return await self._update_receiving_impl(business_id, receiving_id, user_id, payload)
        return await self._update_receiving_impl(business_id, receiving_id, user_id, payload)

    async def _update_receiving_impl(
        self,
        business_id: str,
        receiving_id: str,
        user_id: str,
        payload: ReceivingUpdate,
    ) -> ReceivingResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        r = await self.receiving_repo.get_receiving_by_id(receiving_id, business_id)
        if not r:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Receiving not found.",
            )

        if r.status != ReceivingStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only DRAFT receivings can be updated.",
            )

        updated = await self.receiving_repo.update_receiving(
            receiving_id=receiving_id,
            business_id=business_id,
            notes=payload.notes,
        )

        lines = await self.receiving_repo.list_lines_for_receiving(r.id)
        line_resp = [ReceivingLineResponse.model_validate(l) for l in lines]
        return ReceivingResponse(**updated.model_dump(), lines=line_resp)

    async def delete_receiving(
        self, business_id: str, receiving_id: str, user_id: str
    ) -> dict:
        if self.session is not None:
            async with self.session.begin():
                return await self._delete_receiving_impl(business_id, receiving_id, user_id)
        return await self._delete_receiving_impl(business_id, receiving_id, user_id)

    async def _delete_receiving_impl(
        self, business_id: str, receiving_id: str, user_id: str
    ) -> dict:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        r = await self.receiving_repo.get_receiving_by_id(receiving_id, business_id)
        if not r:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Receiving not found.",
            )

        if r.status != ReceivingStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only DRAFT receivings can be deleted.",
            )

        await self.receiving_repo.update_receiving(
            receiving_id=receiving_id,
            business_id=business_id,
            is_deleted=True,
        )

        return {"message": "Receiving draft successfully deleted."}

    async def add_line(
        self,
        business_id: str,
        receiving_id: str,
        user_id: str,
        payload: ReceivingLineCreate,
    ) -> ReceivingLineResponse:
        if self.session is not None:
            async with self.session.begin():
                return await self._add_line_impl(business_id, receiving_id, user_id, payload)
        return await self._add_line_impl(business_id, receiving_id, user_id, payload)

    async def _add_line_impl(
        self,
        business_id: str,
        receiving_id: str,
        user_id: str,
        payload: ReceivingLineCreate,
    ) -> ReceivingLineResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        r = await self.receiving_repo.get_receiving_by_id(receiving_id, business_id)
        if not r:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Receiving not found.",
            )

        if r.status != ReceivingStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify lines of a non-draft receiving.",
            )

        purchase_line = await self.purchase_repo.get_line_by_id(payload.purchase_line_id, r.purchase_id)
        if not purchase_line:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Purchase line not found or does not belong to this purchase.",
            )

        total_received = await self.receiving_repo.sum_received_quantity_for_purchase_line(payload.purchase_line_id)
        if total_received + payload.quantity > purchase_line.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Over-receiving: ordered={purchase_line.quantity}, already_received={total_received}, requested={payload.quantity}, would_exceed_by={(total_received + payload.quantity) - purchase_line.quantity}.",
            )

        line = await self.receiving_repo.create_line(
            receiving_id=receiving_id,
            purchase_line_id=payload.purchase_line_id,
            product_id=purchase_line.product_id,
            variant_id=purchase_line.variant_id,
            quantity=payload.quantity,
            batch_allocations=payload.batch_allocations,
        )

        return ReceivingLineResponse.model_validate(line)

    async def update_line(
        self,
        business_id: str,
        receiving_id: str,
        line_id: str,
        user_id: str,
        payload: ReceivingLineUpdate,
    ) -> ReceivingLineResponse:
        if self.session is not None:
            async with self.session.begin():
                return await self._update_line_impl(business_id, receiving_id, line_id, user_id, payload)
        return await self._update_line_impl(business_id, receiving_id, line_id, user_id, payload)

    async def _update_line_impl(
        self,
        business_id: str,
        receiving_id: str,
        line_id: str,
        user_id: str,
        payload: ReceivingLineUpdate,
    ) -> ReceivingLineResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        r = await self.receiving_repo.get_receiving_by_id(receiving_id, business_id)
        if not r:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Receiving not found.",
            )

        if r.status != ReceivingStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify lines of a non-draft receiving.",
            )

        line = await self.receiving_repo.get_line_by_id(line_id, receiving_id)
        if not line:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Receiving line not found.",
            )

        purchase_line = await self.purchase_repo.get_line_by_id(line.purchase_line_id, r.purchase_id)
        if not purchase_line:
            purchase_lines = await self.purchase_repo.list_lines_for_purchase(r.purchase_id)
            for pl in purchase_lines:
                if pl.id == line.purchase_line_id:
                    purchase_line = pl
                    break
            if not purchase_line:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Associated purchase line not found.",
                )

        total_received = await self.receiving_repo.sum_received_quantity_for_purchase_line(line.purchase_line_id)
        adjusted = total_received - line.quantity + payload.quantity
        if adjusted > purchase_line.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Over-receiving: ordered={purchase_line.quantity}, already_received={total_received}, current_line={line.quantity}, requested={payload.quantity}, would_exceed_by={adjusted - purchase_line.quantity}.",
            )

        updated_line = await self.receiving_repo.update_line(
            line_id=line_id,
            receiving_id=receiving_id,
            quantity=payload.quantity,
        )

        return ReceivingLineResponse.model_validate(updated_line)

    async def delete_line(
        self, business_id: str, receiving_id: str, line_id: str, user_id: str
    ) -> dict:
        if self.session is not None:
            async with self.session.begin():
                return await self._delete_line_impl(business_id, receiving_id, line_id, user_id)
        return await self._delete_line_impl(business_id, receiving_id, line_id, user_id)

    async def _delete_line_impl(
        self, business_id: str, receiving_id: str, line_id: str, user_id: str
    ) -> dict:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        r = await self.receiving_repo.get_receiving_by_id(receiving_id, business_id)
        if not r:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Receiving not found.",
            )

        if r.status != ReceivingStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify lines of a non-draft receiving.",
            )

        success = await self.receiving_repo.delete_line(line_id, receiving_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Receiving line not found.",
            )

        return {"message": "Receiving line successfully deleted."}

    async def finalize_receiving(
        self, business_id: str, receiving_id: str, user_id: str
    ) -> ReceivingResponse:
        if self.session is not None:
            async with self.session.begin():
                return await self._finalize_receiving_impl(business_id, receiving_id, user_id)
        return await self._finalize_receiving_impl(business_id, receiving_id, user_id)

    async def _finalize_receiving_impl(
        self, business_id: str, receiving_id: str, user_id: str
    ) -> ReceivingResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        r = await self.receiving_repo.get_receiving_by_id(receiving_id, business_id)
        if not r:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Receiving not found.",
            )

        if r.status != ReceivingStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Receiving is not in DRAFT status.",
            )

        lines = await self.receiving_repo.list_lines_for_receiving(receiving_id)
        if not lines:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot finalize a receiving without any lines.",
            )

        for line in lines:
            purchase_line = await self.purchase_repo.get_line_by_id(line.purchase_line_id, r.purchase_id)
            if not purchase_line:
                purchase_lines = await self.purchase_repo.list_lines_for_purchase(r.purchase_id)
                for pl in purchase_lines:
                    if pl.id == line.purchase_line_id and pl.purchase_id == r.purchase_id:
                        purchase_line = pl
                        break
                if purchase_line is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Purchase line {line.purchase_line_id} not found in purchase {r.purchase_id}.",
                    )

        from collections import defaultdict
        qty_by_pline: dict[str, Decimal] = defaultdict(Decimal)
        for line in lines:
            qty_by_pline[line.purchase_line_id] += line.quantity

        for pline_id, qty_in_this_receiving in qty_by_pline.items():
            purchase_lines = await self.purchase_repo.list_lines_for_purchase(r.purchase_id)
            purchase_line = None
            for pl in purchase_lines:
                if pl.id == pline_id:
                    purchase_line = pl
                    break
            if not purchase_line:
                continue

            total_for_line = await self.receiving_repo.sum_received_quantity_for_purchase_line(pline_id)

            if total_for_line > purchase_line.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Over-receiving at finalization: purchase_line={pline_id} ordered={purchase_line.quantity}, total_received={total_for_line}.",
                )

        from app.modules.inventory.service import inventory_service
        from app.modules.inventory.schemas import (
            MovementType, MovementDirection, ReferenceType as InvReferenceType,
            InventoryCostMovementType,
        )
        from app.modules.product.repository import product_repository

        product_repo = product_repository

        await inventory_service._validate_location(business_id, r.inventory_location_id)

        existing_movements = await inventory_service.movement_repo.list_movements(
            business_id=business_id,
            movement_type=MovementType.ADJUSTMENT_IN,
        )
        for m in existing_movements:
            if m.reference_type == InvReferenceType.RECEIVING and m.reference_id == receiving_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Receiving has already been finalized. Duplicate finalization rejected.",
                )

        now = datetime.now(timezone.utc)
        updated = await self.receiving_repo.update_receiving(
            receiving_id=receiving_id,
            business_id=business_id,
            status=ReceivingStatus.FINALIZED,
            finalized_by_user_id=user_id,
            finalized_at=now,
        )

        for line in lines:
            allocations = getattr(line, 'batch_allocations', None) or []
            for alloc in allocations:
                await inventory_batch_service.record_batch_inbound(
                    business_id=r.business_id,
                    inventory_location_id=r.inventory_location_id,
                    product_id=line.product_id,
                    variant_id=line.variant_id,
                    batch_number=alloc.get("batch_number", f"AUTO-{line.id}"),
                    quantity=Decimal(str(alloc.get("quantity", 0))),
                    manufacture_date=None,
                    expiry_date=None,
                    stock_movement_id=f"RCV:{receiving_id}:{line.id}",
                )

        for line in lines:
            movement = await inventory_service.movement_repo.create_movement(
                business_id=business_id,
                movement_type=MovementType.ADJUSTMENT_IN,
                performed_by_user_id=user_id,
                reference_type=InvReferenceType.RECEIVING,
                reference_id=receiving_id,
                notes=f"Stock inbound from Receiving {receiving_id}",
            )

            await inventory_service.movement_repo.create_line(
                movement_id=movement.id,
                inventory_location_id=r.inventory_location_id,
                product_id=line.product_id,
                variant_id=line.variant_id,
                quantity=line.quantity,
                direction=MovementDirection.IN,
            )

            await inventory_service.balance_repo.upsert_balance(
                business_id=business_id,
                inventory_location_id=r.inventory_location_id,
                product_id=line.product_id,
                variant_id=line.variant_id,
                delta=line.quantity,
            )

            purchase_line = await self.purchase_repo.get_line_by_id(line.purchase_line_id, r.purchase_id)
            if not purchase_line:
                plines = await self.purchase_repo.list_lines_for_purchase(r.purchase_id)
                for pl in plines:
                    if pl.id == line.purchase_line_id:
                        purchase_line = pl
                        break

            if purchase_line and purchase_line.quantity and purchase_line.quantity > Decimal("0"):
                unit_cost = purchase_line.unit_price
                await inventory_service.record_cost_inbound(
                    business_id=business_id,
                    product_id=line.product_id,
                    variant_id=line.variant_id,
                    inbound_qty=line.quantity,
                    inbound_unit_cost=unit_cost,
                    movement_type=InventoryCostMovementType.PURCHASE_RECEIVING,
                    reference_type="RECEIVING",
                    reference_id=receiving_id,
                )

        for line in lines:
            has_batches = await inventory_batch_service.has_batch_balances(
                r.business_id, r.inventory_location_id, line.product_id, line.variant_id,
            )
            if has_batches:
                balance = await inventory_service.balance_repo.get_balance(
                    business_id, r.inventory_location_id, line.product_id, line.variant_id,
                )
                aggregate_qty = balance.quantity if balance else Decimal("0")
                await inventory_batch_service.validate_batch_aggregate_invariant(
                    r.business_id, r.inventory_location_id, line.product_id, line.variant_id,
                    aggregate_quantity=aggregate_qty,
                )

        line_resp = [ReceivingLineResponse.model_validate(l) for l in lines]

        # ── NOTIFICATION (post-commit, failure-isolated) ──
        try:
            from app.modules.notification.service import _send_notification
            from app.modules.notification.schemas import (
                NotificationScope, NotificationType, NotificationSeverity,
            )
            from app.modules.business_membership.repository import (
                business_membership_repository,
            )
            from app.modules.business_membership.schemas import (
                BusinessMembershipRole, BusinessMembershipStatus,
            )

            purchase = await self.purchase_repo.get_purchase_by_id(r.purchase_id, business_id)
            purchase_number = purchase.purchase_number if purchase else "N/A"

            owner_admin_ids = [
                m.user_id
                for m in business_membership_repository._memberships.values()
                if m.business_id == business_id
                and m.status == BusinessMembershipStatus.ACTIVE
                and m.role in (BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
            ]
            for member_id in owner_admin_ids:
                await _send_notification(
                    recipient_id=member_id,
                    scope=NotificationScope.TENANT,
                    notif_type=NotificationType.PURCHASE_RECEIVED,
                    severity=NotificationSeverity.INFO,
                    title="Goods Received",
                    message=f"Receiving {updated.receiving_number} for purchase {purchase_number} has been finalized.",
                    business_id=business_id,
                    metadata={
                        "receiving_id": receiving_id,
                        "purchase_id": r.purchase_id,
                        "receiving_number": updated.receiving_number,
                        "branch_id": None,
                    },
                    deduplication_key=f"PURCHASE_RECEIVED:{receiving_id}:{member_id}",
                )
        except Exception:
            pass

        return ReceivingResponse(**updated.model_dump(), lines=line_resp)

    async def cancel_receiving(
        self, business_id: str, receiving_id: str, user_id: str
    ) -> ReceivingResponse:
        if self.session is not None:
            async with self.session.begin():
                return await self._cancel_receiving_impl(business_id, receiving_id, user_id)
        return await self._cancel_receiving_impl(business_id, receiving_id, user_id)

    async def _cancel_receiving_impl(
        self, business_id: str, receiving_id: str, user_id: str
    ) -> ReceivingResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        r = await self.receiving_repo.get_receiving_by_id(receiving_id, business_id)
        if not r:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Receiving not found.",
            )

        if r.status != ReceivingStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only DRAFT receivings can be cancelled.",
            )

        now = datetime.now(timezone.utc)
        updated = await self.receiving_repo.update_receiving(
            receiving_id=receiving_id,
            business_id=business_id,
            status=ReceivingStatus.CANCELLED,
            cancelled_by_user_id=user_id,
            cancelled_at=now,
        )

        lines = await self.receiving_repo.list_lines_for_receiving(receiving_id)
        line_resp = [ReceivingLineResponse.model_validate(l) for l in lines]
        return ReceivingResponse(**updated.model_dump(), lines=line_resp)


receiving_service = ReceivingService()

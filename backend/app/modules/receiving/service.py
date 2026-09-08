from typing import List, Optional
from decimal import Decimal
from datetime import datetime, timezone
from fastapi import HTTPException, status

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


class ReceivingService:
    def __init__(
        self,
        receiving_repo: AbstractReceivingRepository = receiving_repository,
        membership_service: BusinessMembershipService = business_membership_service,
    ):
        self.receiving_repo = receiving_repo
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

    async def _validate_purchase_finalized(self, business_id: str, purchase_id: str):
        purchase = await purchase_repository.get_purchase_by_id(purchase_id, business_id)
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
        loc = await inventory_location_repository.get_by_id(inventory_location_id)
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

        purchase_line = await purchase_repository.get_line_by_id(payload.purchase_line_id, r.purchase_id)
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

        purchase_line = await purchase_repository.get_line_by_id(line.purchase_line_id, r.purchase_id)
        if not purchase_line:
            for lid, lval in purchase_repository._lines.items():
                if lval.id == line.purchase_line_id:
                    purchase_line = lval
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
            purchase_line = await purchase_repository.get_line_by_id(line.purchase_line_id, r.purchase_id)
            if not purchase_line:
                found = None
                for lid, lval in purchase_repository._lines.items():
                    if lval.id == line.purchase_line_id and lval.purchase_id == r.purchase_id:
                        found = lval
                        break
                if not found:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Purchase line {line.purchase_line_id} not found in purchase {r.purchase_id}.",
                    )
                purchase_line = found

        from collections import defaultdict
        qty_by_pline: dict[str, Decimal] = defaultdict(Decimal)
        for line in lines:
            qty_by_pline[line.purchase_line_id] += line.quantity

        for pline_id, qty_in_this_receiving in qty_by_pline.items():
            purchase_line = None
            for lid, lval in purchase_repository._lines.items():
                if lval.id == pline_id:
                    purchase_line = lval
                    break
            if not purchase_line:
                continue

            total_for_line = Decimal("0")
            for rl in self.receiving_repo._lines.values():
                if rl.purchase_line_id != pline_id:
                    continue
                rr = self.receiving_repo._receivings.get(rl.receiving_id)
                if not rr or rr.is_deleted:
                    continue
                if rr.status == ReceivingStatus.CANCELLED:
                    continue
                total_for_line += rl.quantity

            if total_for_line > purchase_line.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Over-receiving at finalization: purchase_line={pline_id} ordered={purchase_line.quantity}, total_received={total_for_line}.",
                )

        now = datetime.now(timezone.utc)
        updated = await self.receiving_repo.update_receiving(
            receiving_id=receiving_id,
            business_id=business_id,
            status=ReceivingStatus.FINALIZED,
            finalized_by_user_id=user_id,
            finalized_at=now,
        )

        line_resp = [ReceivingLineResponse.model_validate(l) for l in lines]
        return ReceivingResponse(**updated.model_dump(), lines=line_resp)

    async def cancel_receiving(
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

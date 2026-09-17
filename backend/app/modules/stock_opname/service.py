from typing import List, Optional
from decimal import Decimal
from datetime import datetime, timezone
import uuid
from fastapi import HTTPException, status

from app.modules.stock_opname.schemas import (
    StockOpnameInDB,
    StockOpnameLineInDB,
    StockOpnameResponse,
    StockOpnameLineResponse,
    StockOpnameCreate,
    StockOpnameLineCreate,
    StockOpnameLineUpdateCount,
    StockOpnameStatus,
)
from app.modules.stock_opname.repository import (
    AbstractStockOpnameRepository,
    stock_opname_repository,
)
from app.modules.inventory.service import (
    InventoryService,
    inventory_service,
)
from app.modules.inventory.schemas import (
    AdjustmentInput,
    ReferenceType,
)
from app.modules.business_membership.schemas import BusinessMembershipRole


class StockOpnameService:
    def __init__(
        self,
        opname_repo: AbstractStockOpnameRepository = stock_opname_repository,
        inv_service: InventoryService = inventory_service,
    ):
        self.opname_repo = opname_repo
        self.inv_service = inv_service

    async def create_opname(
        self, business_id: str, user_id: str, payload: StockOpnameCreate
    ) -> StockOpnameResponse:
        await self.inv_service._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        await self.inv_service._validate_location(business_id, payload.inventory_location_id)

        opname = await self.opname_repo.create_opname(
            business_id=business_id,
            inventory_location_id=payload.inventory_location_id,
            created_by_user_id=user_id,
            notes=payload.notes,
        )

        return StockOpnameResponse(**opname.model_dump(), lines=[])

    async def add_line(
        self, business_id: str, opname_id: str, user_id: str, payload: StockOpnameLineCreate
    ) -> StockOpnameLineResponse:
        await self.inv_service._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        opname = await self.opname_repo.get_opname_by_id(opname_id, business_id)
        if not opname:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stock opname not found.",
            )

        if opname.status != StockOpnameStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify a finalized stock opname.",
            )

        await self.inv_service._validate_product_and_variant(
            business_id, payload.product_id, payload.variant_id
        )

        # Duplicate line check
        existing_lines = await self.opname_repo.list_lines_for_opname(opname_id)
        for el in existing_lines:
            if el.product_id == payload.product_id and el.variant_id == payload.variant_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Duplicate product/variant line in opname.",
                )

        # System quantity snapshot from current StockBalance
        current_balance = await self.inv_service.balance_repo.get_balance(
            business_id, opname.inventory_location_id, payload.product_id, payload.variant_id
        )
        system_quantity = current_balance.quantity if current_balance else Decimal("0")

        line = await self.opname_repo.create_line(
            opname_id=opname_id,
            inventory_location_id=opname.inventory_location_id,
            product_id=payload.product_id,
            variant_id=payload.variant_id,
            system_quantity=system_quantity,
        )

        return StockOpnameLineResponse(**line.model_dump())

    async def update_line_count(
        self,
        business_id: str,
        opname_id: str,
        line_id: str,
        user_id: str,
        payload: StockOpnameLineUpdateCount,
    ) -> StockOpnameLineResponse:
        await self.inv_service._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        opname = await self.opname_repo.get_opname_by_id(opname_id, business_id)
        if not opname:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stock opname not found.",
            )

        if opname.status != StockOpnameStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify a finalized stock opname.",
            )

        line = await self.opname_repo.get_line_by_id(line_id, opname_id)
        if not line:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Opname line not found.",
            )

        # Server-side variance calculation
        variance = payload.counted_quantity - line.system_quantity

        updated_line = await self.opname_repo.update_line_count(
            line_id=line_id,
            opname_id=opname_id,
            counted_quantity=payload.counted_quantity,
            variance=variance,
        )
        return StockOpnameLineResponse(**updated_line.model_dump())

    async def delete_line(
        self, business_id: str, opname_id: str, line_id: str, user_id: str
    ) -> dict:
        await self.inv_service._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        opname = await self.opname_repo.get_opname_by_id(opname_id, business_id)
        if not opname:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stock opname not found.",
            )

        if opname.status != StockOpnameStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify a finalized stock opname.",
            )

        deleted = await self.opname_repo.delete_line(line_id, opname_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Opname line not found.",
            )
        return {"message": "Opname line deleted successfully."}

    async def delete_opname(self, business_id: str, opname_id: str, user_id: str) -> dict:
        await self.inv_service._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        opname = await self.opname_repo.get_opname_by_id(opname_id, business_id)
        if not opname:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stock opname not found.",
            )

        if opname.status != StockOpnameStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Finalized stock opname cannot be deleted.",
            )

        await self.opname_repo.delete_opname(opname_id, business_id)
        return {"message": "Stock opname deleted successfully."}

    async def finalize_opname(
        self, business_id: str, opname_id: str, user_id: str
    ) -> StockOpnameResponse:
        await self.inv_service._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        opname = await self.opname_repo.get_opname_by_id(opname_id, business_id)
        if not opname:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stock opname not found.",
            )

        if opname.status == StockOpnameStatus.FINALIZED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stock opname is already finalized.",
            )

        # Validate location is still active
        await self.inv_service._validate_location(business_id, opname.inventory_location_id)

        lines = await self.opname_repo.list_lines_for_opname(opname_id)
        if not lines:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot finalize stock opname without lines.",
            )

        # Ensure all lines have physical count entered
        for line in lines:
            if line.counted_quantity is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="All opname lines must have physical count entered before finalization.",
                )

        # STALE STOCK CHECK:
        # Verify that current StockBalance for each line equals line.system_quantity
        for line in lines:
            current_balance = await self.inv_service.balance_repo.get_balance(
                business_id, opname.inventory_location_id, line.product_id, line.variant_id
            )
            cur_qty = current_balance.quantity if current_balance else Decimal("0")
            if cur_qty != line.system_quantity:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Stok berubah sejak opname dibuat. Opname tidak dapat difinalisasi. Silakan periksa kembali stok atau buat opname baru.",
                )

        # Finalization Movements - Logical Atomicity Implementation:
        # Snapshot balances before movement generation so we can rollback if anything fails
        balance_snapshot = {
            k: v.model_copy()
            for k, v in self.inv_service.balance_repo._balances.items()
        }
        movement_snapshot = {
            k: v.model_copy()
            for k, v in self.inv_service.movement_repo._movements.items()
        }
        lines_snapshot = [l.model_copy() for l in self.inv_service.movement_repo._lines]

        try:
            # ── RESERVATION CONFLICT CHECK for negative adjustments ──
            from app.modules.sales_order.availability import availability_service, _inventory_lock
            _inventory_lock.acquire()
            try:
                for line in lines:
                    if line.variance is not None and line.variance < Decimal("0"):
                        physical_qty = await self.inv_service.get_physical_quantity(business_id, line.product_id, line.variant_id)
                        reserved_qty = await availability_service.get_all_reservations_for_product(business_id, line.product_id, line.variant_id)
                        new_physical = physical_qty + line.variance  # variance is negative
                        if new_physical < reserved_qty:
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Reservation conflict for product {line.product_id}: opname would reduce physical stock ({new_physical}) below active reservations ({reserved_qty}). Resolve reservation conflicts first.",
                            )
            finally:
                _inventory_lock.release()

            for line in lines:
                if line.variance is None or line.variance == Decimal("0"):
                    pass
                elif line.variance > Decimal("0"):
                    await self.inv_service.adjust_in(
                        business_id=business_id,
                        user_id=user_id,
                        payload=AdjustmentInput(
                            inventory_location_id=opname.inventory_location_id,
                            product_id=line.product_id,
                            variant_id=line.variant_id,
                            quantity=line.variance,
                            notes=f"Stock Opname adjustment: {opname.id}",
                        ),
                        reference_type=ReferenceType.STOCK_OPNAME,
                        reference_id=opname.id,
                    )
                elif line.variance < Decimal("0"):
                    await self.inv_service.adjust_out(
                        business_id=business_id,
                        user_id=user_id,
                        payload=AdjustmentInput(
                            inventory_location_id=opname.inventory_location_id,
                            product_id=line.product_id,
                            variant_id=line.variant_id,
                            quantity=abs(line.variance),
                            notes=f"Stock Opname adjustment: {opname.id}",
                        ),
                        reference_type=ReferenceType.STOCK_OPNAME,
                        reference_id=opname.id,
                    )

                # Synchronize InventoryCostState using live MAC without GL adjustment journal
                new_phys_qty = await self.inv_service.get_physical_quantity(business_id, line.product_id, line.variant_id)
                await self.inv_service.sync_opname_cost_state(
                    business_id=business_id,
                    product_id=line.product_id,
                    variant_id=line.variant_id,
                    new_physical_qty=new_phys_qty,
                    reference_id=opname.id,
                )
        except Exception as exc:
            # Revert in-memory repos to pre-finalization state on failure (atomic rollback)
            self.inv_service.balance_repo._balances = balance_snapshot
            self.inv_service.movement_repo._movements = movement_snapshot
            self.inv_service.movement_repo._lines = lines_snapshot
            raise exc

        now = datetime.now(timezone.utc)
        updated_opname = await self.opname_repo.update_opname_status(
            opname_id=opname_id,
            business_id=business_id,
            status=StockOpnameStatus.FINALIZED,
            finalized_by_user_id=user_id,
            finalized_at=now,
        )

        return StockOpnameResponse(
            **updated_opname.model_dump(),
            lines=[StockOpnameLineResponse(**l.model_dump()) for l in lines],
        )

    async def list_opnames(
        self,
        business_id: str,
        user_id: str,
        status_filter: Optional[StockOpnameStatus] = None,
        inventory_location_id: Optional[str] = None,
    ) -> List[StockOpnameResponse]:
        await self.inv_service._validate_access(business_id, user_id)
        opnames = await self.opname_repo.list_opnames(
            business_id=business_id,
            status=status_filter,
            inventory_location_id=inventory_location_id,
        )

        results = []
        for op in opnames:
            lines = await self.opname_repo.list_lines_for_opname(op.id)
            results.append(
                StockOpnameResponse(
                    **op.model_dump(),
                    lines=[StockOpnameLineResponse(**l.model_dump()) for l in lines],
                )
            )
        return results

    async def get_opname(
        self, business_id: str, opname_id: str, user_id: str
    ) -> StockOpnameResponse:
        await self.inv_service._validate_access(business_id, user_id)
        opname = await self.opname_repo.get_opname_by_id(opname_id, business_id)
        if not opname:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stock opname not found.",
            )

        lines = await self.opname_repo.list_lines_for_opname(opname.id)
        return StockOpnameResponse(
            **opname.model_dump(),
            lines=[StockOpnameLineResponse(**l.model_dump()) for l in lines],
        )


stock_opname_service = StockOpnameService()

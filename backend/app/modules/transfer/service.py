from typing import Any, Dict, List, Optional
from decimal import Decimal
from datetime import datetime, timezone
from fastapi import HTTPException, status

from app.modules.transfer.schemas import (
    TransferInDB,
    TransferLineInDB,
    TransferResponse,
    TransferLineResponse,
    TransferListResponse,
    TransferCreate,
    TransferLineCreate,
    TransferStatus,
)
from app.modules.transfer.repository import (
    AbstractTransferRepository,
    transfer_repository,
)
from app.modules.business_membership.service import (
    BusinessMembershipService,
    business_membership_service,
)
from app.modules.business_membership.schemas import BusinessMembershipRole
from app.modules.product.repository import product_repository
from app.modules.product.schemas import ProductType
from app.modules.inventory.service import inventory_service
from app.modules.inventory.schemas import (
    InventoryCostMovementType,
    MovementType,
    MovementDirection,
    ReferenceType,
)
from app.modules.inventory.repository import (
    stock_balance_repository,
    stock_movement_repository,
    inventory_cost_repository,
)
from app.modules.warehouse.repository import inventory_location_repository, warehouse_repository
from app.modules.warehouse.schemas import InventoryLocationStatus, WarehouseStatus
from app.modules.sales_order.availability import _inventory_lock


class TransferService:
    def __init__(
        self,
        transfer_repo: AbstractTransferRepository = transfer_repository,
        membership_service: BusinessMembershipService = business_membership_service,
    ):
        self.transfer_repo = transfer_repo
        self.membership_service = membership_service

    # ----------------------------------------------------------------
    # ATOMICITY — Snapshot / Restore (Feature #60)
    # ----------------------------------------------------------------

    def _snapshot_all_repos(self) -> Dict[str, Any]:
        return {
            "tr_transfers": {k: v.model_copy() for k, v in self.transfer_repo._transfers.items()},
            "tr_lines": {k: v.model_copy() for k, v in self.transfer_repo._lines.items()},
            "tr_sequences": dict(self.transfer_repo._sequences),
            "balances": {k: v.model_copy() for k, v in stock_balance_repository._balances.items()},
            "movements": {k: v.model_copy() for k, v in stock_movement_repository._movements.items()},
            "movement_lines": [l.model_copy() for l in stock_movement_repository._lines],
            "cost_states": {k: v.model_copy() for k, v in inventory_cost_repository._cost_states.items()},
            "cost_movements": [l.model_copy() for l in inventory_cost_repository._cost_movements],
        }

    def _restore_all_repos(self, snap: Dict[str, Any]) -> None:
        self.transfer_repo._transfers = snap["tr_transfers"]
        self.transfer_repo._lines = snap["tr_lines"]
        self.transfer_repo._sequences = snap["tr_sequences"]
        stock_balance_repository._balances = snap["balances"]
        stock_movement_repository._movements = snap["movements"]
        stock_movement_repository._lines = snap["movement_lines"]
        inventory_cost_repository._cost_states = snap["cost_states"]
        inventory_cost_repository._cost_movements = snap["cost_movements"]

    # ----------------------------------------------------------------

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

    async def _validate_location(self, business_id: str, location_id: str) -> None:
        loc = await inventory_location_repository.get_by_id(location_id)
        if not loc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inventory location not found.",
            )
        if loc.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inventory location not found in this business.",
            )
        wh = await warehouse_repository.get_by_id(loc.warehouse_id)
        if not wh or wh.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Warehouse for this inventory location is invalid.",
            )
        if wh.status != WarehouseStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Warehouse for this inventory location is not ACTIVE.",
            )
        if loc.status != InventoryLocationStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Inventory location is not ACTIVE (current: {loc.status}).",
            )

    async def _validate_product(self, business_id: str, product_id: str, variant_id: Optional[str]) -> None:
        product = await product_repository.get_by_id(product_id, business_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product not found in this business.",
            )
        if product.product_type != ProductType.GOODS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only GOODS products can be transferred. SERVICE products are not transferable.",
            )
        if variant_id:
            from app.modules.product_variant.repository import product_variant_repository
            variant = await product_variant_repository.get_by_id(variant_id, business_id)
            if not variant:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Product variant not found in this business.",
                )

    async def _get_authoritative_mac(
        self, business_id: str, product_id: str, variant_id: Optional[str]
    ) -> Decimal:
        mac = await inventory_service.get_current_mac(business_id, product_id, variant_id)
        return mac

    # ----------------------------------------------------------------
    # CRUD Operations
    # ----------------------------------------------------------------

    async def create_transfer(
        self, business_id: str, user_id: str, payload: TransferCreate
    ) -> TransferResponse:
        await self._validate_access(
            business_id, user_id,
            required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN),
        )

        source_id = payload.source_location_id.strip()
        dest_id = payload.destination_location_id.strip()

        if source_id == dest_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source and destination locations must be different.",
            )

        await self._validate_location(business_id, source_id)
        await self._validate_location(business_id, dest_id)

        seq = await self.transfer_repo.get_next_transfer_sequence(business_id)
        transfer_number = f"TRF-{seq:06d}"

        transfer = await self.transfer_repo.create_transfer(
            business_id=business_id,
            transfer_number=transfer_number,
            source_location_id=source_id,
            destination_location_id=dest_id,
            created_by_user_id=user_id,
            notes=payload.notes,
        )

        lines = await self.transfer_repo.list_lines_for_transfer(transfer.id)
        line_resp = [TransferLineResponse.model_validate(l) for l in lines]
        return TransferResponse(**transfer.model_dump(), lines=line_resp)

    async def list_transfers(
        self,
        business_id: str,
        user_id: str,
        status_filter: Optional[TransferStatus] = None,
        source_location_id: Optional[str] = None,
        destination_location_id: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> TransferListResponse:
        await self._validate_access(business_id, user_id)

        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        transfers, total = await self.transfer_repo.list_transfers(
            business_id=business_id,
            status=status_filter,
            source_location_id=source_location_id,
            destination_location_id=destination_location_id,
            search=search,
            page=page,
            page_size=page_size,
        )

        items = []
        for t in transfers:
            lines = await self.transfer_repo.list_lines_for_transfer(t.id)
            line_resp = [TransferLineResponse.model_validate(l) for l in lines]
            items.append(TransferResponse(**t.model_dump(), lines=line_resp))

        return TransferListResponse(items=items, page=page, page_size=page_size, total=total)

    async def get_transfer(
        self, business_id: str, transfer_id: str, user_id: str
    ) -> TransferResponse:
        await self._validate_access(business_id, user_id)
        t = await self.transfer_repo.get_transfer_by_id(transfer_id, business_id)
        if not t:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transfer order not found.",
            )
        lines = await self.transfer_repo.list_lines_for_transfer(t.id)
        line_resp = [TransferLineResponse.model_validate(l) for l in lines]
        return TransferResponse(**t.model_dump(), lines=line_resp)

    # ----------------------------------------------------------------
    # Line Management
    # ----------------------------------------------------------------

    async def add_line(
        self,
        business_id: str,
        transfer_id: str,
        user_id: str,
        payload: TransferLineCreate,
    ) -> TransferLineResponse:
        await self._validate_access(
            business_id, user_id,
            required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN),
        )

        t = await self.transfer_repo.get_transfer_by_id(transfer_id, business_id)
        if not t:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transfer order not found.",
            )
        if t.status != TransferStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify lines of a non-draft transfer order.",
            )

        await self._validate_product(business_id, payload.product_id, payload.variant_id)

        existing_lines = await self.transfer_repo.list_lines_for_transfer(transfer_id)
        for el in existing_lines:
            if el.product_id == payload.product_id and el.variant_id == payload.variant_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This product/variant is already included in this transfer order.",
                )

        line = await self.transfer_repo.create_line(
            transfer_id=transfer_id,
            product_id=payload.product_id,
            variant_id=payload.variant_id,
            quantity=payload.quantity,
        )

        return TransferLineResponse.model_validate(line)

    async def update_line(
        self,
        business_id: str,
        transfer_id: str,
        line_id: str,
        user_id: str,
        quantity: Decimal,
    ) -> TransferLineResponse:
        await self._validate_access(
            business_id, user_id,
            required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN),
        )

        t = await self.transfer_repo.get_transfer_by_id(transfer_id, business_id)
        if not t:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transfer order not found.",
            )
        if t.status != TransferStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify lines of a non-draft transfer order.",
            )

        line = await self.transfer_repo.get_line_by_id(line_id, transfer_id)
        if not line:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transfer line not found.",
            )

        if quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quantity must be greater than zero.",
            )

        line.quantity = quantity
        line.updated_at = datetime.now(timezone.utc)
        return TransferLineResponse.model_validate(line)

    async def delete_line(
        self, business_id: str, transfer_id: str, line_id: str, user_id: str
    ) -> dict:
        await self._validate_access(
            business_id, user_id,
            required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN),
        )

        t = await self.transfer_repo.get_transfer_by_id(transfer_id, business_id)
        if not t:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transfer order not found.",
            )
        if t.status != TransferStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify lines of a non-draft transfer order.",
            )

        line = await self.transfer_repo.get_line_by_id(line_id, transfer_id)
        if not line:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transfer line not found.",
            )

        del self.transfer_repo._lines[line_id]
        return {"message": "Transfer line successfully deleted."}

    # ----------------------------------------------------------------
    # Lifecycle Operations
    # ----------------------------------------------------------------

    async def dispatch_transfer(
        self, business_id: str, transfer_id: str, user_id: str
    ) -> TransferResponse:
        await self._validate_access(
            business_id, user_id,
            required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN),
        )

        _inventory_lock.acquire()
        try:
            t = await self.transfer_repo.get_transfer_by_id(transfer_id, business_id)
            if not t:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Transfer order not found.",
                )
            if t.status != TransferStatus.DRAFT:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Transfer order is not in DRAFT status.",
                )

            lines = await self.transfer_repo.list_lines_for_transfer(transfer_id)
            if not lines:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot dispatch a transfer order without any lines.",
                )

            # Validate stock availability for all lines before any mutation
            for line in lines:
                bal = await stock_balance_repository.get_balance(
                    business_id, t.source_location_id, line.product_id, line.variant_id
                )
                if not bal or bal.quantity < line.quantity:
                    available = bal.quantity if bal else Decimal("0")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Insufficient stock at source for product {line.product_id}. Available: {available}, requested: {line.quantity}.",
                    )

            # Snapshot before any mutation
            snapshots = self._snapshot_all_repos()

            try:
                now = datetime.now(timezone.utc)
                total_outbound_value = Decimal("0")

                # Process each line: capture MAC, deduct source stock, record movements
                for line in lines:
                    # Authoritative MAC at dispatch time
                    mac = await self._get_authoritative_mac(
                        business_id, line.product_id, line.variant_id
                    )

                    # Store immutable cost snapshot on the line
                    await self.transfer_repo.update_line_cost_snapshot(
                        line_id=line.id,
                        transfer_id=transfer_id,
                        unit_cost_snapshot=mac,
                    )

                    # Source stock deduction
                    await stock_balance_repository.upsert_balance(
                        business_id=business_id,
                        inventory_location_id=t.source_location_id,
                        product_id=line.product_id,
                        variant_id=line.variant_id,
                        delta=-line.quantity,
                    )

                    # Source MAC outbound
                    await inventory_service.record_cost_outbound(
                        business_id=business_id,
                        product_id=line.product_id,
                        variant_id=line.variant_id,
                        outbound_qty=line.quantity,
                        unit_cost=mac,
                        movement_type=InventoryCostMovementType.TRANSFER_OUT,
                        reference_type="TRANSFER_ORDER",
                        reference_id=transfer_id,
                    )

                    total_outbound_value += line.quantity * mac

                # Create stock movement record for audit
                movement = await stock_movement_repository.create_movement(
                    business_id=business_id,
                    movement_type=MovementType.TRANSFER_OUT,
                    performed_by_user_id=user_id,
                    reference_type=ReferenceType.TRANSFER,
                    reference_id=transfer_id,
                    notes=f"Transfer dispatch: {t.transfer_number}",
                )
                for line in lines:
                    await stock_movement_repository.create_line(
                        movement_id=movement.id,
                        inventory_location_id=t.source_location_id,
                        product_id=line.product_id,
                        variant_id=line.variant_id,
                        quantity=line.quantity,
                        direction=MovementDirection.OUT,
                    )

                # Update transfer status
                updated = await self.transfer_repo.update_transfer(
                    transfer_id=transfer_id,
                    business_id=business_id,
                    status=TransferStatus.DISPATCHED,
                    dispatched_by_user_id=user_id,
                    dispatched_at=now,
                )
            except Exception:
                self._restore_all_repos(snapshots)
                raise

        finally:
            _inventory_lock.release()

        lines = await self.transfer_repo.list_lines_for_transfer(transfer_id)
        line_resp = [TransferLineResponse.model_validate(l) for l in lines]
        return TransferResponse(**updated.model_dump(), lines=line_resp)

    async def receive_transfer(
        self, business_id: str, transfer_id: str, user_id: str
    ) -> TransferResponse:
        await self._validate_access(
            business_id, user_id,
            required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN),
        )

        _inventory_lock.acquire()
        try:
            t = await self.transfer_repo.get_transfer_by_id(transfer_id, business_id)
            if not t:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Transfer order not found.",
                )
            if t.status != TransferStatus.DISPATCHED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Transfer order is not in DISPATCHED status.",
                )

            lines = await self.transfer_repo.list_lines_for_transfer(transfer_id)

            # Snapshot before any mutation
            snapshots = self._snapshot_all_repos()

            try:
                now = datetime.now(timezone.utc)

                for line in lines:
                    # Destination stock increase
                    await stock_balance_repository.upsert_balance(
                        business_id=business_id,
                        inventory_location_id=t.destination_location_id,
                        product_id=line.product_id,
                        variant_id=line.variant_id,
                        delta=+line.quantity,
                    )

                    # Destination MAC inbound using immutable dispatch cost snapshot
                    await inventory_service.record_cost_inbound(
                        business_id=business_id,
                        product_id=line.product_id,
                        variant_id=line.variant_id,
                        inbound_qty=line.quantity,
                        inbound_unit_cost=line.unit_cost_snapshot,
                        movement_type=InventoryCostMovementType.TRANSFER_IN,
                        reference_type="TRANSFER_ORDER",
                        reference_id=transfer_id,
                    )

                # Create stock movement record for audit
                movement = await stock_movement_repository.create_movement(
                    business_id=business_id,
                    movement_type=MovementType.TRANSFER_IN,
                    performed_by_user_id=user_id,
                    reference_type=ReferenceType.TRANSFER,
                    reference_id=transfer_id,
                    notes=f"Transfer receipt: {t.transfer_number}",
                )
                for line in lines:
                    await stock_movement_repository.create_line(
                        movement_id=movement.id,
                        inventory_location_id=t.destination_location_id,
                        product_id=line.product_id,
                        variant_id=line.variant_id,
                        quantity=line.quantity,
                        direction=MovementDirection.IN,
                    )

                # Update transfer status
                updated = await self.transfer_repo.update_transfer(
                    transfer_id=transfer_id,
                    business_id=business_id,
                    status=TransferStatus.RECEIVED,
                    received_by_user_id=user_id,
                    received_at=now,
                )
            except Exception:
                self._restore_all_repos(snapshots)
                raise

        finally:
            _inventory_lock.release()

        lines = await self.transfer_repo.list_lines_for_transfer(transfer_id)
        line_resp = [TransferLineResponse.model_validate(l) for l in lines]
        return TransferResponse(**updated.model_dump(), lines=line_resp)

    async def cancel_transfer(
        self, business_id: str, transfer_id: str, user_id: str
    ) -> TransferResponse:
        await self._validate_access(
            business_id, user_id,
            required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN),
        )

        t = await self.transfer_repo.get_transfer_by_id(transfer_id, business_id)
        if not t:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transfer order not found.",
            )

        now = datetime.now(timezone.utc)

        if t.status == TransferStatus.DRAFT:
            # Cancel from DRAFT: zero inventory effect, just status change
            updated = await self.transfer_repo.update_transfer(
                transfer_id=transfer_id,
                business_id=business_id,
                status=TransferStatus.CANCELLED,
                cancelled_by_user_id=user_id,
                cancelled_at=now,
            )
            lines = await self.transfer_repo.list_lines_for_transfer(transfer_id)
            line_resp = [TransferLineResponse.model_validate(l) for l in lines]
            return TransferResponse(**updated.model_dump(), lines=line_resp)

        if t.status == TransferStatus.DISPATCHED:
            # Cancel from DISPATCHED: restore source stock and MAC
            _inventory_lock.acquire()
            try:
                lines = await self.transfer_repo.list_lines_for_transfer(transfer_id)

                # Snapshot before any mutation
                snapshots = self._snapshot_all_repos()

                try:
                    for line in lines:
                        # Source stock restoration
                        await stock_balance_repository.upsert_balance(
                            business_id=business_id,
                            inventory_location_id=t.source_location_id,
                            product_id=line.product_id,
                            variant_id=line.variant_id,
                            delta=+line.quantity,
                        )

                        # Source MAC restoration using the original dispatch cost snapshot
                        await inventory_service.record_cost_inbound(
                            business_id=business_id,
                            product_id=line.product_id,
                            variant_id=line.variant_id,
                            inbound_qty=line.quantity,
                            inbound_unit_cost=line.unit_cost_snapshot,
                            movement_type=InventoryCostMovementType.TRANSFER_IN,
                            reference_type="TRANSFER_ORDER_CANCEL",
                            reference_id=transfer_id,
                        )

                    # Create reversal stock movement for audit
                    movement = await stock_movement_repository.create_movement(
                        business_id=business_id,
                        movement_type=MovementType.TRANSFER_IN,
                        performed_by_user_id=user_id,
                        reference_type=ReferenceType.TRANSFER,
                        reference_id=transfer_id,
                        notes=f"Transfer cancellation restoration: {t.transfer_number}",
                    )
                    for line in lines:
                        await stock_movement_repository.create_line(
                            movement_id=movement.id,
                            inventory_location_id=t.source_location_id,
                            product_id=line.product_id,
                            variant_id=line.variant_id,
                            quantity=line.quantity,
                            direction=MovementDirection.IN,
                        )

                    # Update transfer status
                    updated = await self.transfer_repo.update_transfer(
                        transfer_id=transfer_id,
                        business_id=business_id,
                        status=TransferStatus.CANCELLED,
                        cancelled_by_user_id=user_id,
                        cancelled_at=now,
                    )
                except Exception:
                    self._restore_all_repos(snapshots)
                    raise

            finally:
                _inventory_lock.release()

            lines = await self.transfer_repo.list_lines_for_transfer(transfer_id)
            line_resp = [TransferLineResponse.model_validate(l) for l in lines]
            return TransferResponse(**updated.model_dump(), lines=line_resp)

        if t.status in (TransferStatus.RECEIVED, TransferStatus.CANCELLED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Transfer order is in {t.status.value} status and cannot be cancelled.",
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transfer order is in {t.status.value} status and cannot be cancelled.",
        )


transfer_service = TransferService()

import threading
from decimal import Decimal
from typing import Optional, Tuple

from fastapi import HTTPException, status

from app.modules.sales_order.repository import (
    reservation_repository,
    AbstractReservationRepository,
)
from app.modules.inventory.service import InventoryService, inventory_service
from app.modules.sales_order.schemas import ReservationStatus

_inventory_lock = threading.RLock()


class AvailabilityService:
    def __init__(
        self,
        reservation_repo: AbstractReservationRepository = reservation_repository,
        inventory_srv: InventoryService = inventory_service,
    ):
        self.reservation_repo = reservation_repo
        self.inventory_srv = inventory_srv

    async def get_physical_quantity(self, business_id: str, product_id: str, variant_id: Optional[str]) -> Decimal:
        return await self.inventory_srv.get_physical_quantity(business_id, product_id, variant_id)

    async def get_active_reserved_quantity(
        self, business_id: str, warehouse_id: str, product_id: str, variant_id: Optional[str]
    ) -> Decimal:
        active = await self.reservation_repo.list_active_by_warehouse_product(
            business_id, warehouse_id, product_id, variant_id
        )
        total = Decimal("0")
        for r in active:
            total += r.quantity
        return total

    async def get_available_to_sell(
        self, business_id: str, warehouse_id: str, product_id: str, variant_id: Optional[str]
    ) -> Decimal:
        physical = await self.get_physical_quantity(business_id, product_id, variant_id)
        reserved = await self.get_active_reserved_quantity(business_id, warehouse_id, product_id, variant_id)
        available = physical - reserved
        if available < Decimal("0"):
            available = Decimal("0")
        return available

    async def check_availability(
        self,
        business_id: str,
        warehouse_id: str,
        product_id: str,
        variant_id: Optional[str],
        requested_quantity: Decimal,
    ) -> Tuple[bool, Decimal, Decimal, Decimal]:
        physical = await self.get_physical_quantity(business_id, product_id, variant_id)
        reserved = await self.get_active_reserved_quantity(business_id, warehouse_id, product_id, variant_id)
        available = physical - reserved
        if available < Decimal("0"):
            available = Decimal("0")
        is_available = available >= requested_quantity
        return is_available, physical, reserved, available

    async def resolve_warehouse_from_location(self, inventory_location_id: str) -> Optional[str]:
        from app.modules.warehouse.repository import warehouse_repository
        locations = warehouse_repository._locations if hasattr(warehouse_repository, '_locations') else {}
        loc = locations.get(inventory_location_id)
        if loc:
            return loc.warehouse_id
        return None

    async def get_all_reservations_for_product(
        self, business_id: str, product_id: str, variant_id: Optional[str]
    ) -> Decimal:
        all_active = []
        for r in self.reservation_repo._reservations.values():
            if (r.business_id == business_id
                    and r.product_id == product_id
                    and r.variant_id == variant_id
                    and r.status == ReservationStatus.ACTIVE):
                all_active.append(r)
        total = Decimal("0")
        for r in all_active:
            total += r.quantity
        return total

    async def check_available_for_deduction(
        self,
        business_id: str,
        warehouse_id: str,
        product_id: str,
        variant_id: Optional[str],
        quantity: Decimal,
    ) -> None:
        is_available, physical, reserved, available = await self.check_availability(
            business_id, warehouse_id, product_id, variant_id, quantity
        )
        if not is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient available stock for {product_id}: requested {quantity}, available {available}.",
            )

    def acquire_lock(self):
        _inventory_lock.acquire()

    def release_lock(self):
        _inventory_lock.release()

    def lock(self):
        return _inventory_lock


availability_service = AvailabilityService()

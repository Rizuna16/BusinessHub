from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime, timezone
import threading
from uuid import uuid4
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.delivery_note.schemas import (
    DeliveryNoteInDB,
    DeliveryNoteLineInDB,
    DeliveryNoteResponse,
    DeliveryNoteLineResponse,
    DeliveryNoteListResponse,
    DeliveryNoteCreate,
    DeliveryNoteUpdate,
    DeliveryNoteStatus,
    DeliveryNoteLineCreate,
)
from app.modules.delivery_note.repository import (
    AbstractDeliveryNoteRepository,
    delivery_note_repository,
)
from app.modules.sales_order.repository import (
    AbstractSalesOrderRepository,
    sales_order_repository,
    AbstractReservationRepository,
    reservation_repository,
)
from app.modules.sales_order.schemas import (
    SalesOrderStatus,
    SalesOrderInDB,
    SalesOrderLineInDB,
    ReservationStatus,
)
from app.modules.sales_order.availability import _inventory_lock
from app.modules.business_membership.service import (
    BusinessMembershipService,
    business_membership_service,
)
from app.modules.business_membership.schemas import BusinessMembershipRole
from app.modules.customer.repository import customer_repository
from app.modules.branch.repository import branch_repository
from app.modules.product.repository import product_repository
from app.modules.product_variant.repository import product_variant_repository
from app.modules.customer.schemas import CustomerStatus
from app.modules.branch.schemas import BranchStatus
from app.modules.product.schemas import ProductType
from app.modules.inventory.service import InventoryService, inventory_service
from app.modules.inventory.schemas import InventoryCostMovementType
from app.modules.accounting.integration import accounting_integration_service
from app.modules.inventory.repository import (
    stock_balance_repository,
    stock_movement_repository,
    inventory_cost_repository,
)
from app.modules.inventory_batch.service import inventory_batch_service


DELIVERY_NOTE_NOT_FOUND = "DELIVERY_NOTE_NOT_FOUND"
DELIVERY_NOTE_INVALID_STATUS = "DELIVERY_NOTE_INVALID_STATUS"
DELIVERY_NOTE_LINE_NOT_FOUND = "DELIVERY_NOTE_LINE_NOT_FOUND"
DELIVERY_NOTE_INVALID_QUANTITY = "DELIVERY_NOTE_INVALID_QUANTITY"
DELIVERY_NOTE_QUANTITY_EXCEEDS_REMAINING = "DELIVERY_NOTE_QUANTITY_EXCEEDS_REMAINING"
DELIVERY_NOTE_SALES_ORDER_INVALID = "DELIVERY_NOTE_SALES_ORDER_INVALID"
DELIVERY_NOTE_ALREADY_CANCELLED = "DELIVERY_NOTE_ALREADY_CANCELLED"
DELIVERY_NOTE_BUSINESS_MISMATCH = "DELIVERY_NOTE_BUSINESS_MISMATCH"

EDITABLE_STATES = {DeliveryNoteStatus.DRAFT}
TERMINAL_STATES = {DeliveryNoteStatus.DELIVERED, DeliveryNoteStatus.CANCELLED}


def _snapshot_repositories() -> Dict[str, Any]:
    return {
        "dn": {k: v.model_copy() for k, v in delivery_note_repository._delivery_notes.items()},
        "dn_lines": {k: v.model_copy() for k, v in delivery_note_repository._lines.items()},
        "so": {k: v.model_copy() for k, v in sales_order_repository._orders.items()},
        "so_lines": {k: v.model_copy() for k, v in sales_order_repository._lines.items()},
        "reservations": {k: v.model_copy() for k, v in reservation_repository._reservations.items()},
        "balances": {k: v.model_copy() for k, v in stock_balance_repository._balances.items()},
        "movements": {
            "movements": {k: v.model_copy() for k, v in stock_movement_repository._movements.items()},
            "lines": [l.model_copy() for l in stock_movement_repository._lines],
        },
        "cost_states": {k: v.model_copy() for k, v in inventory_cost_repository._cost_states.items()},
        "cost_movements": [l.model_copy() for l in inventory_cost_repository._cost_movements],
    }


def _restore_repositories(snapshots: Dict[str, Any]) -> None:
    delivery_note_repository._delivery_notes = snapshots["dn"]
    delivery_note_repository._lines = snapshots["dn_lines"]
    sales_order_repository._orders = snapshots["so"]
    sales_order_repository._lines = snapshots["so_lines"]
    reservation_repository._reservations = snapshots["reservations"]
    stock_balance_repository._balances = snapshots["balances"]
    stock_movement_repository._movements = snapshots["movements"]["movements"]
    stock_movement_repository._lines = snapshots["movements"]["lines"]
    inventory_cost_repository._cost_states = snapshots["cost_states"]
    inventory_cost_repository._cost_movements = snapshots["cost_movements"]


class DeliveryNoteService:
    def __init__(
        self,
        delivery_note_repo: AbstractDeliveryNoteRepository = delivery_note_repository,
        sales_order_repo: AbstractSalesOrderRepository = sales_order_repository,
        membership_service: BusinessMembershipService = business_membership_service,
        session: Optional[AsyncSession] = None,
    ):
        self.delivery_note_repo = delivery_note_repo
        self.sales_order_repo = sales_order_repo
        self.membership_service = membership_service
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

    async def _validate_customer(self, business_id: str, customer_id: Optional[str]):
        if customer_id is None:
            return None
        customer = await customer_repository.get_by_id(customer_id, business_id)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Customer not found in this business.",
            )
        if customer.status != CustomerStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Customer is not ACTIVE (current: {customer.status}).",
            )
        return customer

    async def _validate_branch(self, business_id: str, branch_id: str):
        branch = await branch_repository.get_by_id(branch_id)
        if not branch or branch.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Branch not found in this business.",
            )
        if branch.status != BranchStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Branch is not ACTIVE (current: {branch.status}).",
            )
        return branch

    async def _validate_sales_order(self, business_id: str, sales_order_id: str) -> SalesOrderInDB:
        so = await self.sales_order_repo.get_order_by_id(sales_order_id, business_id)
        if not so:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sales Order not found in this business.",
            )
        if so.status not in (SalesOrderStatus.CONFIRMED, SalesOrderStatus.PARTIALLY_FULFILLED, SalesOrderStatus.FULFILLED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sales Order must be CONFIRMED, PARTIALLY_FULFILLED, or FULFILLED to create Delivery Note. Current status: {so.status.value}.",
            )
        return so

    async def _validate_delivery_note(self, delivery_note_id: str, business_id: str) -> DeliveryNoteInDB:
        dn = await self.delivery_note_repo.get_by_id(delivery_note_id, business_id)
        if not dn:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Delivery Note not found.",
            )
        return dn

    async def _get_remaining_delivery_quantity(self, business_id: str, sales_order_line_id: str, sales_order_line: SalesOrderLineInDB) -> Decimal:
        active_documented = await self.delivery_note_repo.get_active_documented_quantity(business_id, sales_order_line_id)
        remaining = sales_order_line.quantity_ordered - sales_order_line.quantity_fulfilled - active_documented
        if remaining < Decimal("0"):
            remaining = Decimal("0")
        return remaining

    async def _build_response(self, business_id: str, dn: DeliveryNoteInDB) -> DeliveryNoteResponse:
        lines = await self.delivery_note_repo.list_lines_for_delivery_note(dn.id)
        return DeliveryNoteResponse(**dn.model_dump(), lines=lines)

    async def create_delivery_note(self, business_id: str, user_id: str, payload: DeliveryNoteCreate) -> DeliveryNoteResponse:
        if self.session is not None:
            async with self.session.begin():
                return await self._create_delivery_note_with_retry(business_id, user_id, payload)
        return await self._create_delivery_note_with_retry(business_id, user_id, payload)

    async def _create_delivery_note_with_retry(self, business_id: str, user_id: str, payload: DeliveryNoteCreate) -> DeliveryNoteResponse:
        for attempt in range(3):
            try:
                if self.session is not None:
                    async with self.session.begin_nested():
                        return await self._create_delivery_note_impl(business_id, user_id, payload)
                else:
                    return await self._create_delivery_note_impl(business_id, user_id, payload)
            except Exception as e:
                err_str = str(e).lower()
                if ("unique" in err_str and ("delivery_number" in err_str or "uq_delivery" in err_str)) and attempt < 2:
                    continue
                raise
        raise HTTPException(status_code=409, detail="Document number collision; please retry")

    async def _create_delivery_note_impl(self, business_id: str, user_id: str, payload: DeliveryNoteCreate) -> DeliveryNoteResponse:
        await self._validate_access(business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN))

        so = await self._validate_sales_order(business_id, payload.sales_order_id)
        await self._validate_branch(business_id, payload.branch_id)
        if payload.customer_id is not None:
            await self._validate_customer(business_id, payload.customer_id)

        _inventory_lock.acquire()
        try:
            lines_data = []
            for line_payload in payload.lines:
                so_line = await self.sales_order_repo.get_line_by_id(line_payload.sales_order_line_id, payload.sales_order_id)
                if not so_line:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Sales Order line {line_payload.sales_order_line_id} not found in order.",
                    )

                if line_payload.delivery_quantity <= Decimal("0"):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Delivery quantity must be positive.",
                    )

                remaining = await self._get_remaining_delivery_quantity(business_id, so_line.id, so_line)
                if line_payload.delivery_quantity > remaining:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Delivery quantity {line_payload.delivery_quantity} exceeds remaining deliverable quantity {remaining} for line {so_line.id}.",
                    )

                product = await product_repository.get_by_id(so_line.product_id, business_id)
                product_name = product.name if product else "Unknown Product"
                variant_snapshot = None
                if so_line.variant_id:
                    variant = await product_variant_repository.get_by_id(so_line.variant_id, business_id)
                    if variant:
                        variant_snapshot = f"{variant.sku}" if hasattr(variant, 'sku') else variant.id

                unit = None
                if product and hasattr(product, 'unit_id') and product.unit_id:
                    from app.modules.unit.repository import unit_repository
                    unit_obj = await unit_repository.get_by_id(product.unit_id, business_id)
                    if unit_obj:
                        unit = unit_obj.symbol if hasattr(unit_obj, 'symbol') else unit_obj.name

                lines_data.append({
                    "sales_order_line_id": so_line.id,
                    "product_id": so_line.product_id,
                    "variant_id": so_line.variant_id,
                    "product_name_snapshot": product_name,
                    "variant_snapshot": variant_snapshot,
                    "ordered_quantity_snapshot": so_line.quantity_ordered,
                    "fulfilled_quantity_snapshot": so_line.quantity_fulfilled,
                    "delivery_quantity": line_payload.delivery_quantity,
                    "unit": unit,
                    "notes": line_payload.notes,
                })

            seq = await self.delivery_note_repo.get_next_sequence(business_id)
            delivery_number = f"DN-{seq:06d}"

            dn = await self.delivery_note_repo.create_delivery_note(
                business_id=business_id,
                branch_id=payload.branch_id,
                delivery_number=delivery_number,
                sales_order_id=payload.sales_order_id,
                customer_id=payload.customer_id,
                delivery_date=payload.delivery_date,
                shipping_address=payload.shipping_address,
                recipient_name=payload.recipient_name,
                recipient_phone=payload.recipient_phone,
                notes=payload.notes,
                created_by_user_id=user_id,
            )

            for ld in lines_data:
                await self.delivery_note_repo.create_line(
                    delivery_note_id=dn.id,
                    sales_order_line_id=ld["sales_order_line_id"],
                    product_id=ld["product_id"],
                    variant_id=ld["variant_id"],
                    product_name_snapshot=ld["product_name_snapshot"],
                    variant_snapshot=ld["variant_snapshot"],
                    ordered_quantity_snapshot=ld["ordered_quantity_snapshot"],
                    fulfilled_quantity_snapshot=ld["fulfilled_quantity_snapshot"],
                    delivery_quantity=ld["delivery_quantity"],
                    unit=ld["unit"],
                    notes=ld["notes"],
                )

        finally:
            _inventory_lock.release()

        return await self._build_response(business_id, dn)

    async def list_delivery_notes(
        self,
        business_id: str,
        user_id: str,
        status: Optional[DeliveryNoteStatus] = None,
        sales_order_id: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> DeliveryNoteListResponse:
        await self._validate_access(business_id, user_id)
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20
        items, total = await self.delivery_note_repo.list_delivery_notes(
            business_id=business_id, status=status, sales_order_id=sales_order_id,
            search=search, page=page, page_size=page_size,
        )
        responses = [await self._build_response(business_id, dn) for dn in items]
        return DeliveryNoteListResponse(items=responses, page=page, page_size=page_size, total=total)

    async def get_delivery_note(self, business_id: str, delivery_note_id: str, user_id: str) -> DeliveryNoteResponse:
        await self._validate_access(business_id, user_id)
        dn = await self._validate_delivery_note(delivery_note_id, business_id)
        return await self._build_response(business_id, dn)

    async def update_delivery_note(self, business_id: str, delivery_note_id: str, user_id: str, payload: DeliveryNoteUpdate) -> DeliveryNoteResponse:
        await self._validate_access(business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN))
        dn = await self._validate_delivery_note(delivery_note_id, business_id)
        if dn.status not in EDITABLE_STATES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot modify a {dn.status.value} Delivery Note.",
            )
        updated = await self.delivery_note_repo.update_delivery_note(
            delivery_note_id=delivery_note_id, business_id=business_id,
            delivery_date=payload.delivery_date,
            shipping_address=payload.shipping_address,
            recipient_name=payload.recipient_name,
            recipient_phone=payload.recipient_phone,
            notes=payload.notes,
        )
        return await self._build_response(business_id, updated)

    async def add_line(self, business_id: str, delivery_note_id: str, user_id: str, payload: DeliveryNoteLineCreate) -> DeliveryNoteLineResponse:
        await self._validate_access(business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN))
        dn = await self._validate_delivery_note(delivery_note_id, business_id)
        if dn.status not in EDITABLE_STATES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot add lines to a {dn.status.value} Delivery Note.",
            )

        so_line = await self.sales_order_repo.get_line_by_id(payload.sales_order_line_id, dn.sales_order_id)
        if not so_line:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sales Order line {payload.sales_order_line_id} not found.",
            )

        if payload.delivery_quantity <= Decimal("0"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Delivery quantity must be positive.",
            )

        _inventory_lock.acquire()
        try:
            remaining = await self._get_remaining_delivery_quantity(business_id, so_line.id, so_line)
            if payload.delivery_quantity > remaining:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Delivery quantity {payload.delivery_quantity} exceeds remaining deliverable quantity {remaining}.",
                )

            product = await product_repository.get_by_id(so_line.product_id, business_id)
            product_name = product.name if product else "Unknown Product"
            variant_snapshot = None
            if so_line.variant_id:
                variant = await product_variant_repository.get_by_id(so_line.variant_id, business_id)
                if variant:
                    variant_snapshot = f"{variant.sku}" if hasattr(variant, 'sku') else variant.id

            unit = None
            if product and hasattr(product, 'unit_id') and product.unit_id:
                from app.modules.unit.repository import unit_repository
                unit_obj = await unit_repository.get_by_id(product.unit_id, business_id)
                if unit_obj:
                    unit = unit_obj.symbol if hasattr(unit_obj, 'symbol') else unit_obj.name

            line = await self.delivery_note_repo.create_line(
                delivery_note_id=delivery_note_id,
                sales_order_line_id=so_line.id,
                product_id=so_line.product_id,
                variant_id=so_line.variant_id,
                product_name_snapshot=product_name,
                variant_snapshot=variant_snapshot,
                ordered_quantity_snapshot=so_line.quantity_ordered,
                fulfilled_quantity_snapshot=so_line.quantity_fulfilled,
                delivery_quantity=payload.delivery_quantity,
                unit=unit,
                notes=payload.notes,
            )
        finally:
            _inventory_lock.release()

        return DeliveryNoteLineResponse(**line.model_dump())

    async def update_line(self, business_id: str, delivery_note_id: str, line_id: str, user_id: str, delivery_quantity: Decimal, notes: Optional[str] = None) -> DeliveryNoteLineResponse:
        await self._validate_access(business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN))
        dn = await self._validate_delivery_note(delivery_note_id, business_id)
        if dn.status not in EDITABLE_STATES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot modify lines of a {dn.status.value} Delivery Note.",
            )
        line = await self.delivery_note_repo.get_line_by_id(line_id, delivery_note_id)
        if not line:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Delivery Note line not found.",
            )

        so_line = await self.sales_order_repo.get_line_by_id(line.sales_order_line_id, dn.sales_order_id)
        if not so_line:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Associated Sales Order line not found.",
            )

        if delivery_quantity <= Decimal("0"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Delivery quantity must be positive.",
            )

        _inventory_lock.acquire()
        try:
            active_documented = await self.delivery_note_repo.get_active_documented_quantity(business_id, line.sales_order_line_id)
            current_line_qty = line.delivery_quantity
            remaining_without_this_line = so_line.quantity_ordered - so_line.quantity_fulfilled - (active_documented - current_line_qty)
            if remaining_without_this_line < Decimal("0"):
                remaining_without_this_line = Decimal("0")

            if delivery_quantity > remaining_without_this_line:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Delivery quantity {delivery_quantity} exceeds remaining deliverable quantity {remaining_without_this_line}.",
                )
        finally:
            _inventory_lock.release()

        update_kwargs = {"delivery_quantity": delivery_quantity}
        if notes is not None:
            update_kwargs["notes"] = notes

        updated_line = await self.delivery_note_repo.update_line(line_id, delivery_note_id, **update_kwargs)
        return DeliveryNoteLineResponse(**updated_line.model_dump())

    async def delete_line(self, business_id: str, delivery_note_id: str, line_id: str, user_id: str) -> dict:
        await self._validate_access(business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN))
        dn = await self._validate_delivery_note(delivery_note_id, business_id)
        if dn.status not in EDITABLE_STATES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete lines from a {dn.status.value} Delivery Note.",
            )
        success = await self.delivery_note_repo.delete_line(line_id, delivery_note_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Delivery Note line not found.",
            )
        return {"message": "Delivery Note line successfully deleted."}

    async def ready_delivery_note(self, business_id: str, delivery_note_id: str, user_id: str) -> DeliveryNoteResponse:
        await self._validate_access(business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN))
        dn = await self._validate_delivery_note(delivery_note_id, business_id)
        if dn.status != DeliveryNoteStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot mark a {dn.status.value} Delivery Note as READY.",
            )

        lines = await self.delivery_note_repo.list_lines_for_delivery_note(delivery_note_id)
        if not lines:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot mark Delivery Note as READY without lines.",
            )

        so = await self.sales_order_repo.get_order_by_id(dn.sales_order_id, business_id)
        if not so:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Associated Sales Order not found.",
            )

        _inventory_lock.acquire()
        try:
            for line in lines:
                so_line = await self.sales_order_repo.get_line_by_id(line.sales_order_line_id, dn.sales_order_id)
                if not so_line:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Sales Order line {line.sales_order_line_id} not found.",
                    )
                active_documented = await self.delivery_note_repo.get_active_documented_quantity(business_id, line.sales_order_line_id)
                if active_documented + so_line.quantity_fulfilled > so_line.quantity_ordered:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Line {line.id} total documented quantity {active_documented} plus fulfilled {so_line.quantity_fulfilled} exceeds ordered {so_line.quantity_ordered}.",
                    )
        finally:
            _inventory_lock.release()

        now = datetime.now(timezone.utc)
        updated = await self.delivery_note_repo.update_delivery_note(
            delivery_note_id=delivery_note_id, business_id=business_id,
            status=DeliveryNoteStatus.READY,
            ready_by_user_id=user_id, ready_at=now,
        )
        return await self._build_response(business_id, updated)

    async def deliver_delivery_note(self, business_id: str, delivery_note_id: str, user_id: str) -> DeliveryNoteResponse:
        if self.session is not None:
            async with self.session.begin():
                return await self._deliver_delivery_note_impl(business_id, delivery_note_id, user_id)
        else:
            return await self._deliver_delivery_note_impl(business_id, delivery_note_id, user_id)

    async def _deliver_delivery_note_impl(self, business_id: str, delivery_note_id: str, user_id: str) -> DeliveryNoteResponse:
        await self._validate_access(business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN))
        
        _inventory_lock.acquire()
        try:
            dn = await self._validate_delivery_note(delivery_note_id, business_id)
            if dn.status != DeliveryNoteStatus.READY:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot mark a {dn.status.value} Delivery Note as DELIVERED.",
                )

            so = await self.sales_order_repo.get_order_by_id(dn.sales_order_id, business_id)
            if not so:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Associated Sales Order not found.",
                )

            lines = await self.delivery_note_repo.list_lines_for_delivery_note(delivery_note_id)
            if not lines:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot mark Delivery Note as DELIVERED without lines.",
                )

            # Re-validate remaining deliverable quantity under lock
            for line in lines:
                so_line = await self.sales_order_repo.get_line_by_id(line.sales_order_line_id, dn.sales_order_id)
                if not so_line:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Sales Order line {line.sales_order_line_id} not found.",
                    )
                active_documented = await self.delivery_note_repo.get_active_documented_quantity(business_id, line.sales_order_line_id)
                if active_documented + so_line.quantity_fulfilled > so_line.quantity_ordered:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Delivery quantity {active_documented} plus fulfilled {so_line.quantity_fulfilled} exceeds ordered {so_line.quantity_ordered} for line {line.sales_order_line_id}.",
                    )

            # Capture complete state snapshots before mutation
            snapshots = _snapshot_repositories()

            try:
                # 1. Collect GOODS lines and calculate pre-outbound MACs
                goods_lines_for_deduction = []
                mac_by_line = {}
                for line in lines:
                    so_line = await self.sales_order_repo.get_line_by_id(line.sales_order_line_id, dn.sales_order_id)
                    product = await product_repository.get_by_id(so_line.product_id, business_id)
                    if product and product.product_type == ProductType.GOODS:
                        goods_lines_for_deduction.append({
                            "product_id": so_line.product_id,
                            "variant_id": so_line.variant_id,
                            "quantity": line.delivery_quantity,
                            "sales_line_id": so_line.id,
                        })
                        # Pre-outbound MAC calculation BEFORE stock deduction
                        mac = await inventory_service.get_current_mac(business_id, so_line.product_id, so_line.variant_id)
                        mac_by_line[line.id] = mac

                # 2. Process GOODS inventory deduction
                if goods_lines_for_deduction:
                    await inventory_service.deduct_sales_stock(
                        business_id=business_id,
                        user_id=user_id,
                        sales_id=delivery_note_id,
                        sales_number=dn.delivery_number,
                        explicit_location_id=None,
                        branch_id=dn.branch_id,
                        goods_lines=goods_lines_for_deduction,
                    )

                    # 3. Record MAC outbound cost movement
                    for line in lines:
                        if line.id in mac_by_line:
                            mac = mac_by_line[line.id]
                            await inventory_service.record_cost_outbound(
                                business_id=business_id,
                                product_id=line.product_id,
                                variant_id=line.variant_id,
                                outbound_qty=line.delivery_quantity,
                                unit_cost=mac,
                                movement_type=InventoryCostMovementType.SALE_OUT,
                                reference_type="DELIVERY_NOTE",
                                reference_id=delivery_note_id,
                            )

                    # 4. Batch allocation via FEFO for GOODS lines
                    if goods_lines_for_deduction:
                        resolved_location_id = await inventory_service._resolve_sale_location(
                            business_id, None, dn.branch_id,
                        )
                        for gl in goods_lines_for_deduction:
                            await inventory_batch_service.allocate_fefo_outbound(
                                business_id=business_id,
                                inventory_location_id=resolved_location_id,
                                product_id=gl["product_id"],
                                variant_id=gl.get("variant_id"),
                                total_quantity=gl["quantity"],
                                stock_movement_id=f"DN:{delivery_note_id}:{gl.get('sales_line_id', '')}",
                            )
                        for gl in goods_lines_for_deduction:
                            await inventory_batch_service.validate_batch_aggregate_invariant(
                                business_id, resolved_location_id, gl["product_id"], gl.get("variant_id"),
                            )

                    # 5. Update Sales Order Line Fulfillment & Reservations
                active_reservations = await reservation_repository.list_by_order_for_update(dn.sales_order_id)
                active_res_map = {r.sales_order_line_id: r for r in active_reservations if r.status == ReservationStatus.ACTIVE}

                for line in lines:
                    so_line = await self.sales_order_repo.get_line_by_id(line.sales_order_line_id, dn.sales_order_id)
                    new_fulfilled = so_line.quantity_fulfilled + line.delivery_quantity
                    new_remaining = so_line.quantity_ordered - new_fulfilled

                    await self.sales_order_repo.update_line(
                        line_id=so_line.id,
                        sales_order_id=dn.sales_order_id,
                        quantity_fulfilled=new_fulfilled,
                        quantity_remaining=new_remaining,
                    )

                    # Update Reservation for GOODS only (res will be None for SERVICE lines)
                    res = active_res_map.get(so_line.id)
                    if res:
                        new_res_qty = res.quantity - line.delivery_quantity
                        if new_res_qty <= Decimal("0"):
                            await reservation_repository.update_status(res.id, ReservationStatus.FULFILLED)
                        else:
                            await reservation_repository.update_quantity(res.id, new_res_qty)

                # 5. Update Sales Order header status
                all_so_lines = await self.sales_order_repo.list_lines_for_order(dn.sales_order_id)
                all_fully_fulfilled = all(l.quantity_remaining <= Decimal("0") for l in all_so_lines)

                new_so_status = SalesOrderStatus.FULFILLED if all_fully_fulfilled else SalesOrderStatus.PARTIALLY_FULFILLED
                now = datetime.now(timezone.utc)
                await self.sales_order_repo.update_order(
                    order_id=dn.sales_order_id,
                    business_id=business_id,
                    status=new_so_status,
                    fulfilled_by_user_id=user_id,
                    fulfilled_at=now,
                )

                # 6. Update Delivery Note header to DELIVERED
                updated_dn = await self.delivery_note_repo.update_delivery_note(
                    delivery_note_id=delivery_note_id,
                    business_id=business_id,
                    status=DeliveryNoteStatus.DELIVERED,
                    delivered_by_user_id=user_id,
                    delivered_at=now,
                )

            except Exception as exc:
                _restore_repositories(snapshots)
                raise exc

        finally:
            _inventory_lock.release()

        return await self._build_response(business_id, updated_dn)

    async def cancel_delivery_note(self, business_id: str, delivery_note_id: str, user_id: str) -> DeliveryNoteResponse:
        await self._validate_access(business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN))
        dn = await self._validate_delivery_note(delivery_note_id, business_id)
        if dn.status in TERMINAL_STATES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel a {dn.status.value} Delivery Note.",
            )
        if dn.status not in (DeliveryNoteStatus.DRAFT, DeliveryNoteStatus.READY):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel a {dn.status.value} Delivery Note.",
            )

        now = datetime.now(timezone.utc)
        updated = await self.delivery_note_repo.update_delivery_note(
            delivery_note_id=delivery_note_id, business_id=business_id,
            status=DeliveryNoteStatus.CANCELLED,
            cancelled_by_user_id=user_id, cancelled_at=now,
        )
        return await self._build_response(business_id, updated)


delivery_note_service = DeliveryNoteService()

from typing import List, Optional
from decimal import Decimal
from datetime import datetime, timezone
import uuid
from fastapi import HTTPException, status

from app.modules.sales_order.schemas import (
    SalesOrderInDB,
    SalesOrderLineInDB,
    SalesOrderResponse,
    SalesOrderLineResponse,
    SalesOrderListResponse,
    SalesOrderCreate,
    SalesOrderUpdate,
    SalesOrderAction,
    SalesOrderFulfill,
    SalesOrderFulfillResponse,
    SalesOrderStatus,
    ReservationStatus,
    SalesOrderLineFulfill,
    InventoryReservationConflict,
)
from app.modules.sales_order.repository import (
    AbstractSalesOrderRepository,
    sales_order_repository,
    AbstractReservationRepository,
    reservation_repository,
)
from app.modules.sales_order.availability import AvailabilityService, availability_service, _inventory_lock
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
from app.modules.product.schemas import ProductStatus, ProductType
from app.modules.product_variant.schemas import ProductVariantStatus
from app.modules.warehouse.repository import warehouse_repository
from app.modules.warehouse.schemas import WarehouseStatus
from app.modules.inventory.service import InventoryService, inventory_service
from app.modules.inventory.schemas import InventoryCostMovementType
from app.modules.accounting.integration import accounting_integration_service
from app.modules.accounting.tax_calculation import tax_calculation_service
from app.modules.accounting.schemas import TaxSnapshot, PricingMode, TaxTreatment
from app.modules.accounting.repository import accounting_repository


SALES_ORDER_INVALID_STATUS = "SALES_ORDER_INVALID_STATUS"
INSUFFICIENT_AVAILABLE_STOCK = "INSUFFICIENT_AVAILABLE_STOCK"
INVENTORY_RESERVATION_CONFLICT = "INVENTORY_RESERVATION_CONFLICT"
RESERVATION_NOT_FOUND = "RESERVATION_NOT_FOUND"
FULFILLMENT_INVALID = "FULFILLMENT_INVALID"


class SalesOrderService:
    def __init__(
        self,
        order_repo: AbstractSalesOrderRepository = sales_order_repository,
        reservation_repo: AbstractReservationRepository = reservation_repository,
        availability_svc: AvailabilityService = availability_service,
        membership_service: BusinessMembershipService = business_membership_service,
        inventory_srv: InventoryService = inventory_service,
    ):
        self.order_repo = order_repo
        self.reservation_repo = reservation_repo
        self.availability_svc = availability_svc
        self.membership_service = membership_service
        self.inventory_srv = inventory_srv

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
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Customer not found in this business.")
        if customer.status != CustomerStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Customer is not ACTIVE (current: {customer.status}).")
        return customer

    async def _validate_branch(self, business_id: str, branch_id: str):
        branch = await branch_repository.get_by_id(branch_id)
        if not branch or branch.business_id != business_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Branch not found in this business.")
        if branch.status != BranchStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Branch is not ACTIVE (current: {branch.status}).")
        return branch

    async def _validate_warehouse(self, business_id: str, warehouse_id: str):
        warehouse = await warehouse_repository.get_by_id(warehouse_id)
        if not warehouse or warehouse.business_id != business_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Warehouse not found in this business.")
        if warehouse.status != WarehouseStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Warehouse is not ACTIVE (current: {warehouse.status}).")
        return warehouse

    async def _validate_product_and_variant(
        self, business_id: str, product_id: Optional[str], variant_id: Optional[str]
    ) -> tuple[str, Optional[str]]:
        if variant_id:
            variant = await product_variant_repository.get_by_id(variant_id, business_id)
            if not variant or variant.business_id != business_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product variant not found in this business.")
            if variant.status != ProductVariantStatus.ACTIVE:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product variant is not ACTIVE.")
            parent_product = await product_repository.get_by_id(variant.product_id, business_id)
            if not parent_product or parent_product.business_id != business_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parent product not found in this business.")
            if parent_product.status != ProductStatus.ACTIVE:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parent product is not ACTIVE.")
            if parent_product.product_type != ProductType.GOODS:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Variants are only supported for GOODS product type.")
            if product_id and product_id != variant.product_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product variant does not belong to the specified product.")
            return variant.product_id, variant.id
        elif product_id:
            product = await product_repository.get_by_id(product_id, business_id)
            if not product:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product not found in this business.")
            if product.status != ProductStatus.ACTIVE:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product is not ACTIVE.")
            return product.id, None
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Line must specify product_id or variant_id.")

    def _is_terminal(self, s: SalesOrderStatus) -> bool:
        return s in (SalesOrderStatus.FULFILLED, SalesOrderStatus.CANCELLED)

    def _validate_transition(self, current: SalesOrderStatus, target: SalesOrderStatus) -> bool:
        transitions = {
            SalesOrderStatus.DRAFT: {SalesOrderStatus.CONFIRMED, SalesOrderStatus.CANCELLED},
            SalesOrderStatus.CONFIRMED: {SalesOrderStatus.PARTIALLY_FULFILLED, SalesOrderStatus.FULFILLED, SalesOrderStatus.CANCELLED},
            SalesOrderStatus.PARTIALLY_FULFILLED: {SalesOrderStatus.FULFILLED, SalesOrderStatus.CANCELLED},
        }
        return target in transitions.get(current, set())

    async def _recalculate_totals(self, business_id: str, order_id: str):
        lines = await self.order_repo.list_lines_for_order(order_id)
        subtotal = Decimal("0")
        discount_total = Decimal("0")
        tax_total = Decimal("0")
        for l in lines:
            subtotal += l.line_subtotal
            discount_total += l.discount_amount
            tax_total += l.tax_amount
        grand_total = subtotal - discount_total + tax_total
        await self.order_repo.update_order(
            order_id=order_id, business_id=business_id,
            subtotal=subtotal, discount_total=discount_total,
            tax_total=tax_total, grand_total=grand_total,
        )

    async def _build_response(self, business_id: str, o: SalesOrderInDB) -> SalesOrderResponse:
        lines = await self.order_repo.list_lines_for_order(o.id)
        return SalesOrderResponse(**o.model_dump(), lines=lines)

    async def create_order(self, business_id: str, user_id: str, payload: SalesOrderCreate) -> SalesOrderResponse:
        await self._validate_access(business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN))
        await self._validate_customer(business_id, payload.customer_id)
        await self._validate_branch(business_id, payload.branch_id)
        await self._validate_warehouse(business_id, payload.warehouse_id)

        seq = await self.order_repo.get_next_order_sequence(business_id)
        sales_order_number = f"SO-{seq:06d}"

        o = await self.order_repo.create_order(
            business_id=business_id,
            customer_id=payload.customer_id,
            branch_id=payload.branch_id,
            warehouse_id=payload.warehouse_id,
            sales_order_number=sales_order_number,
            order_date=payload.order_date,
            created_by_user_id=user_id,
            notes=payload.notes,
        )
        return await self._build_response(business_id, o)

    async def list_orders(
        self,
        business_id: str,
        user_id: str,
        status: Optional[SalesOrderStatus] = None,
        customer_id: Optional[str] = None,
        branch_id: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> SalesOrderListResponse:
        await self._validate_access(business_id, user_id)
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20
        items, total = await self.order_repo.list_orders(
            business_id=business_id, status=status, customer_id=customer_id,
            branch_id=branch_id, search=search, page=page, page_size=page_size,
        )
        responses = [await self._build_response(business_id, o) for o in items]
        return SalesOrderListResponse(items=responses, page=page, page_size=page_size, total=total)

    async def get_order(self, business_id: str, order_id: str, user_id: str) -> SalesOrderResponse:
        await self._validate_access(business_id, user_id)
        o = await self.order_repo.get_order_by_id(order_id, business_id)
        if not o:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales Order not found.")
        return await self._build_response(business_id, o)

    async def update_order(self, business_id: str, order_id: str, user_id: str, payload: SalesOrderUpdate) -> SalesOrderResponse:
        await self._validate_access(business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN))
        o = await self.order_repo.get_order_by_id(order_id, business_id)
        if not o:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales Order not found.")
        if self._is_terminal(o.status):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot modify a {o.status.value} sales order.")
        if payload.customer_id is not None:
            await self._validate_customer(business_id, payload.customer_id)
        if payload.branch_id is not None:
            await self._validate_branch(business_id, payload.branch_id)
        if payload.warehouse_id is not None:
            await self._validate_warehouse(business_id, payload.warehouse_id)
        updated = await self.order_repo.update_order(
            order_id=order_id, business_id=business_id,
            customer_id=payload.customer_id, branch_id=payload.branch_id,
            warehouse_id=payload.warehouse_id, order_date=payload.order_date,
            notes=payload.notes,
        )
        return await self._build_response(business_id, updated)

    async def add_line(self, business_id: str, order_id: str, user_id: str, payload) -> SalesOrderLineResponse:
        await self._validate_access(business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN))
        o = await self.order_repo.get_order_by_id(order_id, business_id)
        if not o:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales Order not found.")
        if o.status != SalesOrderStatus.DRAFT:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot add lines to non-DRAFT sales order.")
        from app.modules.sales_order.schemas import SalesOrderLineCreate
        if isinstance(payload, SalesOrderLineCreate):
            pass
        else:
            payload = SalesOrderLineCreate(**payload.model_dump() if hasattr(payload, 'model_dump') else payload)
        resolved_product_id, resolved_variant_id = await self._validate_product_and_variant(business_id, payload.product_id, payload.variant_id)
        line_subtotal = payload.quantity * payload.unit_price
        line_total = line_subtotal - payload.discount_amount + payload.tax_amount
        line = await self.order_repo.create_line(
            sales_order_id=order_id, product_id=resolved_product_id, variant_id=resolved_variant_id,
            description=payload.description, quantity_ordered=payload.quantity, unit_price=payload.unit_price,
            discount_amount=payload.discount_amount, tax_amount=payload.tax_amount,
            line_subtotal=line_subtotal, line_total=line_total,
        )
        await self._recalculate_totals(business_id, order_id)
        return SalesOrderLineResponse(**line.model_dump())

    async def update_line(self, business_id: str, order_id: str, line_id: str, user_id: str, payload) -> SalesOrderLineResponse:
        await self._validate_access(business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN))
        o = await self.order_repo.get_order_by_id(order_id, business_id)
        if not o:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales Order not found.")
        if o.status != SalesOrderStatus.DRAFT:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify lines of non-DRAFT sales order.")
        line = await self.order_repo.get_line_by_id(line_id, order_id)
        if not line:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales Order line not found.")
        target_product_id = payload.product_id if payload.product_id is not None else line.product_id
        target_variant_id = payload.variant_id if payload.variant_id is not None else line.variant_id
        if payload.product_id is not None or payload.variant_id is not None:
            resolved_product_id, resolved_variant_id = await self._validate_product_and_variant(business_id, target_product_id, target_variant_id)
        else:
            resolved_product_id, resolved_variant_id = target_product_id, target_variant_id
        target_qty = payload.quantity if payload.quantity is not None else line.quantity_ordered
        target_price = payload.unit_price if payload.unit_price is not None else line.unit_price
        target_disc = payload.discount_amount if payload.discount_amount is not None else line.discount_amount
        target_tax = payload.tax_amount if payload.tax_amount is not None else line.tax_amount
        line_subtotal = target_qty * target_price
        line_total = line_subtotal - target_disc + target_tax
        updated_line = await self.order_repo.update_line(
            line_id=line_id, sales_order_id=order_id,
            product_id=resolved_product_id, variant_id=resolved_variant_id,
            description=payload.description, quantity_ordered=payload.quantity,
            unit_price=payload.unit_price, discount_amount=payload.discount_amount,
            tax_amount=payload.tax_amount, line_subtotal=line_subtotal, line_total=line_total,
            quantity_remaining=payload.quantity,
        )
        await self._recalculate_totals(business_id, order_id)
        return SalesOrderLineResponse(**updated_line.model_dump())

    async def delete_line(self, business_id: str, order_id: str, line_id: str, user_id: str) -> dict:
        await self._validate_access(business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN))
        o = await self.order_repo.get_order_by_id(order_id, business_id)
        if not o:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales Order not found.")
        if o.status != SalesOrderStatus.DRAFT:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify lines of non-DRAFT sales order.")
        success = await self.order_repo.delete_line(line_id, order_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales Order line not found.")
        await self._recalculate_totals(business_id, order_id)
        return {"message": "Sales Order line successfully deleted."}

    async def confirm_order(self, business_id: str, order_id: str, user_id: str) -> SalesOrderResponse:
        await self._validate_access(business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN))
        o = await self.order_repo.get_order_by_id(order_id, business_id)
        if not o:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales Order not found.")
        if not self._validate_transition(o.status, SalesOrderStatus.CONFIRMED):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot confirm a {o.status.value} sales order.")
        lines = await self.order_repo.list_lines_for_order(order_id)
        if not lines:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot confirm sales order without lines.")
        for l in lines:
            resolved_product_id, resolved_variant_id = await self._validate_product_and_variant(business_id, l.product_id, l.variant_id)
        await self._recalculate_totals(business_id, order_id)

        _inventory_lock.acquire()
        try:
            conflicts: List[InventoryReservationConflict] = []
            for l in lines:
                product = await product_repository.get_by_id(l.product_id, business_id)
                if product and product.product_type != ProductType.GOODS:
                    continue
                is_available, physical, reserved, available = await self.availability_svc.check_availability(
                    business_id, o.warehouse_id, l.product_id, l.variant_id, l.quantity_ordered,
                )
                if not is_available:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Insufficient available stock for {l.product_id}: requested {l.quantity_ordered}, available {available}.",
                    )
            for l in lines:
                product = await product_repository.get_by_id(l.product_id, business_id)
                if product and product.product_type != ProductType.GOODS:
                    continue
                await self.reservation_repo.create_reservation(
                    business_id=business_id,
                    sales_order_id=o.id,
                    sales_order_line_id=l.id,
                    warehouse_id=o.warehouse_id,
                    product_id=l.product_id,
                    variant_id=l.variant_id,
                    quantity=l.quantity_ordered,
                )
            now = datetime.now(timezone.utc)
            updated = await self.order_repo.update_order(
                order_id=order_id, business_id=business_id,
                status=SalesOrderStatus.CONFIRMED,
                confirmed_by_user_id=user_id, confirmed_at=now,
            )
        finally:
            _inventory_lock.release()

        return await self._build_response(business_id, updated)

    async def cancel_order(self, business_id: str, order_id: str, user_id: str) -> SalesOrderResponse:
        await self._validate_access(business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN))
        o = await self.order_repo.get_order_by_id(order_id, business_id)
        if not o:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales Order not found.")
        if self._is_terminal(o.status):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot cancel a {o.status.value} sales order.")
        if not self._validate_transition(o.status, SalesOrderStatus.CANCELLED):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot cancel a {o.status.value} sales order.")

        active_reservations = await self.reservation_repo.list_by_order(order_id)
        for r in active_reservations:
            if r.status == ReservationStatus.ACTIVE:
                await self.reservation_repo.update_status(r.id, ReservationStatus.RELEASED)

        now = datetime.now(timezone.utc)
        updated = await self.order_repo.update_order(
            order_id=order_id, business_id=business_id,
            status=SalesOrderStatus.CANCELLED,
            cancelled_by_user_id=user_id, cancelled_at=now,
        )
        return await self._build_response(business_id, updated)

    async def fulfill_order(self, business_id: str, order_id: str, user_id: str, payload: SalesOrderFulfill) -> SalesOrderResponse:
        await self._validate_access(business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN))
        
        _inventory_lock.acquire()
        try:
            o = await self.order_repo.get_order_by_id(order_id, business_id)
            if not o:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales Order not found.")
            if o.status not in (SalesOrderStatus.CONFIRMED, SalesOrderStatus.PARTIALLY_FULFILLED):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot fulfill a {o.status.value} sales order.")

            lines = await self.order_repo.list_lines_for_order(order_id)
            active_reservations = await self.reservation_repo.list_by_order(order_id)
            active_res_map = {r.sales_order_line_id: r for r in active_reservations if r.status == ReservationStatus.ACTIVE}

            total_fulfilled = Decimal("0")
            all_fully_fulfilled = True
            for lf in payload.line_fulfillments:
                line = await self.order_repo.get_line_by_id(lf.line_id, order_id)
                if not line:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Line {lf.line_id} not found in order.")
                if lf.quantity <= Decimal("0"):
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fulfillment quantity must be positive.")
                remaining = line.quantity_ordered - line.quantity_fulfilled
                if lf.quantity > remaining:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot fulfill {lf.quantity} of line {lf.line_id}. Only {remaining} remaining.")

            now = datetime.now(timezone.utc)
            total_fulfilled = Decimal("0")
            all_fully_fulfilled = True

            for lf in payload.line_fulfillments:
                line = await self.order_repo.get_line_by_id(lf.line_id, order_id)
                new_fulfilled = line.quantity_fulfilled + lf.quantity
                new_remaining = line.quantity_ordered - new_fulfilled
                await self.order_repo.update_line(
                    line_id=lf.line_id, sales_order_id=order_id,
                    quantity_fulfilled=new_fulfilled,
                    quantity_remaining=new_remaining,
                )
                total_fulfilled += lf.quantity
                if new_remaining > Decimal("0"):
                    all_fully_fulfilled = False

                res = active_res_map.get(lf.line_id)
                if res:
                    new_res_qty = res.quantity - lf.quantity
                    if new_res_qty <= Decimal("0"):
                        await self.reservation_repo.update_status(res.id, ReservationStatus.FULFILLED)
                    else:
                        await self.reservation_repo.update_quantity(res.id, new_res_qty)

            if total_fulfilled > Decimal("0"):
                goods_lines_fulfill = []
                for lf in payload.line_fulfillments:
                    line = await self.order_repo.get_line_by_id(lf.line_id, order_id)
                    product = await product_repository.get_by_id(line.product_id, business_id)
                    if product and product.product_type == ProductType.GOODS:
                        goods_lines_fulfill.append({
                            "product_id": line.product_id,
                            "variant_id": line.variant_id,
                            "quantity": lf.quantity,
                            "sales_line_id": lf.line_id,
                        })
                if goods_lines_fulfill:
                    fulfillment_ref_id = str(uuid.uuid4())
                    await self.inventory_srv.deduct_sales_stock(
                        business_id=business_id,
                        user_id=user_id,
                        sales_id=fulfillment_ref_id,
                        sales_number=o.sales_order_number,
                        explicit_location_id=None,
                        branch_id=o.branch_id,
                        goods_lines=goods_lines_fulfill,
                    )
                    for g in goods_lines_fulfill:
                        mac = await self.inventory_srv.get_current_mac(business_id, g["product_id"], g["variant_id"])
                        await self.inventory_srv.record_cost_outbound(
                            business_id=business_id,
                            product_id=g["product_id"],
                            variant_id=g["variant_id"],
                            outbound_qty=g["quantity"],
                            unit_cost=mac,
                            movement_type=InventoryCostMovementType.SALE_OUT,
                            reference_type="SALES_ORDER",
                            reference_id=order_id,
                        )

            if all_fully_fulfilled:
                new_status = SalesOrderStatus.FULFILLED
            else:
                new_status = SalesOrderStatus.PARTIALLY_FULFILLED

            updated = await self.order_repo.update_order(
                order_id=order_id, business_id=business_id,
                status=new_status,
                fulfilled_by_user_id=user_id, fulfilled_at=now,
            )
        finally:
            _inventory_lock.release()

        return await self._build_response(business_id, updated)


sales_order_service = SalesOrderService()

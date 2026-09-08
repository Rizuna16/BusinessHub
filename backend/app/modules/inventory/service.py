from typing import List, Optional
from decimal import Decimal
import uuid
from fastapi import HTTPException, status

from app.modules.warehouse.schemas import (
    InventoryLocationStatus,
    WarehouseStatus,
    InventoryLocationType,
    WarehouseInDB,
)
from app.modules.inventory.schemas import (
    StockBalanceInDB,
    StockBalanceResponse,
    StockMovementInDB,
    StockMovementResponse,
    StockMovementLineResponse,
    StockMovementLineCreate,
    OpeningBalanceInput,
    AdjustmentInput,
    TransferInput,
    MovementType,
    MovementDirection,
    ReferenceType,
    TotalStockResponse,
    InventoryCostStateInDB,
    InventoryCostMovementInDB,
    InventoryCostMovementType,
    ValuationSummaryResponse,
    ValuationSummaryItem,
)
from app.modules.inventory.repository import (
    AbstractStockBalanceRepository,
    stock_balance_repository,
    AbstractStockMovementRepository,
    stock_movement_repository,
    AbstractInventoryCostRepository,
    inventory_cost_repository,
)
from app.modules.business_membership.service import (
    BusinessMembershipService,
    business_membership_service,
)
from app.modules.business_membership.schemas import (
    BusinessMembershipRole,
    BusinessMembershipInDB,
)
from app.modules.business.repository import (
    AbstractBusinessRepository,
    business_repository,
)
from app.modules.business.schemas import BusinessStatus
from app.modules.warehouse.repository import (
    AbstractWarehouseRepository,
    AbstractInventoryLocationRepository,
    inventory_location_repository,
    warehouse_repository,
)
from app.modules.product.repository import (
    AbstractProductRepository,
    product_repository,
)
from app.modules.product.schemas import ProductStatus, ProductType
from app.modules.product_variant.repository import (
    AbstractProductVariantRepository,
    product_variant_repository,
)
from app.modules.product_variant.schemas import ProductVariantStatus


class InventoryService:
    def __init__(
        self,
        balance_repo: AbstractStockBalanceRepository = stock_balance_repository,
        movement_repo: AbstractStockMovementRepository = stock_movement_repository,
        cost_repo: AbstractInventoryCostRepository = inventory_cost_repository,
        membership_service: BusinessMembershipService = business_membership_service,
        business_repo: AbstractBusinessRepository = business_repository,
        location_repo: AbstractInventoryLocationRepository = inventory_location_repository,
        warehouse_repo: AbstractWarehouseRepository = warehouse_repository,
        product_repo: AbstractProductRepository = product_repository,
        variant_repo: AbstractProductVariantRepository = product_variant_repository,
    ):
        self.balance_repo = balance_repo
        self.movement_repo = movement_repo
        self.cost_repo = cost_repo
        self.membership_service = membership_service
        self.business_repo = business_repo
        self.location_repo = location_repo
        self.warehouse_repo = warehouse_repo
        self.product_repo = product_repo
        self.variant_repo = variant_repo

    async def _validate_access(
        self,
        business_id: str,
        user_id: str,
        required_roles: Optional[tuple[BusinessMembershipRole, ...]] = None,
    ) -> BusinessMembershipInDB:
        """
        Validate business existence and user active membership.
        Follows anti-enumeration pattern (returns 404 for nonexistent/archived business or non-members).
        """
        business = await self.business_repo.get_by_id(business_id)
        if not business or business.status == BusinessStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found or access denied.",
            )

        try:
            membership = await self.membership_service.require_active_membership(business_id, user_id)
        except HTTPException as exc:
            if exc.status_code == status.HTTP_403_FORBIDDEN:
                # Anti-enumeration policy check: if user is not in business at all vs suspended
                # Check membership details from membership service
                mem = await self.membership_service.membership_repo.get_membership(business_id, user_id)
                if not mem or mem.status == "REMOVED":
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Business not found or access denied.",
                    )
                raise exc
            raise exc

        if required_roles and membership.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied for this inventory operation.",
            )

        return membership

    async def _validate_location(self, business_id: str, location_id: str) -> None:
        location = await self.location_repo.get_by_id(location_id)
        if (
            not location
            or location.business_id != business_id
            or location.status != InventoryLocationStatus.ACTIVE
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inventory location is invalid, inactive, or belongs to another business.",
            )

    async def _validate_product_and_variant(
        self, business_id: str, product_id: str, variant_id: Optional[str]
    ) -> None:
        product = await self.product_repo.get_by_id(product_id, business_id)
        if not product or product.status != ProductStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product not found, inactive, or belongs to another business.",
            )

        if product.product_type != ProductType.GOODS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inventory stock can only be managed for GOODS products, not SERVICE products.",
            )

        if variant_id is not None:
            variant = await self.variant_repo.get_by_id(variant_id, business_id)
            if not variant or variant.status != ProductVariantStatus.ACTIVE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Product variant not found, inactive, or belongs to another business.",
                )
            if variant.product_id != product_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Variant does not belong to the specified product.",
                )

    async def _resolve_sale_location(
        self,
        business_id: str,
        explicit_location_id: Optional[str],
        branch_id: Optional[str],
    ) -> str:
        """
        Resolve active inventory location for a Sales order.

        Priority:
        1. Explicit location_id provided -> validate ownership/business/active.
        2. Branch-scoped default warehouse + default location.
        3. Business-level default warehouse + default location.
        """
        if explicit_location_id is not None:
            loc = await self.location_repo.get_by_id(explicit_location_id)
            if not loc or loc.business_id != business_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Inventory location not found in this business.",
                )

            wh = await self.warehouse_repo.get_by_id(loc.warehouse_id)
            if not wh or wh.business_id != business_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Warehouse for this inventory location belongs to another business or is missing.",
                )
            if wh.status != WarehouseStatus.ACTIVE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Warehouse is not ACTIVE (current: {wh.status}).",
                )
            if loc.status != InventoryLocationStatus.ACTIVE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Inventory location is not ACTIVE (current: {loc.status}).",
                )
            if loc.location_type in (InventoryLocationType.DAMAGED, InventoryLocationType.QUARANTINE):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Inventory location cannot be DAMAGED or QUARANTINE.",
                )
            return loc.id

        wh: Optional[WarehouseInDB] = None
        if branch_id:
            branch_warehouses = await self.warehouse_repo.list_by_branch(business_id, branch_id)
            for w in branch_warehouses:
                if w.status == WarehouseStatus.ACTIVE and w.is_default:
                    wh = w
                    break

        if wh is None:
            wh = await self.warehouse_repo.get_default(business_id)
            if wh is not None and wh.status != WarehouseStatus.ACTIVE:
                wh = None

        if wh is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active default warehouse available in this business.",
            )

        location = await self.location_repo.get_default(wh.id)
        if location is None or location.status != InventoryLocationStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active default inventory location in the resolved warehouse.",
            )
        return location.id

    async def create_opening_balance(
        self, business_id: str, user_id: str, payload: OpeningBalanceInput
    ) -> StockMovementResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        await self._validate_location(business_id, payload.inventory_location_id)
        await self._validate_product_and_variant(business_id, payload.product_id, payload.variant_id)

        if payload.quantity <= Decimal("0"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quantity must be greater than zero.",
            )

        ref_id = str(uuid.uuid4())
        movement = await self.movement_repo.create_movement(
            business_id=business_id,
            movement_type=MovementType.OPENING_BALANCE,
            performed_by_user_id=user_id,
            reference_type=ReferenceType.OPENING_BALANCE,
            reference_id=ref_id,
            notes=payload.notes,
        )

        line = await self.movement_repo.create_line(
            movement_id=movement.id,
            inventory_location_id=payload.inventory_location_id,
            product_id=payload.product_id,
            variant_id=payload.variant_id,
            quantity=payload.quantity,
            direction=MovementDirection.IN,
        )

        await self.balance_repo.upsert_balance(
            business_id=business_id,
            inventory_location_id=payload.inventory_location_id,
            product_id=payload.product_id,
            variant_id=payload.variant_id,
            delta=payload.quantity,
        )

        # Feature #38: Initialize cost state.
        # Physical stock and cost state quantity MUST match. Always record quantity.
        if payload.unit_cost is not None and payload.unit_cost > Decimal("0"):
            await self.record_cost_inbound(
                business_id=business_id,
                product_id=payload.product_id,
                variant_id=payload.variant_id,
                inbound_qty=payload.quantity,
                inbound_unit_cost=payload.unit_cost,
                movement_type=InventoryCostMovementType.OPENING_BALANCE,
                reference_type="OPENING_BALANCE",
                reference_id=ref_id,
            )
        else:
            await self.record_cost_inbound(
                business_id=business_id,
                product_id=payload.product_id,
                variant_id=payload.variant_id,
                inbound_qty=payload.quantity,
                inbound_unit_cost=Decimal("0.0000"),
                movement_type=InventoryCostMovementType.OPENING_BALANCE,
                reference_type="OPENING_BALANCE",
                reference_id=ref_id,
            )

        return StockMovementResponse(
            **movement.model_dump(),
            lines=[StockMovementLineResponse(**line.model_dump())],
        )

    async def adjust_in(
        self,
        business_id: str,
        user_id: str,
        payload: AdjustmentInput,
        reference_type: Optional[ReferenceType] = None,
        reference_id: Optional[str] = None,
    ) -> StockMovementResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        await self._validate_location(business_id, payload.inventory_location_id)
        await self._validate_product_and_variant(business_id, payload.product_id, payload.variant_id)

        if payload.quantity <= Decimal("0"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quantity must be greater than zero.",
            )

        ref_t = reference_type or ReferenceType.ADJUSTMENT
        ref_i = reference_id or str(uuid.uuid4())
        movement = await self.movement_repo.create_movement(
            business_id=business_id,
            movement_type=MovementType.ADJUSTMENT_IN,
            performed_by_user_id=user_id,
            reference_type=ref_t,
            reference_id=ref_i,
            notes=payload.notes,
        )

        line = await self.movement_repo.create_line(
            movement_id=movement.id,
            inventory_location_id=payload.inventory_location_id,
            product_id=payload.product_id,
            variant_id=payload.variant_id,
            quantity=payload.quantity,
            direction=MovementDirection.IN,
        )

        await self.balance_repo.upsert_balance(
            business_id=business_id,
            inventory_location_id=payload.inventory_location_id,
            product_id=payload.product_id,
            variant_id=payload.variant_id,
            delta=payload.quantity,
        )

        return StockMovementResponse(
            **movement.model_dump(),
            lines=[StockMovementLineResponse(**line.model_dump())],
        )

    async def adjust_out(
        self,
        business_id: str,
        user_id: str,
        payload: AdjustmentInput,
        reference_type: Optional[ReferenceType] = None,
        reference_id: Optional[str] = None,
    ) -> StockMovementResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        await self._validate_location(business_id, payload.inventory_location_id)
        await self._validate_product_and_variant(business_id, payload.product_id, payload.variant_id)

        if payload.quantity <= Decimal("0"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quantity must be greater than zero.",
            )

        current_balance = await self.balance_repo.get_balance(
            business_id, payload.inventory_location_id, payload.product_id, payload.variant_id
        )

        available_qty = current_balance.quantity if current_balance else Decimal("0")
        if available_qty < payload.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock balance. Available: {available_qty}, requested adjustment OUT: {payload.quantity}.",
            )

        ref_t = reference_type or ReferenceType.ADJUSTMENT
        ref_i = reference_id or str(uuid.uuid4())
        movement = await self.movement_repo.create_movement(
            business_id=business_id,
            movement_type=MovementType.ADJUSTMENT_OUT,
            performed_by_user_id=user_id,
            reference_type=ref_t,
            reference_id=ref_i,
            notes=payload.notes,
        )

        line = await self.movement_repo.create_line(
            movement_id=movement.id,
            inventory_location_id=payload.inventory_location_id,
            product_id=payload.product_id,
            variant_id=payload.variant_id,
            quantity=payload.quantity,
            direction=MovementDirection.OUT,
        )

        await self.balance_repo.upsert_balance(
            business_id=business_id,
            inventory_location_id=payload.inventory_location_id,
            product_id=payload.product_id,
            variant_id=payload.variant_id,
            delta=-payload.quantity,
        )

        return StockMovementResponse(
            **movement.model_dump(),
            lines=[StockMovementLineResponse(**line.model_dump())],
        )

    async def create_transfer(
        self, business_id: str, user_id: str, payload: TransferInput
    ) -> List[StockMovementResponse]:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        if payload.source_inventory_location_id == payload.destination_inventory_location_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source and destination inventory locations must be different.",
            )

        await self._validate_location(business_id, payload.source_inventory_location_id)
        await self._validate_location(business_id, payload.destination_inventory_location_id)
        await self._validate_product_and_variant(business_id, payload.product_id, payload.variant_id)

        if payload.quantity <= Decimal("0"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quantity must be greater than zero.",
            )

        # Check source balance
        source_balance = await self.balance_repo.get_balance(
            business_id, payload.source_inventory_location_id, payload.product_id, payload.variant_id
        )
        available_qty = source_balance.quantity if source_balance else Decimal("0")
        if available_qty < payload.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock at source location. Available: {available_qty}, requested transfer: {payload.quantity}.",
            )

        transfer_id = str(uuid.uuid4())

        # Atomic logical operation: 1. TRANSFER_OUT, 2. TRANSFER_IN
        # TRANSFER_OUT movement
        m_out = await self.movement_repo.create_movement(
            business_id=business_id,
            movement_type=MovementType.TRANSFER_OUT,
            performed_by_user_id=user_id,
            reference_type=ReferenceType.TRANSFER,
            reference_id=transfer_id,
            notes=payload.notes,
        )
        line_out = await self.movement_repo.create_line(
            movement_id=m_out.id,
            inventory_location_id=payload.source_inventory_location_id,
            product_id=payload.product_id,
            variant_id=payload.variant_id,
            quantity=payload.quantity,
            direction=MovementDirection.OUT,
        )

        # TRANSFER_IN movement
        m_in = await self.movement_repo.create_movement(
            business_id=business_id,
            movement_type=MovementType.TRANSFER_IN,
            performed_by_user_id=user_id,
            reference_type=ReferenceType.TRANSFER,
            reference_id=transfer_id,
            notes=payload.notes,
        )
        line_in = await self.movement_repo.create_line(
            movement_id=m_in.id,
            inventory_location_id=payload.destination_inventory_location_id,
            product_id=payload.product_id,
            variant_id=payload.variant_id,
            quantity=payload.quantity,
            direction=MovementDirection.IN,
        )

        # Update stock balances
        await self.balance_repo.upsert_balance(
            business_id=business_id,
            inventory_location_id=payload.source_inventory_location_id,
            product_id=payload.product_id,
            variant_id=payload.variant_id,
            delta=-payload.quantity,
        )
        await self.balance_repo.upsert_balance(
            business_id=business_id,
            inventory_location_id=payload.destination_inventory_location_id,
            product_id=payload.product_id,
            variant_id=payload.variant_id,
            delta=payload.quantity,
        )

        res_out = StockMovementResponse(
            **m_out.model_dump(),
            lines=[StockMovementLineResponse(**line_out.model_dump())],
        )
        res_in = StockMovementResponse(
            **m_in.model_dump(),
            lines=[StockMovementLineResponse(**line_in.model_dump())],
        )

        return [res_out, res_in]

    async def list_stock_balances(
        self,
        business_id: str,
        user_id: str,
        inventory_location_id: Optional[str] = None,
        product_id: Optional[str] = None,
        variant_id: Optional[str] = None,
    ) -> List[StockBalanceResponse]:
        await self._validate_access(business_id, user_id)
        balances = await self.balance_repo.list_balances(
            business_id=business_id,
            inventory_location_id=inventory_location_id,
            product_id=product_id,
            variant_id=variant_id,
        )
        return [StockBalanceResponse(**b.model_dump()) for b in balances]

    async def get_stock_balance(
        self, business_id: str, user_id: str, stock_id: str
    ) -> StockBalanceResponse:
        await self._validate_access(business_id, user_id)
        sb = await self.balance_repo.get_by_id(stock_id, business_id)
        if not sb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stock balance record not found.",
            )
        return StockBalanceResponse(**sb.model_dump())

    async def list_movements(
        self,
        business_id: str,
        user_id: str,
        movement_type: Optional[MovementType] = None,
        inventory_location_id: Optional[str] = None,
        product_id: Optional[str] = None,
        variant_id: Optional[str] = None,
    ) -> List[StockMovementResponse]:
        await self._validate_access(business_id, user_id)
        movements = await self.movement_repo.list_movements(
            business_id=business_id,
            movement_type=movement_type,
            inventory_location_id=inventory_location_id,
            product_id=product_id,
            variant_id=variant_id,
        )

        results = []
        for m in movements:
            lines = await self.movement_repo.list_lines_for_movement(m.id)
            results.append(
                StockMovementResponse(
                    **m.model_dump(),
                    lines=[StockMovementLineResponse(**l.model_dump()) for l in lines],
                )
            )
        return results

    async def get_total_stock(
        self,
        business_id: str,
        user_id: str,
        product_id: str,
        variant_id: Optional[str] = None,
    ) -> TotalStockResponse:
        await self._validate_access(business_id, user_id)
        await self._validate_product_and_variant(business_id, product_id, variant_id)

        product = await self.product_repo.get_by_id(product_id, business_id)
        variant_name = None
        if variant_id:
            variant = await self.variant_repo.get_by_id(variant_id, business_id)
            if variant:
                variant_name = variant.name

        balances = await self.balance_repo.list_balances(
            business_id=business_id,
            product_id=product_id,
            variant_id=variant_id,
        )

        total_qty = sum((b.quantity for b in balances), Decimal("0"))

        return TotalStockResponse(
            product_id=product_id,
            product_name=product.name if product else "",
            variant_id=variant_id,
            variant_name=variant_name,
            total_quantity=total_qty,
        )

    async def deduct_sales_stock(
        self,
        business_id: str,
        user_id: str,
        sales_id: str,
        sales_number: str,
        explicit_location_id: Optional[str],
        branch_id: Optional[str],
        goods_lines: List[dict],
    ) -> Optional[StockMovementResponse]:
        """
        Deduct stock for GOODS lines in a Sales order during finalization.

        1. Duplicate posting check (ReferenceType.SALES, reference_id=sales_id).
        2. Resolve inventory location.
        3. Aggregate required quantity by (product_id, variant_id).
        4. Validate stock availability for all aggregated targets before mutation.
        5. Create SALE_OUT StockMovement + Lines + update StockBalance.
        """
        if not goods_lines:
            return None

        # 1. Duplicate posting check
        existing_movements = await self.movement_repo.list_movements(
            business_id=business_id,
            movement_type=MovementType.SALE_OUT,
        )
        for m in existing_movements:
            if m.reference_type == ReferenceType.SALES and m.reference_id == sales_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Inventory stock has already been deducted for this Sales order.",
                )

        # 2. Resolve inventory location
        location_id = await self._resolve_sale_location(business_id, explicit_location_id, branch_id)

        # 3. Aggregate required quantity by target stock identity
        aggregated_demands = {}
        for g in goods_lines:
            pid = g["product_id"]
            vid = g.get("variant_id")
            qty = g["quantity"]

            # Validate active product/variant
            await self._validate_product_and_variant(business_id, pid, vid)

            key = (pid, vid)
            aggregated_demands[key] = aggregated_demands.get(key, Decimal("0")) + qty

        # 4. Validate stock availability for all aggregated targets before mutation
        for (pid, vid), req_qty in aggregated_demands.items():
            balance = await self.balance_repo.get_balance(business_id, location_id, pid, vid)
            avail_qty = balance.quantity if balance else Decimal("0")
            if avail_qty < req_qty:
                target_name = f"variant {vid}" if vid else f"product {pid}"
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock for {target_name} at resolved location. Available: {avail_qty}, required: {req_qty}.",
                )

        # 5. Create SALE_OUT movement + lines + update balances
        movement = await self.movement_repo.create_movement(
            business_id=business_id,
            movement_type=MovementType.SALE_OUT,
            performed_by_user_id=user_id,
            reference_type=ReferenceType.SALES,
            reference_id=sales_id,
            notes=f"Stock deduction for Sales {sales_number}",
        )

        movement_lines = []
        for g in goods_lines:
            pid = g["product_id"]
            vid = g.get("variant_id")
            qty = g["quantity"]

            line = await self.movement_repo.create_line(
                movement_id=movement.id,
                inventory_location_id=location_id,
                product_id=pid,
                variant_id=vid,
                quantity=qty,
                direction=MovementDirection.OUT,
            )
            movement_lines.append(line)

            await self.balance_repo.upsert_balance(
                business_id=business_id,
                inventory_location_id=location_id,
                product_id=pid,
                variant_id=vid,
                delta=-qty,
            )

        return StockMovementResponse(
            **movement.model_dump(),
            lines=[StockMovementLineResponse(**l.model_dump()) for l in movement_lines],
        )

    async def return_sales_stock(
        self,
        business_id: str,
        user_id: str,
        sales_return_id: str,
        return_number: str,
        location_id: str,
        goods_lines: List[dict],
    ) -> StockMovementResponse:
        """
        Return stock for GOODS lines in a Sales Return during finalization.
        1. Duplicate posting check (ReferenceType.SALES_RETURN, reference_id=sales_return_id).
        2. Validate location and active product/variants.
        3. Create SALE_RETURN_IN movement + lines + update balances (delta = +qty).
        """
        if not goods_lines:
            return None

        # 1. Duplicate posting check
        existing_movements = await self.movement_repo.list_movements(
            business_id=business_id,
            movement_type=MovementType.SALE_RETURN_IN,
        )
        for m in existing_movements:
            if m.reference_type == ReferenceType.SALES_RETURN and m.reference_id == sales_return_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Inventory stock has already been returned for this Sales Return.",
                )

        # 2. Validate location
        await self._validate_location(business_id, location_id)

        # Validate products/variants
        for g in goods_lines:
            pid = g["product_id"]
            vid = g.get("variant_id")
            await self._validate_product_and_variant(business_id, pid, vid)

        # 3. Create SALE_RETURN_IN movement + lines + update balances
        movement = await self.movement_repo.create_movement(
            business_id=business_id,
            movement_type=MovementType.SALE_RETURN_IN,
            performed_by_user_id=user_id,
            reference_type=ReferenceType.SALES_RETURN,
            reference_id=sales_return_id,
            notes=f"Stock return for Sales Return {return_number}",
        )

        movement_lines = []
        for g in goods_lines:
            pid = g["product_id"]
            vid = g.get("variant_id")
            qty = g["quantity"]

            line = await self.movement_repo.create_line(
                movement_id=movement.id,
                inventory_location_id=location_id,
                product_id=pid,
                variant_id=vid,
                quantity=qty,
                direction=MovementDirection.IN,
            )
            movement_lines.append(line)

            await self.balance_repo.upsert_balance(
                business_id=business_id,
                inventory_location_id=location_id,
                product_id=pid,
                variant_id=vid,
                delta=qty,
            )

        return StockMovementResponse(
            **movement.model_dump(),
            lines=[StockMovementLineResponse(**l.model_dump()) for l in movement_lines],
        )

    async def get_physical_quantity(
        self, business_id: str, product_id: str, variant_id: Optional[str] = None
    ) -> Decimal:
        balances = await self.balance_repo.list_balances(
            business_id=business_id,
            product_id=product_id,
            variant_id=variant_id,
        )
        return sum((b.quantity for b in balances), Decimal("0"))

    async def validate_physical_cost_consistency(
        self, business_id: str, product_id: str, variant_id: Optional[str] = None
    ) -> Optional[InventoryCostStateInDB]:
        physical_qty = await self.get_physical_quantity(business_id, product_id, variant_id)
        cost_state = await self.cost_repo.get_cost_state(business_id, product_id, variant_id)
        cost_qty = cost_state.quantity if cost_state else Decimal("0")

        # Only enforce consistency check if a cost state exists
        if cost_state is not None and physical_qty != cost_qty:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"INVENTORY_VALUATION_MISMATCH: Physical stock quantity ({physical_qty}) does not match valuation cost state quantity ({cost_qty}) for product {product_id}.",
            )
        return cost_state

    async def get_current_mac(
        self, business_id: str, product_id: str, variant_id: Optional[str] = None
    ) -> Decimal:
        cost_state = await self.cost_repo.get_cost_state(business_id, product_id, variant_id)
        return cost_state.unit_cost if cost_state else Decimal("0")

    async def record_cost_inbound(
        self,
        business_id: str,
        product_id: str,
        variant_id: Optional[str],
        inbound_qty: Decimal,
        inbound_unit_cost: Decimal,
        movement_type: InventoryCostMovementType,
        reference_type: Optional[str],
        reference_id: Optional[str],
    ) -> InventoryCostStateInDB:
        existing = await self.cost_repo.get_cost_state(business_id, product_id, variant_id)
        cur_qty = existing.quantity if existing else Decimal("0")
        cur_total_cost = existing.total_cost if existing else Decimal("0")

        inbound_total_cost = inbound_qty * inbound_unit_cost
        new_qty = cur_qty + inbound_qty
        new_total_cost = cur_total_cost + inbound_total_cost

        # MAC recalculation
        if new_qty > Decimal("0"):
            new_mac = new_total_cost / new_qty
        else:
            new_mac = Decimal("0")
            new_total_cost = Decimal("0")
            new_qty = Decimal("0")

        updated_cost_state = await self.cost_repo.update_cost_state(
            business_id=business_id,
            product_id=product_id,
            variant_id=variant_id,
            quantity=new_qty,
            total_cost=new_total_cost,
            unit_cost=new_mac,
        )

        await self.cost_repo.create_cost_movement(
            business_id=business_id,
            product_id=product_id,
            variant_id=variant_id,
            movement_type=movement_type,
            reference_type=reference_type,
            reference_id=reference_id,
            quantity_delta=inbound_qty,
            cost_delta=inbound_total_cost,
            unit_cost_at_time=new_mac,
        )

        return updated_cost_state

    async def record_cost_outbound(
        self,
        business_id: str,
        product_id: str,
        variant_id: Optional[str],
        outbound_qty: Decimal,
        unit_cost: Decimal,
        movement_type: InventoryCostMovementType,
        reference_type: Optional[str],
        reference_id: Optional[str],
    ) -> tuple[InventoryCostStateInDB, Decimal]:
        existing = await self.cost_repo.get_cost_state(business_id, product_id, variant_id)
        cur_qty = existing.quantity if existing else Decimal("0")
        cur_total_cost = existing.total_cost if existing else Decimal("0")
        cur_mac = existing.unit_cost if existing else Decimal("0")

        cost_deduction = outbound_qty * unit_cost
        new_qty = cur_qty - outbound_qty
        new_total_cost = cur_total_cost - cost_deduction

        if new_qty <= Decimal("0"):
            new_qty = Decimal("0")
            new_total_cost = Decimal("0")
            new_mac = Decimal("0")
        else:
            if new_total_cost < Decimal("0"):
                new_total_cost = Decimal("0")
            new_mac = cur_mac

        updated_cost_state = await self.cost_repo.update_cost_state(
            business_id=business_id,
            product_id=product_id,
            variant_id=variant_id,
            quantity=new_qty,
            total_cost=new_total_cost,
            unit_cost=new_mac,
        )

        await self.cost_repo.create_cost_movement(
            business_id=business_id,
            product_id=product_id,
            variant_id=variant_id,
            movement_type=movement_type,
            reference_type=reference_type,
            reference_id=reference_id,
            quantity_delta=-outbound_qty,
            cost_delta=-cost_deduction,
            unit_cost_at_time=unit_cost,
        )

        return updated_cost_state, cost_deduction

    async def sync_opname_cost_state(
        self,
        business_id: str,
        product_id: str,
        variant_id: Optional[str],
        new_physical_qty: Decimal,
        reference_id: str,
    ) -> None:
        existing = await self.cost_repo.get_cost_state(business_id, product_id, variant_id)
        cur_qty = existing.quantity if existing else Decimal("0")
        cur_total_cost = existing.total_cost if existing else Decimal("0")
        mac = existing.unit_cost if existing else Decimal("0")

        if new_physical_qty <= Decimal("0") or mac <= Decimal("0"):
            new_total_cost = Decimal("0")
            if new_physical_qty <= Decimal("0"):
                mac = Decimal("0")
        else:
            new_total_cost = new_physical_qty * mac

        await self.cost_repo.update_cost_state(
            business_id=business_id,
            product_id=product_id,
            variant_id=variant_id,
            quantity=new_physical_qty,
            total_cost=new_total_cost,
            unit_cost=mac,
        )

        await self.cost_repo.create_cost_movement(
            business_id=business_id,
            product_id=product_id,
            variant_id=variant_id,
            movement_type=InventoryCostMovementType.OPNAME_SYNC,
            reference_type="STOCK_OPNAME",
            reference_id=reference_id,
            quantity_delta=new_physical_qty - cur_qty,
            cost_delta=new_total_cost - cur_total_cost,
            unit_cost_at_time=mac,
        )

    async def get_valuation_summary(
        self, business_id: str, user_id: str
    ) -> ValuationSummaryResponse:
        await self._validate_access(business_id, user_id)

        cost_states = await self.cost_repo.list_cost_states(business_id=business_id)
        items: List[ValuationSummaryItem] = []
        total_inventory_value = Decimal("0")

        for cs in cost_states:
            product = await self.product_repo.get_by_id(cs.product_id, business_id)
            product_name = product.name if product else cs.product_id
            variant_name = None
            if cs.variant_id:
                variant = await self.variant_repo.get_by_id(cs.variant_id, business_id)
                variant_name = variant.name if variant else cs.variant_id

            item = ValuationSummaryItem(
                product_id=cs.product_id,
                product_name=product_name,
                variant_id=cs.variant_id,
                variant_name=variant_name,
                total_quantity=cs.quantity,
                unit_cost=cs.unit_cost,
                total_cost=cs.total_cost,
            )
            items.append(item)
            total_inventory_value += cs.total_cost

        return ValuationSummaryResponse(
            items=items,
            total_inventory_value=total_inventory_value,
        )


inventory_service = InventoryService()

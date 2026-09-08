from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime, timezone, date, timedelta
from fastapi import HTTPException, status

from app.modules.inventory.schemas import (
    StockCardResponse,
    StockCardLineResponse,
    StatementDateRange,
    MovementType,
    MovementDirection,
)
from app.modules.inventory.repository import (
    stock_movement_repository,
    AbstractStockMovementRepository,
    inventory_cost_repository,
    AbstractInventoryCostRepository,
)
from app.modules.purchase.repository import (
    purchase_repository,
    AbstractPurchaseRepository,
)
from app.modules.purchase.schemas import PurchaseStatus
from app.modules.purchase_return.repository import (
    purchase_return_repository,
    AbstractPurchaseReturnRepository,
)
from app.modules.purchase_return.schemas import PurchaseReturnStatus
from app.modules.sales.repository import (
    sales_repository,
    AbstractSalesRepository,
)
from app.modules.sales.schemas import SalesStatus
from app.modules.sales_return.repository import (
    sales_return_repository,
    AbstractSalesReturnRepository,
)
from app.modules.sales_return.schemas import SalesReturnStatus
from app.modules.warehouse.repository import (
    inventory_location_repository,
    AbstractInventoryLocationRepository,
    warehouse_repository,
    AbstractWarehouseRepository,
)
from app.modules.warehouse.schemas import (
    WarehouseStatus,
    InventoryLocationStatus,
)
from app.modules.product.repository import (
    product_repository,
    AbstractProductRepository,
)
from app.modules.product_variant.repository import (
    product_variant_repository,
    AbstractProductVariantRepository,
)
from app.modules.unit.repository import unit_repository
from app.modules.business_membership.service import (
    BusinessMembershipService,
    business_membership_service,
)
from app.modules.business_membership.schemas import BusinessMembershipRole


class InternalStockEvent:
    def __init__(
        self,
        transaction_date: datetime,
        movement_type: str,
        type_priority: int,
        reference_id: str,
        reference_number: Optional[str],
        notes: Optional[str],
        qty_in: Decimal,
        qty_out: Decimal,
        unit_cost: Decimal,
        source_id: str,
    ):
        self.transaction_date = transaction_date
        self.movement_type = movement_type
        self.type_priority = type_priority
        self.reference_id = reference_id
        self.reference_number = reference_number
        self.notes = notes
        self.qty_in = qty_in
        self.qty_out = qty_out
        self.unit_cost = unit_cost
        self.source_id = source_id


class StockCardService:
    def __init__(
        self,
        movement_repo: AbstractStockMovementRepository = stock_movement_repository,
        cost_repo: AbstractInventoryCostRepository = inventory_cost_repository,
        purchase_repo: AbstractPurchaseRepository = purchase_repository,
        purchase_return_repo: AbstractPurchaseReturnRepository = purchase_return_repository,
        sales_repo: AbstractSalesRepository = sales_repository,
        sales_return_repo: AbstractSalesReturnRepository = sales_return_repository,
        location_repo: AbstractInventoryLocationRepository = inventory_location_repository,
        warehouse_repo: AbstractWarehouseRepository = warehouse_repository,
        product_repo: AbstractProductRepository = product_repository,
        variant_repo: AbstractProductVariantRepository = product_variant_repository,
        membership_service: BusinessMembershipService = business_membership_service,
    ):
        self.movement_repo = movement_repo
        self.cost_repo = cost_repo
        self.purchase_repo = purchase_repo
        self.purchase_return_repo = purchase_return_repo
        self.sales_repo = sales_repo
        self.sales_return_repo = sales_return_repo
        self.location_repo = location_repo
        self.warehouse_repo = warehouse_repo
        self.product_repo = product_repo
        self.variant_repo = variant_repo
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

    async def _resolve_purchase_location(self, business_id: str, branch_id: str) -> Optional[str]:
        whs = await self.warehouse_repo.list_by_branch(business_id, branch_id)
        wh = None
        for w in whs:
            if w.status == WarehouseStatus.ACTIVE and w.is_default:
                wh = w
                break
        if not wh:
            wh = await self.warehouse_repo.get_default(business_id)
        if not wh:
            return None
        loc = await self.location_repo.get_default(wh.id)
        if not loc or loc.status != InventoryLocationStatus.ACTIVE:
            return None
        return loc.id

    async def get_stock_card(
        self,
        business_id: str,
        user_id: str,
        location_id: str,
        product_id: str,
        variant_id: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> StockCardResponse:
        await self._validate_access(
            business_id,
            user_id,
            required_roles=(
                BusinessMembershipRole.OWNER,
                BusinessMembershipRole.ADMIN,
                BusinessMembershipRole.MEMBER,
            ),
        )

        # Validate location
        location = await self.location_repo.get_by_id(location_id)
        if not location or location.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Location not found in this business.",
            )

        # Validate product
        product = await self.product_repo.get_by_id(product_id, business_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found in this business.",
            )

        # Check product variants invariant
        variants = await self.variant_repo.list_by_product(business_id, product_id)
        if variants and not variant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product has variants. Please specify variant_id.",
            )

        variant_name = None
        if variant_id:
            variant = await self.variant_repo.get_by_id(variant_id, business_id)
            if not variant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Variant not found for this product.",
                )
            variant_name = variant.name

        unit_code = None
        if product.unit_id:
            u = await unit_repository.get_by_id(product.unit_id, business_id)
            if u:
                unit_code = u.code

        # Validate dates
        if date_from is None:
            today = date.today()
            date_from = date(today.year, today.month, 1)
        if date_to is None:
            date_to = date.today()

        if date_from > date_to:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="date_from must be less than or equal to date_to.",
            )

        if page < 1:
            page = 1
        if page_size < 1 or page_size > 500:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="page_size must be between 1 and 500.",
            )

        start_dt = datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc)
        end_dt_exclusive = datetime.combine(
            date_to + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc
        )

        def _normalize_dt(dt: datetime) -> datetime:
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)

        type_priority = {
            "OPENING_BALANCE": 1,
            "PURCHASE": 2,
            "ADJUSTMENT_IN": 4,
            "TRANSFER_IN": 5,
            "SALE_RETURN_IN": 6,
            "SALE_OUT": 7,
            "TRANSFER_OUT": 8,
            "PURCHASE_RETURN": 9,
            "ADJUSTMENT_OUT": 10,
        }

        # 1. Collect all StockMovement records matching filters
        movements = await self.movement_repo.list_movements(
            business_id=business_id,
            inventory_location_id=location_id,
            product_id=product_id,
            variant_id=variant_id,
        )

        # Load all cost movements for this product/variant (needed for opening balance valuation)
        cost_movements = self.cost_repo._cost_movements
        hist_cost_movements = [
            cm for cm in cost_movements
            if cm.business_id == business_id
            and cm.product_id == product_id
            and cm.variant_id == variant_id
        ]
        hist_cost_movements.sort(key=lambda x: x.created_at)

        all_events: List[InternalStockEvent] = []

        for m in movements:
            lines = await self.movement_repo.list_lines_for_movement(m.id)
            for l in lines:
                if l.inventory_location_id != location_id or l.product_id != product_id or l.variant_id != variant_id:
                    continue

                m_type = m.movement_type.value if hasattr(m.movement_type, "value") else str(m.movement_type)
                ref_id = m.reference_id or m.id
                ref_num = None
                tx_date = _normalize_dt(m.created_at)
                unit_cost = Decimal("0.00")

                if m_type == "OPENING_BALANCE":
                    # Opening balance cost is stored in InventoryCostMovement, not movement line.
                    # Retrieve the most recent cost movement for this reference.
                    for cm in reversed(hist_cost_movements):
                        if cm.reference_id == ref_id:
                            unit_cost = cm.unit_cost_at_time
                            break

                elif m_type == "SALE_OUT":
                    if m.reference_id:
                        s_obj = await self.sales_repo.get_sales_by_id(m.reference_id, business_id)
                        if not s_obj or s_obj.status != SalesStatus.FINALIZED:
                            continue
                        tx_date = _normalize_dt(s_obj.sales_date)
                        ref_num = s_obj.sales_number
                        s_lines = await self.sales_repo.list_lines_for_sales(s_obj.id)
                        for sl in s_lines:
                            if sl.product_id == product_id and sl.variant_id == variant_id:
                                if sl.unit_cost_snapshot is not None:
                                    unit_cost = sl.unit_cost_snapshot
                                break
                elif m_type == "SALE_RETURN_IN":
                    if m.reference_id:
                        r_obj = await self.sales_return_repo.get_return_by_id(m.reference_id, business_id)
                        if not r_obj or r_obj.status != SalesReturnStatus.FINALIZED:
                            continue
                        tx_date = _normalize_dt(r_obj.return_date)
                        ref_num = r_obj.return_number
                        sr_lines = await self.sales_return_repo.list_lines_for_return(r_obj.id)
                        for srl in sr_lines:
                            if srl.product_id == product_id and srl.variant_id == variant_id:
                                s_obj = await self.sales_repo.get_sales_by_id(r_obj.sales_id, business_id)
                                if s_obj:
                                    s_lines = await self.sales_repo.list_lines_for_sales(s_obj.id)
                                    for sl in s_lines:
                                        if sl.id == srl.sales_line_id and sl.unit_cost_snapshot is not None:
                                            unit_cost = sl.unit_cost_snapshot
                                            break
                                break

                qty_in = l.quantity if l.direction == MovementDirection.IN else Decimal("0.00")
                qty_out = l.quantity if l.direction == MovementDirection.OUT else Decimal("0.00")
                prio = type_priority.get(m_type, 5)

                all_events.append(
                    InternalStockEvent(
                        transaction_date=tx_date,
                        movement_type=m_type,
                        type_priority=prio,
                        reference_id=ref_id,
                        reference_number=ref_num,
                        notes=m.notes,
                        qty_in=qty_in,
                        qty_out=qty_out,
                        unit_cost=unit_cost,
                        source_id=f"MOV_{m.id}_{l.id}",
                    )
                )

        # 2. Collect FINALIZED Purchases
        all_purchases, _ = await self.purchase_repo.list_purchases(
            business_id=business_id,
            status=PurchaseStatus.FINALIZED,
            page=1,
            page_size=100000,
        )

        for pur in all_purchases:
            pur_loc_id = await self._resolve_purchase_location(business_id, pur.branch_id)
            if pur_loc_id != location_id:
                continue

            pur_lines = await self.purchase_repo.list_lines_for_purchase(pur.id)
            for pl in pur_lines:
                if pl.product_id == product_id and pl.variant_id == variant_id:
                    tx_date = _normalize_dt(pur.finalized_at or pur.purchase_date)
                    unit_cost = pl.unit_price
                    all_events.append(
                        InternalStockEvent(
                            transaction_date=tx_date,
                            movement_type="PURCHASE",
                            type_priority=type_priority["PURCHASE"],
                            reference_id=pur.id,
                            reference_number=pur.purchase_number,
                            notes=None,
                            qty_in=pl.quantity,
                            qty_out=Decimal("0.00"),
                            unit_cost=unit_cost,
                            source_id=f"PUR_{pur.id}_{pl.id}",
                        )
                    )

        # 3. Collect FINALIZED Purchase Returns
        all_purchase_returns, _ = await self.purchase_return_repo.list_returns(
            business_id=business_id,
            status=PurchaseReturnStatus.FINALIZED,
            page=1,
            page_size=100000,
        )

        for pret in all_purchase_returns:
            if pret.is_deleted or pret.inventory_location_id != location_id:
                continue

            pret_lines = await self.purchase_return_repo.list_lines_for_return(pret.id)
            for prl in pret_lines:
                if prl.product_id == product_id and prl.variant_id == variant_id:
                    tx_date = _normalize_dt(pret.finalized_at or pret.created_at)
                    unit_cost = prl.unit_price
                    all_events.append(
                        InternalStockEvent(
                            transaction_date=tx_date,
                            movement_type="PURCHASE_RETURN",
                            type_priority=type_priority["PURCHASE_RETURN"],
                            reference_id=pret.id,
                            reference_number=pret.return_number,
                            notes=pret.notes,
                            qty_in=Decimal("0.00"),
                            qty_out=prl.quantity,
                            unit_cost=unit_cost,
                            source_id=f"PRET_{pret.id}_{prl.id}",
                        )
                    )

        # Deterministic sort across all physical events
        all_events.sort(
            key=lambda x: (
                x.transaction_date,
                x.type_priority,
                x.reference_id,
                x.source_id,
            )
        )

        # Calculate historical MAC cost movements before start_dt to reconstruct opening_unit_cost
        opening_unit_cost = Decimal("0.00")
        for cm in hist_cost_movements:
            dt = _normalize_dt(cm.created_at)
            if dt < start_dt:
                opening_unit_cost = cm.unit_cost_at_time

        # Calculate opening quantity and opening valuation
        opening_quantity = Decimal("0.00")
        for ev in all_events:
            if ev.transaction_date < start_dt:
                opening_quantity += ev.qty_in - ev.qty_out

        opening_valuation = opening_quantity * opening_unit_cost

        # Process in-period events
        period_events = [
            ev for ev in all_events
            if start_dt <= ev.transaction_date < end_dt_exclusive
        ]

        lines: List[StockCardLineResponse] = []
        running_quantity = opening_quantity
        running_valuation = opening_valuation

        total_qty_in = Decimal("0.00")
        total_qty_out = Decimal("0.00")
        total_in_value = Decimal("0.00")
        total_out_value = Decimal("0.00")

        for ev in period_events:
            if ev.qty_in > Decimal("0.00"):
                movement_val = ev.qty_in * ev.unit_cost
                total_qty_in += ev.qty_in
                total_in_value += movement_val
                running_quantity += ev.qty_in
                running_valuation += movement_val
            else:
                movement_val = ev.qty_out * ev.unit_cost
                total_qty_out += ev.qty_out
                total_out_value += movement_val
                running_quantity -= ev.qty_out
                running_valuation -= movement_val

            lines.append(
                StockCardLineResponse(
                    transaction_date=ev.transaction_date,
                    movement_type=ev.movement_type,
                    reference_id=ev.reference_id,
                    reference_number=ev.reference_number,
                    notes=ev.notes,
                    qty_in=ev.qty_in,
                    qty_out=ev.qty_out,
                    unit_cost=ev.unit_cost,
                    movement_value=movement_val,
                    running_quantity=running_quantity,
                    running_valuation=running_valuation,
                )
            )

        closing_quantity = opening_quantity + total_qty_in - total_qty_out
        closing_valuation = opening_valuation + total_in_value - total_out_value

        total_items = len(lines)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paged_lines = lines[start_idx:end_idx]

        return StockCardResponse(
            business_id=business_id,
            location_id=location_id,
            location_name=location.name,
            product_id=product_id,
            product_name=product.name,
            variant_id=variant_id,
            variant_name=variant_name,
            unit_code=unit_code,
            date_range=StatementDateRange(start_date=date_from, end_date=date_to),
            opening_quantity=opening_quantity,
            opening_unit_cost=opening_unit_cost,
            opening_valuation=opening_valuation,
            lines=paged_lines,
            total_qty_in=total_qty_in,
            total_qty_out=total_qty_out,
            total_in_value=total_in_value,
            total_out_value=total_out_value,
            closing_quantity=closing_quantity,
            closing_valuation=closing_valuation,
            page=page,
            page_size=page_size,
            total_items=total_items,
        )


stock_card_service = StockCardService()

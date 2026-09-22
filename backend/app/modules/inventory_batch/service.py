from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
import uuid

from fastapi import HTTPException, status as http_status

from app.modules.inventory_batch.repository import (
    AbstractInventoryBatchRepository,
    AbstractBatchStockBalanceRepository,
    AbstractBatchStockMovementRepository,
    InMemoryInventoryBatchRepository,
    InMemoryBatchStockBalanceRepository,
    InMemoryBatchStockMovementRepository,
)
from app.modules.inventory_batch.schemas import (
    InventoryBatchInDB, InventoryBatchResponse, InventoryBatchListResponse,
    BatchStockBalanceInDB, BatchStockMovementInDB,
    BatchAllocationInput, BatchReceivingInput,
    FEFOCandidate, FEFOCandidateListResponse,
    InventoryBatchCreate, BatchMovementDirection,
)
from app.modules.inventory.schemas import MovementDirection
from app.modules.business_membership.service import business_membership_service
from app.modules.business_membership.schemas import BusinessMembershipRole

# Default InMemory repos (overridden by SQLA deps in production)
inventory_batch_repository: AbstractInventoryBatchRepository = InMemoryInventoryBatchRepository()
batch_stock_balance_repository: AbstractBatchStockBalanceRepository = InMemoryBatchStockBalanceRepository()
batch_stock_movement_repository: AbstractBatchStockMovementRepository = InMemoryBatchStockMovementRepository()


class InventoryBatchService:
    def __init__(
        self,
        batch_repo: AbstractInventoryBatchRepository = None,
        balance_repo: AbstractBatchStockBalanceRepository = None,
        movement_repo: AbstractBatchStockMovementRepository = None,
    ):
        self.batch_repo = batch_repo or inventory_batch_repository
        self.balance_repo = balance_repo or batch_stock_balance_repository
        self.movement_repo = movement_repo or batch_stock_movement_repository

    async def _validate_access(self, business_id: str, user_id: str, required_roles: Optional[List[BusinessMembershipRole]] = None):
        membership = await business_membership_service.get_membership_by_user_and_business(user_id, business_id)
        if not membership:
            raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Not a member of this business")
        if required_roles and membership.role not in required_roles:
            raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return membership

    # ── Batch CRUD ────────────────────────────────────────────────────────

    async def create_batch(
        self, business_id: str, user_id: str,
        payload: InventoryBatchCreate,
    ) -> InventoryBatchResponse:
        await self._validate_access(business_id, user_id, [BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN])
        existing = await self.batch_repo.get_batch_by_identity(
            business_id, payload.inventory_location_id,
            payload.product_id, payload.variant_id, payload.batch_number,
        )
        if existing:
            raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail="Batch number already exists for this product/location")
        if payload.expiry_date and payload.manufacture_date and payload.expiry_date < payload.manufacture_date:
            raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Expiry date must be after manufacture date")
        batch = await self.batch_repo.create_batch(
            business_id, payload.inventory_location_id,
            payload.product_id, payload.variant_id,
            payload.batch_number, payload.manufacture_date, payload.expiry_date,
        )
        return InventoryBatchResponse.from_db(batch, remaining=Decimal("0"))

    async def get_batch(self, business_id: str, user_id: str, batch_id: str) -> InventoryBatchResponse:
        await self._validate_access(business_id, user_id)
        batch = await self.batch_repo.get_batch(batch_id, business_id)
        if not batch:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Batch not found")
        balance = await self.balance_repo.get_balance(business_id, batch.inventory_location_id, batch_id)
        remaining = balance.quantity if balance else Decimal("0")
        return InventoryBatchResponse.from_db(batch, remaining=remaining)

    async def list_batches(
        self, business_id: str, user_id: str,
        inventory_location_id: Optional[str] = None,
        product_id: Optional[str] = None,
        variant_id: Optional[str] = None,
        expired_only: bool = False,
        page: int = 1, page_size: int = 50,
    ) -> InventoryBatchListResponse:
        await self._validate_access(business_id, user_id)
        batches, total = await self.batch_repo.list_batches(
            business_id, inventory_location_id, product_id, variant_id, expired_only, page, page_size,
        )
        items = []
        for b in batches:
            balance = await self.balance_repo.get_balance(business_id, b.inventory_location_id, b.id)
            remaining = balance.quantity if balance else Decimal("0")
            items.append(InventoryBatchResponse.from_db(b, remaining=remaining))
        return InventoryBatchListResponse(items=items, page=page, page_size=page_size, total=total)

    async def update_batch_dates(
        self, business_id: str, user_id: str, batch_id: str,
        manufacture_date: Optional[date] = None,
        expiry_date: Optional[date] = None,
    ) -> InventoryBatchResponse:
        await self._validate_access(business_id, user_id, [BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN])
        batch = await self.batch_repo.get_batch(batch_id, business_id)
        if not batch:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Batch not found")
        eff_mfg = manufacture_date if manufacture_date is not None else batch.manufacture_date
        eff_exp = expiry_date if expiry_date is not None else batch.expiry_date
        if eff_exp and eff_mfg and eff_exp < eff_mfg:
            raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Expiry date must be after manufacture date")
        updated = await self.batch_repo.update_batch_dates(batch_id, business_id, manufacture_date, expiry_date)
        balance = await self.balance_repo.get_balance(business_id, updated.inventory_location_id, batch_id)
        remaining = balance.quantity if balance else Decimal("0")
        return InventoryBatchResponse.from_db(updated, remaining=remaining)

    # ── FEFO ──────────────────────────────────────────────────────────────

    async def get_fefo_candidates(
        self, business_id: str, user_id: str,
        inventory_location_id: str, product_id: str,
        variant_id: Optional[str] = None,
    ) -> FEFOCandidateListResponse:
        await self._validate_access(business_id, user_id)
        balances = await self.balance_repo.list_balances_for_product(
            business_id, inventory_location_id, product_id, variant_id,
        )
        today = date.today()
        candidates = []
        for bal in balances:
            batch = await self.batch_repo.get_batch(bal.batch_id, business_id)
            if not batch:
                continue
            is_expired = batch.expiry_date is not None and batch.expiry_date < today
            if bal.quantity <= Decimal("0"):
                continue
            candidates.append(FEFOCandidate(
                batch_id=batch.id,
                batch_number=batch.batch_number,
                expiry_date=batch.expiry_date,
                available_quantity=bal.quantity,
                is_expired=is_expired,
            ))
        candidates.sort(key=lambda c: (c.expiry_date or date.max, c.batch_number))
        return FEFOCandidateListResponse(candidates=candidates)

    # ── Core batch stock mutation (called by integration services) ───────

    async def record_batch_inbound(
        self, business_id: str, inventory_location_id: str,
        product_id: str, variant_id: Optional[str],
        batch_number: str, quantity: Decimal,
        manufacture_date: Optional[date], expiry_date: Optional[date],
        stock_movement_id: str,
    ) -> tuple[InventoryBatchInDB, BatchStockBalanceInDB]:
        batch = await self.batch_repo.get_batch_by_identity(
            business_id, inventory_location_id, product_id, variant_id, batch_number,
        )
        if not batch:
            batch = await self.batch_repo.create_batch(
                business_id, inventory_location_id, product_id, variant_id,
                batch_number, manufacture_date, expiry_date,
            )
        balance = await self.balance_repo.upsert_balance(
            business_id, inventory_location_id, batch.id,
            product_id, variant_id, quantity,
        )
        await self.movement_repo.create_movement(
            business_id, stock_movement_id, batch.id,
            inventory_location_id, product_id, variant_id,
            quantity, "IN",
        )
        return batch, balance

    async def record_batch_outbound(
        self, business_id: str, inventory_location_id: str,
        product_id: str, variant_id: Optional[str],
        batch_id: str, quantity: Decimal,
        stock_movement_id: str,
    ) -> BatchStockBalanceInDB:
        balance = await self.balance_repo.get_balance_for_update(
            business_id, inventory_location_id, batch_id,
        )
        if not balance or balance.quantity < quantity:
            raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail="Insufficient batch stock")
        balance = await self.balance_repo.upsert_balance(
            business_id, inventory_location_id, batch_id,
            product_id, variant_id, -quantity,
        )
        await self.movement_repo.create_movement(
            business_id, stock_movement_id, batch_id,
            inventory_location_id, product_id, variant_id,
            quantity, "OUT",
        )
        return balance

    async def _get_fefo_candidates_internal(
        self, business_id: str,
        inventory_location_id: str, product_id: str,
        variant_id: Optional[str] = None,
    ) -> FEFOCandidateListResponse:
        """Internal FEFO candidate lookup without auth validation."""
        balances = await self.balance_repo.list_balances_for_product(
            business_id, inventory_location_id, product_id, variant_id,
        )
        today = date.today()
        candidates = []
        for bal in balances:
            batch = await self.batch_repo.get_batch(bal.batch_id, business_id)
            if not batch:
                continue
            is_expired = batch.expiry_date is not None and batch.expiry_date < today
            if bal.quantity <= Decimal("0"):
                continue
            candidates.append(FEFOCandidate(
                batch_id=batch.id,
                batch_number=batch.batch_number,
                expiry_date=batch.expiry_date,
                available_quantity=bal.quantity,
                is_expired=is_expired,
            ))
        candidates.sort(key=lambda c: (c.expiry_date or date.max, c.batch_number))
        return FEFOCandidateListResponse(candidates=candidates)

    async def allocate_fefo_outbound(
        self, business_id: str, inventory_location_id: str,
        product_id: str, variant_id: Optional[str],
        total_quantity: Decimal,
        stock_movement_id: str,
        allow_expired_override: bool = False,
        override_reason: Optional[str] = None,
    ) -> List[dict]:
        candidates_resp = await self._get_fefo_candidates_internal(
            business_id, inventory_location_id, product_id, variant_id,
        )
        today = date.today()
        eligible = [c for c in candidates_resp.candidates if not c.is_expired or allow_expired_override]
        if not eligible:
            raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail="No eligible batches for allocation")
        remaining = total_quantity
        allocations = []
        for c in eligible:
            if remaining <= Decimal("0"):
                break
            alloc_qty = min(c.available_quantity, remaining)
            await self.record_batch_outbound(
                business_id, inventory_location_id, product_id, variant_id,
                c.batch_id, alloc_qty, stock_movement_id,
            )
            allocations.append({"batch_id": c.batch_id, "batch_number": c.batch_number, "quantity": alloc_qty})
            remaining -= alloc_qty
        if remaining > Decimal("0"):
            raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=f"Insufficient batch stock, {remaining} units unallocated")
        return allocations

    async def record_batch_adjustment(
        self, business_id: str, inventory_location_id: str,
        product_id: str, variant_id: Optional[str],
        batch_id: str, delta: Decimal,
        stock_movement_id: str,
    ) -> BatchStockBalanceInDB:
        balance = await self.balance_repo.get_balance_for_update(
            business_id, inventory_location_id, batch_id,
        )
        if not balance:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Batch balance not found")
        if balance.quantity + delta < Decimal("0"):
            raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail="Batch adjustment would result in negative balance")
        balance = await self.balance_repo.upsert_balance(
            business_id, inventory_location_id, batch_id,
            product_id, variant_id, delta,
        )
        direction = "IN" if delta > Decimal("0") else "OUT"
        await self.movement_repo.create_movement(
            business_id, stock_movement_id, batch_id,
            inventory_location_id, product_id, variant_id,
            abs(delta), direction,
        )
        return balance

    async def get_batch_ledger(
        self, business_id: str, user_id: str, batch_id: str,
    ) -> dict:
        await self._validate_access(business_id, user_id)
        batch = await self.batch_repo.get_batch(batch_id, business_id)
        if not batch:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Batch not found")
        balance = await self.balance_repo.get_balance(business_id, batch.inventory_location_id, batch_id)
        movements = await self.movement_repo.list_movements_for_batch(batch_id, business_id)
        return {"batch": batch, "balance": balance, "movements": movements}

    # ── Aggregate invariant check ─────────────────────────────────────────

    async def validate_batch_aggregate_invariant(
        self, business_id: str, inventory_location_id: str,
        product_id: str, variant_id: Optional[str],
        aggregate_quantity: Optional[Decimal] = None,
    ) -> bool:
        batch_balances = await self.balance_repo.list_balances_for_product(
            business_id, inventory_location_id, product_id, variant_id,
        )
        total_batch_qty = sum(b.quantity for b in batch_balances)
        if aggregate_quantity is None:
            aggregate_quantity = total_batch_qty
        if total_batch_qty != aggregate_quantity:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=f"BATCH_AGGREGATE_INVARIANT_VIOLATION: SUM(batch_stock_balances)={total_batch_qty} != StockBalance.quantity={aggregate_quantity} for product {product_id}.",
            )
        return True

    async def has_batch_balances(
        self, business_id: str, inventory_location_id: str,
        product_id: str, variant_id: Optional[str],
    ) -> bool:
        batch_balances = await self.balance_repo.list_balances_for_product(
            business_id, inventory_location_id, product_id, variant_id,
        )
        return len(batch_balances) > 0

    async def get_batch_balance_quantity(
        self, business_id: str, inventory_location_id: str,
        batch_id: str,
    ) -> Decimal:
        balance = await self.balance_repo.get_balance(business_id, inventory_location_id, batch_id)
        return balance.quantity if balance else Decimal("0")

    async def list_batch_balances(
        self, business_id: str, inventory_location_id: str,
        product_id: str, variant_id: Optional[str],
    ) -> List:
        return await self.balance_repo.list_balances_for_product(
            business_id, inventory_location_id, product_id, variant_id,
        )


inventory_batch_service = InventoryBatchService()

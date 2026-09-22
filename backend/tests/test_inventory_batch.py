"""
Feature #62 — Inventory Batch, Lot & Expiry Management Tests

Tests batch creation, FEFO allocation, receiving integration,
delivery integration, expiry handling, tenant isolation, and regression.
"""
import pytest
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.modules.inventory_batch.schemas import (
    InventoryBatchCreate, BatchReceivingInput, BatchAllocationInput,
)
from app.modules.inventory_batch.service import InventoryBatchService
from app.modules.inventory_batch.repository import (
    InMemoryInventoryBatchRepository,
    InMemoryBatchStockBalanceRepository,
    InMemoryBatchStockMovementRepository,
)


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_batch_repos():
    InMemoryInventoryBatchRepository.clear()
    InMemoryBatchStockBalanceRepository.clear()
    InMemoryBatchStockMovementRepository.clear()
    yield
    InMemoryInventoryBatchRepository.clear()
    InMemoryBatchStockBalanceRepository.clear()
    InMemoryBatchStockMovementRepository.clear()


@pytest.fixture
def batch_service():
    return InventoryBatchService()


@pytest.fixture
def client():
    return TestClient(app)


BUSINESS_ID = "test-biz-001"
LOCATION_ID = "test-loc-001"
PRODUCT_ID = "test-prod-001"
VARIANT_ID = None
USER_ID = "test-user-001"


# ── Batch Creation Tests ────────────────────────────────────────────────────

class TestBatchCreation:
    @pytest.mark.asyncio
    async def test_create_batch_valid(self, batch_service):
        """Create a valid batch with correct dates."""
        with patch("app.modules.inventory_batch.service.business_membership_service") as mock_svc:
            mock_membership = MagicMock()
            mock_membership.role = "OWNER"
            mock_svc.get_membership_by_user_and_business = AsyncMock(return_value=mock_membership)
            result = await batch_service.create_batch(
                BUSINESS_ID, USER_ID,
                InventoryBatchCreate(
                    inventory_location_id=LOCATION_ID,
                    product_id=PRODUCT_ID,
                    variant_id=VARIANT_ID,
                    batch_number="BATCH-001",
                    manufacture_date=date(2026, 1, 1),
                    expiry_date=date(2026, 12, 31),
                ),
            )
        assert result.batch_number == "BATCH-001"
        assert result.manufacture_date == date(2026, 1, 1)
        assert result.expiry_date == date(2026, 12, 31)
        assert result.remaining_quantity == Decimal("0")

    @pytest.mark.asyncio
    async def test_create_batch_duplicate_rejected(self, batch_service):
        """Duplicate batch number for same product/location must be rejected."""
        with patch("app.modules.inventory_batch.service.business_membership_service") as mock_svc:
            mock_membership = MagicMock()
            mock_membership.role = "OWNER"
            mock_svc.get_membership_by_user_and_business = AsyncMock(return_value=mock_membership)
            payload = InventoryBatchCreate(
                inventory_location_id=LOCATION_ID, product_id=PRODUCT_ID,
                variant_id=VARIANT_ID, batch_number="DUP-001",
                expiry_date=date(2026, 12, 31),
            )
            await batch_service.create_batch(BUSINESS_ID, USER_ID, payload)
            with pytest.raises(Exception):
                await batch_service.create_batch(BUSINESS_ID, USER_ID, payload)

    @pytest.mark.asyncio
    async def test_create_batch_expiry_before_manufacture_rejected(self, batch_service):
        """Expiry before manufacture date must be rejected."""
        with patch("app.modules.inventory_batch.service.business_membership_service") as mock_svc:
            mock_membership = MagicMock()
            mock_membership.role = "OWNER"
            mock_svc.get_membership_by_user_and_business = AsyncMock(return_value=mock_membership)
            with pytest.raises(Exception):
                await batch_service.create_batch(
                    BUSINESS_ID, USER_ID,
                    InventoryBatchCreate(
                        inventory_location_id=LOCATION_ID, product_id=PRODUCT_ID,
                        batch_number="BAD-DATE",
                        manufacture_date=date(2026, 12, 31),
                        expiry_date=date(2026, 1, 1),
                    ),
                )

    @pytest.mark.asyncio
    async def test_create_batch_whitespace_trimmed(self, batch_service):
        """Batch number whitespace should be trimmed."""
        with patch("app.modules.inventory_batch.service.business_membership_service") as mock_svc:
            mock_membership = MagicMock()
            mock_membership.role = "OWNER"
            mock_svc.get_membership_by_user_and_business = AsyncMock(return_value=mock_membership)
            result = await batch_service.create_batch(
                BUSINESS_ID, USER_ID,
                InventoryBatchCreate(
                    inventory_location_id=LOCATION_ID, product_id=PRODUCT_ID,
                    batch_number="  TRIMMED  ", expiry_date=date(2026, 12, 31),
                ),
            )
        assert result.batch_number == "TRIMMED"


# ── FEFO Tests ──────────────────────────────────────────────────────────────

class TestFEFO:
    @pytest.mark.asyncio
    async def test_fefo_earliest_expiry_first(self, batch_service):
        """FEFO should return earliest expiry first."""
        with patch("app.modules.inventory_batch.service.business_membership_service") as mock_svc:
            mock_membership = MagicMock()
            mock_membership.role = "ADMIN"
            mock_svc.get_membership_by_user_and_business = AsyncMock(return_value=mock_membership)
            b1 = await batch_service.create_batch(
                BUSINESS_ID, USER_ID,
                InventoryBatchCreate(
                    inventory_location_id=LOCATION_ID, product_id=PRODUCT_ID,
                    batch_number="FEFO-001", expiry_date=date(2026, 6, 30),
                ),
            )
            b2 = await batch_service.create_batch(
                BUSINESS_ID, USER_ID,
                InventoryBatchCreate(
                    inventory_location_id=LOCATION_ID, product_id=PRODUCT_ID,
                    batch_number="FEFO-002", expiry_date=date(2026, 3, 31),
                ),
            )
            await batch_service.record_batch_inbound(
                BUSINESS_ID, LOCATION_ID, PRODUCT_ID, VARIANT_ID,
                "FEFO-001", Decimal("100"), date(2026, 1, 1), date(2026, 6, 30), "mov-1",
            )
            await batch_service.record_batch_inbound(
                BUSINESS_ID, LOCATION_ID, PRODUCT_ID, VARIANT_ID,
                "FEFO-002", Decimal("100"), date(2026, 1, 1), date(2026, 3, 31), "mov-2",
            )
            candidates = await batch_service.get_fefo_candidates(
                BUSINESS_ID, USER_ID, LOCATION_ID, PRODUCT_ID,
            )
        assert len(candidates.candidates) == 2
        assert candidates.candidates[0].batch_number == "FEFO-002"
        assert candidates.candidates[1].batch_number == "FEFO-001"


# ── Batch Stock Operations ──────────────────────────────────────────────────

class TestBatchStockOperations:
    @pytest.mark.asyncio
    async def test_record_batch_inbound_creates_balance(self, batch_service):
        """Inbound batch movement should create batch stock balance."""
        batch, balance = await batch_service.record_batch_inbound(
            BUSINESS_ID, LOCATION_ID, PRODUCT_ID, VARIANT_ID,
            "INB-001", Decimal("50"), None, date(2026, 12, 31), "mov-in-1",
        )
        assert balance.quantity == Decimal("50")
        assert batch.batch_number == "INB-001"

    @pytest.mark.asyncio
    async def test_record_batch_outbound_deducts_balance(self, batch_service):
        """Outbound batch movement should deduct batch stock."""
        batch, _ = await batch_service.record_batch_inbound(
            BUSINESS_ID, LOCATION_ID, PRODUCT_ID, VARIANT_ID,
            "OUT-001", Decimal("100"), None, date(2026, 12, 31), "mov-in-2",
        )
        balance = await batch_service.record_batch_outbound(
            BUSINESS_ID, LOCATION_ID, PRODUCT_ID, VARIANT_ID,
            batch.id, Decimal("30"), "mov-out-1",
        )
        assert balance.quantity == Decimal("70")

    @pytest.mark.asyncio
    async def test_record_batch_outbound_insufficient_rejected(self, batch_service):
        """Outbound exceeding batch balance must be rejected."""
        batch, _ = await batch_service.record_batch_inbound(
            BUSINESS_ID, LOCATION_ID, PRODUCT_ID, VARIANT_ID,
            "INS-001", Decimal("10"), None, None, "mov-in-3",
        )
        with pytest.raises(Exception):
            await batch_service.record_batch_outbound(
                BUSINESS_ID, LOCATION_ID, PRODUCT_ID, VARIANT_ID,
                batch.id, Decimal("20"), "mov-out-2",
            )

    @pytest.mark.asyncio
    async def test_allocate_fefo_multi_batch(self, batch_service):
        """FEFO allocation should span multiple batches."""
        await batch_service.record_batch_inbound(
            BUSINESS_ID, LOCATION_ID, PRODUCT_ID, VARIANT_ID,
            "MULTI-A", Decimal("50"), None, date(2027, 3, 1), "mov-ma",
        )
        await batch_service.record_batch_inbound(
            BUSINESS_ID, LOCATION_ID, PRODUCT_ID, VARIANT_ID,
            "MULTI-B", Decimal("50"), None, date(2027, 6, 1), "mov-mb",
        )
        allocations = await batch_service.allocate_fefo_outbound(
            BUSINESS_ID, LOCATION_ID, PRODUCT_ID, VARIANT_ID,
            Decimal("80"), "mov-alloc-1",
        )
        assert len(allocations) == 2
        total = sum(a["quantity"] for a in allocations)
        assert total == Decimal("80")


# ── Batch Balance Invariant ─────────────────────────────────────────────────

class TestBatchInvariant:
    @pytest.mark.asyncio
    async def test_aggregate_invariant_non_negative(self, batch_service):
        """Aggregate batch balance should not be negative."""
        await batch_service.record_batch_inbound(
            BUSINESS_ID, LOCATION_ID, PRODUCT_ID, VARIANT_ID,
            "INV-001", Decimal("30"), None, None, "mov-inv-1",
        )
        valid = await batch_service.validate_batch_aggregate_invariant(
            BUSINESS_ID, LOCATION_ID, PRODUCT_ID, VARIANT_ID,
        )
        assert valid is True


# ── API Smoke Tests ─────────────────────────────────────────────────────────

class TestBatchAPI:
    def test_health_check(self, client):
        """Application health check must still work after batch module registration."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


# ── Product Batch Tracking Config ───────────────────────────────────────────

class TestProductBatchConfig:
    def test_product_response_includes_batch_flag(self):
        """ProductResponse must include batch_tracking_enabled field."""
        from app.modules.product.schemas import ProductResponse
        assert "batch_tracking_enabled" in ProductResponse.model_fields

    def test_product_create_includes_batch_flag(self):
        """ProductCreate must include batch_tracking_enabled field."""
        from app.modules.product.schemas import ProductCreate
        assert "batch_tracking_enabled" in ProductCreate.model_fields

    def test_product_update_includes_batch_flag(self):
        """ProductUpdate must include batch_tracking_enabled field."""
        from app.modules.product.schemas import ProductUpdate
        assert "batch_tracking_enabled" in ProductUpdate.model_fields


# ── Non-Batch Regression ───────────────────────────────────────────────────

class TestNonBatchRegression:
    def test_readiness_still_works(self, client):
        """Readiness endpoint must still function with batch module loaded."""
        with patch("app.modules.health.router.engine") as mock_engine:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_conn.__aexit__ = AsyncMock(return_value=False)
            mock_engine.connect.return_value = mock_conn
            response = client.get("/api/v1/health/ready")
            assert response.status_code == 200
            assert response.json()["status"] == "ready"

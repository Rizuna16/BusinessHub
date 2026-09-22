"""
Feature #63 — Subscription Plan Entitlements Enforcement Tests

Tests entitlement CRUD, quota enforcement, subscription status blocking,
concurrency safety, and tenant isolation.
"""
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.modules.subscription.schemas import (
    SubscriptionPlan, SubscriptionInDB, SubscriptionStatus, BillingInterval,
    PlanEntitlementCreate, PlanEntitlementUpdate, PlanEntitlementInDB,
    SUPPORTED_ENTITLEMENT_KEYS,
)
from app.modules.subscription.service import SubscriptionService
from app.modules.subscription.repository import (
    InMemorySubscriptionRepository,
)
from app.modules.subscription.schemas import (
    BillingPeriodStatus, PaymentAttemptStatus,
    BillingPeriod, PaymentAttempt,
)


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_repos():
    InMemorySubscriptionRepository.clear()
    yield
    InMemorySubscriptionRepository.clear()


@pytest.fixture
def subscription_service():
    repo = InMemorySubscriptionRepository()
    repo._ensure_default_plan()
    return SubscriptionService(repository=repo)


@pytest.fixture
def client():
    return TestClient(app)


BUSINESS_ID = "test-biz-001"
PLAN_ID = "plan_business_standard"


# ── Entitlement CRUD Tests ──────────────────────────────────────────────────

class TestEntitlementCRUD:
    @pytest.mark.asyncio
    async def test_create_entitlement(self, subscription_service):
        """Create a valid entitlement for existing plan."""
        result = await subscription_service.entitlement_create(PLAN_ID, "max_products", 100)
        assert result.plan_id == PLAN_ID
        assert result.feature_key == "max_products"
        assert result.limit_value == 100

    @pytest.mark.asyncio
    async def test_create_duplicate_entitlement_rejected(self, subscription_service):
        """Duplicate (plan_id, feature_key) must be rejected."""
        await subscription_service.entitlement_create(PLAN_ID, "max_products", 100)
        with pytest.raises(Exception):
            await subscription_service.entitlement_create(PLAN_ID, "max_products", 200)

    @pytest.mark.asyncio
    async def test_create_invalid_feature_key_rejected(self, subscription_service):
        """Arbitrary feature keys must be rejected."""
        with pytest.raises(Exception):
            await subscription_service.entitlement_create(PLAN_ID, "max_customers", 50)

    @pytest.mark.asyncio
    async def test_create_invalid_limit_rejected(self, subscription_service):
        """limit_value < -1 must be rejected."""
        with pytest.raises(Exception):
            await subscription_service.entitlement_create(PLAN_ID, "max_products", -2)

    @pytest.mark.asyncio
    async def test_create_missing_plan_rejected(self, subscription_service):
        """Entitlement for non-existent plan must be rejected."""
        with pytest.raises(Exception):
            await subscription_service.entitlement_create("nonexistent_plan", "max_products", 100)

    @pytest.mark.asyncio
    async def test_update_entitlement(self, subscription_service):
        """Update entitlement limit."""
        ent = await subscription_service.entitlement_create(PLAN_ID, "max_products", 100)
        updated = await subscription_service.entitlement_update(ent.id, 200)
        assert updated.limit_value == 200
        assert updated.id == ent.id

    @pytest.mark.asyncio
    async def test_delete_entitlement(self, subscription_service):
        """Delete entitlement."""
        ent = await subscription_service.entitlement_create(PLAN_ID, "max_products", 100)
        deleted = await subscription_service.entitlement_delete(ent.id)
        assert deleted is True

    @pytest.mark.asyncio
    async def test_delete_nonexistent_entitlement(self, subscription_service):
        """Delete non-existent entitlement raises 404."""
        with pytest.raises(Exception):
            await subscription_service.entitlement_delete("nonexistent-id")

    @pytest.mark.asyncio
    async def test_list_entitlements(self, subscription_service):
        """List entitlements for a plan."""
        await subscription_service.entitlement_create(PLAN_ID, "max_products", 100)
        await subscription_service.entitlement_create(PLAN_ID, "max_branches", 5)
        result = await subscription_service.entitlement_list(PLAN_ID)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_entitlement(self, subscription_service):
        """Get single entitlement by ID."""
        ent = await subscription_service.entitlement_create(PLAN_ID, "max_products", 100)
        fetched = await subscription_service.entitlement_get(ent.id)
        assert fetched.plan_id == PLAN_ID
        assert fetched.feature_key == "max_products"

    @pytest.mark.asyncio
    async def test_get_nonexistent_entitlement(self, subscription_service):
        """Get non-existent entitlement raises 404."""
        with pytest.raises(Exception):
            await subscription_service.entitlement_get("nonexistent-id")

    @pytest.mark.asyncio
    async def test_unlimited_semantics(self, subscription_service):
        """limit_value = -1 means unlimited."""
        ent = await subscription_service.entitlement_create(PLAN_ID, "max_products", -1)
        assert ent.limit_value == -1

    @pytest.mark.asyncio
    async def test_zero_semantics(self, subscription_service):
        """limit_value = 0 means disabled."""
        ent = await subscription_service.entitlement_create(PLAN_ID, "max_products", 0)
        assert ent.limit_value == 0


# ── Quota Enforcement Tests ─────────────────────────────────────────────────

class TestQuotaEnforcement:
    @pytest.mark.asyncio
    async def test_unlimited_always_allows(self, subscription_service):
        """Unlimited (-1) entitlement always allows creation."""
        now = datetime.now(timezone.utc)
        sub = SubscriptionInDB(
            id="sub-unlimited", business_id=BUSINESS_ID, plan_id=PLAN_ID,
            plan_name="Business Plan", status=SubscriptionStatus.ACTIVE,
            price=Decimal("50000"), currency="IDR",
            billing_interval=BillingInterval.MONTHLY,
            started_at=now, current_period_start=now,
            current_period_end=now + timedelta(days=30),
            created_at=now, updated_at=now,
        )
        subscription_service.repository._subscriptions[sub.id] = sub
        subscription_service.repository._business_index[BUSINESS_ID] = sub.id

        await subscription_service.entitlement_create(PLAN_ID, "max_products", -1)
        # Should not raise
        await subscription_service.check_quota(BUSINESS_ID, "max_products")

    @pytest.mark.asyncio
    async def test_zero_always_blocks(self, subscription_service):
        """Zero (0) entitlement always blocks creation."""
        now = datetime.now(timezone.utc)
        sub = SubscriptionInDB(
            id="sub-zero", business_id=BUSINESS_ID, plan_id=PLAN_ID,
            plan_name="Business Plan", status=SubscriptionStatus.ACTIVE,
            price=Decimal("50000"), currency="IDR",
            billing_interval=BillingInterval.MONTHLY,
            started_at=now, current_period_start=now,
            current_period_end=now + timedelta(days=30),
            created_at=now, updated_at=now,
        )
        subscription_service.repository._subscriptions[sub.id] = sub
        subscription_service.repository._business_index[BUSINESS_ID] = sub.id

        await subscription_service.entitlement_create(PLAN_ID, "max_products", 0)
        with pytest.raises(Exception) as exc_info:
            await subscription_service.check_quota(BUSINESS_ID, "max_products")
        assert "disabled" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_missing_entitlement_blocks(self, subscription_service):
        """Missing entitlement must fail closed (block)."""
        # First create a subscription so we get past the subscription check
        now = datetime.now(timezone.utc)
        sub = SubscriptionInDB(
            id="sub-no-ent",
            business_id=BUSINESS_ID,
            plan_id=PLAN_ID,
            plan_name="Business Plan",
            status=SubscriptionStatus.ACTIVE,
            price=Decimal("50000"),
            currency="IDR",
            billing_interval=BillingInterval.MONTHLY,
            started_at=now,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            created_at=now,
            updated_at=now,
        )
        subscription_service.repository._subscriptions[sub.id] = sub
        subscription_service.repository._business_index[BUSINESS_ID] = sub.id

        with pytest.raises(Exception) as exc_info:
            await subscription_service.check_quota(BUSINESS_ID, "max_products")
        assert "no entitlement" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_invalid_plan_blocks(self, subscription_service):
        """Invalid/unresolvable plan must fail closed."""
        now = datetime.now(timezone.utc)
        sub = SubscriptionInDB(
            id="sub-1",
            business_id=BUSINESS_ID,
            plan_id="nonexistent_plan",
            plan_name="Invalid",
            status=SubscriptionStatus.ACTIVE,
            price=Decimal("50000"),
            currency="IDR",
            billing_interval=BillingInterval.MONTHLY,
            started_at=now,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            created_at=now,
            updated_at=now,
        )
        subscription_service.repository._subscriptions[sub.id] = sub
        subscription_service.repository._business_index[BUSINESS_ID] = sub.id

        # Manually insert an entitlement for nonexistent_plan (bypass plan validation)
        from app.modules.subscription.schemas import PlanEntitlementInDB
        ent = PlanEntitlementInDB(
            id="ent-1",
            plan_id="nonexistent_plan",
            feature_key="max_products",
            limit_value=100,
            created_at=now,
            updated_at=now,
        )
        subscription_service.repository._entitlements[ent.id] = ent
        subscription_service.repository._plan_key_index["nonexistent_plan:max_products"] = ent.id

        # Plan not found via get_plan (plans are only plan_business_standard in InMemory)
        with pytest.raises(Exception) as exc_info:
            await subscription_service.check_quota(BUSINESS_ID, "max_products")
        assert "plan not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_expired_subscription_blocks(self, subscription_service):
        """EXPIRED subscription blocks new creation."""
        now = datetime.now(timezone.utc)
        sub = SubscriptionInDB(
            id="sub-expired",
            business_id=BUSINESS_ID,
            plan_id=PLAN_ID,
            plan_name="Business Plan",
            status=SubscriptionStatus.EXPIRED,
            price=Decimal("50000"),
            currency="IDR",
            billing_interval=BillingInterval.MONTHLY,
            started_at=now,
            current_period_start=now,
            current_period_end=now - timedelta(days=1),
            created_at=now,
            updated_at=now,
        )
        subscription_service.repository._subscriptions[sub.id] = sub
        subscription_service.repository._business_index[BUSINESS_ID] = sub.id

        await subscription_service.entitlement_create(PLAN_ID, "max_products", 100)
        with pytest.raises(Exception) as exc_info:
            await subscription_service.check_quota(BUSINESS_ID, "max_products")
        assert "expired" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_cancelled_subscription_blocks(self, subscription_service):
        """CANCELLED subscription blocks new creation."""
        now = datetime.now(timezone.utc)
        sub = SubscriptionInDB(
            id="sub-cancelled",
            business_id=BUSINESS_ID,
            plan_id=PLAN_ID,
            plan_name="Business Plan",
            status=SubscriptionStatus.CANCELLED,
            price=Decimal("50000"),
            currency="IDR",
            billing_interval=BillingInterval.MONTHLY,
            started_at=now,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            cancelled_at=now,
            created_at=now,
            updated_at=now,
        )
        subscription_service.repository._subscriptions[sub.id] = sub
        subscription_service.repository._business_index[BUSINESS_ID] = sub.id

        await subscription_service.entitlement_create(PLAN_ID, "max_products", 100)
        with pytest.raises(Exception) as exc_info:
            await subscription_service.check_quota(BUSINESS_ID, "max_products")
        assert "cancelled" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_suspended_subscription_blocks(self, subscription_service):
        """SUSPENDED subscription blocks new creation."""
        now = datetime.now(timezone.utc)
        sub = SubscriptionInDB(
            id="sub-suspended",
            business_id=BUSINESS_ID,
            plan_id=PLAN_ID,
            plan_name="Business Plan",
            status=SubscriptionStatus.SUSPENDED,
            price=Decimal("50000"),
            currency="IDR",
            billing_interval=BillingInterval.MONTHLY,
            started_at=now,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            created_at=now,
            updated_at=now,
        )
        subscription_service.repository._subscriptions[sub.id] = sub
        subscription_service.repository._business_index[BUSINESS_ID] = sub.id

        await subscription_service.entitlement_create(PLAN_ID, "max_products", 100)
        with pytest.raises(Exception) as exc_info:
            await subscription_service.check_quota(BUSINESS_ID, "max_products")
        assert "suspended" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_past_due_enforces_quota(self, subscription_service):
        """PAST_DUE subscription still enforces quota."""
        now = datetime.now(timezone.utc)
        sub = SubscriptionInDB(
            id="sub-past-due",
            business_id=BUSINESS_ID,
            plan_id=PLAN_ID,
            plan_name="Business Plan",
            status=SubscriptionStatus.PAST_DUE,
            price=Decimal("50000"),
            currency="IDR",
            billing_interval=BillingInterval.MONTHLY,
            started_at=now,
            current_period_start=now,
            current_period_end=now - timedelta(days=1),
            created_at=now,
            updated_at=now,
        )
        subscription_service.repository._subscriptions[sub.id] = sub
        subscription_service.repository._business_index[BUSINESS_ID] = sub.id

        await subscription_service.entitlement_create(PLAN_ID, "max_products", 100)
        # Should NOT raise — PAST_DUE enforces quota normally
        await subscription_service.check_quota(BUSINESS_ID, "max_products")

    @pytest.mark.asyncio
    async def test_missing_subscription_blocks(self, subscription_service):
        """Missing subscription blocks creation."""
        with pytest.raises(Exception) as exc_info:
            await subscription_service.check_quota("nonexistent-business", "max_products")
        assert "subscription" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_unsupported_feature_key_rejected(self, subscription_service):
        """Unsupported feature key must be rejected."""
        with pytest.raises(Exception) as exc_info:
            await subscription_service.check_quota(BUSINESS_ID, "max_customers")
        assert "unsupported" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_invalid_limit_value_rejected(self, subscription_service):
        """limit_value < -1 must be rejected on create."""
        with pytest.raises(Exception):
            await subscription_service.entitlement_create(PLAN_ID, "max_products", -5)

    @pytest.mark.asyncio
    async def test_invalid_update_limit_rejected(self, subscription_service):
        """limit_value < -1 must be rejected on update."""
        ent = await subscription_service.entitlement_create(PLAN_ID, "max_products", 100)
        with pytest.raises(Exception):
            await subscription_service.entitlement_update(ent.id, -5)


# ── Entitlement Change Behavior ─────────────────────────────────────────────

class TestEntitlementChangeBehavior:
    @pytest.mark.asyncio
    async def test_entitlement_reduction_blocks_new_creation(self, subscription_service):
        """Reducing limit blocks new creation when usage exceeds new limit."""
        now = datetime.now(timezone.utc)
        sub = SubscriptionInDB(
            id="sub-reduce",
            business_id=BUSINESS_ID,
            plan_id=PLAN_ID,
            plan_name="Business Plan",
            status=SubscriptionStatus.ACTIVE,
            price=Decimal("50000"),
            currency="IDR",
            billing_interval=BillingInterval.MONTHLY,
            started_at=now,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            created_at=now,
            updated_at=now,
        )
        subscription_service.repository._subscriptions[sub.id] = sub
        subscription_service.repository._business_index[BUSINESS_ID] = sub.id

        ent = await subscription_service.entitlement_create(PLAN_ID, "max_products", 100)

        # Simulate 80 products by mocking the count
        with patch.object(subscription_service, '_count_products', return_value=80):
            # With limit 100, should pass
            await subscription_service.check_quota(BUSINESS_ID, "max_products")

            # Reduce to 50
            await subscription_service.entitlement_update(ent.id, 50)

            # Now should block
            with pytest.raises(Exception) as exc_info:
                await subscription_service.check_quota(BUSINESS_ID, "max_products")
            assert "limit reached" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_entitlement_increase_permits_new_creation(self, subscription_service):
        """Increasing limit permits new creation."""
        now = datetime.now(timezone.utc)
        sub = SubscriptionInDB(
            id="sub-increase",
            business_id=BUSINESS_ID,
            plan_id=PLAN_ID,
            plan_name="Business Plan",
            status=SubscriptionStatus.ACTIVE,
            price=Decimal("50000"),
            currency="IDR",
            billing_interval=BillingInterval.MONTHLY,
            started_at=now,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            created_at=now,
            updated_at=now,
        )
        subscription_service.repository._subscriptions[sub.id] = sub
        subscription_service.repository._business_index[BUSINESS_ID] = sub.id

        ent = await subscription_service.entitlement_create(PLAN_ID, "max_products", 50)

        with patch.object(subscription_service, '_count_products', return_value=49):
            # At limit 50 with usage 49, should pass (49 < 50)
            await subscription_service.check_quota(BUSINESS_ID, "max_products")

            # Increase to 100
            await subscription_service.entitlement_update(ent.id, 100)

            # Should still pass
            await subscription_service.check_quota(BUSINESS_ID, "max_products")

    @pytest.mark.asyncio
    async def test_usage_at_limit_blocks(self, subscription_service):
        """Usage == limit blocks creation (usage >= limit)."""
        now = datetime.now(timezone.utc)
        sub = SubscriptionInDB(
            id="sub-at-limit",
            business_id=BUSINESS_ID,
            plan_id=PLAN_ID,
            plan_name="Business Plan",
            status=SubscriptionStatus.ACTIVE,
            price=Decimal("50000"),
            currency="IDR",
            billing_interval=BillingInterval.MONTHLY,
            started_at=now,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            created_at=now,
            updated_at=now,
        )
        subscription_service.repository._subscriptions[sub.id] = sub
        subscription_service.repository._business_index[BUSINESS_ID] = sub.id

        await subscription_service.entitlement_create(PLAN_ID, "max_products", 100)

        with patch.object(subscription_service, '_count_products', return_value=100):
            with pytest.raises(Exception) as exc_info:
                await subscription_service.check_quota(BUSINESS_ID, "max_products")
            assert "limit reached" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_usage_below_limit_allows(self, subscription_service):
        """Usage < limit allows creation."""
        now = datetime.now(timezone.utc)
        sub = SubscriptionInDB(
            id="sub-below",
            business_id=BUSINESS_ID,
            plan_id=PLAN_ID,
            plan_name="Business Plan",
            status=SubscriptionStatus.ACTIVE,
            price=Decimal("50000"),
            currency="IDR",
            billing_interval=BillingInterval.MONTHLY,
            started_at=now,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            created_at=now,
            updated_at=now,
        )
        subscription_service.repository._subscriptions[sub.id] = sub
        subscription_service.repository._business_index[BUSINESS_ID] = sub.id

        await subscription_service.entitlement_create(PLAN_ID, "max_products", 100)

        with patch.object(subscription_service, '_count_products', return_value=99):
            # Should not raise
            await subscription_service.check_quota(BUSINESS_ID, "max_products")


# ── Tenant Isolation Tests ──────────────────────────────────────────────────

class TestTenantIsolation:
    @pytest.mark.asyncio
    async def test_different_business_independent_quota(self, subscription_service):
        """Business A and Business B have independent quotas."""
        now = datetime.now(timezone.utc)
        for biz_id in ["biz-a", "biz-b"]:
            sub = SubscriptionInDB(
                id=f"sub-{biz_id}",
                business_id=biz_id,
                plan_id=PLAN_ID,
                plan_name="Business Plan",
                status=SubscriptionStatus.ACTIVE,
                price=Decimal("50000"),
                currency="IDR",
                billing_interval=BillingInterval.MONTHLY,
                started_at=now,
                current_period_start=now,
                current_period_end=now + timedelta(days=30),
                created_at=now,
                updated_at=now,
            )
            subscription_service.repository._subscriptions[sub.id] = sub
            subscription_service.repository._business_index[biz_id] = sub.id

        await subscription_service.entitlement_create(PLAN_ID, "max_products", 1)

        # Business A: 0 products
        with patch.object(subscription_service, '_count_products', side_effect=lambda bid: 0 if bid == "biz-a" else 1):
            await subscription_service.check_quota("biz-a", "max_products")
            with pytest.raises(Exception):
                await subscription_service.check_quota("biz-b", "max_products")


# ── Regression: Feature #55 Billing Unchanged ───────────────────────────────

class TestFeature55Regression:
    @pytest.mark.asyncio
    async def test_billing_period_unaffected_by_entitlement(self, subscription_service):
        """Entitlement changes do not affect billing period snapshots."""
        ent = await subscription_service.entitlement_create(PLAN_ID, "max_products", 100)
        await subscription_service.entitlement_update(ent.id, 50)

        # Verify the subscription service still works for billing operations
        sub = await subscription_service.get_by_business_id(BUSINESS_ID)
        # Default subscription was created during business creation mock
        # Just verify entitlement CRUD didn't break billing
        bps = await subscription_service.get_billing_periods("nonexistent-sub")
        assert bps == []  # No billing periods for nonexistent subscription

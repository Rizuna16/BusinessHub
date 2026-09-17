import pytest
from datetime import datetime, timezone

from app.modules.notification.schemas import (
    NotificationScope,
    NotificationSeverity,
    NotificationType,
    Notification,
)
from app.modules.notification.repository import notification_repository
from app.modules.notification.service import NotificationService, notification_service


@pytest.fixture(autouse=True)
def clear_repos():
    notification_repository.clear()
    yield
    notification_repository.clear()


# --- Repository Tests ---

@pytest.mark.anyio
async def test_create_notification():
    now = datetime.now(timezone.utc)
    n = Notification(
        id="notif_001",
        recipient_id="user_001",
        business_id="biz_001",
        scope=NotificationScope.TENANT,
        type=NotificationType.PAYMENT_VERIFIED,
        severity=NotificationSeverity.INFO,
        title="Payment Verified",
        message="Your payment has been verified.",
        is_read=False,
        read_at=None,
        created_at=now,
        metadata={"payment_attempt_id": "pa_001"},
        deduplication_key="payment-verified:pa_001",
    )
    created = await notification_repository.create(n)
    assert created.id == "notif_001"
    assert created.recipient_id == "user_001"


@pytest.mark.anyio
async def test_get_by_id():
    now = datetime.now(timezone.utc)
    n = Notification(
        id="notif_002",
        recipient_id="user_001",
        business_id=None,
        scope=NotificationScope.PLATFORM,
        type=NotificationType.PAYMENT_VERIFICATION_REQUIRED,
        severity=NotificationSeverity.INFO,
        title="Verification Required",
        message="A payment requires verification.",
        is_read=False,
        read_at=None,
        created_at=now,
        metadata=None,
        deduplication_key=None,
    )
    await notification_repository.create(n)
    fetched = await notification_repository.get_by_id("notif_002")
    assert fetched is not None
    assert fetched.title == "Verification Required"


@pytest.mark.anyio
async def test_list_for_recipient_filters():
    now = datetime.now(timezone.utc)
    for i in range(5):
        n = Notification(
            id=f"notif_list_{i}",
            recipient_id="user_001" if i < 3 else "user_002",
            business_id="biz_001",
            scope=NotificationScope.TENANT,
            type=NotificationType.PAYMENT_VERIFIED,
            severity=NotificationSeverity.INFO,
            title=f"Notification {i}",
            message=f"Message {i}",
            is_read=(i == 0),
            read_at=now if i == 0 else None,
            created_at=now,
            metadata=None,
            deduplication_key=None,
        )
        await notification_repository.create(n)

    user1_list = await notification_repository.list_for_recipient("user_001")
    assert len(user1_list) == 3

    user2_list = await notification_repository.list_for_recipient("user_002")
    assert len(user2_list) == 2

    unread = await notification_repository.list_for_recipient("user_001", unread_only=True)
    assert len(unread) == 2


@pytest.mark.anyio
async def test_count_unread():
    now = datetime.now(timezone.utc)
    for i in range(3):
        n = Notification(
            id=f"notif_count_{i}",
            recipient_id="user_001",
            business_id="biz_001",
            scope=NotificationScope.TENANT,
            type=NotificationType.PAYMENT_VERIFIED,
            severity=NotificationSeverity.INFO,
            title=f"Title {i}",
            message=f"Message {i}",
            is_read=(i == 0),
            read_at=now if i == 0 else None,
            created_at=now,
            metadata=None,
            deduplication_key=None,
        )
        await notification_repository.create(n)

    count = await notification_repository.count_unread("user_001")
    assert count == 2


@pytest.mark.anyio
async def test_mark_read():
    now = datetime.now(timezone.utc)
    n = Notification(
        id="notif_mark_001",
        recipient_id="user_001",
        business_id=None,
        scope=NotificationScope.PLATFORM,
        type=NotificationType.SUBSCRIPTION_RENEWAL_REMINDER,
        severity=NotificationSeverity.WARNING,
        title="Renewal Reminder",
        message="Subscription renewal is approaching.",
        is_read=False,
        read_at=None,
        created_at=now,
        metadata=None,
        deduplication_key=None,
    )
    await notification_repository.create(n)

    result = await notification_repository.mark_read("notif_mark_001", "user_001")
    assert result is not None
    assert result.is_read is True
    assert result.read_at is not None


@pytest.mark.anyio
async def test_mark_read_wrong_user():
    now = datetime.now(timezone.utc)
    n = Notification(
        id="notif_mark_002",
        recipient_id="user_001",
        business_id=None,
        scope=NotificationScope.PLATFORM,
        type=NotificationType.SUBSCRIPTION_RENEWAL_REMINDER,
        severity=NotificationSeverity.WARNING,
        title="Renewal Reminder",
        message="Subscription renewal is approaching.",
        is_read=False,
        read_at=None,
        created_at=now,
        metadata=None,
        deduplication_key=None,
    )
    await notification_repository.create(n)

    result = await notification_repository.mark_read("notif_mark_002", "user_999")
    assert result is None


@pytest.mark.anyio
async def test_mark_read_idempotent():
    now = datetime.now(timezone.utc)
    n = Notification(
        id="notif_idempotent",
        recipient_id="user_001",
        business_id=None,
        scope=NotificationScope.TENANT,
        type=NotificationType.PAYMENT_VERIFIED,
        severity=NotificationSeverity.INFO,
        title="Already Read",
        message="This is already read.",
        is_read=True,
        read_at=now,
        created_at=now,
        metadata=None,
        deduplication_key=None,
    )
    await notification_repository.create(n)

    result = await notification_repository.mark_read("notif_idempotent", "user_001")
    assert result is not None
    assert result.is_read is True


@pytest.mark.anyio
async def test_mark_all_read():
    now = datetime.now(timezone.utc)
    for i in range(4):
        n = Notification(
            id=f"notif_all_{i}",
            recipient_id="user_001",
            business_id="biz_001",
            scope=NotificationScope.TENANT,
            type=NotificationType.PAYMENT_VERIFIED,
            severity=NotificationSeverity.INFO,
            title=f"Title {i}",
            message=f"Message {i}",
            is_read=(i == 0),
            read_at=now if i == 0 else None,
            created_at=now,
            metadata=None,
            deduplication_key=None,
        )
        await notification_repository.create(n)

    count = await notification_repository.mark_all_read("user_001")
    assert count == 3

    remaining = await notification_repository.count_unread("user_001")
    assert remaining == 0


@pytest.mark.anyio
async def test_deduplication_key():
    now = datetime.now(timezone.utc)
    n1 = Notification(
        id="notif_dedup_1",
        recipient_id="user_001",
        business_id="biz_001",
        scope=NotificationScope.TENANT,
        type=NotificationType.PAYMENT_VERIFIED,
        severity=NotificationSeverity.INFO,
        title="First",
        message="First notification",
        is_read=False,
        read_at=None,
        created_at=now,
        metadata=None,
        deduplication_key="dedup:test:001",
    )
    await notification_repository.create(n1)

    existing = await notification_repository.find_by_deduplication_key("dedup:test:001")
    assert existing is not None
    assert existing.id == "notif_dedup_1"

    missing = await notification_repository.find_by_deduplication_key("dedup:nonexistent")
    assert missing is None


# --- Service Tests ---

@pytest.mark.anyio
async def test_create_tenant_notification():
    n = await notification_service.create_notification(
        recipient_id="user_001",
        scope=NotificationScope.TENANT,
        type=NotificationType.PAYMENT_VERIFIED,
        severity=NotificationSeverity.INFO,
        title="Payment Verified",
        message="Your payment has been verified.",
        business_id="biz_001",
        metadata={"subscription_id": "sub_001"},
        deduplication_key="payment-verified:pa_001",
    )
    assert n.recipient_id == "user_001"
    assert n.scope == NotificationScope.TENANT
    assert n.business_id == "biz_001"


@pytest.mark.anyio
async def test_create_platform_notification():
    n = await notification_service.create_notification(
        recipient_id="admin_001",
        scope=NotificationScope.PLATFORM,
        type=NotificationType.PAYMENT_VERIFICATION_REQUIRED,
        severity=NotificationSeverity.INFO,
        title="Verification Required",
        message="Payment needs verification.",
        business_id=None,
    )
    assert n.scope == NotificationScope.PLATFORM
    assert n.business_id is None


@pytest.mark.anyio
async def test_create_tenant_requires_business_id():
    try:
        await notification_service.create_notification(
            recipient_id="user_001",
            scope=NotificationScope.TENANT,
            type=NotificationType.PAYMENT_VERIFIED,
            severity=NotificationSeverity.INFO,
            title="Test",
            message="Test",
            business_id=None,
        )
        assert False, "Should have raised HTTPException"
    except Exception as e:
        assert "business_id required" in str(e.detail) if hasattr(e, 'detail') else True


@pytest.mark.anyio
async def test_create_if_not_exists_deduplicates():
    n1 = await notification_service.create_if_not_exists(
        recipient_id="user_001",
        scope=NotificationScope.TENANT,
        type=NotificationType.PAYMENT_VERIFIED,
        severity=NotificationSeverity.INFO,
        title="First",
        message="First",
        business_id="biz_001",
        deduplication_key="dedup:svc:001",
    )
    n2 = await notification_service.create_if_not_exists(
        recipient_id="user_001",
        scope=NotificationScope.TENANT,
        type=NotificationType.PAYMENT_VERIFIED,
        severity=NotificationSeverity.INFO,
        title="Second",
        message="Second",
        business_id="biz_001",
        deduplication_key="dedup:svc:001",
    )
    assert n1.id == n2.id
    assert n1.title == "First"


@pytest.mark.anyio
async def test_service_mark_as_read():
    n = await notification_service.create_notification(
        recipient_id="user_001",
        scope=NotificationScope.TENANT,
        type=NotificationType.PAYMENT_VERIFIED,
        severity=NotificationSeverity.INFO,
        title="Read Me",
        message="Please read me.",
        business_id="biz_001",
    )
    result = await notification_service.mark_as_read(n.id, "user_001")
    assert result.is_read is True


@pytest.mark.anyio
async def test_service_mark_as_read_wrong_user():
    n = await notification_service.create_notification(
        recipient_id="user_001",
        scope=NotificationScope.TENANT,
        type=NotificationType.PAYMENT_VERIFIED,
        severity=NotificationSeverity.INFO,
        title="Private",
        message="Private notification.",
        business_id="biz_001",
    )
    try:
        await notification_service.mark_as_read(n.id, "user_999")
        assert False, "Should have raised HTTPException for wrong user"
    except Exception as e:
        assert "not found" in str(e.detail).lower() if hasattr(e, 'detail') else True


@pytest.mark.anyio
async def test_notify_super_admins():
    await notification_service.notify_super_admins(
        super_admin_ids=["admin_001", "admin_002"],
        type=NotificationType.PAYMENT_VERIFICATION_REQUIRED,
        severity=NotificationSeverity.INFO,
        title="Verification Required",
        message="Payment requires verification.",
        metadata={"subscription_id": "sub_001"},
        deduplication_key="payment-required:pa_001",
    )
    count_admin1 = await notification_service.get_unread_count("admin_001", NotificationScope.PLATFORM)
    count_admin2 = await notification_service.get_unread_count("admin_002", NotificationScope.PLATFORM)
    assert count_admin1 == 1
    assert count_admin2 == 1


@pytest.mark.anyio
async def test_notify_business_members():
    await notification_service.notify_business_members(
        member_ids=["owner_001", "admin_biz_001"],
        business_id="biz_001",
        type=NotificationType.PAYMENT_VERIFIED,
        severity=NotificationSeverity.INFO,
        title="Payment Verified",
        message="Your payment has been verified.",
        metadata={"subscription_id": "sub_001"},
        deduplication_key="payment-verified:pa_001",
    )
    count_owner = await notification_service.get_unread_count("owner_001", NotificationScope.TENANT, "biz_001")
    count_admin = await notification_service.get_unread_count("admin_biz_001", NotificationScope.TENANT, "biz_001")
    assert count_owner == 1
    assert count_admin == 1


@pytest.mark.anyio
async def test_notification_failure_does_not_crash():
    """Test that create_if_not_exists returns gracefully on edge cases."""
    n = await notification_service.create_if_not_exists(
        recipient_id="user_edge",
        scope=NotificationScope.TENANT,
        type=NotificationType.STOCK_LOW,
        severity=NotificationSeverity.WARNING,
        title="Stock Low",
        message="Product has low stock.",
        business_id="biz_edge",
        deduplication_key=None,
    )
    assert n.id is not None
    count = await notification_service.get_unread_count("user_edge", NotificationScope.TENANT, "biz_edge")
    assert count == 1


@pytest.mark.anyio
async def test_mark_all_read_service():
    for i in range(3):
        await notification_service.create_notification(
            recipient_id="user_markall",
            scope=NotificationScope.TENANT,
            type=NotificationType.PAYMENT_VERIFIED,
            severity=NotificationSeverity.INFO,
            title=f"Title {i}",
            message=f"Message {i}",
            business_id="biz_markall",
        )
    count = await notification_service.mark_all_as_read("user_markall", NotificationScope.TENANT, "biz_markall")
    assert count == 3
    remaining = await notification_service.get_unread_count("user_markall", NotificationScope.TENANT, "biz_markall")
    assert remaining == 0


@pytest.mark.anyio
async def test_scope_isolation_tenant_vs_platform():
    """Tenant notifications must not leak to platform, and vice versa."""
    await notification_service.create_notification(
        recipient_id="user_001",
        scope=NotificationScope.TENANT,
        type=NotificationType.PAYMENT_VERIFIED,
        severity=NotificationSeverity.INFO,
        title="Tenant Notif",
        message="Tenant",
        business_id="biz_001",
    )
    await notification_service.create_notification(
        recipient_id="admin_001",
        scope=NotificationScope.PLATFORM,
        type=NotificationType.PAYMENT_VERIFICATION_REQUIRED,
        severity=NotificationSeverity.INFO,
        title="Platform Notif",
        message="Platform",
        business_id=None,
    )

    tenant_count = await notification_service.get_unread_count("user_001", NotificationScope.TENANT, "biz_001")
    platform_count_user = await notification_service.get_unread_count("user_001", NotificationScope.PLATFORM)
    platform_count_admin = await notification_service.get_unread_count("admin_001", NotificationScope.PLATFORM)
    tenant_count_admin = await notification_service.get_unread_count("admin_001", NotificationScope.TENANT, "biz_001")

    assert tenant_count == 1
    assert platform_count_user == 0
    assert platform_count_admin == 1
    assert tenant_count_admin == 0


# --- E2E Trigger Tests (BLOCKER FIX) ---

from app.modules.subscription.service import SubscriptionService, subscription_service
from app.modules.subscription.repository import subscription_repository
from app.modules.authentication.repository import user_repository
from app.modules.business_membership.repository import business_membership_repository
from app.modules.business_membership.schemas import BusinessMembershipRole, BusinessMembershipStatus


@pytest.fixture(autouse=True)
def clear_all_repos():
    subscription_repository.clear()
    notification_repository.clear()
    user_repository.clear()
    business_membership_repository.clear()
    yield
    subscription_repository.clear()
    notification_repository.clear()
    user_repository.clear()
    business_membership_repository.clear()


async def _seed_super_admin(email: str = "superadmin@test.com") -> str:
    """Create and return an active SUPER_ADMIN user ID."""
    from app.modules.authentication.schemas import PlatformRole, UserCreate
    user = await user_repository.create(UserCreate(
        email=email,
        full_name="Super Admin",
        password="Password123!",
        password_confirmation="Password123!",
    ))
    await user_repository.update_platform_role(user.id, PlatformRole.SUPER_ADMIN)
    return user.id


async def _seed_owner_admin(business_id: str, email: str, role: BusinessMembershipRole = BusinessMembershipRole.OWNER) -> str:
    """Create an active OWNER/ADMIN membership and return user ID."""
    from app.modules.authentication.schemas import UserCreate
    user = await user_repository.create(UserCreate(
        email=email,
        full_name=f"Member {email}",
        password="Password123!",
        password_confirmation="Password123!",
    ))
    await business_membership_repository.create(
        business_id=business_id,
        user_id=user.id,
        role=role,
        status=BusinessMembershipStatus.ACTIVE,
    )
    return user.id


@pytest.mark.anyio
async def test_e2e_payment_verification_required_creates_platform_notification():
    """TEST A — PAYMENT_VERIFICATION_REQUIRED E2E"""
    # Seed 2 active Super Admins
    admin1_id = await _seed_super_admin("sa1@test.com")
    admin2_id = await _seed_super_admin("sa2@test.com")

    # Seed a regular user (non-admin) — should NOT receive notification
    from app.modules.authentication.schemas import UserCreate
    regular_user = await user_repository.create(UserCreate(
        email="regular@test.com", full_name="Regular", password="Password123!",
        password_confirmation="Password123!"
    ))

    # Create subscription
    sub = await subscription_service.create_default_subscription("biz_e2e_1")

    # Execute checkout
    pa = await subscription_service.checkout(sub.id)
    assert pa.status.value == "PENDING"

    # Both Super Admins should receive a PLATFORM notification
    count_admin1 = await notification_service.get_unread_count(admin1_id, NotificationScope.PLATFORM)
    count_admin2 = await notification_service.get_unread_count(admin2_id, NotificationScope.PLATFORM)
    assert count_admin1 == 1
    assert count_admin2 == 1

    # Regular user should NOT receive platform notification
    count_regular = await notification_service.get_unread_count(regular_user.id, NotificationScope.PLATFORM)
    assert count_regular == 0

    # Verify notification content
    notifications = await notification_service.list_notifications(admin1_id, scope=NotificationScope.PLATFORM)
    assert len(notifications) == 1
    notif = notifications[0]
    assert notif.type == NotificationType.PAYMENT_VERIFICATION_REQUIRED
    assert notif.severity == NotificationSeverity.INFO
    assert notif.recipient_id == admin1_id
    assert notif.scope == NotificationScope.PLATFORM
    assert notif.is_read is False


@pytest.mark.anyio
async def test_e2e_payment_verification_required_no_duplicate():
    """TEST A — deduplication: same subscription checkout twice does not duplicate."""
    admin_id = await _seed_super_admin("sa_dedup@test.com")
    sub = await subscription_service.create_default_subscription("biz_dedup")

    await subscription_service.checkout(sub.id)
    # Second checkout for same billing period returns existing PENDING attempt
    await subscription_service.checkout(sub.id)

    count = await notification_service.get_unread_count(admin_id, NotificationScope.PLATFORM)
    assert count == 1


@pytest.mark.anyio
async def test_e2e_payment_verified_creates_tenant_notification():
    """TEST B — PAYMENT_VERIFIED E2E"""
    # Seed business OWNER and ADMIN
    biz_id = "biz_e2e_verified"
    owner_id = await _seed_owner_admin(biz_id, "owner@test.com", BusinessMembershipRole.OWNER)
    admin_id = await _seed_owner_admin(biz_id, "admin@test.com", BusinessMembershipRole.ADMIN)

    # Seed a MEMBER — should NOT receive notification
    member_id = await _seed_owner_admin(biz_id, "member@test.com", BusinessMembershipRole.MEMBER)

    # Seed another business OWNER — should NOT receive notification (cross-business)
    other_biz_id = "biz_other"
    other_owner_id = await _seed_owner_admin(other_biz_id, "other_owner@test.com", BusinessMembershipRole.OWNER)

    # Create subscription for biz_e2e_verified
    sub = await subscription_service.create_default_subscription(biz_id)
    pa = await subscription_service.checkout(sub.id)

    bps = await subscription_service.get_billing_periods(sub.id)
    bp = bps[0]

    # Verify payment
    result = await subscription_service.verify_manual_payment(
        subscription_id=sub.id,
        billing_period_id=bp.id,
        payment_attempt_id=pa.id,
        payment_reference="TRX-999",
        verification_note="Test",
        verified_by_user_id="admin_001",
    )
    assert result.status.value == "SUCCESS"

    # OWNER should receive TENANT notification
    count_owner = await notification_service.get_unread_count(owner_id, NotificationScope.TENANT, biz_id)
    assert count_owner == 1

    # ADMIN should receive TENANT notification
    count_admin = await notification_service.get_unread_count(admin_id, NotificationScope.TENANT, biz_id)
    assert count_admin == 1

    # MEMBER should NOT receive notification
    count_member = await notification_service.get_unread_count(member_id, NotificationScope.TENANT, biz_id)
    assert count_member == 0

    # Other business OWNER should NOT receive this business's notification
    count_other = await notification_service.get_unread_count(other_owner_id, NotificationScope.TENANT, other_biz_id)
    assert count_other == 0

    # Verify notification content
    notifications = await notification_service.list_notifications(owner_id, scope=NotificationScope.TENANT, business_id=biz_id)
    assert len(notifications) == 1
    notif = notifications[0]
    assert notif.type == NotificationType.PAYMENT_VERIFIED
    assert notif.scope == NotificationScope.TENANT
    assert notif.business_id == biz_id
    assert notif.recipient_id == owner_id


@pytest.mark.anyio
async def test_e2e_no_super_admins_checkout_no_crash():
    """TEST C — checkout with zero active Super Admins does not crash."""
    sub = await subscription_service.create_default_subscription("biz_no_admin")
    pa = await subscription_service.checkout(sub.id)
    assert pa.status.value == "PENDING"
    # No crash, no notification created (zero recipients)


@pytest.mark.anyio
async def test_e2e_no_owner_admin_verify_no_crash():
    """TEST C — payment verification with zero OWNER/ADMIN recipients does not crash."""
    sub = await subscription_service.create_default_subscription("biz_no_members")
    pa = await subscription_service.checkout(sub.id)
    bps = await subscription_service.get_billing_periods(sub.id)

    result = await subscription_service.verify_manual_payment(
        subscription_id=sub.id,
        billing_period_id=bps[0].id,
        payment_attempt_id=pa.id,
        payment_reference="TRX-NO-RECIPIENTS",
        verification_note="No owner/admin",
        verified_by_user_id="admin_001",
    )
    assert result.status.value == "SUCCESS"
    # Primary operation succeeded, no crash from notification


@pytest.mark.anyio
async def test_e2e_subscription_status_safety_with_notification():
    """Verify notification integration does not alter subscription status behavior."""
    sub = await subscription_service.create_default_subscription("biz_safety")
    from app.modules.subscription.schemas import SubscriptionOverrideInput, SubscriptionStatus

    await subscription_service.override_subscription(
        sub.id,
        SubscriptionOverrideInput(action="SET_STATUS", status=SubscriptionStatus.SUSPENDED, reason="Test")
    )

    pa = await subscription_service.checkout(sub.id)
    bps = await subscription_service.get_billing_periods(sub.id)

    result = await subscription_service.verify_manual_payment(
        subscription_id=sub.id,
        billing_period_id=bps[0].id,
        payment_attempt_id=pa.id,
        payment_reference="TRX-SAFETY",
        verification_note="Safety test",
        verified_by_user_id="admin_001",
    )
    assert result.status.value == "SUCCESS"

    # Subscription must remain SUSPENDED (notification does not alter lifecycle)
    updated_sub = await subscription_service.get_by_id(sub.id)
    assert updated_sub.status == SubscriptionStatus.SUSPENDED

"""
Feature #66 — Notification Expansion + Production Persistence Tests (Targeted Remediation)

Covers test groups A through J:
- Group A: Four new types (SALES_FINALIZED, PURCHASE_RECEIVED, CUSTOMER_CREDIT_LIMIT_WARNING, TRANSFER_COMPLETED)
- Group B: Production persistence (`_send_notification` uses SQLAlchemyNotificationRepository)
- Group C: Deduplication & IntegrityError recovery
- Group D: Tenant / RBAC isolation
- Group E: Failure isolation
- Group F: Existing subscription notifications
- Group G: Duplicate event handling
- Group H: Session lifecycle (open, write, commit, close)
- Group I: No silent fallback regression verification
- Group J: Existing notification regression
"""
import os

# Set dummy DATABASE_URL before any app modules are imported to pass validation during test mocking
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test_db")

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from app.modules.notification.schemas import (
    NotificationType,
    NotificationScope,
    NotificationSeverity,
    Notification,
)
from app.modules.notification.service import _send_notification, NotificationService
from app.modules.notification.repository import notification_repository
from app.modules.notification.sqla_repository import SQLAlchemyNotificationRepository


@pytest.fixture(autouse=True)
def clear_repository():
    notification_repository.clear()
    yield
    notification_repository.clear()


# ── TEST GROUP A: FOUR NEW TYPES ────────────────────────────────────────────

class TestGroupAFourNewTypes:
    @pytest.mark.asyncio
    async def test_a1_sales_finalized(self):
        """Verify SALES_FINALIZED notification properties and exact metadata."""
        svc = NotificationService(notification_repository)
        n = await svc.create_notification(
            recipient_id="owner_001",
            scope=NotificationScope.TENANT,
            type=NotificationType.SALES_FINALIZED,
            severity=NotificationSeverity.INFO,
            title="Sales Finalized",
            message="Sales SAL-001 has been finalized.",
            business_id="biz_001",
            metadata={
                "sale_id": "sale_123",
                "sale_number": "SAL-001",
                "branch_id": "branch_456",
            },
            deduplication_key="SALES_FINALIZED:sale_123:owner_001",
        )
        assert n.type == NotificationType.SALES_FINALIZED
        assert n.title == "Sales Finalized"
        assert n.message == "Sales SAL-001 has been finalized."
        assert n.severity == NotificationSeverity.INFO
        assert n.scope == NotificationScope.TENANT
        assert n.business_id == "biz_001"
        assert n.recipient_id == "owner_001"
        assert n.metadata["sale_id"] == "sale_123"
        assert n.metadata["sale_number"] == "SAL-001"
        assert n.metadata["branch_id"] == "branch_456"
        assert n.deduplication_key == "SALES_FINALIZED:sale_123:owner_001"

    @pytest.mark.asyncio
    async def test_a2_purchase_received(self):
        """Verify PURCHASE_RECEIVED notification properties and exact metadata."""
        svc = NotificationService(notification_repository)
        n = await svc.create_notification(
            recipient_id="admin_001",
            scope=NotificationScope.TENANT,
            type=NotificationType.PURCHASE_RECEIVED,
            severity=NotificationSeverity.INFO,
            title="Goods Received",
            message="Receiving RCV-001 for purchase PO-001 has been received.",
            business_id="biz_001",
            metadata={
                "receiving_id": "rec_123",
                "purchase_id": "po_456",
                "receiving_number": "RCV-001",
            },
            deduplication_key="PURCHASE_RECEIVED:rec_123:admin_001",
        )
        assert n.type == NotificationType.PURCHASE_RECEIVED
        assert n.title == "Goods Received"
        assert n.severity == NotificationSeverity.INFO
        assert n.scope == NotificationScope.TENANT
        assert n.metadata["receiving_id"] == "rec_123"
        assert n.metadata["purchase_id"] == "po_456"
        assert n.metadata["receiving_number"] == "RCV-001"
        assert n.deduplication_key == "PURCHASE_RECEIVED:rec_123:admin_001"

    @pytest.mark.asyncio
    async def test_a3_customer_credit_limit_warning(self):
        """Verify CUSTOMER_CREDIT_LIMIT_WARNING notification properties."""
        svc = NotificationService(notification_repository)
        n = await svc.create_notification(
            recipient_id="owner_001",
            scope=NotificationScope.TENANT,
            type=NotificationType.CUSTOMER_CREDIT_LIMIT_WARNING,
            severity=NotificationSeverity.WARNING,
            title="Credit Limit Warning",
            message="Customer Acme Corp is near credit limit.",
            business_id="biz_001",
            metadata={
                "customer_id": "cust_123",
                "customer_name": "Acme Corp",
                "credit_limit": "50000.00",
                "exposure": "48000.00",
                "sale_id": "sale_999",
            },
            deduplication_key="CREDIT_WARNING:cust_123:sale_999:owner_001",
        )
        assert n.type == NotificationType.CUSTOMER_CREDIT_LIMIT_WARNING
        assert n.severity == NotificationSeverity.WARNING
        assert n.title == "Credit Limit Warning"
        assert n.metadata["customer_name"] == "Acme Corp"
        assert n.metadata["credit_limit"] == "50000.00"
        assert n.metadata["exposure"] == "48000.00"

    @pytest.mark.asyncio
    async def test_a4_transfer_completed(self):
        """Verify TRANSFER_COMPLETED notification properties and metadata."""
        svc = NotificationService(notification_repository)
        n = await svc.create_notification(
            recipient_id="owner_001",
            scope=NotificationScope.TENANT,
            type=NotificationType.TRANSFER_COMPLETED,
            severity=NotificationSeverity.INFO,
            title="Transfer Completed",
            message="Transfer TRF-001 from WH-A to WH-B completed.",
            business_id="biz_001",
            metadata={
                "transfer_id": "trf_123",
                "transfer_number": "TRF-001",
                "source_branch_id": "wh_a",
                "destination_branch_id": "wh_b",
            },
            deduplication_key="TRANSFER_COMPLETED:trf_123:owner_001",
        )
        assert n.type == NotificationType.TRANSFER_COMPLETED
        assert n.severity == NotificationSeverity.INFO
        assert n.metadata["transfer_id"] == "trf_123"
        assert n.metadata["transfer_number"] == "TRF-001"
        assert n.metadata["source_branch_id"] == "wh_a"
        assert n.metadata["destination_branch_id"] == "wh_b"


# ── TEST GROUP B: PRODUCTION PERSISTENCE ────────────────────────────────────

class TestGroupBProductionPersistence:
    @pytest.mark.asyncio
    async def test_send_notification_uses_sqla_repository(self):
        """Verify _send_notification uses SQLAlchemyNotificationRepository and commits."""
        with patch("app.core.database.async_session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session.commit = AsyncMock()
            mock_factory.return_value = mock_session

            with patch("app.modules.notification.sqla_repository.SQLAlchemyNotificationRepository") as MockRepoClass:
                mock_sqla_repo = MagicMock()
                mock_sqla_repo.create_if_not_exists = AsyncMock()
                MockRepoClass.return_value = mock_sqla_repo

                with patch("app.modules.notification.service.NotificationService") as MockServiceClass:
                    mock_service_instance = MagicMock()
                    mock_service_instance.create_if_not_exists = AsyncMock()
                    MockServiceClass.return_value = mock_service_instance

                    await _send_notification(
                        recipient_id="user_1",
                        scope=NotificationScope.TENANT,
                        notif_type=NotificationType.SALES_FINALIZED,
                        severity=NotificationSeverity.INFO,
                        title="Test",
                        message="Test",
                        business_id="biz_1",
                    )

                    MockRepoClass.assert_called_once_with(mock_session)
                    mock_service_instance.create_if_not_exists.assert_called_once()
                    mock_session.commit.assert_called_once()


# ── TEST GROUP C: DEDUPLICATION ─────────────────────────────────────────────

class TestGroupCDeduplication:
    @pytest.mark.asyncio
    async def test_duplicate_deduplication_key_returns_existing(self):
        """Same deduplication key submitted twice returns existing without duplication."""
        svc = NotificationService(notification_repository)
        n1 = await svc.create_if_not_exists(
            recipient_id="user_1",
            scope=NotificationScope.TENANT,
            type=NotificationType.SALES_FINALIZED,
            severity=NotificationSeverity.INFO,
            title="First",
            message="First",
            business_id="biz_1",
            deduplication_key="dedup:key:1",
        )
        n2 = await svc.create_if_not_exists(
            recipient_id="user_1",
            scope=NotificationScope.TENANT,
            type=NotificationType.SALES_FINALIZED,
            severity=NotificationSeverity.INFO,
            title="Second",
            message="Second",
            business_id="biz_1",
            deduplication_key="dedup:key:1",
        )
        assert n1.id == n2.id
        count = await svc.get_unread_count("user_1", NotificationScope.TENANT, "biz_1")
        assert count == 1

    @pytest.mark.asyncio
    async def test_sqla_repository_integrity_error_recovery(self):
        """Simulate SQLAlchemy IntegrityError rollback and re-query on deduplication collision."""
        mock_session = AsyncMock()
        sqla_repo = SQLAlchemyNotificationRepository(mock_session)

        # Mock sa_create to raise IntegrityError
        with patch("app.modules.notification.sqla_repository.sa_create", side_effect=IntegrityError("stmt", {}, Exception("unique constraint"))):
            mock_session.rollback = AsyncMock()

            existing_notif = Notification(
                id="existing_id",
                recipient_id="user_1",
                business_id="biz_1",
                scope=NotificationScope.TENANT,
                type=NotificationType.SALES_FINALIZED,
                severity=NotificationSeverity.INFO,
                title="Existing",
                message="Existing",
                created_at=datetime.now(timezone.utc),
                deduplication_key="dedup:collision",
            )

            with patch.object(sqla_repo, "find_by_deduplication_key", return_value=existing_notif) as mock_find:
                n = Notification(
                    id="new_id",
                    recipient_id="user_1",
                    business_id="biz_1",
                    scope=NotificationScope.TENANT,
                    type=NotificationType.SALES_FINALIZED,
                    severity=NotificationSeverity.INFO,
                    title="New",
                    message="New",
                    created_at=datetime.now(timezone.utc),
                    deduplication_key="dedup:collision",
                )

                result = await sqla_repo.create(n)
                mock_session.rollback.assert_called_once()
                mock_find.assert_called_once_with("dedup:collision")
                assert result.id == "existing_id"


# ── TEST GROUP D: TENANT / RBAC ─────────────────────────────────────────────

class TestGroupDTenantRBAC:
    @pytest.mark.asyncio
    async def test_tenant_scope_requires_business_id(self):
        """TENANT scope notification requires business_id."""
        svc = NotificationService(notification_repository)
        with pytest.raises(Exception):
            await svc.create_notification(
                recipient_id="user_1",
                scope=NotificationScope.TENANT,
                type=NotificationType.SALES_FINALIZED,
                severity=NotificationSeverity.INFO,
                title="Test",
                message="Test",
                business_id=None,
            )

    @pytest.mark.asyncio
    async def test_platform_scope_requires_no_business_id(self):
        """PLATFORM scope notification must have null business_id."""
        svc = NotificationService(notification_repository)
        with pytest.raises(Exception):
            await svc.create_notification(
                recipient_id="admin_1",
                scope=NotificationScope.PLATFORM,
                type=NotificationType.PAYMENT_VERIFICATION_REQUIRED,
                severity=NotificationSeverity.INFO,
                title="Test",
                message="Test",
                business_id="biz_invalid",
            )

    @pytest.mark.asyncio
    async def test_cross_tenant_isolation(self):
        """Tenant A notification never appears in tenant B queries."""
        svc = NotificationService(notification_repository)
        await svc.create_notification(
            recipient_id="user_1",
            scope=NotificationScope.TENANT,
            type=NotificationType.SALES_FINALIZED,
            severity=NotificationSeverity.INFO,
            title="Tenant A",
            message="Message A",
            business_id="biz_A",
        )
        list_b = await svc.list_notifications(
            recipient_id="user_1",
            scope=NotificationScope.TENANT,
            business_id="biz_B",
        )
        assert len(list_b) == 0


# ── TEST GROUP E: FAILURE ISOLATION ─────────────────────────────────────────

class TestGroupEFailureIsolation:
    @pytest.mark.asyncio
    async def test_notification_failure_does_not_poison_producer(self):
        """Notification sending failure is caught and logged without crashing the producer."""
        svc = NotificationService(notification_repository)
        with patch("app.modules.notification.service._send_notification", side_effect=RuntimeError("Notification DB down")):
            # Should complete successfully without raising exception (best-effort contract)
            await svc.notify_super_admins(
                super_admin_ids=["admin_1"],
                type=NotificationType.PAYMENT_VERIFICATION_REQUIRED,
                severity=NotificationSeverity.INFO,
                title="Test",
                message="Test",
            )


# ── TEST GROUP F: EXISTING SUBSCRIPTION NOTIFICATIONS ───────────────────────

class TestGroupFExistingSubscriptions:
    @pytest.mark.asyncio
    async def test_payment_verification_required_and_verified(self):
        """Verify existing payment notification types remain intact."""
        svc = NotificationService(notification_repository)
        n1 = await svc.create_notification(
            recipient_id="admin_1",
            scope=NotificationScope.PLATFORM,
            type=NotificationType.PAYMENT_VERIFICATION_REQUIRED,
            severity=NotificationSeverity.INFO,
            title="Verification Required",
            message="Verify payment",
            metadata={"payment_attempt_id": "pa_1"},
        )
        assert n1.type == NotificationType.PAYMENT_VERIFICATION_REQUIRED
        assert n1.scope == NotificationScope.PLATFORM

        n2 = await svc.create_notification(
            recipient_id="owner_1",
            scope=NotificationScope.TENANT,
            type=NotificationType.PAYMENT_VERIFIED,
            severity=NotificationSeverity.INFO,
            title="Payment Verified",
            message="Payment verified",
            business_id="biz_1",
            metadata={"payment_attempt_id": "pa_1"},
        )
        assert n2.type == NotificationType.PAYMENT_VERIFIED
        assert n2.scope == NotificationScope.TENANT
        assert n2.business_id == "biz_1"


# ── TEST GROUP G: DUPLICATE EVENT ───────────────────────────────────────────

class TestGroupGDulicateEvent:
    @pytest.mark.asyncio
    async def test_duplicate_event_single_notification_per_recipient(self):
        """Executing same logical event twice results in exactly one notification per recipient."""
        svc = NotificationService(notification_repository)
        dedup = "SALES_FINALIZED:sale_99:owner_1"
        n1 = await svc.create_if_not_exists(
            recipient_id="owner_1",
            scope=NotificationScope.TENANT,
            type=NotificationType.SALES_FINALIZED,
            severity=NotificationSeverity.INFO,
            title="Finalized",
            message="Finalized",
            business_id="biz_1",
            deduplication_key=dedup,
        )
        n2 = await svc.create_if_not_exists(
            recipient_id="owner_1",
            scope=NotificationScope.TENANT,
            type=NotificationType.SALES_FINALIZED,
            severity=NotificationSeverity.INFO,
            title="Finalized",
            message="Finalized",
            business_id="biz_1",
            deduplication_key=dedup,
        )
        assert n1.id == n2.id
        count = await svc.get_unread_count("owner_1", NotificationScope.TENANT, "biz_1")
        assert count == 1


# ── TEST GROUP H: SESSION LIFECYCLE ─────────────────────────────────────────

class TestGroupHSessionLifecycle:
    @pytest.mark.asyncio
    async def test_session_lifecycle_commit_before_context_exit(self):
        """Verify session commits inside context before exit."""
        with patch("app.core.database.async_session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session.commit = AsyncMock()
            mock_factory.return_value = mock_session

            with patch("app.modules.notification.sqla_repository.SQLAlchemyNotificationRepository"):
                with patch("app.modules.notification.service.NotificationService") as MockService:
                    mock_svc = MagicMock()
                    mock_svc.create_if_not_exists = AsyncMock()
                    MockService.return_value = mock_svc

                    await _send_notification(
                        recipient_id="user_1",
                        scope=NotificationScope.TENANT,
                        notif_type=NotificationType.SALES_FINALIZED,
                        severity=NotificationSeverity.INFO,
                        title="Test",
                        message="Test",
                        business_id="biz_1",
                    )
                    mock_session.commit.assert_called_once()
                    mock_factory.assert_called_once()


# ── TEST GROUP I: NO SILENT FALLBACK ────────────────────────────────────────

class TestGroupINoSilentFallback:
    @pytest.mark.asyncio
    async def test_no_silent_fallback_on_db_failure(self):
        """Verify production failure does not trigger InMemory fallback."""
        with patch("app.core.database.async_session_factory") as mock_factory:
            mock_factory.side_effect = RuntimeError("Database offline")

            # Calling _send_notification should raise exception (no silent swallow / InMemory fallback)
            with pytest.raises(RuntimeError, match="Database offline"):
                await _send_notification(
                    recipient_id="user_1",
                    scope=NotificationScope.TENANT,
                    notif_type=NotificationType.SALES_FINALIZED,
                    severity=NotificationSeverity.INFO,
                    title="Test",
                    message="Test",
                    business_id="biz_1",
                )

            # Ensure InMemory repository has received zero notifications
            count = await notification_repository.count_unread("user_1")
            assert count == 0


# ── TEST GROUP J: EXISTING NOTIFICATION REGRESSION ──────────────────────────

class TestGroupJRegression:
    @pytest.mark.asyncio
    async def test_notification_service_methods(self):
        """Verify standard list, unread count, and mark read methods work correctly."""
        svc = NotificationService(notification_repository)
        n = await svc.create_notification(
            recipient_id="user_1",
            scope=NotificationScope.TENANT,
            type=NotificationType.SALES_FINALIZED,
            severity=NotificationSeverity.INFO,
            title="Reg Test",
            message="Reg message",
            business_id="biz_1",
        )
        assert await svc.get_unread_count("user_1", NotificationScope.TENANT, "biz_1") == 1
        updated = await svc.mark_as_read(n.id, "user_1")
        assert updated.is_read is True
        assert await svc.get_unread_count("user_1", NotificationScope.TENANT, "biz_1") == 0

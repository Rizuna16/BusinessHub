import pytest
import time

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory, engine
from app.core.container import RepositoryContainer


@pytest.fixture(autouse=True)
async def _reset_engine_pool():
    """Reset engine pool state before each test to avoid Windows ProactorEventLoop contamination."""
    await engine.dispose()
    yield
    await engine.dispose()
from app.modules.business.service import BusinessService
from app.modules.business.sqla_repository import SQLAlchemyBusinessRepository
from app.modules.business.repository import InMemoryBusinessRepository
from app.modules.business_membership.sqla_repository import SQLAlchemyBusinessMembershipRepository
from app.modules.business_membership.service import BusinessMembershipService
from app.modules.subscription.sqla_repository import SQLAlchemySubscriptionRepository
from app.modules.subscription.service import SubscriptionService
from app.modules.business.schemas import BusinessCreate, BusinessType


async def _cleanup(business_id: str):
    async with async_session_factory() as session:
        await session.execute(text("DELETE FROM payment_attempts WHERE billing_period_id IN (SELECT id FROM billing_periods WHERE business_id = :bid)"), {"bid": business_id})
        await session.execute(text("DELETE FROM billing_periods WHERE business_id = :bid"), {"bid": business_id})
        await session.execute(text("DELETE FROM subscriptions WHERE business_id = :bid"), {"bid": business_id})
        await session.execute(text("DELETE FROM business_memberships WHERE business_id = :bid"), {"bid": business_id})
        await session.execute(text("DELETE FROM businesses WHERE id = :bid"), {"bid": business_id})
        await session.commit()


@pytest.mark.anyio
async def test_phase41_transaction_success():
    """A. SUCCESS: Business + Membership + Subscription all committed atomically."""
    ts = time.time_ns()
    biz_name = f"Tx Success Biz {ts}"
    owner_id = f"user-tx-success-{ts}"
    async with async_session_factory() as session:
        container = RepositoryContainer(session)
        membership_svc = BusinessMembershipService(repository=container.business_membership)
        subscription_svc = SubscriptionService(repository=container.subscription)
        svc = BusinessService(
            repository=container.business,
            membership_service=membership_svc,
            subscription_service_instance=subscription_svc,
            session=session,
        )
        result = await svc.create_business(
            BusinessCreate(name=biz_name, business_type=BusinessType.RETAIL, timezone="UTC", locale="en-US"),
            owner_user_id=owner_id,
        )
        business_id = result.id

    async with async_session_factory() as session:
        container = RepositoryContainer(session)
        biz = await container.business.get_by_id(business_id)
        assert biz is not None, "Business should persist after commit"
        assert biz.name == biz_name

        memberships = await container.business_membership.list_by_business(business_id)
        assert len(memberships) == 1, "Owner membership should persist"
        assert memberships[0].role.value == "OWNER"
        assert memberships[0].user_id == owner_id

        sub = await container.subscription.get_by_business_id(business_id)
        assert sub is not None, "Default subscription should persist"

    await _cleanup(business_id)


@pytest.mark.anyio
async def test_phase41_transaction_rollback_on_membership_failure():
    """B. FAILURE: Exception after Business creation. Entire transaction rolled back."""

    class FailingMembershipService(BusinessMembershipService):
        async def create_owner_membership(self, business_id, user_id):
            raise RuntimeError("Simulated membership failure")

    ts = time.time_ns()
    biz_name = f"Tx Rollback Biz {ts}"
    owner_id = f"user-tx-rollback-{ts}"
    async with async_session_factory() as session:
        container = RepositoryContainer(session)
        failing_membership_svc = FailingMembershipService(repository=container.business_membership)
        subscription_svc = SubscriptionService(repository=container.subscription)
        svc = BusinessService(
            repository=container.business,
            membership_service=failing_membership_svc,
            subscription_service_instance=subscription_svc,
            session=session,
        )
        try:
            await svc.create_business(
                BusinessCreate(name=biz_name, business_type=BusinessType.RETAIL, timezone="UTC", locale="en-US"),
                owner_user_id=owner_id,
            )
            assert False, "Should have raised RuntimeError"
        except RuntimeError:
            pass

    async with async_session_factory() as session:
        from sqlalchemy import select, func
        from app.modules.business.models import Business
        stmt = select(func.count()).select_from(Business).where(Business.name == biz_name)
        result = await session.execute(stmt)
        assert result.scalar() == 0, "Business should NOT exist after rollback"

        from app.modules.business_membership.models import BusinessMembership
        stmt2 = select(func.count()).select_from(BusinessMembership).where(
            BusinessMembership.user_id == owner_id
        )
        result2 = await session.execute(stmt2)
        assert result2.scalar() == 0, "Membership should NOT exist after rollback"


@pytest.mark.anyio
async def test_phase41_retry_after_rollback():
    """C. RETRY: After rollback, workflow succeeds without duplicate state."""
    ts = time.time_ns()
    biz_name = f"Retry Biz {ts}"
    owner_id = f"user-retry-{ts}"

    class OnceFailingMembershipService(BusinessMembershipService):
        _call_count = 0

        async def create_owner_membership(self, business_id, user_id):
            OnceFailingMembershipService._call_count += 1
            if OnceFailingMembershipService._call_count == 1:
                raise RuntimeError("First call failure")
            return await super().create_owner_membership(business_id, user_id)

    async with async_session_factory() as session:
        container = RepositoryContainer(session)
        failing_svc = OnceFailingMembershipService(repository=container.business_membership)
        subscription_svc = SubscriptionService(repository=container.subscription)
        svc = BusinessService(
            repository=container.business,
            membership_service=failing_svc,
            subscription_service_instance=subscription_svc,
            session=session,
        )
        try:
            await svc.create_business(
                BusinessCreate(name=biz_name, business_type=BusinessType.RETAIL, timezone="UTC", locale="en-US"),
                owner_user_id=owner_id,
            )
            assert False, "Should have raised RuntimeError on first call"
        except RuntimeError:
            pass

    async with async_session_factory() as session:
        from sqlalchemy import select, func
        from app.modules.business.models import Business
        stmt = select(func.count()).select_from(Business).where(Business.name == biz_name)
        result = await session.execute(stmt)
        assert result.scalar() == 0, "No partial business from failed first attempt"

    async with async_session_factory() as session:
        container = RepositoryContainer(session)
        membership_svc = BusinessMembershipService(repository=container.business_membership)
        subscription_svc = SubscriptionService(repository=container.subscription)
        svc = BusinessService(
            repository=container.business,
            membership_service=membership_svc,
            subscription_service_instance=subscription_svc,
            session=session,
        )
        result = await svc.create_business(
            BusinessCreate(name=biz_name, business_type=BusinessType.RETAIL, timezone="UTC", locale="en-US"),
            owner_user_id=owner_id,
        )
        business_id = result.id

    async with async_session_factory() as session:
        container = RepositoryContainer(session)
        biz = await container.business.get_by_id(business_id)
        assert biz is not None
        assert biz.name == biz_name

        memberships = await container.business_membership.list_by_business(business_id)
        assert len(memberships) == 1

    await _cleanup(business_id)


@pytest.mark.anyio
async def test_phase41_restart_persistence():
    """D. RESTART: After commit + new session factory, records remain accessible."""
    ts = time.time_ns()
    biz_name = f"Restart Biz {ts}"
    owner_id = f"user-restart-{ts}"
    async with async_session_factory() as session:
        container = RepositoryContainer(session)
        membership_svc = BusinessMembershipService(repository=container.business_membership)
        subscription_svc = SubscriptionService(repository=container.subscription)
        svc = BusinessService(
            repository=container.business,
            membership_service=membership_svc,
            subscription_service_instance=subscription_svc,
            session=session,
        )
        result = await svc.create_business(
            BusinessCreate(name=biz_name, business_type=BusinessType.RETAIL, timezone="UTC", locale="en-US"),
            owner_user_id=owner_id,
        )
        business_id = result.id

    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from app.core.config import settings
    new_engine = create_async_engine(settings.database_url, echo=False, pool_size=5, pool_pre_ping=True)
    NewSession = async_sessionmaker(new_engine, class_=AsyncSession, expire_on_commit=False)

    async with NewSession() as session:
        container = RepositoryContainer(session)
        biz = await container.business.get_by_id(business_id)
        assert biz is not None, "Business persists across engine restart"
        assert biz.name == biz_name

        memberships = await container.business_membership.list_by_business(business_id)
        assert len(memberships) == 1

    await new_engine.dispose()
    await _cleanup(business_id)


@pytest.mark.anyio
async def test_phase41_repository_no_commit():
    """E. REPOSITORY COMMIT GUARD: SQLAlchemy repositories never expose commit."""
    async with async_session_factory() as session:
        repo = SQLAlchemyBusinessRepository(session)
        assert not callable(getattr(repo, 'commit', None)), \
            "BusinessRepository should not have commit method"

        membership_repo = SQLAlchemyBusinessMembershipRepository(session)
        assert not callable(getattr(membership_repo, 'commit', None)), \
            "BusinessMembershipRepository should not have commit method"


@pytest.mark.anyio
async def test_phase41_session_sharing():
    """F. SESSION SHARING: Both repositories use the same AsyncSession during workflow."""
    async with async_session_factory() as session:
        container = RepositoryContainer(session)
        assert container.business.session is session
        assert container.business_membership.session is session
        assert container.subscription.session is session
        assert container.business.session is container.business_membership.session


@pytest.mark.anyio
async def test_phase41_no_inmemory_fallback():
    """Verify production path uses SQLAlchemy, not InMemory."""
    async with async_session_factory() as session:
        container = RepositoryContainer(session)
        assert isinstance(container.business, SQLAlchemyBusinessRepository)
        assert not isinstance(container.business, InMemoryBusinessRepository)
        assert isinstance(container.business_membership, SQLAlchemyBusinessMembershipRepository)
        assert isinstance(container.subscription, SQLAlchemySubscriptionRepository)


@pytest.mark.anyio
async def test_phase41_rollback_leaves_no_partial_membership():
    """Verify subscription failure rolls back both business and membership."""

    class FailingSubscriptionService(SubscriptionService):
        async def create_default_subscription(self, business_id):
            raise RuntimeError("Simulated subscription failure")

    ts = time.time_ns()
    biz_name = f"Sub Fail Biz {ts}"
    owner_id = f"user-sub-fail-{ts}"
    async with async_session_factory() as session:
        container = RepositoryContainer(session)
        membership_svc = BusinessMembershipService(repository=container.business_membership)
        failing_sub_svc = FailingSubscriptionService(repository=container.subscription)
        svc = BusinessService(
            repository=container.business,
            membership_service=membership_svc,
            subscription_service_instance=failing_sub_svc,
            session=session,
        )
        try:
            await svc.create_business(
                BusinessCreate(name=biz_name, business_type=BusinessType.RETAIL, timezone="UTC", locale="en-US"),
                owner_user_id=owner_id,
            )
            assert False, "Should have raised RuntimeError"
        except RuntimeError:
            pass

    async with async_session_factory() as session:
        from sqlalchemy import select, func
        from app.modules.business.models import Business
        stmt = select(func.count()).select_from(Business).where(Business.name == biz_name)
        result = await session.execute(stmt)
        assert result.scalar() == 0, "Business should not exist after subscription failure rollback"

        from app.modules.business_membership.models import BusinessMembership
        stmt2 = select(func.count()).select_from(BusinessMembership).where(
            BusinessMembership.user_id == owner_id
        )
        result2 = await session.execute(stmt2)
        assert result2.scalar() == 0, "Membership should not exist after subscription failure rollback"

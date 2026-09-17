import pytest
import time
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.core.database import async_session_factory, engine
from app.core.container import RepositoryContainer
from app.modules.business.schemas import BusinessCreate, BusinessType, BusinessStatus
from app.modules.product.schemas import ProductCreate, ProductType, ProductTaxTreatment
from app.modules.unit.schemas import UnitCreate


@pytest.mark.anyio
async def test_all_persistence_lifecycle():
    """Combined test block to ensure single event loop session safety on Windows."""
    
    # 1. Test Session Lifecycle & Container
    async with async_session_factory() as session:
        container = RepositoryContainer(session)
        assert container.session is session
        assert hasattr(container, 'business')
        assert hasattr(container, 'product')

    # 2. Test Rollback on Exception
    slug_rb = f"rollback-test-{time.time_ns()}"
    try:
        async with async_session_factory() as session:
            container = RepositoryContainer(session)
            await container.business.create(
                BusinessCreate(name="Rollback Test", business_type=BusinessType.RETAIL, timezone="UTC", locale="en-US"),
                owner_user_id="user-rollback",
                slug=slug_rb
            )
            await session.flush()
            raise ValueError("Simulated failure forcing rollback")
    except ValueError:
        pass
    async with async_session_factory() as session:
        container = RepositoryContainer(session)
        biz = await container.business.get_by_slug(slug_rb)
        assert biz is None

    # 3. Test Successful Commit & Restart Simulation
    slug_commit = f"commit-test-{time.time_ns()}"
    async with async_session_factory() as session:
        container = RepositoryContainer(session)
        created = await container.business.create(
            BusinessCreate(name="Commit Test Business", business_type=BusinessType.RETAIL, timezone="UTC", locale="en-US"),
            owner_user_id="user-commit",
            slug=slug_commit
        )
        business_id = created.id
        await session.commit()

    async with async_session_factory() as session:
        container = RepositoryContainer(session)
        biz = await container.business.get_by_id(business_id)
        assert biz is not None
        assert biz.name == "Commit Test Business"
        assert biz.slug == slug_commit
        assert biz.status == BusinessStatus.ACTIVE

    async with async_session_factory() as session:
        await session.execute(text(f"DELETE FROM businesses WHERE id = '{business_id}'"))
        await session.commit()

    # 4. Test Tenant Isolation
    ts = time.time_ns()
    slug_a = f"alpha-biz-{ts}"
    slug_b = f"beta-biz-{ts}"
    async with async_session_factory() as session:
        container = RepositoryContainer(session)
        biz_a = await container.business.create(
            BusinessCreate(name="Alpha", business_type=BusinessType.RETAIL, timezone="UTC", locale="en-US"),
            owner_user_id="user-alpha",
            slug=slug_a
        )
        biz_b = await container.business.create(
            BusinessCreate(name="Beta", business_type=BusinessType.RETAIL, timezone="UTC", locale="en-US"),
            owner_user_id="user-beta",
            slug=slug_b
        )
        unit_a = await container.unit.create(
            business_id=biz_a.id,
            unit_data=UnitCreate(name="Piece", code="PC", symbol="pc")
        )
        await session.commit()

    async with async_session_factory() as session:
        container = RepositoryContainer(session)
        prod_a = await container.product.create(
            business_id=biz_a.id,
            product_data=ProductCreate(name="Alpha Product", code=f"ALPHA-{ts}", unit_id=unit_a.id, product_type=ProductType.GOODS)
        )
        await session.commit()

    async with async_session_factory() as session:
        container = RepositoryContainer(session)
        products_b = await container.product.list_by_business(biz_b.id)
        assert not any(p.code == f"ALPHA-{ts}" for p in products_b)

    async with async_session_factory() as session:
        await session.execute(text(f"DELETE FROM products WHERE business_id = '{biz_a.id}'"))
        await session.execute(text(f"DELETE FROM units WHERE business_id = '{biz_a.id}'"))
        await session.execute(text(f"DELETE FROM businesses WHERE id = '{biz_a.id}' OR id = '{biz_b.id}'"))
        await session.commit()

    # 5. Test No InMemory Fallback
    from app.modules.business.sqla_repository import SQLAlchemyBusinessRepository
    from app.modules.business.repository import InMemoryBusinessRepository
    async with async_session_factory() as session:
        container = RepositoryContainer(session)
        assert isinstance(container.business, SQLAlchemyBusinessRepository)
        assert not isinstance(container.business, InMemoryBusinessRepository)

    # 6. Test Database Failure Behavior
    invalid_engine = create_async_engine(
        "postgresql+asyncpg://invalid:invalid@localhost:5432/nonexistent",
        echo=False
    )
    try:
        with pytest.raises(Exception):
            async with invalid_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
    finally:
        await invalid_engine.dispose()

    # Dispose pool to prevent stale connections across event loops (Windows ProactorEventLoop)
    await engine.dispose()

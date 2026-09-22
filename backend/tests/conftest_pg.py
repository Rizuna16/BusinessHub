"""
PostgreSQL-backed concurrency test infrastructure.

Provides independent AsyncSession fixtures for testing real database
concurrency scenarios with row-level locking, unique constraints,
and transaction isolation.
"""
import asyncio
import uuid
import pytest
import pytest_asyncio
from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.database import Base
from app.core.config import settings


# ── Engine & Session Factory ──────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session")
async def pg_engine():
    """Create a dedicated async engine for PostgreSQL concurrency tests."""
    url = settings.database_url
    if not url:
        pytest.skip("DATABASE_URL not configured; skipping PostgreSQL concurrency tests")
    
    engine = create_async_engine(
        url,
        echo=False,
        pool_size=5,
        max_overflow=5,
        pool_pre_ping=True,
    )
    
    # Ensure all tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def pg_session_factory(pg_engine):
    """Create a session factory for independent sessions."""
    return async_sessionmaker(
        pg_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest_asyncio.fixture
async def session_a(pg_session_factory):
    """Independent PostgreSQL session A."""
    async with pg_session_factory() as session:
        yield session
        if session.is_active:
            await session.rollback()


@pytest_asyncio.fixture
async def session_b(pg_session_factory):
    """Independent PostgreSQL session B."""
    async with pg_session_factory() as session:
        yield session
        if session.is_active:
            await session.rollback()


@pytest.fixture
def business_id():
    """Unique business ID for test isolation."""
    return str(uuid.uuid4())


@pytest.fixture
def location_id():
    """Unique location ID for test isolation."""
    return str(uuid.uuid4())


@pytest.fixture
def product_id():
    """Unique product ID for test isolation."""
    return str(uuid.uuid4())

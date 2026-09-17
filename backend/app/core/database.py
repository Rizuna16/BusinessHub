"""
Database foundation — PostgreSQL via SQLAlchemy Async.

Provides:
- async engine
- session factory
- session dependency
- declarative base
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


import os
from fastapi import HTTPException, status
from sqlalchemy.exc import OperationalError

if not settings.database_url:
    raise RuntimeError("CRITICAL: DATABASE_URL is not configured. Production requires explicit DATABASE_URL. No fallback allowed.")

try:
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
    )
except OperationalError as e:
    raise RuntimeError(f"CRITICAL: PostgreSQL unreachable. No fallback allowed. Error: {e}")

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db_session():
    try:
        async with async_session_factory() as session:
            try:
                yield session
            except Exception:
                if session.is_active:
                    await session.rollback()
                raise
    except OperationalError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database persistence unavailable. No fallback allowed."
        )


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

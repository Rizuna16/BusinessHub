"""Shared SQLAlchemy repository utilities."""
from typing import TypeVar, Type, Optional, List, Tuple, Any
from decimal import Decimal
from datetime import datetime
from sqlalchemy import select, func, delete, update, desc, asc, String, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

ModelT = TypeVar("ModelT", bound=DeclarativeBase)

async def sa_create(session: AsyncSession, model_class: Type[ModelT], data: dict) -> ModelT:
    """Create and flush a new ORM record. Does NOT commit."""
    instance = model_class(**data)
    session.add(instance)
    await session.flush()
    return instance

async def sa_get(session: AsyncSession, model_class: Type[ModelT], pk_value: str, business_id: Optional[str] = None) -> Optional[ModelT]:
    """Get by primary key, optionally scoped to business_id."""
    stmt = select(model_class).where(model_class.id == pk_value)
    if business_id and hasattr(model_class, 'business_id'):
        stmt = stmt.where(model_class.business_id == business_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def sa_list(session: AsyncSession, model_class: Type[ModelT], business_id: Optional[str] = None, filters: Optional[List] = None, order_by: Optional[List] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> List[ModelT]:
    """List records with optional business scope and filters."""
    stmt = select(model_class)
    if business_id and hasattr(model_class, 'business_id'):
        stmt = stmt.where(model_class.business_id == business_id)
    if filters:
        stmt = stmt.where(and_(*filters))
    if order_by:
        stmt = stmt.order_by(*order_by)
    else:
        if hasattr(model_class, 'created_at'):
            stmt = stmt.order_by(desc(model_class.created_at))
    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())

async def sa_count(session: AsyncSession, model_class: Type[ModelT], business_id: Optional[str] = None, filters: Optional[List] = None) -> int:
    """Count records."""
    stmt = select(func.count()).select_from(model_class)
    if business_id and hasattr(model_class, 'business_id'):
        stmt = stmt.where(model_class.business_id == business_id)
    if filters:
        stmt = stmt.where(and_(*filters))
    result = await session.execute(stmt)
    return result.scalar_one()

async def sa_update(session: AsyncSession, model_class: Type[ModelT], pk_value: str, business_id: Optional[str] = None, **kwargs) -> Optional[ModelT]:
    """Update fields and return updated instance."""
    instance = await sa_get(session, model_class, pk_value, business_id)
    if not instance:
        return None
    for key, value in kwargs.items():
        if value is not None and hasattr(instance, key):
            setattr(instance, key, value)
    await session.flush()
    return instance

async def sa_delete(session: AsyncSession, model_class: Type[ModelT], pk_value: str, business_id: Optional[str] = None) -> bool:
    """Delete by primary key."""
    instance = await sa_get(session, model_class, pk_value, business_id)
    if not instance:
        return False
    await session.delete(instance)
    await session.flush()
    return True

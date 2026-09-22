from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select, func, and_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.pricing.models import PriceList, PriceEntry, DiscountRule as DiscountRuleModel
from app.modules.pricing.repository import (
    AbstractPriceListRepository,
    AbstractPriceEntryRepository,
    PriceListInDB,
    PriceEntryInDB,
)
from app.modules.pricing.schemas import (
    PriceListCreate,
    PriceListStatus,
    PriceListUpdate,
    PriceEntryCreate,
    PriceEntryStatus,
    PriceEntryUpdate,
)
from app.modules.sqla_base import sa_create


def _to_price_list(obj: PriceList) -> PriceListInDB:
    return PriceListInDB(
        id=obj.id,
        business_id=obj.business_id,
        name=obj.name,
        code=obj.code,
        description=obj.description,
        currency=obj.currency,
        status=PriceListStatus(obj.status),
        is_default=obj.is_default,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


def _to_price_entry(obj: PriceEntry) -> PriceEntryInDB:
    return PriceEntryInDB(
        id=obj.id,
        business_id=obj.business_id,
        price_list_id=obj.price_list_id,
        product_id=obj.product_id,
        variant_id=obj.variant_id,
        amount=obj.amount,
        currency=obj.currency,
        effective_from=obj.effective_from,
        effective_to=obj.effective_to,
        status=PriceEntryStatus(obj.status),
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


class SQLAlchemyPriceListRepository(AbstractPriceListRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, business_id: str, data: PriceListCreate) -> PriceListInDB:
        # Check if there are any existing active price lists for this business
        count_stmt = select(func.count()).select_from(PriceList).where(
            PriceList.business_id == business_id,
            PriceList.status == PriceListStatus.ACTIVE.value,
        )
        count_res = await self.session.execute(count_stmt)
        is_default = (count_res.scalar_one() or 0) == 0

        record = {
            "business_id": business_id,
            "name": data.name,
            "code": data.code.strip().upper(),
            "description": data.description,
            "currency": data.currency,
            "status": PriceListStatus.ACTIVE.value,
            "is_default": is_default,
        }
        obj = await sa_create(self.session, PriceList, record)
        return _to_price_list(obj)

    async def get_by_id(self, price_list_id: str, business_id: str) -> Optional[PriceListInDB]:
        stmt = select(PriceList).where(
            PriceList.id == price_list_id,
            PriceList.business_id == business_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_price_list(obj) if obj else None

    async def list_by_business(self, business_id: str, include_archived: bool = False) -> List[PriceListInDB]:
        filters = [PriceList.business_id == business_id]
        if not include_archived:
            filters.append(PriceList.status == PriceListStatus.ACTIVE.value)
        stmt = select(PriceList).where(and_(*filters)).order_by(asc(PriceList.created_at))
        res = await self.session.execute(stmt)
        return [_to_price_list(o) for o in res.scalars().all()]

    async def update(self, price_list_id: str, business_id: str, data: PriceListUpdate) -> Optional[PriceListInDB]:
        stmt = select(PriceList).where(
            PriceList.id == price_list_id,
            PriceList.business_id == business_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            return None
        update_dict = data.model_dump(exclude_unset=True)
        if not update_dict:
            return _to_price_list(obj)
        for field, value in update_dict.items():
            setattr(obj, field, value)
        await self.session.flush()
        return _to_price_list(obj)

    async def archive(self, price_list_id: str, business_id: str) -> Optional[PriceListInDB]:
        stmt = select(PriceList).where(
            PriceList.id == price_list_id,
            PriceList.business_id == business_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            return None
        was_default = obj.is_default
        obj.status = PriceListStatus.ARCHIVED.value
        obj.is_default = False
        if was_default:
            oldest_stmt = (
                select(PriceList)
                .where(
                    PriceList.business_id == business_id,
                    PriceList.status == PriceListStatus.ACTIVE.value,
                )
                .order_by(asc(PriceList.created_at), asc(PriceList.id))
                .limit(1)
            )
            oldest_res = await self.session.execute(oldest_stmt)
            oldest = oldest_res.scalar_one_or_none()
            if oldest:
                oldest.is_default = True
        await self.session.flush()
        return _to_price_list(obj)

    async def find_by_code(self, business_id: str, code: str) -> Optional[PriceListInDB]:
        norm = code.strip().upper()
        stmt = select(PriceList).where(
            PriceList.business_id == business_id,
            func.upper(PriceList.code) == norm,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_price_list(obj) if obj else None

    async def exists_by_code(self, business_id: str, code: str) -> bool:
        return (await self.find_by_code(business_id, code)) is not None

    async def set_default(self, business_id: str, price_list_id: str) -> Optional[PriceListInDB]:
        target_stmt = select(PriceList).where(
            PriceList.id == price_list_id,
            PriceList.business_id == business_id,
            PriceList.status == PriceListStatus.ACTIVE.value,
        )
        target_res = await self.session.execute(target_stmt)
        target = target_res.scalar_one_or_none()
        if not target:
            return None

        # Unset existing default
        unset_stmt = select(PriceList).where(
            PriceList.business_id == business_id,
            PriceList.is_default == True,
        )
        unset_res = await self.session.execute(unset_stmt)
        for pl in unset_res.scalars().all():
            pl.is_default = False

        target.is_default = True
        await self.session.flush()
        return _to_price_list(target)

    async def get_default(self, business_id: str) -> Optional[PriceListInDB]:
        stmt = select(PriceList).where(
            PriceList.business_id == business_id,
            PriceList.is_default == True,
            PriceList.status == PriceListStatus.ACTIVE.value,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_price_list(obj) if obj else None

    @classmethod
    def clear(cls):
        pass


class SQLAlchemyPriceEntryRepository(AbstractPriceEntryRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        business_id: str,
        price_list_id: str,
        currency: str,
        data: PriceEntryCreate,
    ) -> PriceEntryInDB:
        record = {
            "business_id": business_id,
            "price_list_id": price_list_id,
            "product_id": data.product_id,
            "variant_id": data.variant_id,
            "amount": data.amount,
            "currency": currency,
            "effective_from": data.effective_from,
            "effective_to": data.effective_to,
            "status": PriceEntryStatus.ACTIVE.value,
        }
        obj = await sa_create(self.session, PriceEntry, record)
        return _to_price_entry(obj)

    async def get_by_id(self, entry_id: str, business_id: str) -> Optional[PriceEntryInDB]:
        stmt = select(PriceEntry).where(
            PriceEntry.id == entry_id,
            PriceEntry.business_id == business_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_price_entry(obj) if obj else None

    async def list_by_business(self, business_id: str, include_archived: bool = False) -> List[PriceEntryInDB]:
        filters = [PriceEntry.business_id == business_id]
        if not include_archived:
            filters.append(PriceEntry.status == PriceEntryStatus.ACTIVE.value)
        stmt = select(PriceEntry).where(and_(*filters)).order_by(asc(PriceEntry.created_at))
        res = await self.session.execute(stmt)
        return [_to_price_entry(o) for o in res.scalars().all()]

    async def list_by_price_list(self, price_list_id: str, business_id: str, include_archived: bool = False) -> List[PriceEntryInDB]:
        filters = [
            PriceEntry.business_id == business_id,
            PriceEntry.price_list_id == price_list_id,
        ]
        if not include_archived:
            filters.append(PriceEntry.status == PriceEntryStatus.ACTIVE.value)
        stmt = select(PriceEntry).where(and_(*filters)).order_by(asc(PriceEntry.created_at))
        res = await self.session.execute(stmt)
        return [_to_price_entry(o) for o in res.scalars().all()]

    async def list_by_product(self, product_id: str, business_id: str, include_archived: bool = False) -> List[PriceEntryInDB]:
        filters = [
            PriceEntry.business_id == business_id,
            PriceEntry.product_id == product_id,
        ]
        if not include_archived:
            filters.append(PriceEntry.status == PriceEntryStatus.ACTIVE.value)
        stmt = select(PriceEntry).where(and_(*filters)).order_by(asc(PriceEntry.created_at))
        res = await self.session.execute(stmt)
        return [_to_price_entry(o) for o in res.scalars().all()]

    async def list_by_variant(self, variant_id: str, business_id: str, include_archived: bool = False) -> List[PriceEntryInDB]:
        filters = [
            PriceEntry.business_id == business_id,
            PriceEntry.variant_id == variant_id,
        ]
        if not include_archived:
            filters.append(PriceEntry.status == PriceEntryStatus.ACTIVE.value)
        stmt = select(PriceEntry).where(and_(*filters)).order_by(asc(PriceEntry.created_at))
        res = await self.session.execute(stmt)
        return [_to_price_entry(o) for o in res.scalars().all()]

    async def update(self, entry_id: str, business_id: str, data: PriceEntryUpdate) -> Optional[PriceEntryInDB]:
        stmt = select(PriceEntry).where(
            PriceEntry.id == entry_id,
            PriceEntry.business_id == business_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            return None
        update_dict = data.model_dump(exclude_unset=True)
        if not update_dict:
            return _to_price_entry(obj)
        for field, value in update_dict.items():
            setattr(obj, field, value)
        await self.session.flush()
        return _to_price_entry(obj)

    async def archive(self, entry_id: str, business_id: str) -> Optional[PriceEntryInDB]:
        stmt = select(PriceEntry).where(
            PriceEntry.id == entry_id,
            PriceEntry.business_id == business_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            return None
        obj.status = PriceEntryStatus.ARCHIVED.value
        await self.session.flush()
        return _to_price_entry(obj)

    async def find_overlapping_active(
        self,
        business_id: str,
        price_list_id: str,
        product_id: Optional[str],
        variant_id: Optional[str],
        effective_from: datetime,
        effective_to: Optional[datetime],
        exclude_id: Optional[str] = None,
    ) -> List[PriceEntryInDB]:
        filters = [
            PriceEntry.business_id == business_id,
            PriceEntry.price_list_id == price_list_id,
            PriceEntry.status == PriceEntryStatus.ACTIVE.value,
        ]
        if product_id:
            filters.append(PriceEntry.product_id == product_id)
        if variant_id:
            filters.append(PriceEntry.variant_id == variant_id)
        if exclude_id:
            filters.append(PriceEntry.id != exclude_id)

        # SQL overlap: a_start <= b_end AND b_start <= a_end
        cond1 = (PriceEntry.effective_to == None) | (effective_from <= PriceEntry.effective_to)
        cond2 = (effective_to == None) | (PriceEntry.effective_from <= effective_to)
        filters.append(cond1)
        filters.append(cond2)

        stmt = select(PriceEntry).where(and_(*filters))
        res = await self.session.execute(stmt)
        return [_to_price_entry(o) for o in res.scalars().all()]

    async def exists(self, entry_id: str, business_id: str) -> bool:
        stmt = select(func.count()).select_from(PriceEntry).where(
            PriceEntry.id == entry_id,
            PriceEntry.business_id == business_id,
        )
        res = await self.session.execute(stmt)
        return (res.scalar_one() or 0) > 0

    @classmethod
    def clear(cls):
        pass


def _to_discount_rule(obj: DiscountRuleModel) -> "DiscountRuleInDB":
    from app.modules.pricing.schemas import DiscountRuleInDB
    return DiscountRuleInDB(
        id=obj.id,
        business_id=obj.business_id,
        name=obj.name,
        description=obj.description,
        type=obj.type,
        value=obj.value,
        product_id=obj.product_id,
        variant_id=obj.variant_id,
        starts_at=obj.starts_at,
        ends_at=obj.ends_at,
        priority=obj.priority,
        status=obj.status,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


class SQLAlchemyDiscountRuleRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, business_id: str, data: dict) -> "DiscountRuleInDB":
        obj = await sa_create(self.session, DiscountRuleModel, {
            "business_id": business_id,
            **data,
        })
        return _to_discount_rule(obj)

    async def get_by_id(self, rule_id: str, business_id: str) -> Optional["DiscountRuleInDB"]:
        stmt = select(DiscountRuleModel).where(
            DiscountRuleModel.id == rule_id,
            DiscountRuleModel.business_id == business_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_discount_rule(obj) if obj else None

    async def list_by_business(self, business_id: str, include_archived: bool = False) -> List["DiscountRuleInDB"]:
        filters = [DiscountRuleModel.business_id == business_id]
        if not include_archived:
            filters.append(DiscountRuleModel.status != "ARCHIVED")
        stmt = select(DiscountRuleModel).where(and_(*filters)).order_by(
            asc(DiscountRuleModel.priority), asc(DiscountRuleModel.id)
        )
        res = await self.session.execute(stmt)
        return [_to_discount_rule(o) for o in res.scalars().all()]

    async def update(self, rule_id: str, business_id: str, updates: dict) -> Optional["DiscountRuleInDB"]:
        stmt = select(DiscountRuleModel).where(
            DiscountRuleModel.id == rule_id,
            DiscountRuleModel.business_id == business_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            return None
        for k, v in updates.items():
            if v is not None and hasattr(obj, k):
                setattr(obj, k, v)
        await self.session.flush()
        return _to_discount_rule(obj)

    async def update_status(self, rule_id: str, business_id: str, status: str) -> Optional["DiscountRuleInDB"]:
        return await self.update(rule_id, business_id, {"status": status})

    async def delete(self, rule_id: str, business_id: str) -> bool:
        stmt = select(DiscountRuleModel).where(
            DiscountRuleModel.id == rule_id,
            DiscountRuleModel.business_id == business_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            return False
        await self.session.delete(obj)
        await self.session.flush()
        return True

    @classmethod
    def clear(cls):
        pass

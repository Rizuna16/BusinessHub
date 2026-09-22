import uuid
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional

from app.modules.pricing.schemas import (
    PriceEntryCreate,
    PriceEntryStatus,
    PriceEntryUpdate,
    PriceListCreate,
    PriceListStatus,
    PriceListUpdate,
)


@dataclass
class PriceListInDB:
    id: str
    business_id: str
    name: str
    code: str
    description: Optional[str]
    currency: str
    status: PriceListStatus
    is_default: bool
    created_at: datetime
    updated_at: datetime


@dataclass
class PriceEntryInDB:
    id: str
    business_id: str
    price_list_id: str
    product_id: Optional[str]
    variant_id: Optional[str]
    amount: Decimal
    currency: str
    effective_from: datetime
    effective_to: Optional[datetime]
    status: PriceEntryStatus
    created_at: datetime
    updated_at: datetime


class AbstractPriceListRepository(ABC):
    @abstractmethod
    async def create(self, business_id: str, data: PriceListCreate) -> PriceListInDB:
        pass

    @abstractmethod
    async def get_by_id(self, price_list_id: str, business_id: str) -> Optional[PriceListInDB]:
        pass

    @abstractmethod
    async def list_by_business(self, business_id: str, include_archived: bool = False) -> List[PriceListInDB]:
        pass

    @abstractmethod
    async def update(self, price_list_id: str, business_id: str, data: PriceListUpdate) -> Optional[PriceListInDB]:
        pass

    @abstractmethod
    async def archive(self, price_list_id: str, business_id: str) -> Optional[PriceListInDB]:
        pass

    @abstractmethod
    async def find_by_code(self, business_id: str, code: str) -> Optional[PriceListInDB]:
        pass

    @abstractmethod
    async def exists_by_code(self, business_id: str, code: str) -> bool:
        pass

    @abstractmethod
    async def set_default(self, business_id: str, price_list_id: str) -> Optional[PriceListInDB]:
        pass

    @abstractmethod
    async def get_default(self, business_id: str) -> Optional[PriceListInDB]:
        pass

    @abstractmethod
    async def clear(self) -> None:
        pass


class InMemoryPriceListRepository(AbstractPriceListRepository):
    _price_lists: Dict[str, PriceListInDB] = {}

    def _key(self, business_id: str, price_list_id: str) -> str:
        return f"{business_id}:{price_list_id}"

    async def create(self, business_id: str, data: PriceListCreate) -> PriceListInDB:
        now = datetime.now(timezone.utc)
        price_list_id = str(uuid.uuid4())

        # Check if there are any existing active price lists for this business
        active_lists = [
            pl for pl in self._price_lists.values()
            if pl.business_id == business_id and pl.status == PriceListStatus.ACTIVE
        ]
        is_default = len(active_lists) == 0

        price_list = PriceListInDB(
            id=price_list_id,
            business_id=business_id,
            name=data.name,
            code=data.code,
            description=data.description,
            currency=data.currency,
            status=PriceListStatus.ACTIVE,
            is_default=is_default,
            created_at=now,
            updated_at=now,
        )
        self._price_lists[self._key(business_id, price_list_id)] = price_list
        return price_list

    async def get_by_id(self, price_list_id: str, business_id: str) -> Optional[PriceListInDB]:
        return self._price_lists.get(self._key(business_id, price_list_id))

    async def list_by_business(self, business_id: str, include_archived: bool = False) -> List[PriceListInDB]:
        results = [
            pl for pl in self._price_lists.values()
            if pl.business_id == business_id and (include_archived or pl.status == PriceListStatus.ACTIVE)
        ]
        results.sort(key=lambda x: x.created_at)
        return results

    async def update(self, price_list_id: str, business_id: str, data: PriceListUpdate) -> Optional[PriceListInDB]:
        key = self._key(business_id, price_list_id)
        price_list = self._price_lists.get(key)
        if not price_list:
            return None

        update_dict = data.model_dump(exclude_unset=True)
        if not update_dict:
            return price_list

        for field, value in update_dict.items():
            setattr(price_list, field, value)

        price_list.updated_at = datetime.now(timezone.utc)
        self._price_lists[key] = price_list
        return price_list

    async def archive(self, price_list_id: str, business_id: str) -> Optional[PriceListInDB]:
        key = self._key(business_id, price_list_id)
        price_list = self._price_lists.get(key)
        if not price_list:
            return None

        was_default = price_list.is_default
        price_list.status = PriceListStatus.ARCHIVED
        price_list.is_default = False
        price_list.updated_at = datetime.now(timezone.utc)
        self._price_lists[key] = price_list

        if was_default:
            # Reassign default to oldest active price list
            active_lists = [
                pl for pl in self._price_lists.values()
                if pl.business_id == business_id and pl.status == PriceListStatus.ACTIVE
            ]
            if active_lists:
                active_lists.sort(key=lambda x: (x.created_at, x.id))
                oldest = active_lists[0]
                oldest.is_default = True
                oldest.updated_at = datetime.now(timezone.utc)
                self._price_lists[self._key(business_id, oldest.id)] = oldest

        return price_list

    async def find_by_code(self, business_id: str, code: str) -> Optional[PriceListInDB]:
        code_upper = code.strip().upper()
        for pl in self._price_lists.values():
            if pl.business_id == business_id and pl.code.upper() == code_upper:
                return pl
        return None

    async def exists_by_code(self, business_id: str, code: str) -> bool:
        return (await self.find_by_code(business_id, code)) is not None

    async def set_default(self, business_id: str, price_list_id: str) -> Optional[PriceListInDB]:
        target_key = self._key(business_id, price_list_id)
        target = self._price_lists.get(target_key)
        if not target or target.status != PriceListStatus.ACTIVE:
            return None

        now = datetime.now(timezone.utc)
        for pl in self._price_lists.values():
            if pl.business_id == business_id and pl.is_default:
                pl.is_default = False
                pl.updated_at = now

        target.is_default = True
        target.updated_at = now
        self._price_lists[target_key] = target
        return target

    async def get_default(self, business_id: str) -> Optional[PriceListInDB]:
        for pl in self._price_lists.values():
            if pl.business_id == business_id and pl.is_default and pl.status == PriceListStatus.ACTIVE:
                return pl
        return None

    @classmethod
    def clear(cls) -> None:
        cls._price_lists.clear()


class AbstractPriceEntryRepository(ABC):
    @abstractmethod
    async def create(
        self,
        business_id: str,
        price_list_id: str,
        currency: str,
        data: PriceEntryCreate,
    ) -> PriceEntryInDB:
        pass

    @abstractmethod
    async def get_by_id(self, entry_id: str, business_id: str) -> Optional[PriceEntryInDB]:
        pass

    @abstractmethod
    async def list_by_business(self, business_id: str, include_archived: bool = False) -> List[PriceEntryInDB]:
        pass

    @abstractmethod
    async def list_by_price_list(self, price_list_id: str, business_id: str, include_archived: bool = False) -> List[PriceEntryInDB]:
        pass

    @abstractmethod
    async def list_by_product(self, product_id: str, business_id: str, include_archived: bool = False) -> List[PriceEntryInDB]:
        pass

    @abstractmethod
    async def list_by_variant(self, variant_id: str, business_id: str, include_archived: bool = False) -> List[PriceEntryInDB]:
        pass

    @abstractmethod
    async def update(self, entry_id: str, business_id: str, data: PriceEntryUpdate) -> Optional[PriceEntryInDB]:
        pass

    @abstractmethod
    async def archive(self, entry_id: str, business_id: str) -> Optional[PriceEntryInDB]:
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def exists(self, entry_id: str, business_id: str) -> bool:
        pass

    @abstractmethod
    async def clear(self) -> None:
        pass


class InMemoryPriceEntryRepository(AbstractPriceEntryRepository):
    _price_entries: Dict[str, PriceEntryInDB] = {}

    def _key(self, business_id: str, entry_id: str) -> str:
        return f"{business_id}:{entry_id}"

    async def create(
        self,
        business_id: str,
        price_list_id: str,
        currency: str,
        data: PriceEntryCreate,
    ) -> PriceEntryInDB:
        now = datetime.now(timezone.utc)
        entry_id = str(uuid.uuid4())

        entry = PriceEntryInDB(
            id=entry_id,
            business_id=business_id,
            price_list_id=price_list_id,
            product_id=data.product_id if data.product_id else None,
            variant_id=data.variant_id if data.variant_id else None,
            amount=data.amount,
            currency=currency,
            effective_from=data.effective_from,
            effective_to=data.effective_to,
            status=PriceEntryStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        self._price_entries[self._key(business_id, entry_id)] = entry
        return entry

    async def get_by_id(self, entry_id: str, business_id: str) -> Optional[PriceEntryInDB]:
        return self._price_entries.get(self._key(business_id, entry_id))

    async def list_by_business(self, business_id: str, include_archived: bool = False) -> List[PriceEntryInDB]:
        results = [
            pe for pe in self._price_entries.values()
            if pe.business_id == business_id and (include_archived or pe.status == PriceEntryStatus.ACTIVE)
        ]
        results.sort(key=lambda x: x.created_at)
        return results

    async def list_by_price_list(self, price_list_id: str, business_id: str, include_archived: bool = False) -> List[PriceEntryInDB]:
        results = [
            pe for pe in self._price_entries.values()
            if pe.business_id == business_id and pe.price_list_id == price_list_id and (include_archived or pe.status == PriceEntryStatus.ACTIVE)
        ]
        results.sort(key=lambda x: x.created_at)
        return results

    async def list_by_product(self, product_id: str, business_id: str, include_archived: bool = False) -> List[PriceEntryInDB]:
        results = [
            pe for pe in self._price_entries.values()
            if pe.business_id == business_id and pe.product_id == product_id and (include_archived or pe.status == PriceEntryStatus.ACTIVE)
        ]
        results.sort(key=lambda x: x.created_at)
        return results

    async def list_by_variant(self, variant_id: str, business_id: str, include_archived: bool = False) -> List[PriceEntryInDB]:
        results = [
            pe for pe in self._price_entries.values()
            if pe.business_id == business_id and pe.variant_id == variant_id and (include_archived or pe.status == PriceEntryStatus.ACTIVE)
        ]
        results.sort(key=lambda x: x.created_at)
        return results

    async def update(self, entry_id: str, business_id: str, data: PriceEntryUpdate) -> Optional[PriceEntryInDB]:
        key = self._key(business_id, entry_id)
        entry = self._price_entries.get(key)
        if not entry:
            return None

        update_dict = data.model_dump(exclude_unset=True)
        if not update_dict:
            return entry

        for field, value in update_dict.items():
            setattr(entry, field, value)

        entry.updated_at = datetime.now(timezone.utc)
        self._price_entries[key] = entry
        return entry

    async def archive(self, entry_id: str, business_id: str) -> Optional[PriceEntryInDB]:
        key = self._key(business_id, entry_id)
        entry = self._price_entries.get(key)
        if not entry:
            return None

        entry.status = PriceEntryStatus.ARCHIVED
        entry.updated_at = datetime.now(timezone.utc)
        self._price_entries[key] = entry
        return entry

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
        overlapping = []
        for pe in self._price_entries.values():
            if pe.business_id != business_id or pe.price_list_id != price_list_id:
                continue
            if pe.status != PriceEntryStatus.ACTIVE:
                continue
            if exclude_id and pe.id == exclude_id:
                continue

            # Match target
            if product_id and pe.product_id != product_id:
                continue
            if variant_id and pe.variant_id != variant_id:
                continue

            # Overlap check logic:
            # Two periods [A_start, A_end] and [B_start, B_end] overlap if:
            # A_start <= B_end (if B_end is not None) AND B_start <= A_end (if A_end is not None)
            # A is (effective_from, effective_to), B is (pe.effective_from, pe.effective_to)
            a_start, a_end = effective_from, effective_to
            b_start, b_end = pe.effective_from, pe.effective_to

            cond1 = (b_end is None) or (a_start <= b_end)
            cond2 = (a_end is None) or (b_start <= a_end)

            if cond1 and cond2:
                overlapping.append(pe)

        return overlapping

    async def exists(self, entry_id: str, business_id: str) -> bool:
        return self._key(business_id, entry_id) in self._price_entries

    @classmethod
    def clear(cls) -> None:
        cls._price_entries.clear()


class AbstractDiscountRuleRepository(ABC):
    @abstractmethod
    async def create(self, business_id: str, data: dict) -> "DiscountRuleInDB": ...

    @abstractmethod
    async def get_by_id(self, rule_id: str, business_id: str) -> Optional["DiscountRuleInDB"]: ...

    @abstractmethod
    async def list_by_business(self, business_id: str, include_archived: bool = False) -> List["DiscountRuleInDB"]: ...

    @abstractmethod
    async def update(self, rule_id: str, business_id: str, updates: dict) -> Optional["DiscountRuleInDB"]: ...

    @abstractmethod
    async def update_status(self, rule_id: str, business_id: str, status: str) -> Optional["DiscountRuleInDB"]: ...

    @abstractmethod
    async def delete(self, rule_id: str, business_id: str) -> bool: ...

    @classmethod
    @abstractmethod
    def clear(cls): ...


class InMemoryDiscountRuleRepository(AbstractDiscountRuleRepository):
    _rules: Dict[str, "DiscountRuleInDB"] = {}
    _lock = asyncio.Lock()

    async def create(self, business_id: str, data: dict) -> "DiscountRuleInDB":
        from app.modules.pricing.schemas import DiscountRuleInDB
        async with self._lock:
            now = datetime.now(timezone.utc)
            rule = DiscountRuleInDB(
                id=str(uuid.uuid4()),
                business_id=business_id,
                name=data["name"],
                description=data.get("description"),
                type=data["type"],
                value=data["value"],
                currency=data.get("currency", "IDR"),
                product_id=data.get("product_id"),
                variant_id=data.get("variant_id"),
                starts_at=data["starts_at"],
                ends_at=data.get("ends_at"),
                priority=data.get("priority", 100),
                status="ACTIVE",
                created_at=now,
                updated_at=now,
            )
            self._rules[rule.id] = rule
            return rule

    async def get_by_id(self, rule_id: str, business_id: str) -> Optional["DiscountRuleInDB"]:
        rule = self._rules.get(rule_id)
        if rule and rule.business_id == business_id:
            return rule
        return None

    async def list_by_business(self, business_id: str, include_archived: bool = False) -> List["DiscountRuleInDB"]:
        results = []
        for r in self._rules.values():
            if r.business_id == business_id:
                if include_archived or r.status != "ARCHIVED":
                    results.append(r)
        results.sort(key=lambda r: (r.priority, r.id))
        return results

    async def update(self, rule_id: str, business_id: str, updates: dict) -> Optional["DiscountRuleInDB"]:
        from app.modules.pricing.schemas import DiscountRuleInDB
        async with self._lock:
            rule = self._rules.get(rule_id)
            if not rule or rule.business_id != business_id:
                return None
            current = rule.model_dump()
            for k, v in updates.items():
                if v is not None:
                    current[k] = v
            current["updated_at"] = datetime.now(timezone.utc)
            updated = DiscountRuleInDB(**current)
            self._rules[rule_id] = updated
            return updated

    async def update_status(self, rule_id: str, business_id: str, status: str) -> Optional["DiscountRuleInDB"]:
        return await self.update(rule_id, business_id, {"status": status})

    async def delete(self, rule_id: str, business_id: str) -> bool:
        async with self._lock:
            rule = self._rules.get(rule_id)
            if rule and rule.business_id == business_id:
                del self._rules[rule_id]
                return True
            return False

    @classmethod
    def clear(cls):
        cls._rules.clear()


price_list_repository = InMemoryPriceListRepository()
price_entry_repository = InMemoryPriceEntryRepository()
discount_rule_repository = InMemoryDiscountRuleRepository()

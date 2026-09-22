from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
from decimal import Decimal
import uuid

from app.modules.sales_order.schemas import (
    QuotationInDB,
    QuotationLineInDB,
    QuotationStatus,
    SalesOrderInDB,
    SalesOrderLineInDB,
    SalesOrderStatus,
    SalesOrderReservationInDB,
    ReservationStatus,
)


class AbstractQuotationRepository(ABC):
    @abstractmethod
    async def create_quotation(self, business_id: str, customer_id: Optional[str], branch_id: str, warehouse_id: str, quotation_number: str, quotation_date: datetime, validity_date: Optional[datetime], created_by_user_id: str, notes: Optional[str]) -> QuotationInDB:
        pass

    @abstractmethod
    async def get_quotation_by_id(self, quotation_id: str, business_id: str) -> Optional[QuotationInDB]:
        pass

    @abstractmethod
    async def get_quotation_by_number(self, business_id: str, quotation_number: str) -> Optional[QuotationInDB]:
        pass

    @abstractmethod
    async def list_quotations(self, business_id: str, status: Optional[QuotationStatus], customer_id: Optional[str], branch_id: Optional[str], search: Optional[str], page: int, page_size: int) -> Tuple[List[QuotationInDB], int]:
        pass

    @abstractmethod
    async def update_quotation(self, quotation_id: str, business_id: str, **kwargs) -> Optional[QuotationInDB]:
        pass

    @abstractmethod
    async def get_next_quotation_sequence(self, business_id: str) -> int:
        pass

    @abstractmethod
    async def create_line(self, quotation_id: str, product_id: str, variant_id: Optional[str], description: Optional[str], quantity: Decimal, unit_price: Decimal, discount_amount: Decimal, tax_amount: Decimal, line_subtotal: Decimal, line_total: Decimal, discount_rule_id: Optional[str] = None, discount_rule_name_snapshot: Optional[str] = None) -> QuotationLineInDB:
        pass

    @abstractmethod
    async def get_line_by_id(self, line_id: str, quotation_id: str) -> Optional[QuotationLineInDB]:
        pass

    @abstractmethod
    async def list_lines_for_quotation(self, quotation_id: str) -> List[QuotationLineInDB]:
        pass

    @abstractmethod
    async def update_line(self, line_id: str, quotation_id: str, **kwargs) -> Optional[QuotationLineInDB]:
        pass

    @abstractmethod
    async def delete_line(self, line_id: str, quotation_id: str) -> bool:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemoryQuotationRepository(AbstractQuotationRepository):
    _quotations: Dict[str, QuotationInDB] = {}
    _lines: Dict[str, QuotationLineInDB] = {}
    _sequences: Dict[str, int] = {}

    async def create_quotation(
        self,
        business_id: str,
        customer_id: Optional[str],
        branch_id: str,
        warehouse_id: str,
        quotation_number: str,
        quotation_date: datetime,
        validity_date: Optional[datetime],
        created_by_user_id: str,
        notes: Optional[str],
    ) -> QuotationInDB:
        qid = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        q = QuotationInDB(
            id=qid,
            business_id=business_id,
            customer_id=customer_id,
            branch_id=branch_id,
            warehouse_id=warehouse_id,
            quotation_number=quotation_number,
            quotation_date=quotation_date,
            validity_date=validity_date,
            notes=notes,
            status=QuotationStatus.DRAFT,
            is_deleted=False,
            subtotal=Decimal("0"),
            discount_total=Decimal("0"),
            tax_total=Decimal("0"),
            grand_total=Decimal("0"),
            created_by_user_id=created_by_user_id,
            created_at=now,
            updated_at=now,
        )
        self._quotations[qid] = q
        return q

    async def get_quotation_by_id(self, quotation_id: str, business_id: str) -> Optional[QuotationInDB]:
        q = self._quotations.get(quotation_id)
        if not q or q.business_id != business_id or q.is_deleted:
            return None
        return q

    async def get_quotation_by_number(self, business_id: str, quotation_number: str) -> Optional[QuotationInDB]:
        for q in self._quotations.values():
            if q.business_id == business_id and q.quotation_number == quotation_number and not q.is_deleted:
                return q
        return None

    async def list_quotations(
        self,
        business_id: str,
        status: Optional[QuotationStatus],
        customer_id: Optional[str],
        branch_id: Optional[str],
        search: Optional[str],
        page: int,
        page_size: int,
    ) -> Tuple[List[QuotationInDB], int]:
        items = []
        for q in self._quotations.values():
            if q.business_id != business_id or q.is_deleted:
                continue
            if status and q.status != status:
                continue
            if customer_id and q.customer_id != customer_id:
                continue
            if branch_id and q.branch_id != branch_id:
                continue
            if search:
                s = search.lower()
                if s not in q.quotation_number.lower() and (not q.notes or s not in q.notes.lower()):
                    continue
            items.append(q)

        items.sort(key=lambda x: x.created_at, reverse=True)
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        return items[start:end], total

    async def update_quotation(self, quotation_id: str, business_id: str, **kwargs) -> Optional[QuotationInDB]:
        q = await self.get_quotation_by_id(quotation_id, business_id)
        if not q:
            return None
        data = q.model_dump()
        for k, v in kwargs.items():
            if v is not None or k in ["customer_id", "validity_date", "notes", "sent_by_user_id", "sent_at", "accepted_by_user_id", "accepted_at", "rejected_by_user_id", "rejected_at", "expired_by_user_id", "expired_at", "cancelled_by_user_id", "cancelled_at", "converted_at", "converted_sales_order_id", "status"]:
                data[k] = v
        data["updated_at"] = datetime.now(timezone.utc)
        updated = QuotationInDB(**data)
        self._quotations[quotation_id] = updated
        return updated

    async def get_next_quotation_sequence(self, business_id: str) -> int:
        cur = self._sequences.get(business_id, 0) + 1
        self._sequences[business_id] = cur
        return cur

    async def create_line(
        self,
        quotation_id: str,
        product_id: str,
        variant_id: Optional[str],
        description: Optional[str],
        quantity: Decimal,
        unit_price: Decimal,
        discount_amount: Decimal,
        tax_amount: Decimal,
        line_subtotal: Decimal,
        line_total: Decimal,
        discount_rule_id: Optional[str] = None,
        discount_rule_name_snapshot: Optional[str] = None,
    ) -> QuotationLineInDB:
        lid = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        line = QuotationLineInDB(
            id=lid,
            quotation_id=quotation_id,
            product_id=product_id,
            variant_id=variant_id,
            description=description,
            quantity=quantity,
            unit_price=unit_price,
            discount_amount=discount_amount,
            discount_rule_id=discount_rule_id,
            discount_rule_name_snapshot=discount_rule_name_snapshot,
            tax_amount=tax_amount,
            line_subtotal=line_subtotal,
            line_total=line_total,
            created_at=now,
            updated_at=now,
        )
        self._lines[lid] = line
        return line

    async def get_line_by_id(self, line_id: str, quotation_id: str) -> Optional[QuotationLineInDB]:
        l = self._lines.get(line_id)
        if not l or l.quotation_id != quotation_id:
            return None
        return l

    async def list_lines_for_quotation(self, quotation_id: str) -> List[QuotationLineInDB]:
        return [l for l in self._lines.values() if l.quotation_id == quotation_id]

    async def update_line(self, line_id: str, quotation_id: str, **kwargs) -> Optional[QuotationLineInDB]:
        l = await self.get_line_by_id(line_id, quotation_id)
        if not l:
            return None
        data = l.model_dump()
        for k, v in kwargs.items():
            if v is not None:
                data[k] = v
        data["updated_at"] = datetime.now(timezone.utc)
        updated = QuotationLineInDB(**data)
        self._lines[line_id] = updated
        return updated

    async def delete_line(self, line_id: str, quotation_id: str) -> bool:
        l = await self.get_line_by_id(line_id, quotation_id)
        if not l:
            return False
        del self._lines[line_id]
        return True

    @classmethod
    def clear(cls):
        cls._quotations.clear()
        cls._lines.clear()
        cls._sequences.clear()


quotation_repository = InMemoryQuotationRepository()


class AbstractSalesOrderRepository(ABC):
    @abstractmethod
    async def create_order(self, business_id: str, customer_id: Optional[str], branch_id: str, warehouse_id: str, sales_order_number: str, order_date: datetime, created_by_user_id: str, notes: Optional[str]) -> SalesOrderInDB:
        pass

    @abstractmethod
    async def get_order_by_id(self, order_id: str, business_id: str) -> Optional[SalesOrderInDB]:
        pass

    @abstractmethod
    async def get_sales_order_for_update(self, order_id: str, business_id: str) -> Optional[SalesOrderInDB]:
        pass

    @abstractmethod
    async def get_order_by_number(self, business_id: str, order_number: str) -> Optional[SalesOrderInDB]:
        pass

    @abstractmethod
    async def list_orders(self, business_id: str, status: Optional[SalesOrderStatus], customer_id: Optional[str], branch_id: Optional[str], search: Optional[str], page: int, page_size: int) -> Tuple[List[SalesOrderInDB], int]:
        pass

    @abstractmethod
    async def update_order(self, order_id: str, business_id: str, **kwargs) -> Optional[SalesOrderInDB]:
        pass

    @abstractmethod
    async def get_next_order_sequence(self, business_id: str) -> int:
        pass

    @abstractmethod
    async def create_line(self, sales_order_id: str, product_id: str, variant_id: Optional[str], description: Optional[str], quantity_ordered: Decimal, unit_price: Decimal, discount_amount: Decimal, tax_amount: Decimal, line_subtotal: Decimal, line_total: Decimal, discount_rule_id: Optional[str] = None, discount_rule_name_snapshot: Optional[str] = None) -> SalesOrderLineInDB:
        pass

    @abstractmethod
    async def get_line_by_id(self, line_id: str, sales_order_id: str) -> Optional[SalesOrderLineInDB]:
        pass

    @abstractmethod
    async def list_lines_for_order(self, sales_order_id: str) -> List[SalesOrderLineInDB]:
        pass

    @abstractmethod
    async def update_line(self, line_id: str, sales_order_id: str, **kwargs) -> Optional[SalesOrderLineInDB]:
        pass

    @abstractmethod
    async def delete_line(self, line_id: str, sales_order_id: str) -> bool:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemorySalesOrderRepository(AbstractSalesOrderRepository):
    _orders: Dict[str, SalesOrderInDB] = {}
    _lines: Dict[str, SalesOrderLineInDB] = {}
    _sequences: Dict[str, int] = {}

    async def create_order(
        self,
        business_id: str,
        customer_id: Optional[str],
        branch_id: str,
        warehouse_id: str,
        sales_order_number: str,
        order_date: datetime,
        created_by_user_id: str,
        notes: Optional[str],
    ) -> SalesOrderInDB:
        oid = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        o = SalesOrderInDB(
            id=oid,
            business_id=business_id,
            customer_id=customer_id,
            branch_id=branch_id,
            warehouse_id=warehouse_id,
            sales_order_number=sales_order_number,
            order_date=order_date,
            notes=notes,
            status=SalesOrderStatus.DRAFT,
            is_deleted=False,
            subtotal=Decimal("0"),
            discount_total=Decimal("0"),
            tax_total=Decimal("0"),
            grand_total=Decimal("0"),
            created_by_user_id=created_by_user_id,
            created_at=now,
            updated_at=now,
        )
        self._orders[oid] = o
        return o

    async def get_order_by_id(self, order_id: str, business_id: str) -> Optional[SalesOrderInDB]:
        o = self._orders.get(order_id)
        if not o or o.business_id != business_id or o.is_deleted:
            return None
        return o

    async def get_sales_order_for_update(self, order_id: str, business_id: str) -> Optional[SalesOrderInDB]:
        return await self.get_order_by_id(order_id, business_id)

    async def get_order_by_number(self, business_id: str, order_number: str) -> Optional[SalesOrderInDB]:
        for o in self._orders.values():
            if o.business_id == business_id and o.sales_order_number == order_number and not o.is_deleted:
                return o
        return None

    async def list_orders(
        self,
        business_id: str,
        status: Optional[SalesOrderStatus],
        customer_id: Optional[str],
        branch_id: Optional[str],
        search: Optional[str],
        page: int,
        page_size: int,
    ) -> Tuple[List[SalesOrderInDB], int]:
        items = []
        for o in self._orders.values():
            if o.business_id != business_id or o.is_deleted:
                continue
            if status and o.status != status:
                continue
            if customer_id and o.customer_id != customer_id:
                continue
            if branch_id and o.branch_id != branch_id:
                continue
            if search:
                s = search.lower()
                if s not in o.sales_order_number.lower() and (not o.notes or s not in o.notes.lower()):
                    continue
            items.append(o)

        items.sort(key=lambda x: x.created_at, reverse=True)
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        return items[start:end], total

    async def update_order(self, order_id: str, business_id: str, **kwargs) -> Optional[SalesOrderInDB]:
        o = await self.get_order_by_id(order_id, business_id)
        if not o:
            return None
        data = o.model_dump()
        for k, v in kwargs.items():
            if v is not None or k in ["customer_id", "notes", "confirmed_by_user_id", "confirmed_at", "cancelled_by_user_id", "cancelled_at", "fulfilled_by_user_id", "fulfilled_at", "status"]:
                data[k] = v
        data["updated_at"] = datetime.now(timezone.utc)
        updated = SalesOrderInDB(**data)
        self._orders[order_id] = updated
        return updated

    async def get_next_order_sequence(self, business_id: str) -> int:
        cur = self._sequences.get(business_id, 0) + 1
        self._sequences[business_id] = cur
        return cur

    async def create_line(
        self,
        sales_order_id: str,
        product_id: str,
        variant_id: Optional[str],
        description: Optional[str],
        quantity_ordered: Decimal,
        unit_price: Decimal,
        discount_amount: Decimal,
        tax_amount: Decimal,
        line_subtotal: Decimal,
        line_total: Decimal,
        discount_rule_id: Optional[str] = None,
        discount_rule_name_snapshot: Optional[str] = None,
    ) -> SalesOrderLineInDB:
        lid = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        line = SalesOrderLineInDB(
            id=lid,
            sales_order_id=sales_order_id,
            product_id=product_id,
            variant_id=variant_id,
            description=description,
            quantity_ordered=quantity_ordered,
            quantity_fulfilled=Decimal("0"),
            quantity_remaining=quantity_ordered,
            unit_price=unit_price,
            discount_amount=discount_amount,
            discount_rule_id=discount_rule_id,
            discount_rule_name_snapshot=discount_rule_name_snapshot,
            tax_amount=tax_amount,
            line_subtotal=line_subtotal,
            line_total=line_total,
            created_at=now,
            updated_at=now,
        )
        self._lines[lid] = line
        return line

    async def get_line_by_id(self, line_id: str, sales_order_id: str) -> Optional[SalesOrderLineInDB]:
        l = self._lines.get(line_id)
        if not l or l.sales_order_id != sales_order_id:
            return None
        return l

    async def list_lines_for_order(self, sales_order_id: str) -> List[SalesOrderLineInDB]:
        return [l for l in self._lines.values() if l.sales_order_id == sales_order_id]

    async def update_line(self, line_id: str, sales_order_id: str, **kwargs) -> Optional[SalesOrderLineInDB]:
        l = await self.get_line_by_id(line_id, sales_order_id)
        if not l:
            return None
        data = l.model_dump()
        for k, v in kwargs.items():
            if v is not None:
                data[k] = v
        data["updated_at"] = datetime.now(timezone.utc)
        updated = SalesOrderLineInDB(**data)
        self._lines[line_id] = updated
        return updated

    async def delete_line(self, line_id: str, sales_order_id: str) -> bool:
        l = await self.get_line_by_id(line_id, sales_order_id)
        if not l:
            return False
        del self._lines[line_id]
        return True

    @classmethod
    def clear(cls):
        cls._orders.clear()
        cls._lines.clear()
        cls._sequences.clear()


sales_order_repository = InMemorySalesOrderRepository()


class AbstractReservationRepository(ABC):
    @abstractmethod
    async def create_reservation(self, business_id: str, sales_order_id: str, sales_order_line_id: str, warehouse_id: str, product_id: str, variant_id: Optional[str], quantity: Decimal) -> SalesOrderReservationInDB:
        pass

    @abstractmethod
    async def get_by_id(self, reservation_id: str, business_id: str) -> Optional[SalesOrderReservationInDB]:
        pass

    @abstractmethod
    async def get_reservation_for_update(self, reservation_id: str) -> Optional[SalesOrderReservationInDB]:
        pass

    @abstractmethod
    async def list_by_order(self, sales_order_id: str) -> List[SalesOrderReservationInDB]:
        pass

    @abstractmethod
    async def list_by_order_for_update(self, sales_order_id: str) -> List[SalesOrderReservationInDB]:
        pass

    @abstractmethod
    async def list_active_by_warehouse_product(self, business_id: str, warehouse_id: str, product_id: str, variant_id: Optional[str]) -> List[SalesOrderReservationInDB]:
        pass

    @abstractmethod
    async def list_active_reservations_for_update(self, business_id: str, warehouse_id: str, product_id: str, variant_id: Optional[str]) -> List[SalesOrderReservationInDB]:
        pass

    @abstractmethod
    async def update_status(self, reservation_id: str, status: ReservationStatus) -> Optional[SalesOrderReservationInDB]:
        pass

    @abstractmethod
    async def update_quantity(self, reservation_id: str, quantity: Decimal) -> Optional[SalesOrderReservationInDB]:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemoryReservationRepository(AbstractReservationRepository):
    _reservations: Dict[str, SalesOrderReservationInDB] = {}

    async def create_reservation(
        self,
        business_id: str,
        sales_order_id: str,
        sales_order_line_id: str,
        warehouse_id: str,
        product_id: str,
        variant_id: Optional[str],
        quantity: Decimal,
    ) -> SalesOrderReservationInDB:
        rid = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        r = SalesOrderReservationInDB(
            id=rid,
            business_id=business_id,
            sales_order_id=sales_order_id,
            sales_order_line_id=sales_order_line_id,
            warehouse_id=warehouse_id,
            product_id=product_id,
            variant_id=variant_id,
            quantity=quantity,
            status=ReservationStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        self._reservations[rid] = r
        return r

    async def get_by_id(self, reservation_id: str, business_id: str) -> Optional[SalesOrderReservationInDB]:
        r = self._reservations.get(reservation_id)
        if not r or r.business_id != business_id:
            return None
        return r

    async def get_reservation_for_update(self, reservation_id: str) -> Optional[SalesOrderReservationInDB]:
        r = self._reservations.get(reservation_id)
        if not r:
            return None
        return r

    async def list_by_order(self, sales_order_id: str) -> List[SalesOrderReservationInDB]:
        return [r for r in self._reservations.values() if r.sales_order_id == sales_order_id]

    async def list_by_order_for_update(self, sales_order_id: str) -> List[SalesOrderReservationInDB]:
        return await self.list_by_order(sales_order_id)

    async def list_active_by_warehouse_product(
        self, business_id: str, warehouse_id: str, product_id: str, variant_id: Optional[str]
    ) -> List[SalesOrderReservationInDB]:
        results = []
        for r in self._reservations.values():
            if (
                r.business_id == business_id
                and r.warehouse_id == warehouse_id
                and r.product_id == product_id
                and r.variant_id == variant_id
                and r.status == ReservationStatus.ACTIVE
            ):
                results.append(r)
        return results

    async def list_active_reservations_for_update(
        self, business_id: str, warehouse_id: str, product_id: str, variant_id: Optional[str]
    ) -> List[SalesOrderReservationInDB]:
        return await self.list_active_by_warehouse_product(business_id, warehouse_id, product_id, variant_id)

    async def update_status(self, reservation_id: str, status: ReservationStatus) -> Optional[SalesOrderReservationInDB]:
        r = self._reservations.get(reservation_id)
        if not r:
            return None
        data = r.model_dump()
        data["status"] = status
        data["updated_at"] = datetime.now(timezone.utc)
        updated = SalesOrderReservationInDB(**data)
        self._reservations[reservation_id] = updated
        return updated

    async def update_quantity(self, reservation_id: str, quantity: Decimal) -> Optional[SalesOrderReservationInDB]:
        r = self._reservations.get(reservation_id)
        if not r:
            return None
        data = r.model_dump()
        data["quantity"] = quantity
        data["updated_at"] = datetime.now(timezone.utc)
        updated = SalesOrderReservationInDB(**data)
        self._reservations[reservation_id] = updated
        return updated

    @classmethod
    def clear(cls):
        cls._reservations.clear()


reservation_repository = InMemoryReservationRepository()

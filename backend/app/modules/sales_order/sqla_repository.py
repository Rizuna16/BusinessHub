import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Any
from decimal import Decimal

from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sales_order.models import (
    Quotation as QuotationModel,
    QuotationLine as QuotationLineModel,
    SalesOrder as SalesOrderModel,
    SalesOrderLine as SalesOrderLineModel,
    SalesOrderReservation as ReservationModel,
)
from app.modules.sales_order.repository import (
    AbstractQuotationRepository,
    AbstractSalesOrderRepository,
    AbstractReservationRepository,
)
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
from app.modules.sqla_base import sa_create


def _to_quotation_in_db(obj: QuotationModel) -> QuotationInDB:
    return QuotationInDB(
        id=obj.id,
        business_id=obj.business_id,
        customer_id=obj.customer_id,
        branch_id=obj.branch_id,
        warehouse_id=obj.warehouse_id,
        quotation_number=obj.quotation_number,
        quotation_date=obj.quotation_date,
        validity_date=obj.validity_date,
        notes=obj.notes,
        status=QuotationStatus(obj.status),
        is_deleted=obj.is_deleted,
        subtotal=obj.subtotal,
        discount_total=obj.discount_total,
        tax_total=obj.tax_total,
        grand_total=obj.grand_total,
        created_by_user_id=obj.created_by_user_id,
        sent_by_user_id=obj.sent_by_user_id,
        sent_at=obj.sent_at,
        accepted_by_user_id=obj.accepted_by_user_id,
        accepted_at=obj.accepted_at,
        rejected_by_user_id=obj.rejected_by_user_id,
        rejected_at=obj.rejected_at,
        expired_by_user_id=obj.expired_by_user_id,
        expired_at=obj.expired_at,
        cancelled_by_user_id=obj.cancelled_by_user_id,
        cancelled_at=obj.cancelled_at,
        converted_at=obj.converted_at,
        converted_sales_order_id=obj.converted_sales_order_id,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


def _to_quotation_line_in_db(obj: QuotationLineModel) -> QuotationLineInDB:
    return QuotationLineInDB(
        id=obj.id,
        quotation_id=obj.quotation_id,
        product_id=obj.product_id,
        variant_id=obj.variant_id,
        description=obj.description,
        quantity=obj.quantity,
        unit_price=obj.unit_price,
        discount_amount=obj.discount_amount,
        tax_amount=obj.tax_amount,
        line_subtotal=obj.line_subtotal,
        line_total=obj.line_total,
        tax_snapshot=obj.tax_snapshot,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


def _to_sales_order_in_db(obj: SalesOrderModel) -> SalesOrderInDB:
    return SalesOrderInDB(
        id=obj.id,
        business_id=obj.business_id,
        customer_id=obj.customer_id,
        branch_id=obj.branch_id,
        warehouse_id=obj.warehouse_id,
        sales_order_number=obj.sales_order_number,
        order_date=obj.order_date,
        notes=obj.notes,
        status=SalesOrderStatus(obj.status),
        is_deleted=obj.is_deleted,
        subtotal=obj.subtotal,
        discount_total=obj.discount_total,
        tax_total=obj.tax_total,
        grand_total=obj.grand_total,
        created_by_user_id=obj.created_by_user_id,
        confirmed_by_user_id=obj.confirmed_by_user_id,
        confirmed_at=obj.confirmed_at,
        cancelled_by_user_id=obj.cancelled_by_user_id,
        cancelled_at=obj.cancelled_at,
        fulfilled_by_user_id=obj.fulfilled_by_user_id,
        fulfilled_at=obj.fulfilled_at,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


def _to_sales_order_line_in_db(obj: SalesOrderLineModel) -> SalesOrderLineInDB:
    return SalesOrderLineInDB(
        id=obj.id,
        sales_order_id=obj.sales_order_id,
        product_id=obj.product_id,
        variant_id=obj.variant_id,
        description=obj.description,
        quantity_ordered=obj.quantity_ordered,
        quantity_fulfilled=obj.quantity_fulfilled,
        quantity_remaining=obj.quantity_remaining,
        unit_price=obj.unit_price,
        discount_amount=obj.discount_amount,
        tax_amount=obj.tax_amount,
        line_subtotal=obj.line_subtotal,
        line_total=obj.line_total,
        tax_snapshot=obj.tax_snapshot,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


def _to_reservation_in_db(obj: ReservationModel) -> SalesOrderReservationInDB:
    return SalesOrderReservationInDB(
        id=obj.id,
        business_id=obj.business_id,
        sales_order_id=obj.sales_order_id,
        sales_order_line_id=obj.sales_order_line_id,
        warehouse_id=obj.warehouse_id,
        product_id=obj.product_id,
        variant_id=obj.variant_id,
        quantity=obj.quantity,
        status=ReservationStatus(obj.status),
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


class SQLAlchemyQuotationRepository(AbstractQuotationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

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
        data = {
            "id": str(uuid.uuid4()),
            "business_id": business_id,
            "customer_id": customer_id,
            "branch_id": branch_id,
            "warehouse_id": warehouse_id,
            "quotation_number": quotation_number,
            "quotation_date": quotation_date,
            "validity_date": validity_date,
            "notes": notes,
            "status": QuotationStatus.DRAFT.value,
            "is_deleted": False,
            "subtotal": Decimal("0"),
            "discount_total": Decimal("0"),
            "tax_total": Decimal("0"),
            "grand_total": Decimal("0"),
            "created_by_user_id": created_by_user_id,
        }
        obj = await sa_create(self.session, QuotationModel, data)
        return _to_quotation_in_db(obj)

    async def get_quotation_by_id(self, quotation_id: str, business_id: str) -> Optional[QuotationInDB]:
        stmt = select(QuotationModel).where(
            QuotationModel.id == quotation_id,
            QuotationModel.business_id == business_id,
            QuotationModel.is_deleted == False,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_quotation_in_db(obj) if obj else None

    async def get_quotation_by_number(self, business_id: str, quotation_number: str) -> Optional[QuotationInDB]:
        stmt = select(QuotationModel).where(
            QuotationModel.business_id == business_id,
            QuotationModel.quotation_number == quotation_number,
            QuotationModel.is_deleted == False,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_quotation_in_db(obj) if obj else None

    async def list_quotations(
        self, business_id: str, status: Optional[QuotationStatus], customer_id: Optional[str],
        branch_id: Optional[str], search: Optional[str], page: int, page_size: int,
    ) -> Tuple[List[QuotationInDB], int]:
        filters = [
            QuotationModel.business_id == business_id,
            QuotationModel.is_deleted == False,
        ]
        if status is not None:
            filters.append(QuotationModel.status == status.value)
        if customer_id is not None:
            filters.append(QuotationModel.customer_id == customer_id)
        if branch_id is not None:
            filters.append(QuotationModel.branch_id == branch_id)
        if search:
            filters.append(
                or_(
                    QuotationModel.quotation_number.ilike(f"%{search}%"),
                    QuotationModel.notes.ilike(f"%{search}%"),
                )
            )
        count_stmt = select(func.count()).select_from(QuotationModel).where(and_(*filters))
        total = (await self.session.execute(count_stmt)).scalar_one()
        stmt = (
            select(QuotationModel)
            .where(and_(*filters))
            .order_by(desc(QuotationModel.created_at))
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        result = await self.session.execute(stmt)
        items = [_to_quotation_in_db(o) for o in result.scalars().all()]
        return items, total

    async def update_quotation(self, quotation_id: str, business_id: str, **kwargs) -> Optional[QuotationInDB]:
        stmt = select(QuotationModel).where(
            QuotationModel.id == quotation_id,
            QuotationModel.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        for key, value in kwargs.items():
            if key == "status" and value is not None:
                obj.status = value.value if hasattr(value, "value") else value
            elif hasattr(obj, key) and (value is not None or key in [
                "customer_id", "validity_date", "notes", "sent_by_user_id", "sent_at",
                "accepted_by_user_id", "accepted_at", "rejected_by_user_id", "rejected_at",
                "expired_by_user_id", "expired_at", "cancelled_by_user_id", "cancelled_at",
                "converted_at", "converted_sales_order_id", "status",
            ]):
                setattr(obj, key, value)
        obj.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return _to_quotation_in_db(obj)

    async def get_next_quotation_sequence(self, business_id: str) -> int:
        from sqlalchemy import Integer
        stmt = select(func.max(func.cast(QuotationModel.quotation_number, Integer))).where(
            QuotationModel.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        max_num = result.scalar_one()
        if max_num is None:
            return 1
        try:
            return int(max_num) + 1
        except (ValueError, TypeError):
            return 1

    async def create_line(
        self, quotation_id: str, product_id: str, variant_id: Optional[str], description: Optional[str],
        quantity: Decimal, unit_price: Decimal, discount_amount: Decimal, tax_amount: Decimal,
        line_subtotal: Decimal, line_total: Decimal,
        discount_rule_id: Optional[str] = None, discount_rule_name_snapshot: Optional[str] = None,
    ) -> QuotationLineInDB:
        data = {
            "id": str(uuid.uuid4()),
            "quotation_id": quotation_id,
            "product_id": product_id,
            "variant_id": variant_id,
            "description": description,
            "quantity": quantity,
            "unit_price": unit_price,
            "discount_amount": discount_amount,
            "discount_rule_id": discount_rule_id,
            "discount_rule_name_snapshot": discount_rule_name_snapshot,
            "tax_amount": tax_amount,
            "line_subtotal": line_subtotal,
            "line_total": line_total,
        }
        obj = await sa_create(self.session, QuotationLineModel, data)
        return _to_quotation_line_in_db(obj)

    async def get_line_by_id(self, line_id: str, quotation_id: str) -> Optional[QuotationLineInDB]:
        stmt = select(QuotationLineModel).where(
            QuotationLineModel.id == line_id,
            QuotationLineModel.quotation_id == quotation_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_quotation_line_in_db(obj) if obj else None

    async def list_lines_for_quotation(self, quotation_id: str) -> List[QuotationLineInDB]:
        stmt = (
            select(QuotationLineModel)
            .where(QuotationLineModel.quotation_id == quotation_id)
            .order_by(QuotationLineModel.created_at, QuotationLineModel.id)
        )
        result = await self.session.execute(stmt)
        return [_to_quotation_line_in_db(o) for o in result.scalars().all()]

    async def update_line(self, line_id: str, quotation_id: str, **kwargs) -> Optional[QuotationLineInDB]:
        stmt = select(QuotationLineModel).where(
            QuotationLineModel.id == line_id,
            QuotationLineModel.quotation_id == quotation_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        for key, value in kwargs.items():
            if value is not None and hasattr(obj, key):
                setattr(obj, key, value)
        obj.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return _to_quotation_line_in_db(obj)

    async def delete_line(self, line_id: str, quotation_id: str) -> bool:
        stmt = select(QuotationLineModel).where(
            QuotationLineModel.id == line_id,
            QuotationLineModel.quotation_id == quotation_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return False
        await self.session.delete(obj)
        await self.session.flush()
        return True

    @classmethod
    def clear(cls):
        pass


class SQLAlchemySalesOrderRepository(AbstractSalesOrderRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

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
        data = {
            "id": str(uuid.uuid4()),
            "business_id": business_id,
            "customer_id": customer_id,
            "branch_id": branch_id,
            "warehouse_id": warehouse_id,
            "sales_order_number": sales_order_number,
            "order_date": order_date,
            "notes": notes,
            "status": SalesOrderStatus.DRAFT.value,
            "is_deleted": False,
            "subtotal": Decimal("0"),
            "discount_total": Decimal("0"),
            "tax_total": Decimal("0"),
            "grand_total": Decimal("0"),
            "created_by_user_id": created_by_user_id,
        }
        obj = await sa_create(self.session, SalesOrderModel, data)
        return _to_sales_order_in_db(obj)

    async def get_order_by_id(self, order_id: str, business_id: str) -> Optional[SalesOrderInDB]:
        stmt = select(SalesOrderModel).where(
            SalesOrderModel.id == order_id,
            SalesOrderModel.business_id == business_id,
            SalesOrderModel.is_deleted == False,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_sales_order_in_db(obj) if obj else None

    async def get_sales_order_for_update(self, order_id: str, business_id: str) -> Optional[SalesOrderInDB]:
        stmt = select(SalesOrderModel).where(
            SalesOrderModel.id == order_id,
            SalesOrderModel.business_id == business_id,
            SalesOrderModel.is_deleted == False,
        ).with_for_update()
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_sales_order_in_db(obj) if obj else None

    async def get_order_by_number(self, business_id: str, order_number: str) -> Optional[SalesOrderInDB]:
        stmt = select(SalesOrderModel).where(
            SalesOrderModel.business_id == business_id,
            SalesOrderModel.sales_order_number == order_number,
            SalesOrderModel.is_deleted == False,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_sales_order_in_db(obj) if obj else None

    async def list_orders(
        self, business_id: str, status: Optional[SalesOrderStatus], customer_id: Optional[str],
        branch_id: Optional[str], search: Optional[str], page: int, page_size: int,
    ) -> Tuple[List[SalesOrderInDB], int]:
        filters = [
            SalesOrderModel.business_id == business_id,
            SalesOrderModel.is_deleted == False,
        ]
        if status is not None:
            filters.append(SalesOrderModel.status == status.value)
        if customer_id is not None:
            filters.append(SalesOrderModel.customer_id == customer_id)
        if branch_id is not None:
            filters.append(SalesOrderModel.branch_id == branch_id)
        if search:
            filters.append(
                or_(
                    SalesOrderModel.sales_order_number.ilike(f"%{search}%"),
                    SalesOrderModel.notes.ilike(f"%{search}%"),
                )
            )
        count_stmt = select(func.count()).select_from(SalesOrderModel).where(and_(*filters))
        total = (await self.session.execute(count_stmt)).scalar_one()
        stmt = (
            select(SalesOrderModel)
            .where(and_(*filters))
            .order_by(desc(SalesOrderModel.created_at))
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        result = await self.session.execute(stmt)
        items = [_to_sales_order_in_db(o) for o in result.scalars().all()]
        return items, total

    async def update_order(self, order_id: str, business_id: str, **kwargs) -> Optional[SalesOrderInDB]:
        stmt = select(SalesOrderModel).where(
            SalesOrderModel.id == order_id,
            SalesOrderModel.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        for key, value in kwargs.items():
            if key == "status" and value is not None:
                obj.status = value.value if hasattr(value, "value") else value
            elif hasattr(obj, key) and (value is not None or key in [
                "customer_id", "notes", "confirmed_by_user_id", "confirmed_at",
                "cancelled_by_user_id", "cancelled_at", "fulfilled_by_user_id",
                "fulfilled_at", "status",
            ]):
                setattr(obj, key, value)
        obj.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return _to_sales_order_in_db(obj)

    async def get_next_order_sequence(self, business_id: str) -> int:
        from sqlalchemy import Integer
        stmt = select(func.max(func.cast(SalesOrderModel.sales_order_number, Integer))).where(
            SalesOrderModel.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        max_num = result.scalar_one()
        if max_num is None:
            return 1
        try:
            return int(max_num) + 1
        except (ValueError, TypeError):
            return 1

    async def create_line(
        self, sales_order_id: str, product_id: str, variant_id: Optional[str], description: Optional[str],
        quantity_ordered: Decimal, unit_price: Decimal, discount_amount: Decimal, tax_amount: Decimal,
        line_subtotal: Decimal, line_total: Decimal,
        discount_rule_id: Optional[str] = None, discount_rule_name_snapshot: Optional[str] = None,
    ) -> SalesOrderLineInDB:
        data = {
            "id": str(uuid.uuid4()),
            "sales_order_id": sales_order_id,
            "product_id": product_id,
            "variant_id": variant_id,
            "description": description,
            "quantity_ordered": quantity_ordered,
            "quantity_fulfilled": Decimal("0"),
            "quantity_remaining": quantity_ordered,
            "unit_price": unit_price,
            "discount_amount": discount_amount,
            "discount_rule_id": discount_rule_id,
            "discount_rule_name_snapshot": discount_rule_name_snapshot,
            "tax_amount": tax_amount,
            "line_subtotal": line_subtotal,
            "line_total": line_total,
        }
        obj = await sa_create(self.session, SalesOrderLineModel, data)
        return _to_sales_order_line_in_db(obj)

    async def get_line_by_id(self, line_id: str, sales_order_id: str) -> Optional[SalesOrderLineInDB]:
        stmt = select(SalesOrderLineModel).where(
            SalesOrderLineModel.id == line_id,
            SalesOrderLineModel.sales_order_id == sales_order_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_sales_order_line_in_db(obj) if obj else None

    async def list_lines_for_order(self, sales_order_id: str) -> List[SalesOrderLineInDB]:
        stmt = (
            select(SalesOrderLineModel)
            .where(SalesOrderLineModel.sales_order_id == sales_order_id)
            .order_by(SalesOrderLineModel.created_at, SalesOrderLineModel.id)
        )
        result = await self.session.execute(stmt)
        return [_to_sales_order_line_in_db(o) for o in result.scalars().all()]

    async def update_line(self, line_id: str, sales_order_id: str, **kwargs) -> Optional[SalesOrderLineInDB]:
        stmt = select(SalesOrderLineModel).where(
            SalesOrderLineModel.id == line_id,
            SalesOrderLineModel.sales_order_id == sales_order_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        for key, value in kwargs.items():
            if value is not None and hasattr(obj, key):
                setattr(obj, key, value)
        obj.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return _to_sales_order_line_in_db(obj)

    async def delete_line(self, line_id: str, sales_order_id: str) -> bool:
        stmt = select(SalesOrderLineModel).where(
            SalesOrderLineModel.id == line_id,
            SalesOrderLineModel.sales_order_id == sales_order_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return False
        await self.session.delete(obj)
        await self.session.flush()
        return True

    @classmethod
    def clear(cls):
        pass


class SQLAlchemyReservationRepository(AbstractReservationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

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
        data = {
            "id": str(uuid.uuid4()),
            "business_id": business_id,
            "sales_order_id": sales_order_id,
            "sales_order_line_id": sales_order_line_id,
            "warehouse_id": warehouse_id,
            "product_id": product_id,
            "variant_id": variant_id,
            "quantity": quantity,
            "status": ReservationStatus.ACTIVE.value,
        }
        obj = await sa_create(self.session, ReservationModel, data)
        return _to_reservation_in_db(obj)

    async def get_by_id(self, reservation_id: str, business_id: str) -> Optional[SalesOrderReservationInDB]:
        stmt = select(ReservationModel).where(
            ReservationModel.id == reservation_id,
            ReservationModel.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_reservation_in_db(obj) if obj else None

    async def get_reservation_for_update(self, reservation_id: str) -> Optional[SalesOrderReservationInDB]:
        stmt = select(ReservationModel).where(
            ReservationModel.id == reservation_id,
        ).with_for_update()
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_reservation_in_db(obj) if obj else None

    async def list_by_order(self, sales_order_id: str) -> List[SalesOrderReservationInDB]:
        stmt = (
            select(ReservationModel)
            .where(ReservationModel.sales_order_id == sales_order_id)
            .order_by(ReservationModel.created_at, ReservationModel.id)
        )
        result = await self.session.execute(stmt)
        return [_to_reservation_in_db(o) for o in result.scalars().all()]

    async def list_by_order_for_update(self, sales_order_id: str) -> List[SalesOrderReservationInDB]:
        stmt = (
            select(ReservationModel)
            .where(ReservationModel.sales_order_id == sales_order_id)
            .order_by(ReservationModel.created_at, ReservationModel.id)
        ).with_for_update()
        result = await self.session.execute(stmt)
        return [_to_reservation_in_db(o) for o in result.scalars().all()]

    async def list_active_by_warehouse_product(
        self, business_id: str, warehouse_id: str, product_id: str, variant_id: Optional[str]
    ) -> List[SalesOrderReservationInDB]:
        filters = [
            ReservationModel.business_id == business_id,
            ReservationModel.warehouse_id == warehouse_id,
            ReservationModel.product_id == product_id,
            ReservationModel.variant_id == variant_id,
            ReservationModel.status == ReservationStatus.ACTIVE.value,
        ]
        stmt = select(ReservationModel).where(and_(*filters))
        result = await self.session.execute(stmt)
        return [_to_reservation_in_db(o) for o in result.scalars().all()]

    async def list_active_reservations_for_update(
        self, business_id: str, warehouse_id: str, product_id: str, variant_id: Optional[str]
    ) -> List[SalesOrderReservationInDB]:
        filters = [
            ReservationModel.business_id == business_id,
            ReservationModel.warehouse_id == warehouse_id,
            ReservationModel.product_id == product_id,
            ReservationModel.status == ReservationStatus.ACTIVE.value,
        ]
        if variant_id is not None:
            filters.append(ReservationModel.variant_id == variant_id)
        else:
            filters.append(ReservationModel.variant_id == None)
        stmt = select(ReservationModel).where(and_(*filters)).with_for_update()
        result = await self.session.execute(stmt)
        return [_to_reservation_in_db(o) for o in result.scalars().all()]

    async def update_status(self, reservation_id: str, status: ReservationStatus) -> Optional[SalesOrderReservationInDB]:
        stmt = select(ReservationModel).where(ReservationModel.id == reservation_id)
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        obj.status = status.value
        obj.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return _to_reservation_in_db(obj)

    async def update_quantity(self, reservation_id: str, quantity: Decimal) -> Optional[SalesOrderReservationInDB]:
        stmt = select(ReservationModel).where(ReservationModel.id == reservation_id)
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        obj.quantity = quantity
        obj.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return _to_reservation_in_db(obj)

    @classmethod
    def clear(cls):
        pass

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Any
from decimal import Decimal

from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sales.models import Sales as SalesModel, SalesLine as SalesLineModel
from app.modules.sales.repository import AbstractSalesRepository
from app.modules.sales.schemas import (
    SalesInDB,
    SalesLineInDB,
    SalesStatus,
)
from app.modules.sqla_base import sa_create


def _to_sales_in_db(obj: SalesModel) -> SalesInDB:
    return SalesInDB(
        id=obj.id,
        business_id=obj.business_id,
        customer_id=obj.customer_id,
        branch_id=obj.branch_id,
        sales_number=obj.sales_number,
        sales_date=obj.sales_date,
        notes=obj.notes,
        status=SalesStatus(obj.status),
        is_deleted=obj.is_deleted,
        subtotal=obj.subtotal,
        discount_total=obj.discount_total,
        tax_total=obj.tax_total,
        grand_total=obj.grand_total,
        created_by_user_id=obj.created_by_user_id,
        finalized_by_user_id=obj.finalized_by_user_id,
        cancelled_by_user_id=obj.cancelled_by_user_id,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        finalized_at=obj.finalized_at,
        cancelled_at=obj.cancelled_at,
    )


def _to_sales_line_in_db(obj: SalesLineModel) -> SalesLineInDB:
    return SalesLineInDB(
        id=obj.id,
        sales_id=obj.sales_id,
        product_id=obj.product_id,
        variant_id=obj.variant_id,
        description=obj.description,
        quantity=obj.quantity,
        unit_price=obj.unit_price,
        discount_amount=obj.discount_amount,
        discount_rule_id=obj.discount_rule_id,
        discount_rule_name_snapshot=obj.discount_rule_name_snapshot,
        tax_amount=obj.tax_amount,
        line_subtotal=obj.line_subtotal,
        line_total=obj.line_total,
        tax_snapshot=obj.tax_snapshot,
        unit_cost_snapshot=obj.unit_cost_snapshot,
        cost_total_snapshot=obj.cost_total_snapshot,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


class SQLAlchemySalesRepository(AbstractSalesRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_sales(
        self,
        business_id: str,
        customer_id: Optional[str],
        branch_id: str,
        sales_number: str,
        sales_date: datetime,
        created_by_user_id: str,
        notes: Optional[str] = None,
    ) -> SalesInDB:
        data = {
            "id": str(uuid.uuid4()),
            "business_id": business_id,
            "customer_id": customer_id,
            "branch_id": branch_id,
            "sales_number": sales_number,
            "sales_date": sales_date,
            "created_by_user_id": created_by_user_id,
            "notes": notes,
            "status": SalesStatus.DRAFT.value,
            "subtotal": Decimal("0"),
            "discount_total": Decimal("0"),
            "tax_total": Decimal("0"),
            "grand_total": Decimal("0"),
        }
        obj = await sa_create(self.session, SalesModel, data)
        return _to_sales_in_db(obj)

    async def get_sales_by_id(self, sales_id: str, business_id: str) -> Optional[SalesInDB]:
        stmt = select(SalesModel).where(
            SalesModel.id == sales_id,
            SalesModel.business_id == business_id,
            SalesModel.is_deleted == False,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_sales_in_db(obj) if obj else None

    async def get_sales_for_update(self, sales_id: str, business_id: str) -> Optional[SalesInDB]:
        stmt = select(SalesModel).where(
            SalesModel.id == sales_id,
            SalesModel.business_id == business_id,
            SalesModel.is_deleted == False,
        ).with_for_update()
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_sales_in_db(obj) if obj else None

    async def get_sales_by_number(self, business_id: str, sales_number: str) -> Optional[SalesInDB]:
        stmt = select(SalesModel).where(
            SalesModel.business_id == business_id,
            SalesModel.sales_number == sales_number,
            SalesModel.is_deleted == False,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_sales_in_db(obj) if obj else None

    async def list_sales(
        self,
        business_id: str,
        status: Optional[SalesStatus] = None,
        customer_id: Optional[str] = None,
        branch_id: Optional[str] = None,
        search: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[SalesInDB], int]:
        filters = [
            SalesModel.business_id == business_id,
            SalesModel.is_deleted == False,
        ]
        if status is not None:
            filters.append(SalesModel.status == status.value)
        if customer_id is not None:
            filters.append(SalesModel.customer_id == customer_id)
        if branch_id is not None:
            filters.append(SalesModel.branch_id == branch_id)
        if date_from is not None:
            filters.append(SalesModel.sales_date >= date_from)
        if date_to is not None:
            filters.append(SalesModel.sales_date <= date_to)
        if search:
            filters.append(SalesModel.sales_number.ilike(f"%{search}%"))

        count_stmt = select(func.count()).select_from(SalesModel).where(and_(*filters))
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(SalesModel)
            .where(and_(*filters))
            .order_by(desc(SalesModel.sales_date), desc(SalesModel.created_at), desc(SalesModel.id))
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        result = await self.session.execute(stmt)
        items = [_to_sales_in_db(o) for o in result.scalars().all()]
        return items, total

    async def update_sales(
        self,
        sales_id: str,
        business_id: str,
        customer_id: Optional[str] = None,
        branch_id: Optional[str] = None,
        sales_date: Optional[datetime] = None,
        notes: Optional[str] = None,
        status: Optional[SalesStatus] = None,
        subtotal: Optional[Decimal] = None,
        discount_total: Optional[Decimal] = None,
        tax_total: Optional[Decimal] = None,
        grand_total: Optional[Decimal] = None,
        finalized_by_user_id: Optional[str] = None,
        finalized_at: Optional[datetime] = None,
        cancelled_by_user_id: Optional[str] = None,
        cancelled_at: Optional[datetime] = None,
        is_deleted: Optional[bool] = None,
    ) -> Optional[SalesInDB]:
        stmt = select(SalesModel).where(
            SalesModel.id == sales_id,
            SalesModel.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        if customer_id is not None:
            obj.customer_id = customer_id
        if branch_id is not None:
            obj.branch_id = branch_id
        if sales_date is not None:
            obj.sales_date = sales_date
        if notes is not None:
            obj.notes = notes
        if status is not None:
            obj.status = status.value
        if subtotal is not None:
            obj.subtotal = subtotal
        if discount_total is not None:
            obj.discount_total = discount_total
        if tax_total is not None:
            obj.tax_total = tax_total
        if grand_total is not None:
            obj.grand_total = grand_total
        if finalized_by_user_id is not None:
            obj.finalized_by_user_id = finalized_by_user_id
        if finalized_at is not None:
            obj.finalized_at = finalized_at
        if cancelled_by_user_id is not None:
            obj.cancelled_by_user_id = cancelled_by_user_id
        if cancelled_at is not None:
            obj.cancelled_at = cancelled_at
        if is_deleted is not None:
            obj.is_deleted = is_deleted
        obj.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return _to_sales_in_db(obj)

    async def get_next_sales_sequence(self, business_id: str) -> int:
        stmt = select(func.max(func.cast(SalesModel.sales_number, Integer))).where(
            SalesModel.business_id == business_id,
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
        self,
        sales_id: str,
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
    ) -> SalesLineInDB:
        data = {
            "id": str(uuid.uuid4()),
            "sales_id": sales_id,
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
        obj = await sa_create(self.session, SalesLineModel, data)
        return _to_sales_line_in_db(obj)

    async def get_line_by_id(self, line_id: str, sales_id: str) -> Optional[SalesLineInDB]:
        stmt = select(SalesLineModel).where(
            SalesLineModel.id == line_id,
            SalesLineModel.sales_id == sales_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_sales_line_in_db(obj) if obj else None

    async def list_lines_for_sales(self, sales_id: str) -> List[SalesLineInDB]:
        stmt = (
            select(SalesLineModel)
            .where(SalesLineModel.sales_id == sales_id)
            .order_by(SalesLineModel.created_at, SalesLineModel.id)
        )
        result = await self.session.execute(stmt)
        return [_to_sales_line_in_db(o) for o in result.scalars().all()]

    async def update_line(
        self,
        line_id: str,
        sales_id: str,
        product_id: Optional[str] = None,
        variant_id: Optional[str] = None,
        description: Optional[str] = None,
        quantity: Optional[Decimal] = None,
        unit_price: Optional[Decimal] = None,
        discount_amount: Optional[Decimal] = None,
        tax_amount: Optional[Decimal] = None,
        line_subtotal: Optional[Decimal] = None,
        line_total: Optional[Decimal] = None,
    ) -> Optional[SalesLineInDB]:
        stmt = select(SalesLineModel).where(
            SalesLineModel.id == line_id,
            SalesLineModel.sales_id == sales_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        if product_id is not None:
            obj.product_id = product_id
        if variant_id is not None:
            obj.variant_id = variant_id
        if description is not None:
            obj.description = description
        if quantity is not None:
            obj.quantity = quantity
        if unit_price is not None:
            obj.unit_price = unit_price
        if discount_amount is not None:
            obj.discount_amount = discount_amount
        if tax_amount is not None:
            obj.tax_amount = tax_amount
        if line_subtotal is not None:
            obj.line_subtotal = line_subtotal
        if line_total is not None:
            obj.line_total = line_total
        obj.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return _to_sales_line_in_db(obj)

    async def delete_line(self, line_id: str, sales_id: str) -> bool:
        stmt = select(SalesLineModel).where(
            SalesLineModel.id == line_id,
            SalesLineModel.sales_id == sales_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return False
        await self.session.delete(obj)
        await self.session.flush()
        return True

    async def update_line_snapshot(self, line_id: str, sales_id: str, snapshot: Any) -> Optional[SalesLineInDB]:
        stmt = select(SalesLineModel).where(
            SalesLineModel.id == line_id,
            SalesLineModel.sales_id == sales_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        obj.tax_snapshot = snapshot
        obj.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return _to_sales_line_in_db(obj)

    async def update_line_cost_snapshots(
        self,
        line_id: str,
        sales_id: str,
        unit_cost_snapshot: Decimal,
        cost_total_snapshot: Decimal,
    ) -> Optional[SalesLineInDB]:
        stmt = select(SalesLineModel).where(
            SalesLineModel.id == line_id,
            SalesLineModel.sales_id == sales_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        obj.unit_cost_snapshot = unit_cost_snapshot
        obj.cost_total_snapshot = cost_total_snapshot
        obj.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return _to_sales_line_in_db(obj)

    @classmethod
    def clear(cls):
        pass

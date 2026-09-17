import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Any
from decimal import Decimal

from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.purchase.models import Purchase as PurchaseModel, PurchaseLine as PurchaseLineModel
from app.modules.purchase.repository import AbstractPurchaseRepository
from app.modules.purchase.schemas import (
    PurchaseInDB,
    PurchaseLineInDB,
    PurchaseStatus,
)
from app.modules.sqla_base import sa_create


def _to_purchase_in_db(obj: PurchaseModel) -> PurchaseInDB:
    return PurchaseInDB(
        id=obj.id,
        business_id=obj.business_id,
        supplier_id=obj.supplier_id,
        branch_id=obj.branch_id,
        purchase_number=obj.purchase_number,
        purchase_date=obj.purchase_date,
        notes=obj.notes,
        status=PurchaseStatus(obj.status),
        subtotal=obj.subtotal,
        discount_total=obj.discount_total,
        tax_total=obj.tax_total,
        grand_total=obj.grand_total,
        input_vat_creditable=obj.input_vat_creditable,
        created_by_user_id=obj.created_by_user_id,
        finalized_by_user_id=obj.finalized_by_user_id,
        cancelled_by_user_id=obj.cancelled_by_user_id,
        is_deleted=obj.is_deleted,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        finalized_at=obj.finalized_at,
        cancelled_at=obj.cancelled_at,
    )


def _to_purchase_line_in_db(obj: PurchaseLineModel) -> PurchaseLineInDB:
    return PurchaseLineInDB(
        id=obj.id,
        purchase_id=obj.purchase_id,
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


class SQLAlchemyPurchaseRepository(AbstractPurchaseRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_purchase(
        self,
        business_id: str,
        supplier_id: str,
        branch_id: str,
        purchase_number: str,
        purchase_date: datetime,
        created_by_user_id: str,
        notes: Optional[str] = None,
        input_vat_creditable: bool = False,
    ) -> PurchaseInDB:
        data = {
            "id": str(uuid.uuid4()),
            "business_id": business_id,
            "supplier_id": supplier_id,
            "branch_id": branch_id,
            "purchase_number": purchase_number,
            "purchase_date": purchase_date,
            "created_by_user_id": created_by_user_id,
            "notes": notes,
            "status": PurchaseStatus.DRAFT.value,
            "subtotal": Decimal("0"),
            "discount_total": Decimal("0"),
            "tax_total": Decimal("0"),
            "grand_total": Decimal("0"),
            "input_vat_creditable": input_vat_creditable,
            "is_deleted": False,
        }
        obj = await sa_create(self.session, PurchaseModel, data)
        return _to_purchase_in_db(obj)

    async def get_purchase_by_id(
        self, purchase_id: str, business_id: str
    ) -> Optional[PurchaseInDB]:
        stmt = select(PurchaseModel).where(
            PurchaseModel.id == purchase_id,
            PurchaseModel.business_id == business_id,
            PurchaseModel.is_deleted == False,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_purchase_in_db(obj) if obj else None

    async def get_purchase_by_number(
        self, business_id: str, purchase_number: str
    ) -> Optional[PurchaseInDB]:
        stmt = select(PurchaseModel).where(
            PurchaseModel.business_id == business_id,
            PurchaseModel.purchase_number == purchase_number,
            PurchaseModel.is_deleted == False,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_purchase_in_db(obj) if obj else None

    async def list_purchases(
        self,
        business_id: str,
        status: Optional[PurchaseStatus] = None,
        supplier_id: Optional[str] = None,
        branch_id: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[PurchaseInDB], int]:
        filters = [
            PurchaseModel.business_id == business_id,
            PurchaseModel.is_deleted == False,
        ]
        if status is not None:
            filters.append(PurchaseModel.status == status.value)
        if supplier_id is not None:
            filters.append(PurchaseModel.supplier_id == supplier_id)
        if branch_id is not None:
            filters.append(PurchaseModel.branch_id == branch_id)
        if search:
            filters.append(PurchaseModel.purchase_number.ilike(f"%{search}%"))

        count_stmt = select(func.count()).select_from(PurchaseModel).where(and_(*filters))
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(PurchaseModel)
            .where(and_(*filters))
            .order_by(desc(PurchaseModel.purchase_date), desc(PurchaseModel.created_at), desc(PurchaseModel.id))
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        result = await self.session.execute(stmt)
        items = [_to_purchase_in_db(o) for o in result.scalars().all()]
        return items, total

    async def update_purchase(
        self,
        purchase_id: str,
        business_id: str,
        supplier_id: Optional[str] = None,
        branch_id: Optional[str] = None,
        purchase_date: Optional[datetime] = None,
        notes: Optional[str] = None,
        status: Optional[PurchaseStatus] = None,
        subtotal: Optional[Decimal] = None,
        discount_total: Optional[Decimal] = None,
        tax_total: Optional[Decimal] = None,
        grand_total: Optional[Decimal] = None,
        finalized_by_user_id: Optional[str] = None,
        finalized_at: Optional[datetime] = None,
        cancelled_by_user_id: Optional[str] = None,
        cancelled_at: Optional[datetime] = None,
        is_deleted: Optional[bool] = None,
    ) -> Optional[PurchaseInDB]:
        stmt = select(PurchaseModel).where(
            PurchaseModel.id == purchase_id,
            PurchaseModel.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        if supplier_id is not None:
            obj.supplier_id = supplier_id
        if branch_id is not None:
            obj.branch_id = branch_id
        if purchase_date is not None:
            obj.purchase_date = purchase_date
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
        return _to_purchase_in_db(obj)

    async def get_next_purchase_sequence(self, business_id: str) -> int:
        from sqlalchemy import Integer
        stmt = select(func.max(func.cast(PurchaseModel.purchase_number, Integer))).where(
            PurchaseModel.business_id == business_id,
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
        purchase_id: str,
        product_id: str,
        variant_id: Optional[str],
        description: Optional[str],
        quantity: Decimal,
        unit_price: Decimal,
        discount_amount: Decimal,
        tax_amount: Decimal,
        line_subtotal: Decimal,
        line_total: Decimal,
    ) -> PurchaseLineInDB:
        data = {
            "id": str(uuid.uuid4()),
            "purchase_id": purchase_id,
            "product_id": product_id,
            "variant_id": variant_id,
            "description": description,
            "quantity": quantity,
            "unit_price": unit_price,
            "discount_amount": discount_amount,
            "tax_amount": tax_amount,
            "line_subtotal": line_subtotal,
            "line_total": line_total,
        }
        obj = await sa_create(self.session, PurchaseLineModel, data)
        return _to_purchase_line_in_db(obj)

    async def get_line_by_id(
        self, line_id: str, purchase_id: str
    ) -> Optional[PurchaseLineInDB]:
        stmt = select(PurchaseLineModel).where(
            PurchaseLineModel.id == line_id,
            PurchaseLineModel.purchase_id == purchase_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_purchase_line_in_db(obj) if obj else None

    async def list_lines_for_purchase(self, purchase_id: str) -> List[PurchaseLineInDB]:
        stmt = (
            select(PurchaseLineModel)
            .where(PurchaseLineModel.purchase_id == purchase_id)
            .order_by(PurchaseLineModel.created_at, PurchaseLineModel.id)
        )
        result = await self.session.execute(stmt)
        return [_to_purchase_line_in_db(o) for o in result.scalars().all()]

    async def update_line(
        self,
        line_id: str,
        purchase_id: str,
        product_id: Optional[str] = None,
        variant_id: Optional[str] = None,
        description: Optional[str] = None,
        quantity: Optional[Decimal] = None,
        unit_price: Optional[Decimal] = None,
        discount_amount: Optional[Decimal] = None,
        tax_amount: Optional[Decimal] = None,
        line_subtotal: Optional[Decimal] = None,
        line_total: Optional[Decimal] = None,
    ) -> Optional[PurchaseLineInDB]:
        stmt = select(PurchaseLineModel).where(
            PurchaseLineModel.id == line_id,
            PurchaseLineModel.purchase_id == purchase_id,
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
        return _to_purchase_line_in_db(obj)

    async def delete_line(self, line_id: str, purchase_id: str) -> bool:
        stmt = select(PurchaseLineModel).where(
            PurchaseLineModel.id == line_id,
            PurchaseLineModel.purchase_id == purchase_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return False
        await self.session.delete(obj)
        await self.session.flush()
        return True

    async def update_line_snapshot(self, line_id: str, purchase_id: str, snapshot: Any) -> Optional[PurchaseLineInDB]:
        stmt = select(PurchaseLineModel).where(
            PurchaseLineModel.id == line_id,
            PurchaseLineModel.purchase_id == purchase_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        obj.tax_snapshot = snapshot
        obj.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return _to_purchase_line_in_db(obj)

    @classmethod
    def clear(cls):
        pass

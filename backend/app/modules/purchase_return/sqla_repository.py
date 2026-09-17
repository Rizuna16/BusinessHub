import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from decimal import Decimal

from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.purchase_return.models import (
    PurchaseReturn as PurchaseReturnModel,
    PurchaseReturnLine as PurchaseReturnLineModel,
)
from app.modules.purchase_return.repository import AbstractPurchaseReturnRepository
from app.modules.purchase_return.schemas import (
    PurchaseReturnInDB,
    PurchaseReturnLineInDB,
    PurchaseReturnStatus,
)
from app.modules.sqla_base import sa_create


def _to_purchase_return_in_db(obj: PurchaseReturnModel) -> PurchaseReturnInDB:
    return PurchaseReturnInDB(
        id=obj.id,
        business_id=obj.business_id,
        purchase_id=obj.purchase_id,
        inventory_location_id=obj.inventory_location_id,
        return_number=obj.return_number,
        status=PurchaseReturnStatus(obj.status),
        notes=obj.notes,
        subtotal=obj.subtotal,
        discount_total=obj.discount_total,
        tax_total=obj.tax_total,
        grand_total=obj.grand_total,
        created_by_user_id=obj.created_by_user_id,
        finalized_by_user_id=obj.finalized_by_user_id,
        cancelled_by_user_id=obj.cancelled_by_user_id,
        is_deleted=obj.is_deleted,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        finalized_at=obj.finalized_at,
        cancelled_at=obj.cancelled_at,
    )


def _to_purchase_return_line_in_db(obj: PurchaseReturnLineModel) -> PurchaseReturnLineInDB:
    return PurchaseReturnLineInDB(
        id=obj.id,
        return_id=obj.return_id,
        purchase_line_id=obj.purchase_line_id,
        product_id=obj.product_id,
        variant_id=obj.variant_id,
        quantity=obj.quantity,
        unit_price=obj.unit_price,
        discount_amount=obj.discount_amount,
        tax_amount=obj.tax_amount,
        line_subtotal=obj.line_subtotal,
        line_total=obj.line_total,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


class SQLAlchemyPurchaseReturnRepository(AbstractPurchaseReturnRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_return(
        self,
        business_id: str,
        purchase_id: str,
        inventory_location_id: str,
        return_number: str,
        created_by_user_id: str,
        notes: Optional[str] = None,
    ) -> PurchaseReturnInDB:
        data = {
            "id": str(uuid.uuid4()),
            "business_id": business_id,
            "purchase_id": purchase_id,
            "inventory_location_id": inventory_location_id,
            "return_number": return_number,
            "status": PurchaseReturnStatus.DRAFT.value,
            "notes": notes,
            "subtotal": Decimal("0"),
            "discount_total": Decimal("0"),
            "tax_total": Decimal("0"),
            "grand_total": Decimal("0"),
            "created_by_user_id": created_by_user_id,
            "is_deleted": False,
        }
        obj = await sa_create(self.session, PurchaseReturnModel, data)
        return _to_purchase_return_in_db(obj)

    async def get_return_by_id(
        self, return_id: str, business_id: str
    ) -> Optional[PurchaseReturnInDB]:
        stmt = select(PurchaseReturnModel).where(
            PurchaseReturnModel.id == return_id,
            PurchaseReturnModel.business_id == business_id,
            PurchaseReturnModel.is_deleted == False,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_purchase_return_in_db(obj) if obj else None

    async def get_next_return_sequence(self, business_id: str) -> int:
        from sqlalchemy import Integer
        stmt = select(func.max(func.cast(PurchaseReturnModel.return_number, Integer))).where(
            PurchaseReturnModel.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        max_num = result.scalar_one()
        if max_num is None:
            return 1
        try:
            return int(max_num) + 1
        except (ValueError, TypeError):
            return 1

    async def list_returns(
        self,
        business_id: str,
        status: Optional[PurchaseReturnStatus] = None,
        purchase_id: Optional[str] = None,
        inventory_location_id: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[PurchaseReturnInDB], int]:
        filters = [
            PurchaseReturnModel.business_id == business_id,
            PurchaseReturnModel.is_deleted == False,
        ]
        if status is not None:
            filters.append(PurchaseReturnModel.status == status.value)
        if purchase_id is not None:
            filters.append(PurchaseReturnModel.purchase_id == purchase_id)
        if inventory_location_id is not None:
            filters.append(PurchaseReturnModel.inventory_location_id == inventory_location_id)
        if search:
            filters.append(PurchaseReturnModel.return_number.ilike(f"%{search}%"))

        count_stmt = select(func.count()).select_from(PurchaseReturnModel).where(and_(*filters))
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(PurchaseReturnModel)
            .where(and_(*filters))
            .order_by(desc(PurchaseReturnModel.created_at), desc(PurchaseReturnModel.id))
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        result = await self.session.execute(stmt)
        items = [_to_purchase_return_in_db(o) for o in result.scalars().all()]
        return items, total

    async def update_return(
        self,
        return_id: str,
        business_id: str,
        notes: Optional[str] = None,
        status: Optional[PurchaseReturnStatus] = None,
        subtotal: Optional[Decimal] = None,
        discount_total: Optional[Decimal] = None,
        tax_total: Optional[Decimal] = None,
        grand_total: Optional[Decimal] = None,
        finalized_by_user_id: Optional[str] = None,
        finalized_at: Optional[datetime] = None,
        cancelled_by_user_id: Optional[str] = None,
        cancelled_at: Optional[datetime] = None,
        is_deleted: Optional[bool] = None,
    ) -> Optional[PurchaseReturnInDB]:
        stmt = select(PurchaseReturnModel).where(
            PurchaseReturnModel.id == return_id,
            PurchaseReturnModel.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
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
        return _to_purchase_return_in_db(obj)

    async def create_line(
        self,
        return_id: str,
        purchase_line_id: str,
        product_id: str,
        variant_id: Optional[str],
        quantity: Decimal,
        unit_price: Decimal,
        discount_amount: Decimal,
        tax_amount: Decimal,
        line_subtotal: Decimal,
        line_total: Decimal,
    ) -> PurchaseReturnLineInDB:
        data = {
            "id": str(uuid.uuid4()),
            "return_id": return_id,
            "purchase_line_id": purchase_line_id,
            "product_id": product_id,
            "variant_id": variant_id,
            "quantity": quantity,
            "unit_price": unit_price,
            "discount_amount": discount_amount,
            "tax_amount": tax_amount,
            "line_subtotal": line_subtotal,
            "line_total": line_total,
        }
        obj = await sa_create(self.session, PurchaseReturnLineModel, data)
        return _to_purchase_return_line_in_db(obj)

    async def get_line_by_id(
        self, line_id: str, return_id: str
    ) -> Optional[PurchaseReturnLineInDB]:
        stmt = select(PurchaseReturnLineModel).where(
            PurchaseReturnLineModel.id == line_id,
            PurchaseReturnLineModel.return_id == return_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_purchase_return_line_in_db(obj) if obj else None

    async def list_lines_for_return(self, return_id: str) -> List[PurchaseReturnLineInDB]:
        stmt = (
            select(PurchaseReturnLineModel)
            .where(PurchaseReturnLineModel.return_id == return_id)
            .order_by(PurchaseReturnLineModel.created_at, PurchaseReturnLineModel.id)
        )
        result = await self.session.execute(stmt)
        return [_to_purchase_return_line_in_db(o) for o in result.scalars().all()]

    async def update_line(
        self,
        line_id: str,
        return_id: str,
        quantity: Optional[Decimal] = None,
        unit_price: Optional[Decimal] = None,
        discount_amount: Optional[Decimal] = None,
        tax_amount: Optional[Decimal] = None,
        line_subtotal: Optional[Decimal] = None,
        line_total: Optional[Decimal] = None,
    ) -> Optional[PurchaseReturnLineInDB]:
        stmt = select(PurchaseReturnLineModel).where(
            PurchaseReturnLineModel.id == line_id,
            PurchaseReturnLineModel.return_id == return_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
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
        return _to_purchase_return_line_in_db(obj)

    async def delete_line(self, line_id: str, return_id: str) -> bool:
        stmt = select(PurchaseReturnLineModel).where(
            PurchaseReturnLineModel.id == line_id,
            PurchaseReturnLineModel.return_id == return_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return False
        await self.session.delete(obj)
        await self.session.flush()
        return True

    async def sum_returned_quantity_for_purchase_line(
        self, purchase_line_id: str
    ) -> Decimal:
        stmt = (
            select(func.coalesce(func.sum(PurchaseReturnLineModel.quantity), 0))
            .join(PurchaseReturnModel, PurchaseReturnLineModel.return_id == PurchaseReturnModel.id)
            .where(
                PurchaseReturnLineModel.purchase_line_id == purchase_line_id,
                PurchaseReturnModel.is_deleted == False,
                PurchaseReturnModel.status.in_(["DRAFT", "FINALIZED"]),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    @classmethod
    def clear(cls):
        pass

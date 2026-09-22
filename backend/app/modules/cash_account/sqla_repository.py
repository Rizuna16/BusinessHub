from datetime import datetime, timezone
from typing import Optional, List
from decimal import Decimal

from sqlalchemy import select, func, and_, desc, asc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.cash_account.models import CashAccountInDB as CashAccountModel, CashMovementInDB as CashMovementModel
from app.modules.cash_account.repository import AbstractCashAccountRepository
from app.modules.cash_account.schemas import (
    CashAccountInDB,
    CashMovementInDB,
    CashAccountType,
    CashAccountStatus,
    CashMovementType,
    MovementDirection,
    CashMovementStatus,
)
from app.modules.sqla_base import sa_create


def _to_account(obj: CashAccountModel) -> CashAccountInDB:
    return CashAccountInDB(
        id=obj.id,
        business_id=obj.business_id,
        name=obj.name,
        code=obj.code,
        account_type=CashAccountType(obj.account_type),
        currency=obj.currency,
        description=obj.description,
        opening_balance=obj.opening_balance,
        status=CashAccountStatus(obj.status),
        is_default=obj.is_default,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


def _to_movement(obj: CashMovementModel) -> CashMovementInDB:
    return CashMovementInDB(
        id=obj.id,
        business_id=obj.business_id,
        cash_account_id=obj.cash_account_id,
        movement_type=CashMovementType(obj.movement_type),
        amount=obj.amount,
        direction=MovementDirection(obj.direction),
        reference_type=obj.reference_type,
        reference_id=obj.reference_id,
        description=obj.description,
        performed_by_user_id=obj.performed_by_user_id,
        shift_id=obj.shift_id,
        status=CashMovementStatus(obj.status),
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


class SQLAlchemyCashAccountRepository(AbstractCashAccountRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_account(
        self,
        business_id: str,
        name: str,
        code: str,
        account_type: CashAccountType,
        currency: str,
        opening_balance: Decimal,
        is_default: bool,
        description: Optional[str] = None,
    ) -> CashAccountInDB:
        if is_default:
            unset_stmt = select(CashAccountModel).where(
                CashAccountModel.business_id == business_id,
                CashAccountModel.is_default == True,
            )
            unset_res = await self.session.execute(unset_stmt)
            for acc in unset_res.scalars().all():
                acc.is_default = False

        data = {
            "business_id": business_id,
            "name": name,
            "code": code.upper(),
            "account_type": account_type.value,
            "currency": currency,
            "opening_balance": opening_balance,
            "status": CashAccountStatus.ACTIVE.value,
            "is_default": is_default,
            "description": description,
        }
        obj = await sa_create(self.session, CashAccountModel, data)
        return _to_account(obj)

    async def get_account_by_id(self, account_id: str, business_id: str) -> Optional[CashAccountInDB]:
        stmt = select(CashAccountModel).where(
            CashAccountModel.id == account_id,
            CashAccountModel.business_id == business_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_account(obj) if obj else None

    async def get_account_by_id_for_update(self, account_id: str, business_id: str) -> Optional[CashAccountInDB]:
        stmt = select(CashAccountModel).where(
            CashAccountModel.id == account_id,
            CashAccountModel.business_id == business_id,
        ).with_for_update()
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_account(obj) if obj else None

    async def get_account_by_code(self, business_id: str, code: str) -> Optional[CashAccountInDB]:
        code_upper = code.upper()
        stmt = select(CashAccountModel).where(
            CashAccountModel.business_id == business_id,
            func.upper(CashAccountModel.code) == code_upper,
            CashAccountModel.status != CashAccountStatus.ARCHIVED.value,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_account(obj) if obj else None

    async def get_default_account(self, business_id: str) -> Optional[CashAccountInDB]:
        stmt = select(CashAccountModel).where(
            CashAccountModel.business_id == business_id,
            CashAccountModel.status == CashAccountStatus.ACTIVE.value,
            CashAccountModel.is_default == True,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_account(obj) if obj else None

    async def list_accounts(
        self,
        business_id: str,
        account_type: Optional[CashAccountType] = None,
        status: Optional[CashAccountStatus] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[CashAccountInDB], int]:
        filters = [
            CashAccountModel.business_id == business_id,
            CashAccountModel.status != CashAccountStatus.ARCHIVED.value,
        ]
        if account_type:
            filters.append(CashAccountModel.account_type == account_type.value)
        if status:
            filters.append(CashAccountModel.status == status.value)
        if search:
            s_lower = search.lower()
            filters.append(
                or_(
                    func.lower(CashAccountModel.name).like(f"%{s_lower}%"),
                    func.lower(CashAccountModel.code).like(f"%{s_lower}%"),
                )
            )

        count_stmt = select(func.count()).select_from(CashAccountModel).where(and_(*filters))
        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one()

        stmt = (
            select(CashAccountModel)
            .where(and_(*filters))
            .order_by(desc(CashAccountModel.is_default), desc(CashAccountModel.created_at), desc(CashAccountModel.id))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        res = await self.session.execute(stmt)
        items = [_to_account(o) for o in res.scalars().all()]
        return items, total

    async def update_account(
        self,
        account_id: str,
        business_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[CashAccountStatus] = None,
        is_default: Optional[bool] = None,
    ) -> Optional[CashAccountInDB]:
        stmt = select(CashAccountModel).where(
            CashAccountModel.id == account_id,
            CashAccountModel.business_id == business_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            return None
        if is_default:
            unset_stmt = select(CashAccountModel).where(
                CashAccountModel.business_id == business_id,
                CashAccountModel.is_default == True,
                CashAccountModel.id != account_id,
            )
            unset_res = await self.session.execute(unset_stmt)
            for acc in unset_res.scalars().all():
                acc.is_default = False
        if name is not None:
            obj.name = name
        if description is not None:
            obj.description = description
        if status is not None:
            obj.status = status.value
        if is_default is not None:
            obj.is_default = is_default
        await self.session.flush()
        return _to_account(obj)

    async def create_movement(
        self,
        business_id: str,
        cash_account_id: str,
        movement_type: CashMovementType,
        amount: Decimal,
        direction: MovementDirection,
        performed_by_user_id: str,
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None,
        description: Optional[str] = None,
        shift_id: Optional[str] = None,
    ) -> CashMovementInDB:
        data = {
            "business_id": business_id,
            "cash_account_id": cash_account_id,
            "movement_type": movement_type.value,
            "amount": amount,
            "direction": direction.value,
            "reference_type": reference_type,
            "reference_id": reference_id,
            "description": description,
            "performed_by_user_id": performed_by_user_id,
            "shift_id": shift_id,
            "status": CashMovementStatus.POSTED.value,
        }
        obj = await sa_create(self.session, CashMovementModel, data)
        return _to_movement(obj)

    async def list_movements_for_account(
        self,
        business_id: str,
        cash_account_id: str,
        movement_type: Optional[CashMovementType] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[CashMovementInDB], int]:
        filters = [
            CashMovementModel.business_id == business_id,
            CashMovementModel.cash_account_id == cash_account_id,
        ]
        if movement_type:
            filters.append(CashMovementModel.movement_type == movement_type.value)
        if date_from:
            filters.append(CashMovementModel.created_at >= date_from)
        if date_to:
            filters.append(CashMovementModel.created_at <= date_to)

        count_stmt = select(func.count()).select_from(CashMovementModel).where(and_(*filters))
        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one()

        stmt = (
            select(CashMovementModel)
            .where(and_(*filters))
            .order_by(desc(CashMovementModel.created_at), desc(CashMovementModel.id))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        res = await self.session.execute(stmt)
        items = [_to_movement(o) for o in res.scalars().all()]
        return items, total

    async def list_all_movements_for_account(
        self, business_id: str, cash_account_id: str
    ) -> List[CashMovementInDB]:
        stmt = select(CashMovementModel).where(
            CashMovementModel.business_id == business_id,
            CashMovementModel.cash_account_id == cash_account_id,
            CashMovementModel.status == CashMovementStatus.POSTED.value,
        )
        res = await self.session.execute(stmt)
        return [_to_movement(o) for o in res.scalars().all()]

    async def find_movement_by_reference(
        self, business_id: str, reference_type: str, reference_id: str
    ) -> Optional[CashMovementInDB]:
        stmt = select(CashMovementModel).where(
            CashMovementModel.business_id == business_id,
            CashMovementModel.reference_type == reference_type,
            CashMovementModel.reference_id == reference_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_movement(obj) if obj else None

    async def delete_movement_by_reference(
        self, business_id: str, reference_type: str, reference_id: str
    ) -> bool:
        stmt = select(CashMovementModel).where(
            CashMovementModel.business_id == business_id,
            CashMovementModel.reference_type == reference_type,
            CashMovementModel.reference_id == reference_id,
        )
        res = await self.session.execute(stmt)
        deleted = False
        for obj in res.scalars().all():
            await self.session.delete(obj)
            deleted = True
        if deleted:
            await self.session.flush()
        return deleted

    @classmethod
    def clear(cls):
        pass

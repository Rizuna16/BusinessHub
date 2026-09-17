from typing import List, Optional
from decimal import Decimal
from datetime import datetime, timezone
from fastapi import HTTPException, status

from app.modules.cashier_shift.schemas import (
    CashierShiftInDB,
    CashierShiftResponse,
    CashierShiftListResponse,
    CashierShiftCreate,
    CashierShiftClose,
    CashierShiftForceClose,
    ShiftStatus,
)
from app.modules.cashier_shift.repository import (
    AbstractCashierShiftRepository,
    cashier_shift_repository,
)
from app.modules.cash_account.repository import cash_account_repository
from app.modules.cash_account.schemas import CashAccountType, CashAccountStatus, MovementDirection, CashMovementStatus, CashMovementListResponse, CashMovementResponse
from app.modules.branch.repository import branch_repository
from app.modules.branch.schemas import BranchStatus
from app.modules.business_membership.service import (
    BusinessMembershipService,
    business_membership_service,
)
from app.modules.business_membership.schemas import BusinessMembershipRole


class CashierShiftService:
    def __init__(
        self,
        shift_repo: AbstractCashierShiftRepository = cashier_shift_repository,
        membership_service: BusinessMembershipService = business_membership_service,
    ):
        self.shift_repo = shift_repo
        self.membership_service = membership_service

    async def _validate_access(
        self,
        business_id: str,
        user_id: str,
        required_roles: Optional[tuple[BusinessMembershipRole, ...]] = None,
    ):
        membership = await self.membership_service.require_active_membership(business_id, user_id)
        if required_roles and membership.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of roles: {[r.value for r in required_roles]}",
            )
        return membership

    async def _validate_branch(self, business_id: str, branch_id: str):
        branch = await branch_repository.get_by_id(branch_id)
        if not branch or branch.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Branch not found in this business.",
            )
        if branch.status != BranchStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Branch is not ACTIVE (current: {branch.status}).",
            )
        return branch

    async def _validate_cash_account(self, business_id: str, cash_account_id: str):
        acc = await cash_account_repository.get_account_by_id(cash_account_id, business_id)
        if not acc or acc.status != CashAccountStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cash account is inactive or not found.",
            )
        if acc.account_type != CashAccountType.CASH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Shift requires a CASH type account. Non-CASH accounts are not supported for drawer management.",
            )
        return acc

    async def _build_shift_response(self, shift: CashierShiftInDB) -> CashierShiftResponse:
        expected_cash = await self._calculate_expected_cash(shift)
        cash_account_name = None
        branch_name = None
        cashier_name = None

        acc = await cash_account_repository.get_account_by_id(shift.cash_account_id, shift.business_id)
        if acc:
            cash_account_name = acc.name

        br = await branch_repository.get_by_id(shift.branch_id)
        if br:
            branch_name = br.name

        return CashierShiftResponse(
            **shift.model_dump(),
            expected_cash=expected_cash,
            cash_account_name=cash_account_name,
            branch_name=branch_name,
            cashier_name=cashier_name,
        )

    async def _calculate_expected_cash(self, shift: CashierShiftInDB) -> Decimal:
        movements = await cash_account_repository.list_all_movements_for_account(
            shift.business_id, shift.cash_account_id
        )
        expected = shift.opening_balance
        for m in movements:
            if m.shift_id != shift.id:
                continue
            if m.status != CashMovementStatus.POSTED:
                continue
            if m.direction == MovementDirection.IN:
                expected += m.amount
            elif m.direction == MovementDirection.OUT:
                expected -= m.amount
        return expected

    async def open_shift(
        self, business_id: str, user_id: str, payload: CashierShiftCreate
    ) -> CashierShiftResponse:
        await self._validate_access(business_id, user_id)

        await self._validate_branch(business_id, payload.branch_id)
        await self._validate_cash_account(business_id, payload.cash_account_id)

        existing = await self.shift_repo.get_open_shift(business_id, payload.cash_account_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cash account already has an active shift.",
            )

        shift = await self.shift_repo.create_shift(
            business_id=business_id,
            branch_id=payload.branch_id,
            cashier_user_id=user_id,
            cash_account_id=payload.cash_account_id,
            opening_balance=payload.opening_balance,
            notes=payload.notes,
        )

        return await self._build_shift_response(shift)

    async def list_shifts(
        self,
        business_id: str,
        user_id: str,
        status_filter: Optional[ShiftStatus] = None,
        branch_id: Optional[str] = None,
        cashier_user_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> CashierShiftListResponse:
        membership = await self._validate_access(business_id, user_id)

        if membership.role == BusinessMembershipRole.MEMBER:
            cashier_user_id = user_id

        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        shifts, total = await self.shift_repo.list_shifts(
            business_id=business_id,
            status_filter=status_filter,
            branch_id=branch_id,
            cashier_user_id=cashier_user_id,
            page=page,
            page_size=page_size,
        )

        items = []
        for s in shifts:
            items.append(await self._build_shift_response(s))

        return CashierShiftListResponse(items=items, page=page, page_size=page_size, total=total)

    async def get_shift(
        self, business_id: str, shift_id: str, user_id: str
    ) -> CashierShiftResponse:
        membership = await self._validate_access(business_id, user_id)

        shift = await self.shift_repo.get_shift_by_id(shift_id, business_id)
        if not shift:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shift not found.",
            )

        if membership.role == BusinessMembershipRole.MEMBER and shift.cashier_user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this shift.",
            )

        return await self._build_shift_response(shift)

    async def close_shift(
        self, business_id: str, shift_id: str, user_id: str, payload: CashierShiftClose
    ) -> CashierShiftResponse:
        membership = await self._validate_access(business_id, user_id)

        shift = await self.shift_repo.get_shift_by_id(shift_id, business_id)
        if not shift:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shift not found.",
            )

        if membership.role == BusinessMembershipRole.MEMBER and shift.cashier_user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to close this shift.",
            )

        if shift.status != ShiftStatus.OPEN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Shift is not in OPEN status.",
            )

        expected_cash = await self._calculate_expected_cash(shift)
        discrepancy = payload.actual_cash_count - expected_cash

        now = datetime.now(timezone.utc)
        updated = await self.shift_repo.update_shift(
            shift_id=shift_id,
            business_id=business_id,
            status=ShiftStatus.CLOSED,
            closed_at=now,
            closed_by_user_id=user_id,
            actual_cash_count=payload.actual_cash_count,
            discrepancy=discrepancy,
            notes=payload.notes,
        )

        return await self._build_shift_response(updated)

    async def force_close_shift(
        self, business_id: str, shift_id: str, user_id: str, payload: CashierShiftForceClose
    ) -> CashierShiftResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )

        shift = await self.shift_repo.get_shift_by_id(shift_id, business_id)
        if not shift:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shift not found.",
            )

        if shift.status != ShiftStatus.OPEN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Shift is not in OPEN status.",
            )

        now = datetime.now(timezone.utc)
        updated = await self.shift_repo.update_shift(
            shift_id=shift_id,
            business_id=business_id,
            status=ShiftStatus.CLOSED,
            closed_at=now,
            closed_by_user_id=user_id,
            actual_cash_count=None,
            discrepancy=None,
            notes=payload.notes,
        )

        return await self._build_shift_response(updated)

    async def get_shift_transactions(
        self,
        business_id: str,
        shift_id: str,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> CashMovementListResponse:
        membership = await self._validate_access(business_id, user_id)

        shift = await self.shift_repo.get_shift_by_id(shift_id, business_id)
        if not shift:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shift not found.",
            )

        if membership.role == BusinessMembershipRole.MEMBER and shift.cashier_user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this shift's transactions.",
            )

        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        all_movements = await cash_account_repository.list_all_movements_for_account(
            business_id, shift.cash_account_id
        )
        filtered = [m for m in all_movements if m.shift_id == shift.id]
        filtered.sort(key=lambda x: (x.created_at, x.id), reverse=True)
        total = len(filtered)

        start = (page - 1) * page_size
        end = start + page_size
        paged = filtered[start:end]

        items = [CashMovementResponse(**m.model_dump()) for m in paged]
        return CashMovementListResponse(items=items, page=page, page_size=page_size, total=total)


cashier_shift_service = CashierShiftService()

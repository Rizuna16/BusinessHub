from typing import List, Optional
from decimal import Decimal
from datetime import datetime
from fastapi import HTTPException, status

from app.modules.cash_account.schemas import (
    CashAccountInDB,
    CashMovementInDB,
    CashAccountResponse,
    CashAccountListResponse,
    CashMovementResponse,
    CashMovementListResponse,
    CashSummaryResponse,
    CashAccountCreate,
    CashAccountUpdate,
    CashMovementCreate,
    CashTransferInput,
    CashAccountType,
    CashAccountStatus,
    CashMovementType,
    MovementDirection,
    CashMovementStatus,
)
from app.modules.cash_account.repository import (
    AbstractCashAccountRepository,
    cash_account_repository,
)
from app.modules.business_membership.service import (
    BusinessMembershipService,
    business_membership_service,
)
from app.modules.business_membership.schemas import BusinessMembershipRole
from app.modules.cashier_shift.service import cashier_shift_service
from app.modules.accounting.integration import accounting_integration_service as acct_integration


class CashAccountService:
    def __init__(
        self,
        account_repo: AbstractCashAccountRepository = cash_account_repository,
        membership_service: BusinessMembershipService = business_membership_service,
    ):
        self.account_repo = account_repo
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

    async def _calculate_balance(self, business_id: str, account: CashAccountInDB) -> Decimal:
        movements = await self.account_repo.list_all_movements_for_account(business_id, account.id)
        balance = account.opening_balance

        for m in movements:
            if m.direction == MovementDirection.IN:
                balance += m.amount
            elif m.direction == MovementDirection.OUT:
                balance -= m.amount

        return balance

    async def _build_account_response(self, business_id: str, account: CashAccountInDB) -> CashAccountResponse:
        current_balance = await self._calculate_balance(business_id, account)
        return CashAccountResponse(**account.model_dump(), current_balance=current_balance)

    async def create_account(
        self, business_id: str, user_id: str, payload: CashAccountCreate
    ) -> CashAccountResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )

        existing_code = await self.account_repo.get_account_by_code(business_id, payload.code)
        if existing_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cash account code '{payload.code.upper()}' already exists in this business.",
            )

        # Check if first active account -> make default automatically
        existing_accounts, total = await self.account_repo.list_accounts(business_id=business_id, page=1, page_size=1)
        is_def = payload.is_default or (total == 0)

        account = await self.account_repo.create_account(
            business_id=business_id,
            name=payload.name,
            code=payload.code,
            account_type=payload.account_type,
            currency=payload.currency,
            opening_balance=payload.opening_balance,
            is_default=is_def,
            description=payload.description,
        )

        return await self._build_account_response(business_id, account)

    async def list_accounts(
        self,
        business_id: str,
        user_id: str,
        account_type: Optional[CashAccountType] = None,
        status_filter: Optional[CashAccountStatus] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> CashAccountListResponse:
        await self._validate_access(business_id, user_id)

        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        accounts, total = await self.account_repo.list_accounts(
            business_id=business_id,
            account_type=account_type,
            status=status_filter,
            search=search,
            page=page,
            page_size=page_size,
        )

        items = []
        for a in accounts:
            items.append(await self._build_account_response(business_id, a))

        return CashAccountListResponse(items=items, page=page, page_size=page_size, total=total)

    async def get_account(
        self, business_id: str, account_id: str, user_id: str
    ) -> CashAccountResponse:
        await self._validate_access(business_id, user_id)
        account = await self.account_repo.get_account_by_id(account_id, business_id)
        if not account or account.status == CashAccountStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cash account not found.",
            )

        return await self._build_account_response(business_id, account)

    async def update_account(
        self,
        business_id: str,
        account_id: str,
        user_id: str,
        payload: CashAccountUpdate,
    ) -> CashAccountResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        account = await self.account_repo.get_account_by_id(account_id, business_id)
        if not account or account.status == CashAccountStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cash account not found.",
            )

        updated = await self.account_repo.update_account(
            account_id=account_id,
            business_id=business_id,
            name=payload.name,
            description=payload.description,
            is_default=payload.is_default,
        )

        return await self._build_account_response(business_id, updated)

    async def activate_account(
        self, business_id: str, account_id: str, user_id: str
    ) -> CashAccountResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        account = await self.account_repo.get_account_by_id(account_id, business_id)
        if not account or account.status == CashAccountStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cash account not found.",
            )

        updated = await self.account_repo.update_account(
            account_id=account_id,
            business_id=business_id,
            status=CashAccountStatus.ACTIVE,
        )

        return await self._build_account_response(business_id, updated)

    async def deactivate_account(
        self, business_id: str, account_id: str, user_id: str
    ) -> CashAccountResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        account = await self.account_repo.get_account_by_id(account_id, business_id)
        if not account or account.status == CashAccountStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cash account not found.",
            )

        # Cannot deactivate default account
        if account.is_default:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate the default cash account. Set another account as default first.",
            )

        updated = await self.account_repo.update_account(
            account_id=account_id,
            business_id=business_id,
            status=CashAccountStatus.INACTIVE,
        )

        return await self._build_account_response(business_id, updated)

    async def create_cash_movement(
        self,
        business_id: str,
        account_id: str,
        user_id: str,
        payload: CashMovementCreate,
    ) -> CashMovementResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        account = await self.account_repo.get_account_by_id_for_update(account_id, business_id)
        if not account or account.status != CashAccountStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cash account is inactive or not found.",
            )

        if payload.amount <= Decimal("0"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Amount must be greater than zero.",
            )

        # Non-negative balance check for CASH and E_WALLET OUT movements
        if payload.direction == MovementDirection.OUT and account.account_type in (CashAccountType.CASH, CashAccountType.E_WALLET):
            curr_bal = await self._calculate_balance(business_id, account)
            if curr_bal < payload.amount:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient balance in cash account. Current balance: {curr_bal}, requested: {payload.amount}.",
                )

        movement = await self.account_repo.create_movement(
            business_id=business_id,
            cash_account_id=account_id,
            movement_type=payload.movement_type,
            amount=payload.amount,
            direction=payload.direction,
            performed_by_user_id=user_id,
            reference_type=payload.reference_type,
            reference_id=payload.reference_id,
            description=payload.description,
            shift_id=payload.shift_id,
        )

        return CashMovementResponse(**movement.model_dump())

    async def create_transfer(
        self, business_id: str, user_id: str, payload: CashTransferInput
    ) -> List[CashMovementResponse]:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )

        if payload.source_account_id == payload.destination_account_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source and destination accounts must be different.",
            )

        source = await self.account_repo.get_account_by_id_for_update(payload.source_account_id, business_id)
        dest = await self.account_repo.get_account_by_id_for_update(payload.destination_account_id, business_id)

        if not source or source.status != CashAccountStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source cash account is inactive or not found.",
            )
        if not dest or dest.status != CashAccountStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Destination cash account is inactive or not found.",
            )

        if source.currency != dest.currency:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cross-currency transfer is not supported ({source.currency} -> {dest.currency}).",
            )

        if payload.amount <= Decimal("0"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transfer amount must be greater than zero.",
            )

        # Check source balance
        source_bal = await self._calculate_balance(business_id, source)
        if source_bal < payload.amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient balance in source account. Available: {source_bal}, requested: {payload.amount}.",
            )

        import uuid
        transfer_ref_id = payload.idempotency_key or str(uuid.uuid4())

        # Resolve shift context for each side independently
        source_shift_id = None
        dest_shift_id = None
        if source.account_type == CashAccountType.CASH:
            shift = await cashier_shift_service.shift_repo.get_open_shift(business_id, source.id)
            if shift:
                source_shift_id = shift.id
        if dest.account_type == CashAccountType.CASH:
            shift = await cashier_shift_service.shift_repo.get_open_shift(business_id, dest.id)
            if shift:
                dest_shift_id = shift.id

        # Atomic logical transfer: 1. TRANSFER_OUT, 2. TRANSFER_IN
        m_out = await self.account_repo.create_movement(
            business_id=business_id,
            cash_account_id=source.id,
            movement_type=CashMovementType.TRANSFER_OUT,
            amount=payload.amount,
            direction=MovementDirection.OUT,
            performed_by_user_id=user_id,
            reference_type="CASH_TRANSFER",
            reference_id=transfer_ref_id,
            description=payload.description or f"Transfer OUT to {dest.name}",
            shift_id=source_shift_id,
        )

        m_in = await self.account_repo.create_movement(
            business_id=business_id,
            cash_account_id=dest.id,
            movement_type=CashMovementType.TRANSFER_IN,
            amount=payload.amount,
            direction=MovementDirection.IN,
            performed_by_user_id=user_id,
            reference_type="CASH_TRANSFER",
            reference_id=transfer_ref_id,
            description=payload.description or f"Transfer IN from {source.name}",
            shift_id=dest_shift_id,
        )

        # Accounting Integration: post double-entry journal for the transfer.
        # Failure propagates → session auto-rolls back all operational mutations.
        from datetime import datetime, timezone
        await acct_integration.post_cash_transfer(
            business_id=business_id,
            user_id=user_id,
            transfer_id=transfer_ref_id,
            amount=payload.amount,
            transfer_date=datetime.now(timezone.utc),
        )

        return [CashMovementResponse(**m_out.model_dump()), CashMovementResponse(**m_in.model_dump())]

    async def list_movements(
        self,
        business_id: str,
        account_id: str,
        user_id: str,
        movement_type: Optional[CashMovementType] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> CashMovementListResponse:
        await self._validate_access(business_id, user_id)
        account = await self.account_repo.get_account_by_id(account_id, business_id)
        if not account or account.status == CashAccountStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cash account not found.",
            )

        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        movements, total = await self.account_repo.list_movements_for_account(
            business_id=business_id,
            cash_account_id=account_id,
            movement_type=movement_type,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )

        items = [CashMovementResponse(**m.model_dump()) for m in movements]
        return CashMovementListResponse(items=items, page=page, page_size=page_size, total=total)

    async def get_summary(self, business_id: str, user_id: str) -> CashSummaryResponse:
        await self._validate_access(business_id, user_id)

        accounts, total = await self.account_repo.list_accounts(
            business_id=business_id, page=1, page_size=10000
        )

        total_balance = Decimal("0")
        active_count = 0

        for a in accounts:
            if a.currency == "IDR":  # Primary business currency
                bal = await self._calculate_balance(business_id, a)
                total_balance += bal
            if a.status == CashAccountStatus.ACTIVE:
                active_count += 1

        return CashSummaryResponse(
            total_cash_balance=total_balance,
            cash_account_count=total,
            active_account_count=active_count,
            currency="IDR",
        )


cash_account_service = CashAccountService()

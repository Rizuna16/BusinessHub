from typing import List, Optional
from decimal import Decimal
from datetime import datetime, timezone
from fastapi import HTTPException, status

from app.modules.expense.schemas import (
    ExpenseInDB,
    ExpenseCategoryInDB,
    ExpenseResponse,
    ExpenseListResponse,
    ExpenseCategoryResponse,
    ExpenseCategoryListResponse,
    ExpenseSummaryResponse,
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseCategoryCreate,
    ExpenseCategoryUpdate,
    ExpenseStatus,
    ExpenseCategoryStatus,
    ExpenseAnalyticsByCategoryResponse,
    CategoryBreakdownItem,
)
from app.modules.expense.repository import (
    AbstractExpenseRepository,
    expense_repository,
)
from app.modules.cash_account.repository import cash_account_repository
from app.modules.cash_account.schemas import CashAccountStatus, CashMovementType, MovementDirection, CashAccountType
from app.modules.cash_account.service import cash_account_service
from app.modules.supplier.repository import supplier_repository
from app.modules.supplier.schemas import SupplierStatus
from app.modules.business_membership.service import (
    BusinessMembershipService,
    business_membership_service,
)
from app.modules.business_membership.schemas import BusinessMembershipRole
from app.modules.accounting.integration import accounting_integration_service
from app.modules.cashier_shift.service import cashier_shift_service
from app.modules.cashier_shift.schemas import ShiftStatus


class ExpenseService:
    def __init__(
        self,
        expense_repo: AbstractExpenseRepository = expense_repository,
        membership_service: BusinessMembershipService = business_membership_service,
    ):
        self.expense_repo = expense_repo
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

    async def _validate_category(self, business_id: str, category_id: str):
        c = await self.expense_repo.get_category_by_id(category_id, business_id)
        if not c:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Expense category not found in this business.",
            )
        if c.status != ExpenseCategoryStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Expense category is not ACTIVE (current: {c.status}).",
            )
        return c

    async def _validate_cash_account(self, business_id: str, cash_account_id: Optional[str]):
        if cash_account_id is None:
            return None
        acc = await cash_account_repository.get_account_by_id(cash_account_id, business_id)
        if not acc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cash account not found in this business.",
            )
        if acc.status != CashAccountStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cash account is not ACTIVE (current: {acc.status}).",
            )
        return acc

    async def _validate_supplier(self, business_id: str, supplier_id: Optional[str]):
        if supplier_id is None:
            return None
        sup = await supplier_repository.get_by_id(supplier_id, business_id)
        if not sup:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Supplier not found in this business.",
            )
        if sup.status != SupplierStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Supplier is not ACTIVE (current: {sup.status}).",
            )
        return sup

    async def _build_expense_response(self, business_id: str, exp: ExpenseInDB) -> ExpenseResponse:
        cat_name = None
        cash_acc_name = None
        sup_name = None

        if exp.category_id:
            c = await self.expense_repo.get_category_by_id(exp.category_id, business_id)
            if c:
                cat_name = c.name

        if exp.cash_account_id:
            acc = await cash_account_repository.get_account_by_id(exp.cash_account_id, business_id)
            if acc:
                cash_acc_name = acc.name

        if exp.supplier_id:
            s = await supplier_repository.get_by_id(exp.supplier_id, business_id)
            if s:
                sup_name = s.name

        return ExpenseResponse(
            **exp.model_dump(),
            category_name=cat_name,
            cash_account_name=cash_acc_name,
            supplier_name=sup_name,
        )

    # --- Category Management ---

    async def create_category(
        self, business_id: str, user_id: str, payload: ExpenseCategoryCreate
    ) -> ExpenseCategoryResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )

        existing = await self.expense_repo.get_category_by_code(business_id, payload.code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Expense category code '{payload.code.upper()}' already exists in this business.",
            )

        cat = await self.expense_repo.create_category(
            business_id=business_id,
            name=payload.name,
            code=payload.code,
            description=payload.description,
        )
        return ExpenseCategoryResponse(**cat.model_dump())

    async def list_categories(
        self,
        business_id: str,
        user_id: str,
        status_filter: Optional[ExpenseCategoryStatus] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> ExpenseCategoryListResponse:
        await self._validate_access(business_id, user_id)

        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        categories, total = await self.expense_repo.list_categories(
            business_id=business_id,
            status=status_filter,
            search=search,
            page=page,
            page_size=page_size,
        )

        items = [ExpenseCategoryResponse(**c.model_dump()) for c in categories]
        return ExpenseCategoryListResponse(items=items, page=page, page_size=page_size, total=total)

    async def update_category(
        self,
        business_id: str,
        category_id: str,
        user_id: str,
        payload: ExpenseCategoryUpdate,
    ) -> ExpenseCategoryResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        await self._validate_category(business_id, category_id)

        updated = await self.expense_repo.update_category(
            category_id=category_id,
            business_id=business_id,
            name=payload.name,
            description=payload.description,
        )
        return ExpenseCategoryResponse(**updated.model_dump())

    async def archive_category(
        self, business_id: str, category_id: str, user_id: str
    ) -> ExpenseCategoryResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        await self._validate_category(business_id, category_id)

        updated = await self.expense_repo.update_category(
            category_id=category_id,
            business_id=business_id,
            status=ExpenseCategoryStatus.ARCHIVED,
        )
        return ExpenseCategoryResponse(**updated.model_dump())

    # --- Expense Management ---

    async def create_expense(
        self, business_id: str, user_id: str, payload: ExpenseCreate
    ) -> ExpenseResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        await self._validate_category(business_id, payload.category_id)
        await self._validate_cash_account(business_id, payload.cash_account_id)
        await self._validate_supplier(business_id, payload.supplier_id)

        seq = await self.expense_repo.get_next_expense_sequence(business_id)
        expense_number = f"EXP-{seq:06d}"

        exp = await self.expense_repo.create_expense(
            business_id=business_id,
            expense_number=expense_number,
            expense_date=payload.expense_date,
            category_id=payload.category_id,
            amount=payload.amount,
            currency=payload.currency,
            created_by_user_id=user_id,
            cash_account_id=payload.cash_account_id,
            supplier_id=payload.supplier_id,
            description=payload.description,
        )

        return await self._build_expense_response(business_id, exp)

    async def list_expenses(
        self,
        business_id: str,
        user_id: str,
        category_id: Optional[str] = None,
        cash_account_id: Optional[str] = None,
        supplier_id: Optional[str] = None,
        status_filter: Optional[ExpenseStatus] = None,
        search: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> ExpenseListResponse:
        await self._validate_access(business_id, user_id)

        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        expenses, total = await self.expense_repo.list_expenses(
            business_id=business_id,
            category_id=category_id,
            cash_account_id=cash_account_id,
            supplier_id=supplier_id,
            status=status_filter,
            search=search,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )

        items = []
        for e in expenses:
            items.append(await self._build_expense_response(business_id, e))

        return ExpenseListResponse(items=items, page=page, page_size=page_size, total=total)

    async def get_expense(
        self, business_id: str, expense_id: str, user_id: str
    ) -> ExpenseResponse:
        await self._validate_access(business_id, user_id)
        exp = await self.expense_repo.get_expense_by_id(expense_id, business_id)
        if not exp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Expense record not found.",
            )

        return await self._build_expense_response(business_id, exp)

    async def update_expense(
        self,
        business_id: str,
        expense_id: str,
        user_id: str,
        payload: ExpenseUpdate,
    ) -> ExpenseResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        exp = await self.expense_repo.get_expense_id if hasattr(self.expense_repo, 'get_expense_id') else await self.expense_repo.get_expense_by_id(expense_id, business_id)
        if not exp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Expense record not found.",
            )

        if exp.status != ExpenseStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only DRAFT expenses can be updated.",
            )

        if payload.category_id is not None:
            await self._validate_category(business_id, payload.category_id)
        if payload.cash_account_id is not None:
            await self._validate_cash_account(business_id, payload.cash_account_id)
        if payload.supplier_id is not None:
            await self._validate_supplier(business_id, payload.supplier_id)

        updated = await self.expense_repo.update_expense(
            expense_id=expense_id,
            business_id=business_id,
            category_id=payload.category_id,
            cash_account_id=payload.cash_account_id,
            supplier_id=payload.supplier_id,
            expense_date=payload.expense_date,
            amount=payload.amount,
            currency=payload.currency,
            description=payload.description,
        )

        return await self._build_expense_response(business_id, updated)

    async def finalize_expense(
        self, business_id: str, expense_id: str, user_id: str
    ) -> ExpenseResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        exp = await self.expense_repo.get_expense_by_id(expense_id, business_id)
        if not exp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Expense record not found.",
            )

        if exp.status == ExpenseStatus.FINALIZED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Expense is already FINALIZED.",
            )
        if exp.status == ExpenseStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot finalize a CANCELLED expense.",
            )

        # 1. Re-validate category
        await self._validate_category(business_id, exp.category_id)

        # 2. Re-validate cash account and post CASH_OUT if specified
        expense_shift_id = None
        if exp.cash_account_id:
            cash_acc = await self._validate_cash_account(business_id, exp.cash_account_id)
            
            # Resolve shift context for CASH account expenses
            if cash_acc.account_type == CashAccountType.CASH:
                shift = await cashier_shift_service.shift_repo.get_open_shift(
                    business_id, exp.cash_account_id
                )
                if shift:
                    expense_shift_id = shift.id

            # Check duplicate posting guard (reference_type="EXPENSE", reference_id=expense_id)
            existing_mov = await cash_account_repository.find_movement_by_reference(
                business_id=business_id, reference_type="EXPENSE", reference_id=expense_id
            )
            if existing_mov:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cash movement for this expense has already been posted.",
                )

            # Atomic cash posting via cash_account_service / repository
            from app.modules.cash_account.schemas import CashMovementCreate
            await cash_account_service.create_cash_movement(
                business_id=business_id,
                account_id=exp.cash_account_id,
                user_id=user_id,
                payload=CashMovementCreate(
                    movement_type=CashMovementType.EXPENSE,
                    amount=exp.amount,
                    direction=MovementDirection.OUT,
                    reference_type="EXPENSE",
                    reference_id=expense_id,
                    description=f"Expense {exp.expense_number}: {exp.description or ''}".strip(),
                    shift_id=expense_shift_id,
                ),
            )

        now = datetime.now(timezone.utc)

        updated = await self.expense_repo.update_expense(
            expense_id=expense_id,
            business_id=business_id,
            status=ExpenseStatus.FINALIZED,
            finalized_by_user_id=user_id,
            finalized_at=now,
        )

        # Accounting Integration (safe_post for idempotency, with compensation)
        idem_key = f"EXPENSE:{expense_id}:FINALIZED"
        try:
            await accounting_integration_service.safe_post(
                idem_key,
                lambda: accounting_integration_service.post_expense_finalized(
                    business_id=business_id,
                    user_id=user_id,
                    expense_id=expense_id,
                    amount=updated.amount,
                    expense_date=updated.expense_date,
                )
            )
        except Exception as exc:
            await self.expense_repo.update_expense(
                expense_id=expense_id, business_id=business_id,
                status=ExpenseStatus.DRAFT, finalized_by_user_id=None, finalized_at=None,
            )
            if updated.cash_account_id:
                await cash_account_repository.delete_movement_by_reference(
                    business_id=business_id, reference_type="EXPENSE", reference_id=expense_id
                )
            raise exc

        return await self._build_expense_response(business_id, updated)

    async def cancel_expense(
        self, business_id: str, expense_id: str, user_id: str
    ) -> ExpenseResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        exp = await self.expense_repo.get_expense_by_id(expense_id, business_id)
        if not exp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Expense record not found.",
            )

        if exp.status == ExpenseStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Expense is already CANCELLED.",
            )
        if exp.status == ExpenseStatus.FINALIZED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel a FINALIZED expense.",
            )

        now = datetime.now(timezone.utc)
        updated = await self.expense_repo.update_expense(
            expense_id=expense_id,
            business_id=business_id,
            status=ExpenseStatus.CANCELLED,
            cancelled_by_user_id=user_id,
            cancelled_at=now,
        )

        return await self._build_expense_response(business_id, updated)

    async def get_summary(
        self, business_id: str, user_id: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        category_id: Optional[str] = None,
    ) -> ExpenseSummaryResponse:
        await self._validate_access(business_id, user_id)
        
        # Validate date parameters
        if (date_from is None) != (date_to is None):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Both date_from and date_to must be provided together.",
            )
        if date_from and date_to and date_from > date_to:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="date_from must be before or equal to date_to.",
            )
        
        # Validate category_id if provided
        if category_id:
            cat = await self.expense_repo.get_category_by_id(category_id, business_id)
            if not cat:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Expense category not found in this business.",
                )
        
        expenses, total = await self.expense_repo.list_expenses(
            business_id=business_id,
            category_id=category_id,
            date_from=date_from,
            date_to=date_to,
            page=1,
            page_size=10000,
        )
        
        total_amount = Decimal("0")
        finalized_cnt = 0
        draft_cnt = 0
        
        for e in expenses:
            if e.currency == "IDR" and e.status == ExpenseStatus.FINALIZED:
                total_amount += e.amount
            if e.status == ExpenseStatus.FINALIZED:
                finalized_cnt += 1
            elif e.status == ExpenseStatus.DRAFT:
                draft_cnt += 1
        
        return ExpenseSummaryResponse(
            total_expense_amount=total_amount,
            expense_count=total,
            finalized_count=finalized_cnt,
            draft_count=draft_cnt,
            currency="IDR",
        )

    async def get_analytics_by_category(
        self,
        business_id: str,
        user_id: str,
        date_from: datetime,
        date_to: datetime,
        category_id: Optional[str] = None,
    ) -> ExpenseAnalyticsByCategoryResponse:
        await self._validate_access(business_id, user_id)

        if date_from > date_to:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="date_from must be before or equal to date_to.",
            )

        if category_id:
            cat = await self.expense_repo.get_category_by_id(category_id, business_id)
            if not cat:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Expense category not found in this business.",
                )

        expenses, _ = await self.expense_repo.list_expenses(
            business_id=business_id,
            category_id=category_id,
            date_from=date_from,
            date_to=date_to,
            status=ExpenseStatus.FINALIZED,
            page=1,
            page_size=10000,
        )

        cat_map: dict[str, dict] = {}
        for e in expenses:
            cid = e.category_id
            if cid not in cat_map:
                c = await self.expense_repo.get_category_by_id(cid, business_id)
                cat_map[cid] = {
                    "category_id": cid,
                    "category_code": c.code if c else "UNKNOWN",
                    "category_name": c.name if c else "Unknown",
                    "total": Decimal("0"),
                    "expense_count": 0,
                }
            cat_map[cid]["total"] += e.amount
            cat_map[cid]["expense_count"] += 1

        categories = [
            CategoryBreakdownItem(**v) for v in cat_map.values()
        ]
        categories.sort(key=lambda x: (-x.total, x.category_name, x.category_id or ""))

        overall_total = sum((c.total for c in categories), Decimal("0"))
        overall_count = sum(c.expense_count for c in categories)

        return ExpenseAnalyticsByCategoryResponse(
            date_from=date_from,
            date_to=date_to,
            total=overall_total,
            expense_count=overall_count,
            categories=categories,
        )


expense_service = ExpenseService()

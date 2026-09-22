from fastapi import APIRouter, Depends, Path, Query, status
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.core.container import RepositoryContainer
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.expense.schemas import (
    ExpenseResponse,
    ExpenseListResponse,
    ExpenseCategoryResponse,
    ExpenseCategoryListResponse,
    ExpenseSummaryResponse,
    ExpenseAnalyticsByCategoryResponse,
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseCategoryCreate,
    ExpenseCategoryUpdate,
    ExpenseStatus,
    ExpenseCategoryStatus,
)
from app.modules.expense.service import (
    ExpenseService,
    expense_service,
)
from app.modules.business_membership.service import BusinessMembershipService

router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}",
    tags=["Expenses"],
)


def get_expense_service() -> ExpenseService:
    return expense_service


async def get_scoped_expense_service(session: AsyncSession = Depends(get_db_session)) -> ExpenseService:
    """
    Request-scoped ExpenseService wired to the same AsyncSession for transaction boundary.
    """
    container = RepositoryContainer(session)
    membership_svc = BusinessMembershipService(
        repository=container.business_membership,
        user_repo=container.user,
        account_repo=container.account,
        business_repo=container.business,
    )
    return ExpenseService(
        expense_repo=container.expense,
        membership_service=membership_svc,
        session=session,
    )


# --- Expense Categories ---

@router.post("/expense-categories", response_model=ExpenseCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: ExpenseCategoryCreate,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: ExpenseService = Depends(get_scoped_expense_service),
):
    return await service.create_category(business_id, current_user.id, payload)


@router.get("/expense-categories", response_model=ExpenseCategoryListResponse, status_code=status.HTTP_200_OK)
async def list_categories(
    business_id: str = Path(...),
    status: Optional[ExpenseCategoryStatus] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
    service: ExpenseService = Depends(get_scoped_expense_service),
):
    return await service.list_categories(
        business_id=business_id,
        user_id=current_user.id,
        status_filter=status,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.patch("/expense-categories/{category_id}", response_model=ExpenseCategoryResponse, status_code=status.HTTP_200_OK)
async def update_category(
    payload: ExpenseCategoryUpdate,
    business_id: str = Path(...),
    category_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: ExpenseService = Depends(get_scoped_expense_service),
):
    return await service.update_category(business_id, category_id, current_user.id, payload)


@router.post("/expense-categories/{category_id}/archive", response_model=ExpenseCategoryResponse, status_code=status.HTTP_200_OK)
async def archive_category(
    business_id: str = Path(...),
    category_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: ExpenseService = Depends(get_scoped_expense_service),
):
    return await service.archive_category(business_id, category_id, current_user.id)


# --- Expenses ---

@router.post("/expenses", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    payload: ExpenseCreate,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: ExpenseService = Depends(get_scoped_expense_service),
):
    return await service.create_expense(business_id, current_user.id, payload)


@router.get("/expenses", response_model=ExpenseListResponse, status_code=status.HTTP_200_OK)
async def list_expenses(
    business_id: str = Path(...),
    category_id: Optional[str] = Query(None),
    cash_account_id: Optional[str] = Query(None),
    supplier_id: Optional[str] = Query(None),
    status: Optional[ExpenseStatus] = Query(None),
    search: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
    service: ExpenseService = Depends(get_scoped_expense_service),
):
    return await service.list_expenses(
        business_id=business_id,
        user_id=current_user.id,
        category_id=category_id,
        cash_account_id=cash_account_id,
        supplier_id=supplier_id,
        status_filter=status,
        search=search,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )


@router.get("/expenses/summary", response_model=ExpenseSummaryResponse, status_code=status.HTTP_200_OK)
async def get_expense_summary(
    business_id: str = Path(...),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    category_id: Optional[str] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
    service: ExpenseService = Depends(get_scoped_expense_service),
):
    return await service.get_summary(
        business_id=business_id,
        user_id=current_user.id,
        date_from=date_from,
        date_to=date_to,
        category_id=category_id,
    )


@router.get("/expenses/analytics/by-category", response_model=ExpenseAnalyticsByCategoryResponse, status_code=status.HTTP_200_OK)
async def get_expense_analytics_by_category(
    business_id: str = Path(...),
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    category_id: Optional[str] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
    service: ExpenseService = Depends(get_scoped_expense_service),
):
    return await service.get_analytics_by_category(
        business_id=business_id,
        user_id=current_user.id,
        date_from=date_from,
        date_to=date_to,
        category_id=category_id,
    )


@router.get("/expenses/{expense_id}", response_model=ExpenseResponse, status_code=status.HTTP_200_OK)
async def get_expense(
    business_id: str = Path(...),
    expense_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: ExpenseService = Depends(get_scoped_expense_service),
):
    return await service.get_expense(business_id, expense_id, current_user.id)


@router.patch("/expenses/{expense_id}", response_model=ExpenseResponse, status_code=status.HTTP_200_OK)
async def update_expense(
    payload: ExpenseUpdate,
    business_id: str = Path(...),
    expense_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: ExpenseService = Depends(get_scoped_expense_service),
):
    return await service.update_expense(business_id, expense_id, current_user.id, payload)


@router.post("/expenses/{expense_id}/finalize", response_model=ExpenseResponse, status_code=status.HTTP_200_OK)
async def finalize_expense(
    business_id: str = Path(...),
    expense_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: ExpenseService = Depends(get_scoped_expense_service),
):
    return await service.finalize_expense(business_id, expense_id, current_user.id)


@router.post("/expenses/{expense_id}/cancel", response_model=ExpenseResponse, status_code=status.HTTP_200_OK)
async def cancel_expense(
    business_id: str = Path(...),
    expense_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: ExpenseService = Depends(get_scoped_expense_service),
):
    return await service.cancel_expense(business_id, expense_id, current_user.id)

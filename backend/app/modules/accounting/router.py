from typing import Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, Path, Query, status

from app.core.config import settings
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.accounting.schemas import (
    AccountCreate,
    AccountUpdate,
    AccountResponse,
    AccountListResponse,
    JournalEntryCreate,
    JournalEntryResponse,
    JournalEntryListResponse,
    GeneralLedgerResponse,
    TrialBalanceResponse,
    AccountingPeriodCreate,
    AccountingPeriodResponse,
    AccountingPeriodListResponse,
    ProfitAndLossResponse,
    BalanceSheetResponse,
    TaxConfigurationUpdate,
    TaxConfigurationResponse,
    TaxSummaryResponse,
    CashFlowResponse,
    AccountType,
    JournalStatus,
)
from app.modules.accounting.service import (
    AccountingService,
    accounting_service,
)


router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/accounting",
    tags=["Accounting Foundation"],
)


def get_accounting_service() -> AccountingService:
    return accounting_service


# --- Chart of Accounts Routes ---

@router.get("/accounts", response_model=AccountListResponse, status_code=status.HTTP_200_OK)
async def list_accounts(
    business_id: str = Path(...),
    account_type: Optional[AccountType] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
    service: AccountingService = Depends(get_accounting_service),
):
    return await service.list_accounts(business_id=business_id, user_id=current_user.id, account_type=account_type)


@router.post("/accounts", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    payload: AccountCreate,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: AccountingService = Depends(get_accounting_service),
):
    return await service.create_account(business_id=business_id, user_id=current_user.id, payload=payload)


@router.get("/accounts/{account_id}", response_model=AccountResponse, status_code=status.HTTP_200_OK)
async def get_account(
    business_id: str = Path(...),
    account_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: AccountingService = Depends(get_accounting_service),
):
    return await service.get_account(business_id=business_id, account_id=account_id, user_id=current_user.id)


@router.patch("/accounts/{account_id}", response_model=AccountResponse, status_code=status.HTTP_200_OK)
async def update_account(
    payload: AccountUpdate,
    business_id: str = Path(...),
    account_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: AccountingService = Depends(get_accounting_service),
):
    return await service.update_account(business_id=business_id, account_id=account_id, user_id=current_user.id, payload=payload)


@router.delete("/accounts/{account_id}", response_model=AccountResponse, status_code=status.HTTP_200_OK)
async def archive_account(
    business_id: str = Path(...),
    account_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: AccountingService = Depends(get_accounting_service),
):
    return await service.archive_account(business_id=business_id, account_id=account_id, user_id=current_user.id)


# --- Journal Entry Routes ---

@router.get("/journals", response_model=JournalEntryListResponse, status_code=status.HTTP_200_OK)
async def list_journals(
    business_id: str = Path(...),
    branch_id: Optional[str] = Query(None),
    status_filter: Optional[JournalStatus] = Query(None, alias="status"),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
    service: AccountingService = Depends(get_accounting_service),
):
    return await service.list_journals(
        business_id=business_id,
        user_id=current_user.id,
        branch_id=branch_id,
        status_filter=status_filter,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )


@router.post("/journals", response_model=JournalEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_and_post_journal(
    payload: JournalEntryCreate,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: AccountingService = Depends(get_accounting_service),
):
    return await service.create_and_post_journal(business_id=business_id, user_id=current_user.id, payload=payload)


@router.get("/journals/{journal_id}", response_model=JournalEntryResponse, status_code=status.HTTP_200_OK)
async def get_journal(
    business_id: str = Path(...),
    journal_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: AccountingService = Depends(get_accounting_service),
):
    return await service.get_journal(business_id=business_id, journal_id=journal_id, user_id=current_user.id)


@router.post("/journals/{journal_id}/void", response_model=JournalEntryResponse, status_code=status.HTTP_200_OK)
async def void_journal(
    business_id: str = Path(...),
    journal_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: AccountingService = Depends(get_accounting_service),
):
    return await service.void_journal(business_id=business_id, journal_id=journal_id, user_id=current_user.id)


# --- Ledger & Trial Balance Routes ---

@router.get("/ledger/{account_id}", response_model=GeneralLedgerResponse, status_code=status.HTTP_200_OK)
async def get_general_ledger(
    business_id: str = Path(...),
    account_id: str = Path(...),
    branch_id: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
    service: AccountingService = Depends(get_accounting_service),
):
    return await service.get_general_ledger(
        business_id=business_id,
        account_id=account_id,
        user_id=current_user.id,
        branch_id=branch_id,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/trial-balance", response_model=TrialBalanceResponse, status_code=status.HTTP_200_OK)
async def get_trial_balance(
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: AccountingService = Depends(get_accounting_service),
):
    return await service.get_trial_balance(business_id=business_id, user_id=current_user.id)


# --- Accounting Period Routes ---

@router.get("/periods", response_model=AccountingPeriodListResponse, status_code=status.HTTP_200_OK)
async def list_periods(
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: AccountingService = Depends(get_accounting_service),
):
    return await service.list_periods(business_id=business_id, user_id=current_user.id)


@router.post("/periods", response_model=AccountingPeriodResponse, status_code=status.HTTP_201_CREATED)
async def create_period(
    payload: AccountingPeriodCreate,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: AccountingService = Depends(get_accounting_service),
):
    return await service.create_period(business_id=business_id, user_id=current_user.id, payload=payload)


@router.get("/periods/{period_id}", response_model=AccountingPeriodResponse, status_code=status.HTTP_200_OK)
async def get_period(
    business_id: str = Path(...),
    period_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: AccountingService = Depends(get_accounting_service),
):
    return await service.get_period(business_id=business_id, period_id=period_id, user_id=current_user.id)


@router.post("/periods/{period_id}/close", response_model=AccountingPeriodResponse, status_code=status.HTTP_200_OK)
async def close_period(
    business_id: str = Path(...),
    period_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: AccountingService = Depends(get_accounting_service),
):
    return await service.close_period_by_id(business_id=business_id, period_id=period_id, user_id=current_user.id)


# --- Financial Report Routes (Feature #36) ---

@router.get("/reports/profit-and-loss", response_model=ProfitAndLossResponse, status_code=status.HTTP_200_OK)
async def get_profit_and_loss(
    business_id: str = Path(...),
    period_id: str = Query(...),
    current_user: UserResponse = Depends(get_current_user),
    service: AccountingService = Depends(get_accounting_service),
):
    return await service.get_profit_and_loss(business_id=business_id, period_id=period_id, user_id=current_user.id)


@router.get("/reports/balance-sheet", response_model=BalanceSheetResponse, status_code=status.HTTP_200_OK)
async def get_balance_sheet(
    business_id: str = Path(...),
    period_id: str = Query(...),
    current_user: UserResponse = Depends(get_current_user),
    service: AccountingService = Depends(get_accounting_service),
):
    return await service.get_balance_sheet(business_id=business_id, period_id=period_id, user_id=current_user.id)


# --- Tax Configuration Routes (Feature #37) ---

@router.get("/tax-config", response_model=TaxConfigurationResponse, status_code=status.HTTP_200_OK)
async def get_tax_config(
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: AccountingService = Depends(get_accounting_service),
):
    return await service.get_tax_config(business_id=business_id, user_id=current_user.id)


@router.patch("/tax-config", response_model=TaxConfigurationResponse, status_code=status.HTTP_200_OK)
async def update_tax_config(
    payload: TaxConfigurationUpdate,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: AccountingService = Depends(get_accounting_service),
):
    return await service.update_tax_config(business_id=business_id, user_id=current_user.id, payload=payload)


# --- Tax Summary Report (Feature #37) ---

@router.get("/reports/tax-summary", response_model=TaxSummaryResponse, status_code=status.HTTP_200_OK)
async def get_tax_summary(
    business_id: str = Path(...),
    year: int = Query(..., ge=2020, le=2099),
    month: int = Query(..., ge=1, le=12),
    current_user: UserResponse = Depends(get_current_user),
    service: AccountingService = Depends(get_accounting_service),
):
    return await service.get_tax_summary(business_id=business_id, user_id=current_user.id, year=year, month=month)


# --- Cash Flow Statement Report (Feature #40) ---

@router.get("/reports/cash-flow", response_model=CashFlowResponse, status_code=status.HTTP_200_OK)
async def get_cash_flow_statement(
    business_id: str = Path(...),
    period_id: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
    service: AccountingService = Depends(get_accounting_service),
):
    return await service.get_cash_flow_statement(
        business_id=business_id,
        user_id=current_user.id,
        period_id=period_id,
        date_from=date_from,
        date_to=date_to,
    )


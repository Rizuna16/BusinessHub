from datetime import date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field


class DashboardPeriodInfo(BaseModel):
    date_from: date
    date_to: date


class DashboardRevenue(BaseModel):
    total: Decimal = Decimal("0")
    sales_count: int = 0
    return_count: int = 0
    net: Decimal = Decimal("0")


class DashboardExpenses(BaseModel):
    total: Decimal = Decimal("0")
    expense_count: int = 0


class DashboardCashPosition(BaseModel):
    total_balance: Decimal = Decimal("0")
    account_count: int = 0


class DashboardReceivables(BaseModel):
    total_outstanding: Decimal = Decimal("0")
    unpaid_count: int = 0
    partially_paid_count: int = 0


class DashboardPayables(BaseModel):
    total_outstanding: Decimal = Decimal("0")
    unpaid_count: int = 0
    partially_paid_count: int = 0


class DashboardInventory(BaseModel):
    total_items: int = 0
    total_valuation: Decimal = Decimal("0")


class DashboardActivityItem(BaseModel):
    date: str
    type: str
    reference: str
    amount: Decimal
    status: str


class OperationalDashboardResponse(BaseModel):
    period: DashboardPeriodInfo
    revenue: DashboardRevenue
    expenses: DashboardExpenses
    net_operating_result: Decimal
    cash_position: DashboardCashPosition
    receivables: DashboardReceivables
    payables: DashboardPayables
    inventory: DashboardInventory
    recent_activity: List[DashboardActivityItem] = []

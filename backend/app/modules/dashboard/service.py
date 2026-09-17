from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from typing import Optional, List
from dataclasses import dataclass

from fastapi import HTTPException, status

from app.modules.dashboard.schemas import (
    OperationalDashboardResponse,
    DashboardPeriodInfo,
    DashboardRevenue,
    DashboardExpenses,
    DashboardCashPosition,
    DashboardReceivables,
    DashboardPayables,
    DashboardInventory,
    DashboardActivityItem,
)
from app.modules.sales.repository import sales_repository
from app.modules.sales.schemas import SalesStatus
from app.modules.sales_return.repository import sales_return_repository
from app.modules.sales_return.schemas import SalesReturnStatus
from app.modules.sales_receivable.service import sales_receivable_service
from app.modules.purchase_payable.service import purchase_payable_service
from app.modules.cash_account.service import cash_account_service
from app.modules.expense.service import expense_service
from app.modules.expense.repository import expense_repository
from app.modules.expense.schemas import ExpenseStatus
from app.modules.inventory.service import inventory_service
from app.modules.business_membership.service import business_membership_service


class OperationalDashboardService:
    async def _validate_access(self, business_id: str, user_id: str):
        await business_membership_service.require_active_membership(business_id, user_id)

    def _to_half_open_utc(
        self, start_date: date, end_date: date
    ) -> tuple[datetime, datetime]:
        start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
        end_dt_exclusive = datetime.combine(
            end_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc
        )
        return start_dt, end_dt_exclusive

    async def _get_revenue(
        self, business_id: str, start_dt: datetime, end_dt_exclusive: datetime,
        branch_id: Optional[str],
    ) -> DashboardRevenue:
        finalized_sales, finalized_count = await sales_repository.list_sales(
            business_id=business_id,
            status=SalesStatus.FINALIZED,
            branch_id=branch_id,
            page=1,
            page_size=100000,
        )
        sales_in_range = [
            s for s in finalized_sales
            if start_dt <= s.sales_date < end_dt_exclusive
        ]
        total = sum((s.grand_total for s in sales_in_range), Decimal("0"))
        sales_count = len(sales_in_range)

        all_returns, _ = await sales_return_repository.list_returns(
            business_id=business_id,
            status=SalesReturnStatus.FINALIZED,
            page=1,
            page_size=100000,
        )
        returns_in_range = [
            r for r in all_returns
            if start_dt <= r.return_date < end_dt_exclusive
        ]
        return_total = sum((r.grand_total for r in returns_in_range), Decimal("0"))
        return_count = len(returns_in_range)

        net = total - return_total

        return DashboardRevenue(
            total=total.quantize(Decimal("0.01")),
            sales_count=sales_count,
            return_count=return_count,
            net=net.quantize(Decimal("0.01")),
        )

    async def _get_expenses(
        self, business_id: str, start_dt: datetime, end_dt_exclusive: datetime,
        user_id: str,
    ) -> DashboardExpenses:
        all_expenses, _ = await expense_repository.list_expenses(
            business_id=business_id,
            status=ExpenseStatus.FINALIZED,
            page=1,
            page_size=100000,
        )
        expenses_in_range = [
            e for e in all_expenses
            if start_dt <= e.expense_date < end_dt_exclusive
        ]
        total = sum((e.amount for e in expenses_in_range), Decimal("0"))
        count = len(expenses_in_range)

        return DashboardExpenses(
            total=total.quantize(Decimal("0.01")),
            expense_count=count,
        )

    async def _get_cash_position(self, business_id: str, user_id: str) -> DashboardCashPosition:
        summary = await cash_account_service.get_summary(business_id, user_id)
        return DashboardCashPosition(
            total_balance=summary.total_cash_balance.quantize(Decimal("0.01")),
            account_count=summary.active_account_count,
        )

    async def _get_receivables(self, business_id: str, user_id: str) -> DashboardReceivables:
        summary = await sales_receivable_service.get_summary(business_id, user_id)
        return DashboardReceivables(
            total_outstanding=summary.total_outstanding_amount.quantize(Decimal("0.01")),
            unpaid_count=summary.unpaid_count,
            partially_paid_count=summary.partially_paid_count,
        )

    async def _get_payables(self, business_id: str, user_id: str) -> DashboardPayables:
        summary = await purchase_payable_service.get_summary(business_id, user_id)
        return DashboardPayables(
            total_outstanding=summary.total_outstanding_amount.quantize(Decimal("0.01")),
            unpaid_count=summary.unpaid_count,
            partially_paid_count=summary.partially_paid_count,
        )

    async def _get_inventory(self, business_id: str, user_id: str) -> DashboardInventory:
        valuation = await inventory_service.get_valuation_summary(business_id, user_id)
        return DashboardInventory(
            total_items=len(valuation.items),
            total_valuation=valuation.total_inventory_value.quantize(Decimal("0.01")),
        )

    async def _get_recent_activity(
        self, business_id: str, start_dt: datetime, end_dt_exclusive: datetime,
        limit: int = 10,
    ) -> List[DashboardActivityItem]:
        candidates: List[DashboardActivityItem] = []

        finalized_sales, _ = await sales_repository.list_sales(
            business_id=business_id,
            status=SalesStatus.FINALIZED,
            page=1,
            page_size=100000,
        )
        for s in finalized_sales:
            if start_dt <= s.sales_date < end_dt_exclusive:
                candidates.append(DashboardActivityItem(
                    date=s.sales_date.strftime("%Y-%m-%d"),
                    type="SALE",
                    reference=s.sales_number,
                    amount=s.grand_total,
                    status="FINALIZED",
                ))

        all_returns, _ = await sales_return_repository.list_returns(
            business_id=business_id,
            status=SalesReturnStatus.FINALIZED,
            page=1,
            page_size=100000,
        )
        for r in all_returns:
            if start_dt <= r.return_date < end_dt_exclusive:
                candidates.append(DashboardActivityItem(
                    date=r.return_date.strftime("%Y-%m-%d"),
                    type="SALES_RETURN",
                    reference=r.return_number,
                    amount=r.grand_total,
                    status="FINALIZED",
                ))

        all_expenses, _ = await expense_repository.list_expenses(
            business_id=business_id,
            status=ExpenseStatus.FINALIZED,
            page=1,
            page_size=100000,
        )
        for e in all_expenses:
            if start_dt <= e.expense_date < end_dt_exclusive:
                candidates.append(DashboardActivityItem(
                    date=e.expense_date.strftime("%Y-%m-%d"),
                    type="EXPENSE",
                    reference=e.expense_number,
                    amount=e.amount,
                    status="FINALIZED",
                ))

        candidates.sort(key=lambda x: (x.date, x.type, x.reference), reverse=True)
        return candidates[:limit]

    async def get_dashboard(
        self,
        business_id: str,
        user_id: str,
        date_from: date,
        date_to: date,
        branch_id: Optional[str] = None,
    ) -> OperationalDashboardResponse:
        await self._validate_access(business_id, user_id)

        start_dt, end_dt_exclusive = self._to_half_open_utc(date_from, date_to)

        revenue = await self._get_revenue(business_id, start_dt, end_dt_exclusive, branch_id)
        expenses = await self._get_expenses(business_id, start_dt, end_dt_exclusive, user_id)
        cash = await self._get_cash_position(business_id, user_id)
        receivables = await self._get_receivables(business_id, user_id)
        payables = await self._get_payables(business_id, user_id)
        inventory = await self._get_inventory(business_id, user_id)
        activity = await self._get_recent_activity(business_id, start_dt, end_dt_exclusive)

        net_operating = revenue.net - expenses.total

        return OperationalDashboardResponse(
            period=DashboardPeriodInfo(date_from=date_from, date_to=date_to),
            revenue=revenue,
            expenses=expenses,
            net_operating_result=net_operating.quantize(Decimal("0.01")),
            cash_position=cash,
            receivables=receivables,
            payables=payables,
            inventory=inventory,
            recent_activity=activity,
        )


operational_dashboard_service = OperationalDashboardService()

"""
Feature #36 — Financial Reporting (Profit & Loss + Balance Sheet) Test Suite
"""
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from app.main import app
from app.modules.authentication.repository import InMemoryUserRepository
from app.modules.account.repository import InMemoryAccountRepository
from app.modules.business.repository import InMemoryBusinessRepository
from app.modules.business_membership.repository import InMemoryBusinessMembershipRepository
from app.modules.accounting.repository import InMemoryAccountingRepository

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_repositories():
    InMemoryAccountingRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryUserRepository.clear()
    yield
    InMemoryAccountingRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryUserRepository.clear()


# ─────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────

def register_user(email="owner@example.com", name="Owner Test"):
    res = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": name, "password": "Password123", "password_confirmation": "Password123"},
    )
    assert res.status_code == 201
    data = res.json()
    token = data.get("access_token")
    if not token:
        login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123"})
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
    return token, data["id"]


def create_business(token, name="Test Business"):
    res = client.post(
        "/api/v1/businesses",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "legal_name": name, "business_type": "retail", "timezone": "UTC", "locale": "en-US"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def add_member(token, biz_id, member_token):
    member_user_id = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {member_token}"}
    ).json()["id"]
    res = client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": member_user_id, "role": "MEMBER"},
    )
    assert res.status_code == 201
    return res.json()


def create_period(token, biz_id, period_name="2026-01", start_date="2026-01-01", end_date="2026-01-31"):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/accounting/periods",
        headers={"Authorization": f"Bearer {token}"},
        json={"period_name": period_name, "start_date": start_date, "end_date": end_date},
    )
    assert res.status_code == 201
    return res.json()["id"]


def close_period(token, biz_id, period_id):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/accounting/periods/{period_id}/close",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    return res.json()


def get_account_id(token, biz_id, code):
    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/accounts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    for acc in res.json()["items"]:
        if acc["code"] == code:
            return acc["id"]
    return None


def post_journal(token, biz_id, journal_date, description, lines):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/accounting/journals",
        headers={"Authorization": f"Bearer {token}"},
        json={"journal_date": journal_date, "description": description, "lines": lines},
    )
    assert res.status_code == 201
    return res.json()


# ═══════════════════════════════════════════════════
# 1. PROFIT & LOSS TESTS
# ═══════════════════════════════════════════════════

class TestProfitAndLossReport:
    def test_pnl_revenue_and_expense_aggregation(self):
        token, _ = register_user()
        biz_id = create_business(token)
        period_id = create_period(token, biz_id, "2026-01", "2026-01-01", "2026-01-31")

        cash_id = get_account_id(token, biz_id, "1100")
        sales_id = get_account_id(token, biz_id, "4100")
        expense_id = get_account_id(token, biz_id, "5100")

        # Post Revenue: 1,000,000
        post_journal(
            token, biz_id, "2026-01-15T10:00:00Z", "Cash Sale",
            [{"account_id": cash_id, "debit": 1000000, "credit": 0}, {"account_id": sales_id, "debit": 0, "credit": 1000000}],
        )

        # Post Expense: 300,000
        post_journal(
            token, biz_id, "2026-01-20T10:00:00Z", "Office Rent",
            [{"account_id": expense_id, "debit": 300000, "credit": 0}, {"account_id": cash_id, "debit": 0, "credit": 300000}],
        )

        res = client.get(
            f"/api/v1/businesses/{biz_id}/accounting/reports/profit-and-loss?period_id={period_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()

        assert Decimal(str(data["total_revenue"])) == Decimal("1000000")
        assert Decimal(str(data["total_expense"])) == Decimal("300000")
        assert Decimal(str(data["net_profit"])) == Decimal("700000")

        assert len(data["revenue_items"]) == 1
        assert data["revenue_items"][0]["account_code"] == "4100"
        assert Decimal(str(data["revenue_items"][0]["amount"])) == Decimal("1000000")

        assert len(data["expense_items"]) == 1
        assert data["expense_items"][0]["account_code"] == "5100"
        assert Decimal(str(data["expense_items"][0]["amount"])) == Decimal("300000")

    def test_pnl_date_boundaries_inclusive(self):
        token, _ = register_user()
        biz_id = create_business(token)
        period_id = create_period(token, biz_id, "2026-01", "2026-01-01", "2026-01-31")

        cash_id = get_account_id(token, biz_id, "1100")
        sales_id = get_account_id(token, biz_id, "4100")

        # Post exactly on start_date
        post_journal(
            token, biz_id, "2026-01-01T00:00:00Z", "Start Date Sale",
            [{"account_id": cash_id, "debit": 100, "credit": 0}, {"account_id": sales_id, "debit": 0, "credit": 100}],
        )

        # Post exactly on end_date
        post_journal(
            token, biz_id, "2026-01-31T23:59:59Z", "End Date Sale",
            [{"account_id": cash_id, "debit": 200, "credit": 0}, {"account_id": sales_id, "debit": 0, "credit": 200}],
        )

        res = client.get(
            f"/api/v1/businesses/{biz_id}/accounting/reports/profit-and-loss?period_id={period_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert Decimal(str(res.json()["total_revenue"])) == Decimal("300")

    def test_pnl_excludes_outside_period_journals(self):
        token, _ = register_user()
        biz_id = create_business(token)
        period_id = create_period(token, biz_id, "2026-01", "2026-01-01", "2026-01-31")

        cash_id = get_account_id(token, biz_id, "1100")
        sales_id = get_account_id(token, biz_id, "4100")

        # Prior journal (Dec 2025)
        post_journal(
            token, biz_id, "2025-12-31T12:00:00Z", "Dec Sale",
            [{"account_id": cash_id, "debit": 500, "credit": 0}, {"account_id": sales_id, "debit": 0, "credit": 500}],
        )

        # Inside journal (Jan 2026)
        post_journal(
            token, biz_id, "2026-01-15T12:00:00Z", "Jan Sale",
            [{"account_id": cash_id, "debit": 1000, "credit": 0}, {"account_id": sales_id, "debit": 0, "credit": 1000}],
        )

        # Subsequent journal (Feb 2026)
        post_journal(
            token, biz_id, "2026-02-01T12:00:00Z", "Feb Sale",
            [{"account_id": cash_id, "debit": 700, "credit": 0}, {"account_id": sales_id, "debit": 0, "credit": 700}],
        )

        res = client.get(
            f"/api/v1/businesses/{biz_id}/accounting/reports/profit-and-loss?period_id={period_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        # Only Jan sale (1000) included
        assert Decimal(str(res.json()["total_revenue"])) == Decimal("1000")

    def test_pnl_excludes_voided_journals(self):
        token, _ = register_user()
        biz_id = create_business(token)
        period_id = create_period(token, biz_id, "2026-01", "2026-01-01", "2026-01-31")

        cash_id = get_account_id(token, biz_id, "1100")
        sales_id = get_account_id(token, biz_id, "4100")

        j1 = post_journal(
            token, biz_id, "2026-01-10T00:00:00Z", "Valid Sale",
            [{"account_id": cash_id, "debit": 500, "credit": 0}, {"account_id": sales_id, "debit": 0, "credit": 500}],
        )
        j2 = post_journal(
            token, biz_id, "2026-01-12T00:00:00Z", "To Void",
            [{"account_id": cash_id, "debit": 300, "credit": 0}, {"account_id": sales_id, "debit": 0, "credit": 300}],
        )

        # Void j2
        client.post(
            f"/api/v1/businesses/{biz_id}/accounting/journals/{j2['id']}/void",
            headers={"Authorization": f"Bearer {token}"},
        )

        res = client.get(
            f"/api/v1/businesses/{biz_id}/accounting/reports/profit-and-loss?period_id={period_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert Decimal(str(res.json()["total_revenue"])) == Decimal("500")

    def test_pnl_empty_period_returns_zeros(self):
        token, _ = register_user()
        biz_id = create_business(token)
        period_id = create_period(token, biz_id, "2026-01", "2026-01-01", "2026-01-31")

        res = client.get(
            f"/api/v1/businesses/{biz_id}/accounting/reports/profit-and-loss?period_id={period_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert Decimal(str(data["total_revenue"])) == Decimal("0")
        assert Decimal(str(data["total_expense"])) == Decimal("0")
        assert Decimal(str(data["net_profit"])) == Decimal("0")
        assert len(data["revenue_items"]) == 0
        assert len(data["expense_items"]) == 0

    def test_pnl_works_for_closed_period(self):
        token, _ = register_user()
        biz_id = create_business(token)
        period_id = create_period(token, biz_id, "2026-01", "2026-01-01", "2026-01-31")

        cash_id = get_account_id(token, biz_id, "1100")
        sales_id = get_account_id(token, biz_id, "4100")

        post_journal(
            token, biz_id, "2026-01-15T00:00:00Z", "Sale",
            [{"account_id": cash_id, "debit": 1000, "credit": 0}, {"account_id": sales_id, "debit": 0, "credit": 1000}],
        )

        close_period(token, biz_id, period_id)

        res = client.get(
            f"/api/v1/businesses/{biz_id}/accounting/reports/profit-and-loss?period_id={period_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert res.json()["period"]["status"] == "CLOSED"
        assert Decimal(str(res.json()["total_revenue"])) == Decimal("1000")


# ═══════════════════════════════════════════════════
# 2. BALANCE SHEET TESTS
# ═══════════════════════════════════════════════════

class TestBalanceSheetReport:
    def test_balance_sheet_cumulative_and_equation(self):
        """
        Scenario:
        Opening Owner Equity: 1,000 (Cash 1000, Owner Equity 1000)
        Sale: 500 (Cash 500, Revenue 500)
        Expense: 100 (Expense 100, Cash 100)

        Assets:
            Cash = 1000 + 500 - 100 = 1400
        Liabilities: 0
        Equity accounts:
            Owner Equity = 1000 (NOT 1400)
        Current Period Profit:
            500 - 100 = 400
        Total L+E:
            0 + 1000 + 400 = 1400
        is_balanced: true
        """
        token, _ = register_user()
        biz_id = create_business(token)
        period_id = create_period(token, biz_id, "2026-01", "2026-01-01", "2026-01-31")

        cash_id = get_account_id(token, biz_id, "1100")
        equity_id = get_account_id(token, biz_id, "3100")
        sales_id = get_account_id(token, biz_id, "4100")
        expense_id = get_account_id(token, biz_id, "5100")

        # 1. Capital injection
        post_journal(
            token, biz_id, "2026-01-01T10:00:00Z", "Owner Equity",
            [{"account_id": cash_id, "debit": 1000, "credit": 0}, {"account_id": equity_id, "debit": 0, "credit": 1000}],
        )

        # 2. Sale
        post_journal(
            token, biz_id, "2026-01-10T10:00:00Z", "Cash Sale",
            [{"account_id": cash_id, "debit": 500, "credit": 0}, {"account_id": sales_id, "debit": 0, "credit": 500}],
        )

        # 3. Expense
        post_journal(
            token, biz_id, "2026-01-20T10:00:00Z", "General Expense",
            [{"account_id": expense_id, "debit": 100, "credit": 0}, {"account_id": cash_id, "debit": 0, "credit": 100}],
        )

        res = client.get(
            f"/api/v1/businesses/{biz_id}/accounting/reports/balance-sheet?period_id={period_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()

        assert Decimal(str(data["total_assets"])) == Decimal("1400")
        assert Decimal(str(data["total_liabilities"])) == Decimal("0")
        assert Decimal(str(data["total_equity"])) == Decimal("1000")
        assert Decimal(str(data["net_profit_current_period"])) == Decimal("400")
        assert Decimal(str(data["total_liabilities_and_equity"])) == Decimal("1400")
        assert data["is_balanced"] is True

    def test_balance_sheet_includes_prior_period_journals(self):
        """Balance sheet must be cumulative (includes transactions from earlier periods)."""
        token, _ = register_user()
        biz_id = create_business(token)
        period1 = create_period(token, biz_id, "2026-01", "2026-01-01", "2026-01-31")
        period2 = create_period(token, biz_id, "2026-02", "2026-02-01", "2026-02-28")

        cash_id = get_account_id(token, biz_id, "1100")
        equity_id = get_account_id(token, biz_id, "3100")

        # Post in period 1
        post_journal(
            token, biz_id, "2026-01-15T00:00:00Z", "Jan Capital",
            [{"account_id": cash_id, "debit": 5000, "credit": 0}, {"account_id": equity_id, "debit": 0, "credit": 5000}],
        )

        # Check Balance Sheet for period 2 (Feb): Jan capital must be included
        res = client.get(
            f"/api/v1/businesses/{biz_id}/accounting/reports/balance-sheet?period_id={period2}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert Decimal(str(res.json()["total_assets"])) == Decimal("5000")
        assert Decimal(str(res.json()["total_equity"])) == Decimal("5000")

    def test_balance_sheet_excludes_subsequent_journals(self):
        """Balance sheet must NOT include journals posted after period.end_date."""
        token, _ = register_user()
        biz_id = create_business(token)
        period1 = create_period(token, biz_id, "2026-01", "2026-01-01", "2026-01-31")

        cash_id = get_account_id(token, biz_id, "1100")
        equity_id = get_account_id(token, biz_id, "3100")

        # Jan transaction
        post_journal(
            token, biz_id, "2026-01-15T00:00:00Z", "Jan Capital",
            [{"account_id": cash_id, "debit": 1000, "credit": 0}, {"account_id": equity_id, "debit": 0, "credit": 1000}],
        )

        # Feb transaction (after period 1)
        post_journal(
            token, biz_id, "2026-02-10T00:00:00Z", "Feb Capital",
            [{"account_id": cash_id, "debit": 2000, "credit": 0}, {"account_id": equity_id, "debit": 0, "credit": 2000}],
        )

        res = client.get(
            f"/api/v1/businesses/{biz_id}/accounting/reports/balance-sheet?period_id={period1}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        # Only Jan (1000) included
        assert Decimal(str(res.json()["total_assets"])) == Decimal("1000")

    def test_balance_sheet_works_for_closed_period(self):
        token, _ = register_user()
        biz_id = create_business(token)
        period_id = create_period(token, biz_id, "2026-01", "2026-01-01", "2026-01-31")

        cash_id = get_account_id(token, biz_id, "1100")
        equity_id = get_account_id(token, biz_id, "3100")

        post_journal(
            token, biz_id, "2026-01-15T00:00:00Z", "Capital",
            [{"account_id": cash_id, "debit": 1000, "credit": 0}, {"account_id": equity_id, "debit": 0, "credit": 1000}],
        )
        close_period(token, biz_id, period_id)

        res = client.get(
            f"/api/v1/businesses/{biz_id}/accounting/reports/balance-sheet?period_id={period_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert res.json()["is_balanced"] is True


# ═══════════════════════════════════════════════════
# 3. SECURITY & TENANCY TESTS
# ═══════════════════════════════════════════════════

class TestReportingSecurity:
    def test_unauthenticated_requests_rejected(self):
        res1 = client.get("/api/v1/businesses/biz-123/accounting/reports/profit-and-loss?period_id=p1")
        assert res1.status_code == 401
        res2 = client.get("/api/v1/businesses/biz-123/accounting/reports/balance-sheet?period_id=p1")
        assert res2.status_code == 401

    def test_invalid_period_id_returns_404(self):
        token, _ = register_user()
        biz_id = create_business(token)

        res = client.get(
            f"/api/v1/businesses/{biz_id}/accounting/reports/profit-and-loss?period_id=nonexistent",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 404

    def test_cross_business_period_access_denied(self):
        t1, _ = register_user("a@test.com")
        t2, _ = register_user("b@test.com")
        biz1 = create_business(t1)
        biz2 = create_business(t2)

        period1 = create_period(t1, biz1, "2026-01", "2026-01-01", "2026-01-31")

        # User 2 tries to access Biz 1's period in Biz 2 report
        res = client.get(
            f"/api/v1/businesses/{biz2}/accounting/reports/profit-and-loss?period_id={period1}",
            headers={"Authorization": f"Bearer {t2}"},
        )
        assert res.status_code == 404

    def test_member_can_read_reports(self):
        owner_token, _ = register_user("owner@test.com")
        biz_id = create_business(owner_token)
        period_id = create_period(owner_token, biz_id, "2026-01", "2026-01-01", "2026-01-31")

        member_token, _ = register_user("member@test.com", "Member")
        add_member(owner_token, biz_id, member_token)

        res = client.get(
            f"/api/v1/businesses/{biz_id}/accounting/reports/profit-and-loss?period_id={period_id}",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert res.status_code == 200

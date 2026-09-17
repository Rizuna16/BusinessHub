import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta

from app.main import app
from app.modules.authentication.repository import InMemoryUserRepository
from app.modules.account.repository import InMemoryAccountRepository
from app.modules.business.repository import InMemoryBusinessRepository
from app.modules.business_membership.repository import InMemoryBusinessMembershipRepository
from app.modules.cash_account.repository import InMemoryCashAccountRepository
from app.modules.supplier.repository import InMemorySupplierRepository
from app.modules.expense.repository import InMemoryExpenseRepository

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_repositories():
    InMemoryExpenseRepository.clear()
    InMemoryCashAccountRepository.clear()
    InMemorySupplierRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryUserRepository.clear()
    yield
    InMemoryExpenseRepository.clear()
    InMemoryCashAccountRepository.clear()
    InMemorySupplierRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryUserRepository.clear()


def register_user(email="owner@example.com", name="Owner Test"):
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": name,
            "password": "Password123",
            "password_confirmation": "Password123",
        },
    )
    assert res.status_code == 201
    data = res.json()
    token = data.get("access_token")
    if not token:
        login_res = client.post(
            "/api/v1/auth/login", json={"email": email, "password": "Password123"}
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
    return token, data["id"]


def create_business(token, name="Test Business"):
    res = client.post(
        "/api/v1/businesses",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": name,
            "legal_name": name,
            "business_type": "retail",
            "timezone": "UTC",
            "locale": "en-US",
        },
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_category(token, business_id, name="Utilities", code="UTIL"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/expense-categories",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code, "description": "Utilities expense"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_cash_account(token, business_id, name="Kas", code="CASH", balance="10000000"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/cash-accounts",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": name,
            "code": code,
            "account_type": "CASH",
            "currency": "IDR",
            "opening_balance": balance,
        },
    )
    assert res.status_code == 201
    return res.json()["id"]


class TestExpenseAnalytics:

    def test_summary_and_category_breakdown_success(self):
        token, _ = register_user()
        biz_id = create_business(token)
        cat1 = create_category(token, biz_id, name="Utilities", code="UTIL")
        cat2 = create_category(token, biz_id, name="Rent", code="RENT")
        cash_id = create_cash_account(token, biz_id)

        d1 = "2026-09-10T10:00:00Z"
        d2 = "2026-09-15T10:00:00Z"

        # Expense 1 (Finalized, Cat1, 100000)
        exp1 = client.post(
            f"/api/v1/businesses/{biz_id}/expenses",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "category_id": cat1,
                "cash_account_id": cash_id,
                "expense_date": d1,
                "amount": "100000",
                "currency": "IDR",
            },
        ).json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/expenses/{exp1}/finalize", headers={"Authorization": f"Bearer {token}"})

        # Expense 2 (Finalized, Cat1, 200000)
        exp2 = client.post(
            f"/api/v1/businesses/{biz_id}/expenses",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "category_id": cat1,
                "cash_account_id": cash_id,
                "expense_date": d2,
                "amount": "200000",
                "currency": "IDR",
            },
        ).json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/expenses/{exp2}/finalize", headers={"Authorization": f"Bearer {token}"})

        # Expense 3 (Finalized, Cat2, 500000)
        exp3 = client.post(
            f"/api/v1/businesses/{biz_id}/expenses",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "category_id": cat2,
                "cash_account_id": cash_id,
                "expense_date": d2,
                "amount": "500000",
                "currency": "IDR",
            },
        ).json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/expenses/{exp3}/finalize", headers={"Authorization": f"Bearer {token}"})

        # Expense 4 (Draft, Cat1, 999999 - should be excluded from analytics)
        client.post(
            f"/api/v1/businesses/{biz_id}/expenses",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "category_id": cat1,
                "cash_account_id": cash_id,
                "expense_date": d2,
                "amount": "999999",
                "currency": "IDR",
            },
        )

        # 1. Test Summary with Date Range
        sum_res = client.get(
            f"/api/v1/businesses/{biz_id}/expenses/summary?date_from=2026-09-01T00:00:00Z&date_to=2026-09-30T23:59:59Z",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert sum_res.status_code == 200
        sum_data = sum_res.json()
        assert Decimal(str(sum_data["total_expense_amount"])) == Decimal("800000")
        assert sum_data["finalized_count"] == 3
        assert sum_data["draft_count"] == 1

        # 2. Test Category Breakdown
        an_res = client.get(
            f"/api/v1/businesses/{biz_id}/expenses/analytics/by-category?date_from=2026-09-01T00:00:00Z&date_to=2026-09-30T23:59:59Z",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert an_res.status_code == 200
        an_data = an_res.json()
        assert Decimal(str(an_data["total"])) == Decimal("800000")
        assert an_data["expense_count"] == 3
        cats = an_data["categories"]
        assert len(cats) == 2
        # RENT (500000) should be first due to DESC ordering
        assert cats[0]["category_code"] == "RENT"
        assert Decimal(str(cats[0]["total"])) == Decimal("500000")
        assert cats[1]["category_code"] == "UTIL"
        assert Decimal(str(cats[1]["total"])) == Decimal("300000")

    def test_date_validation_rules(self):
        token, _ = register_user()
        biz_id = create_business(token)

        # Only date_from -> 422
        res = client.get(
            f"/api/v1/businesses/{biz_id}/expenses/summary?date_from=2026-09-01T00:00:00Z",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 422

        # Reversed date range (date_from > date_to) -> 422
        res2 = client.get(
            f"/api/v1/businesses/{biz_id}/expenses/analytics/by-category?date_from=2026-09-30T00:00:00Z&date_to=2026-09-01T00:00:00Z",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res2.status_code == 422

    def test_category_filter_and_idor(self):
        token1, _ = register_user(email="u1@example.com")
        biz1 = create_business(token1, name="Biz 1")
        cat1 = create_category(token1, biz1, name="Cat 1", code="C1")

        token2, _ = register_user(email="u2@example.com")
        biz2 = create_business(token2, name="Biz 2")
        cat2 = create_category(token2, biz2, name="Cat 2", code="C2")

        # Business 1 tries to query with Business 2 category_id -> 404
        res = client.get(
            f"/api/v1/businesses/{biz1}/expenses/analytics/by-category?date_from=2026-09-01T00:00:00Z&date_to=2026-09-30T23:59:59Z&category_id={cat2}",
            headers={"Authorization": f"Bearer {token1}"},
        )
        assert res.status_code == 404

    def test_unauthenticated_and_unauthorized(self):
        res = client.get("/api/v1/businesses/somebiz/expenses/analytics/by-category?date_from=2026-09-01T00:00:00Z&date_to=2026-09-30T23:59:59Z")
        assert res.status_code == 401

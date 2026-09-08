import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from datetime import datetime, timezone

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


def create_category(token, business_id, name="Operasional Kantor", code="OFFICE"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/expense-categories",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code, "description": "Biaya kantor"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_cash_account(token, business_id, name="Kas Utama", code="CASH-01", balance="1000000"):
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


def create_supplier(token, business_id, name="PT Supplier"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/suppliers",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "supplier_type": "ORGANIZATION"},
    )
    assert res.status_code == 201
    return res.json()["id"]


class TestExpenseFeature:

    # 1. Unauthenticated access rejected
    def test_unauthenticated_access_rejected(self):
        res = client.get("/api/v1/businesses/biz123/expenses")
        assert res.status_code == 401

    # 2. Category CRUD & uniqueness
    def test_expense_category_crud(self):
        token, _ = register_user()
        biz_id = create_business(token)

        # Create
        cat_id = create_category(token, biz_id, name="Listrik & Air", code="UTILITY")

        # Duplicate code rejected
        dup_res = client.post(
            f"/api/v1/businesses/{biz_id}/expense-categories",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Lainnya", "code": "UTILITY"},
        )
        assert dup_res.status_code == 400

        # List
        list_res = client.get(
            f"/api/v1/businesses/{biz_id}/expense-categories",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_res.status_code == 200
        assert list_res.json()["total"] == 1

        # Archive
        arch_res = client.post(
            f"/api/v1/businesses/{biz_id}/expense-categories/{cat_id}/archive",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert arch_res.status_code == 200
        assert arch_res.json()["status"] == "ARCHIVED"

    # 3. Create Draft Expense & EXP-000001 sequence
    def test_create_expense_draft(self):
        token, _ = register_user()
        biz_id = create_business(token)
        cat_id = create_category(token, biz_id)
        cash_id = create_cash_account(token, biz_id)

        res = client.post(
            f"/api/v1/businesses/{biz_id}/expenses",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "category_id": cat_id,
                "cash_account_id": cash_id,
                "expense_date": datetime.now(timezone.utc).isoformat(),
                "amount": "150000",
                "currency": "IDR",
                "description": "Beli kertas & ATK",
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "DRAFT"
        assert data["expense_number"] == "EXP-000001"
        assert data["amount"] == "150000"

    # 4. Finalize Expense & Cash Account CASH_OUT movement posting
    def test_finalize_expense_posts_cash_movement(self):
        token, _ = register_user()
        biz_id = create_business(token)
        cat_id = create_category(token, biz_id)
        cash_id = create_cash_account(token, biz_id, balance="1000000")

        exp_id = client.post(
            f"/api/v1/businesses/{biz_id}/expenses",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "category_id": cat_id,
                "cash_account_id": cash_id,
                "expense_date": datetime.now(timezone.utc).isoformat(),
                "amount": "200000",
                "currency": "IDR",
                "description": "Pembayaran listrik",
            },
        ).json()["id"]

        # Finalize
        fin_res = client.post(
            f"/api/v1/businesses/{biz_id}/expenses/{exp_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fin_res.status_code == 200
        assert fin_res.json()["status"] == "FINALIZED"

        # Verify Cash Account balance deducted (1,000,000 - 200,000 = 800,000)
        acc = client.get(
            f"/api/v1/businesses/{biz_id}/cash-accounts/{cash_id}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        assert Decimal(str(acc["current_balance"])) == Decimal("800000")

        # Verify Cash Movement record created
        movements = client.get(
            f"/api/v1/businesses/{biz_id}/cash-accounts/{cash_id}/movements",
            headers={"Authorization": f"Bearer {token}"},
        ).json()["items"]

        exp_mov = [m for m in movements if m["movement_type"] == "EXPENSE"]
        assert len(exp_mov) == 1
        assert exp_mov[0]["reference_type"] == "EXPENSE"
        assert exp_mov[0]["reference_id"] == exp_id

    # 5. Insufficient cash balance prevents Expense finalization
    def test_insufficient_cash_prevents_expense_finalization(self):
        token, _ = register_user()
        biz_id = create_business(token)
        cat_id = create_category(token, biz_id)
        cash_id = create_cash_account(token, biz_id, balance="100000")

        exp_id = client.post(
            f"/api/v1/businesses/{biz_id}/expenses",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "category_id": cat_id,
                "cash_account_id": cash_id,
                "expense_date": datetime.now(timezone.utc).isoformat(),
                "amount": "300000",
                "currency": "IDR",
            },
        ).json()["id"]

        fin_res = client.post(
            f"/api/v1/businesses/{biz_id}/expenses/{exp_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fin_res.status_code == 400
        assert "Insufficient balance" in fin_res.json()["message"]

        # Expense remains DRAFT
        exp = client.get(
            f"/api/v1/businesses/{biz_id}/expenses/{exp_id}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        assert exp["status"] == "DRAFT"

    # 6. Double finalization rejected
    def test_double_finalization_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        cat_id = create_category(token, biz_id)
        cash_id = create_cash_account(token, biz_id, balance="1000000")

        exp_id = client.post(
            f"/api/v1/businesses/{biz_id}/expenses",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "category_id": cat_id,
                "cash_account_id": cash_id,
                "expense_date": datetime.now(timezone.utc).isoformat(),
                "amount": "100000",
            },
        ).json()["id"]

        client.post(
            f"/api/v1/businesses/{biz_id}/expenses/{exp_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Second finalization attempt
        fin2_res = client.post(
            f"/api/v1/businesses/{biz_id}/expenses/{exp_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fin2_res.status_code == 400

    # 7. Cancel Draft Expense
    def test_cancel_draft_expense(self):
        token, _ = register_user()
        biz_id = create_business(token)
        cat_id = create_category(token, biz_id)

        exp_id = client.post(
            f"/api/v1/businesses/{biz_id}/expenses",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "category_id": cat_id,
                "expense_date": datetime.now(timezone.utc).isoformat(),
                "amount": "50000",
            },
        ).json()["id"]

        canc_res = client.post(
            f"/api/v1/businesses/{biz_id}/expenses/{exp_id}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert canc_res.status_code == 200
        assert canc_res.json()["status"] == "CANCELLED"

    # 8. Archived Category rejected for new Expense
    def test_archived_category_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        cat_id = create_category(token, biz_id)

        # Archive category
        client.post(
            f"/api/v1/businesses/{biz_id}/expense-categories/{cat_id}/archive",
            headers={"Authorization": f"Bearer {token}"},
        )

        res = client.post(
            f"/api/v1/businesses/{biz_id}/expenses",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "category_id": cat_id,
                "expense_date": datetime.now(timezone.utc).isoformat(),
                "amount": "50000",
            },
        )
        assert res.status_code == 400
        assert "not ACTIVE" in res.json()["message"]

    # 9. Expense Summary
    def test_expense_summary(self):
        token, _ = register_user()
        biz_id = create_business(token)
        cat_id = create_category(token, biz_id)
        cash_id = create_cash_account(token, biz_id, balance="5000000")

        # Draft expense 100,000
        client.post(
            f"/api/v1/businesses/{biz_id}/expenses",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "category_id": cat_id,
                "cash_account_id": cash_id,
                "expense_date": datetime.now(timezone.utc).isoformat(),
                "amount": "100000",
            },
        )

        # Finalized expense 250,000
        exp2 = client.post(
            f"/api/v1/businesses/{biz_id}/expenses",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "category_id": cat_id,
                "cash_account_id": cash_id,
                "expense_date": datetime.now(timezone.utc).isoformat(),
                "amount": "250000",
            },
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/expenses/{exp2}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )

        sum_res = client.get(
            f"/api/v1/businesses/{biz_id}/expenses/summary",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert sum_res.status_code == 200
        data = sum_res.json()
        assert data["total_expense_amount"] == "250000"
        assert data["expense_count"] == 2
        assert data["finalized_count"] == 1
        assert data["draft_count"] == 1

    # 10. Cross-tenant isolation & IDOR
    def test_cross_tenant_isolation(self):
        token1, _ = register_user(email="user1@example.com")
        biz1 = create_business(token1, name="Biz 1")

        token2, _ = register_user(email="user2@example.com")
        biz2 = create_business(token2, name="Biz 2")
        cat2 = create_category(token2, biz2)

        exp2 = client.post(
            f"/api/v1/businesses/{biz2}/expenses",
            headers={"Authorization": f"Bearer {token2}"},
            json={
                "category_id": cat2,
                "expense_date": datetime.now(timezone.utc).isoformat(),
                "amount": "50000",
            },
        ).json()["id"]

        # User 1 attempts to read Biz 2 expense from Biz 1 context
        res = client.get(
            f"/api/v1/businesses/{biz1}/expenses/{exp2}",
            headers={"Authorization": f"Bearer {token1}"},
        )
        assert res.status_code == 404

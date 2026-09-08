import pytest
from decimal import Decimal
from fastapi.testclient import TestClient

from app.main import app
from app.modules.authentication.repository import InMemoryUserRepository
from app.modules.account.repository import InMemoryAccountRepository
from app.modules.business.repository import InMemoryBusinessRepository
from app.modules.business_membership.repository import InMemoryBusinessMembershipRepository
from app.modules.cash_account.repository import InMemoryCashAccountRepository

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_repositories():
    InMemoryCashAccountRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryUserRepository.clear()
    yield
    InMemoryCashAccountRepository.clear()
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


class TestCashAccountFeature:

    # 1. Unauthenticated access rejected
    def test_unauthenticated_access_rejected(self):
        res = client.get("/api/v1/businesses/biz123/cash-accounts")
        assert res.status_code == 401

    # 2. Create Cash Account (First becomes default)
    def test_create_cash_account_success(self):
        token, _ = register_user()
        biz_id = create_business(token)

        res = client.post(
            f"/api/v1/businesses/{biz_id}/cash-accounts",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Kas Utama",
                "code": "CASH-01",
                "account_type": "CASH",
                "currency": "IDR",
                "opening_balance": "500000",
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "Kas Utama"
        assert data["code"] == "CASH-01"
        assert data["account_type"] == "CASH"
        assert data["opening_balance"] == "500000"
        assert data["current_balance"] == "500000"
        assert data["status"] == "ACTIVE"
        assert data["is_default"] is True  # First account becomes default

    # 3. Duplicate code rejected within same business
    def test_duplicate_code_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)

        client.post(
            f"/api/v1/businesses/{biz_id}/cash-accounts",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Kas 1",
                "code": "CASH-01",
                "account_type": "CASH",
                "currency": "IDR",
            },
        )

        res = client.post(
            f"/api/v1/businesses/{biz_id}/cash-accounts",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Kas 2",
                "code": "CASH-01",
                "account_type": "CASH",
                "currency": "IDR",
            },
        )
        assert res.status_code == 400
        assert "already exists" in res.json()["message"]

    # 4. Cash In & Cash Out movements affect balance
    def test_cash_in_and_out_movements(self):
        token, _ = register_user()
        biz_id = create_business(token)

        acc_id = client.post(
            f"/api/v1/businesses/{biz_id}/cash-accounts",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Bank BCA",
                "code": "BCA-01",
                "account_type": "BANK",
                "currency": "IDR",
                "opening_balance": "1000000",
            },
        ).json()["id"]

        # CASH_IN 500,000
        in_res = client.post(
            f"/api/v1/businesses/{biz_id}/cash-accounts/{acc_id}/movements",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "movement_type": "CASH_IN",
                "amount": "500000",
                "direction": "IN",
                "description": "Setoran modal",
            },
        )
        assert in_res.status_code == 201

        # Check balance (1,000,000 + 500,000 = 1,500,000)
        acc = client.get(
            f"/api/v1/businesses/{biz_id}/cash-accounts/{acc_id}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        assert Decimal(str(acc["current_balance"])) == Decimal("1500000")

        # CASH_OUT 200,000
        out_res = client.post(
            f"/api/v1/businesses/{biz_id}/cash-accounts/{acc_id}/movements",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "movement_type": "CASH_OUT",
                "amount": "200000",
                "direction": "OUT",
                "description": "Biaya operasional",
            },
        )
        assert out_res.status_code == 201

        # Check balance (1,500,000 - 200,000 = 1,300,000)
        acc = client.get(
            f"/api/v1/businesses/{biz_id}/cash-accounts/{acc_id}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        assert Decimal(str(acc["current_balance"])) == Decimal("1300000")

    # 5. Overdraft / Insufficient balance prevention for CASH accounts
    def test_insufficient_balance_rejected_for_cash_account(self):
        token, _ = register_user()
        biz_id = create_business(token)

        acc_id = client.post(
            f"/api/v1/businesses/{biz_id}/cash-accounts",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Kas Kasir",
                "code": "KASIR-01",
                "account_type": "CASH",
                "currency": "IDR",
                "opening_balance": "100000",
            },
        ).json()["id"]

        # Attempt to withdraw 150,000 from 100,000 balance
        res = client.post(
            f"/api/v1/businesses/{biz_id}/cash-accounts/{acc_id}/movements",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "movement_type": "CASH_OUT",
                "amount": "150000",
                "direction": "OUT",
            },
        )
        assert res.status_code == 400
        assert "Insufficient balance" in res.json()["message"]

    # 6. Atomic Cash Transfer between accounts
    def test_atomic_cash_transfer(self):
        token, _ = register_user()
        biz_id = create_business(token)

        acc_bca = client.post(
            f"/api/v1/businesses/{biz_id}/cash-accounts",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Bank BCA",
                "code": "BCA-01",
                "account_type": "BANK",
                "currency": "IDR",
                "opening_balance": "1000000",
            },
        ).json()["id"]

        acc_kasir = client.post(
            f"/api/v1/businesses/{biz_id}/cash-accounts",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Kas Kasir",
                "code": "KAS-01",
                "account_type": "CASH",
                "currency": "IDR",
                "opening_balance": "100000",
            },
        ).json()["id"]

        # Transfer 300,000 from BCA to Kas Kasir
        trf_res = client.post(
            f"/api/v1/businesses/{biz_id}/cash-accounts/transfers",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "source_account_id": acc_bca,
                "destination_account_id": acc_kasir,
                "amount": "300000",
                "description": "Tarik tunai untuk operasional",
            },
        )
        assert trf_res.status_code == 201
        movements = trf_res.json()
        assert len(movements) == 2

        # Check BCA balance (1,000,000 - 300,000 = 700,000)
        bca_bal = client.get(
            f"/api/v1/businesses/{biz_id}/cash-accounts/{acc_bca}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()["current_balance"]
        assert Decimal(str(bca_bal)) == Decimal("700000")

        # Check Kasir balance (100,000 + 300,000 = 400,000)
        kas_bal = client.get(
            f"/api/v1/businesses/{biz_id}/cash-accounts/{acc_kasir}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()["current_balance"]
        assert Decimal(str(kas_bal)) == Decimal("400000")

    # 7. Self-transfer rejected
    def test_self_transfer_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)

        acc_id = client.post(
            f"/api/v1/businesses/{biz_id}/cash-accounts",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Bank BCA",
                "code": "BCA-01",
                "account_type": "BANK",
                "currency": "IDR",
                "opening_balance": "1000000",
            },
        ).json()["id"]

        res = client.post(
            f"/api/v1/businesses/{biz_id}/cash-accounts/transfers",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "source_account_id": acc_id,
                "destination_account_id": acc_id,
                "amount": "100000",
            },
        )
        assert res.status_code == 400
        assert "must be different" in res.json()["message"]

    # 8. Cross-currency transfer rejected
    def test_cross_currency_transfer_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)

        acc_idr = client.post(
            f"/api/v1/businesses/{biz_id}/cash-accounts",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Bank IDR",
                "code": "IDR-01",
                "account_type": "BANK",
                "currency": "IDR",
                "opening_balance": "1000000",
            },
        ).json()["id"]

        acc_usd = client.post(
            f"/api/v1/businesses/{biz_id}/cash-accounts",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Bank USD",
                "code": "USD-01",
                "account_type": "BANK",
                "currency": "USD",
                "opening_balance": "100",
            },
        ).json()["id"]

        res = client.post(
            f"/api/v1/businesses/{biz_id}/cash-accounts/transfers",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "source_account_id": acc_idr,
                "destination_account_id": acc_usd,
                "amount": "50000",
            },
        )
        assert res.status_code == 400
        assert "Cross-currency transfer is not supported" in res.json()["message"]

    # 9. Account Activation / Deactivation
    def test_account_lifecycle(self):
        token, _ = register_user()
        biz_id = create_business(token)

        acc1 = client.post(
            f"/api/v1/businesses/{biz_id}/cash-accounts",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Kas Utama",
                "code": "CASH-01",
                "account_type": "CASH",
                "currency": "IDR",
            },
        ).json()["id"]

        acc2 = client.post(
            f"/api/v1/businesses/{biz_id}/cash-accounts",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Kas Cadangan",
                "code": "CASH-02",
                "account_type": "CASH",
                "currency": "IDR",
            },
        ).json()["id"]

        # Deactivate acc2
        deact_res = client.post(
            f"/api/v1/businesses/{biz_id}/cash-accounts/{acc2}/deactivate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert deact_res.status_code == 200
        assert deact_res.json()["status"] == "INACTIVE"

        # Inactive account cannot receive movements
        mov_res = client.post(
            f"/api/v1/businesses/{biz_id}/cash-accounts/{acc2}/movements",
            headers={"Authorization": f"Bearer {token}"},
            json={"movement_type": "CASH_IN", "amount": "10000", "direction": "IN"},
        )
        assert mov_res.status_code == 400

        # Reactivate acc2
        act_res = client.post(
            f"/api/v1/businesses/{biz_id}/cash-accounts/{acc2}/activate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert act_res.status_code == 200
        assert act_res.json()["status"] == "ACTIVE"

    # 10. Cross-tenant access isolation & IDOR
    def test_cross_tenant_isolation(self):
        token1, _ = register_user(email="user1@example.com")
        biz1 = create_business(token1, name="Biz 1")

        token2, _ = register_user(email="user2@example.com")
        biz2 = create_business(token2, name="Biz 2")

        acc2 = client.post(
            f"/api/v1/businesses/{biz2}/cash-accounts",
            headers={"Authorization": f"Bearer {token2}"},
            json={
                "name": "Kas Biz 2",
                "code": "CASH-02",
                "account_type": "CASH",
                "currency": "IDR",
            },
        ).json()["id"]

        # User 1 attempts to access Biz 2 cash account in Biz 1 context
        res = client.get(
            f"/api/v1/businesses/{biz1}/cash-accounts/{acc2}",
            headers={"Authorization": f"Bearer {token1}"},
        )
        assert res.status_code == 404

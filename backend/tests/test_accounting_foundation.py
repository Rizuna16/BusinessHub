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


def create_branch(token, biz_id):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/branches",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Main Branch", "code": "MB"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def get_account_code(token, biz_id, code):
    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/accounts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    for acc in res.json()["items"]:
        if acc["code"] == code:
            return acc["id"]
    return None


class TestChartOfAccounts:
    def test_create_custom_account(self):
        token, _ = register_user()
        biz_id = create_business(token)

        res = client.post(
            f"/api/v1/businesses/{biz_id}/accounting/accounts",
            headers={"Authorization": f"Bearer {token}"},
            json={"code": "6100", "name": "Operational Expense", "account_type": "EXPENSE", "normal_balance": "DEBIT"},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["code"] == "6100"
        assert data["is_system"] is False
        assert data["is_active"] is True

    def test_duplicate_code_rejection(self):
        token, _ = register_user()
        biz_id = create_business(token)

        client.post(
            f"/api/v1/businesses/{biz_id}/accounting/accounts",
            headers={"Authorization": f"Bearer {token}"},
            json={"code": "6200", "name": "Duplicate", "account_type": "EXPENSE"},
        )

        res = client.post(
            f"/api/v1/businesses/{biz_id}/accounting/accounts",
            headers={"Authorization": f"Bearer {token}"},
            json={"code": "6200", "name": "Duplicate Again", "account_type": "EXPENSE"},
        )
        assert res.status_code == 400

    def test_archive_account(self):
        token, _ = register_user()
        biz_id = create_business(token)

        acc_res = client.post(
            f"/api/v1/businesses/{biz_id}/accounting/accounts",
            headers={"Authorization": f"Bearer {token}"},
            json={"code": "6300", "name": "Archive Me", "account_type": "EXPENSE"},
        )
        acc_id = acc_res.json()["id"]

        del_res = client.delete(
            f"/api/v1/businesses/{biz_id}/accounting/accounts/{acc_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert del_res.status_code == 200
        assert del_res.json()["is_active"] is False

    def test_system_account_protection(self):
        token, _ = register_user()
        biz_id = create_business(token)
        
        acc_id = get_account_code(token, biz_id, "1100")
        
        res = client.delete(
            f"/api/v1/businesses/{biz_id}/accounting/accounts/{acc_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 400
        assert "System accounts" in res.json()["message"]


class TestJournalEntry:
    def test_post_balanced_journal(self):
        token, _ = register_user()
        biz_id = create_business(token)

        cash_acc = get_account_code(token, biz_id, "1100")
        sales_acc = get_account_code(token, biz_id, "4100")

        res = client.post(
            f"/api/v1/businesses/{biz_id}/accounting/journals",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "journal_date": datetime.now(timezone.utc).isoformat(),
                "description": "Cash Sales",
                "lines": [
                    {"account_id": cash_acc, "debit": 1000, "credit": 0},
                    {"account_id": sales_acc, "debit": 0, "credit": 1000},
                ],
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "POSTED"
        assert data["journal_number"].startswith("JV-")
        assert Decimal(str(data["total_debit"])) == Decimal("1000")
        assert Decimal(str(data["total_credit"])) == Decimal("1000")
        assert len(data["lines"]) == 2

    def test_reject_unbalanced_journal(self):
        token, _ = register_user()
        biz_id = create_business(token)

        cash_acc = get_account_code(token, biz_id, "1100")
        sales_acc = get_account_code(token, biz_id, "4100")

        res = client.post(
            f"/api/v1/businesses/{biz_id}/accounting/journals",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "journal_date": datetime.now(timezone.utc).isoformat(),
                "description": "Unbalanced Sales",
                "lines": [
                    {"account_id": cash_acc, "debit": 1000, "credit": 0},
                    {"account_id": sales_acc, "debit": 0, "credit": 900},
                ],
            },
        )
        assert res.status_code == 400
        assert "Unbalanced journal entry" in res.json()["message"]

    def test_reject_debit_credit_same_line(self):
        token, _ = register_user()
        biz_id = create_business(token)
        cash_acc = get_account_code(token, biz_id, "1100")

        res = client.post(
            f"/api/v1/businesses/{biz_id}/accounting/journals",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "journal_date": datetime.now(timezone.utc).isoformat(),
                "description": "Invalid Line",
                "lines": [
                    {"account_id": cash_acc, "debit": 1000, "credit": 1000},
                    {"account_id": cash_acc, "debit": 0, "credit": 1000},
                ],
            },
        )
        assert res.status_code == 400

    def test_void_journal(self):
        token, _ = register_user()
        biz_id = create_business(token)

        cash_acc = get_account_code(token, biz_id, "1100")
        sales_acc = get_account_code(token, biz_id, "4100")

        j_res = client.post(
            f"/api/v1/businesses/{biz_id}/accounting/journals",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "journal_date": datetime.now(timezone.utc).isoformat(),
                "description": "To Void",
                "lines": [
                    {"account_id": cash_acc, "debit": 1000, "credit": 0},
                    {"account_id": sales_acc, "debit": 0, "credit": 1000},
                ],
            },
        )
        j_id = j_res.json()["id"]

        void_res = client.post(
            f"/api/v1/businesses/{biz_id}/accounting/journals/{j_id}/void",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert void_res.status_code == 200
        assert void_res.json()["status"] == "VOIDED"

    def test_idempotency_key(self):
        token, _ = register_user()
        biz_id = create_business(token)
        cash_acc = get_account_code(token, biz_id, "1100")
        sales_acc = get_account_code(token, biz_id, "4100")

        payload = {
            "journal_date": datetime.now(timezone.utc).isoformat(),
            "description": "Idempotent Test",
            "idempotency_key": "UNIQUE-IDEM-001",
            "lines": [
                {"account_id": cash_acc, "debit": 500, "credit": 0},
                {"account_id": sales_acc, "debit": 0, "credit": 500},
            ],
        }

        j1 = client.post(
            f"/api/v1/businesses/{biz_id}/accounting/journals",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        ).json()

        j2 = client.post(
            f"/api/v1/businesses/{biz_id}/accounting/journals",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        ).json()

        assert j1["id"] == j2["id"]

    def test_tenant_isolation(self):
        t1, _ = register_user("a@test.com")
        biz1 = create_business(t1)
        
        t2, _ = register_user("b@test.com")
        biz2 = create_business(t2)

        c1 = get_account_code(t1, biz1, "1100")
        c2 = get_account_code(t2, biz2, "1100")

        j_res = client.post(
            f"/api/v1/businesses/{biz1}/accounting/journals",
            headers={"Authorization": f"Bearer {t1}"},
            json={
                "journal_date": datetime.now(timezone.utc).isoformat(),
                "description": "Biz 1 Journal",
                "lines": [
                    {"account_id": c1, "debit": 100, "credit": 0},
                    {"account_id": get_account_code(t1, biz1, "4100"), "debit": 0, "credit": 100},
                ],
            },
        )
        j_id = j_res.json()["id"]

        # Biz 2 accessing Biz 1 journals -> 404
        get_b2 = client.get(
            f"/api/v1/businesses/{biz2}/accounting/journals/{j_id}",
            headers={"Authorization": f"Bearer {t2}"},
        )
        assert get_b2.status_code == 404

        # Biz 2 accessing Biz 1 accounts -> 404
        get_acc_b2 = client.get(
            f"/api/v1/businesses/{biz2}/accounting/accounts/{c1}",
            headers={"Authorization": f"Bearer {t2}"},
        )
        assert get_acc_b2.status_code == 404

    def test_member_cannot_post_journal(self):
        t_owner, _ = register_user()
        biz_id = create_business(t_owner)

        t_member, mem_id = register_user("mem@test.com")
        client.post(
            f"/api/v1/businesses/{biz_id}/members",
            headers={"Authorization": f"Bearer {t_owner}"},
            json={"user_id": mem_id, "role": "MEMBER"},
        )

        # Member cannot access or create journals
        list_j = client.get(
            f"/api/v1/businesses/{biz_id}/accounting/journals",
            headers={"Authorization": f"Bearer {t_member}"},
        )
        assert list_j.status_code == 200  # Read is allowed based on implementation details

        c1 = get_account_code(t_owner, biz_id, "1100")
        c2 = get_account_code(t_owner, biz_id, "4100")

        # Actually, AccountingService creation requires OWNER/ADMIN
        post_j = client.post(
            f"/api/v1/businesses/{biz_id}/accounting/journals",
            headers={"Authorization": f"Bearer {t_member}"},
            json={
                "journal_date": datetime.now(timezone.utc).isoformat(),
                "description": "Member Posting",
                "lines": [
                    {"account_id": c1, "debit": 100, "credit": 0},
                    {"account_id": c2, "debit": 0, "credit": 100},
                ],
            },
        )
        assert post_j.status_code == 403


class TestLedgerAndBalance:
    def test_account_balance_calculation(self):
        token, _ = register_user()
        biz_id = create_business(token)
        cash_acc = get_account_code(token, biz_id, "1100")
        sales_acc = get_account_code(token, biz_id, "4100")

        # Post a journal 1000
        client.post(
            f"/api/v1/businesses/{biz_id}/accounting/journals",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "journal_date": datetime.now(timezone.utc).isoformat(),
                "description": "Sale",
                "lines": [
                    {"account_id": cash_acc, "debit": 1000, "credit": 0},
                    {"account_id": sales_acc, "debit": 0, "credit": 1000},
                ],
            },
        )

        ledger = client.get(
            f"/api/v1/businesses/{biz_id}/accounting/ledger/{cash_acc}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()

        assert Decimal(str(ledger["ending_balance"])) == Decimal("1000")
        assert Decimal(str(ledger["total_debit"])) == Decimal("1000")

        tb = client.get(
            f"/api/v1/businesses/{biz_id}/accounting/trial-balance",
            headers={"Authorization": f"Bearer {token}"},
        ).json()

        assert tb["is_balanced"] is True
        assert Decimal(str(tb["total_debit"])) == Decimal("1000")
        assert Decimal(str(tb["total_credit"])) == Decimal("1000")

    def test_void_journal_removes_from_balance(self):
        token, _ = register_user()
        biz_id = create_business(token)
        cash_acc = get_account_code(token, biz_id, "1100")
        sales_acc = get_account_code(token, biz_id, "4100")

        j_res = client.post(
            f"/api/v1/businesses/{biz_id}/accounting/journals",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "journal_date": datetime.now(timezone.utc).isoformat(),
                "description": "To Void",
                "lines": [
                    {"account_id": cash_acc, "debit": 1000, "credit": 0},
                    {"account_id": sales_acc, "debit": 0, "credit": 1000},
                ],
            },
        ).json()

        client.post(
            f"/api/v1/businesses/{biz_id}/accounting/journals/{j_res['id']}/void",
            headers={"Authorization": f"Bearer {token}"},
        )

        ledger = client.get(
            f"/api/v1/businesses/{biz_id}/accounting/ledger/{cash_acc}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()

        assert Decimal(str(ledger["ending_balance"])) == Decimal("0")

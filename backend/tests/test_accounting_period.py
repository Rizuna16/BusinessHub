"""
Feature #35 — Fiscal Period Management — Comprehensive Test Suite
"""
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from datetime import datetime, timezone, date

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
    """Add the user behind member_token to the business as MEMBER."""
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


def create_accounting_period(token, biz_id, period_name, start_date, end_date):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/accounting/periods",
        headers={"Authorization": f"Bearer {token}"},
        json={"period_name": period_name, "start_date": start_date, "end_date": end_date},
    )
    return res


def close_accounting_period(token, biz_id, period_id):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/accounting/periods/{period_id}/close",
        headers={"Authorization": f"Bearer {token}"},
    )
    return res


def list_periods(token, biz_id):
    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/periods",
        headers={"Authorization": f"Bearer {token}"},
    )
    return res


def get_period(token, biz_id, period_id):
    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/periods/{period_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    return res


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


def create_branch(token, biz_id):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/branches",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Main Branch", "code": "MB"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def post_journal(token, biz_id, journal_date, description, lines, branch_id=None, idempotency_key=None):
    payload = {
        "journal_date": journal_date,
        "description": description,
        "lines": lines,
    }
    if branch_id:
        payload["branch_id"] = branch_id
    if idempotency_key:
        payload["idempotency_key"] = idempotency_key
    res = client.post(
        f"/api/v1/businesses/{biz_id}/accounting/journals",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    return res


# ═══════════════════════════════════════════════════
# A. PERIOD CREATE
# ═══════════════════════════════════════════════════

class TestPeriodCreate:
    def test_owner_can_create_period(self):
        token, _ = register_user()
        biz_id = create_business(token)

        res = create_accounting_period(token, biz_id, "2026-01", "2026-01-01", "2026-01-31")
        assert res.status_code == 201
        data = res.json()
        assert data["period_name"] == "2026-01"
        assert data["start_date"] == "2026-01-01"
        assert data["end_date"] == "2026-01-31"
        assert data["status"] == "OPEN"
        assert data["business_id"] == biz_id

    def test_admin_can_create_period(self):
        owner_token, _ = register_user("owner@test.com")
        biz_id = create_business(owner_token)

        admin_token, admin_id = register_user("admin@test.com", "Admin User")
        res = client.post(
            f"/api/v1/businesses/{biz_id}/members",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"user_id": admin_id, "role": "ADMIN"},
        )
        assert res.status_code == 201

        res = create_accounting_period(admin_token, biz_id, "2026-01", "2026-01-01", "2026-01-31")
        assert res.status_code == 201
        assert res.json()["status"] == "OPEN"

    def test_member_cannot_create_period(self):
        owner_token, _ = register_user("owner@test.com")
        biz_id = create_business(owner_token)

        member_token, _ = register_user("member@test.com", "Member User")
        add_member(owner_token, biz_id, member_token)

        res = create_accounting_period(member_token, biz_id, "2026-01", "2026-01-01", "2026-01-31")
        assert res.status_code == 403

    def test_duplicate_period_name_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)

        res1 = create_accounting_period(token, biz_id, "2026-01", "2026-01-01", "2026-01-31")
        assert res1.status_code == 201

        res2 = create_accounting_period(token, biz_id, "2026-01", "2026-02-01", "2026-02-28")
        assert res2.status_code == 400
        assert "already exists" in res2.json()["message"]

    def test_overlapping_period_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)

        res1 = create_accounting_period(token, biz_id, "2026-01", "2026-01-01", "2026-01-31")
        assert res1.status_code == 201

        res2 = create_accounting_period(token, biz_id, "2026-01B", "2026-01-15", "2026-02-15")
        assert res2.status_code == 400
        assert "overlaps" in res2.json()["message"].lower()

    def test_different_businesses_can_use_same_period(self):
        t1, _ = register_user("b1@test.com")
        t2, _ = register_user("b2@test.com")
        biz1 = create_business(t1)
        biz2 = create_business(t2)

        res1 = create_accounting_period(t1, biz1, "2026-01", "2026-01-01", "2026-01-31")
        assert res1.status_code == 201

        res2 = create_accounting_period(t2, biz2, "2026-01", "2026-01-01", "2026-01-31")
        assert res2.status_code == 201

    def test_invalid_date_range_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)

        res = create_accounting_period(token, biz_id, "2026-01", "2026-01-31", "2026-01-01")
        assert res.status_code == 422

    def test_unauthenticated_create_rejected(self):
        res = client.post(
            "/api/v1/businesses/biz-123/accounting/periods",
            json={"period_name": "2026-01", "start_date": "2026-01-01", "end_date": "2026-01-31"},
        )
        assert res.status_code == 401


# ═══════════════════════════════════════════════════
# B. PERIOD READ
# ═══════════════════════════════════════════════════

class TestPeriodRead:
    def test_list_periods(self):
        token, _ = register_user()
        biz_id = create_business(token)
        create_accounting_period(token, biz_id, "2026-01", "2026-01-01", "2026-01-31")
        create_accounting_period(token, biz_id, "2026-02", "2026-02-01", "2026-02-28")

        res = list_periods(token, biz_id)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 2
        # Most recent first (sorted by start_date desc)
        assert data["items"][0]["period_name"] == "2026-02"

    def test_get_period_detail(self):
        token, _ = register_user()
        biz_id = create_business(token)
        create_res = create_accounting_period(token, biz_id, "2026-01", "2026-01-01", "2026-01-31")
        period_id = create_res.json()["id"]

        res = get_period(token, biz_id, period_id)
        assert res.status_code == 200
        assert res.json()["period_name"] == "2026-01"

    def test_missing_period_returns_404(self):
        token, _ = register_user()
        biz_id = create_business(token)

        res = get_period(token, biz_id, "nonexistent-id")
        assert res.status_code == 404

    def test_cross_business_access_denied(self):
        t1, _ = register_user("a@test.com")
        t2, _ = register_user("b@test.com")
        biz1 = create_business(t1)
        biz2 = create_business(t2)

        create_res = create_accounting_period(t1, biz1, "2026-01", "2026-01-01", "2026-01-31")
        period_id = create_res.json()["id"]

        res = get_period(t2, biz2, period_id)
        assert res.status_code == 404

    def test_member_can_list_periods(self):
        owner_token, _ = register_user()
        biz_id = create_business(owner_token)
        create_accounting_period(owner_token, biz_id, "2026-01", "2026-01-01", "2026-01-31")

        member_token, _ = register_user("member@test.com", "Member User")
        add_member(owner_token, biz_id, member_token)

        res = list_periods(member_token, biz_id)
        assert res.status_code == 200
        assert res.json()["total"] == 1

    def test_unauthenticated_read_rejected(self):
        res = client.get("/api/v1/businesses/biz-123/accounting/periods")
        assert res.status_code == 401


# ═══════════════════════════════════════════════════
# C. PERIOD CLOSE
# ═══════════════════════════════════════════════════

class TestPeriodClose:
    def test_owner_can_close(self):
        token, _ = register_user()
        biz_id = create_business(token)
        create_res = create_accounting_period(token, biz_id, "2026-01", "2026-01-01", "2026-01-31")
        period_id = create_res.json()["id"]

        res = close_accounting_period(token, biz_id, period_id)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "CLOSED"
        assert data["closed_at"] is not None
        assert data["closed_by_user_id"] is not None

    def test_admin_can_close(self):
        owner_token, _ = register_user()
        biz_id = create_business(owner_token)
        create_res = create_accounting_period(owner_token, biz_id, "2026-01", "2026-01-01", "2026-01-31")
        period_id = create_res.json()["id"]

        admin_token, admin_id = register_user("admin@test.com", "Admin User")
        res = client.post(
            f"/api/v1/businesses/{biz_id}/members",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"user_id": admin_id, "role": "ADMIN"},
        )
        assert res.status_code == 201

        close_res = close_accounting_period(admin_token, biz_id, period_id)
        assert close_res.status_code == 200
        assert close_res.json()["status"] == "CLOSED"

    def test_member_cannot_close(self):
        owner_token, _ = register_user()
        biz_id = create_business(owner_token)
        create_res = create_accounting_period(owner_token, biz_id, "2026-01", "2026-01-01", "2026-01-31")
        period_id = create_res.json()["id"]

        member_token, _ = register_user("member@test.com", "Member User")
        add_member(owner_token, biz_id, member_token)

        res = close_accounting_period(member_token, biz_id, period_id)
        assert res.status_code == 403

    def test_already_closed_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        create_res = create_accounting_period(token, biz_id, "2026-01", "2026-01-01", "2026-01-31")
        period_id = create_res.json()["id"]

        res1 = close_accounting_period(token, biz_id, period_id)
        assert res1.status_code == 200

        res2 = close_accounting_period(token, biz_id, period_id)
        assert res2.status_code == 400
        assert "already CLOSED" in res2.json()["message"]

    def test_close_nonexistent_period(self):
        token, _ = register_user()
        biz_id = create_business(token)

        res = close_accounting_period(token, biz_id, "nonexistent-id")
        assert res.status_code == 404


# ═══════════════════════════════════════════════════
# D. JOURNAL POSTING PERIOD GUARD
# ═══════════════════════════════════════════════════

class TestPeriodGuard:
    def test_posting_in_open_period_succeeds(self):
        token, _ = register_user()
        biz_id = create_business(token)
        create_accounting_period(token, biz_id, "2026-01", "2026-01-01", "2026-01-31")

        cash_acc = get_account_id(token, biz_id, "1100")
        sales_acc = get_account_id(token, biz_id, "4100")

        res = post_journal(
            token, biz_id,
            journal_date="2026-01-15T00:00:00Z",
            description="Sale in open period",
            lines=[
                {"account_id": cash_acc, "debit": "1000", "credit": "0"},
                {"account_id": sales_acc, "debit": "0", "credit": "1000"},
            ],
        )
        assert res.status_code == 201
        assert res.json()["status"] == "POSTED"

    def test_posting_in_closed_period_fails(self):
        token, _ = register_user()
        biz_id = create_business(token)
        create_res = create_accounting_period(token, biz_id, "2026-01", "2026-01-01", "2026-01-31")
        close_accounting_period(token, biz_id, create_res.json()["id"])

        cash_acc = get_account_id(token, biz_id, "1100")
        sales_acc = get_account_id(token, biz_id, "4100")

        res = post_journal(
            token, biz_id,
            journal_date="2026-01-15T00:00:00Z",
            description="Sale in closed period",
            lines=[
                {"account_id": cash_acc, "debit": "1000", "credit": "0"},
                {"account_id": sales_acc, "debit": "0", "credit": "1000"},
            ],
        )
        assert res.status_code == 400
        assert "CLOSED" in res.json()["message"]

    def test_posting_outside_any_period_allowed(self):
        token, _ = register_user()
        biz_id = create_business(token)
        create_accounting_period(token, biz_id, "2026-01", "2026-01-01", "2026-01-31")

        cash_acc = get_account_id(token, biz_id, "1100")
        sales_acc = get_account_id(token, biz_id, "4100")

        # Date outside any period
        res = post_journal(
            token, biz_id,
            journal_date="2025-12-31T00:00:00Z",
            description="Before any period",
            lines=[
                {"account_id": cash_acc, "debit": "500", "credit": "0"},
                {"account_id": sales_acc, "debit": "0", "credit": "500"},
            ],
        )
        assert res.status_code == 201

    def test_exact_start_date_accepted(self):
        token, _ = register_user()
        biz_id = create_business(token)
        create_accounting_period(token, biz_id, "2026-01", "2026-01-01", "2026-01-31")

        cash_acc = get_account_id(token, biz_id, "1100")
        sales_acc = get_account_id(token, biz_id, "4100")

        res = post_journal(
            token, biz_id,
            journal_date="2026-01-01T00:00:00Z",
            description="Exact start date",
            lines=[
                {"account_id": cash_acc, "debit": "100", "credit": "0"},
                {"account_id": sales_acc, "debit": "0", "credit": "100"},
            ],
        )
        assert res.status_code == 201

    def test_exact_end_date_accepted(self):
        token, _ = register_user()
        biz_id = create_business(token)
        create_accounting_period(token, biz_id, "2026-01", "2026-01-01", "2026-01-31")

        cash_acc = get_account_id(token, biz_id, "1100")
        sales_acc = get_account_id(token, biz_id, "4100")

        res = post_journal(
            token, biz_id,
            journal_date="2026-01-31T23:59:59Z",
            description="Exact end date",
            lines=[
                {"account_id": cash_acc, "debit": "200", "credit": "0"},
                {"account_id": sales_acc, "debit": "0", "credit": "200"},
            ],
        )
        assert res.status_code == 201


# ═══════════════════════════════════════════════════
# E. SECURITY / TENANCY
# ═══════════════════════════════════════════════════

class TestSecurity:
    def test_cross_business_period_close(self):
        t1, _ = register_user("a@test.com")
        t2, _ = register_user("b@test.com")
        biz1 = create_business(t1)
        biz2 = create_business(t2)

        create_res = create_accounting_period(t1, biz1, "2026-01", "2026-01-01", "2026-01-31")
        period_id = create_res.json()["id"]

        # Biz2 owner tries to close biz1's period
        res = close_accounting_period(t2, biz2, period_id)
        assert res.status_code == 404

    def test_unauthenticated_period_operations(self):
        res1 = client.post("/api/v1/businesses/biz-123/accounting/periods", json={"period_name": "2026-01", "start_date": "2026-01-01", "end_date": "2026-01-31"})
        assert res1.status_code == 401
        res2 = client.get("/api/v1/businesses/biz-123/accounting/periods")
        assert res2.status_code == 401
        res3 = client.post("/api/v1/businesses/biz-123/accounting/periods/some-id/close")
        assert res3.status_code == 401

    def test_empty_business_id_rejected(self):
        token, _ = register_user()
        res = client.get(
            "/api/v1/businesses//accounting/periods",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 404


# ═══════════════════════════════════════════════════
# F. INTEGRATION TEST
# ═══════════════════════════════════════════════════

class TestPeriodIntegration:
    def test_full_lifecycle(self):
        """
        Create period → post journal in OPEN period → close period → post in CLOSED period → rejected.
        This test proves the dead-code guard is now functional.
        """
        token, _ = register_user()
        biz_id = create_business(token)

        cash_acc = get_account_id(token, biz_id, "1100")
        sales_acc = get_account_id(token, biz_id, "4100")

        # 1. No period exists → posting should be allowed (backward compatible)
        res = post_journal(
            token, biz_id,
            journal_date="2025-06-01T00:00:00Z",
            description="Before any period exists",
            lines=[
                {"account_id": cash_acc, "debit": "100", "credit": "0"},
                {"account_id": sales_acc, "debit": "0", "credit": "100"},
            ],
        )
        assert res.status_code == 201

        # 2. Create OPEN period
        create_res = create_accounting_period(token, biz_id, "2026-01", "2026-01-01", "2026-01-31")
        assert create_res.status_code == 201
        period_id = create_res.json()["id"]
        assert create_res.json()["status"] == "OPEN"

        # 3. Post journal inside OPEN period → succeeds
        res = post_journal(
            token, biz_id,
            journal_date="2026-01-15T00:00:00Z",
            description="Inside OPEN period",
            lines=[
                {"account_id": cash_acc, "debit": "500", "credit": "0"},
                {"account_id": sales_acc, "debit": "0", "credit": "500"},
            ],
        )
        assert res.status_code == 201
        assert res.json()["status"] == "POSTED"

        # 4. Close period
        close_res = close_accounting_period(token, biz_id, period_id)
        assert close_res.status_code == 200
        assert close_res.json()["status"] == "CLOSED"

        # 5. Post journal inside CLOSED period → rejected
        res = post_journal(
            token, biz_id,
            journal_date="2026-01-20T00:00:00Z",
            description="Inside CLOSED period - should fail",
            lines=[
                {"account_id": cash_acc, "debit": "700", "credit": "0"},
                {"account_id": sales_acc, "debit": "0", "credit": "700"},
            ],
        )
        assert res.status_code == 400
        assert "CLOSED" in res.json()["message"]

        # 6. Post journal outside period → still allowed
        res = post_journal(
            token, biz_id,
            journal_date="2026-03-01T00:00:00Z",
            description="After the closed period",
            lines=[
                {"account_id": cash_acc, "debit": "300", "credit": "0"},
                {"account_id": sales_acc, "debit": "0", "credit": "300"},
            ],
        )
        assert res.status_code == 201

        # 7. Verify total journals created: 3
        journals_res = client.get(
            f"/api/v1/businesses/{biz_id}/accounting/journals",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert journals_res.status_code == 200
        assert journals_res.json()["total"] == 3

    def test_cross_business_isolation(self):
        """Ensure period in Business A has no effect on Business B."""
        t1, _ = register_user("a@test.com")
        t2, _ = register_user("b@test.com")
        biz1 = create_business(t1)
        biz2 = create_business(t2)

        # Create and close period in biz1
        create_res = create_accounting_period(t1, biz1, "2026-01", "2026-01-01", "2026-01-31")
        close_accounting_period(t1, biz1, create_res.json()["id"])

        cash1 = get_account_id(t1, biz1, "1100")
        sales1 = get_account_id(t1, biz1, "4100")
        cash2 = get_account_id(t2, biz2, "1100")
        sales2 = get_account_id(t2, biz2, "4100")

        # Posting to biz1 on closed date → fails
        res1 = post_journal(
            t1, biz1,
            journal_date="2026-01-15T00:00:00Z",
            description="Biz1 in closed",
            lines=[
                {"account_id": cash1, "debit": "1000", "credit": "0"},
                {"account_id": sales1, "debit": "0", "credit": "1000"},
            ],
        )
        assert res1.status_code == 400

        # Posting to biz2 on same date → succeeds (no period in biz2)
        res2 = post_journal(
            t2, biz2,
            journal_date="2026-01-15T00:00:00Z",
            description="Biz2 in same date - no restriction",
            lines=[
                {"account_id": cash2, "debit": "1000", "credit": "0"},
                {"account_id": sales2, "debit": "0", "credit": "1000"},
            ],
        )
        assert res2.status_code == 201

"""
Feature #51 — Cashier Shift Management Test Suite
"""
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.modules.authentication.repository import InMemoryUserRepository
from app.modules.account.repository import InMemoryAccountRepository
from app.modules.business.repository import InMemoryBusinessRepository
from app.modules.business_membership.repository import InMemoryBusinessMembershipRepository
from app.modules.accounting.repository import InMemoryAccountingRepository
from app.modules.payment.repository import InMemoryPaymentRepository
from app.modules.expense.repository import InMemoryExpenseRepository
from app.modules.cash_account.repository import InMemoryCashAccountRepository
from app.modules.cashier_shift.repository import InMemoryCashierShiftRepository
from app.modules.cash_account.schemas import CashAccountType
from app.modules.payment.schemas import PaymentDirection, PaymentTargetType, PaymentMethod

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_repositories():
    InMemoryAccountingRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryUserRepository.clear()
    InMemoryPaymentRepository.clear()
    InMemoryExpenseRepository.clear()
    InMemoryCashAccountRepository.clear()
    InMemoryCashierShiftRepository.clear()
    yield
    InMemoryAccountingRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryUserRepository.clear()
    InMemoryPaymentRepository.clear()
    InMemoryExpenseRepository.clear()
    InMemoryCashAccountRepository.clear()
    InMemoryCashierShiftRepository.clear()


_user_counter = 0


def register_user(email=None, name="Test User"):
    global _user_counter
    _user_counter += 1
    if not email:
        email = f"user{_user_counter}@example.com"
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


def create_branch(token, business_id, name="Main Branch"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/branches",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": name.upper().replace(" ", "-"), "timezone": "UTC", "locale": "en-US"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_cash_account(token, business_id, name="Cash Register", account_type="CASH"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/cash-accounts",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": name.upper().replace(" ", "-"), "account_type": account_type, "currency": "IDR", "opening_balance": 0},
    )
    assert res.status_code == 201
    return res.json()["id"]


def open_shift(token, business_id, branch_id, cash_account_id, opening_balance="1000000"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/shifts",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "cash_account_id": cash_account_id, "opening_balance": opening_balance},
    )
    return res


def create_sale_with_product(token, business_id, branch_id):
    """Helper to create a finalized sale ready for payment."""
    # Create customer
    cust_res = client.post(
        f"/api/v1/businesses/{business_id}/customers",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Walk-in Customer"},
    )
    assert cust_res.status_code == 201
    customer_id = cust_res.json()["id"]

    # Create product
    unit_res = client.post(
        f"/api/v1/businesses/{business_id}/units",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Piece", "code": "PCS"},
    )
    prod_res = client.post(
        f"/api/v1/businesses/{business_id}/products",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Test Product", "code": f"TP{_user_counter}", "unit_id": unit_res.json()["id"], "product_type": "SERVICE"},
    )
    product_id = prod_res.json()["id"]

    # Create sale
    sale_res = client.post(
        f"/api/v1/businesses/{business_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "customer_id": customer_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    )
    assert sale_res.status_code == 201
    sale_id = sale_res.json()["id"]

    # Add line
    line_res = client.post(
        f"/api/v1/businesses/{business_id}/sales/{sale_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": product_id, "quantity": 1, "unit_price": 50000},
    )
    assert line_res.status_code == 201

    # Finalize
    finalize_res = client.post(
        f"/api/v1/businesses/{business_id}/sales/{sale_id}/finalize",
        headers={"Authorization": f"Bearer {token}"},
        json={},
    )
    assert finalize_res.status_code == 200

    return sale_id


# ═══════════════════════════════════════════════════
# DOMAIN TESTS
# ═══════════════════════════════════════════════════

class TestShiftDomain:
    def test_open_shift_success(self):
        token, uid = register_user()
        biz_id = create_business(token)
        branch_id = create_branch(token, biz_id)
        cash_id = create_cash_account(token, biz_id)

        res = open_shift(token, biz_id, branch_id, cash_id, "500000")
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "OPEN"
        assert float(data["opening_balance"]) == 500000.0
        assert data["cash_account_id"] == cash_id
        assert data["cashier_user_id"] == uid

    def test_open_shift_zero_opening(self):
        token, _ = register_user()
        biz_id = create_business(token)
        branch_id = create_branch(token, biz_id)
        cash_id = create_cash_account(token, biz_id)

        res = open_shift(token, biz_id, branch_id, cash_id, "0")
        assert res.status_code == 201
        assert float(res.json()["opening_balance"]) == 0

    def test_open_shift_non_cash_account_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        branch_id = create_branch(token, biz_id)
        bank_id = create_cash_account(token, biz_id, "Bank Account", "BANK")

        res = open_shift(token, biz_id, branch_id, bank_id)
        assert res.status_code == 400

    def test_open_shift_missing_branch_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        cash_id = create_cash_account(token, biz_id)

        res = open_shift(token, biz_id, "nonexistent-branch", cash_id)
        assert res.status_code == 400

    def test_open_shift_wrong_business_rejected(self):
        token1, _ = register_user()
        token2, _ = register_user()
        biz_id = create_business(token1)
        branch_id = create_branch(token1, biz_id)
        cash_id = create_cash_account(token1, biz_id)

        res = open_shift(token2, biz_id, branch_id, cash_id)
        assert res.status_code in [403, 404]

    def test_open_shift_requires_auth(self):
        res = client.post(
            "/api/v1/businesses/biz-id/shifts",
            json={"branch_id": "x", "cash_account_id": "y", "opening_balance": 0},
        )
        assert res.status_code == 401


# ═══════════════════════════════════════════════════
# UNIQUENESS TESTS
# ═══════════════════════════════════════════════════

class TestShiftUniqueness:
    def test_second_open_same_account_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        branch_id = create_branch(token, biz_id)
        cash_id = create_cash_account(token, biz_id)

        res1 = open_shift(token, biz_id, branch_id, cash_id)
        assert res1.status_code == 201

        res2 = open_shift(token, biz_id, branch_id, cash_id)
        assert res2.status_code == 409

    def test_open_after_close_succeeds(self):
        token, _ = register_user()
        biz_id = create_business(token)
        branch_id = create_branch(token, biz_id)
        cash_id = create_cash_account(token, biz_id)

        res1 = open_shift(token, biz_id, branch_id, cash_id)
        shift_id = res1.json()["id"]

        close_res = client.patch(
            f"/api/v1/businesses/{biz_id}/shifts/{shift_id}/close",
            headers={"Authorization": f"Bearer {token}"},
            json={"actual_cash_count": 1000000},
        )
        assert close_res.status_code == 200

        res2 = open_shift(token, biz_id, branch_id, cash_id)
        assert res2.status_code == 201

    def test_different_cash_account_succeeds(self):
        token, _ = register_user()
        biz_id = create_business(token)
        branch_id = create_branch(token, biz_id)
        cash_id1 = create_cash_account(token, biz_id, "Drawer 1")
        cash_id2 = create_cash_account(token, biz_id, "Drawer 2")

        res1 = open_shift(token, biz_id, branch_id, cash_id1)
        assert res1.status_code == 201

        res2 = open_shift(token, biz_id, branch_id, cash_id2)
        assert res2.status_code == 201

    def test_same_account_different_business_succeeds(self):
        token1, _ = register_user()
        token2, _ = register_user()
        biz1 = create_business(token1, "Biz 1")
        biz2 = create_business(token2, "Biz 2")

        branch1 = create_branch(token1, biz1, "Branch A")
        branch2 = create_branch(token2, biz2, "Branch B")

        cash1_id = create_cash_account(token1, biz1, "Cash A")
        cash2_id = create_cash_account(token2, biz2, "Cash B")

        res1 = open_shift(token1, biz1, branch1, cash1_id)
        assert res1.status_code == 201

        res2 = open_shift(token2, biz2, branch2, cash2_id)
        assert res2.status_code == 201


# ═══════════════════════════════════════════════════
# OWNERSHIP TESTS
# ═══════════════════════════════════════════════════

class TestShiftOwnership:
    def test_member_can_open_own_shift(self):
        owner_token, _ = register_user()
        biz_id = create_business(owner_token)
        branch_id = create_branch(owner_token, biz_id)

        member_token, member_id = register_user()
        client.post(
            f"/api/v1/businesses/{biz_id}/members",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"user_id": member_id, "role": "MEMBER"},
        )

        cash_id = create_cash_account(owner_token, biz_id, "Member Cash")
        res = open_shift(member_token, biz_id, branch_id, cash_id)
        assert res.status_code == 201

    def test_member_can_view_own_shift(self):
        owner_token, _ = register_user()
        biz_id = create_business(owner_token)
        branch_id = create_branch(owner_token, biz_id)

        member_token, member_id = register_user()
        client.post(
            f"/api/v1/businesses/{biz_id}/members",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"user_id": member_id, "role": "MEMBER"},
        )

        cash_id = create_cash_account(owner_token, biz_id, "Member Cash")
        open_res = open_shift(member_token, biz_id, branch_id, cash_id)
        shift_id = open_res.json()["id"]

        get_res = client.get(
            f"/api/v1/businesses/{biz_id}/shifts/{shift_id}",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert get_res.status_code == 200

    def test_member_cannot_view_other_shift(self):
        owner_token, _ = register_user()
        biz_id = create_business(owner_token)
        branch_id = create_branch(owner_token, biz_id)

        member_token, member_id = register_user()
        client.post(
            f"/api/v1/businesses/{biz_id}/members",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"user_id": member_id, "role": "MEMBER"},
        )

        cash_id = create_cash_account(owner_token, biz_id)
        open_res = open_shift(owner_token, biz_id, branch_id, cash_id)
        shift_id = open_res.json()["id"]

        get_res = client.get(
            f"/api/v1/businesses/{biz_id}/shifts/{shift_id}",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert get_res.status_code == 403

    def test_member_cannot_close_other_shift(self):
        owner_token, _ = register_user()
        biz_id = create_business(owner_token)
        branch_id = create_branch(owner_token, biz_id)

        member_token, member_id = register_user()
        client.post(
            f"/api/v1/businesses/{biz_id}/members",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"user_id": member_id, "role": "MEMBER"},
        )

        cash_id = create_cash_account(owner_token, biz_id)
        open_res = open_shift(owner_token, biz_id, branch_id, cash_id)
        shift_id = open_res.json()["id"]

        close_res = client.patch(
            f"/api/v1/businesses/{biz_id}/shifts/{shift_id}/close",
            headers={"Authorization": f"Bearer {member_token}"},
            json={"actual_cash_count": 1000000},
        )
        assert close_res.status_code == 403

    def test_member_cannot_force_close(self):
        token, _ = register_user()
        biz_id = create_business(token)
        branch_id = create_branch(token, biz_id)
        cash_id = create_cash_account(token, biz_id)

        member_token, member_id = register_user()
        client.post(
            f"/api/v1/businesses/{biz_id}/members",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": member_id, "role": "MEMBER"},
        )

        open_res = open_shift(token, biz_id, branch_id, cash_id)
        shift_id = open_res.json()["id"]

        force_res = client.patch(
            f"/api/v1/businesses/{biz_id}/shifts/{shift_id}/force-close",
            headers={"Authorization": f"Bearer {member_token}"},
            json={"notes": "Force close test"},
        )
        assert force_res.status_code == 403

    def test_admin_can_view_all_shifts(self):
        token, _ = register_user()
        biz_id = create_business(token)
        branch_id = create_branch(token, biz_id)
        cash_id = create_cash_account(token, biz_id)

        open_shift(token, biz_id, branch_id, cash_id)

        list_res = client.get(
            f"/api/v1/businesses/{biz_id}/shifts",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_res.status_code == 200
        assert list_res.json()["total"] >= 1

    def test_admin_can_force_close(self):
        owner_token, _ = register_user()
        biz_id = create_business(owner_token)
        branch_id = create_branch(owner_token, biz_id)
        cash_id = create_cash_account(owner_token, biz_id)

        admin_token, admin_id = register_user()
        client.post(
            f"/api/v1/businesses/{biz_id}/members",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"user_id": admin_id, "role": "ADMIN"},
        )

        open_res = open_shift(owner_token, biz_id, branch_id, cash_id)
        shift_id = open_res.json()["id"]

        force_res = client.patch(
            f"/api/v1/businesses/{biz_id}/shifts/{shift_id}/force-close",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"notes": "Admin force close"},
        )
        assert force_res.status_code == 200
        assert force_res.json()["status"] == "CLOSED"


# ═══════════════════════════════════════════════════
# LIFECYCLE TESTS
# ═══════════════════════════════════════════════════

class TestShiftLifecycle:
    def test_open_to_close(self):
        token, _ = register_user()
        biz_id = create_business(token)
        branch_id = create_branch(token, biz_id)
        cash_id = create_cash_account(token, biz_id)

        open_res = open_shift(token, biz_id, branch_id, cash_id)
        shift_id = open_res.json()["id"]

        close_res = client.patch(
            f"/api/v1/businesses/{biz_id}/shifts/{shift_id}/close",
            headers={"Authorization": f"Bearer {token}"},
            json={"actual_cash_count": 1000000},
        )
        assert close_res.status_code == 200
        data = close_res.json()
        assert data["status"] == "CLOSED"
        assert data["closed_at"] is not None
        assert data["closed_by_user_id"] is not None
        assert float(data["actual_cash_count"]) == 1000000.0

    def test_closed_cannot_reopen(self):
        token, _ = register_user()
        biz_id = create_business(token)
        branch_id = create_branch(token, biz_id)
        cash_id = create_cash_account(token, biz_id)

        open_res = open_shift(token, biz_id, branch_id, cash_id)
        shift_id = open_res.json()["id"]

        close_res = client.patch(
            f"/api/v1/businesses/{biz_id}/shifts/{shift_id}/close",
            headers={"Authorization": f"Bearer {token}"},
            json={"actual_cash_count": 1000000},
        )
        assert close_res.status_code == 200

        close_res2 = client.patch(
            f"/api/v1/businesses/{biz_id}/shifts/{shift_id}/close",
            headers={"Authorization": f"Bearer {token}"},
            json={"actual_cash_count": 1000000},
        )
        assert close_res2.status_code == 400

    def test_normal_close_requires_actual_count(self):
        token, _ = register_user()
        biz_id = create_business(token)
        branch_id = create_branch(token, biz_id)
        cash_id = create_cash_account(token, biz_id)

        open_res = open_shift(token, biz_id, branch_id, cash_id)
        shift_id = open_res.json()["id"]

        close_res = client.patch(
            f"/api/v1/businesses/{biz_id}/shifts/{shift_id}/close",
            headers={"Authorization": f"Bearer {token}"},
            json={},
        )
        assert close_res.status_code == 422

    def test_force_close_requires_notes(self):
        token, _ = register_user()
        biz_id = create_business(token)
        branch_id = create_branch(token, biz_id)
        cash_id = create_cash_account(token, biz_id)

        open_res = open_shift(token, biz_id, branch_id, cash_id)
        shift_id = open_res.json()["id"]

        force_res = client.patch(
            f"/api/v1/businesses/{biz_id}/shifts/{shift_id}/force-close",
            headers={"Authorization": f"Bearer {token}"},
            json={"notes": ""},
        )
        assert force_res.status_code == 422

    def test_force_close_actual_count_none(self):
        token, _ = register_user()
        biz_id = create_business(token)
        branch_id = create_branch(token, biz_id)
        cash_id = create_cash_account(token, biz_id)

        open_res = open_shift(token, biz_id, branch_id, cash_id)
        shift_id = open_res.json()["id"]

        force_res = client.patch(
            f"/api/v1/businesses/{biz_id}/shifts/{shift_id}/force-close",
            headers={"Authorization": f"Bearer {token}"},
            json={"notes": "Force close"},
        )
        assert force_res.status_code == 200
        data = force_res.json()
        assert data["status"] == "CLOSED"
        assert data["actual_cash_count"] is None
        assert data["discrepancy"] is None


# ═══════════════════════════════════════════════════
# EXPECTED CASH / RECONCILIATION TESTS
# ═══════════════════════════════════════════════════

class TestExpectedCash:
    def test_expected_cash_with_movements(self):
        token, _ = register_user()
        biz_id = create_business(token)
        branch_id = create_branch(token, biz_id)
        cash_id = create_cash_account(token, biz_id)

        # Open shift
        open_res = open_shift(token, biz_id, branch_id, cash_id, "1000000")
        shift_id = open_res.json()["id"]

        # Create and finalize a sale
        sale_id = create_sale_with_product(token, biz_id, branch_id)

        # Create payment with shift_id
        pay_res = client.post(
            f"/api/v1/businesses/{biz_id}/payments",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "direction": "CUSTOMER_IN",
                "target_type": "SALES",
                "target_id": sale_id,
                "amount": 50000,
                "currency": "IDR",
                "payment_method": "CASH",
                "cash_account_id": cash_id,
                "shift_id": shift_id,
            },
        )
        assert pay_res.status_code == 201

        # Check expected cash
        detail_res = client.get(
            f"/api/v1/businesses/{biz_id}/shifts/{shift_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert detail_res.status_code == 200
        data = detail_res.json()
        # Opening 1M + CASH_IN 50K = 1,050,000
        assert float(data["expected_cash"]) == 1050000.0


# ═══════════════════════════════════════════════════
# PAYMENT INTEGRATION TESTS
# ═══════════════════════════════════════════════════

class TestPaymentShiftIntegration:
    def test_cash_payment_without_shift_rejected(self):
        """CASH payment on CASH account without shift_id must be rejected (SHIFT_REQUIRED)."""
        token, _ = register_user()
        biz_id = create_business(token)
        branch_id = create_branch(token, biz_id)
        cash_id = create_cash_account(token, biz_id)

        sale_id = create_sale_with_product(token, biz_id, branch_id)

        # CASH payment on CASH account without shift_id must fail
        pay_res = client.post(
            f"/api/v1/businesses/{biz_id}/payments",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "direction": "CUSTOMER_IN",
                "target_type": "SALES",
                "target_id": sale_id,
                "amount": 50000,
                "currency": "IDR",
                "payment_method": "CASH",
                "cash_account_id": cash_id,
            },
        )
        assert pay_res.status_code == 400
        body = pay_res.json()
        assert "shift" in body.get("detail", "").lower() or "shift" in str(body).lower()

    def test_cash_payment_with_valid_shift(self):
        token, _ = register_user()
        biz_id = create_business(token)
        branch_id = create_branch(token, biz_id)
        cash_id = create_cash_account(token, biz_id)

        # Open shift
        shift_res = open_shift(token, biz_id, branch_id, cash_id)
        shift_id = shift_res.json()["id"]

        # Create and finalize sale
        sale_id = create_sale_with_product(token, biz_id, branch_id)

        # CASH payment with shift
        pay_res = client.post(
            f"/api/v1/businesses/{biz_id}/payments",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "direction": "CUSTOMER_IN",
                "target_type": "SALES",
                "target_id": sale_id,
                "amount": 50000,
                "currency": "IDR",
                "payment_method": "CASH",
                "cash_account_id": cash_id,
                "shift_id": shift_id,
            },
        )
        assert pay_res.status_code == 201

    def test_non_cash_payment_no_shift_required(self):
        token, _ = register_user()
        biz_id = create_business(token)
        branch_id = create_branch(token, biz_id)
        bank_id = create_cash_account(token, biz_id, "Bank Account", "BANK")

        sale_id = create_sale_with_product(token, biz_id, branch_id)

        # BANK_TRANSFER payment - no shift needed
        pay_res = client.post(
            f"/api/v1/businesses/{biz_id}/payments",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "direction": "CUSTOMER_IN",
                "target_type": "SALES",
                "target_id": sale_id,
                "amount": 50000,
                "currency": "IDR",
                "payment_method": "BANK_TRANSFER",
                "cash_account_id": bank_id,
            },
        )
        assert pay_res.status_code == 201


# ═══════════════════════════════════════════════════
# SECURITY TESTS
# ═══════════════════════════════════════════════════

class TestShiftSecurity:
    def test_cross_business_shift_access_rejected(self):
        token1, _ = register_user()
        token2, _ = register_user()
        biz1 = create_business(token1, "Biz 1")
        biz2 = create_business(token2, "Biz 2")

        branch1 = create_branch(token1, biz1, "Branch 1")

        cash1 = create_cash_account(token1, biz1, "Cash 1")

        res1 = open_shift(token1, biz1, branch1, cash1)
        shift_id = res1.json()["id"]

        # User from biz2 tries to access shift from biz1
        res2 = client.get(
            f"/api/v1/businesses/{biz2}/shifts/{shift_id}",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert res2.status_code == 404

    def test_wrong_cash_account_shift_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        branch_id = create_branch(token, biz_id)
        cash_id = create_cash_account(token, biz_id, "Cash 1")
        cash_id2 = create_cash_account(token, biz_id, "Cash 2")

        # Open shift on Cash 1
        shift_res = open_shift(token, biz_id, branch_id, cash_id)
        shift_id = shift_res.json()["id"]

        # Create a sale
        sale_id = create_sale_with_product(token, biz_id, branch_id)

        # Try to pay with Cash 2 using shift from Cash 1
        pay_res = client.post(
            f"/api/v1/businesses/{biz_id}/payments",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "direction": "CUSTOMER_IN",
                "target_type": "SALES",
                "target_id": sale_id,
                "amount": 50000,
                "currency": "IDR",
                "payment_method": "CASH",
                "cash_account_id": cash_id2,
                "shift_id": shift_id,
            },
        )
        assert pay_res.status_code == 400
        body = pay_res.json()
        assert "cash_account" in body.get("detail", "").lower() or "cash_account" in str(body).lower()

    def test_jwt_required(self):
        res = client.get("/api/v1/businesses/biz-id/shifts")
        assert res.status_code == 401

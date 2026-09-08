"""
Feature #40 — Cash Flow Statement (Direct Method) Test Suite
"""
import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta
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
from app.modules.cash_account.schemas import (
    CashAccountType,
    CashMovementType,
    MovementDirection,
    CashMovementStatus,
)
from app.modules.payment.schemas import (
    PaymentDirection,
    PaymentTargetType,
    PaymentMethod,
    PaymentStatus,
)
from app.modules.expense.schemas import ExpenseStatus

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
    yield
    InMemoryAccountingRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryUserRepository.clear()
    InMemoryPaymentRepository.clear()
    InMemoryExpenseRepository.clear()
    InMemoryCashAccountRepository.clear()


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


def add_member(token, biz_id, member_token, role="MEMBER"):
    member_user_id = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {member_token}"}
    ).json()["id"]
    res = client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": member_user_id, "role": role},
    )
    assert res.status_code == 201
    return res.json()


def create_period(token, biz_id, period_name="2026-09", start_date="2026-09-01", end_date="2026-09-30"):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/accounting/periods",
        headers={"Authorization": f"Bearer {token}"},
        json={"period_name": period_name, "start_date": start_date, "end_date": end_date},
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_cash_account(token, biz_id, name="Bank BCA", opening_balance="10000000.00", code="BCA"):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/cash-accounts",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": name,
            "code": code,
            "account_type": "BANK",
            "currency": "IDR",
            "opening_balance": opening_balance,
            "is_default": True,
        },
    )
    assert res.status_code == 201
    return res.json()["id"]


_payment_seq = 0


def _create_test_payment(biz_id, direction, target_type, target_id, amount, cash_account_id,
                         user_id, payment_date, payment_method="BANK_TRANSFER",
                         status=PaymentStatus.RECORDED):
    global _payment_seq
    _payment_seq += 1
    payment_repo = InMemoryPaymentRepository()
    import asyncio
    return asyncio.run(
        payment_repo.create_payment({
            "business_id": biz_id,
            "branch_id": "WALK_IN",
            "direction": direction,
            "target_type": target_type,
            "target_id": target_id,
            "payment_number": f"PMT-{_payment_seq:06d}",
            "amount": Decimal(str(amount)),
            "currency": "IDR",
            "payment_method": payment_method,
            "cash_account_id": cash_account_id,
            "payment_date": payment_date,
            "status": status,
            "created_by_user_id": user_id,
        })
    )


# ─────────────────────────────────────────────
# Feature #40 Test Cases
# ─────────────────────────────────────────────

def test_01_empty_period():
    token, _ = register_user("owner01@test.com")
    biz_id = create_business(token)
    period_id = create_period(token, biz_id, "2026-09", "2026-09-01", "2026-09-30")
    create_cash_account(token, biz_id, opening_balance="10000000.00")

    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/reports/cash-flow?period_id={period_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["period"]["id"] == period_id
    assert data["period"]["period_name"] == "2026-09"
    assert data["date_range"]["start_date"] == "2026-09-01"
    assert data["date_range"]["end_date"] == "2026-09-30"
    assert Decimal(str(data["opening_cash_balance"])) == Decimal("10000000.00")
    assert Decimal(str(data["operating_activities"]["cash_received_from_customers"])) == Decimal("0.00")
    assert Decimal(str(data["operating_activities"]["cash_paid_to_suppliers"])) == Decimal("0.00")
    assert Decimal(str(data["operating_activities"]["cash_paid_for_expenses"])) == Decimal("0.00")
    assert Decimal(str(data["operating_activities"]["net_cash_from_operating"])) == Decimal("0.00")
    assert Decimal(str(data["investing_activities"]["net_cash_from_investing"])) == Decimal("0.00")
    assert Decimal(str(data["financing_activities"]["net_cash_from_financing"])) == Decimal("0.00")
    assert Decimal(str(data["net_increase_in_cash"])) == Decimal("0.00")
    assert Decimal(str(data["closing_cash_balance"])) == Decimal("10000000.00")
    assert data["reconciliation_status"] == "SUBLEDGER_RECONCILED"


def test_02_customer_receipt():
    token, user_id = register_user("owner02@test.com")
    biz_id = create_business(token)
    acc_id = create_cash_account(token, biz_id, opening_balance="10000000.00")

    _create_test_payment(
        biz_id, PaymentDirection.CUSTOMER_IN, PaymentTargetType.SALES, "sales-001",
        "5000000.00", acc_id, user_id,
        datetime(2026, 9, 15, 10, 0, 0, tzinfo=timezone.utc),
    )

    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/reports/cash-flow?date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert Decimal(str(data["operating_activities"]["cash_received_from_customers"])) == Decimal("5000000.00")
    assert Decimal(str(data["operating_activities"]["net_cash_from_operating"])) == Decimal("5000000.00")
    assert Decimal(str(data["net_increase_in_cash"])) == Decimal("5000000.00")
    assert Decimal(str(data["closing_cash_balance"])) == Decimal("15000000.00")


def test_03_supplier_payment():
    token, user_id = register_user("owner03@test.com")
    biz_id = create_business(token)
    acc_id = create_cash_account(token, biz_id, opening_balance="10000000.00")

    _create_test_payment(
        biz_id, PaymentDirection.SUPPLIER_OUT, PaymentTargetType.PURCHASE, "purchase-001",
        "2000000.00", acc_id, user_id,
        datetime(2026, 9, 16, 11, 0, 0, tzinfo=timezone.utc),
    )

    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/reports/cash-flow?date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert Decimal(str(data["operating_activities"]["cash_paid_to_suppliers"])) == Decimal("2000000.00")
    assert Decimal(str(data["operating_activities"]["net_cash_from_operating"])) == Decimal("-2000000.00")
    assert Decimal(str(data["closing_cash_balance"])) == Decimal("8000000.00")


def test_04_operational_expense():
    token, user_id = register_user("owner04@test.com")
    biz_id = create_business(token)
    acc_id = create_cash_account(token, biz_id, opening_balance="10000000.00")

    expense_repo = InMemoryExpenseRepository()
    import asyncio
    exp = asyncio.run(
        expense_repo.create_expense(
            business_id=biz_id,
            expense_number="EXP-001",
            expense_date=datetime(2026, 9, 17, 14, 0, 0, tzinfo=timezone.utc),
            category_id="cat-001",
            amount=Decimal("500000.00"),
            currency="IDR",
            created_by_user_id=user_id,
            cash_account_id=acc_id,
        )
    )
    asyncio.run(
        expense_repo.update_expense(
            expense_id=exp.id,
            business_id=biz_id,
            status=ExpenseStatus.FINALIZED,
            finalized_by_user_id=user_id,
            finalized_at=datetime(2026, 9, 17, 14, 5, 0, tzinfo=timezone.utc),
        )
    )

    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/reports/cash-flow?date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert Decimal(str(data["operating_activities"]["cash_paid_for_expenses"])) == Decimal("500000.00")
    assert Decimal(str(data["operating_activities"]["net_cash_from_operating"])) == Decimal("-500000.00")
    assert Decimal(str(data["closing_cash_balance"])) == Decimal("9500000.00")


def test_05_combined_operating_flow():
    token, user_id = register_user("owner05@test.com")
    biz_id = create_business(token)
    acc_id = create_cash_account(token, biz_id, opening_balance="10000000.00")

    expense_repo = InMemoryExpenseRepository()
    import asyncio

    # 1. Customer receipt 5,000,000
    _create_test_payment(
        biz_id, PaymentDirection.CUSTOMER_IN, PaymentTargetType.SALES, "sales-001",
        "5000000.00", acc_id, user_id,
        datetime(2026, 9, 5, 10, 0, 0, tzinfo=timezone.utc),
    )

    # 2. Supplier payment 2,000,000
    _create_test_payment(
        biz_id, PaymentDirection.SUPPLIER_OUT, PaymentTargetType.PURCHASE, "purchase-001",
        "2000000.00", acc_id, user_id,
        datetime(2026, 9, 10, 11, 0, 0, tzinfo=timezone.utc),
    )

    # 3. Finalized Expense 500,000
    exp = asyncio.run(
        expense_repo.create_expense(
            business_id=biz_id,
            expense_number="EXP-001",
            expense_date=datetime(2026, 9, 20, 14, 0, 0, tzinfo=timezone.utc),
            category_id="cat-001",
            amount=Decimal("500000.00"),
            currency="IDR",
            created_by_user_id=user_id,
            cash_account_id=acc_id,
        )
    )
    asyncio.run(
        expense_repo.update_expense(
            expense_id=exp.id,
            business_id=biz_id,
            status=ExpenseStatus.FINALIZED,
            finalized_by_user_id=user_id,
        )
    )

    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/reports/cash-flow?date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert Decimal(str(data["opening_cash_balance"])) == Decimal("10000000.00")
    assert Decimal(str(data["operating_activities"]["cash_received_from_customers"])) == Decimal("5000000.00")
    assert Decimal(str(data["operating_activities"]["cash_paid_to_suppliers"])) == Decimal("2000000.00")
    assert Decimal(str(data["operating_activities"]["cash_paid_for_expenses"])) == Decimal("500000.00")
    assert Decimal(str(data["operating_activities"]["net_cash_from_operating"])) == Decimal("2500000.00")
    assert Decimal(str(data["net_increase_in_cash"])) == Decimal("2500000.00")
    assert Decimal(str(data["closing_cash_balance"])) == Decimal("12500000.00")
    assert data["reconciliation_status"] == "SUBLEDGER_RECONCILED"


def test_06_exact_start_boundary():
    token, user_id = register_user("owner06@test.com")
    biz_id = create_business(token)
    acc_id = create_cash_account(token, biz_id, opening_balance="1000.00")

    # Exact start boundary at 00:00:00 UTC on 2026-09-01
    _create_test_payment(
        biz_id, PaymentDirection.CUSTOMER_IN, PaymentTargetType.SALES, "sales-001",
        "100.00", acc_id, user_id,
        datetime(2026, 9, 1, 0, 0, 0, 0, tzinfo=timezone.utc),
        payment_method="CASH",
    )

    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/reports/cash-flow?date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert Decimal(str(res.json()["operating_activities"]["cash_received_from_customers"])) == Decimal("100.00")


def test_07_exact_end_boundary():
    token, user_id = register_user("owner07@test.com")
    biz_id = create_business(token)
    acc_id = create_cash_account(token, biz_id, opening_balance="1000.00")

    # 23:59:59.999999 on 2026-09-30
    _create_test_payment(
        biz_id, PaymentDirection.CUSTOMER_IN, PaymentTargetType.SALES, "sales-001",
        "200.00", acc_id, user_id,
        datetime(2026, 9, 30, 23, 59, 59, 999999, tzinfo=timezone.utc),
        payment_method="CASH",
    )

    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/reports/cash-flow?date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert Decimal(str(res.json()["operating_activities"]["cash_received_from_customers"])) == Decimal("200.00")


def test_08_end_boundary_23_59_59_000000():
    token, user_id = register_user("owner08@test.com")
    biz_id = create_business(token)
    acc_id = create_cash_account(token, biz_id, opening_balance="1000.00")

    _create_test_payment(
        biz_id, PaymentDirection.CUSTOMER_IN, PaymentTargetType.SALES, "sales-001",
        "300.00", acc_id, user_id,
        datetime(2026, 9, 30, 23, 59, 59, 0, tzinfo=timezone.utc),
        payment_method="CASH",
    )

    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/reports/cash-flow?date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert Decimal(str(res.json()["operating_activities"]["cash_received_from_customers"])) == Decimal("300.00")


def test_09_end_boundary_23_59_59_500000():
    token, user_id = register_user("owner09@test.com")
    biz_id = create_business(token)
    acc_id = create_cash_account(token, biz_id, opening_balance="1000.00")

    _create_test_payment(
        biz_id, PaymentDirection.CUSTOMER_IN, PaymentTargetType.SALES, "sales-001",
        "400.00", acc_id, user_id,
        datetime(2026, 9, 30, 23, 59, 59, 500000, tzinfo=timezone.utc),
        payment_method="CASH",
    )

    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/reports/cash-flow?date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert Decimal(str(res.json()["operating_activities"]["cash_received_from_customers"])) == Decimal("400.00")


def test_10_end_boundary_23_59_59_999999():
    token, user_id = register_user("owner10@test.com")
    biz_id = create_business(token)
    acc_id = create_cash_account(token, biz_id, opening_balance="1000.00")

    _create_test_payment(
        biz_id, PaymentDirection.CUSTOMER_IN, PaymentTargetType.SALES, "sales-001",
        "500.00", acc_id, user_id,
        datetime(2026, 9, 30, 23, 59, 59, 999999, tzinfo=timezone.utc),
        payment_method="CASH",
    )

    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/reports/cash-flow?date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert Decimal(str(res.json()["operating_activities"]["cash_received_from_customers"])) == Decimal("500.00")


def test_11_next_day_00_00_00_excluded():
    token, user_id = register_user("owner11@test.com")
    biz_id = create_business(token)
    acc_id = create_cash_account(token, biz_id, opening_balance="1000.00")

    # Next day at exactly 00:00:00 UTC (2026-10-01 00:00:00) must be excluded
    _create_test_payment(
        biz_id, PaymentDirection.CUSTOMER_IN, PaymentTargetType.SALES, "sales-001",
        "600.00", acc_id, user_id,
        datetime(2026, 10, 1, 0, 0, 0, 0, tzinfo=timezone.utc),
        payment_method="CASH",
    )

    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/reports/cash-flow?date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert Decimal(str(res.json()["operating_activities"]["cash_received_from_customers"])) == Decimal("0.00")


def test_12_internal_transfer_excluded_from_activity_totals():
    token, user_id = register_user("owner12@test.com")
    biz_id = create_business(token)
    acc1_id = create_cash_account(token, biz_id, name="Bank A", opening_balance="1000000.00", code="BNKA")
    acc2_id = create_cash_account(token, biz_id, name="Bank B", opening_balance="2000000.00", code="BNKB")

    cash_repo = InMemoryCashAccountRepository()
    import asyncio
    now = datetime(2026, 9, 15, 12, 0, 0, tzinfo=timezone.utc)
    m1 = asyncio.run(
        cash_repo.create_movement(
            business_id=biz_id,
            cash_account_id=acc1_id,
            movement_type=CashMovementType.TRANSFER_OUT,
            amount=Decimal("500000.00"),
            direction=MovementDirection.OUT,
            performed_by_user_id=user_id,
        )
    )
    m2 = asyncio.run(
        cash_repo.create_movement(
            business_id=biz_id,
            cash_account_id=acc2_id,
            movement_type=CashMovementType.TRANSFER_IN,
            amount=Decimal("500000.00"),
            direction=MovementDirection.IN,
            performed_by_user_id=user_id,
        )
    )
    cash_repo._movements[m1.id] = m1.model_copy(update={"created_at": now})
    cash_repo._movements[m2.id] = m2.model_copy(update={"created_at": now})

    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/reports/cash-flow?date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert Decimal(str(data["operating_activities"]["net_cash_from_operating"])) == Decimal("0.00")
    assert Decimal(str(data["investing_activities"]["net_cash_from_investing"])) == Decimal("0.00")
    assert Decimal(str(data["financing_activities"]["net_cash_from_financing"])) == Decimal("0.00")
    assert Decimal(str(data["net_increase_in_cash"])) == Decimal("0.00")
    assert Decimal(str(data["opening_cash_balance"])) == Decimal("3000000.00")
    assert Decimal(str(data["closing_cash_balance"])) == Decimal("3000000.00")


def test_13_transfer_affects_historical_opening_cash():
    token, user_id = register_user("owner13@test.com")
    biz_id = create_business(token)
    acc1_id = create_cash_account(token, biz_id, name="Bank A", opening_balance="1000000.00", code="BNKA")

    cash_repo = InMemoryCashAccountRepository()
    import asyncio
    prior_dt = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
    m = asyncio.run(
        cash_repo.create_movement(
            business_id=biz_id,
            cash_account_id=acc1_id,
            movement_type=CashMovementType.CASH_IN,
            amount=Decimal("500000.00"),
            direction=MovementDirection.IN,
            performed_by_user_id=user_id,
        )
    )
    cash_repo._movements[m.id] = m.model_copy(update={"created_at": prior_dt})

    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/reports/cash-flow?date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert Decimal(str(data["opening_cash_balance"])) == Decimal("1500000.00")
    assert Decimal(str(data["closing_cash_balance"])) == Decimal("1500000.00")


def test_14_cancelled_cash_movement_excluded():
    token, user_id = register_user("owner14@test.com")
    biz_id = create_business(token)
    acc1_id = create_cash_account(token, biz_id, name="Bank A", opening_balance="1000000.00", code="BNKA")

    cash_repo = InMemoryCashAccountRepository()
    import asyncio
    prior_dt = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
    m = asyncio.run(
        cash_repo.create_movement(
            business_id=biz_id,
            cash_account_id=acc1_id,
            movement_type=CashMovementType.CASH_IN,
            amount=Decimal("500000.00"),
            direction=MovementDirection.IN,
            performed_by_user_id=user_id,
        )
    )
    cash_repo._movements[m.id] = m.model_copy(update={"created_at": prior_dt, "status": CashMovementStatus.CANCELLED})

    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/reports/cash-flow?date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert Decimal(str(data["opening_cash_balance"])) == Decimal("1000000.00")


def test_15_voided_payment_excluded():
    token, user_id = register_user("owner15@test.com")
    biz_id = create_business(token)
    acc_id = create_cash_account(token, biz_id, opening_balance="10000000.00")

    _create_test_payment(
        biz_id, PaymentDirection.CUSTOMER_IN, PaymentTargetType.SALES, "sales-001",
        "5000000.00", acc_id, user_id,
        datetime(2026, 9, 15, 10, 0, 0, tzinfo=timezone.utc),
        status=PaymentStatus.VOIDED,
    )

    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/reports/cash-flow?date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert Decimal(str(data["operating_activities"]["cash_received_from_customers"])) == Decimal("0.00")


def test_16_non_finalized_expense_excluded():
    token, user_id = register_user("owner16@test.com")
    biz_id = create_business(token)
    acc_id = create_cash_account(token, biz_id, opening_balance="10000000.00")

    expense_repo = InMemoryExpenseRepository()
    import asyncio
    asyncio.run(
        expense_repo.create_expense(
            business_id=biz_id,
            expense_number="EXP-DRAFT",
            expense_date=datetime(2026, 9, 17, 14, 0, 0, tzinfo=timezone.utc),
            category_id="cat-001",
            amount=Decimal("500000.00"),
            currency="IDR",
            created_by_user_id=user_id,
            cash_account_id=acc_id,
        )
    )

    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/reports/cash-flow?date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert Decimal(str(data["operating_activities"]["cash_paid_for_expenses"])) == Decimal("0.00")


def test_17_opening_balance_reconstruction():
    token, user_id = register_user("owner17@test.com")
    biz_id = create_business(token)
    acc1 = create_cash_account(token, biz_id, name="Acc 1", opening_balance="2000000.00", code="AC1")
    acc2 = create_cash_account(token, biz_id, name="Acc 2", opening_balance="3000000.00", code="AC2")

    cash_repo = InMemoryCashAccountRepository()
    import asyncio
    prior_dt = datetime(2026, 8, 20, 10, 0, 0, tzinfo=timezone.utc)
    m = asyncio.run(
        cash_repo.create_movement(
            business_id=biz_id,
            cash_account_id=acc1,
            movement_type=CashMovementType.CASH_OUT,
            amount=Decimal("500000.00"),
            direction=MovementDirection.OUT,
            performed_by_user_id=user_id,
        )
    )
    cash_repo._movements[m.id] = m.model_copy(update={"created_at": prior_dt})

    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/reports/cash-flow?date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    # 2,000,000 + 3,000,000 - 500,000 = 4,500,000
    assert Decimal(str(res.json()["opening_cash_balance"])) == Decimal("4500000.00")


def test_18_closing_balance_reconstruction():
    token, user_id = register_user("owner18@test.com")
    biz_id = create_business(token)
    acc = create_cash_account(token, biz_id, opening_balance="5000000.00")

    _create_test_payment(
        biz_id, PaymentDirection.CUSTOMER_IN, PaymentTargetType.SALES, "sales-001",
        "1500000.00", acc, user_id,
        datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc),
    )

    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/reports/cash-flow?date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert Decimal(str(data["opening_cash_balance"])) == Decimal("5000000.00")
    assert Decimal(str(data["net_increase_in_cash"])) == Decimal("1500000.00")
    assert Decimal(str(data["closing_cash_balance"])) == Decimal("6500000.00")


def test_19_mathematical_reconciliation():
    token, user_id = register_user("owner19@test.com")
    biz_id = create_business(token)
    acc = create_cash_account(token, biz_id, opening_balance="1234567.89")

    _create_test_payment(
        biz_id, PaymentDirection.CUSTOMER_IN, PaymentTargetType.SALES, "sales-001",
        "987654.32", acc, user_id,
        datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc),
    )

    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/reports/cash-flow?date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    opening = Decimal(str(data["opening_cash_balance"]))
    net_inc = Decimal(str(data["net_increase_in_cash"]))
    closing = Decimal(str(data["closing_cash_balance"]))
    assert opening + net_inc == closing


def test_20_subledger_reconciliation_status():
    token, _ = register_user("owner20@test.com")
    biz_id = create_business(token)
    create_cash_account(token, biz_id, opening_balance="1000000.00")

    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/reports/cash-flow?date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["reconciliation_status"] == "SUBLEDGER_RECONCILED"


def test_21_cross_business_isolation():
    token1, user_id1 = register_user("owner21_1@test.com")
    biz1 = create_business(token1, name="Biz 1")
    acc1 = create_cash_account(token1, biz1, opening_balance="10000000.00")

    token2, user_id2 = register_user("owner21_2@test.com")
    biz2 = create_business(token2, name="Biz 2")
    acc2 = create_cash_account(token2, biz2, opening_balance="20000000.00")

    # Biz 1 payment
    _create_test_payment(
        biz1, PaymentDirection.CUSTOMER_IN, PaymentTargetType.SALES, "sales-001",
        "5000000.00", acc1, user_id1,
        datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc),
    )

    # Biz 2 report must not see Biz 1 payment or account
    res2 = client.get(
        f"/api/v1/businesses/{biz2}/accounting/reports/cash-flow?date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert Decimal(str(data2["opening_cash_balance"])) == Decimal("20000000.00")
    assert Decimal(str(data2["operating_activities"]["cash_received_from_customers"])) == Decimal("0.00")
    assert Decimal(str(data2["closing_cash_balance"])) == Decimal("20000000.00")


def test_22_inactive_membership_rejection():
    token_owner, _ = register_user("owner22@test.com")
    biz_id = create_business(token_owner)
    token_stranger, _ = register_user("stranger22@test.com")

    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/reports/cash-flow?date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token_stranger}"},
    )
    assert res.status_code in (403, 404)


def test_23_owner_access():
    token, _ = register_user("owner23@test.com")
    biz_id = create_business(token)
    create_cash_account(token, biz_id, opening_balance="1000.00")

    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/reports/cash-flow?date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200


def test_24_admin_access():
    token_owner, _ = register_user("owner24@test.com")
    biz_id = create_business(token_owner)
    token_admin, _ = register_user("admin24@test.com")
    add_member(token_owner, biz_id, token_admin, role="ADMIN")

    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/reports/cash-flow?date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert res.status_code == 200


def test_25_member_access():
    token_owner, _ = register_user("owner25@test.com")
    biz_id = create_business(token_owner)
    token_member, _ = register_user("member25@test.com")
    add_member(token_owner, biz_id, token_member, role="MEMBER")

    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/reports/cash-flow?date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token_member}"},
    )
    assert res.status_code == 200


def test_26_missing_parameters_422():
    token, _ = register_user("owner26@test.com")
    biz_id = create_business(token)

    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/reports/cash-flow",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422


def test_27_invalid_date_range_422():
    token, _ = register_user("owner27@test.com")
    biz_id = create_business(token)

    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/reports/cash-flow?date_from=2026-09-30&date_to=2026-09-01",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422


def test_28_invalid_period_404():
    token, _ = register_user("owner28@test.com")
    biz_id = create_business(token)

    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/reports/cash-flow?period_id=00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404


def test_29_decimal_precision():
    token, user_id = register_user("owner29@test.com")
    biz_id = create_business(token)
    acc = create_cash_account(token, biz_id, opening_balance="0.01")

    _create_test_payment(
        biz_id, PaymentDirection.CUSTOMER_IN, PaymentTargetType.SALES, "sales-001",
        "0.02", acc, user_id,
        datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc),
    )

    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/reports/cash-flow?date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert Decimal(str(data["opening_cash_balance"])) == Decimal("0.01")
    assert Decimal(str(data["operating_activities"]["cash_received_from_customers"])) == Decimal("0.02")
    assert Decimal(str(data["closing_cash_balance"])) == Decimal("0.03")


def test_30_no_double_counting():
    token, user_id = register_user("owner30@test.com")
    biz_id = create_business(token)
    acc = create_cash_account(token, biz_id, opening_balance="1000000.00")

    p = _create_test_payment(
        biz_id, PaymentDirection.CUSTOMER_IN, PaymentTargetType.SALES, "sales-001",
        "500000.00", acc, user_id,
        datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc),
    )

    # Also create a CashMovement record (simulating what PaymentService does)
    cash_repo = InMemoryCashAccountRepository()
    import asyncio
    m = asyncio.run(
        cash_repo.create_movement(
            business_id=biz_id,
            cash_account_id=acc,
            movement_type=CashMovementType.SALES_PAYMENT,
            amount=Decimal("500000.00"),
            direction=MovementDirection.IN,
            performed_by_user_id=user_id,
            reference_type="PAYMENT",
            reference_id=p.id,
        )
    )
    cash_repo._movements[m.id] = m.model_copy(
        update={"created_at": datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc)}
    )

    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/reports/cash-flow?date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    # Cash received from customers must be exactly 500,000 (NOT doubled)
    assert Decimal(str(data["operating_activities"]["cash_received_from_customers"])) == Decimal("500000.00")
    assert Decimal(str(data["net_increase_in_cash"])) == Decimal("500000.00")
    assert Decimal(str(data["closing_cash_balance"])) == Decimal("1500000.00")


def test_31_expense_without_cash_account_excluded():
    token, user_id = register_user("owner31@test.com")
    biz_id = create_business(token)
    create_cash_account(token, biz_id, opening_balance="10000000.00")

    expense_repo = InMemoryExpenseRepository()
    import asyncio
    # Expense WITHOUT cash_account_id
    exp = asyncio.run(
        expense_repo.create_expense(
            business_id=biz_id,
            expense_number="EXP-NOACCT",
            expense_date=datetime(2026, 9, 17, 14, 0, 0, tzinfo=timezone.utc),
            category_id="cat-001",
            amount=Decimal("500000.00"),
            currency="IDR",
            created_by_user_id=user_id,
            cash_account_id=None,
        )
    )
    asyncio.run(
        expense_repo.update_expense(
            expense_id=exp.id,
            business_id=biz_id,
            status=ExpenseStatus.FINALIZED,
            finalized_by_user_id=user_id,
        )
    )

    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/reports/cash-flow?date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert Decimal(str(res.json()["operating_activities"]["cash_paid_for_expenses"])) == Decimal("0.00")


def test_32_payment_outside_period_excluded():
    token, user_id = register_user("owner32@test.com")
    biz_id = create_business(token)
    acc_id = create_cash_account(token, biz_id, opening_balance="10000000.00")

    # Payment before period start
    _create_test_payment(
        biz_id, PaymentDirection.CUSTOMER_IN, PaymentTargetType.SALES, "sales-001",
        "1000000.00", acc_id, user_id,
        datetime(2026, 8, 15, 10, 0, 0, tzinfo=timezone.utc),
    )

    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/reports/cash-flow?date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert Decimal(str(res.json()["operating_activities"]["cash_received_from_customers"])) == Decimal("0.00")

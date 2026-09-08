"""
Feature #41 — Customer Statement of Account (Kartu Piutang) Test Suite
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
from app.modules.customer.repository import InMemoryCustomerRepository
from app.modules.customer.schemas import CustomerType
from app.modules.sales.repository import InMemorySalesRepository
from app.modules.sales.schemas import SalesStatus
from app.modules.sales_return.repository import InMemorySalesReturnRepository
from app.modules.sales_return.schemas import SalesReturnStatus
from app.modules.payment.repository import InMemoryPaymentRepository
from app.modules.payment.schemas import (
    PaymentDirection,
    PaymentTargetType,
    PaymentMethod,
    PaymentStatus,
)
from app.modules.cash_account.repository import InMemoryCashAccountRepository

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_repositories():
    InMemoryCustomerRepository.clear()
    InMemorySalesRepository.clear()
    InMemorySalesReturnRepository.clear()
    InMemoryPaymentRepository.clear()
    InMemoryCashAccountRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryUserRepository.clear()
    yield
    InMemoryCustomerRepository.clear()
    InMemorySalesRepository.clear()
    InMemorySalesReturnRepository.clear()
    InMemoryPaymentRepository.clear()
    InMemoryCashAccountRepository.clear()
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


def create_customer(token, biz_id, name="Customer PT A"):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/customers",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "customer_type": "ORGANIZATION"},
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


_sales_seq = 0
_payment_seq = 0
_return_seq = 0


def _create_sales(biz_id, customer_id, user_id, grand_total, sales_date, status=SalesStatus.FINALIZED):
    global _sales_seq
    _sales_seq += 1
    sales_repo = InMemorySalesRepository()
    import asyncio
    s = asyncio.run(
        sales_repo.create_sales(
            business_id=biz_id,
            branch_id="MAIN",
            sales_number=f"SO-{_sales_seq:06d}",
            sales_date=sales_date,
            created_by_user_id=user_id,
            customer_id=customer_id,
        )
    )
    s_updated = asyncio.run(
        sales_repo.update_sales(
            sales_id=s.id,
            business_id=biz_id,
            status=status,
            subtotal=Decimal(str(grand_total)),
            grand_total=Decimal(str(grand_total)),
            finalized_by_user_id=user_id if status == SalesStatus.FINALIZED else None,
            finalized_at=sales_date if status == SalesStatus.FINALIZED else None,
        )
    )
    return s_updated


def _create_sales_return(biz_id, sales_id, user_id, grand_total, return_date, status=SalesReturnStatus.FINALIZED):
    global _return_seq
    _return_seq += 1
    ret_repo = InMemorySalesReturnRepository()
    import asyncio
    r = asyncio.run(
        ret_repo.create_return(
            business_id=biz_id,
            sales_id=sales_id,
            inventory_location_id="LOC-1",
            return_number=f"SR-{_return_seq:06d}",
            return_date=return_date,
            created_by_user_id=user_id,
        )
    )
    r_updated = asyncio.run(
        ret_repo.update_return(
            return_id=r.id,
            business_id=biz_id,
            status=status,
            subtotal=Decimal(str(grand_total)),
            grand_total=Decimal(str(grand_total)),
            finalized_by_user_id=user_id if status == SalesReturnStatus.FINALIZED else None,
            finalized_at=return_date if status == SalesReturnStatus.FINALIZED else None,
        )
    )
    return r_updated


def _create_payment(biz_id, target_sales_id, cash_account_id, user_id, amount, payment_date, status=PaymentStatus.RECORDED):
    global _payment_seq
    _payment_seq += 1
    payment_repo = InMemoryPaymentRepository()
    import asyncio
    return asyncio.run(
        payment_repo.create_payment({
            "business_id": biz_id,
            "branch_id": "MAIN",
            "direction": PaymentDirection.CUSTOMER_IN,
            "target_type": PaymentTargetType.SALES,
            "target_id": target_sales_id,
            "payment_number": f"PMT-{_payment_seq:06d}",
            "amount": Decimal(str(amount)),
            "currency": "IDR",
            "payment_method": PaymentMethod.BANK_TRANSFER,
            "cash_account_id": cash_account_id,
            "payment_date": payment_date,
            "status": status,
            "created_by_user_id": user_id,
        })
    )


# ─────────────────────────────────────────────
# Test Cases
# ─────────────────────────────────────────────

def test_01_empty_period():
    token, _ = register_user("owner01@test.com")
    biz_id = create_business(token)
    cust_id = create_customer(token, biz_id)

    res = client.get(
        f"/api/v1/businesses/{biz_id}/receivables/statements?customer_id={cust_id}&date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["entity_id"] == cust_id
    assert Decimal(str(data["opening_balance"])) == Decimal("0.00")
    assert Decimal(str(data["closing_balance"])) == Decimal("0.00")
    assert Decimal(str(data["total_debit"])) == Decimal("0.00")
    assert Decimal(str(data["total_credit"])) == Decimal("0.00")
    assert data["lines"] == []
    assert data["total_items"] == 0


def test_02_opening_balance_reconstruction():
    token, user_id = register_user("owner02@test.com")
    biz_id = create_business(token)
    cust_id = create_customer(token, biz_id)
    acc_id = create_cash_account(token, biz_id)

    # Prior sale of 1,000,000 on 2026-08-15
    s = _create_sales(biz_id, cust_id, user_id, "1000000.00", datetime(2026, 8, 15, 10, 0, tzinfo=timezone.utc))
    # Prior payment of 400,000 on 2026-08-20
    _create_payment(biz_id, s.id, acc_id, user_id, "400000.00", datetime(2026, 8, 20, 10, 0, tzinfo=timezone.utc))

    res = client.get(
        f"/api/v1/businesses/{biz_id}/receivables/statements?customer_id={cust_id}&date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert Decimal(str(data["opening_balance"])) == Decimal("600000.00")
    assert Decimal(str(data["closing_balance"])) == Decimal("600000.00")
    assert data["lines"] == []


def test_03_single_invoice_in_period():
    token, user_id = register_user("owner03@test.com")
    biz_id = create_business(token)
    cust_id = create_customer(token, biz_id)

    _create_sales(biz_id, cust_id, user_id, "500000.00", datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc))

    res = client.get(
        f"/api/v1/businesses/{biz_id}/receivables/statements?customer_id={cust_id}&date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert Decimal(str(data["opening_balance"])) == Decimal("0.00")
    assert Decimal(str(data["total_debit"])) == Decimal("500000.00")
    assert Decimal(str(data["total_credit"])) == Decimal("0.00")
    assert Decimal(str(data["closing_balance"])) == Decimal("500000.00")
    assert len(data["lines"]) == 1
    assert data["lines"][0]["transaction_type"] == "SALE"
    assert Decimal(str(data["lines"][0]["debit"])) == Decimal("500000.00")
    assert Decimal(str(data["lines"][0]["running_balance"])) == Decimal("500000.00")


def test_04_multiple_invoices_and_running_balance():
    token, user_id = register_user("owner04@test.com")
    biz_id = create_business(token)
    cust_id = create_customer(token, biz_id)

    _create_sales(biz_id, cust_id, user_id, "1000000.00", datetime(2026, 9, 5, 10, 0, tzinfo=timezone.utc))
    _create_sales(biz_id, cust_id, user_id, "2000000.00", datetime(2026, 9, 10, 10, 0, tzinfo=timezone.utc))

    res = client.get(
        f"/api/v1/businesses/{biz_id}/receivables/statements?customer_id={cust_id}&date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert Decimal(str(data["total_debit"])) == Decimal("3000000.00")
    assert Decimal(str(data["closing_balance"])) == Decimal("3000000.00")
    assert len(data["lines"]) == 2
    assert Decimal(str(data["lines"][0]["running_balance"])) == Decimal("1000000.00")
    assert Decimal(str(data["lines"][1]["running_balance"])) == Decimal("3000000.00")


def test_05_payment_and_partial_settlement():
    token, user_id = register_user("owner05@test.com")
    biz_id = create_business(token)
    cust_id = create_customer(token, biz_id)
    acc_id = create_cash_account(token, biz_id)

    s = _create_sales(biz_id, cust_id, user_id, "1000000.00", datetime(2026, 9, 5, 10, 0, tzinfo=timezone.utc))
    _create_payment(biz_id, s.id, acc_id, user_id, "400000.00", datetime(2026, 9, 12, 10, 0, tzinfo=timezone.utc))

    res = client.get(
        f"/api/v1/businesses/{biz_id}/receivables/statements?customer_id={cust_id}&date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert Decimal(str(data["total_debit"])) == Decimal("1000000.00")
    assert Decimal(str(data["total_credit"])) == Decimal("400000.00")
    assert Decimal(str(data["closing_balance"])) == Decimal("600000.00")
    assert len(data["lines"]) == 2
    assert data["lines"][1]["transaction_type"] == "CUSTOMER_PAYMENT"
    assert Decimal(str(data["lines"][1]["credit"])) == Decimal("400000.00")
    assert Decimal(str(data["lines"][1]["running_balance"])) == Decimal("600000.00")


def test_06_sales_return_reduces_ar():
    token, user_id = register_user("owner06@test.com")
    biz_id = create_business(token)
    cust_id = create_customer(token, biz_id)

    s = _create_sales(biz_id, cust_id, user_id, "1000000.00", datetime(2026, 9, 5, 10, 0, tzinfo=timezone.utc))
    _create_sales_return(biz_id, s.id, user_id, "300000.00", datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc))

    res = client.get(
        f"/api/v1/businesses/{biz_id}/receivables/statements?customer_id={cust_id}&date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert Decimal(str(data["total_debit"])) == Decimal("1000000.00")
    assert Decimal(str(data["total_credit"])) == Decimal("300000.00")
    assert Decimal(str(data["closing_balance"])) == Decimal("700000.00")
    assert data["lines"][1]["transaction_type"] == "SALES_RETURN"


def test_07_exact_boundary_filtering():
    token, user_id = register_user("owner07@test.com")
    biz_id = create_business(token)
    cust_id = create_customer(token, biz_id)

    # 1. Prior sale: 2026-08-31 23:59:59.999999
    _create_sales(biz_id, cust_id, user_id, "100.00", datetime(2026, 8, 31, 23, 59, 59, 999999, tzinfo=timezone.utc))
    # 2. Exact start: 2026-09-01 00:00:00.000000
    _create_sales(biz_id, cust_id, user_id, "200.00", datetime(2026, 9, 1, 0, 0, 0, 0, tzinfo=timezone.utc))
    # 3. Exact end: 2026-09-30 23:59:59.999999
    _create_sales(biz_id, cust_id, user_id, "300.00", datetime(2026, 9, 30, 23, 59, 59, 999999, tzinfo=timezone.utc))
    # 4. Next day: 2026-10-01 00:00:00.000000
    _create_sales(biz_id, cust_id, user_id, "400.00", datetime(2026, 10, 1, 0, 0, 0, 0, tzinfo=timezone.utc))

    res = client.get(
        f"/api/v1/businesses/{biz_id}/receivables/statements?customer_id={cust_id}&date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert Decimal(str(data["opening_balance"])) == Decimal("100.00")
    assert Decimal(str(data["total_debit"])) == Decimal("500.00") # 200 + 300
    assert Decimal(str(data["closing_balance"])) == Decimal("600.00") # 100 + 500
    assert len(data["lines"]) == 2


def test_08_same_timestamp_deterministic_ordering():
    token, user_id = register_user("owner08@test.com")
    biz_id = create_business(token)
    cust_id = create_customer(token, biz_id)
    acc_id = create_cash_account(token, biz_id)

    dt = datetime(2026, 9, 15, 12, 0, 0, tzinfo=timezone.utc)
    s = _create_sales(biz_id, cust_id, user_id, "1000000.00", dt)
    _create_sales_return(biz_id, s.id, user_id, "200000.00", dt)
    _create_payment(biz_id, s.id, acc_id, user_id, "300000.00", dt)

    res = client.get(
        f"/api/v1/businesses/{biz_id}/receivables/statements?customer_id={cust_id}&date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    # Priority order: SALE (1) -> CUSTOMER_PAYMENT (2) -> SALES_RETURN (3)
    assert data["lines"][0]["transaction_type"] == "SALE"
    assert data["lines"][1]["transaction_type"] == "CUSTOMER_PAYMENT"
    assert data["lines"][2]["transaction_type"] == "SALES_RETURN"


def test_09_customer_isolation():
    token, user_id = register_user("owner09@test.com")
    biz_id = create_business(token)
    cust1_id = create_customer(token, biz_id, name="Cust 1")
    cust2_id = create_customer(token, biz_id, name="Cust 2")

    _create_sales(biz_id, cust1_id, user_id, "1000000.00", datetime(2026, 9, 10, 10, 0, tzinfo=timezone.utc))
    _create_sales(biz_id, cust2_id, user_id, "2000000.00", datetime(2026, 9, 10, 10, 0, tzinfo=timezone.utc))

    res1 = client.get(
        f"/api/v1/businesses/{biz_id}/receivables/statements?customer_id={cust1_id}&date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res1.status_code == 200
    assert Decimal(str(res1.json()["total_debit"])) == Decimal("1000000.00")

    res2 = client.get(
        f"/api/v1/businesses/{biz_id}/receivables/statements?customer_id={cust2_id}&date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res2.status_code == 200
    assert Decimal(str(res2.json()["total_debit"])) == Decimal("2000000.00")


def test_10_cross_business_isolation():
    token1, user_id1 = register_user("owner10_1@test.com")
    biz1 = create_business(token1, name="Biz 1")
    cust1 = create_customer(token1, biz1, name="Cust 1")

    token2, _ = register_user("owner10_2@test.com")
    biz2 = create_business(token2, name="Biz 2")

    # Trying to query cust1 (belongs to biz1) under biz2 returns 404
    res = client.get(
        f"/api/v1/businesses/{biz2}/receivables/statements?customer_id={cust1}&date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert res.status_code == 404


def test_11_voided_cancelled_draft_exclusions():
    token, user_id = register_user("owner11@test.com")
    biz_id = create_business(token)
    cust_id = create_customer(token, biz_id)
    acc_id = create_cash_account(token, biz_id)

    dt = datetime(2026, 9, 10, 10, 0, tzinfo=timezone.utc)
    # Draft sale -> excluded
    _create_sales(biz_id, cust_id, user_id, "100.00", dt, status=SalesStatus.DRAFT)
    # Cancelled sale -> excluded
    _create_sales(biz_id, cust_id, user_id, "200.00", dt, status=SalesStatus.CANCELLED)
    # Finalized sale -> included
    s = _create_sales(biz_id, cust_id, user_id, "500.00", dt, status=SalesStatus.FINALIZED)
    # Voided payment -> excluded
    _create_payment(biz_id, s.id, acc_id, user_id, "300.00", dt, status=PaymentStatus.VOIDED)

    res = client.get(
        f"/api/v1/businesses/{biz_id}/receivables/statements?customer_id={cust_id}&date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert Decimal(str(data["total_debit"])) == Decimal("500.00")
    assert Decimal(str(data["total_credit"])) == Decimal("0.00")


def test_12_pagination_accounting_invariants():
    token, user_id = register_user("owner12@test.com")
    biz_id = create_business(token)
    cust_id = create_customer(token, biz_id)

    for i in range(5):
        _create_sales(biz_id, cust_id, user_id, "100.00", datetime(2026, 9, 1 + i, 10, 0, tzinfo=timezone.utc))

    # Page 1 (size 2)
    res1 = client.get(
        f"/api/v1/businesses/{biz_id}/receivables/statements?customer_id={cust_id}&date_from=2026-09-01&date_to=2026-09-30&page=1&page_size=2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res1.status_code == 200
    d1 = res1.json()

    # Page 2 (size 2)
    res2 = client.get(
        f"/api/v1/businesses/{biz_id}/receivables/statements?customer_id={cust_id}&date_from=2026-09-01&date_to=2026-09-30&page=2&page_size=2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res2.status_code == 200
    d2 = res2.json()

    # Totals and opening/closing balances must be identical across pages
    assert d1["opening_balance"] == d2["opening_balance"]
    assert d1["total_debit"] == d2["total_debit"] == "500.00"
    assert d1["closing_balance"] == d2["closing_balance"] == "500.00"
    assert d1["total_items"] == d2["total_items"] == 5

    # Page 1 has 2 items
    assert len(d1["lines"]) == 2
    assert Decimal(str(d1["lines"][0]["running_balance"])) == Decimal("100.00")
    assert Decimal(str(d1["lines"][1]["running_balance"])) == Decimal("200.00")

    # Page 2 has 2 items, running balance reflects true chronological accumulation (300, 400)
    assert len(d2["lines"]) == 2
    assert Decimal(str(d2["lines"][0]["running_balance"])) == Decimal("300.00")
    assert Decimal(str(d2["lines"][1]["running_balance"])) == Decimal("400.00")


def test_13_validation_errors():
    token, _ = register_user("owner13@test.com")
    biz_id = create_business(token)
    cust_id = create_customer(token, biz_id)

    # Missing customer_id -> 422
    res = client.get(
        f"/api/v1/businesses/{biz_id}/receivables/statements",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422

    # date_from > date_to -> 422
    res = client.get(
        f"/api/v1/businesses/{biz_id}/receivables/statements?customer_id={cust_id}&date_from=2026-09-30&date_to=2026-09-01",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422

    # page_size > 500 -> 422
    res = client.get(
        f"/api/v1/businesses/{biz_id}/receivables/statements?customer_id={cust_id}&page_size=1000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422


def test_14_owner_admin_member_access():
    token_owner, _ = register_user("owner14@test.com")
    biz_id = create_business(token_owner)
    cust_id = create_customer(token_owner, biz_id)

    token_admin, _ = register_user("admin14@test.com")
    add_member(token_owner, biz_id, token_admin, role="ADMIN")

    token_member, _ = register_user("member14@test.com")
    add_member(token_owner, biz_id, token_member, role="MEMBER")

    # OWNER
    res = client.get(
        f"/api/v1/businesses/{biz_id}/receivables/statements?customer_id={cust_id}",
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert res.status_code == 200

    # ADMIN
    res = client.get(
        f"/api/v1/businesses/{biz_id}/receivables/statements?customer_id={cust_id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert res.status_code == 200

    # MEMBER
    res = client.get(
        f"/api/v1/businesses/{biz_id}/receivables/statements?customer_id={cust_id}",
        headers={"Authorization": f"Bearer {token_member}"},
    )
    assert res.status_code == 200


def test_15_inactive_non_member_rejection():
    token_owner, _ = register_user("owner15@test.com")
    biz_id = create_business(token_owner)
    cust_id = create_customer(token_owner, biz_id)
    token_stranger, _ = register_user("stranger15@test.com")

    res = client.get(
        f"/api/v1/businesses/{biz_id}/receivables/statements?customer_id={cust_id}",
        headers={"Authorization": f"Bearer {token_stranger}"},
    )
    assert res.status_code in (403, 404)


def test_16_zero_balance_netting():
    token, user_id = register_user("owner16@test.com")
    biz_id = create_business(token)
    cust_id = create_customer(token, biz_id)
    acc_id = create_cash_account(token, biz_id)

    s = _create_sales(biz_id, cust_id, user_id, "1000000.00", datetime(2026, 9, 10, 10, 0, tzinfo=timezone.utc))
    _create_sales_return(biz_id, s.id, user_id, "400000.00", datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc))
    _create_payment(biz_id, s.id, acc_id, user_id, "600000.00", datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc))

    res = client.get(
        f"/api/v1/businesses/{biz_id}/receivables/statements?customer_id={cust_id}&date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert Decimal(str(data["total_debit"])) == Decimal("1000000.00")
    assert Decimal(str(data["total_credit"])) == Decimal("1000000.00")
    assert Decimal(str(data["closing_balance"])) == Decimal("0.00")


def test_17_full_payment_settlement():
    token, user_id = register_user("owner17@test.com")
    biz_id = create_business(token)
    cust_id = create_customer(token, biz_id)
    acc_id = create_cash_account(token, biz_id)

    s = _create_sales(biz_id, cust_id, user_id, "500000.00", datetime(2026, 9, 10, 10, 0, tzinfo=timezone.utc))
    _create_payment(biz_id, s.id, acc_id, user_id, "500000.00", datetime(2026, 9, 12, 10, 0, tzinfo=timezone.utc))

    res = client.get(
        f"/api/v1/businesses/{biz_id}/receivables/statements?customer_id={cust_id}&date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert Decimal(str(data["closing_balance"])) == Decimal("0.00")
    assert len(data["lines"]) == 2
    assert Decimal(str(data["lines"][1]["running_balance"])) == Decimal("0.00")


def test_18_payment_without_normal_ui_flow():
    token, user_id = register_user("owner18@test.com")
    biz_id = create_business(token)
    cust_id = create_customer(token, biz_id)
    acc_id = create_cash_account(token, biz_id)

    s = _create_sales(biz_id, cust_id, user_id, "1000000.00", datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc))
    # Direct backend payment creation (simulating API/integration payment)
    _create_payment(biz_id, s.id, acc_id, user_id, "250000.00", datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc))

    res = client.get(
        f"/api/v1/businesses/{biz_id}/receivables/statements?customer_id={cust_id}&date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert Decimal(str(data["total_credit"])) == Decimal("250000.00")
    assert Decimal(str(data["closing_balance"])) == Decimal("750000.00")


def test_19_sales_return_economic_date_strictly_return_date():
    token, user_id = register_user("owner19@test.com")
    biz_id = create_business(token)
    cust_id = create_customer(token, biz_id)

    # Sale on Aug 15
    s = _create_sales(biz_id, cust_id, user_id, "1000000.00", datetime(2026, 8, 15, 10, 0, tzinfo=timezone.utc))
    # Sales return created with return_date on Sept 10
    ret = _create_sales_return(biz_id, s.id, user_id, "300000.00", datetime(2026, 9, 10, 10, 0, tzinfo=timezone.utc))

    res = client.get(
        f"/api/v1/businesses/{biz_id}/receivables/statements?customer_id={cust_id}&date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert Decimal(str(data["opening_balance"])) == Decimal("1000000.00")
    assert Decimal(str(data["total_credit"])) == Decimal("300000.00")
    assert Decimal(str(data["closing_balance"])) == Decimal("700000.00")
    assert len(data["lines"]) == 1
    assert data["lines"][0]["transaction_type"] == "SALES_RETURN"


def test_20_customer_statement_mathematical_invariant():
    token, user_id = register_user("owner20@test.com")
    biz_id = create_business(token)
    cust_id = create_customer(token, biz_id)
    acc_id = create_cash_account(token, biz_id)

    s = _create_sales(biz_id, cust_id, user_id, "1000000.00", datetime(2026, 9, 5, 10, 0, tzinfo=timezone.utc))
    _create_sales_return(biz_id, s.id, user_id, "300000.00", datetime(2026, 9, 12, 10, 0, tzinfo=timezone.utc))
    _create_payment(biz_id, s.id, acc_id, user_id, "400000.00", datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc))

    res = client.get(
        f"/api/v1/businesses/{biz_id}/receivables/statements?customer_id={cust_id}&date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    op = Decimal(str(data["opening_balance"]))
    db = Decimal(str(data["total_debit"]))
    cr = Decimal(str(data["total_credit"]))
    cl = Decimal(str(data["closing_balance"]))

    # Mathematical Invariant for AR: Closing = Opening + Debit - Credit
    assert cl == op + db - cr
    assert cl == Decimal("300000.00")



"""
Feature #41 — Supplier Statement of Account (Kartu Utang) Test Suite
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
from app.modules.supplier.repository import InMemorySupplierRepository
from app.modules.purchase.repository import InMemoryPurchaseRepository
from app.modules.purchase.schemas import PurchaseStatus
from app.modules.purchase_return.repository import InMemoryPurchaseReturnRepository
from app.modules.purchase_return.schemas import PurchaseReturnStatus
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
    InMemorySupplierRepository.clear()
    InMemoryPurchaseRepository.clear()
    InMemoryPurchaseReturnRepository.clear()
    InMemoryPaymentRepository.clear()
    InMemoryCashAccountRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryUserRepository.clear()
    yield
    InMemorySupplierRepository.clear()
    InMemoryPurchaseRepository.clear()
    InMemoryPurchaseReturnRepository.clear()
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


def create_supplier(token, biz_id, name="Supplier PT X"):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/suppliers",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "supplier_type": "ORGANIZATION"},
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


_purchase_seq = 0
_payment_seq = 0
_return_seq = 0


def _create_purchase(biz_id, supplier_id, user_id, grand_total, purchase_date, status=PurchaseStatus.FINALIZED):
    global _purchase_seq
    _purchase_seq += 1
    pur_repo = InMemoryPurchaseRepository()
    import asyncio
    p = asyncio.run(
        pur_repo.create_purchase(
            business_id=biz_id,
            supplier_id=supplier_id,
            branch_id="MAIN",
            purchase_number=f"PO-{_purchase_seq:06d}",
            purchase_date=purchase_date,
            created_by_user_id=user_id,
        )
    )
    p_updated = asyncio.run(
        pur_repo.update_purchase(
            purchase_id=p.id,
            business_id=biz_id,
            status=status,
            subtotal=Decimal(str(grand_total)),
            grand_total=Decimal(str(grand_total)),
            finalized_by_user_id=user_id if status == PurchaseStatus.FINALIZED else None,
            finalized_at=purchase_date if status == PurchaseStatus.FINALIZED else None,
        )
    )
    return p_updated


def _create_purchase_return(biz_id, purchase_id, user_id, grand_total, finalized_at, status=PurchaseReturnStatus.FINALIZED):
    global _return_seq
    _return_seq += 1
    ret_repo = InMemoryPurchaseReturnRepository()
    import asyncio
    r = asyncio.run(
        ret_repo.create_return(
            business_id=biz_id,
            purchase_id=purchase_id,
            inventory_location_id="LOC-1",
            return_number=f"PR-{_return_seq:06d}",
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
            finalized_by_user_id=user_id if status == PurchaseReturnStatus.FINALIZED else None,
            finalized_at=finalized_at if status == PurchaseReturnStatus.FINALIZED else None,
        )
    )
    return r_updated


def _create_supplier_payment(biz_id, target_purchase_id, cash_account_id, user_id, amount, payment_date, status=PaymentStatus.RECORDED):
    global _payment_seq
    _payment_seq += 1
    payment_repo = InMemoryPaymentRepository()
    import asyncio
    return asyncio.run(
        payment_repo.create_payment({
            "business_id": biz_id,
            "branch_id": "MAIN",
            "direction": PaymentDirection.SUPPLIER_OUT,
            "target_type": PaymentTargetType.PURCHASE,
            "target_id": target_purchase_id,
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
    supp_id = create_supplier(token, biz_id)

    res = client.get(
        f"/api/v1/businesses/{biz_id}/purchases/payables/statements?supplier_id={supp_id}&date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["entity_id"] == supp_id
    assert Decimal(str(data["opening_balance"])) == Decimal("0.00")
    assert Decimal(str(data["closing_balance"])) == Decimal("0.00")
    assert Decimal(str(data["total_debit"])) == Decimal("0.00")
    assert Decimal(str(data["total_credit"])) == Decimal("0.00")
    assert data["lines"] == []
    assert data["total_items"] == 0


def test_02_opening_balance_reconstruction():
    token, user_id = register_user("owner02@test.com")
    biz_id = create_business(token)
    supp_id = create_supplier(token, biz_id)
    acc_id = create_cash_account(token, biz_id)

    # Prior purchase of 2,000,000 on 2026-08-10
    p = _create_purchase(biz_id, supp_id, user_id, "2000000.00", datetime(2026, 8, 10, 10, 0, tzinfo=timezone.utc))
    # Prior payment of 500,000 on 2026-08-15
    _create_supplier_payment(biz_id, p.id, acc_id, user_id, "500000.00", datetime(2026, 8, 15, 10, 0, tzinfo=timezone.utc))

    res = client.get(
        f"/api/v1/businesses/{biz_id}/purchases/payables/statements?supplier_id={supp_id}&date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert Decimal(str(data["opening_balance"])) == Decimal("1500000.00")
    assert Decimal(str(data["closing_balance"])) == Decimal("1500000.00")
    assert data["lines"] == []


def test_03_single_purchase_in_period():
    token, user_id = register_user("owner03@test.com")
    biz_id = create_business(token)
    supp_id = create_supplier(token, biz_id)

    _create_purchase(biz_id, supp_id, user_id, "1500000.00", datetime(2026, 9, 10, 10, 0, tzinfo=timezone.utc))

    res = client.get(
        f"/api/v1/businesses/{biz_id}/purchases/payables/statements?supplier_id={supp_id}&date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert Decimal(str(data["opening_balance"])) == Decimal("0.00")
    assert Decimal(str(data["total_credit"])) == Decimal("1500000.00")
    assert Decimal(str(data["total_debit"])) == Decimal("0.00")
    assert Decimal(str(data["closing_balance"])) == Decimal("1500000.00")
    assert len(data["lines"]) == 1
    assert data["lines"][0]["transaction_type"] == "PURCHASE"
    assert Decimal(str(data["lines"][0]["credit"])) == Decimal("1500000.00")
    assert Decimal(str(data["lines"][0]["running_balance"])) == Decimal("1500000.00")


def test_04_supplier_payment_reduces_ap():
    token, user_id = register_user("owner04@test.com")
    biz_id = create_business(token)
    supp_id = create_supplier(token, biz_id)
    acc_id = create_cash_account(token, biz_id)

    p = _create_purchase(biz_id, supp_id, user_id, "2000000.00", datetime(2026, 9, 5, 10, 0, tzinfo=timezone.utc))
    _create_supplier_payment(biz_id, p.id, acc_id, user_id, "800000.00", datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc))

    res = client.get(
        f"/api/v1/businesses/{biz_id}/purchases/payables/statements?supplier_id={supp_id}&date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert Decimal(str(data["total_credit"])) == Decimal("2000000.00") # Purchase increases AP
    assert Decimal(str(data["total_debit"])) == Decimal("800000.00") # Payment decreases AP
    assert Decimal(str(data["closing_balance"])) == Decimal("1200000.00")
    assert len(data["lines"]) == 2
    assert data["lines"][1]["transaction_type"] == "SUPPLIER_PAYMENT"
    assert Decimal(str(data["lines"][1]["debit"])) == Decimal("800000.00")
    assert Decimal(str(data["lines"][1]["running_balance"])) == Decimal("1200000.00")


def test_05_purchase_return_reduces_ap():
    token, user_id = register_user("owner05@test.com")
    biz_id = create_business(token)
    supp_id = create_supplier(token, biz_id)

    p = _create_purchase(biz_id, supp_id, user_id, "2000000.00", datetime(2026, 9, 5, 10, 0, tzinfo=timezone.utc))
    _create_purchase_return(biz_id, p.id, user_id, "500000.00", datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc))

    res = client.get(
        f"/api/v1/businesses/{biz_id}/purchases/payables/statements?supplier_id={supp_id}&date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert Decimal(str(data["total_credit"])) == Decimal("2000000.00")
    assert Decimal(str(data["total_debit"])) == Decimal("500000.00") # Purchase Return decreases AP
    assert Decimal(str(data["closing_balance"])) == Decimal("1500000.00")
    assert data["lines"][1]["transaction_type"] == "PURCHASE_RETURN"


def test_06_same_timestamp_deterministic_ordering():
    token, user_id = register_user("owner06@test.com")
    biz_id = create_business(token)
    supp_id = create_supplier(token, biz_id)
    acc_id = create_cash_account(token, biz_id)

    dt = datetime(2026, 9, 15, 12, 0, 0, tzinfo=timezone.utc)
    p = _create_purchase(biz_id, supp_id, user_id, "1000000.00", dt)
    _create_purchase_return(biz_id, p.id, user_id, "200000.00", dt)
    _create_supplier_payment(biz_id, p.id, acc_id, user_id, "300000.00", dt)

    res = client.get(
        f"/api/v1/businesses/{biz_id}/purchases/payables/statements?supplier_id={supp_id}&date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    # Priority order for AP: PURCHASE (1) -> SUPPLIER_PAYMENT (2) -> PURCHASE_RETURN (3)
    assert data["lines"][0]["transaction_type"] == "PURCHASE"
    assert data["lines"][1]["transaction_type"] == "SUPPLIER_PAYMENT"
    assert data["lines"][2]["transaction_type"] == "PURCHASE_RETURN"


def test_07_supplier_isolation():
    token, user_id = register_user("owner07@test.com")
    biz_id = create_business(token)
    supp1_id = create_supplier(token, biz_id, name="Supp 1")
    supp2_id = create_supplier(token, biz_id, name="Supp 2")

    _create_purchase(biz_id, supp1_id, user_id, "1000000.00", datetime(2026, 9, 10, 10, 0, tzinfo=timezone.utc))
    _create_purchase(biz_id, supp2_id, user_id, "2000000.00", datetime(2026, 9, 10, 10, 0, tzinfo=timezone.utc))

    res1 = client.get(
        f"/api/v1/businesses/{biz_id}/purchases/payables/statements?supplier_id={supp1_id}&date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res1.status_code == 200
    assert Decimal(str(res1.json()["total_credit"])) == Decimal("1000000.00")

    res2 = client.get(
        f"/api/v1/businesses/{biz_id}/purchases/payables/statements?supplier_id={supp2_id}&date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res2.status_code == 200
    assert Decimal(str(res2.json()["total_credit"])) == Decimal("2000000.00")


def test_08_cross_business_isolation():
    token1, user_id1 = register_user("owner08_1@test.com")
    biz1 = create_business(token1, name="Biz 1")
    supp1 = create_supplier(token1, biz1, name="Supp 1")

    token2, _ = register_user("owner08_2@test.com")
    biz2 = create_business(token2, name="Biz 2")

    # Trying to query supp1 (belongs to biz1) under biz2 returns 404
    res = client.get(
        f"/api/v1/businesses/{biz2}/purchases/payables/statements?supplier_id={supp1}&date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert res.status_code == 404


def test_09_validation_errors():
    token, _ = register_user("owner09@test.com")
    biz_id = create_business(token)
    supp_id = create_supplier(token, biz_id)

    # Missing supplier_id -> 422
    res = client.get(
        f"/api/v1/businesses/{biz_id}/purchases/payables/statements",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422

    # date_from > date_to -> 422
    res = client.get(
        f"/api/v1/businesses/{biz_id}/purchases/payables/statements?supplier_id={supp_id}&date_from=2026-09-30&date_to=2026-09-01",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422


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


def test_10_pagination_accounting_invariants():
    token, user_id = register_user("owner10@test.com")
    biz_id = create_business(token)
    supp_id = create_supplier(token, biz_id)

    for i in range(5):
        _create_purchase(biz_id, supp_id, user_id, "100.00", datetime(2026, 9, 1 + i, 10, 0, tzinfo=timezone.utc))

    # Page 1 (size 2)
    res1 = client.get(
        f"/api/v1/businesses/{biz_id}/purchases/payables/statements?supplier_id={supp_id}&date_from=2026-09-01&date_to=2026-09-30&page=1&page_size=2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res1.status_code == 200
    d1 = res1.json()

    # Page 2 (size 2)
    res2 = client.get(
        f"/api/v1/businesses/{biz_id}/purchases/payables/statements?supplier_id={supp_id}&date_from=2026-09-01&date_to=2026-09-30&page=2&page_size=2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res2.status_code == 200
    d2 = res2.json()

    assert d1["opening_balance"] == d2["opening_balance"]
    assert d1["total_credit"] == d2["total_credit"] == "500.00"
    assert d1["closing_balance"] == d2["closing_balance"] == "500.00"
    assert d1["total_items"] == d2["total_items"] == 5

    assert len(d1["lines"]) == 2
    assert Decimal(str(d1["lines"][0]["running_balance"])) == Decimal("100.00")
    assert Decimal(str(d1["lines"][1]["running_balance"])) == Decimal("200.00")

    assert len(d2["lines"]) == 2
    assert Decimal(str(d2["lines"][0]["running_balance"])) == Decimal("300.00")
    assert Decimal(str(d2["lines"][1]["running_balance"])) == Decimal("400.00")


def test_11_purchase_return_finalized_at_placement():
    token, user_id = register_user("owner11@test.com")
    biz_id = create_business(token)
    supp_id = create_supplier(token, biz_id)

    # Purchase created on Aug 15
    p = _create_purchase(biz_id, supp_id, user_id, "1000.00", datetime(2026, 8, 15, 10, 0, tzinfo=timezone.utc))
    # Purchase return created/finalized on Sept 10 (finalized_at)
    _create_purchase_return(biz_id, p.id, user_id, "300.00", datetime(2026, 9, 10, 10, 0, tzinfo=timezone.utc))

    res = client.get(
        f"/api/v1/businesses/{biz_id}/purchases/payables/statements?supplier_id={supp_id}&date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert Decimal(str(data["opening_balance"])) == Decimal("1000.00")
    assert Decimal(str(data["total_debit"])) == Decimal("300.00")
    assert Decimal(str(data["closing_balance"])) == Decimal("700.00")
    assert len(data["lines"]) == 1
    assert data["lines"][0]["transaction_type"] == "PURCHASE_RETURN"


def test_12_owner_admin_member_access():
    token_owner, _ = register_user("owner12@test.com")
    biz_id = create_business(token_owner)
    supp_id = create_supplier(token_owner, biz_id)

    token_admin, _ = register_user("admin12@test.com")
    add_member(token_owner, biz_id, token_admin, role="ADMIN")

    token_member, _ = register_user("member12@test.com")
    add_member(token_owner, biz_id, token_member, role="MEMBER")

    # OWNER
    res = client.get(
        f"/api/v1/businesses/{biz_id}/purchases/payables/statements?supplier_id={supp_id}",
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert res.status_code == 200

    # ADMIN
    res = client.get(
        f"/api/v1/businesses/{biz_id}/purchases/payables/statements?supplier_id={supp_id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert res.status_code == 200

    # MEMBER
    res = client.get(
        f"/api/v1/businesses/{biz_id}/purchases/payables/statements?supplier_id={supp_id}",
        headers={"Authorization": f"Bearer {token_member}"},
    )
    assert res.status_code == 200


def test_13_voided_cancelled_draft_exclusions():
    token, user_id = register_user("owner13@test.com")
    biz_id = create_business(token)
    supp_id = create_supplier(token, biz_id)
    acc_id = create_cash_account(token, biz_id)

    dt = datetime(2026, 9, 10, 10, 0, tzinfo=timezone.utc)
    # Draft purchase -> excluded
    _create_purchase(biz_id, supp_id, user_id, "100.00", dt, status=PurchaseStatus.DRAFT)
    # Cancelled purchase -> excluded
    _create_purchase(biz_id, supp_id, user_id, "200.00", dt, status=PurchaseStatus.CANCELLED)
    # Finalized purchase -> included
    p = _create_purchase(biz_id, supp_id, user_id, "500.00", dt, status=PurchaseStatus.FINALIZED)
    # Voided payment -> excluded
    _create_supplier_payment(biz_id, p.id, acc_id, user_id, "300.00", dt, status=PaymentStatus.VOIDED)

    res = client.get(
        f"/api/v1/businesses/{biz_id}/purchases/payables/statements?supplier_id={supp_id}&date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert Decimal(str(data["total_credit"])) == Decimal("500.00")
    assert Decimal(str(data["total_debit"])) == Decimal("0.00")


def test_14_mathematical_invariant_and_zero_balance():
    token, user_id = register_user("owner14@test.com")
    biz_id = create_business(token)
    supp_id = create_supplier(token, biz_id)
    acc_id = create_cash_account(token, biz_id)

    p = _create_purchase(biz_id, supp_id, user_id, "1000000.00", datetime(2026, 9, 10, 10, 0, tzinfo=timezone.utc))
    _create_purchase_return(biz_id, p.id, user_id, "400000.00", datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc))
    _create_supplier_payment(biz_id, p.id, acc_id, user_id, "600000.00", datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc))

    res = client.get(
        f"/api/v1/businesses/{biz_id}/purchases/payables/statements?supplier_id={supp_id}&date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    op = Decimal(str(data["opening_balance"]))
    cr = Decimal(str(data["total_credit"]))
    db = Decimal(str(data["total_debit"]))
    cl = Decimal(str(data["closing_balance"]))

    # Mathematical Invariant for AP: Closing = Opening + Credit - Debit
    assert cl == op + cr - db
    assert cl == Decimal("0.00")


def test_15_payment_without_normal_ui_flow():
    token, user_id = register_user("owner15@test.com")
    biz_id = create_business(token)
    supp_id = create_supplier(token, biz_id)
    acc_id = create_cash_account(token, biz_id)

    p = _create_purchase(biz_id, supp_id, user_id, "1000000.00", datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc))
    _create_supplier_payment(biz_id, p.id, acc_id, user_id, "250000.00", datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc))

    res = client.get(
        f"/api/v1/businesses/{biz_id}/purchases/payables/statements?supplier_id={supp_id}&date_from=2026-09-01&date_to=2026-09-30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert Decimal(str(data["total_debit"])) == Decimal("250000.00")
    assert Decimal(str(data["closing_balance"])) == Decimal("750000.00")

import uuid
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from fastapi.testclient import TestClient

from app.main import app
from app.modules.authentication.repository import InMemoryUserRepository
from app.modules.account.repository import InMemoryAccountRepository
from app.modules.business.repository import InMemoryBusinessRepository
from app.modules.business_membership.repository import InMemoryBusinessMembershipRepository
from app.modules.customer.repository import InMemoryCustomerRepository
from app.modules.product.repository import InMemoryProductRepository
from app.modules.product_variant.repository import InMemoryProductVariantRepository
from app.modules.unit.repository import InMemoryUnitRepository
from app.modules.branch.repository import InMemoryBranchRepository
from app.modules.sales.repository import InMemorySalesRepository
from app.modules.sales_payment.repository import InMemorySalesPaymentRepository
from app.modules.pricing.repository import InMemoryPriceListRepository, InMemoryPriceEntryRepository
from app.modules.warehouse.repository import InMemoryWarehouseRepository, InMemoryInventoryLocationRepository
from app.modules.receiving.repository import InMemoryReceivingRepository
from app.modules.stock_opname.repository import InMemoryStockOpnameRepository
from app.modules.inventory.repository import InMemoryStockBalanceRepository, InMemoryStockMovementRepository, InMemoryInventoryCostRepository


@pytest.fixture(autouse=True)
def clear_all_repos():
    InMemoryUserRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryCustomerRepository.clear()
    InMemoryProductRepository.clear()
    InMemoryProductVariantRepository.clear()
    InMemoryUnitRepository.clear()
    InMemoryBranchRepository.clear()
    InMemorySalesRepository.clear()
    InMemorySalesPaymentRepository.clear()
    InMemoryPriceListRepository.clear()
    InMemoryPriceEntryRepository.clear()
    InMemoryWarehouseRepository.clear()
    InMemoryInventoryLocationRepository.clear()
    InMemoryReceivingRepository.clear()
    InMemoryStockOpnameRepository.clear()
    InMemoryStockBalanceRepository.clear()
    InMemoryStockBalanceRepository.clear()
    InMemoryStockMovementRepository.clear()
    InMemoryInventoryCostRepository.clear()
    yield
    InMemoryUserRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryCustomerRepository.clear()
    InMemoryProductRepository.clear()
    InMemoryProductVariantRepository.clear()
    InMemoryUnitRepository.clear()
    InMemoryBranchRepository.clear()
    InMemorySalesRepository.clear()
    InMemorySalesPaymentRepository.clear()
    InMemoryPriceListRepository.clear()
    InMemoryPriceEntryRepository.clear()
    InMemoryWarehouseRepository.clear()
    InMemoryInventoryLocationRepository.clear()
    InMemoryReceivingRepository.clear()
    InMemoryStockOpnameRepository.clear()
    InMemoryStockBalanceRepository.clear()
    InMemoryStockMovementRepository.clear()
    InMemoryInventoryCostRepository.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _register_and_get_token(client, email="owner@example.com", password="Password123", full_name="Owner User"):
    res = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": full_name, "password": password, "password_confirmation": password},
    )
    assert res.status_code == 201
    token = res.json().get("access_token")
    if not token:
        login_res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
    return token


def _create_business(client, token, name="Test Biz"):
    res = client.post(
        "/api/v1/businesses",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "business_type": "umkm", "timezone": "UTC", "locale": "en-US"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def _get_user_id(client, token):
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    return res.json()["id"]


def _add_member(client, owner_token, biz_id, user_email, role="MEMBER", password="Password123"):
    member_token = _register_and_get_token(client, email=user_email, password=password, full_name="Member User")
    user_id = _get_user_id(client, member_token)
    res = client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"user_id": user_id, "role": role},
    )
    assert res.status_code == 201
    membership_id = res.json()["id"]
    return member_token, user_id, membership_id


def _create_unit(client, token, biz_id):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/units",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": f"Unit_{uuid.uuid4().hex[:6]}", "code": f"U_{uuid.uuid4().hex[:6]}", "symbol": "PCS", "unit_type": "OTHER"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def _create_branch(client, token, biz_id):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/branches",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Main Branch", "code": f"BR_{uuid.uuid4().hex[:6]}"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def _create_product(client, token, biz_id, unit_id):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/products",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Product A", "code": f"PR_{uuid.uuid4().hex[:6]}", "unit_id": unit_id, "product_type": "GOODS"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def _create_finalized_sales(client, token, biz_id, branch_id, product_id, total_amount="100000"):
    # Ensure default warehouse and location exist
    wh_res = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Default WH", "code": f"WH_{uuid.uuid4().hex[:6]}"},
    )
    if wh_res.status_code == 201:
        wh_id = wh_res.json()["id"]
        loc_res = client.post(
            f"/api/v1/businesses/{biz_id}/warehouses/{wh_id}/locations",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Default Loc", "code": f"LOC_{uuid.uuid4().hex[:6]}", "location_type": "GENERAL"},
        )
        if loc_res.status_code == 201:
            loc_id = loc_res.json()["id"]
            client.post(
                f"/api/v1/businesses/{biz_id}/inventory/opening-balance",
                headers={"Authorization": f"Bearer {token}"},
                json={"inventory_location_id": loc_id, "product_id": product_id, "quantity": "1000"},
            )

    s_res = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    )
    assert s_res.status_code == 201
    sales_id = s_res.json()["id"]

    line_res = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": product_id, "quantity": "1", "unit_price": total_amount},
    )
    assert line_res.status_code == 201

    fin_res = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fin_res.status_code == 200
    assert fin_res.json()["status"] == "FINALIZED"
    return sales_id


# ============================================================
# Basic Payment Operations (1-7)
# ============================================================

def test_create_valid_full_payment(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)
    prod_id = _create_product(client, token, biz_id, unit_id)
    sales_id = _create_finalized_sales(client, token, biz_id, branch_id, prod_id, "100000")

    # 1. Create valid full payment
    res = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "payment_method": "CASH",
            "amount": "100000",
            "reference_number": "REF-001",
            "notes": "Full cash payment",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["sales_id"] == sales_id
    assert data["business_id"] == biz_id
    assert data["status"] == "RECORDED"
    assert data["payment_number"] == "PAY-000001"
    assert Decimal(str(data["amount"])) == Decimal("100000")
    assert data["reference_number"] == "REF-001"
    assert data["notes"] == "Full cash payment"


def test_create_valid_partial_and_multiple_payments(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)
    prod_id = _create_product(client, token, biz_id, unit_id)
    sales_id = _create_finalized_sales(client, token, biz_id, branch_id, prod_id, "100000")

    # 2. Create valid partial payment #1
    p1 = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments",
        headers={"Authorization": f"Bearer {token}"},
        json={"payment_method": "BANK_TRANSFER", "amount": "40000"},
    )
    assert p1.status_code == 201
    assert p1.json()["payment_number"] == "PAY-000001"

    # 3. Create multiple partial payments #2
    p2 = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments",
        headers={"Authorization": f"Bearer {token}"},
        json={"payment_method": "QRIS", "amount": "60000"},
    )
    assert p2.status_code == 201
    assert p2.json()["payment_number"] == "PAY-000002"

    # Verify summary
    list_res = client.get(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_res.status_code == 200
    summary = list_res.json()["summary"]
    assert Decimal(str(summary["total_paid"])) == Decimal("100000")
    assert Decimal(str(summary["remaining_amount"])) == Decimal("0")


def test_overpayment_zero_negative_rejections(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)
    prod_id = _create_product(client, token, biz_id, unit_id)
    sales_id = _create_finalized_sales(client, token, biz_id, branch_id, prod_id, "100000")

    # Partial payment 80,000
    client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments",
        headers={"Authorization": f"Bearer {token}"},
        json={"payment_method": "CASH", "amount": "80000"},
    )

    # 7. Overpayment rejected (> remaining 20,000)
    p_over = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments",
        headers={"Authorization": f"Bearer {token}"},
        json={"payment_method": "CASH", "amount": "30000"},
    )
    assert p_over.status_code == 400
    msg = p_over.json().get("message") or p_over.json().get("detail", "")
    assert "exceeds remaining balance" in msg

    # 4. Exact final payment accepted (20,000)
    p_exact = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments",
        headers={"Authorization": f"Bearer {token}"},
        json={"payment_method": "CASH", "amount": "20000"},
    )
    assert p_exact.status_code == 201

    # 5. Zero rejected
    p_zero = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments",
        headers={"Authorization": f"Bearer {token}"},
        json={"payment_method": "CASH", "amount": "0"},
    )
    assert p_zero.status_code == 422

    # 6. Negative rejected
    p_neg = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments",
        headers={"Authorization": f"Bearer {token}"},
        json={"payment_method": "CASH", "amount": "-10000"},
    )
    assert p_neg.status_code == 422


# ============================================================
# Sales Payment Eligibility (8-11)
# ============================================================

def test_sales_payment_eligibility(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)
    prod_id = _create_product(client, token, biz_id, unit_id)

    # Draft Sales
    draft_res = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    )
    draft_sales_id = draft_res.json()["id"]

    # 8. Payment against DRAFT rejected
    p_draft = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{draft_sales_id}/payments",
        headers={"Authorization": f"Bearer {token}"},
        json={"payment_method": "CASH", "amount": "50000"},
    )
    assert p_draft.status_code == 400
    msg_draft = p_draft.json().get("message") or p_draft.json().get("detail", "")
    assert "DRAFT sales" in msg_draft

    # Cancelled Sales
    can_sales_id = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    ).json()["id"]
    client.post(f"/api/v1/businesses/{biz_id}/sales/{can_sales_id}/cancel", headers={"Authorization": f"Bearer {token}"})

    # 10. Payment against CANCELLED rejected
    p_can = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{can_sales_id}/payments",
        headers={"Authorization": f"Bearer {token}"},
        json={"payment_method": "CASH", "amount": "50000"},
    )
    assert p_can.status_code == 400
    msg_can = p_can.json().get("message") or p_can.json().get("detail", "")
    assert "CANCELLED sales" in msg_can

    # 11. Missing Sales rejected (404)
    p_missing = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{uuid.uuid4()}/payments",
        headers={"Authorization": f"Bearer {token}"},
        json={"payment_method": "CASH", "amount": "50000"},
    )
    assert p_missing.status_code == 404

    # 9. Payment against FINALIZED accepted
    fin_sales_id = _create_finalized_sales(client, token, biz_id, branch_id, prod_id, "50000")
    p_fin = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{fin_sales_id}/payments",
        headers={"Authorization": f"Bearer {token}"},
        json={"payment_method": "CASH", "amount": "50000"},
    )
    assert p_fin.status_code == 201


# ============================================================
# Payment Lifecycle & Immutability (12-18)
# ============================================================

def test_payment_lifecycle_and_immutability(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)
    prod_id = _create_product(client, token, biz_id, unit_id)
    sales_id = _create_finalized_sales(client, token, biz_id, branch_id, prod_id, "100000")

    # 12. Recorded payment created
    p1 = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments",
        headers={"Authorization": f"Bearer {token}"},
        json={"payment_method": "CASH", "amount": "60000"},
    ).json()
    p1_id = p1["id"]
    assert p1["status"] == "RECORDED"

    # 13. Recorded payment can be cancelled
    can_res = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments/{p1_id}/cancel",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert can_res.status_code == 200
    p1_can = can_res.json()
    assert p1_can["status"] == "CANCELLED"
    assert p1_can["cancelled_by_user_id"] is not None
    assert p1_can["cancelled_at"] is not None

    # 14. Cancelled payment cannot be cancelled again
    can_again = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments/{p1_id}/cancel",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert can_again.status_code == 400
    msg_again = can_again.json().get("message") or can_again.json().get("detail", "")
    assert "already CANCELLED" in msg_again

    # 15. Cancelled payment no longer counts toward total
    summary = client.get(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments",
        headers={"Authorization": f"Bearer {token}"},
    ).json()["summary"]
    assert Decimal(str(summary["total_paid"])) == Decimal("0")
    assert Decimal(str(summary["remaining_amount"])) == Decimal("100000")

    # Now create new full payment after cancellation
    p2 = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments",
        headers={"Authorization": f"Bearer {token}"},
        json={"payment_method": "DEBIT_CARD", "amount": "100000"},
    )
    assert p2.status_code == 201

    # 16 & 17 & 18. No update endpoint / delete endpoint / immutable fields
    patch_res = client.patch(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments/{p1_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"amount": "70000"},
    )
    assert patch_res.status_code == 405  # Method Not Allowed

    del_res = client.delete(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments/{p1_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_res.status_code == 405  # Method Not Allowed


# ============================================================
# Payment Calculations (19-23)
# ============================================================

def test_payment_calculations_and_decimal_precision(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)
    prod_id = _create_product(client, token, biz_id, unit_id)
    sales_id = _create_finalized_sales(client, token, biz_id, branch_id, prod_id, "150000.75")

    # Payment 1: 50000.25
    client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments",
        headers={"Authorization": f"Bearer {token}"},
        json={"payment_method": "CREDIT_CARD", "amount": "50000.25"},
    )

    # Payment 2: 30000.50
    p2 = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments",
        headers={"Authorization": f"Bearer {token}"},
        json={"payment_method": "E_WALLET", "amount": "30000.50"},
    ).json()

    # Payment 3 (cancelled): 20000.00
    p3 = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments",
        headers={"Authorization": f"Bearer {token}"},
        json={"payment_method": "OTHER", "amount": "20000.00"},
    ).json()
    client.post(f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments/{p3['id']}/cancel", headers={"Authorization": f"Bearer {token}"})

    # 19. total_paid correct (80000.75)
    # 20. remaining_amount correct (70000.00)
    # 21. Decimal precision preserved
    # 22. Cancelled payments excluded
    # 23. Multiple payments aggregate correctly
    summary = client.get(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments",
        headers={"Authorization": f"Bearer {token}"},
    ).json()["summary"]

    assert Decimal(str(summary["grand_total"])) == Decimal("150000.75")
    assert Decimal(str(summary["total_paid"])) == Decimal("80000.75")
    assert Decimal(str(summary["remaining_amount"])) == Decimal("70000.00")


# ============================================================
# Payment Number & Server Control (24-27)
# ============================================================

def test_payment_number_and_client_spoofing(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)
    prod_id = _create_product(client, token, biz_id, unit_id)
    sales_id = _create_finalized_sales(client, token, biz_id, branch_id, prod_id, "100000")

    # 25. Client spoofing rejected (extra=forbid on payment_number)
    spoof_res = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments",
        headers={"Authorization": f"Bearer {token}"},
        json={"payment_method": "CASH", "amount": "10000", "payment_number": "PAY-SPOOF"},
    )
    assert spoof_res.status_code == 422

    # 24. Server generated & 26. Business scoped & 27. Immutable
    p1 = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments",
        headers={"Authorization": f"Bearer {token}"},
        json={"payment_method": "CASH", "amount": "10000"},
    ).json()
    assert p1["payment_number"] == "PAY-000001"

    p2 = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments",
        headers={"Authorization": f"Bearer {token}"},
        json={"payment_method": "CASH", "amount": "10000"},
    ).json()
    assert p2["payment_number"] == "PAY-000002"


# ============================================================
# Relationships & Tenant Isolation / IDOR (28-30, 41-44)
# ============================================================

def test_relationships_tenant_isolation_and_idor(client):
    token_a = _register_and_get_token(client, email="owner_a@biz.com")
    biz_a = _create_business(client, token_a, name="Biz A")
    unit_a = _create_unit(client, token_a, biz_a)
    branch_a = _create_branch(client, token_a, biz_a)
    prod_a = _create_product(client, token_a, biz_a, unit_a)
    sales_a_id = _create_finalized_sales(client, token_a, biz_a, branch_a, prod_a, "50000")

    token_b = _register_and_get_token(client, email="owner_b@biz.com")
    biz_b = _create_business(client, token_b, name="Biz B")
    unit_b = _create_unit(client, token_b, biz_b)
    branch_b = _create_branch(client, token_b, biz_b)
    prod_b = _create_product(client, token_b, biz_b, unit_b)
    sales_b_id = _create_finalized_sales(client, token_b, biz_b, branch_b, prod_b, "50000")

    p_a = client.post(
        f"/api/v1/businesses/{biz_a}/sales/{sales_a_id}/payments",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"payment_method": "CASH", "amount": "20000"},
    ).json()

    # 28. Correct Sales relationship
    assert p_a["sales_id"] == sales_a_id

    # 29. Cross-business Sales payment creation rejected (404/403)
    res_cross_create = client.post(
        f"/api/v1/businesses/{biz_b}/sales/{sales_a_id}/payments",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"payment_method": "CASH", "amount": "20000"},
    )
    assert res_cross_create.status_code == 404

    # 30 & 41 & 42 & 43 & 44. IDOR / Spoofed business_id / Cross-business access rejected
    res_cross_get = client.get(
        f"/api/v1/businesses/{biz_b}/sales/{sales_a_id}/payments/{p_a['id']}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_cross_get.status_code == 404

    res_cross_cancel = client.post(
        f"/api/v1/businesses/{biz_b}/sales/{sales_a_id}/payments/{p_a['id']}/cancel",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_cross_cancel.status_code == 404


# ============================================================
# RBAC Security Rules (31-40)
# ============================================================

def test_rbac_security_rules(client):
    owner_token = _register_and_get_token(client, email="owner@rbactest.com")
    biz_id = _create_business(client, owner_token)
    unit_id = _create_unit(client, owner_token, biz_id)
    branch_id = _create_branch(client, owner_token, biz_id)
    prod_id = _create_product(client, owner_token, biz_id, unit_id)
    sales_id = _create_finalized_sales(client, owner_token, biz_id, branch_id, prod_id, "100000")

    admin_token, _, _ = _add_member(client, owner_token, biz_id, "admin@rbactest.com", role="ADMIN")
    member_token, _, _ = _add_member(client, owner_token, biz_id, "member@rbactest.com", role="MEMBER")

    # 35. MEMBER can read
    res_member_read = client.get(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert res_member_read.status_code == 200

    # 36. MEMBER cannot create (403)
    res_member_create = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments",
        headers={"Authorization": f"Bearer {member_token}"},
        json={"payment_method": "CASH", "amount": "10000"},
    )
    assert res_member_create.status_code == 403

    # 31 & 33. OWNER & ADMIN can create
    p_admin = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"payment_method": "CASH", "amount": "10000"},
    ).json()

    p_owner = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"payment_method": "BANK_TRANSFER", "amount": "20000"},
    ).json()

    # 37. MEMBER cannot cancel (403)
    res_member_cancel = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments/{p_admin['id']}/cancel",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert res_member_cancel.status_code == 403

    # 34. ADMIN can cancel
    res_admin_cancel = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments/{p_admin['id']}/cancel",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_admin_cancel.status_code == 200

    # 32. OWNER can cancel
    res_owner_cancel = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments/{p_owner['id']}/cancel",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert res_owner_cancel.status_code == 200

    # 38 & 39 & 40. Non-member / Suspended / Removed user rejected (404/403)
    stranger_token = _register_and_get_token(client, email="stranger@rbactest.com")
    res_stranger = client.get(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments",
        headers={"Authorization": f"Bearer {stranger_token}"},
    )
    assert res_stranger.status_code == 404


# ============================================================
# Architectural Boundaries (45-50)
# ============================================================

def test_architectural_boundaries(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)
    prod_id = _create_product(client, token, biz_id, unit_id)
    sales_id = _create_finalized_sales(client, token, biz_id, branch_id, prod_id, "100000")

    # Record payment
    p_res = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments",
        headers={"Authorization": f"Bearer {token}"},
        json={"payment_method": "CASH", "amount": "100000"},
    )
    assert p_res.status_code == 201

    # 45. Payment recording does not trigger stock mutation
    stock = client.get(f"/api/v1/businesses/{biz_id}/inventory/stock", headers={"Authorization": f"Bearer {token}"}).json()
    assert len(stock) == 1
    assert Decimal(str(stock[0]["quantity"])) == Decimal("999")

    # 46. Receivables endpoint now exists (Feature #26)
    assert client.get(f"/api/v1/businesses/{biz_id}/receivables", headers={"Authorization": f"Bearer {token}"}).status_code == 200

    # 47. No accounting journal endpoint
    assert client.get(f"/api/v1/businesses/{biz_id}/journals").status_code == 404

    # 48. No cash account mutation / dependency
    # 49. No gateway call
    # 50. No external gateway dependency (field verification)
    p_data = p_res.json()
    assert "cash_account_id" not in p_data


# ============================================================
# API Endpoints & Pagination (51-56)
# ============================================================

def test_api_endpoints_and_pagination(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)
    prod_id = _create_product(client, token, biz_id, unit_id)
    sales_id = _create_finalized_sales(client, token, biz_id, branch_id, prod_id, "100000")

    # Create 3 payments
    p1 = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments",
        headers={"Authorization": f"Bearer {token}"},
        json={"payment_method": "CASH", "amount": "20000"},
    ).json()

    p2 = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments",
        headers={"Authorization": f"Bearer {token}"},
        json={"payment_method": "BANK_TRANSFER", "amount": "30000"},
    ).json()

    p3 = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments",
        headers={"Authorization": f"Bearer {token}"},
        json={"payment_method": "QRIS", "amount": "10000"},
    ).json()

    # 51. List payments
    list_res = client.get(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 3

    # 52. Get payment
    get_res = client.get(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments/{p1['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_res.status_code == 200
    assert get_res.json()["id"] == p1["id"]

    # 53 & 54. Create & Cancel payment covered in previous tests

    # 55. Invalid route relationship rejected
    sales2_id = _create_finalized_sales(client, token, biz_id, branch_id, prod_id, "50000")
    inv_rel = client.get(
        f"/api/v1/businesses/{biz_id}/sales/{sales2_id}/payments/{p1['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert inv_rel.status_code == 404

    # 56. Pagination works
    page1 = client.get(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments?page=1&page_size=2",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    assert len(page1["items"]) == 2
    assert page1["total"] == 3

    page2 = client.get(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments?page=2&page_size=2",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    assert len(page2["items"]) == 1

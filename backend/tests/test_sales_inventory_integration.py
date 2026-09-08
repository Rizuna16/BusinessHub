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


def _create_warehouse_and_location(client, token, biz_id, branch_id=None, is_default=True):
    wh_res = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Default WH", "code": f"WH_{uuid.uuid4().hex[:6]}", "branch_id": branch_id},
    )
    assert wh_res.status_code == 201
    wh_id = wh_res.json()["id"]

    loc_res = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses/{wh_id}/locations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Default Loc", "code": f"LOC_{uuid.uuid4().hex[:6]}", "location_type": "GENERAL"},
    )
    assert loc_res.status_code == 201
    loc_id = loc_res.json()["id"]
    return wh_id, loc_id


def _create_product(client, token, biz_id, unit_id, p_type="GOODS"):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/products",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": f"Product_{p_type}", "code": f"PR_{uuid.uuid4().hex[:6]}", "unit_id": unit_id, "product_type": p_type},
    )
    assert res.status_code == 201
    return res.json()["id"]


def _create_variant(client, token, biz_id, product_id):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/products/{product_id}/variants",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Variant A", "code": f"VAR_{uuid.uuid4().hex[:6]}"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def _set_opening_balance(client, token, biz_id, location_id, product_id, variant_id=None, quantity="100"):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/inventory/opening-balance",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "inventory_location_id": location_id,
            "product_id": product_id,
            "variant_id": variant_id,
            "quantity": quantity,
        },
    )
    assert res.status_code == 201
    return res.json()


# ============================================================
# Basic Integration & Item Types (1-6)
# ============================================================

def test_goods_sales_finalizes_and_deducts_stock(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)
    wh_id, loc_id = _create_warehouse_and_location(client, token, biz_id, branch_id=branch_id)
    prod_id = _create_product(client, token, biz_id, unit_id, p_type="GOODS")

    # Set initial stock: 10
    _set_opening_balance(client, token, biz_id, loc_id, prod_id, quantity="10")

    # Create Sales order
    sales_res = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    )
    sales_id = sales_res.json()["id"]

    # Add line: GOODS qty 3
    client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_id, "quantity": "3", "unit_price": "50000"},
    )

    # 1. Finalize Sales
    fin_res = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize?inventory_location_id={loc_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fin_res.status_code == 200
    assert fin_res.json()["status"] == "FINALIZED"

    # Assert stock balance deducted (10 - 3 = 7)
    stock = client.get(f"/api/v1/businesses/{biz_id}/inventory/stock", headers={"Authorization": f"Bearer {token}"}).json()
    assert len(stock) == 1
    assert Decimal(str(stock[0]["quantity"])) == Decimal("7")

    # Assert movement created
    movements = client.get(f"/api/v1/businesses/{biz_id}/inventory/movements", headers={"Authorization": f"Bearer {token}"}).json()
    assert len(movements) == 2  # 1 opening_balance + 1 sale_out
    sale_mov = [m for m in movements if m["movement_type"] == "SALE_OUT"][0]
    assert sale_mov["reference_type"] == "SALES"
    assert sale_mov["reference_id"] == sales_id
    assert len(sale_mov["lines"]) == 1
    assert sale_mov["lines"][0]["direction"] == "OUT"
    assert Decimal(str(sale_mov["lines"][0]["quantity"])) == Decimal("3")


def test_service_only_sales_finalizes_without_stock_movement(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)
    prod_srv = _create_product(client, token, biz_id, unit_id, p_type="SERVICE")

    # Create Sales order with SERVICE line
    sales_id = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    ).json()["id"]

    client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_srv, "quantity": "1", "unit_price": "100000"},
    )

    # 2. Finalize SERVICE-only sales (no warehouse/location required)
    fin_res = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fin_res.status_code == 200
    assert fin_res.json()["status"] == "FINALIZED"

    # Assert 0 movements created
    movements = client.get(f"/api/v1/businesses/{biz_id}/inventory/movements", headers={"Authorization": f"Bearer {token}"}).json()
    assert len(movements) == 0


def test_mixed_goods_and_service_sales(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)
    wh_id, loc_id = _create_warehouse_and_location(client, token, biz_id, branch_id=branch_id)
    prod_goods = _create_product(client, token, biz_id, unit_id, p_type="GOODS")
    prod_srv = _create_product(client, token, biz_id, unit_id, p_type="SERVICE")

    _set_opening_balance(client, token, biz_id, loc_id, prod_goods, quantity="20")

    sales_id = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    ).json()["id"]

    # Line 1: GOODS qty 5
    client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_goods, "quantity": "5", "unit_price": "10000"},
    )

    # Line 2: SERVICE qty 1
    client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_srv, "quantity": "1", "unit_price": "50000"},
    )

    # 3. Finalize mixed sales
    fin_res = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize?inventory_location_id={loc_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fin_res.status_code == 200

    # Assert stock balance for GOODS deducted (20 - 5 = 15)
    stock = client.get(f"/api/v1/businesses/{biz_id}/inventory/stock", headers={"Authorization": f"Bearer {token}"}).json()
    assert len(stock) == 1
    assert Decimal(str(stock[0]["quantity"])) == Decimal("15")

    # Assert movement contains only 1 line for GOODS
    movements = client.get(f"/api/v1/businesses/{biz_id}/inventory/movements", headers={"Authorization": f"Bearer {token}"}).json()
    sale_mov = [m for m in movements if m["movement_type"] == "SALE_OUT"][0]
    assert len(sale_mov["lines"]) == 1
    assert sale_mov["lines"][0]["product_id"] == prod_goods


def test_variant_stock_deduction_target(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)
    wh_id, loc_id = _create_warehouse_and_location(client, token, biz_id, branch_id=branch_id)
    prod_id = _create_product(client, token, biz_id, unit_id, p_type="GOODS")
    var_id = _create_variant(client, token, biz_id, prod_id)

    # Set opening balance on VARIANT (not parent product)
    _set_opening_balance(client, token, biz_id, loc_id, prod_id, variant_id=var_id, quantity="15")

    sales_id = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    ).json()["id"]

    # Line targeting variant
    client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"variant_id": var_id, "quantity": "4", "unit_price": "25000"},
    )

    # 5. Variant deduction targets correct stock
    fin_res = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize?inventory_location_id={loc_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fin_res.status_code == 200

    stock = client.get(f"/api/v1/businesses/{biz_id}/inventory/stock", headers={"Authorization": f"Bearer {token}"}).json()
    assert len(stock) == 1
    assert stock[0]["variant_id"] == var_id
    assert Decimal(str(stock[0]["quantity"])) == Decimal("11")


# ============================================================
# Stock Validation & Insufficient Stock (7-15)
# ============================================================

def test_insufficient_stock_rejection_and_atomic_rollback(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)
    wh_id, loc_id = _create_warehouse_and_location(client, token, biz_id, branch_id=branch_id)
    prod_a = _create_product(client, token, biz_id, unit_id, p_type="GOODS")
    prod_b = _create_product(client, token, biz_id, unit_id, p_type="GOODS")

    # Stock A = 10, Stock B = 2
    _set_opening_balance(client, token, biz_id, loc_id, prod_a, quantity="10")
    _set_opening_balance(client, token, biz_id, loc_id, prod_b, quantity="2")

    sales_id = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    ).json()["id"]

    # Line 1: Prod A qty 5 (available)
    client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_a, "quantity": "5", "unit_price": "10000"},
    )
    # Line 2: Prod B qty 5 (insufficient, avail 2)
    client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_b, "quantity": "5", "unit_price": "10000"},
    )

    # 11 & 12 & 13 & 14 & 15. Insufficient stock rejects, Sales remains DRAFT, stock unchanged, no SALE_OUT movement
    fin_res = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize?inventory_location_id={loc_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fin_res.status_code == 400
    msg = fin_res.json().get("message") or fin_res.json().get("detail", "")
    assert "Insufficient stock" in msg

    # Sales remains DRAFT
    sales_detail = client.get(f"/api/v1/businesses/{biz_id}/sales/{sales_id}", headers={"Authorization": f"Bearer {token}"}).json()
    assert sales_detail["status"] == "DRAFT"

    # Stock unchanged (A=10, B=2)
    stock_a = client.get(f"/api/v1/businesses/{biz_id}/inventory/stock?product_id={prod_a}", headers={"Authorization": f"Bearer {token}"}).json()
    assert Decimal(str(stock_a[0]["quantity"])) == Decimal("10")

    stock_b = client.get(f"/api/v1/businesses/{biz_id}/inventory/stock?product_id={prod_b}", headers={"Authorization": f"Bearer {token}"}).json()
    assert Decimal(str(stock_b[0]["quantity"])) == Decimal("2")

    # No SALE_OUT movement created
    movements = client.get(f"/api/v1/businesses/{biz_id}/inventory/movements", headers={"Authorization": f"Bearer {token}"}).json()
    sale_movs = [m for m in movements if m["movement_type"] == "SALE_OUT"]
    assert len(sale_movs) == 0


def test_multiple_lines_same_product_aggregation_validation(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)
    wh_id, loc_id = _create_warehouse_and_location(client, token, biz_id, branch_id=branch_id)
    prod_id = _create_product(client, token, biz_id, unit_id, p_type="GOODS")

    # Stock = 4
    _set_opening_balance(client, token, biz_id, loc_id, prod_id, quantity="4")

    sales_id = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    ).json()["id"]

    # Line 1: qty 3
    client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_id, "quantity": "3", "unit_price": "10000"},
    )
    # Line 2: qty 2 (Aggregated required = 5 > stock 4)
    client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_id, "quantity": "2", "unit_price": "10000"},
    )

    # 10. Aggregated check fails
    fin_res = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize?inventory_location_id={loc_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fin_res.status_code == 400
    msg = fin_res.json().get("message") or fin_res.json().get("detail", "")
    assert "Insufficient stock" in msg

    # Stock remains 4
    stock = client.get(f"/api/v1/businesses/{biz_id}/inventory/stock?product_id={prod_id}", headers={"Authorization": f"Bearer {token}"}).json()
    assert Decimal(str(stock[0]["quantity"])) == Decimal("4")


# ============================================================
# Location Resolution & Default Fallback (16-27)
# ============================================================

def test_explicit_valid_and_invalid_location_handling(client):
    token_a = _register_and_get_token(client, email="a@biz.com")
    biz_a = _create_business(client, token_a, name="Biz A")
    unit_a = _create_unit(client, token_a, biz_a)
    branch_a = _create_branch(client, token_a, biz_a)
    wh_a, loc_a = _create_warehouse_and_location(client, token_a, biz_a, branch_id=branch_a)
    prod_a = _create_product(client, token_a, biz_a, unit_a, p_type="GOODS")
    _set_opening_balance(client, token_a, biz_a, loc_a, prod_a, quantity="10")

    token_b = _register_and_get_token(client, email="b@biz.com")
    biz_b = _create_business(client, token_b, name="Biz B")
    wh_b, loc_b = _create_warehouse_and_location(client, token_b, biz_b)

    sales_id = client.post(
        f"/api/v1/businesses/{biz_a}/sales",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"branch_id": branch_a, "sales_date": datetime.now(timezone.utc).isoformat()},
    ).json()["id"]

    client.post(
        f"/api/v1/businesses/{biz_a}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"product_id": prod_a, "quantity": "2", "unit_price": "10000"},
    )

    # 17. Cross-business location rejected
    res_cross = client.post(
        f"/api/v1/businesses/{biz_a}/sales/{sales_id}/finalize?inventory_location_id={loc_b}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_cross.status_code == 400

    # 16. Valid location accepted
    res_ok = client.post(
        f"/api/v1/businesses/{biz_a}/sales/{sales_id}/finalize?inventory_location_id={loc_a}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_ok.status_code == 200


def test_default_location_resolution(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)
    wh_id, loc_id = _create_warehouse_and_location(client, token, biz_id, branch_id=branch_id, is_default=True)
    prod_id = _create_product(client, token, biz_id, unit_id, p_type="GOODS")
    _set_opening_balance(client, token, biz_id, loc_id, prod_id, quantity="10")

    sales_id = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    ).json()["id"]

    client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_id, "quantity": "3", "unit_price": "10000"},
    )

    # 24 & 25. Finalize without explicit location -> resolves default branch/business location
    res = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "FINALIZED"

    # Verify stock deducted at resolved default location
    stock = client.get(f"/api/v1/businesses/{biz_id}/inventory/stock?inventory_location_id={loc_id}", headers={"Authorization": f"Bearer {token}"}).json()
    assert Decimal(str(stock[0]["quantity"])) == Decimal("7")


# ============================================================
# Lifecycle & Duplicate Posting Protection (28-34)
# ============================================================

def test_duplicate_finalization_and_double_posting_prevention(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)
    wh_id, loc_id = _create_warehouse_and_location(client, token, biz_id, branch_id=branch_id)
    prod_id = _create_product(client, token, biz_id, unit_id, p_type="GOODS")
    _set_opening_balance(client, token, biz_id, loc_id, prod_id, quantity="20")

    sales_id = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    ).json()["id"]

    client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_id, "quantity": "5", "unit_price": "10000"},
    )

    fin1 = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize?inventory_location_id={loc_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fin1.status_code == 200

    # 28 & 32 & 33 & 34. Repeat finalization rejected, no double stock deduction
    fin2 = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize?inventory_location_id={loc_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fin2.status_code == 400

    stock = client.get(f"/api/v1/businesses/{biz_id}/inventory/stock?product_id={prod_id}", headers={"Authorization": f"Bearer {token}"}).json()
    assert Decimal(str(stock[0]["quantity"])) == Decimal("15")  # Deducted only once (20 - 5 = 15)


def test_draft_cancellation_does_not_mutate_stock(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)
    wh_id, loc_id = _create_warehouse_and_location(client, token, biz_id, branch_id=branch_id)
    prod_id = _create_product(client, token, biz_id, unit_id, p_type="GOODS")
    _set_opening_balance(client, token, biz_id, loc_id, prod_id, quantity="10")

    sales_id = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    ).json()["id"]

    client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_id, "quantity": "5", "unit_price": "10000"},
    )

    # 30. Cancel DRAFT Sales
    can_res = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/cancel",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert can_res.status_code == 200
    assert can_res.json()["status"] == "CANCELLED"

    # Stock unchanged (10)
    stock = client.get(f"/api/v1/businesses/{biz_id}/inventory/stock?product_id={prod_id}", headers={"Authorization": f"Bearer {token}"}).json()
    assert Decimal(str(stock[0]["quantity"])) == Decimal("10")


# ============================================================
# Security & Payment Decoupling (35-43)
# ============================================================

def test_rbac_and_payment_decoupling(client):
    owner_token = _register_and_get_token(client, email="owner@biz.com")
    biz_id = _create_business(client, owner_token)
    unit_id = _create_unit(client, owner_token, biz_id)
    branch_id = _create_branch(client, owner_token, biz_id)
    wh_id, loc_id = _create_warehouse_and_location(client, owner_token, biz_id, branch_id=branch_id)
    prod_id = _create_product(client, owner_token, biz_id, unit_id, p_type="GOODS")
    _set_opening_balance(client, owner_token, biz_id, loc_id, prod_id, quantity="50")

    member_token, _, _ = _add_member(client, owner_token, biz_id, "member@biz.com", role="MEMBER")

    sales_id = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    ).json()["id"]

    client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"product_id": prod_id, "quantity": "10", "unit_price": "10000"},
    )

    # 37. MEMBER cannot finalize (403)
    res_mem_fin = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize?inventory_location_id={loc_id}",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert res_mem_fin.status_code == 403

    # 35 & 40. OWNER finalizes unpaid Sales -> stock deducted
    res_owner_fin = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize?inventory_location_id={loc_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert res_owner_fin.status_code == 200
    assert res_owner_fin.json()["status"] == "FINALIZED"

    # Stock deducted (50 - 10 = 40)
    stock = client.get(f"/api/v1/businesses/{biz_id}/inventory/stock?product_id={prod_id}", headers={"Authorization": f"Bearer {owner_token}"}).json()
    assert Decimal(str(stock[0]["quantity"])) == Decimal("40")

    # 41. Record payment after finalization -> stock unaffected
    pay_res = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"payment_method": "CASH", "amount": "100000"},
    )
    assert pay_res.status_code == 201

    stock_after_pay = client.get(f"/api/v1/businesses/{biz_id}/inventory/stock?product_id={prod_id}", headers={"Authorization": f"Bearer {owner_token}"}).json()
    assert Decimal(str(stock_after_pay[0]["quantity"])) == Decimal("40")

    # 43. Payment cancellation -> stock unaffected
    pay_id = pay_res.json()["id"]
    client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/payments/{pay_id}/cancel",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    stock_after_pay_can = client.get(f"/api/v1/businesses/{biz_id}/inventory/stock?product_id={prod_id}", headers={"Authorization": f"Bearer {owner_token}"}).json()
    assert Decimal(str(stock_after_pay_can[0]["quantity"])) == Decimal("40")

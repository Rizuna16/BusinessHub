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
from app.modules.supplier.repository import InMemorySupplierRepository
from app.modules.product.repository import InMemoryProductRepository
from app.modules.product_variant.repository import InMemoryProductVariantRepository
from app.modules.unit.repository import InMemoryUnitRepository
from app.modules.branch.repository import InMemoryBranchRepository
from app.modules.purchase.repository import InMemoryPurchaseRepository
from app.modules.supplier_catalog.repository import InMemorySupplierCatalogRepository
from app.modules.warehouse.repository import InMemoryInventoryLocationRepository, InMemoryWarehouseRepository
from app.modules.receiving.repository import InMemoryReceivingRepository
from app.modules.stock_opname.repository import InMemoryStockOpnameRepository
from app.modules.inventory.repository import InMemoryStockBalanceRepository, InMemoryStockMovementRepository, InMemoryInventoryCostRepository


@pytest.fixture(autouse=True)
def clear_all_repos():
    InMemoryUserRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemorySupplierRepository.clear()
    InMemoryProductRepository.clear()
    InMemoryProductVariantRepository.clear()
    InMemoryUnitRepository.clear()
    InMemoryBranchRepository.clear()
    InMemoryPurchaseRepository.clear()
    InMemorySupplierCatalogRepository.clear()
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
    InMemorySupplierRepository.clear()
    InMemoryProductRepository.clear()
    InMemoryProductVariantRepository.clear()
    InMemoryUnitRepository.clear()
    InMemoryBranchRepository.clear()
    InMemoryPurchaseRepository.clear()
    InMemorySupplierCatalogRepository.clear()
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
        json={
            "email": email,
            "full_name": full_name,
            "password": password,
            "password_confirmation": password,
        },
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


def _create_unit(client, token, biz_id, name=None, code=None):
    if not name:
        name = f"Unit_{uuid.uuid4().hex[:6]}"
    if not code:
        code = f"UNIT_{uuid.uuid4().hex[:6].upper()}"
    res = client.post(
        f"/api/v1/businesses/{biz_id}/units",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code, "symbol": "PCS", "unit_type": "OTHER"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def _create_branch(client, token, biz_id, name="Main Branch", code=None):
    if not code:
        code = f"BR_{uuid.uuid4().hex[:6].upper()}"
    res = client.post(
        f"/api/v1/businesses/{biz_id}/branches",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code},
    )
    assert res.status_code == 201
    return res.json()["id"]


def _create_product(client, token, biz_id, unit_id, name="Product Goods", code=None):
    if not code:
        code = f"PROD_{uuid.uuid4().hex[:6].upper()}"
    res = client.post(
        f"/api/v1/businesses/{biz_id}/products",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code, "unit_id": unit_id, "product_type": "GOODS"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def _create_variant(client, token, biz_id, product_id, name="Variant A", code=None):
    if not code:
        code = f"VAR_{uuid.uuid4().hex[:6].upper()}"
    res = client.post(
        f"/api/v1/businesses/{biz_id}/products/{product_id}/variants",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code},
    )
    assert res.status_code == 201
    return res.json()["id"]


def _create_supplier(client, token, biz_id, name="Supplier A"):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/suppliers",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "supplier_type": "ORGANIZATION"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def _create_purchase(client, token, biz_id, supplier_id, branch_id):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/purchases",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "supplier_id": supplier_id,
            "branch_id": branch_id,
            "purchase_date": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert res.status_code == 201
    return res.json()["id"]


def _add_line(client, token, biz_id, purchase_id, product_id, quantity="10", unit_price="1000"):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/purchases/{purchase_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "product_id": product_id,
            "quantity": quantity,
            "unit_price": unit_price,
        },
    )
    assert res.status_code == 201
    return res.json()


def _finalize_purchase(client, token, biz_id, purchase_id):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/purchases/{purchase_id}/finalize",
        headers={"Authorization": f"Bearer {token}"},
    )
    return res


def _create_receiving(client, token, biz_id, purchase_id, location_id):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/receivings",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "purchase_id": purchase_id,
            "inventory_location_id": location_id,
        },
    )
    assert res.status_code == 201
    return res.json()["id"]


def _add_receiving_line(client, token, biz_id, receiving_id, purchase_line_id, quantity="5"):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/receivings/{receiving_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "purchase_line_id": purchase_line_id,
            "quantity": quantity,
        },
    )
    return res


def _finalize_receiving(client, token, biz_id, receiving_id):
    return client.post(
        f"/api/v1/businesses/{biz_id}/receivings/{receiving_id}/finalize",
        headers={"Authorization": f"Bearer {token}"},
    )


def _create_catalog_item(client, token, biz_id, supplier_id, product_id=None, variant_id=None, price="1000"):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "supplier_id": supplier_id,
            "product_id": product_id,
            "variant_id": variant_id,
            "purchase_price": price,
            "currency": "IDR",
        },
    )
    assert res.status_code == 201
    return res.json()["id"]


# ============================================================
# 1. Catalog Integration Tests
# ============================================================

def test_active_catalog_price_suggestion(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)
    supplier_id = _create_supplier(client, token, biz_id)
    product_id = _create_product(client, token, biz_id, unit_id)

    # Create catalog item
    _create_catalog_item(client, token, biz_id, supplier_id, product_id=product_id, price="125000")

    # Create purchase and add line
    purchase_id = _create_purchase(client, token, biz_id, supplier_id, branch_id)
    line = _add_line(client, token, biz_id, purchase_id, product_id, quantity="10", unit_price="125000")

    assert line["suggested_supplier_price"] == "125000"
    assert line["ordered_quantity"] == "10"
    assert line["received_quantity"] == "0"
    assert line["remaining_quantity"] == "10"

    detail = client.get(
        f"/api/v1/businesses/{biz_id}/purchases/{purchase_id}",
        headers={"Authorization": f"Bearer {token}"},
    ).json()

    assert detail["receiving_summary"]["status"] == "NOT_RECEIVED"
    assert detail["receiving_summary"]["total_ordered"] == "10"
    assert detail["receiving_summary"]["total_received"] == "0"
    assert detail["receiving_summary"]["total_remaining"] == "10"


def test_no_catalog_allows_purchase(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)
    supplier_id = _create_supplier(client, token, biz_id)
    product_id = _create_product(client, token, biz_id, unit_id)

    purchase_id = _create_purchase(client, token, biz_id, supplier_id, branch_id)
    line = _add_line(client, token, biz_id, purchase_id, product_id, quantity="10", unit_price="1000")

    assert line["suggested_supplier_price"] is None
    assert line["ordered_quantity"] == "10"


def test_catalog_does_not_mutate_historical_purchase(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)
    supplier_id = _create_supplier(client, token, biz_id)
    product_id = _create_product(client, token, biz_id, unit_id)

    _create_catalog_item(client, token, biz_id, supplier_id, product_id=product_id, price="100000")

    purchase_id = _create_purchase(client, token, biz_id, supplier_id, branch_id)
    _add_line(client, token, biz_id, purchase_id, product_id, quantity="10", unit_price="97500")

    fin_res = _finalize_purchase(client, token, biz_id, purchase_id)
    assert fin_res.status_code == 200

    # Change catalog price
    catalog_res = client.patch(
        f"/api/v1/businesses/{biz_id}/supplier-catalog", # Need catalog item id to patch
        headers={"Authorization": f"Bearer {token}"},
    )

    detail = client.get(
        f"/api/v1/businesses/{biz_id}/purchases/{purchase_id}",
        headers={"Authorization": f"Bearer {token}"},
    ).json()

    assert detail["lines"][0]["unit_price"] == "97500"
    assert detail["lines"][0]["suggested_supplier_price"] == "100000"


# ============================================================
# 2. Receiving Progress Tests
# ============================================================

def test_no_finalized_receiving(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)
    supplier_id = _create_supplier(client, token, biz_id)
    product_id = _create_product(client, token, biz_id, unit_id)
    location_id = "some_loc_id"
    # TODO: create actual location

    purchase_id = _create_purchase(client, token, biz_id, supplier_id, branch_id)
    line = _add_line(client, token, biz_id, purchase_id, product_id, quantity="10")

    _finalize_purchase(client, token, biz_id, purchase_id)

    detail = client.get(
        f"/api/v1/businesses/{biz_id}/purchases/{purchase_id}",
        headers={"Authorization": f"Bearer {token}"},
    ).json()

    assert detail["receiving_summary"]["status"] == "NOT_RECEIVED"
    assert detail["lines"][0]["received_quantity"] == "0"
    assert detail["lines"][0]["remaining_quantity"] == "10"

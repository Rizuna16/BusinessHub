import uuid
from datetime import datetime, timezone
import pytest
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
from app.modules.warehouse.repository import InMemoryWarehouseRepository
from app.modules.purchase.repository import InMemoryPurchaseRepository
from app.modules.inventory.repository import InMemoryStockBalanceRepository, InMemoryStockMovementRepository, InMemoryInventoryCostRepository
from app.modules.supplier_catalog.repository import InMemorySupplierCatalogRepository


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
    InMemoryWarehouseRepository.clear()
    InMemoryPurchaseRepository.clear()
    InMemoryStockBalanceRepository.clear()
    InMemoryStockMovementRepository.clear()
    InMemoryInventoryCostRepository.clear()
    InMemorySupplierCatalogRepository.clear()
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
    InMemoryWarehouseRepository.clear()
    InMemoryPurchaseRepository.clear()
    InMemoryStockBalanceRepository.clear()
    InMemoryStockMovementRepository.clear()
    InMemoryInventoryCostRepository.clear()
    InMemorySupplierCatalogRepository.clear()


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
        f"/api/v1/businesses",
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


def _create_unit(client, token, biz_id, name=None, code=None, symbol="PCS"):
    if not name:
        name = f"Unit_{uuid.uuid4().hex[:6]}"
    if not code:
        code = f"UNIT_{uuid.uuid4().hex[:6].upper()}"
    res = client.post(
        f"/api/v1/businesses/{biz_id}/units",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code, "symbol": symbol, "unit_type": "OTHER"},
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


def _create_product(client, token, biz_id, unit_id, name="Kaos Cotton 24s", code="AIR-600", product_type="GOODS"):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/products",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": name,
            "code": code,
            "unit_id": unit_id,
            "product_type": product_type,
        },
    )
    assert res.status_code == 201
    return res.json()["id"]


def _create_variant(client, token, biz_id, product_id, name="Red L", code="AIR-600-RED-L"):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/products/{product_id}/variants",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": name,
            "code": code,
        },
    )
    assert res.status_code == 201
    return res.json()["id"]


def _create_supplier(client, token, biz_id, name="PT Supplier Utama", supplier_type="ORGANIZATION"):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/suppliers",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": name,
            "supplier_type": supplier_type,
        },
    )
    assert res.status_code == 201
    return res.json()["id"]


# ============================================================
# Test Suite
# ============================================================

def test_authentication(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)

    # 1. Missing token -> 401
    res = client.get(f"/api/v1/businesses/{biz_id}/supplier-catalog")
    assert res.status_code == 401

    # 2. Invalid token -> 401
    res = client.get(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": "Bearer invalidtoken123"},
    )
    assert res.status_code == 401


def test_membership_and_rbac(client):
    owner_token = _register_and_get_token(client, email="owner@biz.com")
    biz_id = _create_business(client, owner_token)

    unit_id = _create_unit(client, owner_token, biz_id)
    prod_id = _create_product(client, owner_token, biz_id, unit_id)
    sup_id = _create_supplier(client, owner_token, biz_id)

    admin_token, _, _ = _add_member(client, owner_token, biz_id, "admin@biz.com", role="ADMIN")
    member_token, _, _ = _add_member(client, owner_token, biz_id, "member@biz.com", role="MEMBER")

    # 3. OWNER full access (create)
    payload = {
        "supplier_id": sup_id,
        "product_id": prod_id,
        "purchase_price": "3500.50",
        "currency": "idr",
        "supplier_code": "000123",
    }
    res = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {owner_token}"},
        json=payload,
    )
    assert res.status_code == 201
    catalog_id = res.json()["id"]

    # 4. ADMIN full access (update)
    res = client.patch(
        f"/api/v1/businesses/{biz_id}/supplier-catalog/{catalog_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"purchase_price": "3600"},
    )
    assert res.status_code == 200

    # 5. MEMBER read
    res = client.get(
        f"/api/v1/businesses/{biz_id}/supplier-catalog/{catalog_id}",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert res.status_code == 200

    # 6. MEMBER create denied -> 403
    res = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {member_token}"},
        json=payload,
    )
    assert res.status_code == 403

    # 7. MEMBER update denied -> 403
    res = client.patch(
        f"/api/v1/businesses/{biz_id}/supplier-catalog/{catalog_id}",
        headers={"Authorization": f"Bearer {member_token}"},
        json={"purchase_price": "3700"},
    )
    assert res.status_code == 403

    # 8. MEMBER archive denied -> 403
    res = client.delete(
        f"/api/v1/businesses/{biz_id}/supplier-catalog/{catalog_id}",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert res.status_code == 403

    # 9. Suspended membership denied -> 404 (anti-enumeration convention)
    suspended_token, _, suspended_membership_id = _add_member(client, owner_token, biz_id, "suspended@biz.com", role="MEMBER")
    client.patch(
        f"/api/v1/businesses/{biz_id}/members/{suspended_membership_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"status": "SUSPENDED"},
    )
    res = client.get(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {suspended_token}"},
    )
    assert res.status_code == 404

    # 10. Removed membership denied -> 404 (anti-enumeration convention)
    client.patch(
        f"/api/v1/businesses/{biz_id}/members/{suspended_membership_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"status": "REMOVED"},
    )
    res = client.get(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {suspended_token}"},
    )
    assert res.status_code == 404

    # 11. Non-member -> 404
    stranger_token = _register_and_get_token(client, email="stranger@example.com")
    res = client.get(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {stranger_token}"},
    )
    assert res.status_code == 404


def test_tenant_isolation(client):
    token1 = _register_and_get_token(client, email="owner1@biz.com")
    biz1 = _create_business(client, token1, name="Biz 1")

    token2 = _register_and_get_token(client, email="owner2@biz.com")
    biz2 = _create_business(client, token2, name="Biz 2")

    sup2 = _create_supplier(client, token2, biz2, name="Sup 2")
    unit2 = _create_unit(client, token2, biz2)
    prod2 = _create_product(client, token2, biz2, unit2, code="PROD-2")

    # 12. Cross-business supplier rejected
    res = client.post(
        f"/api/v1/businesses/{biz1}/supplier-catalog",
        headers={"Authorization": f"Bearer {token1}"},
        json={
            "supplier_id": sup2,
            "product_id": _create_product(client, token1, biz1, _create_unit(client, token1, biz1)),
            "purchase_price": "1000",
            "currency": "IDR",
        },
    )
    assert res.status_code == 400

    # 13. Cross-business product rejected
    sup1 = _create_supplier(client, token1, biz1, name="Sup 1")
    res = client.post(
        f"/api/v1/businesses/{biz1}/supplier-catalog",
        headers={"Authorization": f"Bearer {token1}"},
        json={
            "supplier_id": sup1,
            "product_id": prod2,
            "purchase_price": "1000",
            "currency": "IDR",
        },
    )
    assert res.status_code == 400

    # 14. Cross-business variant rejected
    var2 = _create_variant(client, token2, biz2, prod2, code="VAR-2")
    res = client.post(
        f"/api/v1/businesses/{biz1}/supplier-catalog",
        headers={"Authorization": f"Bearer {token1}"},
        json={
            "supplier_id": sup1,
            "variant_id": var2,
            "purchase_price": "1000",
            "currency": "IDR",
        },
    )
    assert res.status_code == 400

    # 15. Cross-business catalog access -> 404
    prod1 = _create_product(client, token1, biz1, _create_unit(client, token1, biz1), code="PROD-1")
    res1 = client.post(
        f"/api/v1/businesses/{biz1}/supplier-catalog",
        headers={"Authorization": f"Bearer {token1}"},
        json={
            "supplier_id": sup1,
            "product_id": prod1,
            "purchase_price": "1000",
            "currency": "IDR",
        },
    )
    assert res1.status_code == 201
    cat1_id = res1.json()["id"]

    res = client.get(
        f"/api/v1/businesses/{biz2}/supplier-catalog/{cat1_id}",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert res.status_code == 404


def test_supplier_validation(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    prod_id = _create_product(client, token, biz_id, unit_id)

    sup_id = _create_supplier(client, token, biz_id)

    # 16. Active supplier accepted
    res = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "supplier_id": sup_id,
            "product_id": prod_id,
            "purchase_price": "5000",
            "currency": "IDR",
        },
    )
    assert res.status_code == 201

    # Deactivate supplier
    client.post(f"/api/v1/businesses/{biz_id}/suppliers/{sup_id}/deactivate", headers={"Authorization": f"Bearer {token}"})

    # 17. Inactive supplier rejected
    res2 = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "supplier_id": sup_id,
            "product_id": _create_product(client, token, biz_id, unit_id, code="PROD-B", name="Prod B"),
            "purchase_price": "5000",
            "currency": "IDR",
        },
    )
    assert res2.status_code == 400

    # Archive supplier
    client.delete(f"/api/v1/businesses/{biz_id}/suppliers/{sup_id}", headers={"Authorization": f"Bearer {token}"})

    # 18. Archived supplier rejected
    res3 = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "supplier_id": sup_id,
            "product_id": _create_product(client, token, biz_id, unit_id, code="PROD-C", name="Prod C"),
            "purchase_price": "5000",
            "currency": "IDR",
        },
    )
    assert res3.status_code == 400


def test_product_validation(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    sup_id = _create_supplier(client, token, biz_id)

    # 19. Active GOODS accepted
    prod_goods = _create_product(client, token, biz_id, unit_id, code="GOODS-1", product_type="GOODS")
    res = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "supplier_id": sup_id,
            "product_id": prod_goods,
            "purchase_price": "100",
            "currency": "IDR",
        },
    )
    assert res.status_code == 201

    # 20. SERVICE rejected
    prod_service = _create_product(client, token, biz_id, unit_id, code="SERV-1", product_type="SERVICE")
    res2 = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "supplier_id": sup_id,
            "product_id": prod_service,
            "purchase_price": "100",
            "currency": "IDR",
        },
    )
    assert res2.status_code == 400

    # 21. Archived product rejected
    prod_arch = _create_product(client, token, biz_id, unit_id, code="ARCH-1", product_type="GOODS")
    client.delete(f"/api/v1/businesses/{biz_id}/products/{prod_arch}", headers={"Authorization": f"Bearer {token}"})
    res3 = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "supplier_id": sup_id,
            "product_id": prod_arch,
            "purchase_price": "100",
            "currency": "IDR",
        },
    )
    assert res3.status_code == 400


def test_variant_validation(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    sup_id = _create_supplier(client, token, biz_id)

    prod_id = _create_product(client, token, biz_id, unit_id, code="PROD-V", product_type="GOODS")
    var_id = _create_variant(client, token, biz_id, prod_id, code="VAR-1")

    # 23. Active valid variant accepted
    res = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "supplier_id": sup_id,
            "variant_id": var_id,
            "purchase_price": "150",
            "currency": "USD",
        },
    )
    assert res.status_code == 201

    # 24. Archived variant rejected
    client.delete(f"/api/v1/businesses/{biz_id}/products/{prod_id}/variants/{var_id}", headers={"Authorization": f"Bearer {token}"})
    res2 = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "supplier_id": sup_id,
            "variant_id": var_id,
            "purchase_price": "150",
            "currency": "USD",
        },
    )
    assert res2.status_code == 400

    # 25. Parent product archived -> variant rejected
    prod2 = _create_product(client, token, biz_id, unit_id, code="PROD-V2", product_type="GOODS")
    var2 = _create_variant(client, token, biz_id, prod2, code="VAR-2")
    client.delete(f"/api/v1/businesses/{biz_id}/products/{prod2}", headers={"Authorization": f"Bearer {token}"})
    res3 = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "supplier_id": sup_id,
            "variant_id": var2,
            "purchase_price": "150",
            "currency": "USD",
        },
    )
    assert res3.status_code == 400


def test_xor_target(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    sup_id = _create_supplier(client, token, biz_id)
    prod_id = _create_product(client, token, biz_id, unit_id)
    var_id = _create_variant(client, token, biz_id, prod_id)

    # 27. Product only valid
    res = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {token}"},
        json={"supplier_id": sup_id, "product_id": prod_id, "purchase_price": "10", "currency": "IDR"},
    )
    assert res.status_code == 201

    # 28. Variant only valid
    res = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {token}"},
        json={"supplier_id": sup_id, "variant_id": var_id, "purchase_price": "10", "currency": "IDR"},
    )
    assert res.status_code == 201

    # 29. Both product and variant rejected -> 422
    res = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {token}"},
        json={"supplier_id": sup_id, "product_id": prod_id, "variant_id": var_id, "purchase_price": "10", "currency": "IDR"},
    )
    assert res.status_code == 422

    # 30. Neither product nor variant rejected -> 422
    res = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {token}"},
        json={"supplier_id": sup_id, "purchase_price": "10", "currency": "IDR"},
    )
    assert res.status_code == 422


def test_price_validation(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    sup_id = _create_supplier(client, token, biz_id)
    prod_id = _create_product(client, token, biz_id, unit_id)

    # 31. Zero accepted
    res = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {token}"},
        json={"supplier_id": sup_id, "product_id": prod_id, "purchase_price": "0", "currency": "IDR"},
    )
    assert res.status_code == 201

    # 32. Positive accepted
    res = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {token}"},
        json={"supplier_id": sup_id, "product_id": _create_product(client, token, biz_id, unit_id, code="P-2"), "purchase_price": "3500.50", "currency": "IDR"},
    )
    assert res.status_code == 201
    assert res.json()["purchase_price"] == "3500.50"

    # 33. Negative rejected -> 422
    res = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {token}"},
        json={"supplier_id": sup_id, "product_id": _create_product(client, token, biz_id, unit_id, code="P-3"), "purchase_price": "-10", "currency": "IDR"},
    )
    assert res.status_code == 422


def test_currency_validation(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    sup_id = _create_supplier(client, token, biz_id)
    prod_id = _create_product(client, token, biz_id, unit_id)

    # 35. Valid currencies accepted & 36. lowercase normalized
    res = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {token}"},
        json={"supplier_id": sup_id, "product_id": prod_id, "purchase_price": "100", "currency": "usd"},
    )
    assert res.status_code == 201
    assert res.json()["currency"] == "USD"

    # 37. Unsupported currency rejected -> 422
    res = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {token}"},
        json={"supplier_id": sup_id, "product_id": _create_product(client, token, biz_id, unit_id, code="P-CUR"), "purchase_price": "100", "currency": "XYZ"},
    )
    assert res.status_code == 422


def test_moq_validation(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    sup_id = _create_supplier(client, token, biz_id)
    prod_id = _create_product(client, token, biz_id, unit_id)

    # 38. Null accepted
    res = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {token}"},
        json={"supplier_id": sup_id, "product_id": prod_id, "purchase_price": "100", "currency": "IDR", "minimum_order_quantity": None},
    )
    assert res.status_code == 201

    # 39. Positive Decimal accepted
    res = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {token}"},
        json={"supplier_id": sup_id, "product_id": _create_product(client, token, biz_id, unit_id, code="P-MOQ1"), "purchase_price": "100", "currency": "IDR", "minimum_order_quantity": "50"},
    )
    assert res.status_code == 201
    assert res.json()["minimum_order_quantity"] == "50"

    # 40. Zero rejected -> 422
    res = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {token}"},
        json={"supplier_id": sup_id, "product_id": _create_product(client, token, biz_id, unit_id, code="P-MOQ2"), "purchase_price": "100", "currency": "IDR", "minimum_order_quantity": "0"},
    )
    assert res.status_code == 422

    # 41. Negative rejected -> 422
    res = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {token}"},
        json={"supplier_id": sup_id, "product_id": _create_product(client, token, biz_id, unit_id, code="P-MOQ3"), "purchase_price": "100", "currency": "IDR", "minimum_order_quantity": "-5"},
    )
    assert res.status_code == 422


def test_lead_time_validation(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    sup_id = _create_supplier(client, token, biz_id)
    prod_id = _create_product(client, token, biz_id, unit_id)

    # 42. Null accepted
    res = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {token}"},
        json={"supplier_id": sup_id, "product_id": prod_id, "purchase_price": "100", "currency": "IDR", "lead_time_days": None},
    )
    assert res.status_code == 201

    # 43. Zero accepted
    res = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {token}"},
        json={"supplier_id": sup_id, "product_id": _create_product(client, token, biz_id, unit_id, code="P-LT1"), "purchase_price": "100", "currency": "IDR", "lead_time_days": 0},
    )
    assert res.status_code == 201

    # 44. Positive accepted
    res = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {token}"},
        json={"supplier_id": sup_id, "product_id": _create_product(client, token, biz_id, unit_id, code="P-LT2"), "purchase_price": "100", "currency": "IDR", "lead_time_days": 14},
    )
    assert res.status_code == 201

    # 45. Negative rejected -> 422
    res = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {token}"},
        json={"supplier_id": sup_id, "product_id": _create_product(client, token, biz_id, unit_id, code="P-LT3"), "purchase_price": "100", "currency": "IDR", "lead_time_days": -1},
    )
    assert res.status_code == 422


def test_supplier_code_and_duplicates(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    sup_id = _create_supplier(client, token, biz_id)
    prod_id = _create_product(client, token, biz_id, unit_id)

    # 46. Leading zeros preserved & 47. whitespace normalized
    res = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {token}"},
        json={"supplier_id": sup_id, "product_id": prod_id, "purchase_price": "100", "currency": "IDR", "supplier_code": "  000123  "},
    )
    assert res.status_code == 201
    assert res.json()["supplier_code"] == "000123"

    # 48. Duplicate identity rejected -> 400
    res2 = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {token}"},
        json={"supplier_id": sup_id, "product_id": prod_id, "purchase_price": "200", "currency": "IDR"},
    )
    assert res2.status_code == 400


def test_preferred_supplier_invariant(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    sup1 = _create_supplier(client, token, biz_id, name="Sup 1")
    sup2 = _create_supplier(client, token, biz_id, name="Sup 2")
    prod_id = _create_product(client, token, biz_id, unit_id)

    # 49. One preferred accepted
    res1 = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {token}"},
        json={"supplier_id": sup1, "product_id": prod_id, "purchase_price": "100", "currency": "IDR", "is_preferred": True},
    )
    assert res1.status_code == 201
    item1_id = res1.json()["id"]
    assert res1.json()["is_preferred"] is True

    # 50. Second preferred automatically unsets previous preferred
    res2 = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {token}"},
        json={"supplier_id": sup2, "product_id": prod_id, "purchase_price": "90", "currency": "IDR", "is_preferred": True},
    )
    assert res2.status_code == 201
    item2_id = res2.json()["id"]
    assert res2.json()["is_preferred"] is True

    # Check item 1 is no longer preferred
    get1 = client.get(
        f"/api/v1/businesses/{biz_id}/supplier-catalog/{item1_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get1.json()["is_preferred"] is False


def test_lifecycle(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    sup_id = _create_supplier(client, token, biz_id)
    prod_id = _create_product(client, token, biz_id, unit_id)

    res = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {token}"},
        json={"supplier_id": sup_id, "product_id": prod_id, "purchase_price": "100", "currency": "IDR"},
    )
    assert res.status_code == 201
    item_id = res.json()["id"]
    assert res.json()["status"] == "ACTIVE"

    # 53. Active -> Inactive
    deact = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog/{item_id}/deactivate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert deact.status_code == 200
    assert deact.json()["status"] == "INACTIVE"

    # 54. Inactive -> Active
    act = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog/{item_id}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert act.status_code == 200
    assert act.json()["status"] == "ACTIVE"

    # 55. Active -> Archived (DELETE endpoint)
    arch = client.delete(
        f"/api/v1/businesses/{biz_id}/supplier-catalog/{item_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert arch.status_code == 200
    assert arch.json()["status"] == "ARCHIVED"

    # 57. Archived immutable (cannot update or reactivate)
    upd = client.patch(
        f"/api/v1/businesses/{biz_id}/supplier-catalog/{item_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"purchase_price": "200"},
    )
    assert upd.status_code == 400

    react = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog/{item_id}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert react.status_code == 400


def test_boundaries_independence(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    sup_id = _create_supplier(client, token, biz_id)
    prod_id = _create_product(client, token, biz_id, unit_id)
    branch_id = _create_branch(client, token, biz_id)

    # Create catalog item
    res = client.post(
        f"/api/v1/businesses/{biz_id}/supplier-catalog",
        headers={"Authorization": f"Bearer {token}"},
        json={"supplier_id": sup_id, "product_id": prod_id, "purchase_price": "3500", "currency": "IDR"},
    )
    assert res.status_code == 201
    item_id = res.json()["id"]

    # Create a purchase using different unit_price (e.g. 3700)
    purchase_res = client.post(
        f"/api/v1/businesses/{biz_id}/purchases",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "supplier_id": sup_id,
            "branch_id": branch_id,
            "purchase_date": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert purchase_res.status_code == 201
    purchase_id = purchase_res.json()["id"]

    line_res = client.post(
        f"/api/v1/businesses/{biz_id}/purchases/{purchase_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "product_id": prod_id,
            "quantity": "10",
            "unit_price": "3700",
        },
    )
    assert line_res.status_code == 201

    # 58. Changing catalog price does not change existing PurchaseLine
    client.patch(
        f"/api/v1/businesses/{biz_id}/supplier-catalog/{item_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"purchase_price": "3900"},
    )

    get_purchase = client.get(
        f"/api/v1/businesses/{biz_id}/purchases/{purchase_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert Decimal(get_purchase.json()["lines"][0]["unit_price"]) == Decimal("3700")

    # 59 & 60. Catalog creation does not mutate StockBalance or create StockMovement
    inv_res = client.get(
        f"/api/v1/businesses/{biz_id}/inventory/stock",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert inv_res.status_code == 200
    # Stock balance should be empty (no receiving/transfer happened)
    assert len(inv_res.json()) == 0

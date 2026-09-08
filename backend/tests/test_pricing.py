import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient

from app.main import app
from app.modules.authentication.repository import InMemoryUserRepository
from app.modules.account.repository import InMemoryAccountRepository
from app.modules.business.repository import InMemoryBusinessRepository
from app.modules.business_membership.repository import InMemoryBusinessMembershipRepository
from app.modules.category.repository import InMemoryCategoryRepository
from app.modules.unit.repository import InMemoryUnitRepository
from app.modules.product.repository import InMemoryProductRepository
from app.modules.product_variant.repository import InMemoryProductVariantRepository
from app.modules.barcode.repository import InMemoryBarcodeRepository
from app.modules.pricing.repository import InMemoryPriceListRepository, InMemoryPriceEntryRepository


@pytest.fixture(autouse=True)
def clear_repos():
    InMemoryUserRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryCategoryRepository.clear()
    InMemoryUnitRepository.clear()
    InMemoryProductRepository.clear()
    InMemoryProductVariantRepository.clear()
    InMemoryBarcodeRepository.clear()
    InMemoryPriceListRepository.clear()
    InMemoryPriceEntryRepository.clear()
    yield
    InMemoryUserRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryCategoryRepository.clear()
    InMemoryUnitRepository.clear()
    InMemoryProductRepository.clear()
    InMemoryProductVariantRepository.clear()
    InMemoryBarcodeRepository.clear()
    InMemoryPriceListRepository.clear()
    InMemoryPriceEntryRepository.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _register_and_get_token(client, email="user@example.com", password="Password123", full_name="Test User"):
    payload = {
        "email": email,
        "full_name": full_name,
        "password": password,
        "password_confirmation": password,
    }
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 201
    token = res.json().get("access_token")
    if not token:
        login_res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
    return token


def _create_business(client, token, name="Test Biz", btype="umkm", tz="UTC", locale="en-US"):
    return client.post(
        "/api/v1/businesses",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "business_type": btype, "timezone": tz, "locale": locale},
    )


def _get_user_id(client, token):
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    return me.json()["id"]


def _add_member(client, owner_token, biz_id, user_email, role="MEMBER", password="Password123"):
    member_token = _register_and_get_token(client, email=user_email, password=password, full_name="Member User")
    user_id = _get_user_id(client, member_token)
    client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"user_id": user_id, "role": role},
    )
    return member_token, user_id


def _create_unit(client, token, biz_id, name="Pieces", code="PCS", unit_type="COUNT"):
    return client.post(
        f"/api/v1/businesses/{biz_id}/units",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code, "unit_type": unit_type},
    )


def _create_product(client, token, biz_id, name="Indomie", code="INDOMIE", unit_id=None, product_type="GOODS"):
    if not unit_id:
        unit_res = _create_unit(client, token, biz_id)
        unit_id = unit_res.json()["id"]
    payload = {
        "name": name,
        "code": code,
        "unit_id": unit_id,
        "product_type": product_type,
    }
    return client.post(
        f"/api/v1/businesses/{biz_id}/products",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )


def _create_variant(client, token, biz_id, product_id, name="Goreng", code="IND-GRG"):
    return client.post(
        f"/api/v1/businesses/{biz_id}/products/{product_id}/variants",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code},
    )


def _create_price_list(client, token, biz_id, name="Retail", code="RETAIL", currency="IDR"):
    return client.post(
        f"/api/v1/businesses/{biz_id}/price-lists",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code, "currency": currency},
    )


def _create_price_entry(client, token, biz_id, price_list_id, product_id=None, variant_id=None, amount="3500.00", effective_from=None, effective_to=None):
    if not effective_from:
        effective_from = datetime.now(timezone.utc).isoformat()
    payload = {
        "amount": amount,
        "effective_from": effective_from,
    }
    if product_id:
        payload["product_id"] = product_id
    if variant_id:
        payload["variant_id"] = variant_id
    if effective_to:
        payload["effective_to"] = effective_to

    return client.post(
        f"/api/v1/businesses/{biz_id}/price-lists/{price_list_id}/prices",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )


def _setup(client, email="owner@example.com"):
    token = _register_and_get_token(client, email=email)
    biz_res = _create_business(client, token)
    assert biz_res.status_code == 201
    biz_id = biz_res.json()["id"]
    return token, biz_id


# ============================================================
# Price List Tests
# ============================================================
def test_create_price_list_default_first(client):
    token, biz_id = _setup(client)
    res = _create_price_list(client, token, biz_id, name="Retail List", code="RETAIL")
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Retail List"
    assert data["code"] == "RETAIL"
    assert data["currency"] == "IDR"
    assert data["is_default"] is True
    assert data["status"] == "ACTIVE"


def test_create_second_price_list_not_default(client):
    token, biz_id = _setup(client)
    _create_price_list(client, token, biz_id, name="Retail List", code="RETAIL")
    res2 = _create_price_list(client, token, biz_id, name="Wholesale List", code="WHOLESALE")
    assert res2.status_code == 201
    assert res2.json()["is_default"] is False


def test_price_list_code_uniqueness_same_business(client):
    token, biz_id = _setup(client)
    _create_price_list(client, token, biz_id, code="RETAIL")
    res2 = _create_price_list(client, token, biz_id, code="retail")
    assert res2.status_code == 409


def test_price_list_code_different_business(client):
    token_a, biz_a = _setup(client, email="a@example.com")
    token_b, biz_b = _setup(client, email="b@example.com")

    r1 = _create_price_list(client, token_a, biz_a, code="RETAIL")
    assert r1.status_code == 201

    r2 = _create_price_list(client, token_b, biz_b, code="RETAIL")
    assert r2.status_code == 201


def test_member_create_price_list_denied(client):
    token, biz_id = _setup(client)
    member_token, _ = _add_member(client, token, biz_id, "member@example.com", role="MEMBER")
    res = _create_price_list(client, member_token, biz_id, code="RETAIL")
    assert res.status_code == 403


def test_archive_price_list_reassigns_default(client):
    token, biz_id = _setup(client)
    l1 = _create_price_list(client, token, biz_id, name="List 1", code="L1").json()
    l2 = _create_price_list(client, token, biz_id, name="List 2", code="L2").json()

    assert l1["is_default"] is True
    assert l2["is_default"] is False

    # Archive l1
    del_res = client.delete(f"/api/v1/businesses/{biz_id}/price-lists/{l1['id']}", headers={"Authorization": f"Bearer {token}"})
    assert del_res.status_code == 200

    # l2 should now be default
    l2_get = client.get(f"/api/v1/businesses/{biz_id}/price-lists/{l2['id']}", headers={"Authorization": f"Bearer {token}"})
    assert l2_get.status_code == 200
    assert l2_get.json()["is_default"] is True


# ============================================================
# Price Entry Tests
# ============================================================
def test_create_product_price_entry(client):
    token, biz_id = _setup(client)
    prod = _create_product(client, token, biz_id).json()
    pl = _create_price_list(client, token, biz_id).json()

    res = _create_price_entry(client, token, biz_id, pl["id"], product_id=prod["id"], amount="3500.00")
    assert res.status_code == 201
    data = res.json()
    assert data["product_id"] == prod["id"]
    assert data["variant_id"] is None
    assert data["amount"] == "3500.00"
    assert data["currency"] == "IDR"


def test_create_variant_price_entry(client):
    token, biz_id = _setup(client)
    prod = _create_product(client, token, biz_id).json()
    var = _create_variant(client, token, biz_id, prod["id"]).json()
    pl = _create_price_list(client, token, biz_id).json()

    res = _create_price_entry(client, token, biz_id, pl["id"], variant_id=var["id"], amount="4000.00")
    assert res.status_code == 201
    assert res.json()["variant_id"] == var["id"]


def test_exactly_one_target_rule(client):
    token, biz_id = _setup(client)
    prod = _create_product(client, token, biz_id).json()
    var = _create_variant(client, token, biz_id, prod["id"]).json()
    pl = _create_price_list(client, token, biz_id).json()

    # Both targets rejected
    res1 = _create_price_entry(client, token, biz_id, pl["id"], product_id=prod["id"], variant_id=var["id"])
    assert res1.status_code in (400, 422)

    # Neither target rejected
    res2 = _create_price_entry(client, token, biz_id, pl["id"])
    assert res2.status_code in (400, 422)


def test_overlapping_active_price_entries_rejected(client):
    token, biz_id = _setup(client)
    prod = _create_product(client, token, biz_id).json()
    pl = _create_price_list(client, token, biz_id).json()

    now = datetime.now(timezone.utc)
    t1_from = (now - timedelta(days=10)).isoformat()
    t1_to = (now + timedelta(days=10)).isoformat()

    r1 = _create_price_entry(client, token, biz_id, pl["id"], product_id=prod["id"], effective_from=t1_from, effective_to=t1_to)
    assert r1.status_code == 201

    # Overlapping entry
    t2_from = (now + timedelta(days=5)).isoformat()
    t2_to = (now + timedelta(days=20)).isoformat()
    r2 = _create_price_entry(client, token, biz_id, pl["id"], product_id=prod["id"], effective_from=t2_from, effective_to=t2_to)
    assert r2.status_code == 409


def test_tenant_isolation_cross_business_target_rejected(client):
    token_a, biz_a = _setup(client, email="a@example.com")
    token_b, biz_b = _setup(client, email="b@example.com")

    prod_b = _create_product(client, token_b, biz_b).json()
    pl_a = _create_price_list(client, token_a, biz_a).json()

    # User A tries to assign Product B to Price List A
    res = _create_price_entry(client, token_a, biz_a, pl_a["id"], product_id=prod_b["id"])
    assert res.status_code == 404

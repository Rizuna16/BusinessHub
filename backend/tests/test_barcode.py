import pytest
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


def _create_product(client, token, biz_id, name="Indomie", code="INDOMIE", unit_id=None):
    if not unit_id:
        unit_res = _create_unit(client, token, biz_id)
        unit_id = unit_res.json()["id"]
    payload = {
        "name": name,
        "code": code,
        "unit_id": unit_id,
        "product_type": "GOODS",
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


def _create_barcode(client, token, biz_id, code="8992345678901", barcode_type="EAN13", product_id=None, variant_id=None):
    payload = {
        "code": code,
        "barcode_type": barcode_type,
        "product_id": product_id,
        "variant_id": variant_id,
    }
    return client.post(
        f"/api/v1/businesses/{biz_id}/barcodes",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )


def _setup(client, email="owner@example.com"):
    token = _register_and_get_token(client, email=email)
    biz_res = _create_business(client, token)
    assert biz_res.status_code == 201
    biz_id = biz_res.json()["id"]
    prod_res = _create_product(client, token, biz_id)
    assert prod_res.status_code == 201
    prod_id = prod_res.json()["id"]
    return token, biz_id, prod_id


# ============================================================
# Auth & Membership Tests
# ============================================================
def test_owner_create_barcode(client):
    token, biz_id, prod_id = _setup(client)
    res = _create_barcode(client, token, biz_id, product_id=prod_id)
    assert res.status_code == 201
    data = res.json()
    assert data["code"] == "8992345678901"
    assert data["product_id"] == prod_id
    assert data["variant_id"] is None
    assert data["status"] == "ACTIVE"


def test_member_create_barcode_denied(client):
    token, biz_id, prod_id = _setup(client)
    member_token, _ = _add_member(client, token, biz_id, "member@example.com", role="MEMBER")
    res = _create_barcode(client, member_token, biz_id, product_id=prod_id)
    assert res.status_code == 403


# ============================================================
# Target Rules Tests
# ============================================================
def test_variant_level_barcode(client):
    token, biz_id, prod_id = _setup(client)
    var_res = _create_variant(client, token, biz_id, prod_id)
    assert var_res.status_code == 201
    var_id = var_res.json()["id"]

    res = _create_barcode(client, token, biz_id, code="8992345678902", variant_id=var_id)
    assert res.status_code == 201
    assert res.json()["variant_id"] == var_id
    assert res.json()["product_id"] is None


def test_both_targets_rejected(client):
    token, biz_id, prod_id = _setup(client)
    var_res = _create_variant(client, token, biz_id, prod_id)
    var_id = var_res.json()["id"]

    res = _create_barcode(client, token, biz_id, product_id=prod_id, variant_id=var_id)
    assert res.status_code in (400, 422)


def test_neither_target_rejected(client):
    token, biz_id, prod_id = _setup(client)
    res = _create_barcode(client, token, biz_id)
    assert res.status_code in (400, 422)


def test_cross_business_product_target_rejected(client):
    token_a, biz_a, prod_a = _setup(client, email="a@example.com")
    token_b, biz_b, prod_b = _setup(client, email="b@example.com")

    res = _create_barcode(client, token_a, biz_a, product_id=prod_b)
    assert res.status_code == 404


# ============================================================
# Code Uniqueness & Leading Zeros Tests
# ============================================================
def test_duplicate_barcode_code_rejected(client):
    token, biz_id, prod_id = _setup(client)
    r1 = _create_barcode(client, token, biz_id, code="8991234567890", product_id=prod_id)
    assert r1.status_code == 201

    r2 = _create_barcode(client, token, biz_id, code="8991234567890", product_id=prod_id)
    assert r2.status_code == 409


def test_leading_zeros_preserved(client):
    token, biz_id, prod_id = _setup(client)
    code = "0123456789012"
    r = _create_barcode(client, token, biz_id, code=code, product_id=prod_id)
    assert r.status_code == 201
    assert r.json()["code"] == code


# ============================================================
# Barcode Type Validation Tests
# ============================================================
def test_ean13_length_validation(client):
    token, biz_id, prod_id = _setup(client)
    # Invalid length (10 digits)
    res = _create_barcode(client, token, biz_id, code="1234567890", barcode_type="EAN13", product_id=prod_id)
    assert res.status_code in (400, 422)


def test_code128_and_other_accepted(client):
    token, biz_id, prod_id = _setup(client)
    r1 = _create_barcode(client, token, biz_id, code="ABC-123-XYZ", barcode_type="CODE128", product_id=prod_id)
    assert r1.status_code == 201

    r2 = _create_barcode(client, token, biz_id, code="CUSTOM-0099", barcode_type="OTHER", product_id=prod_id)
    assert r2.status_code == 201


# ============================================================
# Lifecycle & Archive Tests
# ============================================================
def test_archive_barcode(client):
    token, biz_id, prod_id = _setup(client)
    b = _create_barcode(client, token, biz_id, product_id=prod_id).json()

    # Archive
    del_res = client.delete(f"/api/v1/businesses/{biz_id}/barcodes/{b['id']}", headers={"Authorization": f"Bearer {token}"})
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "ARCHIVED"

    # Excluded from active list
    list_res = client.get(f"/api/v1/businesses/{biz_id}/barcodes", headers={"Authorization": f"Bearer {token}"})
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 0

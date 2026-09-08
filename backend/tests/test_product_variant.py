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
    yield
    InMemoryUserRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryCategoryRepository.clear()
    InMemoryUnitRepository.clear()
    InMemoryProductRepository.clear()
    InMemoryProductVariantRepository.clear()


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


def _create_product(client, token, biz_id, name="Kaos Polos", code="TSHIRT", unit_id=None, product_type="GOODS"):
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


def _create_variant(client, token, biz_id, product_id, name="Black / S", code="TSHIRT-BLK-S", attributes=None):
    payload = {"name": name, "code": code}
    if attributes is not None:
        payload["attributes"] = attributes
    return client.post(
        f"/api/v1/businesses/{biz_id}/products/{product_id}/variants",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )


def _setup(client, email="owner@example.com", product_type="GOODS"):
    token = _register_and_get_token(client, email=email)
    biz_res = _create_business(client, token)
    assert biz_res.status_code == 201
    biz_id = biz_res.json()["id"]
    prod_res = _create_product(client, token, biz_id, product_type=product_type)
    assert prod_res.status_code == 201
    product_id = prod_res.json()["id"]
    return token, biz_id, product_id


# ============================================================
# Auth & Membership Tests
# ============================================================
def test_owner_create_variant(client):
    token, biz_id, prod_id = _setup(client)
    res = _create_variant(client, token, biz_id, prod_id, name="Black / M", code="TSHIRT-BLK-M")
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Black / M"
    assert data["code"] == "TSHIRT-BLK-M"
    assert data["product_id"] == prod_id
    assert data["business_id"] == biz_id
    assert data["status"] == "ACTIVE"


def test_admin_create_variant(client):
    token, biz_id, prod_id = _setup(client)
    admin_token, _ = _add_member(client, token, biz_id, "admin@example.com", role="ADMIN")
    res = _create_variant(client, admin_token, biz_id, prod_id, name="White / S", code="TSHIRT-WHT-S")
    assert res.status_code == 201


def test_member_create_variant_denied(client):
    token, biz_id, prod_id = _setup(client)
    member_token, _ = _add_member(client, token, biz_id, "member@example.com", role="MEMBER")
    res = _create_variant(client, member_token, biz_id, prod_id, name="White / S", code="TSHIRT-WHT-S")
    assert res.status_code == 403


def test_unauthenticated_create_variant_denied(client):
    token, biz_id, prod_id = _setup(client)
    res = client.post(
        f"/api/v1/businesses/{biz_id}/products/{prod_id}/variants",
        json={"name": "White / S", "code": "TSHIRT-WHT-S"},
    )
    assert res.status_code == 401


def test_member_read_variant(client):
    token, biz_id, prod_id = _setup(client)
    member_token, _ = _add_member(client, token, biz_id, "member@example.com", role="MEMBER")
    v = _create_variant(client, token, biz_id, prod_id).json()
    res = client.get(f"/api/v1/businesses/{biz_id}/products/{prod_id}/variants/{v['id']}", headers={"Authorization": f"Bearer {member_token}"})
    assert res.status_code == 200
    assert res.json()["id"] == v["id"]


# ============================================================
# Product Validation Tests
# ============================================================
def test_variant_for_service_product_rejected(client):
    token, biz_id, prod_id = _setup(client, product_type="SERVICE")
    res = _create_variant(client, token, biz_id, prod_id, name="Service Var", code="SRV-VAR")
    assert res.status_code == 400


def test_variant_for_archived_product_rejected(client):
    token, biz_id, prod_id = _setup(client)
    # Archive Product
    client.delete(f"/api/v1/businesses/{biz_id}/products/{prod_id}", headers={"Authorization": f"Bearer {token}"})

    res = _create_variant(client, token, biz_id, prod_id, name="New Var", code="NEW-VAR")
    assert res.status_code == 400


def test_variant_for_cross_business_product_rejected(client):
    token_a, biz_a, prod_a = _setup(client, email="owner_a@example.com")
    token_b, biz_b, prod_b = _setup(client, email="owner_b@example.com")

    # User A tries to create variant under biz_a using prod_b
    res = _create_variant(client, token_a, biz_a, prod_b, name="Cross Var", code="CROSS-1")
    assert res.status_code == 404


# ============================================================
# Code Uniqueness & Attributes Tests
# ============================================================
def test_variant_code_uniqueness_same_business(client):
    token, biz_id, prod_id = _setup(client)
    v1 = _create_variant(client, token, biz_id, prod_id, code="VAR-001")
    assert v1.status_code == 201

    v2 = _create_variant(client, token, biz_id, prod_id, code="var-001")
    assert v2.status_code == 409


def test_same_variant_code_different_business_allowed(client):
    token_a, biz_a, prod_a = _setup(client, email="a@example.com")
    token_b, biz_b, prod_b = _setup(client, email="b@example.com")

    v_a = _create_variant(client, token_a, biz_a, prod_a, code="VAR-001")
    assert v_a.status_code == 201

    v_b = _create_variant(client, token_b, biz_b, prod_b, code="VAR-001")
    assert v_b.status_code == 201


def test_valid_attributes_object(client):
    token, biz_id, prod_id = _setup(client)
    attrs = {"color": "Black", "size": "M", "cotton": True, "weight_g": 200}
    res = _create_variant(client, token, biz_id, prod_id, attributes=attrs)
    assert res.status_code == 201
    assert res.json()["attributes"] == attrs


# ============================================================
# Update & Archive Lifecycle Tests
# ============================================================
def test_update_and_archive_variant(client):
    token, biz_id, prod_id = _setup(client)
    v = _create_variant(client, token, biz_id, prod_id, name="Old Name", code="VAR-OLD").json()

    # Update
    patch_res = client.patch(
        f"/api/v1/businesses/{biz_id}/products/{prod_id}/variants/{v['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "New Name", "code": "VAR-NEW"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["name"] == "New Name"
    assert patch_res.json()["code"] == "VAR-NEW"

    # Archive
    del_res = client.delete(
        f"/api/v1/businesses/{biz_id}/products/{prod_id}/variants/{v['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "ARCHIVED"

    # Excluded from default list
    list_res = client.get(f"/api/v1/businesses/{biz_id}/products/{prod_id}/variants", headers={"Authorization": f"Bearer {token}"})
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 0

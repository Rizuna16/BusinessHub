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


@pytest.fixture(autouse=True)
def clear_repos():
    InMemoryUserRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryCategoryRepository.clear()
    InMemoryUnitRepository.clear()
    InMemoryProductRepository.clear()
    yield
    InMemoryUserRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryCategoryRepository.clear()
    InMemoryUnitRepository.clear()
    InMemoryProductRepository.clear()


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


def _create_category(client, token, biz_id, name="Food", code="FOOD"):
    return client.post(
        f"/api/v1/businesses/{biz_id}/categories",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code},
    )


def _create_product(client, token, biz_id, name="Indomie", code="PRD-001", unit_id=None, category_id=None, product_type="GOODS", description=None):
    payload = {
        "name": name,
        "code": code,
        "unit_id": unit_id,
        "category_id": category_id,
        "product_type": product_type,
        "description": description,
    }
    return client.post(
        f"/api/v1/businesses/{biz_id}/products",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )


def _setup(client, email="owner@example.com"):
    token = _register_and_get_token(client, email=email)
    biz_res = _create_business(client, token)
    assert biz_res.status_code == 201
    biz_id = biz_res.json()["id"]
    unit_res = _create_unit(client, token, biz_id)
    assert unit_res.status_code == 201
    unit_id = unit_res.json()["id"]
    return token, biz_id, unit_id


# ============================================================
# Creation Tests
# ============================================================
def test_owner_create_product(client):
    token, biz_id, unit_id = _setup(client)
    res = _create_product(client, token, biz_id, name="Aqua 600ml", code="PRD-001", unit_id=unit_id)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Aqua 600ml"
    assert data["code"] == "PRD-001"
    assert data["unit_id"] == unit_id
    assert data["category_id"] is None
    assert data["product_type"] == "GOODS"
    assert data["status"] == "ACTIVE"
    assert data["business_id"] == biz_id


def test_admin_create_product(client):
    token, biz_id, unit_id = _setup(client)
    admin_token, _ = _add_member(client, token, biz_id, "admin@example.com", role="ADMIN")
    res = _create_product(client, admin_token, biz_id, name="Teh Botol", code="PRD-002", unit_id=unit_id)
    assert res.status_code == 201
    assert res.json()["name"] == "Teh Botol"


def test_member_create_product_denied(client):
    token, biz_id, unit_id = _setup(client)
    member_token, _ = _add_member(client, token, biz_id, "member@example.com", role="MEMBER")
    res = _create_product(client, member_token, biz_id, name="Teh Botol", code="PRD-002", unit_id=unit_id)
    assert res.status_code == 403


def test_unauthenticated_create_product_denied(client):
    token, biz_id, unit_id = _setup(client)
    res = client.post(
        f"/api/v1/businesses/{biz_id}/products",
        json={"name": "Teh Botol", "code": "PRD-002", "unit_id": unit_id, "product_type": "GOODS"},
    )
    assert res.status_code == 401


# ============================================================
# Read Tests
# ============================================================
def test_owner_read_product(client):
    token, biz_id, unit_id = _setup(client)
    prod = _create_product(client, token, biz_id, unit_id=unit_id).json()
    res = client.get(f"/api/v1/businesses/{biz_id}/products/{prod['id']}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["id"] == prod["id"]


def test_admin_read_product(client):
    token, biz_id, unit_id = _setup(client)
    admin_token, _ = _add_member(client, token, biz_id, "admin@example.com", role="ADMIN")
    prod = _create_product(client, token, biz_id, unit_id=unit_id).json()
    res = client.get(f"/api/v1/businesses/{biz_id}/products/{prod['id']}", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200


def test_member_read_product(client):
    token, biz_id, unit_id = _setup(client)
    member_token, _ = _add_member(client, token, biz_id, "member@example.com", role="MEMBER")
    prod = _create_product(client, token, biz_id, unit_id=unit_id).json()
    res = client.get(f"/api/v1/businesses/{biz_id}/products/{prod['id']}", headers={"Authorization": f"Bearer {member_token}"})
    assert res.status_code == 200


def test_suspended_membership_read_denied(client):
    token, biz_id, unit_id = _setup(client)
    member_token, user_id = _add_member(client, token, biz_id, "member@example.com", role="MEMBER")
    prod = _create_product(client, token, biz_id, unit_id=unit_id).json()

    # Get membership ID and suspend
    members_res = client.get(f"/api/v1/businesses/{biz_id}/members", headers={"Authorization": f"Bearer {token}"})
    mem_id = [m for m in members_res.json() if m["user_id"] == user_id][0]["id"]
    client.patch(
        f"/api/v1/businesses/{biz_id}/members/{mem_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "SUSPENDED"},
    )

    res = client.get(f"/api/v1/businesses/{biz_id}/products/{prod['id']}", headers={"Authorization": f"Bearer {member_token}"})
    assert res.status_code in (403, 404)


def test_no_membership_read_denied(client):
    token, biz_id, unit_id = _setup(client)
    other_token = _register_and_get_token(client, email="other@example.com")
    prod = _create_product(client, token, biz_id, unit_id=unit_id).json()
    res = client.get(f"/api/v1/businesses/{biz_id}/products/{prod['id']}", headers={"Authorization": f"Bearer {other_token}"})
    assert res.status_code in (403, 404)


# ============================================================
# Update Tests
# ============================================================
def test_owner_update_product(client):
    token, biz_id, unit_id = _setup(client)
    prod = _create_product(client, token, biz_id, name="Old Name", code="PRD-001", unit_id=unit_id).json()
    res = client.patch(
        f"/api/v1/businesses/{biz_id}/products/{prod['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "New Name", "code": "PRD-001-NEW"},
    )
    assert res.status_code == 200
    assert res.json()["name"] == "New Name"
    assert res.json()["code"] == "PRD-001-NEW"


def test_admin_update_product(client):
    token, biz_id, unit_id = _setup(client)
    admin_token, _ = _add_member(client, token, biz_id, "admin@example.com", role="ADMIN")
    prod = _create_product(client, token, biz_id, unit_id=unit_id).json()
    res = client.patch(
        f"/api/v1/businesses/{biz_id}/products/{prod['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Updated by Admin"},
    )
    assert res.status_code == 200


def test_member_update_product_denied(client):
    token, biz_id, unit_id = _setup(client)
    member_token, _ = _add_member(client, token, biz_id, "member@example.com", role="MEMBER")
    prod = _create_product(client, token, biz_id, unit_id=unit_id).json()
    res = client.patch(
        f"/api/v1/businesses/{biz_id}/products/{prod['id']}",
        headers={"Authorization": f"Bearer {member_token}"},
        json={"name": "Updated by Member"},
    )
    assert res.status_code == 403


# ============================================================
# Archive Tests
# ============================================================
def test_owner_archive_product(client):
    token, biz_id, unit_id = _setup(client)
    prod = _create_product(client, token, biz_id, unit_id=unit_id).json()
    res = client.delete(
        f"/api/v1/businesses/{biz_id}/products/{prod['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "ARCHIVED"


def test_member_archive_product_denied(client):
    token, biz_id, unit_id = _setup(client)
    member_token, _ = _add_member(client, token, biz_id, "member@example.com", role="MEMBER")
    prod = _create_product(client, token, biz_id, unit_id=unit_id).json()
    res = client.delete(
        f"/api/v1/businesses/{biz_id}/products/{prod['id']}",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert res.status_code == 403


# ============================================================
# Tenant Isolation & Reference Validation Tests
# ============================================================
def test_tenant_isolation(client):
    token_a, biz_a, unit_a = _setup(client, email="owner_a@example.com")
    token_b, biz_b, unit_b = _setup(client, email="owner_b@example.com")

    cat_a = _create_category(client, token_a, biz_a, name="Cat A", code="CAT_A").json()
    cat_b = _create_category(client, token_b, biz_b, name="Cat B", code="CAT_B").json()

    prod_a = _create_product(client, token_a, biz_a, name="Prod A", code="PRD-A", unit_id=unit_a, category_id=cat_a["id"]).json()

    # User B cannot read Prod A
    res = client.get(f"/api/v1/businesses/{biz_a}/products/{prod_a['id']}", headers={"Authorization": f"Bearer {token_b}"})
    assert res.status_code in (403, 404)

    # User A cannot create Product assigning Unit B
    res = _create_product(client, token_a, biz_a, name="Prod Invalid Unit", code="PRD-X", unit_id=unit_b)
    assert res.status_code == 404

    # User A cannot create Product assigning Category B
    res = _create_product(client, token_a, biz_a, name="Prod Invalid Cat", code="PRD-Y", unit_id=unit_a, category_id=cat_b["id"])
    assert res.status_code == 404

    # Path spoofing check: User A trying to create under biz_b path
    res = client.post(
        f"/api/v1/businesses/{biz_b}/products",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"name": "Spoofed", "code": "SPOOF", "unit_id": unit_a, "product_type": "GOODS"},
    )
    assert res.status_code in (403, 404)


# ============================================================
# Code Uniqueness Tests
# ============================================================
def test_code_uniqueness_same_business(client):
    token, biz_id, unit_id = _setup(client)
    res1 = _create_product(client, token, biz_id, code="PRD-001", unit_id=unit_id)
    assert res1.status_code == 201

    # Case insensitive duplicate rejected
    res2 = _create_product(client, token, biz_id, code="prd-001", unit_id=unit_id)
    assert res2.status_code == 409


def test_same_code_different_business_allowed(client):
    token_a, biz_a, unit_a = _setup(client, email="owner_a@example.com")
    token_b, biz_b, unit_b = _setup(client, email="owner_b@example.com")

    res_a = _create_product(client, token_a, biz_a, code="PRD-001", unit_id=unit_a)
    assert res_a.status_code == 201

    res_b = _create_product(client, token_b, biz_b, code="PRD-001", unit_id=unit_b)
    assert res_b.status_code == 201


def test_rename_product_preserves_code(client):
    token, biz_id, unit_id = _setup(client)
    prod = _create_product(client, token, biz_id, name="Old Name", code="PRD-001", unit_id=unit_id).json()
    res = client.patch(
        f"/api/v1/businesses/{biz_id}/products/{prod['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "New Name"},
    )
    assert res.status_code == 200
    assert res.json()["code"] == "PRD-001"


# ============================================================
# Category & Unit Status Validation Tests
# ============================================================
def test_archived_category_rejected(client):
    token, biz_id, unit_id = _setup(client)
    cat = _create_category(client, token, biz_id, name="Cat 1", code="CAT_1").json()
    # Archive Category
    client.delete(f"/api/v1/businesses/{biz_id}/categories/{cat['id']}", headers={"Authorization": f"Bearer {token}"})

    res = _create_product(client, token, biz_id, name="Prod 1", code="PRD-001", unit_id=unit_id, category_id=cat["id"])
    assert res.status_code == 400


def test_archived_unit_rejected(client):
    token, biz_id, unit_id = _setup(client)
    # Archive Unit
    client.delete(f"/api/v1/businesses/{biz_id}/units/{unit_id}", headers={"Authorization": f"Bearer {token}"})

    res = _create_product(client, token, biz_id, name="Prod 1", code="PRD-001", unit_id=unit_id)
    assert res.status_code == 400


# ============================================================
# Product Type & Lifecycle Tests
# ============================================================
def test_product_types(client):
    token, biz_id, unit_id = _setup(client)
    res_g = _create_product(client, token, biz_id, name="Goods Item", code="G1", unit_id=unit_id, product_type="GOODS")
    assert res_g.status_code == 201
    assert res_g.json()["product_type"] == "GOODS"

    res_s = _create_product(client, token, biz_id, name="Service Item", code="S1", unit_id=unit_id, product_type="SERVICE")
    assert res_s.status_code == 201
    assert res_s.json()["product_type"] == "SERVICE"


def test_product_lifecycle_and_listing(client):
    token, biz_id, unit_id = _setup(client)
    prod1 = _create_product(client, token, biz_id, name="Prod 1", code="P1", unit_id=unit_id).json()
    prod2 = _create_product(client, token, biz_id, name="Prod 2", code="P2", unit_id=unit_id).json()

    # List active
    list_res = client.get(f"/api/v1/businesses/{biz_id}/products", headers={"Authorization": f"Bearer {token}"})
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 2

    # Archive prod1
    client.delete(f"/api/v1/businesses/{biz_id}/products/{prod1['id']}", headers={"Authorization": f"Bearer {token}"})

    # List default excludes archived
    list_res2 = client.get(f"/api/v1/businesses/{biz_id}/products", headers={"Authorization": f"Bearer {token}"})
    assert list_res2.status_code == 200
    assert list_res2.json()["total"] == 1
    assert list_res2.json()["items"][0]["id"] == prod2["id"]

    # Detail endpoint can still read archived product
    get_res = client.get(f"/api/v1/businesses/{biz_id}/products/{prod1['id']}", headers={"Authorization": f"Bearer {token}"})
    assert get_res.status_code == 200
    assert get_res.json()["status"] == "ARCHIVED"


# ============================================================
# Filter & Search Tests
# ============================================================
def test_list_filters_and_search(client):
    token, biz_id, unit_id = _setup(client)
    cat = _create_category(client, token, biz_id, name="Food", code="FOOD").json()

    _create_product(client, token, biz_id, name="Indomie Goreng", code="IND-01", unit_id=unit_id, category_id=cat["id"], product_type="GOODS")
    _create_product(client, token, biz_id, name="Aqua 600ml", code="AQU-01", unit_id=unit_id, product_type="GOODS")
    _create_product(client, token, biz_id, name="Laundry Service", code="LND-01", unit_id=unit_id, product_type="SERVICE")

    # Filter by category_id
    res_cat = client.get(f"/api/v1/businesses/{biz_id}/products?category_id={cat['id']}", headers={"Authorization": f"Bearer {token}"})
    assert res_cat.status_code == 200
    assert res_cat.json()["total"] == 1
    assert res_cat.json()["items"][0]["code"] == "IND-01"

    # Filter by product_type
    res_srv = client.get(f"/api/v1/businesses/{biz_id}/products?product_type=SERVICE", headers={"Authorization": f"Bearer {token}"})
    assert res_srv.status_code == 200
    assert res_srv.json()["total"] == 1
    assert res_srv.json()["items"][0]["code"] == "LND-01"

    # Search by name
    res_sch = client.get(f"/api/v1/businesses/{biz_id}/products?search=Indomie", headers={"Authorization": f"Bearer {token}"})
    assert res_sch.status_code == 200
    assert res_sch.json()["total"] == 1
    assert res_sch.json()["items"][0]["name"] == "Indomie Goreng"

    # Search by code
    res_sch_code = client.get(f"/api/v1/businesses/{biz_id}/products?search=AQU-01", headers={"Authorization": f"Bearer {token}"})
    assert res_sch_code.status_code == 200
    assert res_sch_code.json()["total"] == 1
    assert res_sch_code.json()["items"][0]["code"] == "AQU-01"

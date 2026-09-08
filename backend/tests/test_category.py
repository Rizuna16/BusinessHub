import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.authentication.repository import InMemoryUserRepository
from app.modules.account.repository import InMemoryAccountRepository
from app.modules.business.repository import InMemoryBusinessRepository
from app.modules.business_membership.repository import InMemoryBusinessMembershipRepository
from app.modules.category.repository import InMemoryCategoryRepository


@pytest.fixture(autouse=True)
def clear_repos():
    InMemoryUserRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryCategoryRepository.clear()
    yield
    InMemoryUserRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryCategoryRepository.clear()


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


def _create_category(client, token, biz_id, name="Food", code="FOOD", parent_id=None, sort_order=0):
    payload = {"name": name, "code": code, "sort_order": sort_order}
    if parent_id:
        payload["parent_id"] = parent_id
    return client.post(
        f"/api/v1/businesses/{biz_id}/categories",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )


def _setup(client, email="owner@example.com", btype="umkm"):
    token = _register_and_get_token(client, email=email)
    biz_res = _create_business(client, token, btype=btype)
    assert biz_res.status_code == 201
    biz_id = biz_res.json()["id"]
    return token, biz_id


# ============================================================
# Creation
# ============================================================
def test_owner_create_category(client):
    token, biz_id = _setup(client)
    res = _create_category(client, token, biz_id, name="Food", code="FOOD")
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Food"
    assert data["code"] == "FOOD"
    assert data["status"] == "ACTIVE"
    assert data["business_id"] == biz_id


def test_admin_create_category(client):
    token, biz_id = _setup(client)
    admin_token, _ = _add_member(client, token, biz_id, "admin@example.com", role="ADMIN")
    res = _create_category(client, admin_token, biz_id, name="Drink", code="DRINK")
    assert res.status_code == 201
    assert res.json()["name"] == "Drink"


def test_member_create_category_denied(client):
    token, biz_id = _setup(client)
    member_token, _ = _add_member(client, token, biz_id, "member@example.com", role="MEMBER")
    res = _create_category(client, member_token, biz_id, name="Drink", code="DRINK")
    assert res.status_code == 403


def test_unauthenticated_create_category_denied(client):
    token, biz_id = _setup(client)
    res = client.post(
        f"/api/v1/businesses/{biz_id}/categories",
        json={"name": "Food", "code": "FOOD"},
    )
    assert res.status_code == 401


# ============================================================
# Read
# ============================================================
def test_owner_get_category(client):
    token, biz_id = _setup(client)
    cat = _create_category(client, token, biz_id).json()
    res = client.get(f"/api/v1/businesses/{biz_id}/categories/{cat['id']}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["id"] == cat["id"]


def test_admin_get_category(client):
    token, biz_id = _setup(client)
    admin_token, _ = _add_member(client, token, biz_id, "admin@example.com", role="ADMIN")
    cat = _create_category(client, token, biz_id).json()
    res = client.get(f"/api/v1/businesses/{biz_id}/categories/{cat['id']}", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200


def test_member_get_category(client):
    token, biz_id = _setup(client)
    member_token, _ = _add_member(client, token, biz_id, "member@example.com", role="MEMBER")
    cat = _create_category(client, token, biz_id).json()
    res = client.get(f"/api/v1/businesses/{biz_id}/categories/{cat['id']}", headers={"Authorization": f"Bearer {member_token}"})
    assert res.status_code == 200


def test_suspended_membership_denied(client):
    token, biz_id = _setup(client)
    member_token, member_user_id = _add_member(client, token, biz_id, "suspended@example.com", role="MEMBER")

    members = client.get(f"/api/v1/businesses/{biz_id}/members", headers={"Authorization": f"Bearer {token}"}).json()
    mem_id = [m["id"] for m in members if m["user_id"] == member_user_id][0]
    client.patch(
        f"/api/v1/businesses/{biz_id}/members/{mem_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "SUSPENDED"},
    )

    res = client.get(f"/api/v1/businesses/{biz_id}/categories", headers={"Authorization": f"Bearer {member_token}"})
    assert res.status_code in (401, 404)


def test_removed_membership_denied(client):
    token, biz_id = _setup(client)
    member_token, member_user_id = _add_member(client, token, biz_id, "removed@example.com", role="MEMBER")

    members = client.get(f"/api/v1/businesses/{biz_id}/members", headers={"Authorization": f"Bearer {token}"}).json()
    mem_id = [m["id"] for m in members if m["user_id"] == member_user_id][0]
    client.delete(f"/api/v1/businesses/{biz_id}/members/{mem_id}", headers={"Authorization": f"Bearer {token}"})

    res = client.get(f"/api/v1/businesses/{biz_id}/categories", headers={"Authorization": f"Bearer {member_token}"})
    assert res.status_code in (401, 404)


def test_no_membership_denied(client):
    token, biz_id = _setup(client)
    outsider_token = _register_and_get_token(client, email="outsider@example.com")
    res = client.get(f"/api/v1/businesses/{biz_id}/categories", headers={"Authorization": f"Bearer {outsider_token}"})
    assert res.status_code in (401, 404)


# ============================================================
# Update
# ============================================================
def test_owner_update_category(client):
    token, biz_id = _setup(client)
    cat = _create_category(client, token, biz_id).json()
    res = client.patch(
        f"/api/v1/businesses/{biz_id}/categories/{cat['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Updated Food", "description": "desc"},
    )
    assert res.status_code == 200
    assert res.json()["name"] == "Updated Food"
    assert res.json()["description"] == "desc"


def test_admin_update_category(client):
    token, biz_id = _setup(client)
    admin_token, _ = _add_member(client, token, biz_id, "admin@example.com", role="ADMIN")
    cat = _create_category(client, token, biz_id).json()
    res = client.patch(
        f"/api/v1/businesses/{biz_id}/categories/{cat['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Updated"},
    )
    assert res.status_code == 200
    assert res.json()["name"] == "Updated"


def test_member_update_category_denied(client):
    token, biz_id = _setup(client)
    member_token, _ = _add_member(client, token, biz_id, "member@example.com", role="MEMBER")
    cat = _create_category(client, token, biz_id).json()
    res = client.patch(
        f"/api/v1/businesses/{biz_id}/categories/{cat['id']}",
        headers={"Authorization": f"Bearer {member_token}"},
        json={"name": "Hacked"},
    )
    assert res.status_code == 403


# ============================================================
# Archive
# ============================================================
def test_owner_archive_category(client):
    token, biz_id = _setup(client)
    cat = _create_category(client, token, biz_id).json()
    res = client.delete(f"/api/v1/businesses/{biz_id}/categories/{cat['id']}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["status"] == "ARCHIVED"


def test_admin_archive_category(client):
    token, biz_id = _setup(client)
    admin_token, _ = _add_member(client, token, biz_id, "admin@example.com", role="ADMIN")
    cat = _create_category(client, token, biz_id).json()
    res = client.delete(f"/api/v1/businesses/{biz_id}/categories/{cat['id']}", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    assert res.json()["status"] == "ARCHIVED"


def test_member_archive_category_denied(client):
    token, biz_id = _setup(client)
    member_token, _ = _add_member(client, token, biz_id, "member@example.com", role="MEMBER")
    cat = _create_category(client, token, biz_id).json()
    res = client.delete(f"/api/v1/businesses/{biz_id}/categories/{cat['id']}", headers={"Authorization": f"Bearer {member_token}"})
    assert res.status_code == 403


# ============================================================
# Isolation
# ============================================================
def test_cross_business_category_access_denied(client):
    token_a, biz_a = _setup(client, email="a@example.com")
    token_b, biz_b = _setup(client, email="b@example.com")
    cat_a = _create_category(client, token_a, biz_a, name="Food", code="FOOD").json()
    res = client.get(f"/api/v1/businesses/{biz_b}/categories/{cat_a['id']}", headers={"Authorization": f"Bearer {token_b}"})
    assert res.status_code in (401, 404)


def test_cross_business_patch_denied(client):
    token_a, biz_a = _setup(client, email="a2@example.com")
    token_b, biz_b = _setup(client, email="b2@example.com")
    cat_a = _create_category(client, token_a, biz_a, name="Food", code="FOOD").json()
    res = client.patch(
        f"/api/v1/businesses/{biz_b}/categories/{cat_a['id']}",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"name": "Spoofed"},
    )
    assert res.status_code in (401, 403, 404)


# ============================================================
# Code uniqueness
# ============================================================
def test_duplicate_code_same_business_rejected(client):
    token, biz_id = _setup(client)
    res1 = _create_category(client, token, biz_id, name="Food", code="FOOD")
    assert res1.status_code == 201
    res2 = _create_category(client, token, biz_id, name="Food2", code="food")
    assert res2.status_code == 409


def test_same_code_different_business_allowed(client):
    token_a, biz_a = _setup(client, email="a3@example.com")
    token_b, biz_b = _setup(client, email="b3@example.com")
    res_a = _create_category(client, token_a, biz_a, name="Food", code="FOOD")
    assert res_a.status_code == 201
    res_b = _create_category(client, token_b, biz_b, name="Food", code="FOOD")
    assert res_b.status_code == 201


# ============================================================
# Name uniqueness
# ============================================================
def test_duplicate_name_same_business_rejected(client):
    token, biz_id = _setup(client)
    res1 = _create_category(client, token, biz_id, name="Food", code="FOOD1")
    assert res1.status_code == 201
    res2 = _create_category(client, token, biz_id, name="FOOD", code="FOOD2")
    assert res2.status_code == 409


def test_same_name_different_business_allowed(client):
    token_a, biz_a = _setup(client, email="a4@example.com")
    token_b, biz_b = _setup(client, email="b4@example.com")
    res_a = _create_category(client, token_a, biz_a, name="Food", code="FC1")
    assert res_a.status_code == 201
    res_b = _create_category(client, token_b, biz_b, name="Food", code="FC2")
    assert res_b.status_code == 201


# ============================================================
# Hierarchy
# ============================================================
def test_valid_parent(client):
    token, biz_id = _setup(client)
    parent = _create_category(client, token, biz_id, name="Food", code="FOOD").json()
    child = _create_category(client, token, biz_id, name="Snacks", code="SNACK", parent_id=parent["id"]).json()
    assert child["parent_id"] == parent["id"]


def test_cross_business_parent_rejected(client):
    token_a, biz_a = _setup(client, email="a5@example.com")
    token_b, biz_b = _setup(client, email="b5@example.com")
    parent_a = _create_category(client, token_a, biz_a, name="Parent", code="PARA").json()
    res = _create_category(client, token_b, biz_b, name="Child", code="CHB", parent_id=parent_a["id"])
    assert res.status_code == 404


def test_self_parent_rejected(client):
    token, biz_id = _setup(client)
    cat = _create_category(client, token, biz_id, name="Food", code="FOOD").json()
    res = client.patch(
        f"/api/v1/businesses/{biz_id}/categories/{cat['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"parent_id": cat["id"]},
    )
    assert res.status_code == 400


def test_circular_reference_rejected(client):
    token, biz_id = _setup(client)
    a = _create_category(client, token, biz_id, name="A", code="CA").json()
    b = _create_category(client, token, biz_id, name="B", code="CB", parent_id=a["id"]).json()
    res = client.patch(
        f"/api/v1/businesses/{biz_id}/categories/{a['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"parent_id": b["id"]},
    )
    assert res.status_code == 400


def test_archived_parent_rejected(client):
    token, biz_id = _setup(client)
    parent = _create_category(client, token, biz_id, name="Parent", code="PAR").json()
    client.delete(f"/api/v1/businesses/{biz_id}/categories/{parent['id']}", headers={"Authorization": f"Bearer {token}"})
    res = _create_category(client, token, biz_id, name="Child", code="CH", parent_id=parent["id"])
    assert res.status_code == 400


def test_max_depth_enforced(client):
    token, biz_id = _setup(client)
    l1 = _create_category(client, token, biz_id, name="L1", code="L1").json()
    l2 = _create_category(client, token, biz_id, name="L2", code="L2", parent_id=l1["id"]).json()
    l3 = _create_category(client, token, biz_id, name="L3", code="L3", parent_id=l2["id"]).json()
    res = _create_category(client, token, biz_id, name="L4", code="L4", parent_id=l3["id"])
    assert res.status_code == 400


# ============================================================
# Lifecycle
# ============================================================
def test_archive_is_soft_delete(client):
    token, biz_id = _setup(client)
    cat = _create_category(client, token, biz_id, name="Food", code="FOOD").json()
    client.delete(f"/api/v1/businesses/{biz_id}/categories/{cat['id']}", headers={"Authorization": f"Bearer {token}"})
    res = client.get(f"/api/v1/businesses/{biz_id}/categories?include_archived=true", headers={"Authorization": f"Bearer {token}"})
    found = [c for c in res.json() if c["id"] == cat["id"]]
    assert len(found) == 1
    assert found[0]["status"] == "ARCHIVED"


# ============================================================
# Idempotency / Regression
# ============================================================
def test_regression_health(client):
    assert client.get("/api/v1/health").status_code == 200


def test_regression_auth(client):
    token = _register_and_get_token(client)
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200


def test_regression_business(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token).json()["id"]
    assert client.get(f"/api/v1/businesses/{biz_id}", headers={"Authorization": f"Bearer {token}"}).status_code == 200


def test_regression_template(client):
    token, biz_id = _setup(client)
    assert client.get(f"/api/v1/businesses/{biz_id}/configuration", headers={"Authorization": f"Bearer {token}"}).status_code == 200


def test_regression_branch(client):
    token, biz_id = _setup(client)
    res = client.post(
        f"/api/v1/businesses/{biz_id}/branches",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Main", "code": "MN01", "timezone": "UTC", "locale": "en-US"},
    )
    assert res.status_code == 201

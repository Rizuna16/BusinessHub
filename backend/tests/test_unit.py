import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.authentication.repository import InMemoryUserRepository
from app.modules.account.repository import InMemoryAccountRepository
from app.modules.business.repository import InMemoryBusinessRepository
from app.modules.business_membership.repository import InMemoryBusinessMembershipRepository
from app.modules.unit.repository import InMemoryUnitRepository


@pytest.fixture(autouse=True)
def clear_repos():
    InMemoryUserRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryUnitRepository.clear()
    yield
    InMemoryUserRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryUnitRepository.clear()


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


def _create_unit(client, token, biz_id, name="Kilogram", code="KG", symbol="kg", unit_type="WEIGHT", precision=3):
    return client.post(
        f"/api/v1/businesses/{biz_id}/units",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code, "symbol": symbol, "unit_type": unit_type, "precision": precision},
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
def test_owner_create_unit(client):
    token, biz_id = _setup(client)
    res = _create_unit(client, token, biz_id, name="Kilogram", code="KG")
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Kilogram"
    assert data["code"] == "KG"
    assert data["precision"] == 3
    assert data["status"] == "ACTIVE"
    assert data["business_id"] == biz_id


def test_admin_create_unit(client):
    token, biz_id = _setup(client)
    admin_token, _ = _add_member(client, token, biz_id, "admin@example.com", role="ADMIN")
    res = _create_unit(client, admin_token, biz_id, name="Piece", code="PCS", unit_type="COUNT", precision=0)
    assert res.status_code == 201
    assert res.json()["code"] == "PCS"


def test_member_create_unit_denied(client):
    token, biz_id = _setup(client)
    member_token, _ = _add_member(client, token, biz_id, "member@example.com", role="MEMBER")
    res = _create_unit(client, member_token, biz_id, name="Piece", code="PCS")
    assert res.status_code == 403


def test_unauthenticated_create_unit_denied(client):
    token, biz_id = _setup(client)
    res = client.post(
        f"/api/v1/businesses/{biz_id}/units",
        json={"name": "Piece", "code": "PCS"},
    )
    assert res.status_code == 401


# ============================================================
# Read
# ============================================================
def test_owner_get_unit(client):
    token, biz_id = _setup(client)
    u = _create_unit(client, token, biz_id).json()
    res = client.get(f"/api/v1/businesses/{biz_id}/units/{u['id']}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["id"] == u["id"]


def test_admin_get_unit(client):
    token, biz_id = _setup(client)
    admin_token, _ = _add_member(client, token, biz_id, "admin@example.com", role="ADMIN")
    u = _create_unit(client, token, biz_id).json()
    res = client.get(f"/api/v1/businesses/{biz_id}/units/{u['id']}", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200


def test_member_get_unit(client):
    token, biz_id = _setup(client)
    member_token, _ = _add_member(client, token, biz_id, "member@example.com", role="MEMBER")
    u = _create_unit(client, token, biz_id).json()
    res = client.get(f"/api/v1/businesses/{biz_id}/units/{u['id']}", headers={"Authorization": f"Bearer {member_token}"})
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

    res = client.get(f"/api/v1/businesses/{biz_id}/units", headers={"Authorization": f"Bearer {member_token}"})
    assert res.status_code in (401, 404)


def test_removed_membership_denied(client):
    token, biz_id = _setup(client)
    member_token, member_user_id = _add_member(client, token, biz_id, "removed@example.com", role="MEMBER")

    members = client.get(f"/api/v1/businesses/{biz_id}/members", headers={"Authorization": f"Bearer {token}"}).json()
    mem_id = [m["id"] for m in members if m["user_id"] == member_user_id][0]
    client.delete(f"/api/v1/businesses/{biz_id}/members/{mem_id}", headers={"Authorization": f"Bearer {token}"})

    res = client.get(f"/api/v1/businesses/{biz_id}/units", headers={"Authorization": f"Bearer {member_token}"})
    assert res.status_code in (401, 404)


# ============================================================
# Update
# ============================================================
def test_owner_update_unit(client):
    token, biz_id = _setup(client)
    u = _create_unit(client, token, biz_id).json()
    res = client.patch(
        f"/api/v1/businesses/{biz_id}/units/{u['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Kilo", "precision": 2},
    )
    assert res.status_code == 200
    assert res.json()["name"] == "Kilo"
    assert res.json()["precision"] == 2


def test_admin_update_unit(client):
    token, biz_id = _setup(client)
    admin_token, _ = _add_member(client, token, biz_id, "admin@example.com", role="ADMIN")
    u = _create_unit(client, token, biz_id).json()
    res = client.patch(
        f"/api/v1/businesses/{biz_id}/units/{u['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"symbol": "KG"},
    )
    assert res.status_code == 200


def test_member_update_unit_denied(client):
    token, biz_id = _setup(client)
    member_token, _ = _add_member(client, token, biz_id, "member@example.com", role="MEMBER")
    u = _create_unit(client, token, biz_id).json()
    res = client.patch(
        f"/api/v1/businesses/{biz_id}/units/{u['id']}",
        headers={"Authorization": f"Bearer {member_token}"},
        json={"name": "Hacked"},
    )
    assert res.status_code == 403


# ============================================================
# Archive
# ============================================================
def test_owner_archive_unit(client):
    token, biz_id = _setup(client)
    u = _create_unit(client, token, biz_id).json()
    res = client.delete(f"/api/v1/businesses/{biz_id}/units/{u['id']}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["status"] == "ARCHIVED"


def test_admin_archive_unit(client):
    token, biz_id = _setup(client)
    admin_token, _ = _add_member(client, token, biz_id, "admin@example.com", role="ADMIN")
    u = _create_unit(client, token, biz_id).json()
    res = client.delete(f"/api/v1/businesses/{biz_id}/units/{u['id']}", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    assert res.json()["status"] == "ARCHIVED"


def test_member_archive_unit_denied(client):
    token, biz_id = _setup(client)
    member_token, _ = _add_member(client, token, biz_id, "member@example.com", role="MEMBER")
    u = _create_unit(client, token, biz_id).json()
    res = client.delete(f"/api/v1/businesses/{biz_id}/units/{u['id']}", headers={"Authorization": f"Bearer {member_token}"})
    assert res.status_code == 403


# ============================================================
# Isolation
# ============================================================
def test_cross_business_unit_access_denied(client):
    token_a, biz_a = _setup(client, email="a@example.com")
    token_b, biz_b = _setup(client, email="b@example.com")
    u_a = _create_unit(client, token_a, biz_a, name="Gram", code="G").json()
    res = client.get(f"/api/v1/businesses/{biz_b}/units/{u_a['id']}", headers={"Authorization": f"Bearer {token_b}"})
    assert res.status_code in (401, 404)


# ============================================================
# Code uniqueness
# ============================================================
def test_duplicate_code_same_business_rejected(client):
    token, biz_id = _setup(client)
    res1 = _create_unit(client, token, biz_id, name="Gram", code="G")
    assert res1.status_code == 201
    res2 = _create_unit(client, token, biz_id, name="Gram2", code="g")
    assert res2.status_code == 409


def test_same_code_different_business_allowed(client):
    token_a, biz_a = _setup(client, email="a3@example.com")
    token_b, biz_b = _setup(client, email="b3@example.com")
    res_a = _create_unit(client, token_a, biz_a, name="Gram", code="G")
    assert res_a.status_code == 201
    res_b = _create_unit(client, token_b, biz_b, name="Gram", code="G")
    assert res_b.status_code == 201


# ============================================================
# Precision validation
# ============================================================
def test_valid_precision(client):
    token, biz_id = _setup(client)
    res = _create_unit(client, token, biz_id, name="P", code="P", precision=6)
    assert res.status_code == 201


def test_negative_precision_rejected(client):
    token, biz_id = _setup(client)
    res = _create_unit(client, token, biz_id, name="P", code="P", precision=-1)
    assert res.status_code == 422


def test_precision_too_high_rejected(client):
    token, biz_id = _setup(client)
    res = _create_unit(client, token, biz_id, name="P", code="P", precision=7)
    assert res.status_code == 422


# ============================================================
# Unit type validation
# ============================================================
def test_valid_unit_type(client):
    token, biz_id = _setup(client)
    res = _create_unit(client, token, biz_id, name="Liter", code="L", unit_type="VOLUME")
    assert res.status_code == 201
    assert res.json()["unit_type"] == "VOLUME"


def test_invalid_unit_type_rejected(client):
    token, biz_id = _setup(client)
    res = _create_unit(client, token, biz_id, name="Liter", code="L", unit_type="INVALID_TYPE")
    assert res.status_code == 422


# ============================================================
# Lifecycle
# ============================================================
def test_archive_is_soft_delete(client):
    token, biz_id = _setup(client)
    u = _create_unit(client, token, biz_id, name="Gram", code="G").json()
    client.delete(f"/api/v1/businesses/{biz_id}/units/{u['id']}", headers={"Authorization": f"Bearer {token}"})
    res = client.get(f"/api/v1/businesses/{biz_id}/units?include_archived=true", headers={"Authorization": f"Bearer {token}"})
    found = [item for item in res.json() if item["id"] == u["id"]]
    assert len(found) == 1
    assert found[0]["status"] == "ARCHIVED"

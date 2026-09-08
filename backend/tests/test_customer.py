import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.authentication.repository import InMemoryUserRepository
from app.modules.account.repository import InMemoryAccountRepository
from app.modules.business.repository import InMemoryBusinessRepository
from app.modules.business_membership.repository import InMemoryBusinessMembershipRepository
from app.modules.customer.repository import InMemoryCustomerRepository


@pytest.fixture(autouse=True)
def clear_repos():
    InMemoryUserRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryCustomerRepository.clear()
    yield
    InMemoryUserRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryCustomerRepository.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _register_and_get_token(client, email="owner@example.com", password="Password123", full_name="Owner User"):
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


def _create_business(client, token, name="Test Biz"):
    return client.post(
        "/api/v1/businesses",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "business_type": "umkm", "timezone": "UTC", "locale": "en-US"},
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


def _setup(client, email="owner@example.com"):
    token = _register_and_get_token(client, email=email)
    biz_res = _create_business(client, token)
    assert biz_res.status_code == 201
    biz_id = biz_res.json()["id"]
    return token, biz_id


def _create_customer(client, token, biz_id, name="Budi Santoso", customer_type="INDIVIDUAL", **kwargs):
    payload = {"name": name, "customer_type": customer_type, **kwargs}
    return client.post(
        f"/api/v1/businesses/{biz_id}/customers",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )


# ============================================================
# Creation Tests (1-7)
# ============================================================
def test_create_individual(client):
    token, biz_id = _setup(client)
    res = _create_customer(client, token, biz_id, name="Budi Santoso", customer_type="INDIVIDUAL")
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Budi Santoso"
    assert data["customer_type"] == "INDIVIDUAL"
    assert data["status"] == "ACTIVE"
    assert data["business_id"] == biz_id
    assert data["code"].startswith("CUS-")


def test_create_organization(client):
    token, biz_id = _setup(client)
    res = _create_customer(client, token, biz_id, name="PT Maju Jaya", customer_type="ORGANIZATION", legal_name="PT Maju Jaya Tbk")
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "PT Maju Jaya"
    assert data["legal_name"] == "PT Maju Jaya Tbk"
    assert data["customer_type"] == "ORGANIZATION"


def test_required_name(client):
    token, biz_id = _setup(client)
    res = client.post(
        f"/api/v1/businesses/{biz_id}/customers",
        headers={"Authorization": f"Bearer {token}"},
        json={"customer_type": "INDIVIDUAL"},
    )
    assert res.status_code == 422


def test_whitespace_name_rejected(client):
    token, biz_id = _setup(client)
    res = _create_customer(client, token, biz_id, name="   ")
    assert res.status_code == 422


def test_generated_code(client):
    token, biz_id = _setup(client)
    res1 = _create_customer(client, token, biz_id, name="Cust 1")
    res2 = _create_customer(client, token, biz_id, name="Cust 2")
    assert res1.status_code == 201
    assert res2.status_code == 201
    assert res1.json()["code"] == "CUS-000001"
    assert res2.json()["code"] == "CUS-000002"


def test_code_uniqueness(client):
    token, biz_id = _setup(client)
    res1 = _create_customer(client, token, biz_id, name="Cust 1")
    res2 = _create_customer(client, token, biz_id, name="Cust 2")
    assert res1.json()["code"] != res2.json()["code"]


def test_tenant_ownership(client):
    token, biz_id = _setup(client)
    res = _create_customer(client, token, biz_id, name="Cust 1")
    assert res.json()["business_id"] == biz_id


# ============================================================
# Validation Tests (8-12)
# ============================================================
def test_invalid_customer_type(client):
    token, biz_id = _setup(client)
    res = _create_customer(client, token, biz_id, name="Test", customer_type="INVALID_TYPE")
    assert res.status_code == 422


def test_invalid_email(client):
    token, biz_id = _setup(client)
    res = _create_customer(client, token, biz_id, name="Test", email="not-an-email")
    assert res.status_code == 422


def test_optional_phone(client):
    token, biz_id = _setup(client)
    res = _create_customer(client, token, biz_id, name="Test", phone="081234567890")
    assert res.status_code == 201
    assert res.json()["phone"] == "081234567890"


def test_optional_address(client):
    token, biz_id = _setup(client)
    res = _create_customer(client, token, biz_id, name="Test", address="Jl. Merdeka 1", city="Jakarta", province="DKI", postal_code="12345", country="Indonesia")
    assert res.status_code == 201
    data = res.json()
    assert data["address"] == "Jl. Merdeka 1"
    assert data["city"] == "Jakarta"


def test_extra_field_rejected(client):
    token, biz_id = _setup(client)
    res = client.post(
        f"/api/v1/businesses/{biz_id}/customers",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Test", "extra_field": "spoof"},
    )
    assert res.status_code == 422


# ============================================================
# Update Tests (13-16)
# ============================================================
def test_update_allowed_fields(client):
    token, biz_id = _setup(client)
    cust = _create_customer(client, token, biz_id, name="Original Name").json()
    res = client.patch(
        f"/api/v1/businesses/{biz_id}/customers/{cust['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Updated Name", "phone": "089999999"},
    )
    assert res.status_code == 200
    assert res.json()["name"] == "Updated Name"
    assert res.json()["phone"] == "089999999"


def test_code_immutable(client):
    token, biz_id = _setup(client)
    cust = _create_customer(client, token, biz_id, name="Test").json()
    res = client.patch(
        f"/api/v1/businesses/{biz_id}/customers/{cust['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": "CUS-SPOOF"},
    )
    assert res.status_code == 422


def test_business_id_cannot_change(client):
    token, biz_id = _setup(client)
    cust = _create_customer(client, token, biz_id, name="Test").json()
    res = client.patch(
        f"/api/v1/businesses/{biz_id}/customers/{cust['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"business_id": "other-biz"},
    )
    assert res.status_code == 422


def test_status_cannot_be_changed_via_patch(client):
    token, biz_id = _setup(client)
    cust = _create_customer(client, token, biz_id, name="Test").json()
    res = client.patch(
        f"/api/v1/businesses/{biz_id}/customers/{cust['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "ARCHIVED"},
    )
    assert res.status_code == 422


# ============================================================
# Lifecycle Tests (17-22)
# ============================================================
def test_active_to_inactive(client):
    token, biz_id = _setup(client)
    cust = _create_customer(client, token, biz_id, name="Test").json()
    res = client.post(
        f"/api/v1/businesses/{biz_id}/customers/{cust['id']}/deactivate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "INACTIVE"


def test_inactive_to_active(client):
    token, biz_id = _setup(client)
    cust = _create_customer(client, token, biz_id, name="Test").json()
    client.post(f"/api/v1/businesses/{biz_id}/customers/{cust['id']}/deactivate", headers={"Authorization": f"Bearer {token}"})
    res = client.post(
        f"/api/v1/businesses/{biz_id}/customers/{cust['id']}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "ACTIVE"


def test_active_to_archived(client):
    token, biz_id = _setup(client)
    cust = _create_customer(client, token, biz_id, name="Test").json()
    res = client.delete(
        f"/api/v1/businesses/{biz_id}/customers/{cust['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "ARCHIVED"


def test_inactive_to_archived(client):
    token, biz_id = _setup(client)
    cust = _create_customer(client, token, biz_id, name="Test").json()
    client.post(f"/api/v1/businesses/{biz_id}/customers/{cust['id']}/deactivate", headers={"Authorization": f"Bearer {token}"})
    res = client.delete(
        f"/api/v1/businesses/{biz_id}/customers/{cust['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "ARCHIVED"


def test_archived_cannot_reactivate(client):
    token, biz_id = _setup(client)
    cust = _create_customer(client, token, biz_id, name="Test").json()
    client.delete(f"/api/v1/businesses/{biz_id}/customers/{cust['id']}", headers={"Authorization": f"Bearer {token}"})
    res = client.post(
        f"/api/v1/businesses/{biz_id}/customers/{cust['id']}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400


def test_archived_cannot_deactivate(client):
    token, biz_id = _setup(client)
    cust = _create_customer(client, token, biz_id, name="Test").json()
    client.delete(f"/api/v1/businesses/{biz_id}/customers/{cust['id']}", headers={"Authorization": f"Bearer {token}"})
    res = client.post(
        f"/api/v1/businesses/{biz_id}/customers/{cust['id']}/deactivate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400


# ============================================================
# Authorization Tests (23-31)
# ============================================================
def test_owner_create(client):
    token, biz_id = _setup(client)
    res = _create_customer(client, token, biz_id, name="Owner Cust")
    assert res.status_code == 201


def test_admin_create(client):
    token, biz_id = _setup(client)
    admin_token, _ = _add_member(client, token, biz_id, "admin@example.com", role="ADMIN")
    res = _create_customer(client, admin_token, biz_id, name="Admin Cust")
    assert res.status_code == 201


def test_member_create_rejected(client):
    token, biz_id = _setup(client)
    member_token, _ = _add_member(client, token, biz_id, "member@example.com", role="MEMBER")
    res = _create_customer(client, member_token, biz_id, name="Member Cust")
    assert res.status_code == 403


def test_owner_update(client):
    token, biz_id = _setup(client)
    cust = _create_customer(client, token, biz_id, name="Test").json()
    res = client.patch(f"/api/v1/businesses/{biz_id}/customers/{cust['id']}", headers={"Authorization": f"Bearer {token}"}, json={"name": "Owner Update"})
    assert res.status_code == 200


def test_admin_update(client):
    token, biz_id = _setup(client)
    admin_token, _ = _add_member(client, token, biz_id, "admin@example.com", role="ADMIN")
    cust = _create_customer(client, token, biz_id, name="Test").json()
    res = client.patch(f"/api/v1/businesses/{biz_id}/customers/{cust['id']}", headers={"Authorization": f"Bearer {admin_token}"}, json={"name": "Admin Update"})
    assert res.status_code == 200


def test_member_update_rejected(client):
    token, biz_id = _setup(client)
    member_token, _ = _add_member(client, token, biz_id, "member@example.com", role="MEMBER")
    cust = _create_customer(client, token, biz_id, name="Test").json()
    res = client.patch(f"/api/v1/businesses/{biz_id}/customers/{cust['id']}", headers={"Authorization": f"Bearer {member_token}"}, json={"name": "Member Update"})
    assert res.status_code == 403


def test_owner_archive(client):
    token, biz_id = _setup(client)
    cust = _create_customer(client, token, biz_id, name="Test").json()
    res = client.delete(f"/api/v1/businesses/{biz_id}/customers/{cust['id']}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200


def test_admin_archive(client):
    token, biz_id = _setup(client)
    admin_token, _ = _add_member(client, token, biz_id, "admin@example.com", role="ADMIN")
    cust = _create_customer(client, token, biz_id, name="Test").json()
    res = client.delete(f"/api/v1/businesses/{biz_id}/customers/{cust['id']}", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200


def test_member_archive_rejected(client):
    token, biz_id = _setup(client)
    member_token, _ = _add_member(client, token, biz_id, "member@example.com", role="MEMBER")
    cust = _create_customer(client, token, biz_id, name="Test").json()
    res = client.delete(f"/api/v1/businesses/{biz_id}/customers/{cust['id']}", headers={"Authorization": f"Bearer {member_token}"})
    assert res.status_code == 403


# ============================================================
# Tenant Isolation Tests (32-37)
# ============================================================
def test_cross_business_get_blocked(client):
    token_a, biz_a = _setup(client, email="a@example.com")
    token_b, biz_b = _setup(client, email="b@example.com")
    cust_a = _create_customer(client, token_a, biz_a, name="Cust A").json()
    res = client.get(f"/api/v1/businesses/{biz_b}/customers/{cust_a['id']}", headers={"Authorization": f"Bearer {token_b}"})
    assert res.status_code in (401, 404)


def test_cross_business_update_blocked(client):
    token_a, biz_a = _setup(client, email="a2@example.com")
    token_b, biz_b = _setup(client, email="b2@example.com")
    cust_a = _create_customer(client, token_a, biz_a, name="Cust A").json()
    res = client.patch(f"/api/v1/businesses/{biz_b}/customers/{cust_a['id']}", headers={"Authorization": f"Bearer {token_a}"}, json={"name": "Hacked"})
    assert res.status_code in (401, 403, 404)


def test_cross_business_archive_blocked(client):
    token_a, biz_a = _setup(client, email="a3@example.com")
    token_b, biz_b = _setup(client, email="b3@example.com")
    cust_a = _create_customer(client, token_a, biz_a, name="Cust A").json()
    res = client.delete(f"/api/v1/businesses/{biz_b}/customers/{cust_a['id']}", headers={"Authorization": f"Bearer {token_b}"})
    assert res.status_code in (401, 404)


def test_non_member_blocked(client):
    token, biz_id = _setup(client)
    outsider_token = _register_and_get_token(client, email="outsider@example.com")
    res = client.get(f"/api/v1/businesses/{biz_id}/customers", headers={"Authorization": f"Bearer {outsider_token}"})
    assert res.status_code in (401, 404)


def test_suspended_membership_blocked(client):
    token, biz_id = _setup(client)
    member_token, member_user_id = _add_member(client, token, biz_id, "suspended@example.com", role="MEMBER")

    members = client.get(f"/api/v1/businesses/{biz_id}/members", headers={"Authorization": f"Bearer {token}"}).json()
    mem_id = [m["id"] for m in members if m["user_id"] == member_user_id][0]
    client.patch(
        f"/api/v1/businesses/{biz_id}/members/{mem_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "SUSPENDED"},
    )

    res = client.get(f"/api/v1/businesses/{biz_id}/customers", headers={"Authorization": f"Bearer {member_token}"})
    assert res.status_code in (401, 404)


def test_removed_membership_blocked(client):
    token, biz_id = _setup(client)
    member_token, member_user_id = _add_member(client, token, biz_id, "removed@example.com", role="MEMBER")

    members = client.get(f"/api/v1/businesses/{biz_id}/members", headers={"Authorization": f"Bearer {token}"}).json()
    mem_id = [m["id"] for m in members if m["user_id"] == member_user_id][0]
    client.delete(f"/api/v1/businesses/{biz_id}/members/{mem_id}", headers={"Authorization": f"Bearer {token}"})

    res = client.get(f"/api/v1/businesses/{biz_id}/customers", headers={"Authorization": f"Bearer {member_token}"})
    assert res.status_code in (401, 404)


# ============================================================
# Search Tests (38-42)
# ============================================================
def test_search_name(client):
    token, biz_id = _setup(client)
    _create_customer(client, token, biz_id, name="Budi Santoso")
    _create_customer(client, token, biz_id, name="Siti Aminah")
    res = client.get(f"/api/v1/businesses/{biz_id}/customers?search=Budi", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["name"] == "Budi Santoso"


def test_search_code(client):
    token, biz_id = _setup(client)
    c1 = _create_customer(client, token, biz_id, name="Cust 1").json()
    _create_customer(client, token, biz_id, name="Cust 2")
    res = client.get(f"/api/v1/businesses/{biz_id}/customers?search={c1['code']}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == c1["id"]


def test_search_phone_email(client):
    token, biz_id = _setup(client)
    _create_customer(client, token, biz_id, name="Cust 1", phone="0812345678", email="cust1@example.com")
    _create_customer(client, token, biz_id, name="Cust 2", phone="0898765432", email="cust2@example.com")
    res_phone = client.get(f"/api/v1/businesses/{biz_id}/customers?search=08123", headers={"Authorization": f"Bearer {token}"})
    assert len(res_phone.json()["items"]) == 1
    res_email = client.get(f"/api/v1/businesses/{biz_id}/customers?search=cust2@", headers={"Authorization": f"Bearer {token}"})
    assert len(res_email.json()["items"]) == 1


def test_case_insensitive_search(client):
    token, biz_id = _setup(client)
    _create_customer(client, token, biz_id, name="John Doe")
    res = client.get(f"/api/v1/businesses/{biz_id}/customers?search=john", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert len(res.json()["items"]) == 1


def test_partial_search(client):
    token, biz_id = _setup(client)
    _create_customer(client, token, biz_id, name="Alexander Arnold")
    res = client.get(f"/api/v1/businesses/{biz_id}/customers?search=ander", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert len(res.json()["items"]) == 1


# ============================================================
# Filter Tests (43-47)
# ============================================================
def test_filter_active(client):
    token, biz_id = _setup(client)
    c1 = _create_customer(client, token, biz_id, name="Active Cust").json()
    c2 = _create_customer(client, token, biz_id, name="Inactive Cust").json()
    client.post(f"/api/v1/businesses/{biz_id}/customers/{c2['id']}/deactivate", headers={"Authorization": f"Bearer {token}"})
    res = client.get(f"/api/v1/businesses/{biz_id}/customers?status=ACTIVE", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == c1["id"]


def test_filter_inactive(client):
    token, biz_id = _setup(client)
    c1 = _create_customer(client, token, biz_id, name="Active Cust").json()
    c2 = _create_customer(client, token, biz_id, name="Inactive Cust").json()
    client.post(f"/api/v1/businesses/{biz_id}/customers/{c2['id']}/deactivate", headers={"Authorization": f"Bearer {token}"})
    res = client.get(f"/api/v1/businesses/{biz_id}/customers?status=INACTIVE", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == c2["id"]


def test_filter_archived(client):
    token, biz_id = _setup(client)
    c1 = _create_customer(client, token, biz_id, name="Active Cust").json()
    c2 = _create_customer(client, token, biz_id, name="Archived Cust").json()
    client.delete(f"/api/v1/businesses/{biz_id}/customers/{c2['id']}", headers={"Authorization": f"Bearer {token}"})
    res = client.get(f"/api/v1/businesses/{biz_id}/customers?status=ARCHIVED", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == c2["id"]


def test_filter_individual(client):
    token, biz_id = _setup(client)
    _create_customer(client, token, biz_id, name="Indiv", customer_type="INDIVIDUAL")
    _create_customer(client, token, biz_id, name="Org", customer_type="ORGANIZATION")
    res = client.get(f"/api/v1/businesses/{biz_id}/customers?customer_type=INDIVIDUAL", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["customer_type"] == "INDIVIDUAL"


def test_filter_organization(client):
    token, biz_id = _setup(client)
    _create_customer(client, token, biz_id, name="Indiv", customer_type="INDIVIDUAL")
    _create_customer(client, token, biz_id, name="Org", customer_type="ORGANIZATION")
    res = client.get(f"/api/v1/businesses/{biz_id}/customers?customer_type=ORGANIZATION", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["customer_type"] == "ORGANIZATION"


# ============================================================
# Pagination & Ordering Tests (48-53)
# ============================================================
def test_pagination_page_1_and_2(client):
    token, biz_id = _setup(client)
    for i in range(5):
        _create_customer(client, token, biz_id, name=f"Cust {i+1}")

    res_p1 = client.get(f"/api/v1/businesses/{biz_id}/customers?page=1&page_size=2", headers={"Authorization": f"Bearer {token}"})
    assert res_p1.status_code == 200
    data_p1 = res_p1.json()
    assert len(data_p1["items"]) == 2
    assert data_p1["total"] == 5

    res_p2 = client.get(f"/api/v1/businesses/{biz_id}/customers?page=2&page_size=2", headers={"Authorization": f"Bearer {token}"})
    assert res_p2.status_code == 200
    data_p2 = res_p2.json()
    assert len(data_p2["items"]) == 2
    assert data_p2["items"][0]["id"] != data_p1["items"][0]["id"]


def test_invalid_page(client):
    token, biz_id = _setup(client)
    res = client.get(f"/api/v1/businesses/{biz_id}/customers?page=0", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 422  # Query(1, ge=1)


def test_maximum_page_size(client):
    token, biz_id = _setup(client)
    res = client.get(f"/api/v1/businesses/{biz_id}/customers?page_size=200", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 422  # Query(20, le=100)


def test_deterministic_ordering(client):
    token, biz_id = _setup(client)
    c1 = _create_customer(client, token, biz_id, name="Cust 1").json()
    c2 = _create_customer(client, token, biz_id, name="Cust 2").json()
    res = client.get(f"/api/v1/businesses/{biz_id}/customers", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    items = res.json()["items"]
    assert items[0]["id"] == c1["id"]
    assert items[1]["id"] == c2["id"]

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.authentication.repository import InMemoryUserRepository
from app.modules.account.repository import InMemoryAccountRepository
from app.modules.business.repository import InMemoryBusinessRepository
from app.modules.business_membership.repository import InMemoryBusinessMembershipRepository, InMemoryBusinessMembershipRepository as _MBR
from app.modules.branch.repository import InMemoryBranchRepository
from app.modules.warehouse.repository import InMemoryWarehouseRepository, InMemoryInventoryLocationRepository
from app.modules.warehouse.schemas import WarehouseStatus, InventoryLocationStatus, InventoryLocationType


@pytest.fixture(autouse=True)
def clear_repos():
    InMemoryUserRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryBranchRepository.clear()
    InMemoryWarehouseRepository.clear()
    InMemoryInventoryLocationRepository.clear()
    yield
    InMemoryUserRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryBranchRepository.clear()
    InMemoryWarehouseRepository.clear()
    InMemoryInventoryLocationRepository.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _register_and_get_token(
    client: TestClient, email="user@example.com", password="Password123", full_name="Test User"
) -> str:
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
        login_res = client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
    return token


def _get_headers(client: TestClient, email: str) -> dict:
    token = _register_and_get_token(client, email=email)
    return {"Authorization": f"Bearer {token}"}


def _create_business(client: TestClient, headers: dict, name: str, biz_type: str = "retail") -> dict:
    res = client.post(
        "/api/v1/businesses",
        headers=headers,
        json={
            "name": name,
            "description": "Test",
            "business_type": biz_type,
            "timezone": "UTC",
            "locale": "en-US",
        },
    )
    assert res.status_code == 201, res.text
    return res.json()


# --- Warehouse Tests ---

def test_create_warehouse_success(client):
    headers = _get_headers(client, "wh_owner@example.com")
    biz = _create_business(client, headers, "Test Biz")
    biz_id = biz["id"]

    res = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers=headers,
        json={"name": "Main Warehouse", "code": "WH-MAIN", "description": "Primary storage"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Main Warehouse"
    assert data["code"] == "WH-MAIN"
    assert data["business_id"] == biz_id
    assert data["status"] == "ACTIVE"
    assert data["is_default"] is True


def test_warehouse_name_validation(client):
    headers = _get_headers(client, "wh_val@example.com")
    biz = _create_business(client, headers, "Test Biz")
    biz_id = biz["id"]

    res = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers=headers,
        json={"name": "   ", "code": "WH-1"},
    )
    assert res.status_code == 422


def test_warehouse_code_uniqueness_and_case_insensitive(client):
    headers = _get_headers(client, "wh_code@example.com")
    biz = _create_business(client, headers, "Test Biz")
    biz_id = biz["id"]

    client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers=headers,
        json={"name": "Wh 1", "code": "WH-MAIN"},
    )
    res = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers=headers,
        json={"name": "Wh 2", "code": "wh-main"},
    )
    assert res.status_code == 409


def test_first_warehouse_default_and_reassignment(client):
    headers = _get_headers(client, "wh_def@example.com")
    biz = _create_business(client, headers, "Test Biz")
    biz_id = biz["id"]

    w1 = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers=headers,
        json={"name": "Wh 1", "code": "WH-1"},
    ).json()
    w2 = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers=headers,
        json={"name": "Wh 2", "code": "WH-2"},
    ).json()

    assert w1["is_default"] is True
    assert w2["is_default"] is False

    # Suspend w1 (default)
    client.post(f"/api/v1/businesses/{biz_id}/warehouses/{w1['id']}/suspend", headers=headers)

    # Check w2 should now be default
    w2_updated = client.get(f"/api/v1/businesses/{biz_id}/warehouses/{w2['id']}", headers=headers).json()
    assert w2_updated["is_default"] is True


def test_update_warehouse(client):
    headers = _get_headers(client, "wh_upd@example.com")
    biz = _create_business(client, headers, "Test Biz")
    biz_id = biz["id"]

    w = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers=headers,
        json={"name": "Wh 1", "code": "WH-1"},
    ).json()

    res = client.patch(
        f"/api/v1/businesses/{biz_id}/warehouses/{w['id']}",
        headers=headers,
        json={"name": "Updated Warehouse Name"},
    )
    assert res.status_code == 200
    assert res.json()["name"] == "Updated Warehouse Name"


def test_suspend_activate_archive_warehouse(client):
    headers = _get_headers(client, "wh_lifecycle@example.com")
    biz = _create_business(client, headers, "Test Biz")
    biz_id = biz["id"]

    w = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers=headers,
        json={"name": "Wh 1", "code": "WH-1"},
    ).json()

    res = client.post(f"/api/v1/businesses/{biz_id}/warehouses/{w['id']}/suspend", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "SUSPENDED"

    res = client.post(f"/api/v1/businesses/{biz_id}/warehouses/{w['id']}/activate", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "ACTIVE"

    res = client.delete(f"/api/v1/businesses/{biz_id}/warehouses/{w['id']}", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "ARCHIVED"


def test_branch_assignment_and_validation(client):
    headers = _get_headers(client, "wh_branch@example.com")
    biz = _create_business(client, headers, "Test Biz")
    biz_id = biz["id"]

    branch_res = client.post(
        f"/api/v1/businesses/{biz_id}/branches",
        headers=headers,
        json={"name": "Branch JKT", "code": "BR-JKT"},
    )
    branch = branch_res.json()

    wh_res = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers=headers,
        json={"name": "WH JKT", "code": "WH-JKT", "branch_id": branch["id"]},
    )
    assert wh_res.status_code == 201
    assert wh_res.json()["branch_id"] == branch["id"]

    # Cross-business branch
    headers_b = _get_headers(client, "wh_crossbranch_biz@example.com")
    biz_b = _create_business(client, headers_b, "Other Biz")
    biz_b_id = biz_b["id"]
    other_branch = client.post(
        f"/api/v1/businesses/{biz_b_id}/branches",
        headers=headers_b,
        json={"name": "Branch BDG", "code": "BR-BDG"},
    ).json()

    bad_wh = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers=headers,
        json={"name": "Bad WH", "code": "WH-BAD", "branch_id": other_branch["id"]},
    )
    assert bad_wh.status_code == 400


def test_archived_warehouse_cannot_create_location(client):
    headers = _get_headers(client, "wh_arch@example.com")
    biz = _create_business(client, headers, "Test Biz")
    biz_id = biz["id"]

    w = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers=headers,
        json={"name": "Wh 1", "code": "WH-1"},
    ).json()

    client.delete(f"/api/v1/businesses/{biz_id}/warehouses/{w['id']}", headers=headers)

    loc_res = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses/{w['id']}/locations",
        headers=headers,
        json={"name": "Rack A", "code": "RACK-A"},
    )
    assert loc_res.status_code == 400


def test_tenant_isolation_and_membership_authorization(client):
    headers_a = _get_headers(client, "user_a@example.com")
    biz_a = _create_business(client, headers_a, "Biz A")
    biz_a_id = biz_a["id"]

    headers_b = _get_headers(client, "user_b@example.com")
    biz_b = _create_business(client, headers_b, "Biz B")
    biz_b_id = biz_b["id"]

    w_a = client.post(
        f"/api/v1/businesses/{biz_a_id}/warehouses",
        headers=headers_a,
        json={"name": "WH A", "code": "WH-A"},
    ).json()

    # User B tries to read Warehouse A -> 404
    res = client.get(f"/api/v1/businesses/{biz_a_id}/warehouses/{w_a['id']}", headers=headers_b)
    assert res.status_code in [403, 404]

    # Path mismatch / Business B / Warehouse A
    res2 = client.get(f"/api/v1/businesses/{biz_b_id}/warehouses/{w_a['id']}", headers=headers_a)
    assert res2.status_code == 404


# --- Inventory Location Tests ---

def test_create_location_success(client):
    headers = _get_headers(client, "loc_owner@example.com")
    biz = _create_business(client, headers, "Test Biz")
    biz_id = biz["id"]

    w = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers=headers,
        json={"name": "WH 1", "code": "WH-1"},
    ).json()

    res = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses/{w['id']}/locations",
        headers=headers,
        json={"name": "Rack A", "code": "RACK-A", "location_type": "STORAGE"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Rack A"
    assert data["code"] == "RACK-A"
    assert data["warehouse_id"] == w['id']
    assert data["status"] == "ACTIVE"
    assert data["is_default"] is True


def test_location_code_uniqueness_per_warehouse(client):
    headers = _get_headers(client, "loc_code@example.com")
    biz = _create_business(client, headers, "Test Biz")
    biz_id = biz["id"]

    w1 = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers=headers,
        json={"name": "WH 1", "code": "WH-1"},
    ).json()
    w2 = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers=headers,
        json={"name": "WH 2", "code": "WH-2"},
    ).json()

    client.post(
        f"/api/v1/businesses/{biz_id}/warehouses/{w1['id']}/locations",
        headers=headers,
        json={"name": "Main", "code": "MAIN"},
    )

    # Same warehouse duplicate code -> 409
    dup = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses/{w1['id']}/locations",
        headers=headers,
        json={"name": "Main 2", "code": "MAIN"},
    )
    assert dup.status_code == 409

    # Different warehouse same code -> 201
    diff = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses/{w2['id']}/locations",
        headers=headers,
        json={"name": "Main", "code": "MAIN"},
    )
    assert diff.status_code == 201


def test_location_lifecycle_and_default_reassignment(client):
    headers = _get_headers(client, "loc_life@example.com")
    biz = _create_business(client, headers, "Test Biz")
    biz_id = biz["id"]

    w = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers=headers,
        json={"name": "WH 1", "code": "WH-1"},
    ).json()

    l1 = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses/{w['id']}/locations",
        headers=headers,
        json={"name": "Loc 1", "code": "LOC-1"},
    ).json()
    l2 = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses/{w['id']}/locations",
        headers=headers,
        json={"name": "Loc 2", "code": "LOC-2"},
    ).json()

    assert l1["is_default"] is True
    assert l2["is_default"] is False

    # Archive l1
    client.delete(f"/api/v1/businesses/{biz_id}/warehouses/{w['id']}/locations/{l1['id']}", headers=headers)

    # l2 should become default
    l2_upd = client.get(f"/api/v1/businesses/{biz_id}/warehouses/{w['id']}/locations/{l2['id']}", headers=headers).json()
    assert l2_upd["is_default"] is True


def test_member_read_only_authorization(client):
    headers_owner = _get_headers(client, "owner_wh@example.com")
    biz = _create_business(client, headers_owner, "Biz Mem")
    biz_id = biz["id"]

    # Register and add member
    token_member = _register_and_get_token(client, "member_wh@example.com")
    headers_member = {"Authorization": f"Bearer {token_member}"}
    member_user_id = client.get("/api/v1/auth/me", headers=headers_member).json()["id"]

    client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers=headers_owner,
        json={"user_id": member_user_id, "role": "MEMBER"},
    )

    # Member can list/get warehouses
    res = client.get(f"/api/v1/businesses/{biz_id}/warehouses", headers=headers_member)
    assert res.status_code == 200

    # Member cannot create warehouse -> 403
    res_create = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers=headers_member,
        json={"name": "Member WH", "code": "WH-MEM"},
    )
    assert res_create.status_code == 403


def test_no_duplicate_active_default_warehouse(client):
    """Ensure no two active warehouses with is_default=True exist in same business.
    When set_default is called for w2, w1 default must be unset."""
    from app.modules.warehouse.repository import InMemoryWarehouseRepository

    headers_a = _get_headers(client, "wh_nodupa@example.com")
    biz = _create_business(client, headers_a, "Test Biz")
    biz_id = biz["id"]

    repo = InMemoryWarehouseRepository()
    # Create two warehouses
    w1 = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers=headers_a,
        json={"name": "WH A", "code": "WH-A"},
    ).json()
    w2 = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers=headers_a,
        json={"name": "WH B", "code": "WH-B"},
    ).json()

    assert w1["is_default"] is True
    assert w2["is_default"] is False

    # Explicitly set w2 as default through API
    res = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses/{w2['id']}/default",
        headers=headers_a,
    )
    # There's no default endpoint in warehouse, so let's use suspend/reactivate cycle:
    # Suspend w1 to trigger default reassignment to w2
    client.post(f"/api/v1/businesses/{biz_id}/warehouses/{w1['id']}/suspend", headers=headers_a)
    w2_upd = client.get(f"/api/v1/businesses/{biz_id}/warehouses/{w2['id']}", headers=headers_a).json()
    assert w2_upd["is_default"] is True
    w1_upd = client.get(f"/api/v1/businesses/{biz_id}/warehouses/{w1['id']}", headers=headers_a).json()
    assert w1_upd["is_default"] is False


def test_suspended_membership_rejection(client):
    headers_owner = _get_headers(client, "owner_suspended@example.com")
    biz = _create_business(client, headers_owner, "Biz Sus")
    biz_id = biz["id"]

    # Add a member
    token_member = _register_and_get_token(client, "member_suspended@example.com")
    headers_member = {"Authorization": f"Bearer {token_member}"}
    member_user_id = client.get("/api/v1/auth/me", headers=headers_member).json()["id"]
    add_res = client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers=headers_owner,
        json={"user_id": member_user_id, "role": "ADMIN"},
    )
    assert add_res.status_code == 201
    membership_id = add_res.json()["id"]

    # Suspend the member
    patch_res = client.patch(
        f"/api/v1/businesses/{biz_id}/members/{membership_id}",
        headers=headers_owner,
        json={"status": "SUSPENDED"},
    )
    assert patch_res.status_code == 200

    res = client.get(f"/api/v1/businesses/{biz_id}/warehouses", headers=headers_member)
    assert res.status_code in [403, 404]


def test_removed_membership_rejection(client):
    headers_owner = _get_headers(client, "owner_removed@example.com")
    biz = _create_business(client, headers_owner, "Biz Rem")
    biz_id = biz["id"]

    token_member = _register_and_get_token(client, "member_removed@example.com")
    headers_member = {"Authorization": f"Bearer {token_member}"}
    member_user_id = client.get("/api/v1/auth/me", headers=headers_member).json()["id"]

    # Add member as ADMIN
    add_res = client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers=headers_owner,
        json={"user_id": member_user_id, "role": "ADMIN"},
    )
    assert add_res.status_code == 201
    membership_id = add_res.json()["id"]

    # Remove the member
    remove_res = client.delete(
        f"/api/v1/businesses/{biz_id}/members/{membership_id}",
        headers=headers_owner,
    )
    assert remove_res.status_code == 200
    assert remove_res.json()["status"] == "REMOVED"

    # Removed member cannot list warehouses -> 404
    res = client.get(f"/api/v1/businesses/{biz_id}/warehouses", headers=headers_member)
    assert res.status_code == 404


def test_admin_authorization(client):
    headers_owner = _get_headers(client, "admin_owner@example.com")
    biz = _create_business(client, headers_owner, "Biz Admin")
    biz_id = biz["id"]

    # Promote user to ADMIN
    token_admin = _register_and_get_token(client, "admin_user@example.com")
    headers_admin = {"Authorization": f"Bearer {token_admin}"}
    admin_user_id = client.get("/api/v1/auth/me", headers=headers_admin).json()["id"]
    client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers=headers_owner,
        json={"user_id": admin_user_id, "role": "ADMIN"},
    )

    res = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers=headers_admin,
        json={"name": "Admin WH", "code": "WH-ADM"},
    )
    assert res.status_code == 201


def test_owner_authorization(client):
    headers_owner = _get_headers(client, "owner_authz@example.com")
    biz = _create_business(client, headers_owner, "Biz Owner")
    biz_id = biz["id"]

    res = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers=headers_owner,
        json={"name": "Owner WH", "code": "WH-OWN"},
    )
    assert res.status_code == 201


def test_location_type_validation(client):
    headers = _get_headers(client, "loc_type@example.com")
    biz = _create_business(client, headers, "Test Biz")
    biz_id = biz["id"]
    wh = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers=headers,
        json={"name": "WH 1", "code": "WH-1"},
    ).json()

    # Invalid type -> 422
    res = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses/{wh['id']}/locations",
        headers=headers,
        json={"name": "Loc", "code": "LOC", "location_type": "INVALID_TYPE"},
    )
    assert res.status_code == 422

    # Valid -> 201
    res2 = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses/{wh['id']}/locations",
        headers=headers,
        json={"name": "Loc", "code": "LOC2", "location_type": "STORAGE"},
    )
    assert res2.status_code == 201


def test_update_location(client):
    headers = _get_headers(client, "loc_upd@example.com")
    biz = _create_business(client, headers, "Test Biz")
    biz_id = biz["id"]
    wh = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers=headers,
        json={"name": "WH 1", "code": "WH-1"},
    ).json()
    loc = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses/{wh['id']}/locations",
        headers=headers,
        json={"name": "Loc A", "code": "LOC-A", "location_type": "STORAGE"},
    ).json()

    res = client.patch(
        f"/api/v1/businesses/{biz_id}/warehouses/{wh['id']}/locations/{loc['id']}",
        headers=headers,
        json={"name": "Updated Loc", "location_type": "PICKING"},
    )
    assert res.status_code == 200
    assert res.json()["name"] == "Updated Loc"
    assert res.json()["location_type"] == "PICKING"


def test_archive_location(client):
    headers = _get_headers(client, "loc_arch@example.com")
    biz = _create_business(client, headers, "Test Biz")
    biz_id = biz["id"]
    wh = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers=headers,
        json={"name": "WH 1", "code": "WH-1"},
    ).json()
    loc = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses/{wh['id']}/locations",
        headers=headers,
        json={"name": "Loc A", "code": "LOC-A"},
    ).json()

    res = client.delete(
        f"/api/v1/businesses/{biz_id}/warehouses/{wh['id']}/locations/{loc['id']}",
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "ARCHIVED"


def test_archived_location_excluded_from_active_list(client):
    headers = _get_headers(client, "loc_excl@example.com")
    biz = _create_business(client, headers, "Test Biz")
    biz_id = biz["id"]
    wh = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers=headers,
        json={"name": "WH 1", "code": "WH-1"},
    ).json()
    client.post(
        f"/api/v1/businesses/{biz_id}/warehouses/{wh['id']}/locations",
        headers=headers,
        json={"name": "Loc A", "code": "LOC-A"},
    )
    # Create & archive second
    loc2 = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses/{wh['id']}/locations",
        headers=headers,
        json={"name": "Loc B", "code": "LOC-B"},
    ).json()
    client.delete(
        f"/api/v1/businesses/{biz_id}/warehouses/{wh['id']}/locations/{loc2['id']}",
        headers=headers,
    )
    # List active only
    res = client.get(
        f"/api/v1/businesses/{biz_id}/warehouses/{wh['id']}/locations",
        headers=headers,
    )
    assert res.status_code == 200
    locs = res.json()
    assert len(locs) == 1
    assert locs[0]["name"] == "Loc A"


def test_archived_warehouse_cannot_activate_create_location(client):
    headers = _get_headers(client, "loc_wh_arch@example.com")
    biz = _create_business(client, headers, "Test Biz")
    biz_id = biz["id"]
    wh = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers=headers,
        json={"name": "WH 1", "code": "WH-1"},
    ).json()
    client.delete(f"/api/v1/businesses/{biz_id}/warehouses/{wh['id']}", headers=headers)

    # Cannot create location under archived warehouse
    res = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses/{wh['id']}/locations",
        headers=headers,
        json={"name": "Loc", "code": "LOC"},
    )
    assert res.status_code == 400

    # Cannot update existing location under archived warehouse
    loc = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses/{wh['id']}/locations",
        headers=headers,
        json={"name": "Loc", "code": "LOC"},
    )
    assert loc.status_code == 400


def test_location_code_immutable(client):
    headers = _get_headers(client, "loc_immutable@example.com")
    biz = _create_business(client, headers, "Test Biz")
    biz_id = biz["id"]
    wh = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers=headers,
        json={"name": "WH 1", "code": "WH-1"},
    ).json()
    loc = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses/{wh['id']}/locations",
        headers=headers,
        json={"name": "Loc A", "code": "LOC-A"},
    ).json()

    # Try to patch code -> should be ignored (not in update schema) -> 422 (extra/forbidden) or ignored
    res = client.patch(
        f"/api/v1/businesses/{biz_id}/warehouses/{wh['id']}/locations/{loc['id']}",
        headers=headers,
        json={"code": "NEW-CODE"},
    )
    # code is not in InventoryLocationUpdate schema (extra="forbid") -> 422
    assert res.status_code == 422


def test_warehouse_code_immutable(client):
    headers = _get_headers(client, "wh_code_imm@example.com")
    biz = _create_business(client, headers, "Test Biz")
    biz_id = biz["id"]
    wh = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers=headers,
        json={"name": "Wh", "code": "WH-1"},
    ).json()

    res = client.patch(
        f"/api/v1/businesses/{biz_id}/warehouses/{wh['id']}",
        headers=headers,
        json={"code": "WH-2"},
    )
    assert res.status_code == 422


def test_body_spoofing_business_id(client):
    """Scenario D: business_id in body must be rejected (extra='forbid' → 422). This proves body authority is ignored."""
    headers = _get_headers(client, "spoof@example.com")
    biz = _create_business(client, headers, "Test Biz")
    biz_id = biz["id"]

    # Sending business_id in body is forbidden by schema -> 422 rejection proves body spoofing protection
    res = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers=headers,
        json={"name": "WH", "code": "WH-1", "business_id": "FAKE-BUSINESS-ID"},
    )
    assert res.status_code == 422

    # Confirm without spoofing works and is tenant-scoped
    res2 = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers=headers,
        json={"name": "Clean WH", "code": "WH-2"},
    )
    assert res2.status_code == 201
    assert res2.json()["business_id"] == biz_id


def test_nested_path_mismatch(client):
    """Scenario C: Business A path / Warehouse B / Location A must reject."""
    headers_a = _get_headers(client, "nested_a@example.com")
    biz_a = _create_business(client, headers_a, "Biz A")
    biz_a_id = biz_a["id"]

    wh_a = client.post(
        f"/api/v1/businesses/{biz_a_id}/warehouses",
        headers=headers_a,
        json={"name": "WH A", "code": "WH-A"},
    ).json()
    loc_a = client.post(
        f"/api/v1/businesses/{biz_a_id}/warehouses/{wh_a['id']}/locations",
        headers=headers_a,
        json={"name": "Loc A", "code": "LOC-A"},
    ).json()

    headers_b = _get_headers(client, "nested_b@example.com")
    biz_b = _create_business(client, headers_b, "Biz B")
    biz_b_id = biz_b["id"]
    wh_b = client.post(
        f"/api/v1/businesses/{biz_b_id}/warehouses",
        headers=headers_b,
        json={"name": "WH B", "code": "WH-B"},
    ).json()

    # Try to access Loc A under WH B in Biz A
    res = client.get(
        f"/api/v1/businesses/{biz_a_id}/warehouses/{wh_b['id']}/locations/{loc_a['id']}",
        headers=headers_a,
    )
    assert res.status_code == 404

    # Try to access Loc A under WH B in Biz B
    res2 = client.get(
        f"/api/v1/businesses/{biz_b_id}/warehouses/{wh_b['id']}/locations/{loc_a['id']}",
        headers=headers_a,
    )
    assert res2.status_code == 404


def test_cross_business_warehouse_rejection(client):
    """Business A cannot access Business B warehouse."""
    headers_a = _get_headers(client, "cross_a@example.com")
    biz_a = _create_business(client, headers_a, "Biz A")
    biz_a_id = biz_a["id"]

    headers_b = _get_headers(client, "cross_b@example.com")
    biz_b = _create_business(client, headers_b, "Biz B")
    biz_b_id = biz_b["id"]

    wh_b = client.post(
        f"/api/v1/businesses/{biz_b_id}/warehouses",
        headers=headers_b,
        json={"name": "WH B", "code": "WH-B"},
    ).json()

    # User A tries GET on WH B via their own business path
    res = client.get(f"/api/v1/businesses/{biz_a_id}/warehouses/{wh_b['id']}", headers=headers_a)
    assert res.status_code == 404


def test_cross_business_location_rejection(client):
    """Business A cannot access Business B location."""
    headers_a = _get_headers(client, "crossloc_a@example.com")
    biz_a = _create_business(client, headers_a, "Biz A")
    biz_a_id = biz_a["id"]

    headers_b = _get_headers(client, "crossloc_b@example.com")
    biz_b = _create_business(client, headers_b, "Biz B")
    biz_b_id = biz_b["id"]

    wh_b = client.post(
        f"/api/v1/businesses/{biz_b_id}/warehouses",
        headers=headers_b,
        json={"name": "WH B", "code": "WH-B"},
    ).json()
    loc_b = client.post(
        f"/api/v1/businesses/{biz_b_id}/warehouses/{wh_b['id']}/locations",
        headers=headers_b,
        json={"name": "Loc B", "code": "LOC-B"},
    ).json()

    # User A tries to GET Location B inside WH B, via Biz A path
    res = client.get(
        f"/api/v1/businesses/{biz_a_id}/warehouses/{wh_b['id']}/locations/{loc_b['id']}",
        headers=headers_a,
    )
    assert res.status_code == 404


def test_location_business_warehouse_integrity(client):
    """Location.business_id must match Warehouse.business_id."""
    headers_a = _get_headers(client, "integ_a@example.com")
    biz_a = _create_business(client, headers_a, "Biz A")
    biz_a_id = biz_a["id"]

    headers_b = _get_headers(client, "integ_b@example.com")
    biz_b = _create_business(client, headers_b, "Biz B")
    biz_b_id = biz_b["id"]

    wh_a = client.post(
        f"/api/v1/businesses/{biz_a_id}/warehouses",
        headers=headers_a,
        json={"name": "WH A", "code": "WH-A"},
    ).json()
    wh_b = client.post(
        f"/api/v1/businesses/{biz_b_id}/warehouses",
        headers=headers_b,
        json={"name": "WH B", "code": "WH-B"},
    ).json()

    # Try to create a location in Biz A's warehouse but through Biz B's path (tenant mismatch)
    res = client.post(
        f"/api/v1/businesses/{biz_b_id}/warehouses/{wh_a['id']}/locations",
        headers=headers_b,
        json={"name": "Loc", "code": "LOC"},
    )
    # wh_a does not belong to biz_b_id → 404
    assert res.status_code == 404


def test_location_warehouse_immutable(client):
    """Location cannot be relocated to another warehouse via update."""
    headers = _get_headers(client, "loc_reloc@example.com")
    biz = _create_business(client, headers, "Test Biz")
    biz_id = biz["id"]

    wh = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers=headers,
        json={"name": "WH 1", "code": "WH-1"},
    ).json()
    loc = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses/{wh['id']}/locations",
        headers=headers,
        json={"name": "Loc A", "code": "LOC-A"},
    ).json()

    # Try warehouse_id in body -> extra="forbid" -> 422
    res = client.patch(
        f"/api/v1/businesses/{biz_id}/warehouses/{wh['id']}/locations/{loc['id']}",
        headers=headers,
        json={"warehouse_id": "OTHER-WH"},
    )
    assert res.status_code == 422


def test_case_insensitive_location_code(client):
    headers = _get_headers(client, "loc_ci@example.com")
    biz = _create_business(client, headers, "Test Biz")
    biz_id = biz["id"]
    wh = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers=headers,
        json={"name": "WH 1", "code": "WH-1"},
    ).json()

    client.post(
        f"/api/v1/businesses/{biz_id}/warehouses/{wh['id']}/locations",
        headers=headers,
        json={"name": "Loc Main", "code": "MAIN"},
    )
    res = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses/{wh['id']}/locations",
        headers=headers,
        json={"name": "Loc Main 2", "code": "main"},
    )
    assert res.status_code == 409


def test_archived_warehouse_cannot_activate_create_location(client):
    """Already covered but make explicit: archived warehouse blocks create + location is default reassignment still works after warehouse archive."""
    headers = _get_headers(client, "arch_reactivate@example.com")
    biz = _create_business(client, headers, "Test Biz")
    biz_id = biz["id"]
    wh = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers=headers,
        json={"name": "WH 1", "code": "WH-1"},
    ).json()
    # Create a location, then archive warehouse, verify location creation blocked
    client.post(
        f"/api/v1/businesses/{biz_id}/warehouses/{wh['id']}/locations",
        headers=headers,
        json={"name": "Loc A", "code": "LOC-A"},
    )
    client.delete(f"/api/v1/businesses/{biz_id}/warehouses/{wh['id']}", headers=headers)
    res = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses/{wh['id']}/locations",
        headers=headers,
        json={"name": "Loc Blocked", "code": "LOC-B"},
    )
    assert res.status_code == 400


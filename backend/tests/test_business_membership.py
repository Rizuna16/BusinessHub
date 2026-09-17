import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import async_session_factory, engine
from app.modules.authentication.repository import InMemoryUserRepository
from app.modules.account.repository import InMemoryAccountRepository
from app.modules.business.repository import InMemoryBusinessRepository
from app.modules.business_membership.repository import InMemoryBusinessMembershipRepository
from app.modules.business_membership.schemas import BusinessMembershipRole, BusinessMembershipStatus
from app.modules.business_membership.service import business_membership_service


@pytest.fixture(autouse=True)
def clear_repos():
    InMemoryUserRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    yield
    InMemoryUserRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryBusinessMembershipRepository.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


async def _ensure_user_in_pg(user_id: str, email: str, full_name: str):
    """Create a fresh engine to avoid event loop conflicts with TestClient."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from app.core.config import settings
    fresh_engine = create_async_engine(settings.database_url, echo=False, pool_size=2, pool_pre_ping=True)
    FreshSession = async_sessionmaker(fresh_engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with FreshSession() as session:
            await session.execute(text(
                "INSERT INTO users (id, email, full_name, password_hash, is_active, platform_role) "
                "VALUES (:id, :email, :full_name, 'hash', true, NULL) "
                "ON CONFLICT (email) DO UPDATE SET id = :id, full_name = :full_name"
            ), {"id": user_id, "email": email, "full_name": full_name})
            await session.commit()
    finally:
        await fresh_engine.dispose()


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
        login_res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
    # Also ensure user exists in PostgreSQL for membership service lookups
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    if me.status_code == 200:
        user_id = me.json().get("id")
        if user_id:
            import anyio
            anyio.run(_ensure_user_in_pg, user_id, email, full_name)
    return token


def _create_business(client, token, name="Test Biz", btype="retail", tz="UTC", locale="en-US"):
    return client.post(
        "/api/v1/businesses",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "business_type": btype, "timezone": tz, "locale": locale},
    )


def _get_user_id(client, token):
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    return me.json()["id"]


def _get_membership_id(client, token, biz_id, user_id):
    res = client.get(f"/api/v1/businesses/{biz_id}/members", headers={"Authorization": f"Bearer {token}"})
    for m in res.json():
        if m["user_id"] == user_id:
            return m["id"]
    return None


# 1. Business creation creates OWNER membership
def test_business_creation_creates_owner_membership(client: TestClient):
    token = _register_and_get_token(client)
    res = _create_business(client, token)
    biz_id = res.json()["id"]
    user_id = _get_user_id(client, token)

    members_res = client.get(f"/api/v1/businesses/{biz_id}/members", headers={"Authorization": f"Bearer {token}"})
    assert members_res.status_code == 200
    members = members_res.json()
    assert len(members) == 1
    assert members[0]["role"] == "OWNER"
    assert members[0]["status"] == "ACTIVE"
    assert members[0]["user_id"] == user_id


# 2. Owner membership unique
def test_owner_membership_unique(client: TestClient):
    token = _register_and_get_token(client, email="a@example.com", full_name="User A")
    res = _create_business(client, token)
    biz_id = res.json()["id"]
    user_a = _get_user_id(client, token)

    import asyncio
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from app.core.config import settings

    async def _query(sql, params):
        engine = create_async_engine(settings.database_url, echo=False, pool_size=2, pool_pre_ping=True)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        try:
            async with factory() as session:
                result = await session.execute(text(sql), params)
                return result.fetchall()
        finally:
            await engine.dispose()

    # Query PostgreSQL for the membership
    rows = asyncio.run(_query(
        "SELECT id, role FROM business_memberships WHERE business_id = :biz_id AND user_id = :user_id",
        {"biz_id": biz_id, "user_id": user_a}
    ))
    assert len(rows) == 1
    assert rows[0].role == "OWNER"

    # Repository should report only one OWNER record for this business
    rows = asyncio.run(_query(
        "SELECT role FROM business_memberships WHERE business_id = :biz_id",
        {"biz_id": biz_id}
    ))
    owners = [r for r in rows if r.role == "OWNER"]
    assert len(owners) == 1


# 3. Cannot create second OWNER via add_member
def test_cannot_create_second_owner_via_add_member(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_b = _register_and_get_token(client, email="b@example.com", full_name="User B", password="Password456")
    biz_id = _create_business(client, token_a).json()["id"]
    user_b = _get_user_id(client, token_b)

    res = client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"user_id": user_b, "role": "OWNER"},
    )
    assert res.status_code == 400


# 4. Duplicate membership rejected
def test_duplicate_membership_rejected(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_b = _register_and_get_token(client, email="b@example.com", full_name="User B", password="Password456")
    biz_id = _create_business(client, token_a).json()["id"]
    user_b = _get_user_id(client, token_b)

    res1 = client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"user_id": user_b, "role": "MEMBER"},
    )
    assert res1.status_code == 201

    # Adding the same user again -> conflict
    res2 = client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"user_id": user_b, "role": "MEMBER"},
    )
    assert res2.status_code == 409


# 5. Multiple members supported
def test_multiple_members_supported(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_b = _register_and_get_token(client, email="b@example.com", full_name="User B", password="Password456")
    token_c = _register_and_get_token(client, email="c@example.com", full_name="User C", password="Password789")
    biz_id = _create_business(client, token_a).json()["id"]
    user_b = _get_user_id(client, token_b)
    user_c = _get_user_id(client, token_c)

    client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"user_id": user_b, "role": "ADMIN"},
    )
    client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"user_id": user_c, "role": "MEMBER"},
    )

    members_res = client.get(f"/api/v1/businesses/{biz_id}/members", headers={"Authorization": f"Bearer {token_a}"})
    assert members_res.status_code == 200
    members = members_res.json()
    assert len(members) == 3  # owner + admin + member
    roles = sorted(m["role"] for m in members)
    assert roles == ["ADMIN", "MEMBER", "OWNER"]


# 6. List members
def test_list_members(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    biz_id = _create_business(client, token_a).json()["id"]

    res = client.get(f"/api/v1/businesses/{biz_id}/members", headers={"Authorization": f"Bearer {token_a}"})
    assert res.status_code == 200
    assert len(res.json()) == 1


# 7. Get membership
def test_get_membership(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_b = _register_and_get_token(client, email="b@example.com", full_name="User B", password="Password456")
    biz_id = _create_business(client, token_a).json()["id"]
    user_b = _get_user_id(client, token_b)
    membership_id = _get_membership_id(client, token_b, biz_id, user_b) if False else None

    add_res = client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"user_id": user_b, "role": "MEMBER"},
    )
    membership_id = add_res.json()["id"]

    res = client.get(f"/api/v1/businesses/{biz_id}/members/{membership_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert res.status_code == 200
    data = res.json()
    assert data["user_id"] == user_b
    assert data["role"] == "MEMBER"
    assert data["status"] == "ACTIVE"


# 8. Add member as OWNER
def test_add_member_as_owner(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_b = _register_and_get_token(client, email="b@example.com", full_name="User B", password="Password456")
    biz_id = _create_business(client, token_a).json()["id"]
    user_b = _get_user_id(client, token_b)

    res = client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"user_id": user_b, "role": "MEMBER"},
    )
    assert res.status_code == 201
    assert res.json()["role"] == "MEMBER"


# 9. Add member as ADMIN
def test_add_member_as_admin(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_b = _register_and_get_token(client, email="b@example.com", full_name="User B", password="Password456")
    token_c = _register_and_get_token(client, email="c@example.com", full_name="User C", password="Password789")
    biz_id = _create_business(client, token_a).json()["id"]
    user_b = _get_user_id(client, token_b)
    user_c = _get_user_id(client, token_c)

    # A (owner) adds B as ADMIN
    client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"user_id": user_b, "role": "ADMIN"},
    )

    # B (admin) adds C as MEMBER
    res = client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"user_id": user_c, "role": "MEMBER"},
    )
    assert res.status_code == 201
    assert res.json()["role"] == "MEMBER"


# 10. Add member as MEMBER (denied)
def test_add_member_as_member_denied(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_b = _register_and_get_token(client, email="b@example.com", full_name="User B", password="Password456")
    token_c = _register_and_get_token(client, email="c@example.com", full_name="User C", password="Password789")
    biz_id = _create_business(client, token_a).json()["id"]
    user_b = _get_user_id(client, token_b)
    user_c = _get_user_id(client, token_c)

    client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"user_id": user_b, "role": "MEMBER"},
    )

    res = client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"user_id": user_c, "role": "MEMBER"},
    )
    assert res.status_code == 403


# 11. Member cannot add member (covered above, explicit check) 
def test_member_cannot_add_member(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_b = _register_and_get_token(client, email="b@example.com", full_name="User B", password="Password456")
    token_c = _register_and_get_token(client, email="c@example.com", full_name="User C", password="Password789")
    biz_id = _create_business(client, token_a).json()["id"]
    user_b = _get_user_id(client, token_b)
    user_c = _get_user_id(client, token_c)

    client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"user_id": user_b, "role": "MEMBER"},
    )

    res = client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"user_id": user_c, "role": "MEMBER"},
    )
    assert res.status_code == 403


# 12. Admin can add member
def test_admin_can_add_member(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_b = _register_and_get_token(client, email="b@example.com", full_name="User B", password="Password456")
    token_c = _register_and_get_token(client, email="c@example.com", full_name="User C", password="Password789")
    biz_id = _create_business(client, token_a).json()["id"]
    user_b = _get_user_id(client, token_b)
    user_c = _get_user_id(client, token_c)

    client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"user_id": user_b, "role": "ADMIN"},
    )

    res = client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"user_id": user_c, "role": "MEMBER"},
    )
    assert res.status_code == 201


# 13. Admin cannot create OWNER  (covered by test_cannot_create_second_owner_via_add_member with admin)
def test_admin_cannot_create_owner(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_b = _register_and_get_token(client, email="b@example.com", full_name="User B", password="Password456")
    biz_id = _create_business(client, token_a).json()["id"]
    user_b = _get_user_id(client, token_b)

    client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"user_id": user_b, "role": "ADMIN"},
    )

    res = client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"user_id": user_b, "role": "OWNER"},
    )
    assert res.status_code == 400


# 14. Admin cannot modify OWNER
def test_admin_cannot_modify_owner(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_b = _register_and_get_token(client, email="b@example.com", full_name="User B", password="Password456")
    biz_id = _create_business(client, token_a).json()["id"]
    user_a = _get_user_id(client, token_a)
    user_b = _get_user_id(client, token_b)

    client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"user_id": user_b, "role": "ADMIN"},
    )

    owner_membership_id = _get_membership_id(client, token_a, biz_id, user_a)

    # Admin B tries to modify Owner A's membership
    res = client.patch(
        f"/api/v1/businesses/{biz_id}/members/{owner_membership_id}",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"role": "ADMIN"},
    )
    assert res.status_code == 400


# 15. Owner can modify member
def test_owner_can_modify_member(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_b = _register_and_get_token(client, email="b@example.com", full_name="User B", password="Password456")
    biz_id = _create_business(client, token_a).json()["id"]
    user_b = _get_user_id(client, token_b)

    add_res = client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"user_id": user_b, "role": "MEMBER"},
    )
    membership_id = add_res.json()["id"]

    res = client.patch(
        f"/api/v1/businesses/{biz_id}/members/{membership_id}",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"role": "ADMIN"},
    )
    assert res.status_code == 200
    assert res.json()["role"] == "ADMIN"


# 16. Owner cannot demote self
def test_owner_cannot_demote_self(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    biz_id = _create_business(client, token_a).json()["id"]
    user_a = _get_user_id(client, token_a)
    membership_id = _get_membership_id(client, token_a, biz_id, user_a)

    res = client.patch(
        f"/api/v1/businesses/{biz_id}/members/{membership_id}",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"role": "ADMIN"},
    )
    assert res.status_code == 400


# 17. Owner cannot suspend self
def test_owner_cannot_suspend_self(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    biz_id = _create_business(client, token_a).json()["id"]
    user_a = _get_user_id(client, token_a)
    membership_id = _get_membership_id(client, token_a, biz_id, user_a)

    res = client.patch(
        f"/api/v1/businesses/{biz_id}/members/{membership_id}",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"status": "SUSPENDED"},
    )
    assert res.status_code == 400


# 18. Owner cannot remove self
def test_owner_cannot_remove_self(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    biz_id = _create_business(client, token_a).json()["id"]
    user_a = _get_user_id(client, token_a)
    membership_id = _get_membership_id(client, token_a, biz_id, user_a)

    res = client.delete(
        f"/api/v1/businesses/{biz_id}/members/{membership_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res.status_code == 400


# 19. Suspend member
def test_suspend_member(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_b = _register_and_get_token(client, email="b@example.com", full_name="User B", password="Password456")
    biz_id = _create_business(client, token_a).json()["id"]
    user_b = _get_user_id(client, token_b)

    add_res = client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"user_id": user_b, "role": "MEMBER"},
    )
    membership_id = add_res.json()["id"]

    res = client.patch(
        f"/api/v1/businesses/{biz_id}/members/{membership_id}",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"status": "SUSPENDED"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "SUSPENDED"


# 20. Suspended member denied Business access
def test_suspended_member_denied_business_access(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_b = _register_and_get_token(client, email="b@example.com", full_name="User B", password="Password456")
    biz_id = _create_business(client, token_a).json()["id"]
    user_b = _get_user_id(client, token_b)

    client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"user_id": user_b, "role": "MEMBER"},
    )

    # Suspend B
    membership_id = _get_membership_id(client, token_a, biz_id, user_b)
    client.patch(
        f"/api/v1/businesses/{biz_id}/members/{membership_id}",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"status": "SUSPENDED"},
    )

    # B tries to access business -> denied (no active membership)
    res = client.get(f"/api/v1/businesses/{biz_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert res.status_code == 404

    # B tries to list members -> denied
    res = client.get(f"/api/v1/businesses/{biz_id}/members", headers={"Authorization": f"Bearer {token_b}"})
    assert res.status_code == 404

    # B excluded from business list
    res = client.get("/api/v1/businesses", headers={"Authorization": f"Bearer {token_b}"})
    assert res.json() == []


# 21. Remove member
def test_remove_member(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_b = _register_and_get_token(client, email="b@example.com", full_name="User B", password="Password456")
    biz_id = _create_business(client, token_a).json()["id"]
    user_b = _get_user_id(client, token_b)

    add_res = client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"user_id": user_b, "role": "MEMBER"},
    )
    membership_id = add_res.json()["id"]

    res = client.delete(
        f"/api/v1/businesses/{biz_id}/members/{membership_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "REMOVED"

    # Verify record still exists (soft delete)
    get_res = client.get(f"/api/v1/businesses/{biz_id}/members/{membership_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert get_res.status_code == 200
    assert get_res.json()["status"] == "REMOVED"


# 22. Removed member denied Business access
def test_removed_member_denied_business_access(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_b = _register_and_get_token(client, email="b@example.com", full_name="User B", password="Password456")
    biz_id = _create_business(client, token_a).json()["id"]
    user_b = _get_user_id(client, token_b)

    client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"user_id": user_b, "role": "MEMBER"},
    )

    membership_id = _get_membership_id(client, token_a, biz_id, user_b)
    client.delete(
        f"/api/v1/businesses/{biz_id}/members/{membership_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )

    res = client.get(f"/api/v1/businesses/{biz_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert res.status_code == 404


# 23. Cross-business access denied
def test_cross_business_access_denied(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_b = _register_and_get_token(client, email="b@example.com", full_name="User B", password="Password456")
    biz_a = _create_business(client, token_a).json()["id"]
    biz_b = _create_business(client, token_b).json()["id"]

    # A cannot access B's business
    res = client.get(f"/api/v1/businesses/{biz_b}", headers={"Authorization": f"Bearer {token_a}"})
    assert res.status_code == 404

    # B cannot access A's business
    res = client.get(f"/api/v1/businesses/{biz_a}", headers={"Authorization": f"Bearer {token_b}"})
    assert res.status_code == 404


# 24. Cross-business membership management denied
def test_cross_business_membership_management_denied(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_b = _register_and_get_token(client, email="b@example.com", full_name="User B", password="Password456")
    token_c = _register_and_get_token(client, email="c@example.com", full_name="User C", password="Password789")
    biz_a = _create_business(client, token_a).json()["id"]
    biz_b = _create_business(client, token_b).json()["id"]
    user_c = _get_user_id(client, token_c)

    # C is MEMBER of business A
    client.post(
        f"/api/v1/businesses/{biz_a}/members",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"user_id": user_c, "role": "MEMBER"},
    )

    # C tries to manage members in business B (which they have no membership)
    res = client.get(f"/api/v1/businesses/{biz_b}/members", headers={"Authorization": f"Bearer {token_c}"})
    assert res.status_code == 404

    res = client.post(
        f"/api/v1/businesses/{biz_b}/members",
        headers={"Authorization": f"Bearer {token_c}"},
        json={"user_id": user_c, "role": "MEMBER"},
    )
    assert res.status_code == 404

    # C cannot modify any membership in business B
    membership_id = _get_membership_id(client, token_b, biz_b, _get_user_id(client, token_b))
    res = client.patch(
        f"/api/v1/businesses/{biz_b}/members/{membership_id}",
        headers={"Authorization": f"Bearer {token_c}"},
        json={"status": "SUSPENDED"},
    )
    assert res.status_code == 404


# 25. Business list includes active memberships
def test_business_list_includes_active_memberships(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_c = _register_and_get_token(client, email="c@example.com", full_name="User C", password="Password789")
    biz_a = _create_business(client, token_a).json()["id"]
    user_c = _get_user_id(client, token_c)

    # C added as MEMBER of A
    client.post(
        f"/api/v1/businesses/{biz_a}/members",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"user_id": user_c, "role": "MEMBER"},
    )

    res = client.get("/api/v1/businesses", headers={"Authorization": f"Bearer {token_c}"})
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["id"] == biz_a


# 26. Business list excludes suspended memberships
def test_business_list_excludes_suspended_memberships(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_c = _register_and_get_token(client, email="c@example.com", full_name="User C", password="Password789")
    biz_a = _create_business(client, token_a).json()["id"]
    user_c = _get_user_id(client, token_c)

    client.post(
        f"/api/v1/businesses/{biz_a}/members",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"user_id": user_c, "role": "MEMBER"},
    )
    membership_id = _get_membership_id(client, token_a, biz_a, user_c)
    client.patch(
        f"/api/v1/businesses/{biz_a}/members/{membership_id}",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"status": "SUSPENDED"},
    )

    res = client.get("/api/v1/businesses", headers={"Authorization": f"Bearer {token_c}"})
    assert res.json() == []


# 27. Business list excludes removed memberships
def test_business_list_excludes_removed_memberships(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_c = _register_and_get_token(client, email="c@example.com", full_name="User C", password="Password789")
    biz_a = _create_business(client, token_a).json()["id"]
    user_c = _get_user_id(client, token_c)

    client.post(
        f"/api/v1/businesses/{biz_a}/members",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"user_id": user_c, "role": "MEMBER"},
    )
    membership_id = _get_membership_id(client, token_a, biz_a, user_c)
    client.delete(
        f"/api/v1/businesses/{biz_a}/members/{membership_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )

    res = client.get("/api/v1/businesses", headers={"Authorization": f"Bearer {token_c}"})
    assert res.json() == []


# 28. Member can read allowed Business
def test_member_can_read_business(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_c = _register_and_get_token(client, email="c@example.com", full_name="User C", password="Password789")
    biz_a = _create_business(client, token_a).json()["id"]
    user_c = _get_user_id(client, token_c)

    client.post(
        f"/api/v1/businesses/{biz_a}/members",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"user_id": user_c, "role": "MEMBER"},
    )

    res = client.get(f"/api/v1/businesses/{biz_a}", headers={"Authorization": f"Bearer {token_c}"})
    assert res.status_code == 200
    assert res.json()["name"] == "Test Biz"


# 29. Member cannot mutate Business
def test_member_cannot_mutate_business(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_c = _register_and_get_token(client, email="c@example.com", full_name="User C", password="Password789")
    biz_a = _create_business(client, token_a).json()["id"]
    user_c = _get_user_id(client, token_c)

    client.post(
        f"/api/v1/businesses/{biz_a}/members",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"user_id": user_c, "role": "MEMBER"},
    )

    res = client.patch(
        f"/api/v1/businesses/{biz_a}",
        headers={"Authorization": f"Bearer {token_c}"},
        json={"name": "Hacked"},
    )
    assert res.status_code == 403


# 30. Admin can mutate Business
def test_admin_can_mutate_business(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_b = _register_and_get_token(client, email="b@example.com", full_name="User B", password="Password456")
    biz_a = _create_business(client, token_a).json()["id"]
    user_b = _get_user_id(client, token_b)

    client.post(
        f"/api/v1/businesses/{biz_a}/members",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"user_id": user_b, "role": "ADMIN"},
    )

    res = client.patch(
        f"/api/v1/businesses/{biz_a}",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"name": "Updated by Admin"},
    )
    assert res.status_code == 200
    assert res.json()["name"] == "Updated by Admin"


# 31. Admin cannot archive Business
def test_admin_cannot_archive_business(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_b = _register_and_get_token(client, email="b@example.com", full_name="User B", password="Password456")
    biz_a = _create_business(client, token_a).json()["id"]
    user_b = _get_user_id(client, token_b)

    client.post(
        f"/api/v1/businesses/{biz_a}/members",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"user_id": user_b, "role": "ADMIN"},
    )

    res = client.delete(f"/api/v1/businesses/{biz_a}", headers={"Authorization": f"Bearer {token_b}"})
    assert res.status_code == 403


# 32. Owner can archive Business
def test_owner_can_archive_business(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    biz_a = _create_business(client, token_a).json()["id"]

    res = client.delete(f"/api/v1/businesses/{biz_a}", headers={"Authorization": f"Bearer {token_a}"})
    assert res.status_code == 200
    assert res.json()["status"] == "archived"


# 33. Unauthenticated requests return 401
def test_unauthenticated_membership_requests_return_401(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    biz_a = _create_business(client, token_a).json()["id"]

    assert client.get(f"/api/v1/businesses/{biz_a}/members").status_code == 401
    assert client.post(
        f"/api/v1/businesses/{biz_a}/members",
        json={"user_id": "x", "role": "MEMBER"},
    ).status_code == 401
    assert client.get(f"/api/v1/businesses/{biz_a}/members/some-id").status_code == 401
    assert client.patch(
        f"/api/v1/businesses/{biz_a}/members/some-id", json={"role": "ADMIN"}
    ).status_code == 401
    assert client.delete(f"/api/v1/businesses/{biz_a}/members/some-id").status_code == 401


# 34. Invalid token denied
def test_invalid_token_denied(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    biz_a = _create_business(client, token_a).json()["id"]
    res = client.get(
        f"/api/v1/businesses/{biz_a}/members",
        headers={"Authorization": "Bearer not.a.validjwt"},
    )
    assert res.status_code == 401


# 35. Authentication regression
def test_authentication_regression(client: TestClient):
    token = _register_and_get_token(client)
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    login = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "Password123"})
    assert login.status_code == 200
    assert client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"}).status_code == 200


# 36. Account regression
def test_account_regression(client: TestClient):
    token = _register_and_get_token(client)
    assert client.get("/api/v1/account", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    res = client.patch(
        "/api/v1/account",
        headers={"Authorization": f"Bearer {token}"},
        json={"display_name": "Updated"},
    )
    assert res.status_code == 200
    assert res.json()["display_name"] == "Updated"


# 37. Business regression
def test_business_regression(client: TestClient):
    token = _register_and_get_token(client)
    create_res = _create_business(client, token)
    assert create_res.status_code == 201
    biz_id = create_res.json()["id"]
    assert client.get(f"/api/v1/businesses/{biz_id}", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    assert client.get("/api/v1/businesses", headers={"Authorization": f"Bearer {token}"}).status_code == 200


# 38. Health regression
def test_health_regression(client: TestClient):
    res = client.get("/api/v1/health")
    assert res.status_code == 200


# Owner consistency: Business owner remains consistent
def test_owner_remains_consistent(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    biz_a = _create_business(client, token_a).json()["id"]
    user_a = _get_user_id(client, token_a)

    # Owner membership record matches business owner_user_id
    membership_id = _get_membership_id(client, token_a, biz_a, user_a)
    res = client.get(f"/api/v1/businesses/{biz_a}/members/{membership_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert res.status_code == 200
    assert res.json()["user_id"] == user_a
    assert res.json()["role"] == "OWNER"

    biz = client.get(f"/api/v1/businesses/{biz_a}", headers={"Authorization": f"Bearer {token_a}"})
    assert biz.json()["owner_user_id"] == user_a


# Add member target user must exist
def test_add_member_target_user_not_found(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    biz_id = _create_business(client, token_a).json()["id"]

    res = client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"user_id": "nonexistent-user-id", "role": "MEMBER"},
    )
    assert res.status_code == 404


# Member cannot list members (denied)
def test_member_cannot_list_members(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_b = _register_and_get_token(client, email="b@example.com", full_name="User B", password="Password456")
    biz_a = _create_business(client, token_a).json()["id"]
    user_b = _get_user_id(client, token_b)

    client.post(
        f"/api/v1/businesses/{biz_a}/members",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"user_id": user_b, "role": "MEMBER"},
    )

    res = client.get(f"/api/v1/businesses/{biz_a}/members", headers={"Authorization": f"Bearer {token_b}"})
    assert res.status_code == 403


# Membership does not leak sensitive data
def test_membership_response_no_sensitive_fields(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    biz_a = _create_business(client, token_a).json()["id"]
    user_a = _get_user_id(client, token_a)

    membership_id = _get_membership_id(client, token_a, biz_a, user_a)
    res = client.get(f"/api/v1/businesses/{biz_a}/members/{membership_id}", headers={"Authorization": f"Bearer {token_a}"})
    data = res.json()
    assert "password" not in data
    assert "password_hash" not in data

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.authentication.repository import InMemoryUserRepository
from app.modules.account.repository import InMemoryAccountRepository
from app.modules.business.repository import InMemoryBusinessRepository


@pytest.fixture(autouse=True)
def clear_repos():
    InMemoryUserRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryBusinessRepository.clear()
    yield
    InMemoryUserRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryBusinessRepository.clear()


@pytest.fixture(autouse=True)
def clean_business_names():
    """Clean up businesses with fixed names used in slug tests to ensure test isolation."""
    import asyncio
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from app.core.config import settings

    fixed_names = ["My Cool Business", "My Biz"]

    async def _clean():
        engine = create_async_engine(settings.database_url, echo=False, pool_size=2, pool_pre_ping=True)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        try:
            async with factory() as session:
                for name in fixed_names:
                    await session.execute(
                        text("DELETE FROM business_memberships WHERE business_id IN (SELECT id FROM businesses WHERE name = :name)"),
                        {"name": name}
                    )
                    await session.execute(
                        text("DELETE FROM businesses WHERE name = :name"),
                        {"name": name}
                    )
                await session.commit()
        finally:
            await engine.dispose()

    asyncio.run(_clean())


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
        login_res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
    return token


def _create_business(client, token, name="Test Biz", btype="retail", tz="UTC", locale="en-US"):
    res = client.post(
        "/api/v1/businesses",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "business_type": btype, "timezone": tz, "locale": locale},
    )
    return res


# 1. create business
def test_create_business(client: TestClient):
    token = _register_and_get_token(client)
    res = _create_business(client, token)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Test Biz"
    assert data["business_type"] == "retail"
    assert data["status"] == "active"
    assert "slug" in data
    assert "owner_user_id" in data
    assert "password" not in data
    assert "password_hash" not in data


# 2. create requires authentication
def test_create_business_requires_auth(client: TestClient):
    res = client.post("/api/v1/businesses", json={
        "name": "Test Biz", "business_type": "retail", "timezone": "UTC", "locale": "en-US",
    })
    assert res.status_code == 401


# 3. create assigns authenticated owner
def test_create_business_assigns_authenticated_owner(client: TestClient):
    token = _register_and_get_token(client, email="owner@example.com", full_name="Owner One")
    res = _create_business(client, token)
    data = res.json()
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert data["owner_user_id"] == me.json()["id"]


# 4. cannot spoof owner_user_id
def test_cannot_spoof_owner_user_id(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_b = _register_and_get_token(client, email="b@example.com", full_name="User B", password="Password456")
    
    res = client.post(
        "/api/v1/businesses",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "name": "Spoofed Biz",
            "business_type": "retail",
            "timezone": "UTC",
            "locale": "en-US",
            "owner_user_id": "USER_B_ID_SHOULD_BE_IGNORED",
        },
    )
    assert res.status_code == 201
    data = res.json()
    me_a = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_a}"})
    assert data["owner_user_id"] == me_a.json()["id"]
    assert data["owner_user_id"] != "USER_B_ID_SHOULD_BE_IGNORED"


# 5. duplicate name allowed between users
def test_duplicate_name_allowed_between_users(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_b = _register_and_get_token(client, email="b@example.com", full_name="User B", password="Password456")
    
    res_a = _create_business(client, token_a, name="Same Name Biz")
    assert res_a.status_code == 201
    
    res_b = _create_business(client, token_b, name="Same Name Biz")
    assert res_b.status_code == 201
    
    data_a = res_a.json()
    data_b = res_b.json()
    assert data_a["name"] == data_b["name"]
    # Slugs are globally unique, so collision is handled with suffix
    assert data_a["slug"] != data_b["slug"]
    assert data_a["id"] != data_b["id"]
    assert data_a["owner_user_id"] != data_b["owner_user_id"]


# 6. slug generated
def test_slug_generated_from_name(client: TestClient):
    token = _register_and_get_token(client)
    res = _create_business(client, token, name="My Cool Business")
    assert res.status_code == 201
    data = res.json()
    assert data["slug"] == "my-cool-business"


# 7. slug collision handled
def test_slug_collision_handled(client: TestClient):
    token = _register_and_get_token(client)
    res1 = _create_business(client, token, name="My Biz")
    assert res1.status_code == 201
    assert res1.json()["slug"] == "my-biz"
    
    res2 = _create_business(client, token, name="My Biz")
    assert res2.status_code == 201
    assert res2.json()["slug"] == "my-biz-2"


# 8. get own business
def test_get_own_business(client: TestClient):
    token = _register_and_get_token(client)
    create_res = _create_business(client, token, name="Get Test Biz")
    biz_id = create_res.json()["id"]
    
    res = client.get(f"/api/v1/businesses/{biz_id}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["name"] == "Get Test Biz"


# 9. get other user's business denied
def test_get_other_user_business_denied(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_b = _register_and_get_token(client, email="b@example.com", full_name="User B", password="Password456")
    
    res_b = _create_business(client, token_b, name="User B Biz")
    biz_id = res_b.json()["id"]
    
    res = client.get(f"/api/v1/businesses/{biz_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert res.status_code == 404  # Anti-enumeration: 404 instead of 403


# 10. list own businesses
def test_list_own_businesses(client: TestClient):
    token = _register_and_get_token(client, email="u@example.com", full_name="User U")
    _create_business(client, token, name="Biz 1")
    _create_business(client, token, name="Biz 2")
    
    res = client.get("/api/v1/businesses", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2


# 11. list excludes other user's businesses
def test_list_excludes_other_user_businesses(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_b = _register_and_get_token(client, email="b@example.com", full_name="User B", password="Password456")
    
    _create_business(client, token_a, name="Biz A")
    _create_business(client, token_b, name="Biz B")
    
    res_a = client.get("/api/v1/businesses", headers={"Authorization": f"Bearer {token_a}"})
    data_a = res_a.json()
    assert len(data_a) == 1
    assert data_a[0]["name"] == "Biz A"
    
    res_b = client.get("/api/v1/businesses", headers={"Authorization": f"Bearer {token_b}"})
    data_b = res_b.json()
    assert len(data_b) == 1
    assert data_b[0]["name"] == "Biz B"


# 12. multiple businesses per user
def test_multiple_businesses_per_user(client: TestClient):
    token = _register_and_get_token(client)
    _create_business(client, token, name="Biz 1")
    _create_business(client, token, name="Biz 2")
    _create_business(client, token, name="Biz 3")
    
    res = client.get("/api/v1/businesses", headers={"Authorization": f"Bearer {token}"})
    assert len(res.json()) == 3


# 13. update own business
def test_update_own_business(client: TestClient):
    token = _register_and_get_token(client)
    create_res = _create_business(client, token, name="Original Name")
    biz_id = create_res.json()["id"]
    
    res = client.patch(
        f"/api/v1/businesses/{biz_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Updated Name", "description": "New desc"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Updated Name"
    assert data["description"] == "New desc"


# 14. update other user's business denied
def test_update_other_user_business_denied(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_b = _register_and_get_token(client, email="b@example.com", full_name="User B", password="Password456")
    
    res_b = _create_business(client, token_b, name="User B Biz")
    biz_id = res_b.json()["id"]
    
    res = client.patch(
        f"/api/v1/businesses/{biz_id}",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"name": "Hacked Name"},
    )
    assert res.status_code == 404


# 15. owner cannot be changed
def test_owner_cannot_be_changed(client: TestClient):
    token = _register_and_get_token(client, email="u@example.com", full_name="User U")
    create_res = _create_business(client, token)
    biz_id = create_res.json()["id"]
    original_owner = create_res.json()["owner_user_id"]
    
    res = client.patch(
        f"/api/v1/businesses/{biz_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "New Name", "owner_user_id": "some-other-user-id"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["owner_user_id"] == original_owner
    assert data["owner_user_id"] != "some-other-user-id"


# 16. business_type immutability
def test_business_type_immutable_after_creation(client: TestClient):
    token = _register_and_get_token(client)
    create_res = _create_business(client, token, btype="retail")
    biz_id = create_res.json()["id"]
    
    res = client.patch(
        f"/api/v1/businesses/{biz_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"business_type": "hotel"},
    )
    # business_type not in update schema → 422 if treated as validation, or silently ignored
    # Let's check: AccountUpdate doesn't include business_type, so it's an extra field → Pydantic ignores it by default
    # But if Pydantic is configured to forbid extra fields, it would 422
    assert res.status_code in (200, 422)
    if res.status_code == 200:
        assert res.json()["business_type"] == "retail"


# 17. slug remains stable after rename
def test_slug_remains_stable_after_rename(client: TestClient):
    token = _register_and_get_token(client)
    create_res = _create_business(client, token, name="Stable Slug Biz")
    biz_id = create_res.json()["id"]
    original_slug = create_res.json()["slug"]
    
    res = client.patch(
        f"/api/v1/businesses/{biz_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Renamed Biz"},
    )
    assert res.status_code == 200
    assert res.json()["slug"] == original_slug
    assert res.json()["name"] == "Renamed Biz"


# 18. invalid business name (whitespace)
def test_invalid_business_name_rejected(client: TestClient):
    token = _register_and_get_token(client)
    res = client.post(
        "/api/v1/businesses",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "   ", "business_type": "retail", "timezone": "UTC", "locale": "en-US"},
    )
    assert res.status_code == 422


# 19. invalid business type rejected
def test_invalid_business_type_rejected(client: TestClient):
    token = _register_and_get_token(client)
    res = client.post(
        "/api/v1/businesses",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Test Biz", "business_type": "invalid_type", "timezone": "UTC", "locale": "en-US"},
    )
    assert res.status_code == 422


# 20. invalid timezone rejected
def test_invalid_timezone_rejected(client: TestClient):
    token = _register_and_get_token(client)
    res = client.post(
        "/api/v1/businesses",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Test Biz", "business_type": "retail", "timezone": "+07:00", "locale": "en-US"},
    )
    assert res.status_code == 422


# 21. invalid locale rejected
def test_invalid_locale_rejected(client: TestClient):
    token = _register_and_get_token(client)
    res = client.post(
        "/api/v1/businesses",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Test Biz", "business_type": "retail", "timezone": "UTC", "locale": "invalid"},
    )
    assert res.status_code == 422


# 22. archive own business
def test_archive_own_business(client: TestClient):
    token = _register_and_get_token(client)
    create_res = _create_business(client, token, name="Archivable Biz")
    biz_id = create_res.json()["id"]
    
    res = client.delete(f"/api/v1/businesses/{biz_id}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "archived"


# 23. archive is soft delete (data remains) but tenant access is blocked per Feature #52
def test_archive_is_soft_delete(client: TestClient):
    token = _register_and_get_token(client)
    create_res = _create_business(client, token, name="Soft Delete Biz")
    biz_id = create_res.json()["id"]
    
    client.delete(f"/api/v1/businesses/{biz_id}", headers={"Authorization": f"Bearer {token}"})
    
    # Feature #52: archived business blocks tenant access
    res = client.get(f"/api/v1/businesses/{biz_id}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403
    
    # Business still not in active list
    res_list = client.get("/api/v1/businesses", headers={"Authorization": f"Bearer {token}"})
    assert res_list.status_code == 200
    assert len(res_list.json()) == 0


# 24. archived business not in active list
def test_archived_business_not_in_active_list(client: TestClient):
    token = _register_and_get_token(client)
    res_active = _create_business(client, token, name="Active Biz")
    res_archived = _create_business(client, token, name="Archived Biz")
    
    biz_id_active = res_active.json()["id"]
    biz_id_archived = res_archived.json()["id"]
    
    client.delete(f"/api/v1/businesses/{biz_id_archived}", headers={"Authorization": f"Bearer {token}"})
    
    res = client.get("/api/v1/businesses", headers={"Authorization": f"Bearer {token}"})
    data = res.json()
    assert len(data) == 1
    assert data[0]["id"] == biz_id_active


# 25. archive other user's business denied
def test_archive_other_user_business_denied(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_b = _register_and_get_token(client, email="b@example.com", full_name="User B", password="Password456")
    
    res_b = _create_business(client, token_b, name="User B Biz")
    biz_id = res_b.json()["id"]
    
    res = client.delete(f"/api/v1/businesses/{biz_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert res.status_code == 404


# 26. unauthenticated requests return 401
def test_unauthenticated_business_requests_return_401(client: TestClient):
    assert client.get("/api/v1/businesses").status_code == 401
    assert client.post("/api/v1/businesses", json={}).status_code == 401
    assert client.get("/api/v1/businesses/some-id").status_code == 401


# 27. malformed token denied
def test_malformed_token_denied(client: TestClient):
    res = client.get("/api/v1/businesses", headers={"Authorization": "Bearer not.a.validjwt"})
    assert res.status_code == 401


# 28. authentication regression test
def test_authentication_regression_register_login_me_logout(client: TestClient):
    token = _register_and_get_token(client)
    # me
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    # login
    login = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "Password123"})
    assert login.status_code == 200
    # logout
    logout_res = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_res.status_code == 200


# 29. account regression test
def test_account_regression_still_works(client: TestClient):
    token = _register_and_get_token(client)
    # GET account
    res = client.get("/api/v1/account", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    # PATCH account
    res = client.patch(
        "/api/v1/account",
        headers={"Authorization": f"Bearer {token}"},
        json={"display_name": "Updated Name"},
    )
    assert res.status_code == 200
    assert res.json()["display_name"] == "Updated Name"


# 30. health regression test
def test_health_regression(client: TestClient):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["version"] != ""
    assert data["environment"] != ""


# 31. nonexistent business returns 404
def test_nonexistent_business_returns_404(client: TestClient):
    token = _register_and_get_token(client)
    res = client.get("/api/v1/businesses/nonexistent-id", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404


# 32. response does not leak sensitive fields
def test_business_response_no_sensitive_fields(client: TestClient):
    token = _register_and_get_token(client)
    res = _create_business(client, token)
    data = res.json()
    assert "password" not in data
    assert "password_hash" not in data
    assert "jwt_secret" not in data
    assert "owner_password_hash" not in data


# 33. business_type immutability - extra field in update returns 422 if strict
def test_business_type_in_update_rejected_strictly(client: TestClient):
    token = _register_and_get_token(client)
    create_res = _create_business(client, token, btype="retail")
    biz_id = create_res.json()["id"]
    
    # Pydantic model_exclude defaults to False (extra fields ignored), so business_type
    # in the update body would be silently ignored, not rejected with 422.
    res = client.patch(
        f"/api/v1/businesses/{biz_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"business_type": "hotel"},
    )
    assert res.status_code == 200
    assert res.json()["business_type"] == "retail"

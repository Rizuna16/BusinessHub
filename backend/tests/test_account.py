import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.authentication.repository import InMemoryUserRepository, user_repository
from app.modules.authentication.security import create_access_token
from app.modules.account.repository import InMemoryAccountRepository, account_repository


@pytest.fixture(autouse=True)
def clear_repos():
    """Clear both user and account in-memory stores before each test."""
    InMemoryUserRepository.clear()
    InMemoryAccountRepository.clear()
    yield
    InMemoryUserRepository.clear()
    InMemoryAccountRepository.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _register_and_get_token(client: TestClient, email="user@example.com", password="Password123", full_name="Test User") -> str:
    """Register a user and return a bearer token."""
    payload = {
        "email": email,
        "full_name": full_name,
        "password": password,
        "password_confirmation": password,
    }
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 201
    token = res.json().get("access_token")
    # If no token returned, log in to get one
    if not token:
        login_res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
    return token


# 1. authenticated user can GET account
def test_authenticated_user_can_get_account(client: TestClient):
    token = _register_and_get_token(client)
    res = client.get("/api/v1/account", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["display_name"] == "Test User"
    assert data["timezone"] == "UTC"
    assert data["locale"] == "en-US"
    assert "user_id" in data
    assert "id" in data


# 2. unauthenticated GET account → 401
def test_unauthenticated_get_account_returns_401(client: TestClient):
    res = client.get("/api/v1/account")
    assert res.status_code == 401


# 3. authenticated user can PATCH own account
def test_authenticated_user_can_patch_account(client: TestClient):
    token = _register_and_get_token(client)
    # First GET to create the account
    client.get("/api/v1/account", headers={"Authorization": f"Bearer {token}"})
    res = client.patch(
        "/api/v1/account",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "display_name": "Updated Name",
            "phone": "+6281234567890",
            "avatar_url": "https://example.com/avatar.png",
            "timezone": "Asia/Jakarta",
            "locale": "id-ID",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["display_name"] == "Updated Name"
    assert data["phone"] == "+6281234567890"
    assert data["avatar_url"] == "https://example.com/avatar.png"
    assert data["timezone"] == "Asia/Jakarta"
    assert data["locale"] == "id-ID"


# 4. update only allowed fields
def test_update_only_allowed_fields_enforced(client: TestClient):
    token = _register_and_get_token(client)
    client.get("/api/v1/account", headers={"Authorization": f"Bearer {token}"})
    res = client.patch(
        "/api/v1/account",
        headers={"Authorization": f"Bearer {token}"},
        json={"display_name": "New Name"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["display_name"] == "New Name"
    # id and user_id remain unchanged
    original_get = client.get("/api/v1/account", headers={"Authorization": f"Bearer {token}"})
    original_data = original_get.json()
    assert data["id"] == original_data["id"]
    assert data["user_id"] == original_data["user_id"]


# 5. email cannot be changed (not present in update schema)
def test_email_not_in_update_schema(client: TestClient):
    token = _register_and_get_token(client)
    client.get("/api/v1/account", headers={"Authorization": f"Bearer {token}"})
    res = client.patch(
        "/api/v1/account",
        headers={"Authorization": f"Bearer {token}"},
        json={"display_name": "New", "email": "hacker@evil.com"},
    )
    # email field should be silently ignored by Pydantic (extra fields excluded by default)
    assert res.status_code == 200
    data = res.json()
    assert data["display_name"] == "New"
    # Confirm the email was not changed by checking /auth/me
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["email"] == "user@example.com"


# 6. user_id cannot be changed
def test_user_id_not_in_update_schema(client: TestClient):
    token = _register_and_get_token(client)
    client.get("/api/v1/account", headers={"Authorization": f"Bearer {token}"})
    get_res = client.get("/api/v1/account", headers={"Authorization": f"Bearer {token}"})
    user_id_original = get_res.json()["user_id"]
    res = client.patch(
        "/api/v1/account",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": "arbitrary-other-id"},
    )
    # user_id is ignored by schema - the patch may still succeed with no changes
    # but the account's user_id must remain the original
    get_after = client.get("/api/v1/account", headers={"Authorization": f"Bearer {token}"})
    assert get_after.json()["user_id"] == user_id_original


# 7. password_hash never returned
def test_password_hash_never_returned(client: TestClient):
    token = _register_and_get_token(client)
    res = client.get("/api/v1/account", headers={"Authorization": f"Bearer {token}"})
    data = res.json()
    assert "password_hash" not in data
    assert "password" not in data


# 8. invalid display_name rejected
def test_invalid_display_name_rejected(client: TestClient):
    token = _register_and_get_token(client)
    client.get("/api/v1/account", headers={"Authorization": f"Bearer {token}"})
    res = client.patch(
        "/api/v1/account",
        headers={"Authorization": f"Bearer {token}"},
        json={"display_name": "   "},
    )
    assert res.status_code == 422


# 9. invalid avatar URL rejected
def test_invalid_avatar_url_rejected(client: TestClient):
    token = _register_and_get_token(client)
    client.get("/api/v1/account", headers={"Authorization": f"Bearer {token}"})
    res = client.patch(
        "/api/v1/account",
        headers={"Authorization": f"Bearer {token}"},
        json={"avatar_url": "not-a-valid-url"},
    )
    assert res.status_code == 422


# 10. invalid timezone rejected (offset format)
def test_invalid_timezone_rejected(client: TestClient):
    token = _register_and_get_token(client)
    client.get("/api/v1/account", headers={"Authorization": f"Bearer {token}"})
    res = client.patch(
        "/api/v1/account",
        headers={"Authorization": f"Bearer {token}"},
        json={"timezone": "+07:00"},
    )
    assert res.status_code == 422


# 11. invalid locale handled correctly
def test_invalid_locale_handled(client: TestClient):
    token = _register_and_get_token(client)
    client.get("/api/v1/account", headers={"Authorization": f"Bearer {token}"})
    res = client.patch(
        "/api/v1/account",
        headers={"Authorization": f"Bearer {token}"},
        json={"locale": "invalid_locale_format"},
    )
    assert res.status_code == 422


# 12. partial update preserves unspecified fields
def test_partial_update_preserves_unspecified_fields(client: TestClient):
    token = _register_and_get_token(client)
    client.get("/api/v1/account", headers={"Authorization": f"Bearer {token}"})
    # First set full profile
    client.patch(
        "/api/v1/account",
        headers={"Authorization": f"Bearer {token}"},
        json={"display_name": "Full Update", "timezone": "Asia/Jakarta", "locale": "id-ID"},
    )
    # Then partial update of only display_name
    res = client.patch(
        "/api/v1/account",
        headers={"Authorization": f"Bearer {token}"},
        json={"display_name": "Partial Update"},
    )
    data = res.json()
    assert data["display_name"] == "Partial Update"
    assert data["timezone"] == "Asia/Jakarta"
    assert data["locale"] == "id-ID"


# 13. user A cannot access user B account
def test_user_a_cannot_access_user_b_account(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_b = _register_and_get_token(client, email="b@example.com", full_name="User B", password="Password456")

    # User A gets their own account
    res_a = client.get("/api/v1/account", headers={"Authorization": f"Bearer {token_a}"})
    assert res_a.status_code == 200
    account_a = res_a.json()
    assert account_a["display_name"] == "User A"

    # User B gets their own account - should NOT match user A's account
    res_b = client.get("/api/v1/account", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code == 200
    account_b = res_b.json()
    assert account_b["display_name"] == "User B"

    # Verify they are different accounts
    assert account_a["id"] != account_b["id"]
    assert account_a["user_id"] != account_b["user_id"]


# 14. user A cannot modify user B account
def test_user_a_cannot_modify_user_b_account(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    token_b = _register_and_get_token(client, email="b@example.com", full_name="User B", password="Password456")

    # User A modifies their own account
    client.get("/api/v1/account", headers={"Authorization": f"Bearer {token_a}"})
    res_a = client.patch(
        "/api/v1/account",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"display_name": "Hacked Name"},
    )
    assert res_a.status_code == 200
    data_a = res_a.json()
    assert data_a["display_name"] == "Hacked Name"

    # User B's account is unaffected
    res_b = client.get("/api/v1/account", headers={"Authorization": f"Bearer {token_b}"})
    data_b = res_b.json()
    assert data_b["display_name"] == "User B"


# 15. account persistence works
def test_account_persistence_works(client: TestClient):
    token = _register_and_get_token(client)
    # Create by GET (lazy create)
    res_get = client.get("/api/v1/account", headers={"Authorization": f"Bearer {token}"})
    assert res_get.status_code == 200
    account_id = res_get.json()["id"]

    # Update
    res_patch = client.patch(
        "/api/v1/account",
        headers={"Authorization": f"Bearer {token}"},
        json={"display_name": "Persisted Name", "locale": "id-ID"},
    )
    assert res_patch.status_code == 200

    # Fetch again - should reflect changes (proves persistence)
    res_get2 = client.get("/api/v1/account", headers={"Authorization": f"Bearer {token}"})
    data = res_get2.json()
    assert data["id"] == account_id  # same account
    assert data["display_name"] == "Persisted Name"
    assert data["locale"] == "id-ID"


# 16. default account/profile behavior works
def test_default_account_profile_behavior(client: TestClient):
    token = _register_and_get_token(client, email="new@example.com", full_name="New User")
    res = client.get("/api/v1/account", headers={"Authorization": f"Bearer {token}"})
    data = res.json()
    # Default profile created lazily with display_name from user.full_name
    assert data["display_name"] == "New User"
    assert data["phone"] is None
    assert data["avatar_url"] is None
    assert data["timezone"] == "UTC"
    assert data["locale"] == "en-US"


# 17. authentication regression test: login still works
def test_login_still_works_after_account_feature(client: TestClient):
    _register_and_get_token(client)
    res = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "Password123"})
    assert res.status_code == 200
    assert "access_token" in res.json()


# 18. logout behavior still works
def test_logout_still_works(client: TestClient):
    token = _register_and_get_token(client)
    res = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert "Successfully logged out" in res.json()["message"]


# 19. /auth/me still works
def test_auth_me_still_works(client: TestClient):
    token = _register_and_get_token(client)
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "user@example.com"
    assert "password" not in data
    assert "password_hash" not in data


# 20. invalid authentication returns 401
def test_invalid_auth_returns_401(client: TestClient):
    res = client.get("/api/v1/account", headers={"Authorization": "Bearer invalid.token.here"})
    assert res.status_code == 401


# 21. empty phone is accepted
def test_empty_phone_accepted(client: TestClient):
    token = _register_and_get_token(client)
    client.get("/api/v1/account", headers={"Authorization": f"Bearer {token}"})
    res = client.patch(
        "/api/v1/account",
        headers={"Authorization": f"Bearer {token}"},
        json={"phone": ""},
    )
    assert res.status_code == 200
    data = res.json()
    assert data.get("phone") is None


# 22. UTC timezone accepted
def test_utc_timezone_accepted(client: TestClient):
    token = _register_and_get_token(client)
    client.get("/api/v1/account", headers={"Authorization": f"Bearer {token}"})
    res = client.patch(
        "/api/v1/account",
        headers={"Authorization": f"Bearer {token}"},
        json={"timezone": "UTC"},
    )
    assert res.status_code == 200
    assert res.json()["timezone"] == "UTC"


# 23. valid IANA timezone accepted
def test_valid_iana_timezone_accepted(client: TestClient):
    token = _register_and_get_token(client)
    client.get("/api/v1/account", headers={"Authorization": f"Bearer {token}"})
    res = client.patch(
        "/api/v1/account",
        headers={"Authorization": f"Bearer {token}"},
        json={"timezone": "Asia/Makassar"},
    )
    assert res.status_code == 200
    assert res.json()["timezone"] == "Asia/Makassar"


# 24. PATCH with empty body returns 200 (no-op partial update)
def test_patch_with_empty_body_succeeds(client: TestClient):
    token = _register_and_get_token(client)
    client.get("/api/v1/account", headers={"Authorization": f"Bearer {token}"})
    res = client.patch(
        "/api/v1/account",
        headers={"Authorization": f"Bearer {token}"},
        json={},
    )
    assert res.status_code == 200


# 25. no user_id param in query string can switch accounts
def test_no_user_id_query_param_hijack(client: TestClient):
    token_a = _register_and_get_token(client, email="a@example.com", full_name="User A")
    _register_and_get_token(client, email="b@example.com", full_name="User B", password="Password456")

    # Try to access user B's account via query param - should still return A's account
    res = client.get("/api/v1/account?user_id=b", headers={"Authorization": f"Bearer {token_a}"})
    assert res.status_code == 200
    data = res.json()
    assert data["display_name"] == "User A"
    assert data["user_id"] != "b"


# 26. PATCH also auto-creates account lazily
def test_patch_auto_creates_account_lazily(client: TestClient):
    token = _register_and_get_token(client)
    res = client.patch(
        "/api/v1/account",
        headers={"Authorization": f"Bearer {token}"},
        json={"display_name": "Lazy Create Name"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["display_name"] == "Lazy Create Name"

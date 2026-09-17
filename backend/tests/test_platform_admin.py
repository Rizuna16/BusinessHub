import pytest
from fastapi.testclient import TestClient
from decimal import Decimal
from app.main import app
from app.modules.authentication.repository import InMemoryUserRepository, user_repository
from app.modules.business.repository import InMemoryBusinessRepository, business_repository
from app.modules.subscription.repository import InMemorySubscriptionRepository, subscription_repository
from app.modules.platform_admin.repository import InMemoryPlatformAuditRepository, platform_audit_repository
from app.modules.business_membership.repository import InMemoryBusinessMembershipRepository, business_membership_repository

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_stores():
    InMemoryUserRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemorySubscriptionRepository.clear()
    InMemoryPlatformAuditRepository.clear()
    InMemoryBusinessMembershipRepository.clear()


def register_and_login(email: str, password: str, full_name: str = "Test User") -> str:
    resp = client.post("/api/v1/auth/register", json={
        "email": email,
        "full_name": full_name,
        "password": password,
        "password_confirmation": password
    })
    assert resp.status_code == 200 or resp.status_code == 201

    login_resp = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password
    })
    login_data = login_resp.json()
    return login_data.get("access_token") or login_data["data"]["access_token"]


def create_super_admin(email: str = "super@platform.dev", password: str = "SuperAdminPass123!"):
    # Use repo directly to seed super admin for testing
    import asyncio
    async def _seed():
        return await user_repository.seed_development_superadmin(email=email, plain_password=password)
    return asyncio.run(_seed())


def test_platform_authorization_guard():
    token = register_and_login("tenant@business.dev", "Password123!")
    
    # Normal user cannot access platform dashboard
    resp = client.get("/api/v1/platform/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_super_admin_dashboard_and_businesses():
    super_user = create_super_admin("admin@platform.dev", "AdminPass123!")
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "admin@platform.dev",
        "password": "AdminPass123!"
    })
    login_data = login_resp.json()
    token = login_data.get("access_token") or login_data["data"]["access_token"]

    # Dashboard access
    resp = client.get("/api/v1/platform/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "total_businesses" in data
    assert "mrr_idr" in data

    # List businesses (initially empty)
    resp2 = client.get("/api/v1/platform/businesses", headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 200
    assert len(resp2.json()["data"]) == 0


def test_business_lifecycle_and_suspension_enforcement():
    # 1. Create tenant user and business
    tenant_token = register_and_login("owner@business.dev", "Password123!")
    biz_resp = client.post("/api/v1/businesses", headers={"Authorization": f"Bearer {tenant_token}"}, json={
        "name": "Test Retail",
        "business_type": "retail",
        "timezone": "UTC",
        "locale": "en-US"
    })
    assert biz_resp.status_code == 200 or biz_resp.status_code == 201
    biz_id = biz_resp.json().get("id") or biz_resp.json()["data"]["id"]

    # Verify default subscription created
    sub = subscription_repository._business_index.get(biz_id)
    assert sub is not None

    # 2. Super Admin suspends business
    super_user = create_super_admin("admin2@platform.dev", "AdminPass123!")
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "admin2@platform.dev",
        "password": "AdminPass123!"
    })
    login_data = login_resp.json()
    admin_token = login_data.get("access_token") or login_data["data"]["access_token"]

    suspend_resp = client.post(f"/api/v1/platform/businesses/{biz_id}/suspend", headers={"Authorization": f"Bearer {admin_token}"}, json={
        "reason": "Policy violation"
    })
    assert suspend_resp.status_code == 200
    assert suspend_resp.json()["data"]["status"] == "suspended"

    # 3. Tenant user attempts operation -> should be blocked by business suspension guard
    tenant_req = client.get(f"/api/v1/businesses/{biz_id}", headers={"Authorization": f"Bearer {tenant_token}"})
    assert tenant_req.status_code == 403
    assert "suspended" in tenant_req.json()["message"].lower() or "suspended" in tenant_req.json()["errors"][0].lower()

    # 4. Super Admin reactivates business
    activate_resp = client.post(f"/api/v1/platform/businesses/{biz_id}/activate", headers={"Authorization": f"Bearer {admin_token}"}, json={
        "reason": "Resolved"
    })
    assert activate_resp.status_code == 200
    assert activate_resp.json()["data"]["status"] == "active"

    # 5. Tenant access restored
    tenant_req2 = client.get(f"/api/v1/businesses/{biz_id}", headers={"Authorization": f"Bearer {tenant_token}"})
    assert tenant_req2.status_code == 200


def test_subscription_override():
    tenant_token = register_and_login("owner2@business.dev", "Password123!")
    biz_resp = client.post("/api/v1/businesses", headers={"Authorization": f"Bearer {tenant_token}"}, json={
        "name": "Sub Test",
        "business_type": "service",
        "timezone": "UTC",
        "locale": "en-US"
    })
    biz_id = biz_resp.json().get("id") or biz_resp.json()["data"]["id"]
    sub = subscription_repository._subscriptions[subscription_repository._business_index[biz_id]]

    super_user = create_super_admin("admin3@platform.dev", "AdminPass123!")
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "admin3@platform.dev",
        "password": "AdminPass123!"
    })
    login_data = login_resp.json()
    admin_token = login_data.get("access_token") or login_data["data"]["access_token"]

    # Override subscription period extension
    override_resp = client.post(f"/api/v1/platform/subscriptions/{sub.id}/override", headers={"Authorization": f"Bearer {admin_token}"}, json={
        "action": "EXTEND",
        "extend_days": 60,
        "reason": "Paid annual advance"
    })
    assert override_resp.status_code == 200
    data = override_resp.json()["data"]
    assert data["status"] == "ACTIVE"

    # Audit logs verification
    logs_resp = client.get("/api/v1/platform/audit-logs", headers={"Authorization": f"Bearer {admin_token}"})
    assert logs_resp.status_code == 200
    logs = logs_resp.json()["data"]
    assert any(l["action"] == "SUBSCRIPTION_OVERRIDE" for l in logs)

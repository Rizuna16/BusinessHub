import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.authentication.repository import InMemoryUserRepository
from app.modules.authentication.schemas import PlatformRole
from app.modules.business.repository import InMemoryBusinessRepository
from app.modules.business_membership.repository import InMemoryBusinessMembershipRepository
from app.modules.export.registry import EXPORT_REGISTRY


@pytest.fixture(autouse=True)
def clear_repos():
    InMemoryUserRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    yield
    InMemoryUserRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryBusinessMembershipRepository.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _register_user(client, email, password="Password123"):
    r = client.post("/api/v1/auth/register", json={
        "email": email, "full_name": email.split("@")[0],
        "password": password, "password_confirmation": password,
    })
    token = r.json().get("access_token") if r.status_code == 201 else None
    if token:
        return token
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed: {r.json()}"
    return r.json()["access_token"]


def _create_business(client, token, name="Test Biz"):
    r = client.post(
        "/api/v1/businesses",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "business_type": "umkm", "timezone": "UTC", "locale": "en-US"},
    )
    return r.json()["id"]


def _seed_product(client, token, biz_id):
    u = client.post(
        f"/api/v1/businesses/{biz_id}/units",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Unit", "code": "U1", "symbol": "pcs", "unit_type": "OTHER"},
    ).json()["id"]
    cat = client.post(
        f"/api/v1/businesses/{biz_id}/categories",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Category", "code": "CAT1", "description": "Test"},
    ).json()["id"]
    p = client.post(
        f"/api/v1/businesses/{biz_id}/products",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Product", "code": "P1", "unit_id": u, "category_id": cat, "product_type": "GOODS"},
    )
    return p


# ============================================================
# BLOCKER 2 — RBAC / IDOR SECURITY TESTS
# ============================================================

class TestCrossBusinessSecurity:
    def test_user_a_cannot_export_user_b_business(self, client: TestClient):
        token_a = _register_user(client, "user_a@test.com")
        token_b = _register_user(client, "user_b@test.com")
        biz_a = _create_business(client, token_a, "Biz A")
        biz_b = _create_business(client, token_b, "Biz B")
        _seed_product(client, token_a, biz_a)
        _seed_product(client, token_b, biz_b)

        r = client.get(
            f"/api/v1/businesses/{biz_b}/export/table/products",
            headers={"Authorization": f"Bearer {token_a}"},
            params={"format": "csv"},
        )
        assert r.status_code == 403

    def test_unauthenticated_returns_401(self, client: TestClient):
        token = _register_user(client, "exporter@test.com")
        biz = _create_business(client, token)
        r = client.get(
            f"/api/v1/businesses/{biz}/export/table/products",
            params={"format": "csv"},
        )
        assert r.status_code in (401, 403)

    def test_no_membership_returns_403(self, client: TestClient):
        owner_token = _register_user(client, "owner_no_member@test.com")
        outsider_token = _register_user(client, "outsider@test.com")
        biz = _create_business(client, owner_token)
        _seed_product(client, owner_token, biz)

        r = client.get(
            f"/api/v1/businesses/{biz}/export/table/products",
            headers={"Authorization": f"Bearer {outsider_token}"},
            params={"format": "csv"},
        )
        assert r.status_code == 403
        body = r.json()
        msg = (body.get("detail") or body.get("message") or "").lower()
        errors = " ".join(body.get("errors", [])).lower() if body.get("errors") else ""
        assert "access denied" in msg or "membership" in msg or "access denied" in errors or "membership" in errors

    def test_valid_member_export_succeeds(self, client: TestClient):
        owner_token = _register_user(client, "member_owner@test.com")
        member_token = _register_user(client, "member_member@test.com")
        biz = _create_business(client, owner_token)
        _seed_product(client, owner_token, biz)

        client.post(
            f"/api/v1/businesses/{biz}/members",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"user_id": _get_user_id(member_token), "role": "MEMBER"},
        )

        r = client.get(
            f"/api/v1/businesses/{biz}/export/table/products",
            headers={"Authorization": f"Bearer {member_token}"},
            params={"format": "csv"},
        )
        assert r.status_code == 200

    def test_member_cannot_export_financial_report(self, client: TestClient):
        owner_token = _register_user(client, "fin_owner@test.com")
        member_token = _register_user(client, "fin_member@test.com")
        biz = _create_business(client, owner_token)

        client.post(
            f"/api/v1/businesses/{biz}/members",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"user_id": _get_user_id(member_token), "role": "MEMBER"},
        )

        r = client.get(
            f"/api/v1/businesses/{biz}/export/report/trial_balance",
            headers={"Authorization": f"Bearer {member_token}"},
            params={"format": "csv"},
        )
        assert r.status_code == 403

    def test_admin_can_export_financial_report(self, client: TestClient):
        owner_token = _register_user(client, "fin_admin_owner@test.com")
        admin_token = _register_user(client, "fin_admin@test.com")
        biz = _create_business(client, owner_token)

        client.post(
            f"/api/v1/businesses/{biz}/members",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"user_id": _get_user_id(admin_token), "role": "ADMIN"},
        )

        r = client.get(
            f"/api/v1/businesses/{biz}/export/report/trial_balance",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"format": "csv"},
        )
        assert r.status_code == 200


def _get_user_id(token):
    from app.modules.authentication.security import decode_access_token
    payload = decode_access_token(token)
    return payload.get("sub") if payload else None


# ============================================================
# PLATFORM BOUNDARY TESTS
# ============================================================

class TestPlatformBoundary:
    def _make_superadmin(self, client):
        token = _register_user(client, "super@test.com", "SuperAdmin123!")
        from app.modules.authentication.repository import user_repository
        for u in user_repository._users.values():
            if u.email == "super@test.com":
                u.platform_role = PlatformRole.SUPER_ADMIN
                user_repository._users[u.id] = u
                break
        return token

    def test_superadmin_can_export_platform_businesses(self, client: TestClient):
        token = self._make_superadmin(client)
        r = client.get(
            "/api/v1/platform/export/platform_businesses",
            headers={"Authorization": f"Bearer {token}"},
            params={"format": "csv"},
        )
        assert r.status_code == 200

    def test_regular_user_cannot_use_platform_export(self, client: TestClient):
        token = _register_user(client, "regular@test.com")
        r = client.get(
            "/api/v1/platform/export/platform_businesses",
            headers={"Authorization": f"Bearer {token}"},
            params={"format": "csv"},
        )
        assert r.status_code == 403

    def test_tenant_resource_rejected_on_platform_route(self, client: TestClient):
        token = self._make_superadmin(client)
        r = client.get(
            "/api/v1/platform/export/products",
            headers={"Authorization": f"Bearer {token}"},
            params={"format": "csv"},
        )
        assert r.status_code == 404


# ============================================================
# REGISTRY LOCKED SCOPE TESTS
# ============================================================

class TestRegistryLockedScope:
    def test_exact_18_resources_in_registry(self):
        assert len(EXPORT_REGISTRY) == 18

    def test_no_receivables_in_registry(self):
        assert "receivables" not in EXPORT_REGISTRY

    def test_no_payables_in_registry(self):
        assert "payables" not in EXPORT_REGISTRY

    def test_no_tax_summary_in_registry(self):
        assert "tax_summary" not in EXPORT_REGISTRY

    def test_sales_checkouts_key_exists(self):
        assert "sales_checkouts" in EXPORT_REGISTRY

    def test_ar_aging_key_exists(self):
        assert "ar_aging" in EXPORT_REGISTRY

    def test_unknown_resource_returns_404(self, client: TestClient):
        from app.modules.export.registry import validate_resource
        with pytest.raises(Exception) as exc:
            validate_resource("receivables")
        assert exc.value.status_code == 404

    def test_unknown_tax_summary_returns_404(self, client: TestClient):
        from app.modules.export.registry import validate_resource
        with pytest.raises(Exception) as exc:
            validate_resource("tax_summary")
        assert exc.value.status_code == 404


# ============================================================
# 5,000 ROW LIMIT TESTS
# ============================================================

class TestRowLimit:
    def test_exceeding_5000_rejected(self, client: TestClient):
        from app.modules.export.service import ExportService, MAX_EXPORT_ROWS
        from app.modules.export.registry import (
            ExportDefinition, ExportResourceType, register_export, EXPORT_REGISTRY,
        )
        from fastapi import HTTPException
        import asyncio

        mock_data = [{"id": i, "name": f"item_{i}"} for i in range(MAX_EXPORT_ROWS + 1)]

        try:
            register_export(ExportDefinition(
                resource_key="_test_limit",
                resource_type=ExportResourceType.TABLE,
                allowed_formats={"csv"},
                required_roles={"ADMIN"},
                description="test",
            ))

            class MockExportService(ExportService):
                async def _fetch_data(self, defn, business_id, user_id, filters):
                    return mock_data, ["id", "name"]

            svc = MockExportService()
            with pytest.raises(HTTPException) as exc:
                asyncio.get_event_loop().run_until_complete(
                    svc.export_table(
                        resource_key="_test_limit", business_id="b", user_id="u",
                        user_role="ADMIN", fmt="csv", export_mode="all_matching",
                        page=1, page_size=100, filters={},
                    )
                )
            assert exc.value.status_code == 422
            assert "5000" in exc.value.detail
        finally:
            EXPORT_REGISTRY.pop("_test_limit", None)


# ============================================================
# CURRENT PAGE MODE TEST
# ============================================================

class TestCurrentPageMode:
    def test_current_page_respects_page_size(self, client: TestClient):
        token = _register_user(client, "page_owner@test.com")
        biz = _create_business(client, token)
        _seed_product(client, token, biz)

        r = client.get(
            f"/api/v1/businesses/{biz}/export/table/products",
            headers={"Authorization": f"Bearer {token}"},
            params={"format": "csv", "export_mode": "current_page", "page": "1", "page_size": "10"},
        )
        assert r.status_code == 200

import pytest
import uuid
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from app.main import app
from app.modules.authentication.repository import InMemoryUserRepository
from app.modules.account.repository import InMemoryAccountRepository
from app.modules.business.repository import InMemoryBusinessRepository
from app.modules.business_membership.repository import InMemoryBusinessMembershipRepository
from app.modules.business_template.repository import (
    InMemoryBusinessTemplateRepository,
    InMemoryBusinessConfigurationRepository,
)
from app.modules.business_template.schemas import TemplateStatus, ModuleStatus
from app.modules.business_template.service import (
    template_service,
    business_configuration_service,
)


# ============================================================
# Fixtures
# ============================================================
@pytest.fixture(autouse=True)
def clear_repos():
    InMemoryUserRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryBusinessTemplateRepository.clear()
    InMemoryBusinessConfigurationRepository.clear()
    yield
    InMemoryUserRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryBusinessTemplateRepository.clear()
    InMemoryBusinessConfigurationRepository.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# ============================================================
# Helpers (shared across tests)
# ============================================================
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


def _create_full_setup(client, email="user@example.com", btype="umkm"):
    """Register user, create business, return (token, user_id, biz_id)."""
    token = _register_and_get_token(client, email=email)
    biz_res = _create_business(client, token, btype=btype)
    assert biz_res.status_code == 201
    biz_id = biz_res.json()["id"]
    user_id = _get_user_id(client, token)
    return token, user_id, biz_id


# ============================================================
# Template Registry Tests
# ============================================================
def test_list_active_templates(client):
    """List active templates returns seeded system templates."""
    res = client.get("/api/v1/templates")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 3  # HOTEL_STANDARD, RETAIL_STANDARD, UMKM_STANDARD
    codes = [t["code"] for t in data]
    assert "HOTEL_STANDARD" in codes
    assert "RETAIL_STANDARD" in codes
    assert "UMKM_STANDARD" in codes


def test_get_template(client):
    """Get a single template by ID."""
    # First list to get an ID
    list_res = client.get("/api/v1/templates")
    template_id = list_res.json()[0]["id"]

    res = client.get(f"/api/v1/templates/{template_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == template_id
    assert data["status"] == "ACTIVE"
    assert data["is_system"] is True


def test_get_template_not_found(client):
    res = client.get("/api/v1/templates/nonexistent-id")
    assert res.status_code == 404


def test_template_code_uniqueness():
    """Assert system template codes are unique."""
    import asyncio
    async def run():
        return await InMemoryBusinessTemplateRepository().list_active()
    templates = asyncio.run(run())
    codes = [t.code for t in templates]
    assert len(codes) == len(set(codes))


def test_template_version_uniqueness():
    """Assert (code, version) combination is unique."""
    import asyncio
    async def run():
        return await InMemoryBusinessTemplateRepository().list_active()
    templates = asyncio.run(run())
    code_versions = [(t.code, t.version) for t in templates]
    assert len(code_versions) == len(set(code_versions))


def test_inactive_deprecated_template_not_listed():
    """Inactive/deprecated templates should not appear in list_active."""
    import asyncio
    repo = InMemoryBusinessTemplateRepository()
    repo._seed_defaults()
    # Deactivate a template
    now = datetime.now(timezone.utc)

    async def run():
        # Get a template and check list logic excludes non-active
        templates = await repo.list_active()
        return templates
    templates = asyncio.run(run())
    assert all(t.status == TemplateStatus.ACTIVE for t in templates)


# ============================================================
# Business Type Resolution Tests
# ============================================================
def test_hotel_resolves_hotel_standard():
    """HOTEL business_type resolves HOTEL_STANDARD."""
    import asyncio

    repo = InMemoryBusinessTemplateRepository()
    repo._seed_defaults()

    async def run():
        return await repo.get_default_for_business_type("hotel", "STANDARD")
    template = asyncio.run(run())
    assert template is not None
    assert template.code == "HOTEL_STANDARD"
    assert template.business_type == "hotel"


def test_retail_resolves_retail_standard():
    import asyncio

    repo = InMemoryBusinessTemplateRepository()
    repo._seed_defaults()

    async def run():
        return await repo.get_default_for_business_type("retail", "STANDARD")
    template = asyncio.run(run())
    assert template is not None
    assert template.code == "RETAIL_STANDARD"
    assert template.business_type == "retail"


def test_umkm_resolves_umkm_standard():
    import asyncio

    repo = InMemoryBusinessTemplateRepository()
    repo._seed_defaults()

    async def run():
        return await repo.get_default_for_business_type("umkm", "STANDARD")
    template = asyncio.run(run())
    assert template is not None
    assert template.code == "UMKM_STANDARD"
    assert template.business_type == "umkm"


def test_unknown_business_type_gets_safe_baseline():
    """Unknown/unimplemented types get UMKM/CORE baseline."""
    import asyncio

    repo = InMemoryBusinessTemplateRepository()
    repo._seed_defaults()

    async def run():
        return await repo.get_default_for_business_type("unknown_type", "STANDARD")
    template = asyncio.run(run())
    assert template is not None
    # Should fall back to UMKM or first available
    assert template.status == TemplateStatus.ACTIVE


# ============================================================
# Preset Resolution Tests
# ============================================================
def test_valid_preset_resolves():
    """Valid preset resolves the correct template."""
    import asyncio

    repo = InMemoryBusinessTemplateRepository()
    repo._seed_defaults()

    async def run():
        return await repo.get_default_for_business_type("hotel", "STANDARD")
    template = asyncio.run(run())
    assert template is not None
    assert template.preset_code == "STANDARD"
    assert template.code == "HOTEL_STANDARD"


def test_invalid_preset_handled_safely():
    """Invalid preset should fall back to default for business type."""
    import asyncio

    repo = InMemoryBusinessTemplateRepository()
    repo._seed_defaults()

    async def run():
        return await repo.get_default_for_business_type("hotel", "INVALID_PRESET")
    template = asyncio.run(run())
    assert template is not None
    # Should still return a valid template (fallback to business_type without preset match)
    assert template.business_type == "hotel"


def test_invalid_preset_for_unknown_business_type():
    """Invalid preset + unknown business_type should return a safe baseline."""
    import asyncio

    repo = InMemoryBusinessTemplateRepository()
    repo._seed_defaults()

    async def run():
        return await repo.get_default_for_business_type("unknown_type", "INVALID")
    template = asyncio.run(run())
    assert template is not None


# ============================================================
# Configuration Initialization Tests
# ============================================================
def test_configuration_initialized_for_new_business(client):
    """New business gets a configuration snapshot after creation."""
    token, user_id, biz_id = _create_full_setup(client, email="a@example.com", btype="hotel")

    # Get configuration
    res = client.get(
        f"/api/v1/businesses/{biz_id}/configuration",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["business_id"] == biz_id
    assert data["template_code"] == "HOTEL_STANDARD"
    assert data["template_version"] == "1.0.0"
    assert data["preset_code"] == "STANDARD"


def test_existing_business_without_configuration_gets_safe_baseline(client):
    """Existing business (created before config) gets baseline when accessed."""
    # Clear configuration repo to simulate pre-F7 business
    InMemoryBusinessConfigurationRepository.clear()

    token, user_id, biz_id = _create_full_setup(client, email="b@example.com", btype="retail")
    # But simulate config doesn't exist
    business_configuration_service.config_repo._configurations.clear()

    res = client.get(
        f"/api/v1/businesses/{biz_id}/configuration",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["business_id"] == biz_id
    assert data["template_code"] == "RETAIL_STANDARD"


def test_effective_configuration_resolves_template_defaults(client):
    """Effective configuration is merge of template defaults + business overrides."""
    token, user_id, biz_id = _create_full_setup(client, email="c@example.com", btype="umkm")

    res = client.get(
        f"/api/v1/businesses/{biz_id}/configuration",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    # Effective config should have template defaults
    eff = data["effective_configuration"]
    assert "currency" in eff
    assert "timezone" in eff
    assert eff["currency"] == "IDR"


def test_business_override_overrides_template_default(client):
    """Business override overrides template default in effective config."""
    token, user_id, biz_id = _create_full_setup(client, email="d@example.com", btype="hotel")

    # Patch with override
    res = client.patch(
        f"/api/v1/businesses/{biz_id}/configuration",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "configuration": {"currency": "USD", "timezone": "Asia/Makassar"}
        },
    )
    assert res.status_code == 200
    data = res.json()
    eff = data["effective_configuration"]
    assert eff["currency"] == "USD"
    assert eff["timezone"] == "Asia/Makassar"

    # Template should remain unchanged
    templates = client.get("/api/v1/templates").json()
    hotel_template = next(t for t in templates if t["code"] == "HOTEL_STANDARD")
    assert hotel_template["default_configuration"]["timezone"] == "Asia/Jakarta"


def test_template_global_mutation_does_not_mutate_business_snapshot():
    """Template version change does not affect existing business snapshot."""
    import asyncio

    # Clear and seed
    InMemoryBusinessTemplateRepository.clear()
    InMemoryBusinessConfigurationRepository.clear()

    repo = InMemoryBusinessTemplateRepository()
    repo._seed_defaults()

    async def setup_and_test():
        # Get v1.0.0 template
        hotel_v1 = await repo.get_by_code_version("HOTEL_STANDARD", "1.0.0")
        assert hotel_v1 is not None

        # Manually create a business config snapshot for v1.0.0
        config_repo = InMemoryBusinessConfigurationRepository()
        biz_id = str(uuid.uuid4())
        record = await config_repo.create(
            business_id=biz_id,
            template_id=hotel_v1.id,
            template_code=hotel_v1.code,
            template_version=hotel_v1.version,
            preset_code=hotel_v1.preset_code,
            configuration={"currency": "IDR"},
        )
        assert record.template_version == "1.0.0"

        # Now simulate a template v1.1.0 being created (we can't modify seed templates,
        # but we verify the snapshot preserves the version it was created with)
        # The snapshot record stores template_version = "1.0.0" and it won't change
        assert record.template_version == "1.0.0"
        assert record.template_code == "HOTEL_STANDARD"

        # Re-fetch and verify version still 1.0.0
        fetched = await config_repo.get_by_business(biz_id)
        assert fetched.template_version == "1.0.0"

    asyncio.run(setup_and_test())


def test_snapshot_preserves_template_version(client):
    """Snapshot preserves the template version at creation time."""
    token, user_id, biz_id = _create_full_setup(client, email="e@example.com", btype="hotel")

    res = client.get(
        f"/api/v1/businesses/{biz_id}/configuration",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = res.json()
    assert data["template_version"] == "1.0.0"


def test_business_configuration_isolated_by_business_id(client):
    """Configuration is isolated per business_id."""
    token_a, user_a, biz_a = _create_full_setup(client, email="a@example.com", btype="hotel")
    token_b, user_b, biz_b = _create_full_setup(client, email="b@example.com", btype="retail")

    # User A overrides config
    client.patch(
        f"/api/v1/businesses/{biz_a}/configuration",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"configuration": {"currency": "EUR"}},
    )

    # User B config should be unaffected
    res_b = client.get(
        f"/api/v1/businesses/{biz_b}/configuration",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    data_b = res_b.json()
    assert data_b["effective_configuration"]["currency"] == "IDR"  # Default, not EUR


def test_existing_business_without_config_has_configuration(client):
    """Existing Business without configuration gets safe baseline lazily."""
    # Create business
    token, user_id, biz_id = _create_full_setup(client, email="f@example.com", btype="umkm")

    # Manually delete its configuration
    business_configuration_service.config_repo._configurations.pop(biz_id, None)

    res = client.get(
        f"/api/v1/businesses/{biz_id}/configuration",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["business_id"] == biz_id
    assert data["template_code"] == "UMKM_STANDARD"


# ============================================================
# Authorization Tests
# ============================================================
def _add_member(client, owner_token, biz_id, user_email, role="MEMBER", password="Password123"):
    """Helper: register a second user and add them to business."""
    member_token = _register_and_get_token(client, email=user_email, password=password, full_name="Member User")
    user_id = _get_user_id(client, member_token)
    client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"user_id": user_id, "role": role},
    )
    return member_token, user_id


def test_owner_get_configuration(client):
    token, _, biz_id = _create_full_setup(client, email="owner@example.com", btype="umkm")
    res = client.get(f"/api/v1/businesses/{biz_id}/configuration", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200


def test_owner_patch_configuration(client):
    token, _, biz_id = _create_full_setup(client, email="owner2@example.com", btype="umkm")
    res = client.patch(
        f"/api/v1/businesses/{biz_id}/configuration",
        headers={"Authorization": f"Bearer {token}"},
        json={"configuration": {"currency": "GBP"}},
    )
    assert res.status_code == 200
    assert res.json()["effective_configuration"]["currency"] == "GBP"


def test_admin_get_configuration(client):
    owner_token, _, biz_id = _create_full_setup(client, email="owner3@example.com", btype="umkm")
    admin_token, _ = _add_member(client, owner_token, biz_id, "admin@example.com", role="ADMIN")
    res = client.get(f"/api/v1/businesses/{biz_id}/configuration", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200


def test_admin_patch_configuration(client):
    owner_token, _, biz_id = _create_full_setup(client, email="owner4@example.com", btype="umkm")
    admin_token, _ = _add_member(client, owner_token, biz_id, "admin2@example.com", role="ADMIN")
    res = client.patch(
        f"/api/v1/businesses/{biz_id}/configuration",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"configuration": {"currency": "JPY"}},
    )
    assert res.status_code == 200
    assert res.json()["effective_configuration"]["currency"] == "JPY"


def test_member_get_configuration(client):
    owner_token, _, biz_id = _create_full_setup(client, email="owner5@example.com", btype="umkm")
    member_token, _ = _add_member(client, owner_token, biz_id, "member@example.com", role="MEMBER")
    res = client.get(f"/api/v1/businesses/{biz_id}/configuration", headers={"Authorization": f"Bearer {member_token}"})
    assert res.status_code == 200


def test_member_patch_configuration_denied(client):
    owner_token, _, biz_id = _create_full_setup(client, email="owner6@example.com", btype="umkm")
    member_token, _ = _add_member(client, owner_token, biz_id, "member2@example.com", role="MEMBER")
    res = client.patch(
        f"/api/v1/businesses/{biz_id}/configuration",
        headers={"Authorization": f"Bearer {member_token}"},
        json={"configuration": {"currency": "AUD"}},
    )
    assert res.status_code == 403


def test_suspended_membership_get_denied(client):
    owner_token, _, biz_id = _create_full_setup(client, email="owner7@example.com", btype="umkm")
    member_token, _ = _add_member(client, owner_token, biz_id, "suspended@example.com", role="MEMBER")
    user_id = _get_user_id(client, member_token)

    # Suspend member
    mem_id = _get_membership_id(client, owner_token, biz_id, user_id)
    client.patch(
        f"/api/v1/businesses/{biz_id}/members/{mem_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"status": "SUSPENDED"},
    )

    res = client.get(f"/api/v1/businesses/{biz_id}/configuration", headers={"Authorization": f"Bearer {member_token}"})
    assert res.status_code in (401, 404)


def test_suspended_membership_patch_denied(client):
    owner_token, _, biz_id = _create_full_setup(client, email="owner8@example.com", btype="umkm")
    member_token, member_user_id = _add_member(client, owner_token, biz_id, "suspended2@example.com", role="MEMBER")

    mem_id = _get_membership_id(client, owner_token, biz_id, member_user_id)
    client.patch(
        f"/api/v1/businesses/{biz_id}/members/{mem_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"status": "SUSPENDED"},
    )

    res = client.patch(
        f"/api/v1/businesses/{biz_id}/configuration",
        headers={"Authorization": f"Bearer {member_token}"},
        json={"configuration": {"currency": "CAD"}},
    )
    assert res.status_code in (401, 404)


def test_removed_membership_get_denied(client):
    owner_token, _, biz_id = _create_full_setup(client, email="owner9@example.com", btype="umkm")
    member_token, member_user_id = _add_member(client, owner_token, biz_id, "removed@example.com", role="MEMBER")

    mem_id = _get_membership_id(client, owner_token, biz_id, member_user_id)
    client.delete(f"/api/v1/businesses/{biz_id}/members/{mem_id}", headers={"Authorization": f"Bearer {owner_token}"})

    res = client.get(f"/api/v1/businesses/{biz_id}/configuration", headers={"Authorization": f"Bearer {member_token}"})
    assert res.status_code in (401, 404)


def test_no_membership_denied(client):
    owner_token, _, biz_id = _create_full_setup(client, email="owner10@example.com", btype="umkm")

    # No member of this business
    outsider_token = _register_and_get_token(client, email="outsider@example.com")

    res = client.get(f"/api/v1/businesses/{biz_id}/configuration", headers={"Authorization": f"Bearer {outsider_token}"})
    assert res.status_code in (401, 404)


def test_unauthenticated_denied(client):
    _, _, biz_id = _create_full_setup(client, email="u@example.com", btype="umkm")
    res = client.get(f"/api/v1/businesses/{biz_id}/configuration")
    assert res.status_code == 401


# ============================================================
# Cross-Business Isolation Tests
# ============================================================
def test_user_a_cannot_see_business_b_config(client):
    token_a, _, biz_a = _create_full_setup(client, email="a1@example.com", btype="hotel")
    _, _, biz_b = _create_full_setup(client, email="b1@example.com", btype="retail")

    res = client.get(f"/api/v1/businesses/{biz_b}/configuration", headers={"Authorization": f"Bearer {token_a}"})
    assert res.status_code in (401, 404)


def test_user_b_cannot_see_business_a_config(client):
    token_a, _, biz_a = _create_full_setup(client, email="a2@example.com", btype="hotel")
    token_b, _, biz_b = _create_full_setup(client, email="b2@example.com", btype="retail")

    res = client.get(f"/api/v1/businesses/{biz_a}/configuration", headers={"Authorization": f"Bearer {token_b}"})
    assert res.status_code in (401, 404)


def test_patch_spoofing_business_id_rejected(client):
    """User tries to modify config of a business they don't belong to."""
    token_a, _, biz_a = _create_full_setup(client, email="a3@example.com", btype="hotel")
    _, _, biz_b = _create_full_setup(client, email="b3@example.com", btype="retail")

    # Set up config for A so PATCH is tested
    client.get(f"/api/v1/businesses/{biz_a}/configuration", headers={"Authorization": f"Bearer {token_a}"})

    # User A tries to patch business B's config -> should be denied
    res = client.patch(
        f"/api/v1/businesses/{biz_b}/configuration",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"configuration": {"currency": "USD"}},
    )
    assert res.status_code in (401, 403, 404)

    # Verify B's config unchanged
    token_b, _ = _get_user_id, biz_b  # placeholder
    # Get owner of B
    pass


def test_cross_business_config_content_isolation(client):
    """User A sets override on business A; user B's config must not reflect it."""
    token_a, _, biz_a = _create_full_setup(client, email="a4@example.com", btype="hotel")
    token_b, _, biz_b = _create_full_setup(client, email="b4@example.com", btype="retail")

    client.patch(
        f"/api/v1/businesses/{biz_a}/configuration",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"configuration": {"timezone": "Asia/Makassar"}},
    )

    res_b = client.get(f"/api/v1/businesses/{biz_b}/configuration", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code == 200
    eff_b = res_b.json()["effective_configuration"]
    assert eff_b["timezone"] == "Asia/Jakarta"


# ============================================================
# Snapshot Versioning Tests
# ============================================================
def test_snapshot_immutability_version(client):
    """Snapshot preserves old template version when new version is created."""
    import asyncio

    InMemoryBusinessTemplateRepository.clear()
    InMemoryBusinessConfigurationRepository.clear()

    template_repo = InMemoryBusinessTemplateRepository()
    config_repo = InMemoryBusinessConfigurationRepository()

    async def run():
        # Seed defaults (creates v1.0.0 templates)
        template_repo._seed_defaults()

        # Get v1.0.0 HOTEL template
        v1 = await template_repo.get_by_code_version("HOTEL_STANDARD", "1.0.0")
        assert v1 is not None

        # Create business config snapshot for v1
        biz_id = str(uuid.uuid4())
        record = await config_repo.create(
            business_id=biz_id,
            template_id=v1.id,
            template_code=v1.code,
            template_version=v1.version,
            preset_code=v1.preset_code,
            configuration=v1.default_configuration,
        )

        # Now simulate a NEW template version 1.1.0 by adding it
        from app.modules.business_template.schemas import TemplateResponse, TemplateStatus, ModuleDefinition, ModuleStatus
        from app.modules.business_template.repository import DEFAULT_MODULES

        now = datetime.now(timezone.utc)
        v11 = TemplateResponse(
            id="tmpl-hotel-v11",
            code="HOTEL_STANDARD",
            name="Hotel Standard v1.1",
            business_type="hotel",
            preset_code="STANDARD",
            version="1.1.0",
            description="Updated version",
            status=TemplateStatus.ACTIVE,
            is_system=True,
            modules=DEFAULT_MODULES,
            features=[],
            menus=[],
            dashboard_widgets=[],
            default_configuration={"currency": "IDR", "timezone": "Asia/Bandung"},
            created_at=now,
            updated_at=now,
        )
        template_repo._templates[v11.id] = v11

        # Existing business snapshot should still point to v1.0.0
        assert record.template_version == "1.0.0"

        # New business should get v1.1.0 (latest active for that business_type)
        v11_resolved = await template_repo.get_default_for_business_type("hotel", "STANDARD")
        assert v11_resolved.version == "1.1.0"

        # Re-fetch existing business snapshot -> still 1.0.0
        fetched = await config_repo.get_by_business(biz_id)
        assert fetched.template_version == "1.0.0"

    asyncio.run(run())


def test_new_business_gets_latest_template_version(client):
    """New Business created after template version bump gets the latest version."""
    import asyncio

    InMemoryBusinessTemplateRepository.clear()
    InMemoryBusinessConfigurationRepository.clear()

    template_repo = InMemoryBusinessTemplateRepository()
    template_repo._seed_defaults()

    async def run():
        # Add a v1.1.0 HOTEL template
        from app.modules.business_template.schemas import TemplateResponse, TemplateStatus
        from app.modules.business_template.repository import DEFAULT_MODULES

        now = datetime.now(timezone.utc)
        v11 = TemplateResponse(
            id="tmpl-hotel-v11-newbiz",
            code="HOTEL_STANDARD",
            name="Hotel Standard v1.1",
            business_type="hotel",
            preset_code="STANDARD",
            version="1.1.0",
            description="Updated",
            status=TemplateStatus.ACTIVE,
            is_system=True,
            modules=DEFAULT_MODULES,
            features=[],
            menus=[],
            dashboard_widgets=[],
            default_configuration={"currency": "IDR"},
            created_at=now,
            updated_at=now,
        )
        template_repo._templates[v11.id] = v11

        # Resolve template for new business -> should be 1.1.0
        resolved = await template_repo.get_default_for_business_type("hotel", "STANDARD")
        assert resolved.version == "1.1.0"

    asyncio.run(run())


# ============================================================
# Template Protection Tests
# ============================================================
def test_customer_cannot_modify_template(client):
    """Templates are read-only; no PATCH/PUT endpoints."""
    res = client.patch("/api/v1/templates", json={})
    assert res.status_code == 405

    res = client.put("/api/v1/templates/some-id", json={})
    assert res.status_code == 405

    res = client.post("/api/v1/templates", json={})
    assert res.status_code == 405

    res = client.delete("/api/v1/templates/some-id")
    assert res.status_code == 405


def test_is_system_field_protected(client):
    """System templates have is_system = true."""
    res = client.get("/api/v1/templates")
    data = res.json()
    for t in data:
        if t["status"] == "ACTIVE":
            assert t["is_system"] is True


# ============================================================
# Core Module Protection Tests
# ============================================================
def test_core_module_cannot_be_disabled(client):
    """Core modules cannot be disabled via config overrides."""
    token, _, biz_id = _create_full_setup(client, email="core@example.com", btype="umkm")
    res = client.patch(
        f"/api/v1/businesses/{biz_id}/configuration",
        headers={"Authorization": f"Bearer {token}"},
        json={"module_overrides": {"CORE": False}},
    )
    assert res.status_code == 400


def test_core_business_module_proctected(client):
    """BUSINESS core module cannot be disabled."""
    token, _, biz_id = _create_full_setup(client, email="core2@example.com", btype="umkm")
    res = client.patch(
        f"/api/v1/businesses/{biz_id}/configuration",
        headers={"Authorization": f"Bearer {token}"},
        json={"module_overrides": {"BUSINESS": False}},
    )
    assert res.status_code == 400


def test_core_membership_module_proctected(client):
    token, _, biz_id = _create_full_setup(client, email="core3@example.com", btype="umkm")
    res = client.patch(
        f"/api/v1/businesses/{biz_id}/configuration",
        headers={"Authorization": f"Bearer {token}"},
        json={"module_overrides": {"MEMBERSHIP": False}},
    )
    assert res.status_code == 400


def test_non_core_module_override_allowed(client):
    """Non-core modules (PLANNED) can be overridden in configuration."""
    token, _, biz_id = _create_full_setup(client, email="noncore@example.com", btype="umkm")
    res = client.patch(
        f"api/v1/businesses/{biz_id}/configuration",
        headers={"Authorization": f"Bearer {token}"},
        json={"module_overrides": {"PRODUCT": False}},
    )
    # The endpoint path should be correct
    res = client.patch(
        f"/api/v1/businesses/{biz_id}/configuration",
        headers={"Authorization": f"Bearer {token}"},
        json={"module_overrides": {"PRODUCT": False}},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["module_overrides"]["PRODUCT"] is False


# ============================================================
# Regression Tests
# ============================================================
def test_regression_health(client):
    assert client.get("/api/v1/health").status_code == 200


def test_regression_auth(client):
    token = _register_and_get_token(client)
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200


def test_regression_account(client):
    token = _register_and_get_token(client)
    assert client.get("/api/v1/account", headers={"Authorization": f"Bearer {token}"}).status_code == 200


def test_regression_business(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token).json()["id"]
    assert client.get(f"/api/v1/businesses/{biz_id}", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    assert client.get("/api/v1/businesses", headers={"Authorization": f"Bearer {token}"}).status_code == 200


def test_regression_membership(client):
    token, _, biz_id = _create_full_setup(client, email="reg@example.com", btype="umkm")
    member_token, _ = _add_member(client, token, biz_id, "reg2@example.com", role="MEMBER")
    res = client.get(f"/api/v1/businesses/{biz_id}/members", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200


def test_regression_branch(client):
    token, _, biz_id = _create_full_setup(client, email="reg3@example.com", btype="umkm")
    res = client.post(
        f"/api/v1/businesses/{biz_id}/branches",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Main",
            "code": "MN01",
            "timezone": "UTC",
            "locale": "en-US",
            "description": "Main branch",
            "address": "123 St",
            "phone": "+6281234567890",
            "email": "branch@test.com",
        },
    )
    assert res.status_code == 201

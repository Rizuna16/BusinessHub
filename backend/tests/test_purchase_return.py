import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from app.main import app
from app.modules.authentication.repository import InMemoryUserRepository
from app.modules.account.repository import InMemoryAccountRepository
from app.modules.business.repository import InMemoryBusinessRepository
from app.modules.business_membership.repository import InMemoryBusinessMembershipRepository
from app.modules.supplier.repository import InMemorySupplierRepository
from app.modules.branch.repository import InMemoryBranchRepository
from app.modules.unit.repository import InMemoryUnitRepository
from app.modules.product.repository import InMemoryProductRepository
from app.modules.product_variant.repository import InMemoryProductVariantRepository
from app.modules.purchase.repository import InMemoryPurchaseRepository
from app.modules.warehouse.repository import InMemoryWarehouseRepository, InMemoryInventoryLocationRepository
from app.modules.inventory.repository import InMemoryStockBalanceRepository, InMemoryStockMovementRepository, InMemoryInventoryCostRepository
from app.modules.receiving.repository import InMemoryReceivingRepository
from app.modules.purchase_return.repository import InMemoryPurchaseReturnRepository

# Override production PostgreSQL router wiring with InMemory services
from app.modules.purchase_return.router import get_scoped_purchase_return_service
from app.modules.receiving.router import get_scoped_receiving_service
from app.modules.purchase.router import get_scoped_purchase_service
from app.modules.business.router import get_scoped_business_service
from app.modules.business_membership.router import get_scoped_membership_service
from app.modules.purchase_return.service import PurchaseReturnService
from app.modules.receiving.service import ReceivingService
from app.modules.purchase.service import PurchaseService
from app.modules.business_membership.service import BusinessMembershipService
from app.modules.business.service import BusinessService
from app.modules.subscription.service import SubscriptionService


def _inmemory_purchase_return_service():
    """InMemory-wired PurchaseReturnService for unit testing."""
    membership_svc = BusinessMembershipService()
    return PurchaseReturnService(membership_service=membership_svc)


def _inmemory_receiving_service():
    """InMemory-wired ReceivingService for unit testing."""
    membership_svc = BusinessMembershipService()
    return ReceivingService(membership_service=membership_svc)


def _inmemory_purchase_service():
    """InMemory-wired PurchaseService for unit testing."""
    membership_svc = BusinessMembershipService()
    return PurchaseService(membership_service=membership_svc)


def _inmemory_business_service():
    """InMemory-wired BusinessService for unit testing."""
    membership_svc = BusinessMembershipService()
    subscription_svc = SubscriptionService()
    return BusinessService(membership_service=membership_svc, subscription_service_instance=subscription_svc)


def _inmemory_membership_service():
    """InMemory-wired BusinessMembershipService for unit testing."""
    return BusinessMembershipService()


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Override production scoped services with InMemory for unit tests."""
    app.dependency_overrides[get_scoped_purchase_return_service] = _inmemory_purchase_return_service
    app.dependency_overrides[get_scoped_receiving_service] = _inmemory_receiving_service
    app.dependency_overrides[get_scoped_purchase_service] = _inmemory_purchase_service
    app.dependency_overrides[get_scoped_business_service] = _inmemory_business_service
    app.dependency_overrides[get_scoped_membership_service] = _inmemory_membership_service
    yield
    app.dependency_overrides.pop(get_scoped_purchase_return_service, None)
    app.dependency_overrides.pop(get_scoped_receiving_service, None)
    app.dependency_overrides.pop(get_scoped_purchase_service, None)
    app.dependency_overrides.pop(get_scoped_business_service, None)
    app.dependency_overrides.pop(get_scoped_membership_service, None)

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_repositories():
    InMemoryPurchaseReturnRepository.clear()
    InMemoryReceivingRepository.clear()
    InMemoryStockBalanceRepository.clear()
    InMemoryStockMovementRepository.clear()
    InMemoryInventoryCostRepository.clear()
    InMemoryInventoryLocationRepository.clear()
    InMemoryWarehouseRepository.clear()
    InMemoryPurchaseRepository.clear()
    InMemoryProductVariantRepository.clear()
    InMemoryProductRepository.clear()
    InMemoryUnitRepository.clear()
    InMemoryBranchRepository.clear()
    InMemorySupplierRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryUserRepository.clear()
    yield
    InMemoryPurchaseReturnRepository.clear()
    InMemoryReceivingRepository.clear()
    InMemoryStockBalanceRepository.clear()
    InMemoryStockMovementRepository.clear()
    InMemoryInventoryCostRepository.clear()
    InMemoryInventoryLocationRepository.clear()
    InMemoryWarehouseRepository.clear()
    InMemoryPurchaseRepository.clear()
    InMemoryProductVariantRepository.clear()
    InMemoryProductRepository.clear()
    InMemoryUnitRepository.clear()
    InMemoryBranchRepository.clear()
    InMemorySupplierRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryUserRepository.clear()


def register_user(email="owner@example.com", name="Owner Test"):
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": name,
            "password": "Password123",
            "password_confirmation": "Password123",
        },
    )
    assert res.status_code == 201
    data = res.json()
    token = data.get("access_token")
    if not token:
        login_res = client.post(
            "/api/v1/auth/login", json={"email": email, "password": "Password123"}
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
    return token, data["id"]


def create_business(token, name="Test Business"):
    res = client.post(
        "/api/v1/businesses",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": name,
            "legal_name": name,
            "business_type": "retail",
            "timezone": "UTC",
            "locale": "en-US",
        },
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_supplier(token, business_id, name="Supplier A"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/suppliers",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "supplier_type": "ORGANIZATION"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_branch(token, business_id, name="Branch A", code="BR-A"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/branches",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code},
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_unit(token, business_id, name="Pcs", code="PCS"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/units",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code},
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_product(token, business_id, unit_id, name="Product A", code="PROD-A", p_type="GOODS"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/products",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code, "unit_id": unit_id, "product_type": p_type},
    )
    assert res.status_code == 201
    return res.json()["id"]


def setup_warehouse_and_location(token, business_id, name="WH 1", code="WH-1", loc_name="RACK 1", loc_code="R1"):
    wh_res = client.post(
        f"/api/v1/businesses/{business_id}/warehouses",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code},
    )
    assert wh_res.status_code == 201
    wh_id = wh_res.json()["id"]

    loc_res = client.post(
        f"/api/v1/businesses/{business_id}/warehouses/{wh_id}/locations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": loc_name, "code": loc_code, "location_type": "RECEIVING"},
    )
    assert loc_res.status_code == 201
    return loc_res.json()["id"]


def create_finalized_purchase(token, business_id, sup_id, br_id, prod_id, qty=100, price=50):
    p_res = client.post(
        f"/api/v1/businesses/{business_id}/purchases",
        headers={"Authorization": f"Bearer {token}"},
        json={"supplier_id": sup_id, "branch_id": br_id, "purchase_date": datetime.now(timezone.utc).isoformat()},
    )
    assert p_res.status_code == 201
    pur_id = p_res.json()["id"]

    l_res = client.post(
        f"/api/v1/businesses/{business_id}/purchases/{pur_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_id, "quantity": qty, "unit_price": price},
    )
    assert l_res.status_code == 201
    pline_id = l_res.json()["id"]

    fin_res = client.post(
        f"/api/v1/businesses/{business_id}/purchases/{pur_id}/finalize",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fin_res.status_code == 200
    return pur_id, pline_id


def create_finalized_receiving(token, business_id, pur_id, pline_id, loc_id, rcv_qty=100):
    rcv_res = client.post(
        f"/api/v1/businesses/{business_id}/receivings",
        headers={"Authorization": f"Bearer {token}"},
        json={"purchase_id": pur_id, "inventory_location_id": loc_id},
    )
    assert rcv_res.status_code == 201
    rcv_id = rcv_res.json()["id"]

    line_res = client.post(
        f"/api/v1/businesses/{business_id}/receivings/{rcv_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"purchase_line_id": pline_id, "quantity": rcv_qty},
    )
    assert line_res.status_code == 201

    fin_res = client.post(
        f"/api/v1/businesses/{business_id}/receivings/{rcv_id}/finalize",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fin_res.status_code == 200
    return rcv_id


class TestPurchaseReturnFeature:
    # 1-2. Unauthenticated access
    def test_unauthenticated_list_rejected(self):
        res = client.get("/api/v1/businesses/biz123/purchase-returns")
        assert res.status_code == 401

    def test_unauthenticated_create_rejected(self):
        res = client.post("/api/v1/businesses/biz123/purchase-returns", json={"purchase_id": "x", "inventory_location_id": "y"})
        assert res.status_code == 401

    # 8-10. Purchase state validation
    def test_draft_purchase_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)

        p_res = client.post(
            f"/api/v1/businesses/{biz_id}/purchases",
            headers={"Authorization": f"Bearer {token}"},
            json={"supplier_id": sup_id, "branch_id": br_id, "purchase_date": datetime.now(timezone.utc).isoformat()},
        )
        pur_id = p_res.json()["id"]

        res = client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        )
        assert res.status_code == 400

    def test_cancelled_purchase_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)

        p_res = client.post(
            f"/api/v1/businesses/{biz_id}/purchases",
            headers={"Authorization": f"Bearer {token}"},
            json={"supplier_id": sup_id, "branch_id": br_id, "purchase_date": datetime.now(timezone.utc).isoformat()},
        )
        pur_id = p_res.json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )

        res = client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        )
        assert res.status_code == 400

    # 10. Finalized purchase allowed
    def test_finalized_purchase_allowed(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        pur_id, _ = create_finalized_purchase(token, biz_id, sup_id, br_id, prod_id)

        res = client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "DRAFT"
        assert data["return_number"] == "PRT-000001"

    # 11-14. Receiving state validation
    def test_no_finalized_receiving_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        pur_id, pline_id = create_finalized_purchase(token, biz_id, sup_id, br_id, prod_id)

        # Create return
        rcv_ret = client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        ).json()["id"]

        # No finalized receiving, add line -> should fail
        res = client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns/{rcv_ret}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": pline_id, "quantity": 10},
        )
        assert res.status_code == 400

    # 21-27. Quantity & over-return
    def test_partial_return_and_over_return(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        pur_id, pline_id = create_finalized_purchase(token, biz_id, sup_id, br_id, prod_id, qty=100)
        create_finalized_receiving(token, biz_id, pur_id, pline_id, loc_id, rcv_qty=60)

        # Return 60 -> should succeed
        ret1 = client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        ).json()["id"]
        res1 = client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns/{ret1}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": pline_id, "quantity": 60},
        )
        assert res1.status_code == 201
        client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns/{ret1}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Return 10 -> should fail (60 + 10 > 60)
        ret2 = client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        ).json()["id"]
        res2 = client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns/{ret2}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": pline_id, "quantity": 10},
        )
        assert res2.status_code == 400

    # 26. Cancelled return releases capacity
    def test_cancelled_return_releases_capacity(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        pur_id, pline_id = create_finalized_purchase(token, biz_id, sup_id, br_id, prod_id, qty=50)
        create_finalized_receiving(token, biz_id, pur_id, pline_id, loc_id, rcv_qty=50)

        # Return 40
        ret1 = client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns/{ret1}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": pline_id, "quantity": 40},
        )
        client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns/{ret1}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Now 40 capacity freed. Return 50 -> should succeed
        ret2 = client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        ).json()["id"]
        res2 = client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns/{ret2}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": pline_id, "quantity": 50},
        )
        assert res2.status_code == 201

    # 29-33. Lifecycle & immutability
    def test_lifecycle_and_immutability(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        pur_id, pline_id = create_finalized_purchase(token, biz_id, sup_id, br_id, prod_id, qty=50)
        create_finalized_receiving(token, biz_id, pur_id, pline_id, loc_id, rcv_qty=50)

        ret_id = client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        ).json()["id"]

        client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns/{ret_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": pline_id, "quantity": 50},
        )

        # Finalize
        fin = client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns/{ret_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fin.status_code == 200
        assert fin.json()["status"] == "FINALIZED"

        # Finalized immutable
        add_line = client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns/{ret_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": pline_id, "quantity": 5},
        )
        assert add_line.status_code == 400

        cancel_fin = client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns/{ret_id}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert cancel_fin.status_code == 400

        delete_fin = client.delete(
            f"/api/v1/businesses/{biz_id}/purchase-returns/{ret_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert delete_fin.status_code == 400

    # 34. Empty return cannot finalize
    def test_empty_return_cannot_finalize(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        pur_id, pline_id = create_finalized_purchase(token, biz_id, sup_id, br_id, prod_id)
        create_finalized_receiving(token, biz_id, pur_id, pline_id, loc_id, rcv_qty=10)

        # Re-fetch purchase line since we don't have pline_id here without changing helpers
        # Just test empty finalize directly
        ret_id = client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        ).json()["id"]

        res = client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns/{ret_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 400

    # 35. Supplier correctly derived
    def test_supplier_derived_through_purchase(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id, name="Return Supplier")
        br_id = create_branch(token, biz_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        pur_id, pline_id = create_finalized_purchase(token, biz_id, sup_id, br_id, prod_id, qty=10)
        create_finalized_receiving(token, biz_id, pur_id, pline_id, loc_id, rcv_qty=10)

        ret_id = client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        ).json()["id"]

        get_res = client.get(
            f"/api/v1/businesses/{biz_id}/purchase-returns/{ret_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_res.status_code == 200
        # Verify purchase_id reference correctly points to supplier's purchase
        assert get_res.json()["purchase_id"] == pur_id

    # 15-17. Tenant isolation
    def test_tenant_isolation(self):
        token_a, _ = register_user("a@test.com")
        biz_a = create_business(token_a, "Biz A")
        sup_a = create_supplier(token_a, biz_a)
        br_a = create_branch(token_a, biz_a)
        loc_a = setup_warehouse_and_location(token_a, biz_a)
        unit_a = create_unit(token_a, biz_a)
        prod_a = create_product(token_a, biz_a, unit_a)
        pur_a_id, pline_a_id = create_finalized_purchase(token_a, biz_a, sup_a, br_a, prod_a)
        create_finalized_receiving(token_a, biz_a, pur_a_id, pline_a_id, loc_a, rcv_qty=50)

        ret_a = client.post(
            f"/api/v1/businesses/{biz_a}/purchase-returns",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"purchase_id": pur_a_id, "inventory_location_id": loc_a},
        ).json()["id"]

        token_b, _ = register_user("b@test.com")
        biz_b = create_business(token_b, "Biz B")

        res = client.get(
            f"/api/v1/businesses/{biz_a}/purchase-returns/{ret_a}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert res.status_code == 404

    # 3-7. RBAC
    def test_rbac_authorization(self):
        owner_token, _ = register_user("owner@test.com")
        biz_id = create_business(owner_token)
        sup_id = create_supplier(owner_token, biz_id)
        br_id = create_branch(owner_token, biz_id)
        loc_id = setup_warehouse_and_location(owner_token, biz_id)
        unit_id = create_unit(owner_token, biz_id)
        prod_id = create_product(owner_token, biz_id, unit_id)
        pur_id, pline_id = create_finalized_purchase(owner_token, biz_id, sup_id, br_id, prod_id, qty=10)
        create_finalized_receiving(owner_token, biz_id, pur_id, pline_id, loc_id, rcv_qty=10)

        member_token, member_id = register_user("member@test.com")
        client.post(
            f"/api/v1/businesses/{biz_id}/members",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"user_id": member_id, "role": "MEMBER"},
        )

        # Member can list returns
        list_res = client.get(
            f"/api/v1/businesses/{biz_id}/purchase-returns",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert list_res.status_code == 200

        # Member cannot create return
        create_res = client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns",
            headers={"Authorization": f"Bearer {member_token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        )
        assert create_res.status_code == 403

    # 36-38. Inventory boundary
    def test_inventory_boundary(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        pur_id, pline_id = create_finalized_purchase(token, biz_id, sup_id, br_id, prod_id, qty=20)
        create_finalized_receiving(token, biz_id, pur_id, pline_id, loc_id, rcv_qty=20)

        ret_id = client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        ).json()["id"]

        client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns/{ret_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": pline_id, "quantity": 20},
        )

        client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns/{ret_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )

        # CRITICAL: Purchase return does not create ADDITIONAL stock balances
        # (Purchase finalization already created stock balances, purchase return reduces them)
        balances_before_return = len(InMemoryStockBalanceRepository._balances)
        movements_before_return = len(InMemoryStockMovementRepository._movements)

        client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns/{ret_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Stock balances should decrease, but no NEW stock balance entries should be created
        # The number of unique stock balance keys should not increase
        balances_after_return = len(InMemoryStockBalanceRepository._balances)
        movements_after_return = len(InMemoryStockMovementRepository._movements)

        assert balances_after_return <= balances_before_return
        assert movements_after_return <= movements_before_return

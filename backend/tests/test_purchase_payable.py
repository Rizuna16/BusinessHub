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
from app.modules.receiving.repository import InMemoryReceivingRepository
from app.modules.purchase_return.repository import InMemoryPurchaseReturnRepository

# Override production PostgreSQL router wiring with InMemory services
from app.modules.purchase.router import get_scoped_purchase_service
from app.modules.receiving.router import get_scoped_receiving_service
from app.modules.purchase_return.router import get_scoped_purchase_return_service
from app.modules.business.router import get_scoped_business_service
from app.modules.business_membership.router import get_scoped_membership_service
from app.modules.purchase.service import PurchaseService
from app.modules.receiving.service import ReceivingService
from app.modules.purchase_return.service import PurchaseReturnService
from app.modules.business_membership.service import BusinessMembershipService
from app.modules.business.service import BusinessService
from app.modules.subscription.service import SubscriptionService


def _inmemory_purchase_service():
    return PurchaseService(membership_service=BusinessMembershipService())


def _inmemory_receiving_service():
    return ReceivingService(membership_service=BusinessMembershipService())


def _inmemory_purchase_return_service():
    return PurchaseReturnService(membership_service=BusinessMembershipService())


def _inmemory_business_service():
    membership_svc = BusinessMembershipService()
    subscription_svc = SubscriptionService()
    return BusinessService(membership_service=membership_svc, subscription_service_instance=subscription_svc)


def _inmemory_membership_service():
    return BusinessMembershipService()


@pytest.fixture(autouse=True)
def setup_test_environment():
    app.dependency_overrides[get_scoped_purchase_service] = _inmemory_purchase_service
    app.dependency_overrides[get_scoped_receiving_service] = _inmemory_receiving_service
    app.dependency_overrides[get_scoped_purchase_return_service] = _inmemory_purchase_return_service
    app.dependency_overrides[get_scoped_business_service] = _inmemory_business_service
    app.dependency_overrides[get_scoped_membership_service] = _inmemory_membership_service
    yield
    app.dependency_overrides.pop(get_scoped_purchase_service, None)
    app.dependency_overrides.pop(get_scoped_receiving_service, None)
    app.dependency_overrides.pop(get_scoped_purchase_return_service, None)
    app.dependency_overrides.pop(get_scoped_business_service, None)
    app.dependency_overrides.pop(get_scoped_membership_service, None)

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_repositories():
    InMemoryPurchasePayableRepositoryFixtureFix = None
    InMemoryPurchaseReturnRepository.clear()
    InMemoryReceivingRepository.clear()
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


def create_product(token, business_id, unit_id, name="Product A", code="PROD-A"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/products",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code, "unit_id": unit_id, "product_type": "GOODS"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_warehouse(token, business_id, name="Warehouse A"):
    import uuid
    code = f"WH-{uuid.uuid4().hex[:8]}"
    res = client.post(
        f"/api/v1/businesses/{business_id}/warehouses",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code},
    )
    assert res.status_code == 201
    wh_id = res.json()["id"]
    loc_res = client.post(
        f"/api/v1/businesses/{business_id}/warehouses/{wh_id}/locations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": f"Loc {name}", "code": f"LOC-{code}"},
    )
    assert loc_res.status_code == 201
    return wh_id, loc_res.json()["id"]


def setup_finalized_purchase_with_lines(token, biz_id, sup_id, br_id, prod_id, lines=None):
    wh_id, loc_id = create_warehouse(token, biz_id)
    p_res = client.post(
        f"/api/v1/businesses/{biz_id}/purchases",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "supplier_id": sup_id,
            "branch_id": br_id,
            "purchase_date": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert p_res.status_code == 201
    pur_id = p_res.json()["id"]

    if lines is None:
        lines = [{"product_id": prod_id, "quantity": 10, "unit_price": 1000}]

    for l in lines:
        res_l = client.post(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json=l,
        )
        assert res_l.status_code == 201

    fin_res = client.post(
        f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/finalize",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fin_res.status_code == 200
    return pur_id


class TestPurchasePayableCoreFunctionality:
    def test_list_empty_payables(self):
        token, _ = register_user()
        biz_id = create_business(token)
        res = client.get(
            f"/api/v1/businesses/{biz_id}/purchases/payables",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert res.json()["items"] == []
        assert res.json()["total"] == 0

    def test_payable_created_only_for_finalized_purchase(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        wh_id, loc_id = create_warehouse(token, biz_id)

        # Create but DRAFT purchase
        p_res = client.post(
            f"/api/v1/businesses/{biz_id}/purchases",
            headers={"Authorization": f"Bearer {token}"},
            json={"supplier_id": sup_id, "branch_id": br_id, "purchase_date": datetime.now(timezone.utc).isoformat()},
        )
        assert p_res.status_code == 201

        res = client.get(
            f"/api/v1/businesses/{biz_id}/purchases/payables",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert res.json()["total"] == 0

        # Now add line and finalize
        pur_id = p_res.json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": 1, "unit_price": 100},
        )
        client.post(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )

        res = client.get(
            f"/api/v1/businesses/{biz_id}/purchases/payables",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert res.json()["total"] == 1
        assert res.json()["items"][0]["purchase_id"] == pur_id

    def test_payable_gross_payable_matches_purchase_total(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)

        pur_id = setup_finalized_purchase_with_lines(
            token, biz_id, sup_id, br_id, prod_id,
            lines=[{"product_id": prod_id, "quantity": 10, "unit_price": 1000, "tax_amount": 500}]
        )

        detail = client.get(
            f"/api/v1/businesses/{biz_id}/purchases/payables/{pur_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert detail.status_code == 200
        data = detail.json()
        assert Decimal(str(data["gross_payable"])) == Decimal("10500")
        assert Decimal(str(data["return_adjustment"])) == Decimal("0")
        assert Decimal(str(data["net_payable"])) == Decimal("10500")
        assert data["currency"] == "IDR"

    def test_payable_status_unpaid(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)

        pur_id = setup_finalized_purchase_with_lines(token, biz_id, sup_id, br_id, prod_id)

        detail = client.get(
            f"/api/v1/businesses/{biz_id}/purchases/payables/{pur_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert detail.status_code == 200
        assert detail.json()["status"] == "UNPAID"
        assert Decimal(str(detail.json()["paid_amount"])) == Decimal("0")
        assert Decimal(str(detail.json()["outstanding_amount"])) == Decimal("10000")

    def test_payable_supplier_info_populated(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id, name="Maju Jaya")
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)

        pur_id = setup_finalized_purchase_with_lines(token, biz_id, sup_id, br_id, prod_id)

        detail = client.get(
            f"/api/v1/businesses/{biz_id}/purchases/payables/{pur_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert detail.status_code == 200
        assert detail.json()["supplier_name"] == "Maju Jaya"
        assert detail.json()["supplier_id"] == sup_id


class TestPurchasePayableReturnAdjustment:
    def test_return_adjustment_reduces_payable(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        wh_id, loc_id = create_warehouse(token, biz_id)

        # Finalized purchase 10000
        pur_id = setup_finalized_purchase_with_lines(token, biz_id, sup_id, br_id, prod_id)

        # Create receiving to allow return
        rcv_res = client.post(
            f"/api/v1/businesses/{biz_id}/receivings",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        )
        assert rcv_res.status_code == 201
        rcv_id = rcv_res.json()["id"]

        p_line = client.get(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()["lines"][0]["id"]

        client.post(
            f"/api/v1/businesses/{biz_id}/receivings/{rcv_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": p_line, "quantity": 5},
        )
        client.post(
            f"/api/v1/businesses/{biz_id}/receivings/{rcv_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Create and finalize purchase return
        pr_res = client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        )
        assert pr_res.status_code == 201
        pr_id = pr_res.json()["id"]

        client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns/{pr_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": p_line, "quantity": 2, "unit_price": 1000},
        )
        client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns/{pr_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )

        detail = client.get(
            f"/api/v1/businesses/{biz_id}/purchases/payables/{pur_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert detail.status_code == 200
        data = detail.json()
        assert Decimal(str(data["gross_payable"])) == Decimal("10000")
        assert Decimal(str(data["return_adjustment"])) == Decimal("2000")
        assert Decimal(str(data["net_payable"])) == Decimal("8000")
        assert Decimal(str(data["outstanding_amount"])) == Decimal("8000")
        assert data["return_count"] == 1

    def test_cancelled_return_does_not_reduce_payable(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        wh_id, loc_id = create_warehouse(token, biz_id)

        pur_id = setup_finalized_purchase_with_lines(token, biz_id, sup_id, br_id, prod_id)

        # Receive items first
        rcv_res = client.post(
            f"/api/v1/businesses/{biz_id}/receivings",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        )
        rcv_id = rcv_res.json()["id"]
        p_line = client.get(f"/api/v1/businesses/{biz_id}/purchases/{pur_id}", headers={"Authorization": f"Bearer {token}"}).json()["lines"][0]["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/receivings/{rcv_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": p_line, "quantity": 5},
        )
        client.post(f"/api/v1/businesses/{biz_id}/receivings/{rcv_id}/finalize", headers={"Authorization": f"Bearer {token}"})

        # Create and finalize return
        pr_res = client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        )
        pr_id = pr_res.json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns/{pr_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": p_line, "quantity": 2, "unit_price": 1000},
        )
        client.post(f"/api/v1/businesses/{biz_id}/purchase-returns/{pr_id}/finalize", headers={"Authorization": f"Bearer {token}"})

        # Check payable has return_adjustment
        detail = client.get(
            f"/api/v1/businesses/{biz_id}/purchases/payables/{pur_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert Decimal(str(detail.json()["return_adjustment"])) == Decimal("2000")
        assert Decimal(str(detail.json()["net_payable"])) == Decimal("8000")

        # Now create a draft return, verify it doesn't increase return_adjustment
        pr2_res = client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        )
        pr2_id = pr2_res.json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns/{pr2_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": p_line, "quantity": 1, "unit_price": 1000},
        )

        detail2 = client.get(
            f"/api/v1/businesses/{biz_id}/purchases/payables/{pur_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert Decimal(str(detail2.json()["return_adjustment"])) == Decimal("2000")
        assert detail2.json()["return_count"] == 1

        # Cancel the draft return
        client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns/{pr2_id}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Cancelled return shouldn't affect payable
        detail3 = client.get(
            f"/api/v1/businesses/{biz_id}/purchases/payables/{pur_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert Decimal(str(detail3.json()["return_adjustment"])) == Decimal("2000")
        assert Decimal(str(detail3.json()["net_payable"])) == Decimal("8000")


class TestPurchasePayableTenantIsolation:
    def test_tenant_a_cannot_see_tenant_b_payables(self):
        token_a, _ = register_user("a@test.com")
        biz_a = create_business(token_a, "Biz A")
        sup_a = create_supplier(token_a, biz_a, name="Sup A")
        br_a = create_branch(token_a, biz_a)
        unit_a = create_unit(token_a, biz_a)
        prod_a = create_product(token_a, biz_a, unit_a)

        token_b, _ = register_user("b@test.com")
        biz_b = create_business(token_b, "Biz B")
        sup_b = create_supplier(token_b, biz_b, name="Sup B")
        br_b = create_branch(token_b, biz_b)
        unit_b = create_unit(token_b, biz_b)
        prod_b = create_product(token_b, biz_b, unit_b)

        pur_a = setup_finalized_purchase_with_lines(token_a, biz_a, sup_a, br_a, prod_a)
        pur_b = setup_finalized_purchase_with_lines(token_b, biz_b, sup_b, br_b, prod_b)

        # Tenant B list payables should only see Biz B's
        res_b_list = client.get(
            f"/api/v1/businesses/{biz_b}/purchases/payables",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert res_b_list.status_code == 200
        assert len(res_b_list.json()["items"]) == 1
        assert res_b_list.json()["items"][0]["purchase_id"] == pur_b

        # Tenant B trying to access Biz A payable detail
        res_cross = client.get(
            f"/api/v1/businesses/{biz_a}/purchases/payables/{pur_a}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert res_cross.status_code == 404

    def test_non_member_cannot_access_payables(self):
        token_owner, _ = register_user("owner@test.com")
        biz_id = create_business(token_owner)
        sup_id = create_supplier(token_owner, biz_id)
        br_id = create_branch(token_owner, biz_id)
        unit_id = create_unit(token_owner, biz_id)
        prod_id = create_product(token_owner, biz_id, unit_id)
        setup_finalized_purchase_with_lines(token_owner, biz_id, sup_id, br_id, prod_id)

        token_outsider, _ = register_user("outsider@test.com")

        res = client.get(
            f"/api/v1/businesses/{biz_id}/purchases/payables",
            headers={"Authorization": f"Bearer {token_outsider}"},
        )
        assert res.status_code == 404 or res.status_code == 403


class TestPurchasePayableStatusBehavior:
    def test_status_unpaid_default(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)

        pur_id = setup_finalized_purchase_with_lines(token, biz_id, sup_id, br_id, prod_id)

        detail = client.get(
            f"/api/v1/businesses/{biz_id}/purchases/payables/{pur_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert detail.json()["status"] == "UNPAID"
        assert Decimal(str(detail.json()["paid_amount"])) == Decimal("0")
        assert Decimal(str(detail.json()["outstanding_amount"])) == Decimal("10000")

    def test_fully_returned_purchase_becomes_paid(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        wh_id, loc_id = create_warehouse(token, biz_id)

        pur_id = setup_finalized_purchase_with_lines(token, biz_id, sup_id, br_id, prod_id)

        rcv_res = client.post(
            f"/api/v1/businesses/{biz_id}/receivings",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        )
        rcv_id = rcv_res.json()["id"]
        p_line = client.get(f"/api/v1/businesses/{biz_id}/purchases/{pur_id}", headers={"Authorization": f"Bearer {token}"}).json()["lines"][0]["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/receivings/{rcv_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": p_line, "quantity": 10},
        )
        client.post(f"/api/v1/businesses/{biz_id}/receivings/{rcv_id}/finalize", headers={"Authorization": f"Bearer {token}"})

        pr_res = client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        )
        pr_id = pr_res.json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns/{pr_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": p_line, "quantity": 10, "unit_price": 1000},
        )
        client.post(f"/api/v1/businesses/{biz_id}/purchase-returns/{pr_id}/finalize", headers={"Authorization": f"Bearer {token}"})

        detail = client.get(
            f"/api/v1/businesses/{biz_id}/purchases/payables/{pur_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert detail.json()["status"] == "PAID"
        assert Decimal(str(detail.json()["net_payable"])) == Decimal("0")
        assert Decimal(str(detail.json()["outstanding_amount"])) == Decimal("0")


class TestPurchasePayableSummary:
    def test_summary_zero_when_no_purchases(self):
        token, _ = register_user()
        biz_id = create_business(token)

        res = client.get(
            f"/api/v1/businesses/{biz_id}/purchases/payables/summary",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert Decimal(str(data["total_gross_payable"])) == Decimal("0")
        assert Decimal(str(data["total_net_payable"])) == Decimal("0")
        assert data["unpaid_count"] == 0
        assert data["supplier_count"] == 0

    def test_summary_matches_individual_payables(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)

        pur_id = setup_finalized_purchase_with_lines(token, biz_id, sup_id, br_id, prod_id)

        summary_res = client.get(
            f"/api/v1/businesses/{biz_id}/purchases/payables/summary",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert summary_res.status_code == 200
        data = summary_res.json()
        assert Decimal(str(data["total_gross_payable"])) == Decimal("10000")
        assert data["unpaid_count"] == 1
        assert data["supplier_count"] == 1


class TestPurchasePayableCurrency:
    def test_payable_currency_is_idr(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)

        pur_id = setup_finalized_purchase_with_lines(token, biz_id, sup_id, br_id, prod_id)

        detail = client.get(
            f"/api/v1/businesses/{biz_id}/purchases/payables/{pur_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert detail.json()["currency"] == "IDR"

    def test_filter_by_currency_idr(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)

        pur_id = setup_finalized_purchase_with_lines(token, biz_id, sup_id, br_id, prod_id)

        res = client.get(
            f"/api/v1/businesses/{biz_id}/purchases/payables?currency=IDR",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert len(res.json()["items"]) == 1

    def test_filter_by_nonexistent_currency_returns_empty(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)

        pur_id = setup_finalized_purchase_with_lines(token, biz_id, sup_id, br_id, prod_id)

        res = client.get(
            f"/api/v1/businesses/{biz_id}/purchases/payables?currency=USD",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert len(res.json()["items"]) == 0


class TestPurchasePayableFinancialInvariants:
    def test_no_negative_values(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        wh_id, loc_id = create_warehouse(token, biz_id)

        pur_id = setup_finalized_purchase_with_lines(token, biz_id, sup_id, br_id, prod_id)

        detail = client.get(
            f"/api/v1/businesses/{biz_id}/purchases/payables/{pur_id}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        assert Decimal(str(detail["gross_payable"])) >= Decimal("0")
        assert Decimal(str(detail["return_adjustment"])) >= Decimal("0")
        assert Decimal(str(detail["net_payable"])) >= Decimal("0")
        assert Decimal(str(detail["paid_amount"])) >= Decimal("0")
        assert Decimal(str(detail["outstanding_amount"])) >= Decimal("0")

    def test_outstanding_cannot_be_negative_even_with_many_returns(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        wh_id, loc_id = create_warehouse(token, biz_id)

        pur_id = setup_finalized_purchase_with_lines(
            token, biz_id, sup_id, br_id, prod_id,
            lines=[{"product_id": prod_id, "quantity": 10, "unit_price": 1000}]
        )

        # Receive 10 items
        rcv_res = client.post(
            f"/api/v1/businesses/{biz_id}/receivings",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        )
        rcv_id = rcv_res.json()["id"]
        p_line = client.get(f"/api/v1/businesses/{biz_id}/purchases/{pur_id}", headers={"Authorization": f"Bearer {token}"}).json()["lines"][0]["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/receivings/{rcv_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": p_line, "quantity": 10},
        )
        client.post(f"/api/v1/businesses/{biz_id}/receivings/{rcv_id}/finalize", headers={"Authorization": f"Bearer {token}"})

        # Return all 10
        pr_res = client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        )
        pr_id = pr_res.json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns/{pr_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": p_line, "quantity": 10, "unit_price": 1000},
        )
        client.post(f"/api/v1/businesses/{biz_id}/purchase-returns/{pr_id}/finalize", headers={"Authorization": f"Bearer {token}"})

        detail = client.get(
            f"/api/v1/businesses/{biz_id}/purchases/payables/{pur_id}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        assert Decimal(str(detail["outstanding_amount"])) == Decimal("0")
        assert detail["status"] == "PAID"
        assert Decimal(str(detail["net_payable"])) >= Decimal("0")

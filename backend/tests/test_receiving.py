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

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_repositories():
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


def setup_warehouse_and_location(token, business_id, name="WH 1", code="WH-1", loc_name="RACK 1", loc_code="R1", status="ACTIVE"):
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
    loc_id = loc_res.json()["id"]

    if status == "ARCHIVED":
        client.delete(
            f"/api/v1/businesses/{business_id}/warehouses/{wh_id}/locations/{loc_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    return loc_id


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


class TestReceivingFeature:
    # 1. Create valid Receiving against FINALIZED Purchase
    def test_create_receiving_valid(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        pur_id, _ = create_finalized_purchase(token, biz_id, sup_id, br_id, prod_id)

        res = client.post(
            f"/api/v1/businesses/{biz_id}/receivings",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id, "notes": "Test receiving"},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "DRAFT"
        assert data["receiving_number"] == "RCV-000001"
        assert data["purchase_id"] == pur_id
        assert data["inventory_location_id"] == loc_id

    # 2. Reject Receiving against DRAFT Purchase
    def test_reject_receiving_draft_purchase(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        loc_id = setup_warehouse_and_location(token, biz_id)

        # DRAFT purchase
        p_res = client.post(
            f"/api/v1/businesses/{biz_id}/purchases",
            headers={"Authorization": f"Bearer {token}"},
            json={"supplier_id": sup_id, "branch_id": br_id, "purchase_date": datetime.now(timezone.utc).isoformat()},
        )
        pur_id = p_res.json()["id"]

        res = client.post(
            f"/api/v1/businesses/{biz_id}/receivings",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        )
        assert res.status_code == 400

    # 3. Reject Receiving against CANCELLED Purchase
    def test_reject_receiving_cancelled_purchase(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        loc_id = setup_warehouse_and_location(token, biz_id)

        # DRAFT -> CANCELLED
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
            f"/api/v1/businesses/{biz_id}/receivings",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        )
        assert res.status_code == 400

    # 4. Reject deleted Purchase
    def test_reject_deleted_purchase(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        loc_id = setup_warehouse_and_location(token, biz_id)

        p_res = client.post(
            f"/api/v1/businesses/{biz_id}/purchases",
            headers={"Authorization": f"Bearer {token}"},
            json={"supplier_id": sup_id, "branch_id": br_id, "purchase_date": datetime.now(timezone.utc).isoformat()},
        )
        pur_id = p_res.json()["id"]
        client.delete(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        res = client.post(
            f"/api/v1/businesses/{biz_id}/receivings",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        )
        assert res.status_code == 404

    # 5. Reject missing Purchase
    def test_reject_missing_purchase(self):
        token, _ = register_user()
        biz_id = create_business(token)
        loc_id = setup_warehouse_and_location(token, biz_id)

        res = client.post(
            f"/api/v1/businesses/{biz_id}/receivings",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": "nonexistent-id", "inventory_location_id": loc_id},
        )
        assert res.status_code == 404

    # 6. Reject missing InventoryLocation
    def test_reject_missing_location(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        pur_id, _ = create_finalized_purchase(token, biz_id, sup_id, br_id, prod_id)

        res = client.post(
            f"/api/v1/businesses/{biz_id}/receivings",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": "nonexistent-loc"},
        )
        assert res.status_code == 400

    # 7. Reject inactive (archived) InventoryLocation
    def test_reject_inactive_location(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        archived_loc_id = setup_warehouse_and_location(token, biz_id, status="ARCHIVED")
        pur_id, _ = create_finalized_purchase(token, biz_id, sup_id, br_id, prod_id)

        res = client.post(
            f"/api/v1/businesses/{biz_id}/receivings",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": archived_loc_id},
        )
        assert res.status_code == 400

    # 8. Reject cross-business InventoryLocation
    def test_reject_cross_business_location(self):
        token_a, _ = register_user("a@test.com")
        biz_a = create_business(token_a, "Biz A")
        sup_a = create_supplier(token_a, biz_a)
        br_a = create_branch(token_a, biz_a)
        unit_a = create_unit(token_a, biz_a)
        prod_a = create_product(token_a, biz_a, unit_a)
        pur_a_id, _ = create_finalized_purchase(token_a, biz_a, sup_a, br_a, prod_a)

        token_b, _ = register_user("b@test.com")
        biz_b = create_business(token_b, "Biz B")
        loc_b_id = setup_warehouse_and_location(token_b, biz_b)

        res = client.post(
            f"/api/v1/businesses/{biz_a}/receivings",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"purchase_id": pur_a_id, "inventory_location_id": loc_b_id},
        )
        assert res.status_code == 400

    # 9. Add valid ReceivingLine
    def test_add_valid_receiving_line(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        pur_id, pline_id = create_finalized_purchase(token, biz_id, sup_id, br_id, prod_id, qty=100)

        rcv_res = client.post(
            f"/api/v1/businesses/{biz_id}/receivings",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        )
        rcv_id = rcv_res.json()["id"]

        line_res = client.post(
            f"/api/v1/businesses/{biz_id}/receivings/{rcv_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": pline_id, "quantity": 60},
        )
        assert line_res.status_code == 201
        line_data = line_res.json()
        assert line_data["purchase_line_id"] == pline_id
        assert line_data["product_id"] == prod_id
        assert Decimal(str(line_data["quantity"])) == Decimal("60")

    # 10. Reject invalid PurchaseLine
    def test_reject_invalid_purchase_line(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        pur_id, _ = create_finalized_purchase(token, biz_id, sup_id, br_id, prod_id)

        rcv_res = client.post(
            f"/api/v1/businesses/{biz_id}/receivings",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        )
        rcv_id = rcv_res.json()["id"]

        res = client.post(
            f"/api/v1/businesses/{biz_id}/receivings/{rcv_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": "nonexistent-pline", "quantity": 10},
        )
        assert res.status_code == 400

    # 11. Reject PurchaseLine belonging to another Purchase
    def test_reject_purchase_line_other_purchase(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token, biz_id)

        pur1_id, pline1_id = create_finalized_purchase(token, biz_id, sup_id, br_id, prod_id)
        pur2_id, pline2_id = create_finalized_purchase(token, biz_id, sup_id, br_id, prod_id)

        rcv_res = client.post(
            f"/api/v1/businesses/{biz_id}/receivings",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur1_id, "inventory_location_id": loc_id},
        )
        rcv_id = rcv_res.json()["id"]

        # Attempt to add pline2 (which belongs to pur2) to rcv of pur1
        res = client.post(
            f"/api/v1/businesses/{biz_id}/receivings/{rcv_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": pline2_id, "quantity": 10},
        )
        assert res.status_code == 400

    # 12 & 13. Reject zero / negative quantity
    def test_reject_zero_and_negative_quantity(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        pur_id, pline_id = create_finalized_purchase(token, biz_id, sup_id, br_id, prod_id)

        rcv_res = client.post(
            f"/api/v1/businesses/{biz_id}/receivings",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        )
        rcv_id = rcv_res.json()["id"]

        res0 = client.post(
            f"/api/v1/businesses/{biz_id}/receivings/{rcv_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": pline_id, "quantity": 0},
        )
        assert res0.status_code == 422

        res_neg = client.post(
            f"/api/v1/businesses/{biz_id}/receivings/{rcv_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": pline_id, "quantity": -5},
        )
        assert res_neg.status_code == 422

    # 17, 18, 19, 20. Partial receiving and over-receiving validation
    def test_partial_receiving_and_over_receiving_protection(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        pur_id, pline_id = create_finalized_purchase(token, biz_id, sup_id, br_id, prod_id, qty=100)

        # Receiving #1: 60
        rcv1 = client.post(
            f"/api/v1/businesses/{biz_id}/receivings",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/receivings/{rcv1}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": pline_id, "quantity": 60},
        )
        client.post(
            f"/api/v1/businesses/{biz_id}/receivings/{rcv1}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Receiving #2: 40 (valid)
        rcv2 = client.post(
            f"/api/v1/businesses/{biz_id}/receivings",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        ).json()["id"]
        res_ok = client.post(
            f"/api/v1/businesses/{biz_id}/receivings/{rcv2}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": pline_id, "quantity": 40},
        )
        assert res_ok.status_code == 201

        # Receiving #3: 10 (over-receiving -> 400)
        rcv3 = client.post(
            f"/api/v1/businesses/{biz_id}/receivings",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        ).json()["id"]
        res_over = client.post(
            f"/api/v1/businesses/{biz_id}/receivings/{rcv3}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": pline_id, "quantity": 10},
        )
        assert res_over.status_code == 400

    # 21. Cancelled receiving does not consume remaining quantity
    def test_cancelled_receiving_does_not_consume_quantity(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        pur_id, pline_id = create_finalized_purchase(token, biz_id, sup_id, br_id, prod_id, qty=100)

        # Draft rcv 100 then cancelled
        rcv1 = client.post(
            f"/api/v1/businesses/{biz_id}/receivings",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/receivings/{rcv1}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": pline_id, "quantity": 100},
        )
        client.post(
            f"/api/v1/businesses/{biz_id}/receivings/{rcv1}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )

        # New receiving for 100 should succeed since rcv1 is CANCELLED
        rcv2 = client.post(
            f"/api/v1/businesses/{biz_id}/receivings",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        ).json()["id"]
        res = client.post(
            f"/api/v1/businesses/{biz_id}/receivings/{rcv2}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": pline_id, "quantity": 100},
        )
        assert res.status_code == 201

    # 23-30. Lifecycle and immutability
    def test_lifecycle_and_immutability(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        pur_id, pline_id = create_finalized_purchase(token, biz_id, sup_id, br_id, prod_id, qty=50)

        rcv_id = client.post(
            f"/api/v1/businesses/{biz_id}/receivings",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        ).json()["id"]

        client.post(
            f"/api/v1/businesses/{biz_id}/receivings/{rcv_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": pline_id, "quantity": 50},
        )

        # Finalize
        fin_res = client.post(
            f"/api/v1/businesses/{biz_id}/receivings/{rcv_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fin_res.status_code == 200
        assert fin_res.json()["status"] == "FINALIZED"

        # Finalized immutable (cannot add line) -> 400
        res_add = client.post(
            f"/api/v1/businesses/{biz_id}/receivings/{rcv_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": pline_id, "quantity": 10},
        )
        assert res_add.status_code == 400

        # Cannot cancel finalized -> 400
        res_can = client.post(
            f"/api/v1/businesses/{biz_id}/receivings/{rcv_id}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_can.status_code == 400

        # Cannot delete finalized -> 400
        res_del = client.delete(
            f"/api/v1/businesses/{biz_id}/receivings/{rcv_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_del.status_code == 400

    # 34-37. Tenant isolation
    def test_tenant_isolation(self):
        token_a, _ = register_user("a@test.com")
        biz_a = create_business(token_a, "Biz A")
        sup_a = create_supplier(token_a, biz_a)
        br_a = create_branch(token_a, biz_a)
        unit_a = create_unit(token_a, biz_a)
        prod_a = create_product(token_a, biz_a, unit_a)
        loc_a = setup_warehouse_and_location(token_a, biz_a)
        pur_a_id, _ = create_finalized_purchase(token_a, biz_a, sup_a, br_a, prod_a)

        rcv_a_id = client.post(
            f"/api/v1/businesses/{biz_a}/receivings",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"purchase_id": pur_a_id, "inventory_location_id": loc_a},
        ).json()["id"]

        token_b, _ = register_user("b@test.com")
        biz_b = create_business(token_b, "Biz B")

        # User B accessing Biz A receiving -> 404 anti-enumeration
        res = client.get(
            f"/api/v1/businesses/{biz_a}/receivings/{rcv_a_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert res.status_code == 404

    # 38-42. RBAC matrix
    def test_rbac_authorization(self):
        owner_token, _ = register_user("owner@test.com")
        biz_id = create_business(owner_token)
        sup_id = create_supplier(owner_token, biz_id)
        br_id = create_branch(owner_token, biz_id)
        unit_id = create_unit(owner_token, biz_id)
        prod_id = create_product(owner_token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(owner_token, biz_id)
        pur_id, _ = create_finalized_purchase(owner_token, biz_id, sup_id, br_id, prod_id)

        member_token, member_id = register_user("member@test.com")
        client.post(
            f"/api/v1/businesses/{biz_id}/members",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"user_id": member_id, "role": "MEMBER"},
        )

        # Member can read receivings
        list_res = client.get(
            f"/api/v1/businesses/{biz_id}/receivings",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert list_res.status_code == 200

        # Member cannot create receiving -> 403
        create_res = client.post(
            f"/api/v1/businesses/{biz_id}/receivings",
            headers={"Authorization": f"Bearer {member_token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        )
        assert create_res.status_code == 403

    # MANDATORY CRITICAL NEGATIVE TEST
    def test_mandatory_critical_negative_test(self):
        """
        Create:
        Purchase FINALIZED
        PurchaseLine quantity = 100

        Receiving A: quantity = 80 -> FINALIZE
        Receiving B: quantity = 30 -> Attempt to Add/Finalize -> Expected 400

        StockBalance remains unchanged.
        StockMovement repository remains unchanged.
        """
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token, biz_id)

        pur_id, pline_id = create_finalized_purchase(token, biz_id, sup_id, br_id, prod_id, qty=100)

        # Receiving A: 80 -> FINALIZE
        rcv_a = client.post(
            f"/api/v1/businesses/{biz_id}/receivings",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        ).json()["id"]

        client.post(
            f"/api/v1/businesses/{biz_id}/receivings/{rcv_a}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": pline_id, "quantity": 80},
        )

        fin_a = client.post(
            f"/api/v1/businesses/{biz_id}/receivings/{rcv_a}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fin_a.status_code == 200

        # Receiving B: attempt 30 -> 400
        rcv_b = client.post(
            f"/api/v1/businesses/{biz_id}/receivings",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        ).json()["id"]

        res_b = client.post(
            f"/api/v1/businesses/{biz_id}/receivings/{rcv_b}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": pline_id, "quantity": 30},
        )
        assert res_b.status_code == 400

        # CRITICAL VERIFICATION: StockBalance and StockMovement repository unchanged
        # (Purchase finalization creates stock entries, but receiving should not add more)
        stock_balances = InMemoryStockBalanceRepository._balances
        stock_movements = InMemoryStockMovementRepository._movements
        balances_count = len(stock_balances)
        movements_count = len(stock_movements)

        # Attempt another over-receiving to ensure counts remain the same
        rcv_c = client.post(
            f"/api/v1/businesses/{biz_id}/receivings",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        ).json()["id"]

        res_c = client.post(
            f"/api/v1/businesses/{biz_id}/receivings/{rcv_c}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": pline_id, "quantity": 30},
        )
        assert res_c.status_code == 400

        assert len(stock_balances) == balances_count
        assert len(stock_movements) == movements_count

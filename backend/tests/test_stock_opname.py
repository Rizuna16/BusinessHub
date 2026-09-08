import pytest
from decimal import Decimal
from fastapi.testclient import TestClient

from app.main import app
from app.modules.authentication.repository import InMemoryUserRepository
from app.modules.account.repository import InMemoryAccountRepository
from app.modules.business.repository import InMemoryBusinessRepository
from app.modules.business_membership.repository import InMemoryBusinessMembershipRepository
from app.modules.warehouse.repository import InMemoryWarehouseRepository, InMemoryInventoryLocationRepository
from app.modules.unit.repository import InMemoryUnitRepository
from app.modules.product.repository import InMemoryProductRepository
from app.modules.product_variant.repository import InMemoryProductVariantRepository
from app.modules.inventory.repository import InMemoryStockBalanceRepository, InMemoryStockMovementRepository, InMemoryInventoryCostRepository
from app.modules.stock_opname.repository import InMemoryStockOpnameRepository

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_repositories():
    InMemoryStockOpnameRepository.clear()
    InMemoryStockBalanceRepository.clear()
    InMemoryStockMovementRepository.clear()
    InMemoryInventoryCostRepository.clear()
    InMemoryInventoryLocationRepository.clear()
    InMemoryWarehouseRepository.clear()
    InMemoryProductVariantRepository.clear()
    InMemoryProductRepository.clear()
    InMemoryUnitRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryUserRepository.clear()
    yield
    InMemoryStockOpnameRepository.clear()
    InMemoryStockBalanceRepository.clear()
    InMemoryStockMovementRepository.clear()
    InMemoryInventoryCostRepository.clear()
    InMemoryInventoryLocationRepository.clear()
    InMemoryWarehouseRepository.clear()
    InMemoryProductVariantRepository.clear()
    InMemoryProductRepository.clear()
    InMemoryUnitRepository.clear()
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
    user_id = data["id"]
    token = data.get("access_token")
    if not token:
        login_res = client.post(
            "/api/v1/auth/login", json={"email": email, "password": "Password123"}
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
    return token, user_id


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


def create_unit(token, business_id, name="Pcs", code="PCS"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/units",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code},
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_product(token, business_id, unit_id, name="Test Product", code="PROD-01", p_type="GOODS"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/products",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": name,
            "code": code,
            "unit_id": unit_id,
            "product_type": p_type,
        },
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_variant(token, business_id, product_id, name="Red", code="VAR-RED"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/products/{product_id}/variants",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code},
    )
    assert res.status_code == 201
    return res.json()["id"]


def setup_warehouse_and_location(token, business_id):
    wh_res = client.post(
        f"/api/v1/businesses/{business_id}/warehouses",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Main WH", "code": "WH-MAIN"},
    )
    assert wh_res.status_code == 201
    wh_id = wh_res.json()["id"]

    loc_res = client.post(
        f"/api/v1/businesses/{business_id}/warehouses/{wh_id}/locations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Rack A", "code": "RACK-A", "location_type": "STORAGE"},
    )
    assert loc_res.status_code == 201
    return wh_id, loc_res.json()["id"]


class TestStockOpnameFeature:
    def test_create_opname_success(self):
        token, _ = register_user()
        biz_id = create_business(token)
        _, loc_id = setup_warehouse_and_location(token, biz_id)

        res = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "inventory_location_id": loc_id,
                "notes": "Monthly stock opname",
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "DRAFT"
        assert data["inventory_location_id"] == loc_id
        assert data["notes"] == "Monthly stock opname"

    def test_create_opname_inactive_location_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        wh_id, loc_id = setup_warehouse_and_location(token, biz_id)

        # Archive location
        client.delete(
            f"/api/v1/businesses/{biz_id}/warehouses/{wh_id}/locations/{loc_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        res = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames",
            headers={"Authorization": f"Bearer {token}"},
            json={"inventory_location_id": loc_id},
        )
        assert res.status_code == 400

    def test_add_line_and_snapshot(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        _, loc_id = setup_warehouse_and_location(token, biz_id)

        # Add initial stock balance via opening balance = 100
        client.post(
            f"/api/v1/businesses/{biz_id}/inventory/opening-balance",
            headers={"Authorization": f"Bearer {token}"},
            json={"inventory_location_id": loc_id, "product_id": prod_id, "quantity": 100},
        )

        # Create opname
        op_res = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames",
            headers={"Authorization": f"Bearer {token}"},
            json={"inventory_location_id": loc_id},
        )
        opname_id = op_res.json()["id"]

        # Add line
        line_res = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames/{opname_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "variant_id": None},
        )
        assert line_res.status_code == 201
        line_data = line_res.json()
        assert Decimal(str(line_data["system_quantity"])) == Decimal("100")
        assert line_data["counted_quantity"] is None
        assert line_data["variance"] is None

        # Subsequent inventory movement does NOT change snapshot quantity
        client.post(
            f"/api/v1/businesses/{biz_id}/inventory/adjustments/in",
            headers={"Authorization": f"Bearer {token}"},
            json={"inventory_location_id": loc_id, "product_id": prod_id, "quantity": 25},
        )

        # Check line system_quantity remains 100 (snapshot rule)
        detail_res = client.get(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames/{opname_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert detail_res.status_code == 200
        assert Decimal(str(detail_res.json()["lines"][0]["system_quantity"])) == Decimal("100")

    def test_update_count_and_variance_calculation(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        _, loc_id = setup_warehouse_and_location(token, biz_id)

        client.post(
            f"/api/v1/businesses/{biz_id}/inventory/opening-balance",
            headers={"Authorization": f"Bearer {token}"},
            json={"inventory_location_id": loc_id, "product_id": prod_id, "quantity": 100},
        )

        op_res = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames",
            headers={"Authorization": f"Bearer {token}"},
            json={"inventory_location_id": loc_id},
        )
        opname_id = op_res.json()["id"]

        line_res = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames/{opname_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id},
        )
        line_id = line_res.json()["id"]

        # Update count to 97 (variance should be -3)
        patch_res = client.patch(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames/{opname_id}/lines/{line_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"counted_quantity": 97},
        )
        assert patch_res.status_code == 200
        patch_data = patch_res.json()
        assert Decimal(str(patch_data["counted_quantity"])) == Decimal("97")
        assert Decimal(str(patch_data["variance"])) == Decimal("-3")

    def test_service_product_rejected_in_opname(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        service_prod_id = create_product(token, biz_id, unit_id, name="Consulting", code="SERV-01", p_type="SERVICE")
        _, loc_id = setup_warehouse_and_location(token, biz_id)

        op_res = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames",
            headers={"Authorization": f"Bearer {token}"},
            json={"inventory_location_id": loc_id},
        )
        opname_id = op_res.json()["id"]

        res = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames/{opname_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": service_prod_id},
        )
        assert res.status_code == 400

    def test_duplicate_line_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        _, loc_id = setup_warehouse_and_location(token, biz_id)

        op_res = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames",
            headers={"Authorization": f"Bearer {token}"},
            json={"inventory_location_id": loc_id},
        )
        opname_id = op_res.json()["id"]

        # First line
        client.post(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames/{opname_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id},
        )

        # Duplicate line
        res_dup = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames/{opname_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id},
        )
        assert res_dup.status_code == 400

    def test_finalize_opname_adjustments(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_1 = create_product(token, biz_id, unit_id, name="Product 1", code="P1")
        prod_2 = create_product(token, biz_id, unit_id, name="Product 2", code="P2")
        _, loc_id = setup_warehouse_and_location(token, biz_id)

        # Opening balance P1 = 100, P2 = 50
        client.post(
            f"/api/v1/businesses/{biz_id}/inventory/opening-balance",
            headers={"Authorization": f"Bearer {token}"},
            json={"inventory_location_id": loc_id, "product_id": prod_1, "quantity": 100},
        )
        client.post(
            f"/api/v1/businesses/{biz_id}/inventory/opening-balance",
            headers={"Authorization": f"Bearer {token}"},
            json={"inventory_location_id": loc_id, "product_id": prod_2, "quantity": 50},
        )

        op_res = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames",
            headers={"Authorization": f"Bearer {token}"},
            json={"inventory_location_id": loc_id},
        )
        opname_id = op_res.json()["id"]

        # Add lines
        line_p1 = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames/{opname_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_1},
        ).json()["id"]

        line_p2 = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames/{opname_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_2},
        ).json()["id"]

        # Count P1 = 97 (variance -3 -> ADJUSTMENT_OUT 3)
        client.patch(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames/{opname_id}/lines/{line_p1}",
            headers={"Authorization": f"Bearer {token}"},
            json={"counted_quantity": 97},
        )

        # Count P2 = 55 (variance +5 -> ADJUSTMENT_IN 5)
        client.patch(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames/{opname_id}/lines/{line_p2}",
            headers={"Authorization": f"Bearer {token}"},
            json={"counted_quantity": 55},
        )

        # Finalize
        fin_res = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames/{opname_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fin_res.status_code == 200
        fin_data = fin_res.json()
        assert fin_data["status"] == "FINALIZED"
        assert fin_data["finalized_by_user_id"] is not None

        # Verify stock balance updated: P1 = 97, P2 = 55
        stock_list = client.get(
            f"/api/v1/businesses/{biz_id}/inventory/stock?inventory_location_id={loc_id}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        balances = {s["product_id"]: Decimal(str(s["quantity"])) for s in stock_list}
        assert balances[prod_1] == Decimal("97")
        assert balances[prod_2] == Decimal("55")

        # Verify movements created with reference_type = STOCK_OPNAME
        mov_list = client.get(
            f"/api/v1/businesses/{biz_id}/inventory/movements",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        opname_movements = [m for m in mov_list if m.get("reference_type") == "STOCK_OPNAME" and m.get("reference_id") == opname_id]
        assert len(opname_movements) == 2

    def test_stale_stock_rejected_409(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        _, loc_id = setup_warehouse_and_location(token, biz_id)

        client.post(
            f"/api/v1/businesses/{biz_id}/inventory/opening-balance",
            headers={"Authorization": f"Bearer {token}"},
            json={"inventory_location_id": loc_id, "product_id": prod_id, "quantity": 100},
        )

        op_res = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames",
            headers={"Authorization": f"Bearer {token}"},
            json={"inventory_location_id": loc_id},
        )
        opname_id = op_res.json()["id"]

        line_id = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames/{opname_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id},
        ).json()["id"]

        client.patch(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames/{opname_id}/lines/{line_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"counted_quantity": 90},
        )

        # Stock changes after snapshot (stale stock condition)
        client.post(
            f"/api/v1/businesses/{biz_id}/inventory/adjustments/in",
            headers={"Authorization": f"Bearer {token}"},
            json={"inventory_location_id": loc_id, "product_id": prod_id, "quantity": 10},
        )

        # Attempt to finalize -> 409 Conflict
        fin_res = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames/{opname_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fin_res.status_code == 409
        assert "Stok berubah sejak opname dibuat" in fin_res.json()["message"]

        # Opname remains DRAFT
        get_res = client.get(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames/{opname_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_res.json()["status"] == "DRAFT"

    def test_finalize_missing_count_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        _, loc_id = setup_warehouse_and_location(token, biz_id)

        client.post(
            f"/api/v1/businesses/{biz_id}/inventory/opening-balance",
            headers={"Authorization": f"Bearer {token}"},
            json={"inventory_location_id": loc_id, "product_id": prod_id, "quantity": 100},
        )

        op_res = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames",
            headers={"Authorization": f"Bearer {token}"},
            json={"inventory_location_id": loc_id},
        )
        opname_id = op_res.json()["id"]

        client.post(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames/{opname_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id},
        )

        # Finalize without entering count -> 400
        fin_res = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames/{opname_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fin_res.status_code == 400

    def test_finalized_immutability(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        _, loc_id = setup_warehouse_and_location(token, biz_id)

        client.post(
            f"/api/v1/businesses/{biz_id}/inventory/opening-balance",
            headers={"Authorization": f"Bearer {token}"},
            json={"inventory_location_id": loc_id, "product_id": prod_id, "quantity": 100},
        )

        op_res = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames",
            headers={"Authorization": f"Bearer {token}"},
            json={"inventory_location_id": loc_id},
        )
        opname_id = op_res.json()["id"]

        line_id = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames/{opname_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id},
        ).json()["id"]

        client.patch(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames/{opname_id}/lines/{line_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"counted_quantity": 100},
        )

        client.post(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames/{opname_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Try to add line to finalized opname -> 400
        res_add = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames/{opname_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id},
        )
        assert res_add.status_code == 400

        # Try to delete finalized opname -> 400
        res_del = client.delete(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames/{opname_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_del.status_code == 400

    def test_membership_authorization(self):
        owner_token, _ = register_user("owner@test.com")
        biz_id = create_business(owner_token)
        _, loc_id = setup_warehouse_and_location(owner_token, biz_id)

        member_token, member_id = register_user("member@test.com")
        client.post(
            f"/api/v1/businesses/{biz_id}/members",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"user_id": member_id, "role": "MEMBER"},
        )

        # Member can read opnames
        res_list = client.get(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert res_list.status_code == 200

        # Member CANNOT create opname -> 403
        res_create = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/stock-opnames",
            headers={"Authorization": f"Bearer {member_token}"},
            json={"inventory_location_id": loc_id},
        )
        assert res_create.status_code == 403

    def test_tenant_isolation(self):
        token_a, _ = register_user("a@test.com")
        biz_a = create_business(token_a, "Biz A")
        _, loc_a = setup_warehouse_and_location(token_a, biz_a)

        token_b, _ = register_user("b@test.com")
        biz_b = create_business(token_b, "Biz B")

        # User B accessing Biz A opnames -> 404 anti-enumeration
        res = client.get(
            f"/api/v1/businesses/{biz_a}/inventory/stock-opnames",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert res.status_code == 404

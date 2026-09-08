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

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_repositories():
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


class TestInventoryStockFoundation:
    def test_opening_balance_success(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        _, loc_id = setup_warehouse_and_location(token, biz_id)

        res = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/opening-balance",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "inventory_location_id": loc_id,
                "product_id": prod_id,
                "variant_id": None,
                "quantity": 100,
                "notes": "Initial stock",
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert data["movement_type"] == "OPENING_BALANCE"
        assert len(data["lines"]) == 1
        assert Decimal(str(data["lines"][0]["quantity"])) == Decimal("100")
        assert data["lines"][0]["direction"] == "IN"

        # Check Stock Balance
        stock_res = client.get(
            f"/api/v1/businesses/{biz_id}/inventory/stock",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert stock_res.status_code == 200
        stocks = stock_res.json()
        assert len(stocks) == 1
        assert Decimal(str(stocks[0]["quantity"])) == Decimal("100")

    def test_opening_balance_with_variant(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        var_id = create_variant(token, biz_id, prod_id)
        _, loc_id = setup_warehouse_and_location(token, biz_id)

        res = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/opening-balance",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "inventory_location_id": loc_id,
                "product_id": prod_id,
                "variant_id": var_id,
                "quantity": 50,
            },
        )
        assert res.status_code == 201

        # Check total stock endpoint
        tot_res = client.get(
            f"/api/v1/businesses/{biz_id}/inventory/stock/total?product_id={prod_id}&variant_id={var_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert tot_res.status_code == 200
        assert Decimal(str(tot_res.json()["total_quantity"])) == Decimal("50")

    def test_opening_balance_service_product_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id, p_type="SERVICE")
        _, loc_id = setup_warehouse_and_location(token, biz_id)

        res = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/opening-balance",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "inventory_location_id": loc_id,
                "product_id": prod_id,
                "quantity": 10,
            },
        )
        assert res.status_code == 400
        assert "GOODS" in res.json()["message"]

    def test_opening_balance_negative_zero_quantity_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        _, loc_id = setup_warehouse_and_location(token, biz_id)

        res_zero = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/opening-balance",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "inventory_location_id": loc_id,
                "product_id": prod_id,
                "quantity": 0,
            },
        )
        assert res_zero.status_code in (400, 422)

        res_neg = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/opening-balance",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "inventory_location_id": loc_id,
                "product_id": prod_id,
                "quantity": -5,
            },
        )
        assert res_neg.status_code in (400, 422)

    def test_adjustment_in_and_out(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        _, loc_id = setup_warehouse_and_location(token, biz_id)

        # Adjustment IN +20
        res_in = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/adjustments/in",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "inventory_location_id": loc_id,
                "product_id": prod_id,
                "quantity": 20,
            },
        )
        assert res_in.status_code == 201

        # Adjustment OUT -5
        res_out = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/adjustments/out",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "inventory_location_id": loc_id,
                "product_id": prod_id,
                "quantity": 5,
            },
        )
        assert res_out.status_code == 201

        # Verify stock balance = 15
        stock_res = client.get(
            f"/api/v1/businesses/{biz_id}/inventory/stock",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert Decimal(str(stock_res.json()[0]["quantity"])) == Decimal("15")

    def test_adjustment_out_insufficient_stock_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        _, loc_id = setup_warehouse_and_location(token, biz_id)

        # Attempt to adjust OUT 10 with 0 stock
        res = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/adjustments/out",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "inventory_location_id": loc_id,
                "product_id": prod_id,
                "quantity": 10,
            },
        )
        assert res.status_code == 400
        assert "Insufficient stock" in res.json()["message"]

    def test_transfer_stock(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        wh_id, loc_a = setup_warehouse_and_location(token, biz_id)

        # Create second location
        loc_b_res = client.post(
            f"/api/v1/businesses/{biz_id}/warehouses/{wh_id}/locations",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Rack B", "code": "RACK-B", "location_type": "STORAGE"},
        )
        loc_b = loc_b_res.json()["id"]

        # Initial opening balance 50 at loc_a
        client.post(
            f"/api/v1/businesses/{biz_id}/inventory/opening-balance",
            headers={"Authorization": f"Bearer {token}"},
            json={"inventory_location_id": loc_a, "product_id": prod_id, "quantity": 50},
        )

        # Transfer 15 from loc_a to loc_b
        res_tf = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/transfers",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "source_inventory_location_id": loc_a,
                "destination_inventory_location_id": loc_b,
                "product_id": prod_id,
                "quantity": 15,
            },
        )
        assert res_tf.status_code == 201
        movements = res_tf.json()
        assert len(movements) == 2
        assert movements[0]["movement_type"] == "TRANSFER_OUT"
        assert movements[1]["movement_type"] == "TRANSFER_IN"
        assert movements[0]["reference_id"] == movements[1]["reference_id"]

        # Verify stock at loc_a = 35, loc_b = 15
        s_a = client.get(
            f"/api/v1/businesses/{biz_id}/inventory/stock?inventory_location_id={loc_a}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        assert Decimal(str(s_a[0]["quantity"])) == Decimal("35")

        s_b = client.get(
            f"/api/v1/businesses/{biz_id}/inventory/stock?inventory_location_id={loc_b}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        assert Decimal(str(s_b[0]["quantity"])) == Decimal("15")

    def test_transfer_same_location_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        _, loc_a = setup_warehouse_and_location(token, biz_id)

        res = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/transfers",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "source_inventory_location_id": loc_a,
                "destination_inventory_location_id": loc_a,
                "product_id": prod_id,
                "quantity": 10,
            },
        )
        assert res.status_code == 400

    def test_authorization_member_forbidden(self):
        owner_token, _ = register_user("owner@test.com")
        biz_id = create_business(owner_token)
        unit_id = create_unit(owner_token, biz_id)
        prod_id = create_product(owner_token, biz_id, unit_id)
        _, loc_id = setup_warehouse_and_location(owner_token, biz_id)

        # Register member user & add to business as MEMBER
        member_token, member_id = register_user("member@test.com")
        client.post(
            f"/api/v1/businesses/{biz_id}/members",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"user_id": member_id, "role": "MEMBER"},
        )

        # Member can read stock & movements
        r_stock = client.get(
            f"/api/v1/businesses/{biz_id}/inventory/stock",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert r_stock.status_code == 200

        r_mov = client.get(
            f"/api/v1/businesses/{biz_id}/inventory/movements",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert r_mov.status_code == 200

        # Member CANNOT open balance or adjust or transfer
        res_open = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/opening-balance",
            headers={"Authorization": f"Bearer {member_token}"},
            json={"inventory_location_id": loc_id, "product_id": prod_id, "quantity": 100},
        )
        assert res_open.status_code == 403

        res_adj = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/adjustments/in",
            headers={"Authorization": f"Bearer {member_token}"},
            json={"inventory_location_id": loc_id, "product_id": prod_id, "quantity": 10},
        )
        assert res_adj.status_code == 403

    def test_tenant_isolation_cross_business_blocked(self):
        token_a, _ = register_user("user_a@test.com")
        biz_a = create_business(token_a, "Biz A")
        unit_a = create_unit(token_a, biz_a)
        prod_a = create_product(token_a, biz_a, unit_a)
        _, loc_a = setup_warehouse_and_location(token_a, biz_a)

        token_b, _ = register_user("user_b@test.com")
        biz_b = create_business(token_b, "Biz B")

        # User B trying to access Biz A inventory -> 404 anti-enumeration
        res_stock = client.get(
            f"/api/v1/businesses/{biz_a}/inventory/stock",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert res_stock.status_code == 404

        # User A trying to use Biz B location in Biz A opening balance -> 400
        _, loc_b = setup_warehouse_and_location(token_b, biz_b)
        res_cross_loc = client.post(
            f"/api/v1/businesses/{biz_a}/inventory/opening-balance",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"inventory_location_id": loc_b, "product_id": prod_a, "quantity": 10},
        )
        assert res_cross_loc.status_code == 400

    def test_archived_location_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        wh_id, loc_id = setup_warehouse_and_location(token, biz_id)

        # Archive location
        arch_res = client.delete(
            f"/api/v1/businesses/{biz_id}/warehouses/{wh_id}/locations/{loc_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert arch_res.status_code == 200

        # Attempt opening balance at archived location
        res = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/opening-balance",
            headers={"Authorization": f"Bearer {token}"},
            json={"inventory_location_id": loc_id, "product_id": prod_id, "quantity": 10},
        )
        assert res.status_code == 400

    def test_stock_balance_detail(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        _, loc_id = setup_warehouse_and_location(token, biz_id)

        client.post(
            f"/api/v1/businesses/{biz_id}/inventory/opening-balance",
            headers={"Authorization": f"Bearer {token}"},
            json={"inventory_location_id": loc_id, "product_id": prod_id, "quantity": 40},
        )

        stock_list = client.get(
            f"/api/v1/businesses/{biz_id}/inventory/stock",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        stock_id = stock_list[0]["id"]

        detail_res = client.get(
            f"/api/v1/businesses/{biz_id}/inventory/stock/{stock_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert detail_res.status_code == 200
        assert detail_res.json()["id"] == stock_id
        assert Decimal(str(detail_res.json()["quantity"])) == Decimal("40")

    def test_immutability_endpoints_absent(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        _, loc_id = setup_warehouse_and_location(token, biz_id)

        op_res = client.post(
            f"/api/v1/businesses/{biz_id}/inventory/opening-balance",
            headers={"Authorization": f"Bearer {token}"},
            json={"inventory_location_id": loc_id, "product_id": prod_id, "quantity": 10},
        )
        mov_id = op_res.json()["id"]

        # Try to PATCH or DELETE movement -> 405 Method Not Allowed or 404 Not Found
        patch_res = client.patch(
            f"/api/v1/businesses/{biz_id}/inventory/movements/{mov_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"notes": "Hacked"},
        )
        assert patch_res.status_code in (405, 404)

        del_res = client.delete(
            f"/api/v1/businesses/{biz_id}/inventory/movements/{mov_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert del_res.status_code in (405, 404)

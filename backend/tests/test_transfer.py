import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from datetime import datetime, timezone
from unittest.mock import patch

from app.main import app
from app.modules.authentication.repository import InMemoryUserRepository
from app.modules.account.repository import InMemoryAccountRepository
from app.modules.business.repository import InMemoryBusinessRepository
from app.modules.business_membership.repository import InMemoryBusinessMembershipRepository
from app.modules.business_membership.schemas import BusinessMembershipRole
from app.modules.customer.repository import InMemoryCustomerRepository
from app.modules.branch.repository import InMemoryBranchRepository
from app.modules.unit.repository import InMemoryUnitRepository
from app.modules.product.repository import InMemoryProductRepository
from app.modules.product_variant.repository import InMemoryProductVariantRepository
from app.modules.warehouse.repository import InMemoryWarehouseRepository, InMemoryInventoryLocationRepository
from app.modules.inventory.repository import InMemoryStockBalanceRepository, InMemoryStockMovementRepository, InMemoryInventoryCostRepository
from app.modules.transfer.repository import InMemoryTransferRepository
from app.modules.inventory.schemas import InventoryCostMovementType
import threading

client = TestClient(app)
noclient = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def clear_repositories():
    InMemoryTransferRepository.clear()
    InMemoryStockBalanceRepository.clear()
    InMemoryStockMovementRepository.clear()
    InMemoryInventoryCostRepository.clear()
    InMemoryInventoryLocationRepository.clear()
    InMemoryWarehouseRepository.clear()
    InMemoryProductVariantRepository.clear()
    InMemoryProductRepository.clear()
    InMemoryUnitRepository.clear()
    InMemoryBranchRepository.clear()
    InMemoryCustomerRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryUserRepository.clear()
    yield
    InMemoryTransferRepository.clear()
    InMemoryStockBalanceRepository.clear()
    InMemoryStockMovementRepository.clear()
    InMemoryInventoryCostRepository.clear()
    InMemoryInventoryLocationRepository.clear()
    InMemoryWarehouseRepository.clear()
    InMemoryProductVariantRepository.clear()
    InMemoryProductRepository.clear()
    InMemoryUnitRepository.clear()
    InMemoryBranchRepository.clear()
    InMemoryCustomerRepository.clear()
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


def setup_warehouse_and_location(token, business_id, name="WH 1", code="WH-1", loc_name="LOC 1", loc_code="L1"):
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
        json={"name": loc_name, "code": loc_code, "location_type": "GENERAL"},
    )
    assert loc_res.status_code == 201
    return loc_res.json()["id"]


def add_opening_stock(token, business_id, location_id, product_id, variant_id=None, qty="100", unit_cost="10000"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/inventory/opening-balance",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "inventory_location_id": location_id,
            "product_id": product_id,
            "variant_id": variant_id,
            "quantity": qty,
            "unit_cost": unit_cost,
        },
    )
    assert res.status_code == 201


def _get_stock_qty(token, business_id, location_id, product_id, variant_id=None):
    params = {"inventory_location_id": location_id}
    if product_id:
        params["product_id"] = product_id
    if variant_id:
        params["variant_id"] = variant_id
    bals = client.get(
        f"/api/v1/businesses/{business_id}/inventory/stock",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
    ).json()
    if not bals:
        return Decimal("0")
    for b in bals:
        if b["product_id"] == product_id and b.get("variant_id") == variant_id:
            return Decimal(str(b["quantity"]))
    return Decimal("0")


class TestTransferCreation:

    def test_unauthenticated_rejected(self):
        res = client.get("/api/v1/businesses/biz123/transfer-orders")
        assert res.status_code == 401

    def test_create_transfer_success(self):
        token, _ = register_user()
        biz_id = create_business(token)
        loc1 = setup_warehouse_and_location(token, biz_id, name="WH 1", code="WH1", loc_name="Loc 1", loc_code="L1")
        loc2 = setup_warehouse_and_location(token, biz_id, name="WH 2", code="WH2", loc_name="Loc 2", loc_code="L2")
        res = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "source_location_id": loc1,
                "destination_location_id": loc2,
                "notes": "Inter-warehouse transfer",
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "DRAFT"
        assert data["transfer_number"] == "TRF-000001"
        assert data["source_location_id"] == loc1
        assert data["destination_location_id"] == loc2

    def test_same_source_destination_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        loc1 = setup_warehouse_and_location(token, biz_id)
        res = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "source_location_id": loc1,
                "destination_location_id": loc1,
            },
        )
        assert res.status_code == 400
        assert "must be different" in res.json()["message"]

    def test_duplicate_product_variant_in_same_transfer_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc1 = setup_warehouse_and_location(token, biz_id, name="WH1", code="W1", loc_name="L1", loc_code="C1")
        loc2 = setup_warehouse_and_location(token, biz_id, name="WH2", code="W2", loc_name="L2", loc_code="C2")
        add_opening_stock(token, biz_id, loc1, prod_id, qty="100", unit_cost="10000")
        t_id = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders",
            headers={"Authorization": f"Bearer {token}"},
            json={"source_location_id": loc1, "destination_location_id": loc2},
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": "10"},
        )
        r2 = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": "5"},
        )
        assert r2.status_code == 400
        assert "already included" in r2.json()["message"]

    def test_service_product_transfer_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        srv_id = create_product(token, biz_id, unit_id, name="Service", code="SRV", p_type="SERVICE")
        loc1 = setup_warehouse_and_location(token, biz_id, name="WH1", code="W1", loc_name="L1", loc_code="C1")
        loc2 = setup_warehouse_and_location(token, biz_id, name="WH2", code="W2", loc_name="L2", loc_code="C2")
        t_id = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders",
            headers={"Authorization": f"Bearer {token}"},
            json={"source_location_id": loc1, "destination_location_id": loc2},
        ).json()["id"]
        line_res = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": srv_id, "quantity": "1"},
        )
        assert line_res.status_code == 400
        assert "GOODS products" in line_res.json()["message"]

    def test_invalid_source_location_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        loc1 = setup_warehouse_and_location(token, biz_id)
        res = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "source_location_id": "00000000-0000-0000-0000-000000000000",
                "destination_location_id": loc1,
            },
        )
        assert res.status_code in (400, 404)

    def test_invalid_quantity_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc1 = setup_warehouse_and_location(token, biz_id, name="WH1", code="W1", loc_name="L1", loc_code="C1")
        loc2 = setup_warehouse_and_location(token, biz_id, name="WH2", code="W2", loc_name="L2", loc_code="C2")
        t_id = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders",
            headers={"Authorization": f"Bearer {token}"},
            json={"source_location_id": loc1, "destination_location_id": loc2},
        ).json()["id"]
        line_res = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": "0"},
        )
        assert line_res.status_code == 422

    def test_numbering_sequence(self):
        token, _ = register_user()
        biz_id = create_business(token)
        loc1 = setup_warehouse_and_location(token, biz_id, name="WH1", code="W1", loc_name="L1", loc_code="C1")
        loc2 = setup_warehouse_and_location(token, biz_id, name="WH2", code="W2", loc_name="L2", loc_code="C2")
        t1 = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders",
            headers={"Authorization": f"Bearer {token}"},
            json={"source_location_id": loc1, "destination_location_id": loc2},
        ).json()
        t2 = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders",
            headers={"Authorization": f"Bearer {token}"},
            json={"source_location_id": loc1, "destination_location_id": loc2},
        ).json()
        assert t1["transfer_number"] == "TRF-000001"
        assert t2["transfer_number"] == "TRF-000002"


class TestTransferSecurity:

    def test_cross_business_source_rejected(self):
        token_a, _ = register_user(email="a@a.com")
        token_b, _ = register_user(email="b@b.com")
        biz_a = create_business(token_a, name="Biz A")
        biz_b = create_business(token_b, name="Biz B")
        loc_a = setup_warehouse_and_location(token_a, biz_a, name="WH A", code="WA", loc_name="LA", loc_code="LA1")
        loc_b = setup_warehouse_and_location(token_b, biz_b, name="WH B", code="WB", loc_name="LB", loc_code="LB1")
        res = client.post(
            f"/api/v1/businesses/{biz_a}/transfer-orders",
            headers={"Authorization": f"Bearer {token_a}"},
            json={
                "source_location_id": loc_b,
                "destination_location_id": loc_a,
            },
        )
        assert res.status_code in (400, 404)

    def test_cross_business_destination_rejected(self):
        token_a, _ = register_user(email="cross1@a.com")
        token_b, _ = register_user(email="cross2@b.com")
        biz_a = create_business(token_a, name="Cross A")
        biz_b = create_business(token_b, name="Cross B")
        loc_a = setup_warehouse_and_location(token_a, biz_a, name="WH A", code="WA", loc_name="LA", loc_code="LA1")
        loc_b = setup_warehouse_and_location(token_b, biz_b, name="WH B", code="WB", loc_name="LB", loc_code="LB1")
        res = client.post(
            f"/api/v1/businesses/{biz_a}/transfer-orders",
            headers={"Authorization": f"Bearer {token_a}"},
            json={
                "source_location_id": loc_a,
                "destination_location_id": loc_b,
            },
        )
        assert res.status_code in (400, 404)

    def test_get_transfer_cross_business_rejected(self):
        token_a, _ = register_user(email="get-cross1@a.com")
        token_b, _ = register_user(email="get-cross2@b.com")
        biz_a = create_business(token_a, name="GetCross A")
        biz_b = create_business(token_b, name="GetCross B")
        loc1 = setup_warehouse_and_location(token_a, biz_a, name="WH1", code="W1", loc_name="L1", loc_code="C1")
        loc2 = setup_warehouse_and_location(token_a, biz_a, name="WH2", code="W2", loc_name="L2", loc_code="C2")
        t_id = client.post(
            f"/api/v1/businesses/{biz_a}/transfer-orders",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"source_location_id": loc1, "destination_location_id": loc2},
        ).json()["id"]
        res = noclient.get(
            f"/api/v1/businesses/{biz_b}/transfer-orders/{t_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert res.status_code == 404

    def test_idor_transfer_not_visible_cross_business(self):
        token_a, _ = register_user(email="idor1@a.com")
        token_b, _ = register_user(email="idor2@b.com")
        biz_a = create_business(token_a, name="IDOR A")
        biz_b = create_business(token_b, name="IDOR B")
        loc1 = setup_warehouse_and_location(token_a, biz_a, name="WH1", code="W1", loc_name="L1", loc_code="C1")
        loc2 = setup_warehouse_and_location(token_a, biz_a, name="WH2", code="W2", loc_name="L2", loc_code="C2")
        t_id = client.post(
            f"/api/v1/businesses/{biz_a}/transfer-orders",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"source_location_id": loc1, "destination_location_id": loc2},
        ).json()["id"]
        res = noclient.get(
            f"/api/v1/businesses/{biz_b}/transfer-orders",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        ids = [t["id"] for t in res.json()["items"]]
        assert t_id not in ids


class TestTransferLifecycle:

    def test_dispatch_and_receive_full_lifecycle(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc1 = setup_warehouse_and_location(token, biz_id, name="WH1", code="W1", loc_name="L1", loc_code="C1")
        loc2 = setup_warehouse_and_location(token, biz_id, name="WH2", code="W2", loc_name="L2", loc_code="C2")
        add_opening_stock(token, biz_id, loc1, prod_id, qty="100", unit_cost="15000")

        t_id = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders",
            headers={"Authorization": f"Bearer {token}"},
            json={"source_location_id": loc1, "destination_location_id": loc2},
        ).json()["id"]

        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": "30"},
        )

        disp_res = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/dispatch",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert disp_res.status_code == 200
        assert disp_res.json()["status"] == "DISPATCHED"
        bals = client.get(
            f"/api/v1/businesses/{biz_id}/inventory/stock?inventory_location_id={loc1}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        assert Decimal(str(bals[0]["quantity"])) == Decimal("70")
        bals2 = client.get(
            f"/api/v1/businesses/{biz_id}/inventory/stock?inventory_location_id={loc2}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        assert len(bals2) == 0

        recv_res = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/receive",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert recv_res.status_code == 200
        assert recv_res.json()["status"] == "RECEIVED"
        bals2_recv = client.get(
            f"/api/v1/businesses/{biz_id}/inventory/stock?inventory_location_id={loc2}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        assert Decimal(str(bals2_recv[0]["quantity"])) == Decimal("30")

    def test_duplicate_dispatch_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc1 = setup_warehouse_and_location(token, biz_id, name="WH1", code="W1", loc_name="L1", loc_code="C1")
        loc2 = setup_warehouse_and_location(token, biz_id, name="WH2", code="W2", loc_name="L2", loc_code="C2")
        add_opening_stock(token, biz_id, loc1, prod_id, qty="100", unit_cost="10000")
        t_id = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders",
            headers={"Authorization": f"Bearer {token}"},
            json={"source_location_id": loc1, "destination_location_id": loc2},
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": "10"},
        )
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/dispatch",
            headers={"Authorization": f"Bearer {token}"},
        )
        r = noclient.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/dispatch",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 400

    def test_duplicate_receive_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc1 = setup_warehouse_and_location(token, biz_id, name="WH1", code="W1", loc_name="L1", loc_code="C1")
        loc2 = setup_warehouse_and_location(token, biz_id, name="WH2", code="W2", loc_name="L2", loc_code="C2")
        add_opening_stock(token, biz_id, loc1, prod_id, qty="100", unit_cost="10000")
        t_id = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders",
            headers={"Authorization": f"Bearer {token}"},
            json={"source_location_id": loc1, "destination_location_id": loc2},
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": "10"},
        )
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/dispatch",
            headers={"Authorization": f"Bearer {token}"},
        )
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/receive",
            headers={"Authorization": f"Bearer {token}"},
        )
        r = noclient.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/receive",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 400

    def test_receive_without_dispatch_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc1 = setup_warehouse_and_location(token, biz_id, name="WH1", code="W1", loc_name="L1", loc_code="C1")
        loc2 = setup_warehouse_and_location(token, biz_id, name="WH2", code="W2", loc_name="L2", loc_code="C2")
        add_opening_stock(token, biz_id, loc1, prod_id, qty="100", unit_cost="10000")
        t_id = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders",
            headers={"Authorization": f"Bearer {token}"},
            json={"source_location_id": loc1, "destination_location_id": loc2},
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": "10"},
        )
        r = noclient.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/receive",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 400

    def test_received_is_terminal(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc1 = setup_warehouse_and_location(token, biz_id, name="WH1", code="W1", loc_name="L1", loc_code="C1")
        loc2 = setup_warehouse_and_location(token, biz_id, name="WH2", code="W2", loc_name="L2", loc_code="C2")
        add_opening_stock(token, biz_id, loc1, prod_id, qty="100", unit_cost="10000")
        t_id = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders",
            headers={"Authorization": f"Bearer {token}"},
            json={"source_location_id": loc1, "destination_location_id": loc2},
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": "10"},
        )
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/dispatch",
            headers={"Authorization": f"Bearer {token}"},
        )
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/receive",
            headers={"Authorization": f"Bearer {token}"},
        )
        r = noclient.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 400

    def test_cancelled_is_terminal(self):
        token, _ = register_user()
        biz_id = create_business(token)
        loc1 = setup_warehouse_and_location(token, biz_id, name="WH1", code="W1", loc_name="L1", loc_code="C1")
        loc2 = setup_warehouse_and_location(token, biz_id, name="WH2", code="W2", loc_name="L2", loc_code="C2")
        t_id = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders",
            headers={"Authorization": f"Bearer {token}"},
            json={"source_location_id": loc1, "destination_location_id": loc2},
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )
        r = noclient.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/dispatch",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 400

    def test_insufficient_stock_dispatch_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc1 = setup_warehouse_and_location(token, biz_id, name="WH1", code="W1", loc_name="L1", loc_code="C1")
        loc2 = setup_warehouse_and_location(token, biz_id, name="WH2", code="W2", loc_name="L2", loc_code="C2")
        add_opening_stock(token, biz_id, loc1, prod_id, qty="10", unit_cost="10000")
        t_id = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders",
            headers={"Authorization": f"Bearer {token}"},
            json={"source_location_id": loc1, "destination_location_id": loc2},
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": "20"},
        )
        disp_res = noclient.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/dispatch",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert disp_res.status_code == 400
        assert "Insufficient stock" in disp_res.json()["message"]

    def test_dispatch_without_lines_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        loc1 = setup_warehouse_and_location(token, biz_id, name="WH1", code="W1", loc_name="L1", loc_code="C1")
        loc2 = setup_warehouse_and_location(token, biz_id, name="WH2", code="W2", loc_name="L2", loc_code="C2")
        t_id = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders",
            headers={"Authorization": f"Bearer {token}"},
            json={"source_location_id": loc1, "destination_location_id": loc2},
        ).json()["id"]
        r = noclient.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/dispatch",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 400

    def test_modify_lines_after_dispatch_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        prod2 = create_product(token, biz_id, unit_id, name="P2", code="P2")
        loc1 = setup_warehouse_and_location(token, biz_id, name="WH1", code="W1", loc_name="L1", loc_code="C1")
        loc2 = setup_warehouse_and_location(token, biz_id, name="WH2", code="W2", loc_name="L2", loc_code="C2")
        add_opening_stock(token, biz_id, loc1, prod_id, qty="100", unit_cost="10000")
        t_id = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders",
            headers={"Authorization": f"Bearer {token}"},
            json={"source_location_id": loc1, "destination_location_id": loc2},
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": "10"},
        )
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/dispatch",
            headers={"Authorization": f"Bearer {token}"},
        )
        r = noclient.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod2, "quantity": "5"},
        )
        assert r.status_code == 400
        assert "non-draft" in r.json()["message"]


class TestTransferInventoryCancellation:

    def test_cancel_from_draft_has_zero_inventory_effect(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc1 = setup_warehouse_and_location(token, biz_id, name="WH1", code="W1", loc_name="L1", loc_code="C1")
        loc2 = setup_warehouse_and_location(token, biz_id, name="WH2", code="W2", loc_name="L2", loc_code="C2")
        add_opening_stock(token, biz_id, loc1, prod_id, qty="100", unit_cost="10000")
        t_id = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders",
            headers={"Authorization": f"Bearer {token}"},
            json={"source_location_id": loc1, "destination_location_id": loc2},
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": "20"},
        )
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert _get_stock_qty(token, biz_id, loc1, prod_id) == Decimal("100")

    def test_cancel_from_dispatched_restores_source_exactly(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc1 = setup_warehouse_and_location(token, biz_id, name="WH1", code="W1", loc_name="L1", loc_code="C1")
        loc2 = setup_warehouse_and_location(token, biz_id, name="WH2", code="W2", loc_name="L2", loc_code="C2")
        add_opening_stock(token, biz_id, loc1, prod_id, qty="100", unit_cost="10000")
        t_id = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders",
            headers={"Authorization": f"Bearer {token}"},
            json={"source_location_id": loc1, "destination_location_id": loc2},
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": "40"},
        )
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/dispatch",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert _get_stock_qty(token, biz_id, loc1, prod_id) == Decimal("60")
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert _get_stock_qty(token, biz_id, loc1, prod_id) == Decimal("100")
        assert _get_stock_qty(token, biz_id, loc2, prod_id) == Decimal("0")

    def test_duplicate_cancel_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        loc1 = setup_warehouse_and_location(token, biz_id, name="WH1", code="W1", loc_name="L1", loc_code="C1")
        loc2 = setup_warehouse_and_location(token, biz_id, name="WH2", code="W2", loc_name="L2", loc_code="C2")
        t_id = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders",
            headers={"Authorization": f"Bearer {token}"},
            json={"source_location_id": loc1, "destination_location_id": loc2},
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )
        r = noclient.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 400


class TestTransferCosting:

    def test_dispatch_captures_authoritative_mac_as_snapshot(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc1 = setup_warehouse_and_location(token, biz_id, name="WH1", code="W1", loc_name="L1", loc_code="C1")
        loc2 = setup_warehouse_and_location(token, biz_id, name="WH2", code="W2", loc_name="L2", loc_code="C2")
        add_opening_stock(token, biz_id, loc1, prod_id, qty="100", unit_cost="12000")
        t_id = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders",
            headers={"Authorization": f"Bearer {token}"},
            json={"source_location_id": loc1, "destination_location_id": loc2},
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": "10"},
        )
        disp = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/dispatch",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        assert disp["lines"][0]["unit_cost_snapshot"] == str(Decimal("12000"))

    def test_receipt_uses_dispatch_cost_snapshot_not_current_mac(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc1 = setup_warehouse_and_location(token, biz_id, name="WH1", code="W1", loc_name="L1", loc_code="C1")
        loc2 = setup_warehouse_and_location(token, biz_id, name="WH2", code="W2", loc_name="L2", loc_code="C2")
        add_opening_stock(token, biz_id, loc1, prod_id, qty="100", unit_cost="10000")
        t_id = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders",
            headers={"Authorization": f"Bearer {token}"},
            json={"source_location_id": loc1, "destination_location_id": loc2},
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": "20"},
        )
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/dispatch",
            headers={"Authorization": f"Bearer {token}"},
        )
        t_before = client.get(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        snapshot = t_before["lines"][0]["unit_cost_snapshot"]
        assert Decimal(snapshot) == Decimal("10000")

        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/receive",
            headers={"Authorization": f"Bearer {token}"},
        )
        from app.modules.inventory.repository import inventory_cost_repository
        cs = inventory_cost_repository._cost_states.get(f"{biz_id}:{prod_id}:NONE")
        assert cs is not None
        assert cs.quantity == Decimal("100")
        assert cs.total_cost == Decimal("1000000")

    def test_multiple_lines_multiple_products(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod1 = create_product(token, biz_id, unit_id, name="Prod1", code="PRD1")
        prod2 = create_product(token, biz_id, unit_id, name="Prod2", code="PRD2")
        loc1 = setup_warehouse_and_location(token, biz_id, name="WH1", code="W1", loc_name="L1", loc_code="C1")
        loc2 = setup_warehouse_and_location(token, biz_id, name="WH2", code="W2", loc_name="L2", loc_code="C2")
        add_opening_stock(token, biz_id, loc1, prod1, qty="100", unit_cost="5000")
        add_opening_stock(token, biz_id, loc1, prod2, qty="200", unit_cost="8000")
        t_id = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders",
            headers={"Authorization": f"Bearer {token}"},
            json={"source_location_id": loc1, "destination_location_id": loc2},
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod1, "quantity": "10"},
        )
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod2, "quantity": "20"},
        )
        disp = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/dispatch",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert disp.status_code == 200
        assert len(disp.json()["lines"]) == 2
        assert _get_stock_qty(token, biz_id, loc1, prod1) == Decimal("90")
        assert _get_stock_qty(token, biz_id, loc1, prod2) == Decimal("180")
        recv = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/receive",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert recv.status_code == 200
        assert _get_stock_qty(token, biz_id, loc2, prod1) == Decimal("10")
        assert _get_stock_qty(token, biz_id, loc2, prod2) == Decimal("20")

    def test_cancel_after_dispatch_restores_cost_at_original_snapshot(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc1 = setup_warehouse_and_location(token, biz_id, name="WH1", code="W1", loc_name="L1", loc_code="C1")
        loc2 = setup_warehouse_and_location(token, biz_id, name="WH2", code="W2", loc_name="L2", loc_code="C2")
        add_opening_stock(token, biz_id, loc1, prod_id, qty="100", unit_cost="10000")
        t_id = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders",
            headers={"Authorization": f"Bearer {token}"},
            json={"source_location_id": loc1, "destination_location_id": loc2},
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": "30"},
        )
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/dispatch",
            headers={"Authorization": f"Bearer {token}"},
        )
        snap = client.get(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()["lines"][0]["unit_cost_snapshot"]
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )
        from app.modules.inventory.repository import inventory_cost_repository
        cs = inventory_cost_repository._cost_states.get(f"{biz_id}:{prod_id}:NONE")
        assert cs.quantity == Decimal("100")
        assert cs.total_cost == Decimal("1000000")
        assert cs.unit_cost == Decimal("10000")


class TestTransferAtomicity:

    def _snapshot_repos(self):
        from app.modules.inventory.repository import (
            stock_balance_repository, stock_movement_repository, inventory_cost_repository
        )
        return {
            "balances": {k: v.model_copy() for k, v in stock_balance_repository._balances.items()},
            "movements": {k: v.model_copy() for k, v in stock_movement_repository._movements.items()},
            "movement_lines": [l.model_copy() for l in stock_movement_repository._lines],
            "cost_states": {k: v.model_copy() for k, v in inventory_cost_repository._cost_states.items()},
            "cost_movements": [l.model_copy() for l in inventory_cost_repository._cost_movements],
        }

    def _assert_repos_unchanged(self, pre, post, msg=""):
        assert pre["balances"] == post["balances"], f"{msg}: balances"
        assert pre["movements"] == post["movements"], f"{msg}: movements"
        assert pre["movement_lines"] == post["movement_lines"], f"{msg}: movement_lines"
        assert pre["cost_states"] == post["cost_states"], f"{msg}: cost_states"
        assert pre["cost_movements"] == post["cost_movements"], f"{msg}: cost_movements"

    def test_atomicity_dispatch_stock_failure(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc1 = setup_warehouse_and_location(token, biz_id, name="WH1", code="W1", loc_name="L1", loc_code="C1")
        loc2 = setup_warehouse_and_location(token, biz_id, name="WH2", code="W2", loc_name="L2", loc_code="C2")
        add_opening_stock(token, biz_id, loc1, prod_id, qty="100", unit_cost="10000")
        t_id = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders",
            headers={"Authorization": f"Bearer {token}"},
            json={"source_location_id": loc1, "destination_location_id": loc2},
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": "25"},
        )
        pre = self._snapshot_repos()
        pre_tr = client.get(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        from app.modules.inventory.service import inventory_service
        async def bad_cost_out(*args, **kwargs):
            raise RuntimeError("INJECTED: dispatch cost failure")
        with patch.object(inventory_service, "record_cost_outbound", new=bad_cost_out):
            r = noclient.post(
                f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/dispatch",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r.status_code == 500
        post = self._snapshot_repos()
        self._assert_repos_unchanged(pre, post, "dispatch stock failure")
        post_tr = client.get(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        assert post_tr["status"] == "DRAFT"
        retry = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/dispatch",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert retry.status_code == 200
        assert retry.json()["status"] == "DISPATCHED"

    def test_atomicity_receive_stock_failure(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc1 = setup_warehouse_and_location(token, biz_id, name="WH1", code="W1", loc_name="L1", loc_code="C1")
        loc2 = setup_warehouse_and_location(token, biz_id, name="WH2", code="W2", loc_name="L2", loc_code="C2")
        add_opening_stock(token, biz_id, loc1, prod_id, qty="100", unit_cost="10000")
        t_id = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders",
            headers={"Authorization": f"Bearer {token}"},
            json={"source_location_id": loc1, "destination_location_id": loc2},
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": "25"},
        )
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/dispatch",
            headers={"Authorization": f"Bearer {token}"},
        )
        pre = self._snapshot_repos()
        from app.modules.inventory.service import inventory_service
        async def bad_cost_in(*args, **kwargs):
            raise RuntimeError("INJECTED: receive cost failure")
        with patch.object(inventory_service, "record_cost_inbound", new=bad_cost_in):
            r = noclient.post(
                f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/receive",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r.status_code == 500
        post = self._snapshot_repos()
        self._assert_repos_unchanged(pre, post, "receive cost failure")
        tr = client.get(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        assert tr["status"] == "DISPATCHED"
        retry = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/receive",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert retry.status_code == 200
        assert retry.json()["status"] == "RECEIVED"

    def test_atomicity_cancel_after_dispatch_failure(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc1 = setup_warehouse_and_location(token, biz_id, name="WH1", code="W1", loc_name="L1", loc_code="C1")
        loc2 = setup_warehouse_and_location(token, biz_id, name="WH2", code="W2", loc_name="L2", loc_code="C2")
        add_opening_stock(token, biz_id, loc1, prod_id, qty="100", unit_cost="10000")
        t_id = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders",
            headers={"Authorization": f"Bearer {token}"},
            json={"source_location_id": loc1, "destination_location_id": loc2},
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": "20"},
        )
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/dispatch",
            headers={"Authorization": f"Bearer {token}"},
        )
        pre = self._snapshot_repos()
        from app.modules.inventory.service import inventory_service
        async def bad_cancel_inbound(*args, **kwargs):
            raise RuntimeError("INJECTED: cancel cost failure")
        with patch.object(inventory_service, "record_cost_inbound", new=bad_cancel_inbound):
            r = noclient.post(
                f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/cancel",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r.status_code == 500
        post = self._snapshot_repos()
        self._assert_repos_unchanged(pre, post, "cancel cost failure")
        tr = client.get(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        assert tr["status"] == "DISPATCHED"
        retry = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert retry.status_code == 200
        assert retry.json()["status"] == "CANCELLED"

    def test_atomicity_dispatch_status_update_failure(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc1 = setup_warehouse_and_location(token, biz_id, name="WH1", code="W1", loc_name="L1", loc_code="C1")
        loc2 = setup_warehouse_and_location(token, biz_id, name="WH2", code="W2", loc_name="L2", loc_code="C2")
        add_opening_stock(token, biz_id, loc1, prod_id, qty="100", unit_cost="10000")
        t_id = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders",
            headers={"Authorization": f"Bearer {token}"},
            json={"source_location_id": loc1, "destination_location_id": loc2},
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": "15"},
        )
        pre = self._snapshot_repos()
        from app.modules.transfer.repository import transfer_repository
        orig_update = transfer_repository.update_transfer
        async def selective_fail(*args, **kwargs):
            if kwargs.get("status") is not None and kwargs["status"].value == "DISPATCHED":
                raise RuntimeError("INJECTED: status update failure")
            return await orig_update(*args, **kwargs)
        with patch.object(transfer_repository, "update_transfer", new=selective_fail):
            r = noclient.post(
                f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/dispatch",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r.status_code == 500
        post = self._snapshot_repos()
        self._assert_repos_unchanged(pre, post, "status update failure")
        tr = client.get(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        assert tr["status"] == "DRAFT"
        retry = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/dispatch",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert retry.status_code == 200


class TestTransferConcurrency:

    def test_concurrent_dispatch_serialized(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc1 = setup_warehouse_and_location(token, biz_id, name="WH1", code="W1", loc_name="L1", loc_code="C1")
        loc2 = setup_warehouse_and_location(token, biz_id, name="WH2", code="W2", loc_name="L2", loc_code="C2")
        add_opening_stock(token, biz_id, loc1, prod_id, qty="100", unit_cost="10000")
        t_id = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders",
            headers={"Authorization": f"Bearer {token}"},
            json={"source_location_id": loc1, "destination_location_id": loc2},
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": "10"},
        )
        results = []
        def attempt():
            c = TestClient(app)
            r = c.post(
                f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/dispatch",
                headers={"Authorization": f"Bearer {token}"},
            )
            results.append(r.status_code)
        t1 = threading.Thread(target=attempt)
        t2 = threading.Thread(target=attempt)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        assert results.count(200) == 1
        tr = client.get(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        assert tr["status"] == "DISPATCHED"

    def test_concurrent_receive_serialized(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc1 = setup_warehouse_and_location(token, biz_id, name="WH1", code="W1", loc_name="L1", loc_code="C1")
        loc2 = setup_warehouse_and_location(token, biz_id, name="WH2", code="W2", loc_name="L2", loc_code="C2")
        add_opening_stock(token, biz_id, loc1, prod_id, qty="100", unit_cost="10000")
        t_id = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders",
            headers={"Authorization": f"Bearer {token}"},
            json={"source_location_id": loc1, "destination_location_id": loc2},
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": "10"},
        )
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/dispatch",
            headers={"Authorization": f"Bearer {token}"},
        )
        results = []
        def attempt():
            c = TestClient(app)
            r = c.post(
                f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}/receive",
                headers={"Authorization": f"Bearer {token}"},
            )
            results.append(r.status_code)
        t1 = threading.Thread(target=attempt)
        t2 = threading.Thread(target=attempt)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        assert results.count(200) == 1
        tr = client.get(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t_id}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        assert tr["status"] == "RECEIVED"

    def test_competing_transfers_same_source_stock(self):
        token, _ = register_user()
        biz_id = create_business(token)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc1 = setup_warehouse_and_location(token, biz_id, name="WH1", code="W1", loc_name="L1", loc_code="C1")
        loc2 = setup_warehouse_and_location(token, biz_id, name="WH2", code="W2", loc_name="L2", loc_code="C2")
        add_opening_stock(token, biz_id, loc1, prod_id, qty="20", unit_cost="10000")
        t1_id = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders",
            headers={"Authorization": f"Bearer {token}"},
            json={"source_location_id": loc1, "destination_location_id": loc2},
        ).json()["id"]
        t2_id = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders",
            headers={"Authorization": f"Bearer {token}"},
            json={"source_location_id": loc1, "destination_location_id": loc2},
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t1_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": "15"},
        )
        client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t2_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": "15"},
        )
        r1 = client.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t1_id}/dispatch",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r1.status_code == 200
        r2 = noclient.post(
            f"/api/v1/businesses/{biz_id}/transfer-orders/{t2_id}/dispatch",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r2.status_code == 400
        assert "Insufficient stock" in r2.json()["message"]

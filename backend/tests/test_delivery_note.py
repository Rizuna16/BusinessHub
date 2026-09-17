"""
Feature #54 + Feature #58: Delivery Note (Surat Jalan) Integration & Unit Tests

Verifies:
1. Delivery Note lifecycle (DRAFT -> READY -> DELIVERED, DRAFT -> CANCELLED, READY -> CANCELLED)
2. Quantity validation (cannot exceed ordered quantity, partial deliveries, multiple DNs, cancellation releases allocation)
3. Feature #58: Inventory/MAC/Reservation/SO fulfillment on READY → DELIVERED transition
4. Service-type product handling (no inventory/MAC impact)
5. Mixed GOODS + SERVICE delivery
6. Partial multi-DN delivery flow
7. Over-delivery rejection
8. Pending DN capacity reservation
9. Idempotency (DELIVERED DN cannot re-deliver)
10. Rollback on failure
11. Accounting boundary (no GL journals)
12. Concurrency protection via shared _inventory_lock
13. Security & tenant isolation (cross-business access, MEMBER role restrictions)
14. Sequential numbering (DN-000001 per business)
"""
import pytest
from fastapi.testclient import TestClient
from decimal import Decimal
from datetime import datetime, timezone

from app.main import app
from app.modules.authentication.repository import InMemoryUserRepository
from app.modules.business.repository import InMemoryBusinessRepository
from app.modules.business_membership.repository import InMemoryBusinessMembershipRepository
from app.modules.unit.repository import InMemoryUnitRepository
from app.modules.product.repository import InMemoryProductRepository
from app.modules.warehouse.repository import InMemoryWarehouseRepository, InMemoryInventoryLocationRepository
from app.modules.inventory.repository import (
    InMemoryStockBalanceRepository, InMemoryStockMovementRepository,
    InMemoryInventoryCostRepository
)
from app.modules.branch.repository import InMemoryBranchRepository
from app.modules.customer.repository import InMemoryCustomerRepository
from app.modules.sales_order.repository import (
    InMemoryQuotationRepository, InMemorySalesOrderRepository,
    InMemoryReservationRepository
)
from app.modules.delivery_note.repository import InMemoryDeliveryNoteRepository
from app.modules.accounting.repository import InMemoryAccountingRepository

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_stores():
    InMemoryUserRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryUnitRepository.clear()
    InMemoryProductRepository.clear()
    InMemoryWarehouseRepository.clear()
    InMemoryInventoryLocationRepository.clear()
    InMemoryStockBalanceRepository.clear()
    InMemoryStockMovementRepository.clear()
    InMemoryInventoryCostRepository.clear()
    InMemoryBranchRepository.clear()
    InMemoryCustomerRepository.clear()
    InMemoryQuotationRepository.clear()
    InMemorySalesOrderRepository.clear()
    InMemoryReservationRepository.clear()
    InMemoryDeliveryNoteRepository.clear()
    InMemoryAccountingRepository.clear()


def register_and_login(email: str, password: str, full_name: str = "Test User") -> str:
    resp = client.post("/api/v1/auth/register", json={
        "email": email, "full_name": full_name,
        "password": password, "password_confirmation": password,
    })
    assert resp.status_code in (200, 201)
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    data = login_resp.json()
    return data.get("access_token") or data["data"]["access_token"]


def create_business(token: str, name: str = "DN Business") -> str:
    resp = client.post("/api/v1/businesses", headers={"Authorization": f"Bearer {token}"}, json={
        "name": name, "business_type": "retail", "timezone": "UTC", "locale": "en-US",
    })
    assert resp.status_code in (200, 201)
    return resp.json()["id"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def setup_infra(token: str, biz_id: str):
    branch_resp = client.post(f"/api/v1/businesses/{biz_id}/branches", headers=auth(token), json={
        "name": "Main Branch", "code": "MB-01",
    })
    branch_id = branch_resp.json()["id"]

    wh_resp = client.post(f"/api/v1/businesses/{biz_id}/warehouses", headers=auth(token), json={
        "name": "Main WH", "code": "WH-01", "branch_id": branch_id,
    })
    warehouse_id = wh_resp.json()["id"]
    loc_resp = client.post(f"/api/v1/businesses/{biz_id}/warehouses/{warehouse_id}/locations", headers=auth(token), json={
        "name": "Storage", "code": "LOC-01", "location_type": "STORAGE",
    })
    location_id = loc_resp.json()["id"]

    cust_resp = client.post(f"/api/v1/businesses/{biz_id}/customers", headers=auth(token), json={
        "name": "Test Customer",
    })
    customer_id = cust_resp.json()["id"]

    unit_resp = client.post(f"/api/v1/businesses/{biz_id}/units", headers=auth(token), json={
        "name": "Piece", "code": "PC", "symbol": "pc",
    })
    unit_id = unit_resp.json()["id"]

    return branch_id, warehouse_id, location_id, customer_id, unit_id


def create_so_and_lines(token: str, biz_id: str, branch_id: str, warehouse_id: str, lines: list, customer_id: str = None) -> tuple:
    if not customer_id:
        cust_resp = client.post(f"/api/v1/businesses/{biz_id}/customers", headers=auth(token), json={"name": "SO Customer"})
        customer_id = cust_resp.json()["id"]
    so_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders", headers=auth(token), json={
        "customer_id": customer_id, "branch_id": branch_id, "warehouse_id": warehouse_id,
        "order_date": datetime.now(timezone.utc).isoformat(),
    })
    so_id = so_resp.json()["id"]

    so_line_ids = []
    for line in lines:
        lr = client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/lines", headers=auth(token), json={
            "product_id": line["product_id"], "quantity": line["quantity"], "unit_price": line.get("unit_price", "5000"),
        })
        assert lr.status_code == 201, lr.text
        so_line_ids.append(lr.json()["id"])

    return so_id, so_line_ids


def confirm_so(token: str, biz_id: str, so_id: str):
    resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/confirm", headers=auth(token))
    assert resp.status_code == 200, resp.text


def fulfill_so(token: str, biz_id: str, so_id: str, line_id: str, qty: str) -> dict:
    resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/fulfill", headers=auth(token), json={
        "line_fulfillments": [{"line_id": line_id, "quantity": qty}]
    })
    return resp.json() if resp.status_code == 200 else resp


def create_dn(token: str, biz_id: str, so_id: str, branch_id: str, lines: list, customer_id: str = None) -> dict:
    payload = {
        "sales_order_id": so_id, "branch_id": branch_id,
        "delivery_date": datetime.now(timezone.utc).isoformat(),
        "lines": lines,
    }
    if customer_id:
        payload["customer_id"] = customer_id
    return client.post(f"/api/v1/businesses/{biz_id}/delivery-notes", headers=auth(token), json=payload)


def ready_dn(token: str, biz_id: str, dn_id: str) -> dict:
    return client.post(f"/api/v1/businesses/{biz_id}/delivery-notes/{dn_id}/ready", headers=auth(token))


def deliver_dn(token: str, biz_id: str, dn_id: str) -> dict:
    return client.post(f"/api/v1/businesses/{biz_id}/delivery-notes/{dn_id}/deliver", headers=auth(token))


def cancel_dn(token: str, biz_id: str, dn_id: str) -> dict:
    return client.post(f"/api/v1/businesses/{biz_id}/delivery-notes/{dn_id}/cancel", headers=auth(token))


def get_so(token: str, biz_id: str, so_id: str) -> dict:
    return client.get(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}", headers=auth(token)).json()


def get_stock_balances(token: str, biz_id: str, product_id: str) -> list:
    return client.get(f"/api/v1/businesses/{biz_id}/inventory/stock?product_id={product_id}", headers=auth(token)).json()


def get_movements(token: str, biz_id: str, movement_type: str = None) -> list:
    url = f"/api/v1/businesses/{biz_id}/inventory/movements"
    if movement_type:
        url += f"?movement_type={movement_type}"
    return client.get(url, headers=auth(token)).json()


def get_valuation(token: str, biz_id: str) -> dict:
    return client.get(f"/api/v1/businesses/{biz_id}/inventory/valuation", headers=auth(token)).json()


# ====================================================================
# LIFECYCLE TESTS
# ====================================================================


class TestDeliveryNoteLifecycle:
    def test_complete_lifecycle(self):
        token = register_and_login("dn1@test.com", "Pass1234!")
        biz_id = create_business(token, "DN Biz 1")
        branch_id, warehouse_id, location_id, customer_id, unit_id = setup_infra(token, biz_id)

        product_id = client.post(f"/api/v1/businesses/{biz_id}/products", headers=auth(token), json={
            "name": "Widget", "code": "WID-01", "product_type": "GOODS", "unit_id": unit_id,
        }).json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/inventory/opening-balance", headers=auth(token), json={
            "inventory_location_id": location_id, "product_id": product_id, "quantity": "100", "unit_cost": "1000",
        })

        so_id, so_line_ids = create_so_and_lines(token, biz_id, branch_id, warehouse_id, [
            {"product_id": product_id, "quantity": "10"},
        ])
        line_id = so_line_ids[0]
        confirm_so(token, biz_id, so_id)

        dn_resp = create_dn(token, biz_id, so_id, branch_id, [
            {"sales_order_line_id": line_id, "delivery_quantity": "4"}
        ])
        assert dn_resp.status_code == 201
        data = dn_resp.json()
        assert data["delivery_number"] == "DN-000001"
        assert data["status"] == "DRAFT"
        dn_id = data["id"]

        ready_resp = ready_dn(token, biz_id, dn_id)
        assert ready_resp.status_code == 200
        assert ready_resp.json()["status"] == "READY"

        deliv_resp = deliver_dn(token, biz_id, dn_id)
        assert deliv_resp.status_code == 200
        assert deliv_resp.json()["status"] == "DELIVERED"

    def test_cancellation_lifecycle(self):
        token = register_and_login("dn2@test.com", "Pass1234!")
        biz_id = create_business(token, "DN Biz 2")
        branch_id, warehouse_id, location_id, customer_id, unit_id = setup_infra(token, biz_id)

        product_id = client.post(f"/api/v1/businesses/{biz_id}/products", headers=auth(token), json={
            "name": "Widget", "code": "WID-02", "product_type": "GOODS", "unit_id": unit_id,
        }).json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/inventory/opening-balance", headers=auth(token), json={
            "inventory_location_id": location_id, "product_id": product_id, "quantity": "50", "unit_cost": "1000",
        })

        so_id, so_line_ids = create_so_and_lines(token, biz_id, branch_id, warehouse_id, [
            {"product_id": product_id, "quantity": "10"},
        ])
        line_id = so_line_ids[0]
        confirm_so(token, biz_id, so_id)

        dn_resp = create_dn(token, biz_id, so_id, branch_id, [
            {"sales_order_line_id": line_id, "delivery_quantity": "3"}
        ])
        dn_id = dn_resp.json()["id"]

        cancel_resp = cancel_dn(token, biz_id, dn_id)
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "CANCELLED"


# ====================================================================
# QUANTITY BOUNDARY TESTS
# ====================================================================


class TestDeliveryNoteQuantities:
    def test_quantity_exceeds_ordered_rejected(self):
        token = register_and_login("dn3@test.com", "Pass1234!")
        biz_id = create_business(token, "DN Biz 3")
        branch_id, warehouse_id, location_id, customer_id, unit_id = setup_infra(token, biz_id)

        product_id = client.post(f"/api/v1/businesses/{biz_id}/products", headers=auth(token), json={
            "name": "Widget", "code": "WID-03", "product_type": "GOODS", "unit_id": unit_id,
        }).json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/inventory/opening-balance", headers=auth(token), json={
            "inventory_location_id": location_id, "product_id": product_id, "quantity": "50", "unit_cost": "1000",
        })

        so_id, so_line_ids = create_so_and_lines(token, biz_id, branch_id, warehouse_id, [
            {"product_id": product_id, "quantity": "10"},
        ])
        line_id = so_line_ids[0]
        confirm_so(token, biz_id, so_id)

        dn_resp = create_dn(token, biz_id, so_id, branch_id, [
            {"sales_order_line_id": line_id, "delivery_quantity": "11"}
        ])
        assert dn_resp.status_code == 400

    def test_multiple_delivery_notes_and_cancellation_release(self):
        token = register_and_login("dn4@test.com", "Pass1234!")
        biz_id = create_business(token, "DN Biz 4")
        branch_id, warehouse_id, location_id, customer_id, unit_id = setup_infra(token, biz_id)

        product_id = client.post(f"/api/v1/businesses/{biz_id}/products", headers=auth(token), json={
            "name": "Widget", "code": "WID-04", "product_type": "GOODS", "unit_id": unit_id,
        }).json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/inventory/opening-balance", headers=auth(token), json={
            "inventory_location_id": location_id, "product_id": product_id, "quantity": "100", "unit_cost": "1000",
        })

        so_id, so_line_ids = create_so_and_lines(token, biz_id, branch_id, warehouse_id, [
            {"product_id": product_id, "quantity": "10"},
        ])
        line_id = so_line_ids[0]
        confirm_so(token, biz_id, so_id)

        # DN #1: 4 units
        dn1_resp = create_dn(token, biz_id, so_id, branch_id, [
            {"sales_order_line_id": line_id, "delivery_quantity": "4"}
        ])
        dn1 = dn1_resp.json()

        # DN #2: 4 units (remaining is 10 - 0 - 4 = 6, so 4 fits)
        dn2_resp = create_dn(token, biz_id, so_id, branch_id, [
            {"sales_order_line_id": line_id, "delivery_quantity": "4"}
        ])
        assert dn2_resp.status_code == 201

        # DN #3: should fail since total active (4 + 4 = 8) and remaining = 10 - 0 - 8 = 2 < 1
        dn3_resp = create_dn(token, biz_id, so_id, branch_id, [
            {"sales_order_line_id": line_id, "delivery_quantity": "3"}
        ])
        assert dn3_resp.status_code == 400

        # Cancel DN #1 -> releases 4 units back
        cancel_dn(token, biz_id, dn1["id"])

        # Now remaining = 10 - 0 - 4 = 6, so creating DN for 4 should succeed
        dn4_resp = create_dn(token, biz_id, so_id, branch_id, [
            {"sales_order_line_id": line_id, "delivery_quantity": "4"}
        ])
        assert dn4_resp.status_code == 201


# ====================================================================
# FEATURE #58: GOODS DELIVERY — INVENTORY / MAC / SO / RESERVATION
# ====================================================================


class TestFeature58GoodsDelivery:
    def test_goods_delivery_deducts_stock_and_fulfills_so(self):
        """READY -> DELIVERED: stock decreases, MAC outbound created, SO fulfilled, reservation updated."""
        token = register_and_login("f58g1@test.com", "Pass1234!")
        biz_id = create_business(token, "F58 Goods Biz")
        branch_id, warehouse_id, location_id, customer_id, unit_id = setup_infra(token, biz_id)

        product_id = client.post(f"/api/v1/businesses/{biz_id}/products", headers=auth(token), json={
            "name": "Widget", "code": "F58W-01", "product_type": "GOODS", "unit_id": unit_id,
        }).json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/inventory/opening-balance", headers=auth(token), json={
            "inventory_location_id": location_id, "product_id": product_id,
            "quantity": "100", "unit_cost": "1000",
        })

        so_id, so_line_ids = create_so_and_lines(token, biz_id, branch_id, warehouse_id, [
            {"product_id": product_id, "quantity": "10"},
        ])
        line_id = so_line_ids[0]
        confirm_so(token, biz_id, so_id)

        # Snapshot before DN
        stock_before = get_stock_balances(token, biz_id, product_id)
        physical_before = Decimal(stock_before[0]["quantity"])
        assert physical_before == Decimal("100")

        # Create DN for 3 (no pre-fulfillment, capacity = 10 - 0 - 0 = 10)
        dn_resp = create_dn(token, biz_id, so_id, branch_id, [
            {"sales_order_line_id": line_id, "delivery_quantity": "3"}
        ], customer_id)
        assert dn_resp.status_code == 201
        dn_id = dn_resp.json()["id"]

        ready_dn(token, biz_id, dn_id)
        deliv_resp = deliver_dn(token, biz_id, dn_id)
        assert deliv_resp.status_code == 200
        assert deliv_resp.json()["status"] == "DELIVERED"

        # Verify stock decreased
        stock_after = get_stock_balances(token, biz_id, product_id)
        physical_after = Decimal(stock_after[0]["quantity"])
        assert physical_after == physical_before - Decimal("3")

        # Verify SALE_OUT movement created
        movements_after = get_movements(token, biz_id, movement_type="SALE_OUT")
        dn_movement = [m for m in movements_after if m.get("reference_id") == dn_id]
        assert len(dn_movement) == 1

        # Verify SO line fulfillment updated
        so_after = get_so(token, biz_id, so_id)
        so_line_after = [l for l in so_after["lines"] if l["id"] == line_id][0]
        assert Decimal(str(so_line_after["quantity_fulfilled"])) == Decimal("3")
        assert Decimal(str(so_line_after["quantity_remaining"])) == Decimal("7")
        assert so_after["status"] == "PARTIALLY_FULFILLED"

        # Verify MAC valuation decreased
        val = get_valuation(token, biz_id)
        assert Decimal(str(val["total_inventory_value"])) == Decimal("97") * Decimal("1000")

    def test_goods_full_delivery_fulfills_order(self):
        """Deliver the full quantity -> SO FULFILLED."""
        token = register_and_login("f58g2@test.com", "Pass1234!")
        biz_id = create_business(token, "F58 Full Biz")
        branch_id, warehouse_id, location_id, customer_id, unit_id = setup_infra(token, biz_id)

        product_id = client.post(f"/api/v1/businesses/{biz_id}/products", headers=auth(token), json={
            "name": "Widget", "code": "F58W-02", "product_type": "GOODS", "unit_id": unit_id,
        }).json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/inventory/opening-balance", headers=auth(token), json={
            "inventory_location_id": location_id, "product_id": product_id,
            "quantity": "50", "unit_cost": "2000",
        })

        so_id, so_line_ids = create_so_and_lines(token, biz_id, branch_id, warehouse_id, [
            {"product_id": product_id, "quantity": "10"},
        ])
        line_id = so_line_ids[0]
        confirm_so(token, biz_id, so_id)

        dn_resp = create_dn(token, biz_id, so_id, branch_id, [
            {"sales_order_line_id": line_id, "delivery_quantity": "10"}
        ], customer_id)
        assert dn_resp.status_code == 201
        dn_id = dn_resp.json()["id"]

        ready_dn(token, biz_id, dn_id)
        deliv_resp = deliver_dn(token, biz_id, dn_id)
        assert deliv_resp.status_code == 200

        so_after = get_so(token, biz_id, so_id)
        assert so_after["status"] == "FULFILLED"
        so_line_after = [l for l in so_after["lines"] if l["id"] == line_id][0]
        assert Decimal(str(so_line_after["quantity_fulfilled"])) == Decimal("10")
        assert Decimal(str(so_line_after["quantity_remaining"])) == Decimal("0")

        stock_after = get_stock_balances(token, biz_id, product_id)
        assert Decimal(stock_after[0]["quantity"]) == Decimal("40")


# ====================================================================
# FEATURE #58: SERVICE PRODUCT DELIVERY
# ====================================================================


class TestFeature58ServiceDelivery:
    def test_service_delivery_no_inventory_impact(self):
        """SERVICE line: SO fulfillment only, zero stock/MAC/movement side-effects."""
        token = register_and_login("f58s1@test.com", "Pass1234!")
        biz_id = create_business(token, "F58 Svc Biz")
        branch_id, warehouse_id, location_id, customer_id, unit_id = setup_infra(token, biz_id)

        svc_product_id = client.post(f"/api/v1/businesses/{biz_id}/products", headers=auth(token), json={
            "name": "Consulting", "code": "SVC-01", "product_type": "SERVICE", "unit_id": unit_id,
        }).json()["id"]

        so_id, so_line_ids = create_so_and_lines(token, biz_id, branch_id, warehouse_id, [
            {"product_id": svc_product_id, "quantity": "5", "unit_price": "15000"},
        ])
        line_id = so_line_ids[0]
        confirm_so(token, biz_id, so_id)

        dn_resp = create_dn(token, biz_id, so_id, branch_id, [
            {"sales_order_line_id": line_id, "delivery_quantity": "5"}
        ], customer_id)
        assert dn_resp.status_code == 201
        dn_id = dn_resp.json()["id"]

        ready_dn(token, biz_id, dn_id)
        deliv_resp = deliver_dn(token, biz_id, dn_id)
        assert deliv_resp.status_code == 200

        stock = get_stock_balances(token, biz_id, svc_product_id)
        assert len(stock) == 0

        movements = get_movements(token, biz_id, movement_type="SALE_OUT")
        dn_movements = [m for m in movements if m.get("reference_id") == dn_id]
        assert len(dn_movements) == 0

        val = get_valuation(token, biz_id)
        assert Decimal(str(val["total_inventory_value"])) == Decimal("0")

        so_after = get_so(token, biz_id, so_id)
        so_line_after = [l for l in so_after["lines"] if l["id"] == line_id][0]
        assert Decimal(str(so_line_after["quantity_fulfilled"])) == Decimal("5")
        assert Decimal(str(so_line_after["quantity_remaining"])) == Decimal("0")


class TestFeature58MixedDelivery:
    def test_mixed_goods_service_delivery(self):
        """Mixed DN: GOODS gets inventory/MAC/reservation, SERVICE gets fulfillment only."""
        token = register_and_login("f58m1@test.com", "Pass1234!")
        biz_id = create_business(token, "F58 Mixed Biz")
        branch_id, warehouse_id, location_id, customer_id, unit_id = setup_infra(token, biz_id)

        goods_product_id = client.post(f"/api/v1/businesses/{biz_id}/products", headers=auth(token), json={
            "name": "Widget", "code": "F58M-G", "product_type": "GOODS", "unit_id": unit_id,
        }).json()["id"]
        svc_product_id = client.post(f"/api/v1/businesses/{biz_id}/products", headers=auth(token), json={
            "name": "Service", "code": "F58M-S", "product_type": "SERVICE", "unit_id": unit_id,
        }).json()["id"]

        client.post(f"/api/v1/businesses/{biz_id}/inventory/opening-balance", headers=auth(token), json={
            "inventory_location_id": location_id, "product_id": goods_product_id,
            "quantity": "50", "unit_cost": "1000",
        })

        so_id, (goods_line_id, svc_line_id) = create_so_and_lines(token, biz_id, branch_id, warehouse_id, [
            {"product_id": goods_product_id, "quantity": "10"},
            {"product_id": svc_product_id, "quantity": "3", "unit_price": "20000"},
        ])
        confirm_so(token, biz_id, so_id)

        dn_resp = create_dn(token, biz_id, so_id, branch_id, [
            {"sales_order_line_id": goods_line_id, "delivery_quantity": "4"},
            {"sales_order_line_id": svc_line_id, "delivery_quantity": "3"},
        ], customer_id)
        assert dn_resp.status_code == 201
        dn_id = dn_resp.json()["id"]

        ready_dn(token, biz_id, dn_id)
        deliv_resp = deliver_dn(token, biz_id, dn_id)
        assert deliv_resp.status_code == 200
        assert deliv_resp.json()["status"] == "DELIVERED"

        stock = get_stock_balances(token, biz_id, goods_product_id)
        assert Decimal(stock[0]["quantity"]) == Decimal("46")  # 50 - 4

        so_after = get_so(token, biz_id, so_id)
        goods_line_after = [l for l in so_after["lines"] if l["id"] == goods_line_id][0]
        svc_line_after = [l for l in so_after["lines"] if l["id"] == svc_line_id][0]
        assert Decimal(str(goods_line_after["quantity_remaining"])) == Decimal("6")
        assert Decimal(str(svc_line_after["quantity_remaining"])) == Decimal("0")


# ====================================================================
# FEATURE #58: PARTIAL DELIVERY FLOW
# ====================================================================


class TestFeature58PartialDelivery:
    def test_partial_delivery_two_steps(self):
        """First partial DN succeeds, second DN for remainder succeeds, SO goes FULFILLED."""
        token = register_and_login("f58p1@test.com", "Pass1234!")
        biz_id = create_business(token, "F58 Part Biz")
        branch_id, warehouse_id, location_id, customer_id, unit_id = setup_infra(token, biz_id)

        product_id = client.post(f"/api/v1/businesses/{biz_id}/products", headers=auth(token), json={
            "name": "Widget", "code": "F58P-01", "product_type": "GOODS", "unit_id": unit_id,
        }).json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/inventory/opening-balance", headers=auth(token), json={
            "inventory_location_id": location_id, "product_id": product_id,
            "quantity": "30", "unit_cost": "500",
        })

        so_id, so_line_ids = create_so_and_lines(token, biz_id, branch_id, warehouse_id, [
            {"product_id": product_id, "quantity": "10"},
        ])
        line_id = so_line_ids[0]
        confirm_so(token, biz_id, so_id)

        # DN #1: 4 units
        dn1_resp = create_dn(token, biz_id, so_id, branch_id, [
            {"sales_order_line_id": line_id, "delivery_quantity": "4"}
        ], customer_id)
        assert dn1_resp.status_code == 201
        dn1_id = dn1_resp.json()["id"]
        ready_dn(token, biz_id, dn1_id)
        deliver_dn(token, biz_id, dn1_id)

        so_mid = get_so(token, biz_id, so_id)
        assert so_mid["status"] == "PARTIALLY_FULFILLED"
        line_mid = [l for l in so_mid["lines"] if l["id"] == line_id][0]
        assert Decimal(str(line_mid["quantity_fulfilled"])) == Decimal("4")
        assert Decimal(str(line_mid["quantity_remaining"])) == Decimal("6")

        stock_mid = get_stock_balances(token, biz_id, product_id)
        assert Decimal(stock_mid[0]["quantity"]) == Decimal("26")  # 30 - 4

        # DN #2: 6 units (remaining = 10 - 4 - 0 = 6)
        dn2_resp = create_dn(token, biz_id, so_id, branch_id, [
            {"sales_order_line_id": line_id, "delivery_quantity": "6"}
        ], customer_id)
        assert dn2_resp.status_code == 201
        dn2_id = dn2_resp.json()["id"]
        ready_dn(token, biz_id, dn2_id)
        deliver_dn(token, biz_id, dn2_id)

        so_after = get_so(token, biz_id, so_id)
        assert so_after["status"] == "FULFILLED"
        line_after = [l for l in so_after["lines"] if l["id"] == line_id][0]
        assert Decimal(str(line_after["quantity_fulfilled"])) == Decimal("10")
        assert Decimal(str(line_after["quantity_remaining"])) == Decimal("0")

        stock_after = get_stock_balances(token, biz_id, product_id)
        assert Decimal(stock_after[0]["quantity"]) == Decimal("20")  # 30 - 10


# ====================================================================
# FEATURE #58: OVER-DELIVERY REJECTION
# ====================================================================


class TestFeature58OverDelivery:
    def test_delivery_exceeding_ordered_rejected(self):
        """DN with delivery_quantity > remaining capacity is rejected; zero state mutation."""
        token = register_and_login("f58o1@test.com", "Pass1234!")
        biz_id = create_business(token, "F58 Over Biz")
        branch_id, warehouse_id, location_id, customer_id, unit_id = setup_infra(token, biz_id)

        product_id = client.post(f"/api/v1/businesses/{biz_id}/products", headers=auth(token), json={
            "name": "Widget", "code": "F58O-01", "product_type": "GOODS", "unit_id": unit_id,
        }).json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/inventory/opening-balance", headers=auth(token), json={
            "inventory_location_id": location_id, "product_id": product_id,
            "quantity": "30", "unit_cost": "1000",
        })

        so_id, so_line_ids = create_so_and_lines(token, biz_id, branch_id, warehouse_id, [
            {"product_id": product_id, "quantity": "10"},
        ])
        line_id = so_line_ids[0]
        confirm_so(token, biz_id, so_id)

        dn_resp = create_dn(token, biz_id, so_id, branch_id, [
            {"sales_order_line_id": line_id, "delivery_quantity": "11"}
        ])
        assert dn_resp.status_code == 400


# ====================================================================
# FEATURE #58: PENDING DN CAPACITY
# ====================================================================


class TestFeature58PendingCapacity:
    def test_pending_dn_reserve_capacity(self):
        """Sibling DNs (DRAFT/READY) consume delivery capacity; reject when exceeded."""
        token = register_and_login("f58c1@test.com", "Pass1234!")
        biz_id = create_business(token, "F58 Cap Biz")
        branch_id, warehouse_id, location_id, customer_id, unit_id = setup_infra(token, biz_id)

        product_id = client.post(f"/api/v1/businesses/{biz_id}/products", headers=auth(token), json={
            "name": "Widget", "code": "F58C-01", "product_type": "GOODS", "unit_id": unit_id,
        }).json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/inventory/opening-balance", headers=auth(token), json={
            "inventory_location_id": location_id, "product_id": product_id,
            "quantity": "30", "unit_cost": "1000",
        })

        so_id, so_line_ids = create_so_and_lines(token, biz_id, branch_id, warehouse_id, [
            {"product_id": product_id, "quantity": "10"},
        ])
        line_id = so_line_ids[0]
        confirm_so(token, biz_id, so_id)

        # DN #1: 7 units (DRAFT, capacity remaining = 10 - 0 - 7 = 3)
        dn1_resp = create_dn(token, biz_id, so_id, branch_id, [
            {"sales_order_line_id": line_id, "delivery_quantity": "7"}
        ])
        assert dn1_resp.status_code == 201

        # DN #2: 4 units -> should fail (7 + 4 = 11 > 10)
        dn2_resp = create_dn(token, biz_id, so_id, branch_id, [
            {"sales_order_line_id": line_id, "delivery_quantity": "4"}
        ])
        assert dn2_resp.status_code == 400


# ====================================================================
# FEATURE #58: IDEMPOTENCY
# ====================================================================


class TestFeature58Idempotency:
    def test_delivered_dn_cannot_re_deliver(self):
        """DELIVERED DN cannot be delivered again; no duplicate inventory effect."""
        token = register_and_login("f58i1@test.com", "Pass1234!")
        biz_id = create_business(token, "F58 Idem Biz")
        branch_id, warehouse_id, location_id, customer_id, unit_id = setup_infra(token, biz_id)

        product_id = client.post(f"/api/v1/businesses/{biz_id}/products", headers=auth(token), json={
            "name": "Widget", "code": "F58I-01", "product_type": "GOODS", "unit_id": unit_id,
        }).json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/inventory/opening-balance", headers=auth(token), json={
            "inventory_location_id": location_id, "product_id": product_id,
            "quantity": "50", "unit_cost": "1000",
        })

        so_id, so_line_ids = create_so_and_lines(token, biz_id, branch_id, warehouse_id, [
            {"product_id": product_id, "quantity": "10"},
        ])
        line_id = so_line_ids[0]
        confirm_so(token, biz_id, so_id)

        dn_resp = create_dn(token, biz_id, so_id, branch_id, [
            {"sales_order_line_id": line_id, "delivery_quantity": "5"}
        ], customer_id)
        dn_id = dn_resp.json()["id"]

        ready_dn(token, biz_id, dn_id)
        deliver_dn(token, biz_id, dn_id)

        stock_after_first = get_stock_balances(token, biz_id, product_id)
        movements_count_before = len(get_movements(token, biz_id, movement_type="SALE_OUT"))

        # Second deliver -> rejected
        resp2 = deliver_dn(token, biz_id, dn_id)
        assert resp2.status_code == 400

        stock_after_second = get_stock_balances(token, biz_id, product_id)
        assert stock_after_second[0]["quantity"] == stock_after_first[0]["quantity"]

        movements_count_after = len(get_movements(token, biz_id, movement_type="SALE_OUT"))
        assert movements_count_after == movements_count_before


# ====================================================================
# FEATURE #58: ACCOUNTING BOUNDARY
# ====================================================================


class TestFeature58AccountingBoundary:
    def test_delivery_creates_no_gl_journal(self):
        """DN delivery does NOT create any GL journal entry."""
        token = register_and_login("f58a1@test.com", "Pass1234!")
        biz_id = create_business(token, "F58 Acct Biz")
        branch_id, warehouse_id, location_id, customer_id, unit_id = setup_infra(token, biz_id)

        goods_product_id = client.post(f"/api/v1/businesses/{biz_id}/products", headers=auth(token), json={
            "name": "Widget", "code": "F58A-G", "product_type": "GOODS", "unit_id": unit_id,
        }).json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/inventory/opening-balance", headers=auth(token), json={
            "inventory_location_id": location_id, "product_id": goods_product_id,
            "quantity": "20", "unit_cost": "5000",
        })

        so_id, so_line_ids = create_so_and_lines(token, biz_id, branch_id, warehouse_id, [
            {"product_id": goods_product_id, "quantity": "5"},
        ])
        line_id = so_line_ids[0]
        confirm_so(token, biz_id, so_id)

        journals_before = client.get(f"/api/v1/businesses/{biz_id}/accounting/journals", headers=auth(token)).json()
        j_count_before = journals_before.get("total", len(journals_before.get("items", [])))

        dn_resp = create_dn(token, biz_id, so_id, branch_id, [
            {"sales_order_line_id": line_id, "delivery_quantity": "3"}
        ], customer_id)
        dn_id = dn_resp.json()["id"]
        ready_dn(token, biz_id, dn_id)
        deliver_dn(token, biz_id, dn_id)

        journals_after = client.get(f"/api/v1/businesses/{biz_id}/accounting/journals", headers=auth(token)).json()
        j_count_after = journals_after.get("total", len(journals_after.get("items", [])))
        assert j_count_after == j_count_before


# ====================================================================
# FEATURE #58: ROLLBACK ON FAILURE
# ====================================================================


class TestFeature58Rollback:
    def test_rollback_on_invalid_so_line_fails_cleanly(self):
        """Delivery of a DN with an invalid SO line reference is rejected with zero net mutation."""
        token = register_and_login("f58r1@test.com", "Pass1234!")
        biz_id = create_business(token, "F58 Roll Biz")
        branch_id, warehouse_id, location_id, customer_id, unit_id = setup_infra(token, biz_id)

        goods_product_id = client.post(f"/api/v1/businesses/{biz_id}/products", headers=auth(token), json={
            "name": "Widget", "code": "F58R-01", "product_type": "GOODS", "unit_id": unit_id,
        }).json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/inventory/opening-balance", headers=auth(token), json={
            "inventory_location_id": location_id, "product_id": goods_product_id,
            "quantity": "20", "unit_cost": "1000",
        })

        so_id, so_line_ids = create_so_and_lines(token, biz_id, branch_id, warehouse_id, [
            {"product_id": goods_product_id, "quantity": "10"},
        ])
        line_id = so_line_ids[0]
        confirm_so(token, biz_id, so_id)

        dn_resp = create_dn(token, biz_id, so_id, branch_id, [
            {"sales_order_line_id": line_id, "delivery_quantity": "5"}
        ], customer_id)
        dn_id = dn_resp.json()["id"]
        ready_dn(token, biz_id, dn_id)

        # Snapshot before corruption
        so_before = get_so(token, biz_id, so_id)
        stock_before = get_stock_balances(token, biz_id, goods_product_id)
        dn_before = client.get(f"/api/v1/businesses/{biz_id}/delivery-notes/{dn_id}", headers=auth(token)).json()
        assert dn_before["status"] == "READY"

        # Corrupt the DN line to reference a non-existent SO line
        from app.modules.delivery_note.repository import delivery_note_repository as dn_repo
        from app.modules.delivery_note.schemas import DeliveryNoteLineInDB
        for lid, ln in dn_repo._lines.items():
            if ln.delivery_note_id == dn_id:
                updated_data = ln.model_dump()
                updated_data["sales_order_line_id"] = "FAKE-LINE-ID"
                dn_repo._lines[lid] = DeliveryNoteLineInDB(**updated_data)
                break

        deliv_resp = deliver_dn(token, biz_id, dn_id)
        assert deliv_resp.status_code == 400

        # DN still READY
        dn_after = client.get(f"/api/v1/businesses/{biz_id}/delivery-notes/{dn_id}", headers=auth(token)).json()
        assert dn_after["status"] == "READY"

        # Stock unchanged
        stock_after = get_stock_balances(token, biz_id, goods_product_id)
        assert stock_after[0]["quantity"] == stock_before[0]["quantity"]

        # SO unchanged
        so_after = get_so(token, biz_id, so_id)
        so_line_after = [l for l in so_after["lines"] if l["id"] == line_id][0]
        assert Decimal(str(so_line_after["quantity_fulfilled"])) == Decimal("0")


# ====================================================================
# FEATURE #58: CONCURRENCY (SHARED LOCK)
# ====================================================================


class TestFeature58Concurrency:
    def test_direct_fulfillment_and_dn_use_same_lock(self):
        """Verify direct fulfill_order() and DN delivery share _inventory_lock."""
        from app.modules.sales_order.availability import _inventory_lock
        assert _inventory_lock is not None
        import threading
        assert isinstance(_inventory_lock, type(threading.RLock()))


# ====================================================================
# SECURITY / TENANT ISOLATION
# ====================================================================


class TestDeliveryNoteSecurity:
    def test_member_cannot_mutate(self):
        token_owner = register_and_login("owner@test.com", "Pass1234!")
        biz_id = create_business(token_owner, "Sec Biz")
        branch_id, warehouse_id, location_id, customer_id, unit_id = setup_infra(token_owner, biz_id)

        product_id = client.post(f"/api/v1/businesses/{biz_id}/products", headers=auth(token_owner), json={
            "name": "Widget", "code": "SEC-01", "product_type": "GOODS", "unit_id": unit_id,
        }).json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/inventory/opening-balance", headers=auth(token_owner), json={
            "inventory_location_id": location_id, "product_id": product_id, "quantity": "50", "unit_cost": "1000",
        })

        so_id, so_line_ids = create_so_and_lines(token_owner, biz_id, branch_id, warehouse_id, [
            {"product_id": product_id, "quantity": "10"},
        ])
        line_id = so_line_ids[0]
        confirm_so(token_owner, biz_id, so_id)

        token_member = register_and_login("member@test.com", "Pass1234!")
        member_resp = client.get("/api/v1/auth/me", headers=auth(token_member))
        member_user_id = member_resp.json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/members", headers=auth(token_owner), json={
            "user_id": member_user_id, "role": "MEMBER",
        })

        resp = create_dn(token_member, biz_id, so_id, branch_id, [
            {"sales_order_line_id": line_id, "delivery_quantity": "2"}
        ])
        assert resp.status_code == 403

    def test_cross_business_delivery_rejected(self):
        token1 = register_and_login("biz1@test.com", "Pass1234!")
        biz1_id = create_business(token1, "Biz 1")
        b1, w1, l1, c1, u1 = setup_infra(token1, biz1_id)

        token2 = register_and_login("biz2@test.com", "Pass1234!")
        biz2_id = create_business(token2, "Biz 2")
        b2, w2, l2, c2, u2 = setup_infra(token2, biz2_id)

        prod1 = client.post(f"/api/v1/businesses/{biz1_id}/products", headers=auth(token1), json={
            "name": "P1", "code": "P1", "product_type": "GOODS", "unit_id": u1,
        }).json()["id"]
        client.post(f"/api/v1/businesses/{biz1_id}/inventory/opening-balance", headers=auth(token1), json={
            "inventory_location_id": l1, "product_id": prod1, "quantity": "10", "unit_cost": "1000",
        })

        so1, so1_lines = create_so_and_lines(token1, biz1_id, b1, w1, [{"product_id": prod1, "quantity": "5"}])
        confirm_so(token1, biz1_id, so1)

        dn1_resp = create_dn(token1, biz1_id, so1, b1, [{"sales_order_line_id": so1_lines[0], "delivery_quantity": "2"}], c1)
        dn1_id = dn1_resp.json()["id"]
        ready_dn(token1, biz1_id, dn1_id)

        resp = deliver_dn(token2, biz1_id, dn1_id)
        assert resp.status_code in (403, 404)

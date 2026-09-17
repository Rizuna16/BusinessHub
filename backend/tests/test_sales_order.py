import pytest
import asyncio
from fastapi.testclient import TestClient
from decimal import Decimal
from datetime import datetime, timezone

from app.main import app
from app.modules.authentication.repository import InMemoryUserRepository, user_repository
from app.modules.business.repository import InMemoryBusinessRepository, business_repository
from app.modules.business_membership.repository import InMemoryBusinessMembershipRepository, business_membership_repository
from app.modules.category.repository import InMemoryCategoryRepository, category_repository
from app.modules.unit.repository import InMemoryUnitRepository, unit_repository
from app.modules.product.repository import InMemoryProductRepository, product_repository
from app.modules.warehouse.repository import InMemoryWarehouseRepository, warehouse_repository
from app.modules.inventory.repository import InMemoryStockBalanceRepository, stock_balance_repository, InMemoryStockMovementRepository, stock_movement_repository, InMemoryInventoryCostRepository, inventory_cost_repository
from app.modules.branch.repository import InMemoryBranchRepository, branch_repository
from app.modules.customer.repository import InMemoryCustomerRepository, customer_repository
from app.modules.sales.repository import InMemorySalesRepository, sales_repository
from app.modules.sales_return.repository import InMemorySalesReturnRepository, sales_return_repository
from app.modules.sales_order.repository import InMemoryQuotationRepository, quotation_repository, InMemorySalesOrderRepository, sales_order_repository, InMemoryReservationRepository, reservation_repository
from app.modules.sales_order.schemas import QuotationStatus, SalesOrderStatus, ReservationStatus

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_stores():
    InMemoryUserRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryCategoryRepository.clear()
    InMemoryUnitRepository.clear()
    InMemoryProductRepository.clear()
    InMemoryWarehouseRepository.clear()
    InMemoryStockBalanceRepository.clear()
    InMemoryStockMovementRepository.clear()
    InMemoryInventoryCostRepository.clear()
    InMemoryBranchRepository.clear()
    InMemoryCustomerRepository.clear()
    InMemorySalesRepository.clear()
    InMemorySalesReturnRepository.clear()
    InMemoryQuotationRepository.clear()
    InMemorySalesOrderRepository.clear()
    InMemoryReservationRepository.clear()


def register_and_login(email: str, password: str, full_name: str = "Test User") -> str:
    resp = client.post("/api/v1/auth/register", json={
        "email": email,
        "full_name": full_name,
        "password": password,
        "password_confirmation": password,
    })
    assert resp.status_code == 200 or resp.status_code == 201
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    data = login_resp.json()
    return data.get("access_token") or data["data"]["access_token"]


def create_business(token: str, name: str = "Test Business") -> str:
    resp = client.post("/api/v1/businesses", headers={"Authorization": f"Bearer {token}"}, json={
        "name": name, "business_type": "retail", "timezone": "UTC", "locale": "en-US",
    })
    assert resp.status_code == 200 or resp.status_code == 201
    return resp.json()["id"]


def create_branch(token: str, business_id: str) -> str:
    resp = client.post(f"/api/v1/businesses/{business_id}/branches", headers={"Authorization": f"Bearer {token}"}, json={
        "name": "Main Branch", "code": "MB-01",
    })
    assert resp.status_code == 200 or resp.status_code == 201
    return resp.json()["id"]


def create_warehouse(token: str, business_id: str, branch_id: str) -> tuple:
    resp = client.post(f"/api/v1/businesses/{business_id}/warehouses", headers={"Authorization": f"Bearer {token}"}, json={
        "name": "Main Warehouse", "code": "WH-01", "branch_id": branch_id,
    })
    assert resp.status_code == 200 or resp.status_code == 201
    warehouse_id = resp.json()["id"]
    loc_resp = client.post(f"/api/v1/businesses/{business_id}/warehouses/{warehouse_id}/locations", headers={"Authorization": f"Bearer {token}"}, json={
        "name": "Main Location", "code": "LOC-01", "location_type": "STORAGE",
    })
    assert loc_resp.status_code == 200 or loc_resp.status_code == 201
    location_id = loc_resp.json()["id"]
    return warehouse_id, location_id


def create_customer(token: str, business_id: str) -> str:
    resp = client.post(f"/api/v1/businesses/{business_id}/customers", headers={"Authorization": f"Bearer {token}"}, json={
        "name": "Test Customer",
    })
    assert resp.status_code == 200 or resp.status_code == 201
    return resp.json()["id"]


def create_unit(token: str, business_id: str) -> str:
    resp = client.post(f"/api/v1/businesses/{business_id}/units", headers={"Authorization": f"Bearer {token}"}, json={
        "name": "Piece", "code": "PC", "symbol": "pc",
    })
    assert resp.status_code == 200 or resp.status_code == 201
    return resp.json()["id"]


def create_product(token: str, business_id: str) -> str:
    unit_id = create_unit(token, business_id)
    resp = client.post(f"/api/v1/businesses/{business_id}/products", headers={"Authorization": f"Bearer {token}"}, json={
        "name": "Test Product", "code": "PRD-01", "product_type": "GOODS", "unit_id": unit_id,
    })
    assert resp.status_code == 200 or resp.status_code == 201
    return resp.json()["id"]


def setup_base_data(token: str, business_id: str):
    branch_id = create_branch(token, business_id)
    warehouse_id, location_id = create_warehouse(token, business_id, branch_id)
    customer_id = create_customer(token, business_id)
    product_id = create_product(token, business_id)
    return branch_id, warehouse_id, location_id, customer_id, product_id


class TestQuotationLifecycle:
    def test_create_quotation(self):
        token = register_and_login("q1@test.com", "Pass1234!")
        biz_id = create_business(token, "Q Biz")
        branch_id, warehouse_id, location_id, customer_id, product_id = setup_base_data(token, biz_id)

        resp = client.post(f"/api/v1/businesses/{biz_id}/quotations", headers={"Authorization": f"Bearer {token}"}, json={
            "customer_id": customer_id, "branch_id": branch_id, "warehouse_id": warehouse_id,
            "quotation_date": datetime.now(timezone.utc).isoformat(),
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "DRAFT"
        assert data["quotation_number"].startswith("QT-")

    def test_quotation_lifecycle_full(self):
        token = register_and_login("q2@test.com", "Pass1234!")
        biz_id = create_business(token, "Q Biz 2")
        branch_id, warehouse_id, location_id, customer_id, product_id = setup_base_data(token, biz_id)

        resp = client.post(f"/api/v1/businesses/{biz_id}/quotations", headers={"Authorization": f"Bearer {token}"}, json={
            "customer_id": customer_id, "branch_id": branch_id, "warehouse_id": warehouse_id,
            "quotation_date": datetime.now(timezone.utc).isoformat(),
        })
        q_id = resp.json()["id"]

        add_line = client.post(f"/api/v1/businesses/{biz_id}/quotations/{q_id}/lines", headers={"Authorization": f"Bearer {token}"}, json={
            "product_id": product_id, "quantity": "10", "unit_price": "5000",
        })
        assert add_line.status_code == 201

        send_resp = client.post(f"/api/v1/businesses/{biz_id}/quotations/{q_id}/send", headers={"Authorization": f"Bearer {token}"})
        assert send_resp.status_code == 200
        assert send_resp.json()["status"] == "SENT"

        accept_resp = client.post(f"/api/v1/businesses/{biz_id}/quotations/{q_id}/accept", headers={"Authorization": f"Bearer {token}"})
        assert accept_resp.status_code == 200
        assert accept_resp.json()["status"] == "ACCEPTED"

        convert_resp = client.post(f"/api/v1/businesses/{biz_id}/quotations/{q_id}/convert", headers={"Authorization": f"Bearer {token}"}, json={})
        assert convert_resp.status_code == 200
        assert convert_resp.json()["sales_order_id"] is not None

    def test_quotation_invalid_transition(self):
        token = register_and_login("q3@test.com", "Pass1234!")
        biz_id = create_business(token, "Q Biz 3")
        branch_id, warehouse_id, location_id, customer_id, product_id = setup_base_data(token, biz_id)

        resp = client.post(f"/api/v1/businesses/{biz_id}/quotations", headers={"Authorization": f"Bearer {token}"}, json={
            "customer_id": customer_id, "branch_id": branch_id, "warehouse_id": warehouse_id,
            "quotation_date": datetime.now(timezone.utc).isoformat(),
        })
        q_id = resp.json()["id"]

        add_line = client.post(f"/api/v1/businesses/{biz_id}/quotations/{q_id}/lines", headers={"Authorization": f"Bearer {token}"}, json={
            "product_id": product_id, "quantity": "10", "unit_price": "5000",
        })
        assert add_line.status_code == 201

        reject_resp = client.post(f"/api/v1/businesses/{biz_id}/quotations/{q_id}/reject", headers={"Authorization": f"Bearer {token}"})
        assert reject_resp.status_code == 400

    def test_quotation_cancel(self):
        token = register_and_login("q4@test.com", "Pass1234!")
        biz_id = create_business(token, "Q Biz 4")
        branch_id, warehouse_id, location_id, customer_id, product_id = setup_base_data(token, biz_id)

        resp = client.post(f"/api/v1/businesses/{biz_id}/quotations", headers={"Authorization": f"Bearer {token}"}, json={
            "customer_id": customer_id, "branch_id": branch_id, "warehouse_id": warehouse_id,
            "quotation_date": datetime.now(timezone.utc).isoformat(),
        })
        q_id = resp.json()["id"]

        cancel_resp = client.post(f"/api/v1/businesses/{biz_id}/quotations/{q_id}/cancel", headers={"Authorization": f"Bearer {token}"})
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "CANCELLED"

    def test_quotation_immutable_after_terminal(self):
        token = register_and_login("q5@test.com", "Pass1234!")
        biz_id = create_business(token, "Q Biz 5")
        branch_id, warehouse_id, location_id, customer_id, product_id = setup_base_data(token, biz_id)

        resp = client.post(f"/api/v1/businesses/{biz_id}/quotations", headers={"Authorization": f"Bearer {token}"}, json={
            "customer_id": customer_id, "branch_id": branch_id, "warehouse_id": warehouse_id,
            "quotation_date": datetime.now(timezone.utc).isoformat(),
        })
        q_id = resp.json()["id"]

        add_line = client.post(f"/api/v1/businesses/{biz_id}/quotations/{q_id}/lines", headers={"Authorization": f"Bearer {token}"}, json={
            "product_id": product_id, "quantity": "10", "unit_price": "5000",
        })
        assert add_line.status_code == 201

        send_resp = client.post(f"/api/v1/businesses/{biz_id}/quotations/{q_id}/send", headers={"Authorization": f"Bearer {token}"})
        accept_resp = client.post(f"/api/v1/businesses/{biz_id}/quotations/{q_id}/accept", headers={"Authorization": f"Bearer {token}"})
        convert_resp = client.post(f"/api/v1/businesses/{biz_id}/quotations/{q_id}/convert", headers={"Authorization": f"Bearer {token}"}, json={})

        update_resp = client.put(f"/api/v1/businesses/{biz_id}/quotations/{q_id}", headers={"Authorization": f"Bearer {token}"}, json={
            "notes": "Should fail",
        })
        assert update_resp.status_code == 400

    def test_duplicate_conversion_idempotent(self):
        token = register_and_login("q6@test.com", "Pass1234!")
        biz_id = create_business(token, "Q Biz 6")
        branch_id, warehouse_id, location_id, customer_id, product_id = setup_base_data(token, biz_id)

        resp = client.post(f"/api/v1/businesses/{biz_id}/quotations", headers={"Authorization": f"Bearer {token}"}, json={
            "customer_id": customer_id, "branch_id": branch_id, "warehouse_id": warehouse_id,
            "quotation_date": datetime.now(timezone.utc).isoformat(),
        })
        q_id = resp.json()["id"]

        add_line = client.post(f"/api/v1/businesses/{biz_id}/quotations/{q_id}/lines", headers={"Authorization": f"Bearer {token}"}, json={
            "product_id": product_id, "quantity": "10", "unit_price": "5000",
        })
        client.post(f"/api/v1/businesses/{biz_id}/quotations/{q_id}/send", headers={"Authorization": f"Bearer {token}"})
        client.post(f"/api/v1/businesses/{biz_id}/quotations/{q_id}/accept", headers={"Authorization": f"Bearer {token}"})

        convert1 = client.post(f"/api/v1/businesses/{biz_id}/quotations/{q_id}/convert", headers={"Authorization": f"Bearer {token}"}, json={})
        assert convert1.status_code == 200
        so_id = convert1.json()["sales_order_id"]

        convert2 = client.post(f"/api/v1/businesses/{biz_id}/quotations/{q_id}/convert", headers={"Authorization": f"Bearer {token}"}, json={})
        assert convert2.status_code == 200
        assert convert2.json()["sales_order_id"] == so_id


class TestSalesOrderLifecycle:
    def _setup_so(self):
        token = register_and_login("so1@test.com", "Pass1234!")
        biz_id = create_business(token, "SO Biz")
        branch_id, warehouse_id, location_id, customer_id, product_id = setup_base_data(token, biz_id)
        return token, biz_id, branch_id, warehouse_id, location_id, customer_id, product_id

    def test_create_sales_order(self):
        token, biz_id, branch_id, warehouse_id, location_id, customer_id, product_id = self._setup_so()
        resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders", headers={"Authorization": f"Bearer {token}"}, json={
            "customer_id": customer_id, "branch_id": branch_id, "warehouse_id": warehouse_id,
            "order_date": datetime.now(timezone.utc).isoformat(),
        })
        assert resp.status_code == 201
        assert resp.json()["status"] == "DRAFT"
        assert resp.json()["sales_order_number"].startswith("SO-")

    def test_confirm_order(self):
        token, biz_id, branch_id, warehouse_id, location_id, customer_id, product_id = self._setup_so()
        inv_resp = client.post(f"/api/v1/businesses/{biz_id}/inventory/opening-balance", headers={"Authorization": f"Bearer {token}"}, json={
            "inventory_location_id": location_id, "product_id": product_id, "quantity": "10", "unit_cost": "5000",
        })
        assert inv_resp.status_code == 201
        resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders", headers={"Authorization": f"Bearer {token}"}, json={
            "customer_id": customer_id, "branch_id": branch_id, "warehouse_id": warehouse_id,
            "order_date": datetime.now(timezone.utc).isoformat(),
        })
        so_id = resp.json()["id"]

        add_line = client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/lines", headers={"Authorization": f"Bearer {token}"}, json={
            "product_id": product_id, "quantity": "5", "unit_price": "10000",
        })
        assert add_line.status_code == 201

        confirm_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/confirm", headers={"Authorization": f"Bearer {token}"})
        assert confirm_resp.status_code == 200
        assert confirm_resp.json()["status"] == "CONFIRMED"

    def test_confirm_insufficient_stock(self):
        token, biz_id, branch_id, warehouse_id, location_id, customer_id, product_id = self._setup_so()
        resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders", headers={"Authorization": f"Bearer {token}"}, json={
            "customer_id": customer_id, "branch_id": branch_id, "warehouse_id": warehouse_id,
            "order_date": datetime.now(timezone.utc).isoformat(),
        })
        so_id = resp.json()["id"]

        add_line = client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/lines", headers={"Authorization": f"Bearer {token}"}, json={
            "product_id": product_id, "quantity": "100", "unit_price": "10000",
        })

        confirm_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/confirm", headers={"Authorization": f"Bearer {token}"})
        assert confirm_resp.status_code == 400

    def test_cancel_order_releases_reservation(self):
        token, biz_id, branch_id, warehouse_id, location_id, customer_id, product_id = self._setup_so()

        inv_resp = client.post(f"/api/v1/businesses/{biz_id}/inventory/opening-balance", headers={"Authorization": f"Bearer {token}"}, json={
            "inventory_location_id": location_id, "product_id": product_id, "quantity": "10", "unit_cost": "5000",
        })

        resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders", headers={"Authorization": f"Bearer {token}"}, json={
            "customer_id": customer_id, "branch_id": branch_id, "warehouse_id": warehouse_id,
            "order_date": datetime.now(timezone.utc).isoformat(),
        })
        so_id = resp.json()["id"]

        add_line = client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/lines", headers={"Authorization": f"Bearer {token}"}, json={
            "product_id": product_id, "quantity": "5", "unit_price": "10000",
        })
        client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/confirm", headers={"Authorization": f"Bearer {token}"})

        from app.modules.sales_order.repository import reservation_repository
        active_res = asyncio.run(reservation_repository.list_active_by_warehouse_product(biz_id, warehouse_id, product_id, None))
        assert len(active_res) > 0

        cancel_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/cancel", headers={"Authorization": f"Bearer {token}"})
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "CANCELLED"

        active_res_after = asyncio.run(reservation_repository.list_active_by_warehouse_product(biz_id, warehouse_id, product_id, None))
        assert len(active_res_after) == 0

    def test_fulfill_order(self):
        token, biz_id, branch_id, warehouse_id, location_id, customer_id, product_id = self._setup_so()

        inv_resp = client.post(f"/api/v1/businesses/{biz_id}/inventory/opening-balance", headers={"Authorization": f"Bearer {token}"}, json={
            "inventory_location_id": location_id, "product_id": product_id, "quantity": "10", "unit_cost": "5000",
        })

        resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders", headers={"Authorization": f"Bearer {token}"}, json={
            "customer_id": customer_id, "branch_id": branch_id, "warehouse_id": warehouse_id,
            "order_date": datetime.now(timezone.utc).isoformat(),
        })
        so_id = resp.json()["id"]

        add_line = client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/lines", headers={"Authorization": f"Bearer {token}"}, json={
            "product_id": product_id, "quantity": "5", "unit_price": "10000",
        })
        line_id = add_line.json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/confirm", headers={"Authorization": f"Bearer {token}"})

        fulfill_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/fulfill", headers={"Authorization": f"Bearer {token}"}, json={
            "line_fulfillments": [{"line_id": line_id, "quantity": "3"}],
        })
        assert fulfill_resp.status_code == 200
        assert fulfill_resp.json()["status"] == "PARTIALLY_FULFILLED"

        fulfill_resp2 = client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/fulfill", headers={"Authorization": f"Bearer {token}"}, json={
            "line_fulfillments": [{"line_id": line_id, "quantity": "2"}],
        })
        assert fulfill_resp2.status_code == 200
        assert fulfill_resp2.json()["status"] == "FULFILLED"


class TestHardReservation:
    def test_checkout_respects_reservations(self):
        token = register_and_login("r1@test.com", "Pass1234!")
        biz_id = create_business(token, "Res Biz")
        branch_id, warehouse_id, location_id, customer_id, product_id = setup_base_data(token, biz_id)

        inv_resp = client.post(f"/api/v1/businesses/{biz_id}/inventory/opening-balance", headers={"Authorization": f"Bearer {token}"}, json={
            "inventory_location_id": location_id, "product_id": product_id, "quantity": "10", "unit_cost": "5000",
        })

        so_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders", headers={"Authorization": f"Bearer {token}"}, json={
            "customer_id": customer_id, "branch_id": branch_id, "warehouse_id": warehouse_id,
            "order_date": datetime.now(timezone.utc).isoformat(),
        })
        so_id = so_resp.json()["id"]

        add_line = client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/lines", headers={"Authorization": f"Bearer {token}"}, json={
            "product_id": product_id, "quantity": "7", "unit_price": "10000",
        })
        client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/confirm", headers={"Authorization": f"Bearer {token}"})

        avail_resp = client.get(f"/api/v1/businesses/{biz_id}/inventory/availability/check?product_id={product_id}&warehouse_id={warehouse_id}&quantity=4", headers={"Authorization": f"Bearer {token}"})
        assert avail_resp.status_code == 200
        assert avail_resp.json()["available"] is False

        avail_resp2 = client.get(f"/api/v1/businesses/{biz_id}/inventory/availability/check?product_id={product_id}&warehouse_id={warehouse_id}&quantity=3", headers={"Authorization": f"Bearer {token}"})
        assert avail_resp2.status_code == 200
        assert avail_resp2.json()["available"] is True


class TestQuotationNoAccounting:
    def test_quotation_creates_no_journal(self):
        token = register_and_login("a1@test.com", "Pass1234!")
        biz_id = create_business(token, "Acct Biz")
        branch_id, warehouse_id, location_id, customer_id, product_id = setup_base_data(token, biz_id)

        resp = client.post(f"/api/v1/businesses/{biz_id}/quotations", headers={"Authorization": f"Bearer {token}"}, json={
            "customer_id": customer_id, "branch_id": branch_id, "warehouse_id": warehouse_id,
            "quotation_date": datetime.now(timezone.utc).isoformat(),
        })
        q_id = resp.json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/quotations/{q_id}/lines", headers={"Authorization": f"Bearer {token}"}, json={
            "product_id": product_id, "quantity": "10", "unit_price": "5000",
        })
        client.post(f"/api/v1/businesses/{biz_id}/quotations/{q_id}/send", headers={"Authorization": f"Bearer {token}"})
        client.post(f"/api/v1/businesses/{biz_id}/quotations/{q_id}/accept", headers={"Authorization": f"Bearer {token}"})

        from app.modules.inventory.repository import stock_movement_repository
        movements = asyncio.run(stock_movement_repository.list_movements(business_id=biz_id))
        assert len(movements) == 0


class TestSalesOrderNoAccounting:
    def test_order_creates_no_journal(self):
        token = register_and_login("a2@test.com", "Pass1234!")
        biz_id = create_business(token, "Acct Biz 2")
        branch_id, warehouse_id, location_id, customer_id, product_id = setup_base_data(token, biz_id)

        inv_resp = client.post(f"/api/v1/businesses/{biz_id}/inventory/opening-balance", headers={"Authorization": f"Bearer {token}"}, json={
            "inventory_location_id": location_id, "product_id": product_id, "quantity": "10", "unit_cost": "5000",
        })

        so_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders", headers={"Authorization": f"Bearer {token}"}, json={
            "customer_id": customer_id, "branch_id": branch_id, "warehouse_id": warehouse_id,
            "order_date": datetime.now(timezone.utc).isoformat(),
        })
        so_id = so_resp.json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/lines", headers={"Authorization": f"Bearer {token}"}, json={
            "product_id": product_id, "quantity": "5", "unit_price": "10000",
        })
        client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/confirm", headers={"Authorization": f"Bearer {token}"})

        from app.modules.inventory.repository import stock_movement_repository
        movements = asyncio.run(stock_movement_repository.list_movements(business_id=biz_id))
        sale_movements = [m for m in movements if m.movement_type.value == "SALE_OUT"]
        assert len(sale_movements) == 0


class TestBusinessIsolation:
    def test_cross_business_access_denied(self):
        token_a = register_and_login("iso1@test.com", "Pass1234!")
        token_b = register_and_login("iso2@test.com", "Pass1234!")
        biz_a = create_business(token_a, "Biz A")
        biz_b = create_business(token_b, "Biz B")

        resp_a = client.post(f"/api/v1/businesses/{biz_a}/quotations", headers={"Authorization": f"Bearer {token_a}"}, json={
            "branch_id": "dummy", "warehouse_id": "dummy",
            "quotation_date": datetime.now(timezone.utc).isoformat(),
        })

        resp_cross = client.get(f"/api/v1/businesses/{biz_a}/quotations", headers={"Authorization": f"Bearer {token_b}"})
        assert resp_cross.status_code == 404 or resp_cross.status_code == 403


class TestSalesOrderNumbering:
    def test_sequential_numbering(self):
        token = register_and_login("n1@test.com", "Pass1234!")
        biz_id = create_business(token, "Num Biz")
        branch_id, warehouse_id, location_id, customer_id, product_id = setup_base_data(token, biz_id)

        so1 = client.post(f"/api/v1/businesses/{biz_id}/sales-orders", headers={"Authorization": f"Bearer {token}"}, json={
            "customer_id": customer_id, "branch_id": branch_id, "warehouse_id": warehouse_id,
            "order_date": datetime.now(timezone.utc).isoformat(),
        })
        so2 = client.post(f"/api/v1/businesses/{biz_id}/sales-orders", headers={"Authorization": f"Bearer {token}"}, json={
            "customer_id": customer_id, "branch_id": branch_id, "warehouse_id": warehouse_id,
            "order_date": datetime.now(timezone.utc).isoformat(),
        })
        assert so1.json()["sales_order_number"] != so2.json()["sales_order_number"]
        assert so1.json()["sales_order_number"].startswith("SO-")
        assert so2.json()["sales_order_number"].startswith("SO-")

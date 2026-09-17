import asyncio
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from app.main import app
from app.modules.authentication.repository import InMemoryUserRepository
from app.modules.account.repository import InMemoryAccountRepository
from app.modules.accounting.repository import InMemoryAccountingRepository
from app.modules.business.repository import InMemoryBusinessRepository
from app.modules.business_membership.repository import InMemoryBusinessMembershipRepository
from app.modules.customer.repository import InMemoryCustomerRepository
from app.modules.branch.repository import InMemoryBranchRepository
from app.modules.unit.repository import InMemoryUnitRepository
from app.modules.product.repository import InMemoryProductRepository
from app.modules.product_variant.repository import InMemoryProductVariantRepository
from app.modules.sales.repository import InMemorySalesRepository
from app.modules.warehouse.repository import InMemoryWarehouseRepository, InMemoryInventoryLocationRepository
from app.modules.inventory.repository import InMemoryStockBalanceRepository, InMemoryStockMovementRepository, InMemoryInventoryCostRepository
from app.modules.sales_return.repository import InMemorySalesReturnRepository
from app.modules.delivery_note.repository import InMemoryDeliveryNoteRepository
from app.modules.sales_order.repository import (
    InMemorySalesOrderRepository, InMemoryReservationRepository,
    InMemoryQuotationRepository,
)
from app.modules.inventory.repository import InMemoryInventoryCostRepository
from app.modules.delivery_note.schemas import DeliveryNoteStatus
from app.modules.delivery_note.repository import delivery_note_repository
from app.modules.sales_return.schemas import SalesReturnStatus

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_repositories():
    InMemorySalesReturnRepository.clear()
    InMemoryStockBalanceRepository.clear()
    InMemoryStockMovementRepository.clear()
    InMemoryInventoryCostRepository.clear()
    InMemoryInventoryLocationRepository.clear()
    InMemoryWarehouseRepository.clear()
    InMemorySalesRepository.clear()
    InMemoryProductVariantRepository.clear()
    InMemoryProductRepository.clear()
    InMemoryUnitRepository.clear()
    InMemoryBranchRepository.clear()
    InMemoryCustomerRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryUserRepository.clear()
    InMemoryDeliveryNoteRepository.clear()
    InMemorySalesOrderRepository.clear()
    InMemoryReservationRepository.clear()
    InMemoryQuotationRepository.clear()
    yield
    InMemorySalesReturnRepository.clear()
    InMemoryStockBalanceRepository.clear()
    InMemoryStockMovementRepository.clear()
    InMemoryInventoryCostRepository.clear()
    InMemoryInventoryLocationRepository.clear()
    InMemoryWarehouseRepository.clear()
    InMemorySalesRepository.clear()
    InMemoryProductVariantRepository.clear()
    InMemoryProductRepository.clear()
    InMemoryUnitRepository.clear()
    InMemoryBranchRepository.clear()
    InMemoryCustomerRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryUserRepository.clear()
    InMemoryDeliveryNoteRepository.clear()
    InMemorySalesOrderRepository.clear()
    InMemoryReservationRepository.clear()
    InMemoryQuotationRepository.clear()


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


def create_variant(token, business_id, product_id, name="Variant 1", code="VAR-1"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/products/{product_id}/variants",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code},
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


def add_opening_stock(token, business_id, location_id, product_id, variant_id=None, qty="100"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/inventory/opening-balance",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "inventory_location_id": location_id,
            "product_id": product_id,
            "variant_id": variant_id,
            "quantity": qty,
        },
    )
    assert res.status_code == 201


def create_finalized_sales(token, business_id, br_id, prod_id, variant_id=None, qty="10", price="50000"):
    s_res = client.post(
        f"/api/v1/businesses/{business_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": br_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    )
    assert s_res.status_code == 201
    sales_id = s_res.json()["id"]

    l_payload = {"product_id": prod_id, "quantity": qty, "unit_price": price}
    if variant_id:
        l_payload["variant_id"] = variant_id
        l_payload["product_id"] = None

    l_res = client.post(
        f"/api/v1/businesses/{business_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json=l_payload,
    )
    assert l_res.status_code == 201
    sline_id = l_res.json()["id"]

    fin_res = client.post(
        f"/api/v1/businesses/{business_id}/sales/{sales_id}/finalize",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fin_res.status_code == 200
    return sales_id, sline_id


class TestSalesReturnFeature:

    # 1. Unauthenticated access rejected
    def test_unauthenticated_access_rejected(self):
        res = client.get("/api/v1/businesses/biz123/sales-returns")
        assert res.status_code == 401

    # 2. Source Sales must be FINALIZED
    def test_draft_sales_return_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)

        s_res = client.post(
            f"/api/v1/businesses/{biz_id}/sales",
            headers={"Authorization": f"Bearer {token}"},
            json={"branch_id": br_id, "sales_date": datetime.now(timezone.utc).isoformat()},
        )
        sales_id = s_res.json()["id"]

        res = client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_id": sales_id},
        )
        assert res.status_code == 400
        assert "not FINALIZED" in res.json()["message"]

    # 3. Create Draft Sales Return & sequence SRT-000001
    def test_create_sales_return_success(self):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        add_opening_stock(token, biz_id, loc_id, prod_id, qty="100")

        sales_id, _ = create_finalized_sales(token, biz_id, br_id, prod_id, qty="10")

        res = client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_id": sales_id, "inventory_location_id": loc_id, "notes": "Customer defect"},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "DRAFT"
        assert data["return_number"] == "SRT-000001"
        assert data["sales_id"] == sales_id

    # 4. SERVICE product return rejected
    def test_service_product_return_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        srv_prod_id = create_product(token, biz_id, unit_id, p_type="SERVICE")
        loc_id = setup_warehouse_and_location(token, biz_id)

        sales_id, sline_id = create_finalized_sales(token, biz_id, br_id, srv_prod_id, qty="1")

        ret_res = client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_id": sales_id, "inventory_location_id": loc_id},
        )
        ret_id = ret_res.json()["id"]

        line_res = client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns/{ret_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_line_id": sline_id, "quantity": "1"},
        )
        assert line_res.status_code == 400
        assert "GOODS products" in line_res.json()["message"]

    # 5. Over-return capacity rejected
    def test_over_return_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        add_opening_stock(token, biz_id, loc_id, prod_id, qty="100")

        sales_id, sline_id = create_finalized_sales(token, biz_id, br_id, prod_id, qty="5")

        ret_res = client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_id": sales_id, "inventory_location_id": loc_id},
        )
        ret_id = ret_res.json()["id"]

        # Attempt to return 6 when only 5 sold
        line_res = client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns/{ret_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_line_id": sline_id, "quantity": "6"},
        )
        assert line_res.status_code == 400
        assert "exceeds remaining returnable capacity" in line_res.json()["message"]

    # 6. Multiple partial returns allowed
    def test_multiple_partial_returns(self):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        add_opening_stock(token, biz_id, loc_id, prod_id, qty="100")

        sales_id, sline_id = create_finalized_sales(token, biz_id, br_id, prod_id, qty="10")

        # Return 1: Qty 4
        ret1 = client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_id": sales_id, "inventory_location_id": loc_id},
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns/{ret1}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_line_id": sline_id, "quantity": "4"},
        )
        client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns/{ret1}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Return 2: Qty 6 (should pass, completing 10)
        ret2 = client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_id": sales_id, "inventory_location_id": loc_id},
        ).json()["id"]
        line2_res = client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns/{ret2}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_line_id": sline_id, "quantity": "6"},
        )
        assert line2_res.status_code == 201

        # Return 3: Qty 1 (should fail)
        ret3 = client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_id": sales_id, "inventory_location_id": loc_id},
        ).json()["id"]
        line3_res = client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns/{ret3}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_line_id": sline_id, "quantity": "1"},
        )
        assert line3_res.status_code == 400

    # 7. Duplicate SalesLine in same return rejected
    def test_duplicate_sales_line_in_same_return_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        add_opening_stock(token, biz_id, loc_id, prod_id, qty="100")

        sales_id, sline_id = create_finalized_sales(token, biz_id, br_id, prod_id, qty="10")

        ret_id = client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_id": sales_id, "inventory_location_id": loc_id},
        ).json()["id"]

        res1 = client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns/{ret_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_line_id": sline_id, "quantity": "2"},
        )
        assert res1.status_code == 201

        res2 = client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns/{ret_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_line_id": sline_id, "quantity": "3"},
        )
        assert res2.status_code == 400
        assert "already included" in res2.json()["message"]

    # 8. Cancel releases capacity
    def test_cancel_releases_capacity(self):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        add_opening_stock(token, biz_id, loc_id, prod_id, qty="100")

        sales_id, sline_id = create_finalized_sales(token, biz_id, br_id, prod_id, qty="5")

        ret1 = client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_id": sales_id, "inventory_location_id": loc_id},
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns/{ret1}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_line_id": sline_id, "quantity": "5"},
        )

        # Cancel return 1
        cancel_res = client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns/{ret1}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert cancel_res.status_code == 200
        assert cancel_res.json()["status"] == "CANCELLED"

        # Now return 2 for full 5 quantity should succeed
        ret2 = client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_id": sales_id, "inventory_location_id": loc_id},
        ).json()["id"]
        line2_res = client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns/{ret2}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_line_id": sline_id, "quantity": "5"},
        )
        assert line2_res.status_code == 201

    # 9. Finalization increases inventory stock with Movement SALE_RETURN_IN
    def test_finalization_increases_stock(self):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        add_opening_stock(token, biz_id, loc_id, prod_id, qty="100")

        sales_id, sline_id = create_finalized_sales(token, biz_id, br_id, prod_id, qty="10")

        # Initial stock balance after sale (100 - 10 = 90)
        bal_before = client.get(
            f"/api/v1/businesses/{biz_id}/inventory/stock",
            headers={"Authorization": f"Bearer {token}"},
        ).json()[0]["quantity"]
        assert Decimal(str(bal_before)) == Decimal("90.0000")

        # Create and finalize Sales Return of 4 units
        ret_id = client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_id": sales_id, "inventory_location_id": loc_id},
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns/{ret_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_line_id": sline_id, "quantity": "4"},
        )

        fin_res = client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns/{ret_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fin_res.status_code == 200
        assert fin_res.json()["status"] == "FINALIZED"

        # Check updated stock balance (90 + 4 = 94)
        bal_after = client.get(
            f"/api/v1/businesses/{biz_id}/inventory/stock",
            headers={"Authorization": f"Bearer {token}"},
        ).json()[0]["quantity"]
        assert Decimal(str(bal_after)) == Decimal("94.0000")

        # Check movement record
        movements = client.get(
            f"/api/v1/businesses/{biz_id}/inventory/movements",
            headers={"Authorization": f"Bearer {token}"},
        ).json()

        return_mov = [m for m in movements if m["movement_type"] == "SALE_RETURN_IN"]
        assert len(return_mov) == 1
        assert return_mov[0]["reference_type"] == "SALES_RETURN"
        assert return_mov[0]["reference_id"] == ret_id

    # 10. Double finalization rejected
    def test_double_finalization_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        add_opening_stock(token, biz_id, loc_id, prod_id, qty="100")

        sales_id, sline_id = create_finalized_sales(token, biz_id, br_id, prod_id, qty="10")

        ret_id = client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_id": sales_id, "inventory_location_id": loc_id},
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns/{ret_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_line_id": sline_id, "quantity": "4"},
        )
        client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns/{ret_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Second finalization attempt
        fin2_res = client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns/{ret_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fin2_res.status_code == 400

    # 11. Cross-tenant access rejected
    def test_cross_tenant_access_rejected(self):
        token1, _ = register_user(email="owner1@example.com")
        biz1 = create_business(token1, name="Biz 1")

        token2, _ = register_user(email="owner2@example.com")
        biz2 = create_business(token2, name="Biz 2")
        br2 = create_branch(token2, biz2)
        unit2 = create_unit(token2, biz2)
        prod2 = create_product(token2, biz2, unit2)
        loc2 = setup_warehouse_and_location(token2, biz2)
        add_opening_stock(token2, biz2, loc2, prod2, qty="100")
        sales2_id, _ = create_finalized_sales(token2, biz2, br2, prod2, qty="5")

        # Owner 1 attempts to create sales return in Biz 1 referencing Biz 2 sales
        res = client.post(
            f"/api/v1/businesses/{biz1}/sales-returns",
            headers={"Authorization": f"Bearer {token1}"},
            json={"sales_id": sales2_id},
        )
        assert res.status_code == 404


# ====================================================================
# FEATURE #59 — SALES RETURN → DELIVERY NOTE RECONCILIATION
# ====================================================================

def auth(token):
    return {"Authorization": f"Bearer {token}"}


def setup_f59_infra(token, biz_id):
    """Create branch, warehouse, location, customer, unit. Return (br_id, wh_id, loc_id, cust_id, uid)."""
    br = client.post(f"/api/v1/businesses/{biz_id}/branches", headers=auth(token), json={"name": "B", "code": "BR"}).json()
    br_id = br["id"]
    wh = client.post(f"/api/v1/businesses/{biz_id}/warehouses", headers=auth(token), json={"name": "WH", "code": "WH1", "branch_id": br_id}).json()
    wh_id = wh["id"]
    loc = client.post(f"/api/v1/businesses/{biz_id}/warehouses/{wh_id}/locations", headers=auth(token), json={"name": "L", "code": "L1", "location_type": "GENERAL"}).json()
    loc_id = loc["id"]
    cust = client.post(f"/api/v1/businesses/{biz_id}/customers", headers=auth(token), json={"name": "Cust"}).json()
    cust_id = cust["id"]
    uid = client.post(f"/api/v1/businesses/{biz_id}/units", headers=auth(token), json={"name": "Pcs", "code": "PCS"}).json()["id"]
    return br_id, wh_id, loc_id, cust_id, uid


def f59_product(token, biz_id, uid, name="Goods", code="G1"):
    return client.post(f"/api/v1/businesses/{biz_id}/products", headers=auth(token), json={
        "name": name, "code": code, "product_type": "GOODS", "unit_id": uid,
    }).json()["id"]


def f59_stock(token, biz_id, loc_id, prod_id, qty="200"):
    client.post(f"/api/v1/businesses/{biz_id}/inventory/opening-balance", headers=auth(token), json={
        "inventory_location_id": loc_id, "product_id": prod_id, "quantity": qty, "unit_cost": "1000",
    })


def f59_create_delivered_dn(token, biz_id, so_id, br_id, so_line_id, qty, cust_id=None):
    """Create a DRAFT DN then deliver it. Return (dn_json, dn_id, dn_line_id)."""
    payload = {
        "sales_order_id": so_id, "branch_id": br_id,
        "delivery_date": datetime.now(timezone.utc).isoformat(),
        "lines": [{"sales_order_line_id": so_line_id, "delivery_quantity": str(qty)}],
    }
    if cust_id:
        payload["customer_id"] = cust_id
    dn = client.post(f"/api/v1/businesses/{biz_id}/delivery-notes", headers=auth(token), json=payload)
    assert dn.status_code == 201, dn.text
    dn_id = dn.json()["id"]
    client.post(f"/api/v1/businesses/{biz_id}/delivery-notes/{dn_id}/ready", headers=auth(token))
    d = client.post(f"/api/v1/businesses/{biz_id}/delivery-notes/{dn_id}/deliver", headers=auth(token))
    assert d.status_code == 200, d.text
    dn_line_id = dn.json()["lines"][0]["id"]
    return dn.json(), dn_id, dn_line_id


def f59_create_dn_status(token, biz_id, so_id, br_id, so_line_id, qty, cust_id=None, status="DRAFT"):
    payload = {
        "sales_order_id": so_id, "branch_id": br_id,
        "delivery_date": datetime.now(timezone.utc).isoformat(),
        "lines": [{"sales_order_line_id": so_line_id, "delivery_quantity": str(qty)}],
    }
    if cust_id:
        payload["customer_id"] = cust_id
    dn = client.post(f"/api/v1/businesses/{biz_id}/delivery-notes", headers=auth(token), json=payload)
    assert dn.status_code == 201, dn.text
    dn_id = dn.json()["id"]
    if status == "READY":
        client.post(f"/api/v1/businesses/{biz_id}/delivery-notes/{dn_id}/ready", headers=auth(token))
    elif status == "CANCELLED":
        client.post(f"/api/v1/businesses/{biz_id}/delivery-notes/{dn_id}/cancel", headers=auth(token))
    return dn.json(), dn_id, dn.json()["lines"][0]["id"]


class TestFeature59DnReturn:
    def test_delivered_dn_return_succeeds(self):
        """Return referencing a DELIVERED DN line succeeds and creates SALE_RETURN_IN."""
        token, _ = register_user("f59_1@test.com")
        biz_id = create_business(token, "F59 DN Ret")
        br_id, wh_id, loc_id, cust_id, uid = setup_f59_infra(token, biz_id)
        prod_id = f59_product(token, biz_id, uid)
        f59_stock(token, biz_id, loc_id, prod_id)

        # Create finalized Sales (what SalesReturn.sales_id references)
        sales_id, sline_id = create_finalized_sales(token, biz_id, br_id, prod_id, qty="10")

        # Create SO + DN (DN delivery handles SO fulfillment via Feature #58)
        so_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders", headers=auth(token), json={
            "customer_id": cust_id, "branch_id": br_id, "warehouse_id": wh_id,
            "order_date": datetime.now(timezone.utc).isoformat(),
        })
        so_id = so_resp.json()["id"]
        so_line_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/lines", headers=auth(token), json={
            "product_id": prod_id, "quantity": "10", "unit_price": "5000",
        })
        so_line_id = so_line_resp.json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/confirm", headers=auth(token))
        # DN delivery fulfills the SO (Feature #58)
        dn_json, dn_id, dn_line_id = f59_create_delivered_dn(token, biz_id, so_id, br_id, so_line_id, 10, cust_id)

        # Create SalesReturn referencing Sales, with DN-linked line
        sr_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-returns", headers=auth(token), json={
            "sales_id": sales_id, "inventory_location_id": loc_id, "notes": "DN Return",
        })
        assert sr_resp.status_code == 201
        sr_id = sr_resp.json()["id"]
        lr = client.post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id}/lines", headers=auth(token), json={
            "sales_line_id": sline_id, "quantity": "3",
            "delivery_note_id": dn_id, "delivery_note_line_id": dn_line_id,
        })
        assert lr.status_code == 201, lr.text
        fin = client.post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id}/finalize", headers=auth(token))
        assert fin.status_code == 200

        # Verify SALE_RETURN_IN movement created
        mvts = client.get(f"/api/v1/businesses/{biz_id}/inventory/movements?movement_type=SALE_RETURN_IN", headers=auth(token)).json()
        assert len(mvts) >= 1
        assert any(m["reference_id"] == sr_id for m in mvts)

    def test_draft_dn_rejected(self):
        """Cannot return from a DRAFT DN."""
        token, _ = register_user("f59_2@test.com")
        biz_id = create_business(token, "F59 DN Draft")
        br_id, wh_id, loc_id, cust_id, uid = setup_f59_infra(token, biz_id)
        prod_id = f59_product(token, biz_id, uid)
        f59_stock(token, biz_id, loc_id, prod_id)
        sales_id, sline_id = create_finalized_sales(token, biz_id, br_id, prod_id, qty="10")

        so_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders", headers=auth(token), json={
            "customer_id": cust_id, "branch_id": br_id, "warehouse_id": wh_id,
            "order_date": datetime.now(timezone.utc).isoformat(),
        })
        so_id = so_resp.json()["id"]
        so_line_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/lines", headers=auth(token), json={
            "product_id": prod_id, "quantity": "10", "unit_price": "5000",
        })
        so_line_id = so_line_resp.json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/confirm", headers=auth(token))
        _, dn_id, dn_line_id = f59_create_dn_status(token, biz_id, so_id, br_id, so_line_id, 5, cust_id, "DRAFT")

        sr_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-returns", headers=auth(token), json={
            "sales_id": sales_id, "inventory_location_id": loc_id,
        })
        sr_id = sr_resp.json()["id"]
        lr = client.post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id}/lines", headers=auth(token), json={
            "sales_line_id": sline_id, "quantity": "2",
            "delivery_note_id": dn_id, "delivery_note_line_id": dn_line_id,
        })
        assert lr.status_code == 400
        assert "DELIVERED" in lr.json()["message"]

    def test_ready_dn_rejected(self):
        """Cannot return from a READY DN."""
        token, _ = register_user("f59_3@test.com")
        biz_id = create_business(token, "F59 DN Ready")
        br_id, wh_id, loc_id, cust_id, uid = setup_f59_infra(token, biz_id)
        prod_id = f59_product(token, biz_id, uid)
        f59_stock(token, biz_id, loc_id, prod_id)
        sales_id, sline_id = create_finalized_sales(token, biz_id, br_id, prod_id, qty="10")

        so_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders", headers=auth(token), json={
            "customer_id": cust_id, "branch_id": br_id, "warehouse_id": wh_id,
            "order_date": datetime.now(timezone.utc).isoformat(),
        })
        so_id = so_resp.json()["id"]
        so_line_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/lines", headers=auth(token), json={
            "product_id": prod_id, "quantity": "10", "unit_price": "5000",
        })
        so_line_id = so_line_resp.json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/confirm", headers=auth(token))
        _, dn_id, dn_line_id = f59_create_dn_status(token, biz_id, so_id, br_id, so_line_id, 5, cust_id, "READY")

        sr_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-returns", headers=auth(token), json={
            "sales_id": sales_id, "inventory_location_id": loc_id,
        })
        sr_id = sr_resp.json()["id"]
        lr = client.post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id}/lines", headers=auth(token), json={
            "sales_line_id": sline_id, "quantity": "2",
            "delivery_note_id": dn_id, "delivery_note_line_id": dn_line_id,
        })
        assert lr.status_code == 400
        assert "DELIVERED" in lr.json()["message"]

    def test_cancelled_dn_rejected(self):
        """Cannot return from a CANCELLED DN."""
        token, _ = register_user("f59_4@test.com")
        biz_id = create_business(token, "F59 DN Cancel")
        br_id, wh_id, loc_id, cust_id, uid = setup_f59_infra(token, biz_id)
        prod_id = f59_product(token, biz_id, uid)
        f59_stock(token, biz_id, loc_id, prod_id)
        sales_id, sline_id = create_finalized_sales(token, biz_id, br_id, prod_id, qty="10")

        so_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders", headers=auth(token), json={
            "customer_id": cust_id, "branch_id": br_id, "warehouse_id": wh_id,
            "order_date": datetime.now(timezone.utc).isoformat(),
        })
        so_id = so_resp.json()["id"]
        so_line_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/lines", headers=auth(token), json={
            "product_id": prod_id, "quantity": "10", "unit_price": "5000",
        })
        so_line_id = so_line_resp.json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/confirm", headers=auth(token))
        _, dn_id, dn_line_id = f59_create_dn_status(token, biz_id, so_id, br_id, so_line_id, 5, cust_id, "CANCELLED")

        sr_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-returns", headers=auth(token), json={
            "sales_id": sales_id, "inventory_location_id": loc_id,
        })
        sr_id = sr_resp.json()["id"]
        lr = client.post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id}/lines", headers=auth(token), json={
            "sales_line_id": sline_id, "quantity": "2",
            "delivery_note_id": dn_id, "delivery_note_line_id": dn_line_id,
        })
        assert lr.status_code == 400
        assert "DELIVERED" in lr.json()["message"]

    def test_return_exceeding_dn_delivered_rejected(self):
        """Return quantity exceeding DN delivered quantity is rejected."""
        token, _ = register_user("f59_5@test.com")
        biz_id = create_business(token, "F59 DN Over")
        br_id, wh_id, loc_id, cust_id, uid = setup_f59_infra(token, biz_id)
        prod_id = f59_product(token, biz_id, uid)
        f59_stock(token, biz_id, loc_id, prod_id)
        sales_id, sline_id = create_finalized_sales(token, biz_id, br_id, prod_id, qty="10")

        so_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders", headers=auth(token), json={
            "customer_id": cust_id, "branch_id": br_id, "warehouse_id": wh_id,
            "order_date": datetime.now(timezone.utc).isoformat(),
        })
        so_id = so_resp.json()["id"]
        so_line_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/lines", headers=auth(token), json={
            "product_id": prod_id, "quantity": "10", "unit_price": "5000",
        })
        so_line_id = so_line_resp.json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/confirm", headers=auth(token))
        _, dn_id, dn_line_id = f59_create_delivered_dn(token, biz_id, so_id, br_id, so_line_id, 4, cust_id)

        sr_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-returns", headers=auth(token), json={
            "sales_id": sales_id, "inventory_location_id": loc_id,
        })
        sr_id = sr_resp.json()["id"]
        lr = client.post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id}/lines", headers=auth(token), json={
            "sales_line_id": sline_id, "quantity": "5",
            "delivery_note_id": dn_id, "delivery_note_line_id": dn_line_id,
        })
        assert lr.status_code == 400
        assert "returnable" in lr.json()["message"].lower()

    def test_multiple_returns_same_dn_line(self):
        """Multiple returns against the same DN line reconcile correctly."""
        token, _ = register_user("f59_6@test.com")
        biz_id = create_business(token, "F59 Multi")
        br_id, wh_id, loc_id, cust_id, uid = setup_f59_infra(token, biz_id)
        prod_id = f59_product(token, biz_id, uid)
        f59_stock(token, biz_id, loc_id, prod_id)
        sales_id, sline_id = create_finalized_sales(token, biz_id, br_id, prod_id, qty="10")

        so_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders", headers=auth(token), json={
            "customer_id": cust_id, "branch_id": br_id, "warehouse_id": wh_id,
            "order_date": datetime.now(timezone.utc).isoformat(),
        })
        so_id = so_resp.json()["id"]
        so_line_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/lines", headers=auth(token), json={
            "product_id": prod_id, "quantity": "10", "unit_price": "5000",
        })
        so_line_id = so_line_resp.json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/confirm", headers=auth(token))
        _, dn_id, dn_line_id = f59_create_delivered_dn(token, biz_id, so_id, br_id, so_line_id, 10, cust_id)

        # Return 6
        sr1_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-returns", headers=auth(token), json={
            "sales_id": sales_id, "inventory_location_id": loc_id,
        })
        sr1_id = sr1_resp.json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr1_id}/lines", headers=auth(token), json={
            "sales_line_id": sline_id, "quantity": "6",
            "delivery_note_id": dn_id, "delivery_note_line_id": dn_line_id,
        })
        fin1 = client.post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr1_id}/finalize", headers=auth(token))
        assert fin1.status_code == 200

        # Return 4 (remaining)
        sr2_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-returns", headers=auth(token), json={
            "sales_id": sales_id, "inventory_location_id": loc_id,
        })
        sr2_id = sr2_resp.json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr2_id}/lines", headers=auth(token), json={
            "sales_line_id": sline_id, "quantity": "4",
            "delivery_note_id": dn_id, "delivery_note_line_id": dn_line_id,
        })
        fin2 = client.post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr2_id}/finalize", headers=auth(token))
        assert fin2.status_code == 200

        # Return 1 (no capacity)
        sr3_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-returns", headers=auth(token), json={
            "sales_id": sales_id, "inventory_location_id": loc_id,
        })
        sr3_id = sr3_resp.json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr3_id}/lines", headers=auth(token), json={
            "sales_line_id": sline_id, "quantity": "1",
            "delivery_note_id": dn_id, "delivery_note_line_id": dn_line_id,
        })
        fin3 = client.post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr3_id}/finalize", headers=auth(token))
        assert fin3.status_code == 400

    def test_multiple_dn_lines_return(self):
        """Return spanning multiple DN lines as separate return lines."""
        token, _ = register_user("f59_7@test.com")
        biz_id = create_business(token, "F59 2DN")
        br_id, wh_id, loc_id, cust_id, uid = setup_f59_infra(token, biz_id)
        prod_id = f59_product(token, biz_id, uid)
        f59_stock(token, biz_id, loc_id, prod_id)
        sales_id, sline_id = create_finalized_sales(token, biz_id, br_id, prod_id, qty="10")

        so_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders", headers=auth(token), json={
            "customer_id": cust_id, "branch_id": br_id, "warehouse_id": wh_id,
            "order_date": datetime.now(timezone.utc).isoformat(),
        })
        so_id = so_resp.json()["id"]
        so_line_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/lines", headers=auth(token), json={
            "product_id": prod_id, "quantity": "10", "unit_price": "5000",
        })
        so_line_id = so_line_resp.json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/confirm", headers=auth(token))
        _, dn1_id, dn1_line_id = f59_create_delivered_dn(token, biz_id, so_id, br_id, so_line_id, 4, cust_id)
        _, dn2_id, dn2_line_id = f59_create_delivered_dn(token, biz_id, so_id, br_id, so_line_id, 6, cust_id)

        sr_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-returns", headers=auth(token), json={
            "sales_id": sales_id, "inventory_location_id": loc_id,
        })
        sr_id = sr_resp.json()["id"]
        lr1 = client.post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id}/lines", headers=auth(token), json={
            "sales_line_id": sline_id, "quantity": "2",
            "delivery_note_id": dn1_id, "delivery_note_line_id": dn1_line_id,
        })
        assert lr1.status_code == 201
        lr2 = client.post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id}/lines", headers=auth(token), json={
            "sales_line_id": sline_id, "quantity": "3",
            "delivery_note_id": dn2_id, "delivery_note_line_id": dn2_line_id,
        })
        assert lr2.status_code == 201
        fin = client.post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id}/finalize", headers=auth(token))
        assert fin.status_code == 200

    def test_per_dn_over_return_rejected(self):
        """Individual DN line return exceeding its delivered quantity rejected."""
        token, _ = register_user("f59_8@test.com")
        biz_id = create_business(token, "F59 PerDN")
        br_id, wh_id, loc_id, cust_id, uid = setup_f59_infra(token, biz_id)
        prod_id = f59_product(token, biz_id, uid)
        f59_stock(token, biz_id, loc_id, prod_id)
        sales_id, sline_id = create_finalized_sales(token, biz_id, br_id, prod_id, qty="10")

        so_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders", headers=auth(token), json={
            "customer_id": cust_id, "branch_id": br_id, "warehouse_id": wh_id,
            "order_date": datetime.now(timezone.utc).isoformat(),
        })
        so_id = so_resp.json()["id"]
        so_line_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/lines", headers=auth(token), json={
            "product_id": prod_id, "quantity": "10", "unit_price": "5000",
        })
        so_line_id = so_line_resp.json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/confirm", headers=auth(token))
        _, dn_id, dn_line_id = f59_create_delivered_dn(token, biz_id, so_id, br_id, so_line_id, 3, cust_id)

        sr_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-returns", headers=auth(token), json={
            "sales_id": sales_id, "inventory_location_id": loc_id,
        })
        sr_id = sr_resp.json()["id"]
        lr = client.post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id}/lines", headers=auth(token), json={
            "sales_line_id": sline_id, "quantity": "4",
            "delivery_note_id": dn_id, "delivery_note_line_id": dn_line_id,
        })
        assert lr.status_code == 400
        assert "returnable" in lr.json()["message"].lower()

    def test_aggregate_over_return_rejected(self):
        """New linked returns exceeding aggregate delivered capacity rejected."""
        token, _ = register_user("f59_9@test.com")
        biz_id = create_business(token, "F59 Agg")
        br_id, wh_id, loc_id, cust_id, uid = setup_f59_infra(token, biz_id)
        prod_id = f59_product(token, biz_id, uid)
        f59_stock(token, biz_id, loc_id, prod_id)
        sales_id, sline_id = create_finalized_sales(token, biz_id, br_id, prod_id, qty="10")

        so_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders", headers=auth(token), json={
            "customer_id": cust_id, "branch_id": br_id, "warehouse_id": wh_id,
            "order_date": datetime.now(timezone.utc).isoformat(),
        })
        so_id = so_resp.json()["id"]
        so_line_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/lines", headers=auth(token), json={
            "product_id": prod_id, "quantity": "10", "unit_price": "5000",
        })
        so_line_id = so_line_resp.json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/confirm", headers=auth(token))
        _, dn1_id, dn1_line_id = f59_create_delivered_dn(token, biz_id, so_id, br_id, so_line_id, 4, cust_id)
        _, dn2_id, dn2_line_id = f59_create_delivered_dn(token, biz_id, so_id, br_id, so_line_id, 6, cust_id)

        # Historical unlinked return of 3
        sr0_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-returns", headers=auth(token), json={
            "sales_id": sales_id, "inventory_location_id": loc_id,
        })
        sr0_id = sr0_resp.json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr0_id}/lines", headers=auth(token), json={
            "sales_line_id": sline_id, "quantity": "3",
        })
        fin0 = client.post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr0_id}/finalize", headers=auth(token))
        assert fin0.status_code == 200

        # Aggregate delivered=10, historical_unlinked=3, remaining=7. Try 4+4=8>7
        sr_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-returns", headers=auth(token), json={
            "sales_id": sales_id, "inventory_location_id": loc_id,
        })
        sr_id = sr_resp.json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id}/lines", headers=auth(token), json={
            "sales_line_id": sline_id, "quantity": "4",
            "delivery_note_id": dn1_id, "delivery_note_line_id": dn1_line_id,
        })
        lr2 = client.post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id}/lines", headers=auth(token), json={
            "sales_line_id": sline_id, "quantity": "4",
            "delivery_note_id": dn2_id, "delivery_note_line_id": dn2_line_id,
        })
        assert lr2.status_code == 400
        assert "returnable" in lr2.json()["message"].lower()

    def test_cross_business_dn_rejected(self):
        """Return referencing another business's DN is rejected."""
        token1, _ = register_user("f59_10@test.com")
        biz1 = create_business(token1, "F59 CrossBiz1")
        br1, wh1, loc1, cust1, uid1 = setup_f59_infra(token1, biz1)
        prod1 = f59_product(token1, biz1, uid1)
        f59_stock(token1, biz1, loc1, prod1)
        sales1_id, sline1_id = create_finalized_sales(token1, biz1, br1, prod1, qty="10")
        so1_resp = client.post(f"/api/v1/businesses/{biz1}/sales-orders", headers=auth(token1), json={
            "customer_id": cust1, "branch_id": br1, "warehouse_id": wh1,
            "order_date": datetime.now(timezone.utc).isoformat(),
        })
        so1_id = so1_resp.json()["id"]
        so1_line_resp = client.post(f"/api/v1/businesses/{biz1}/sales-orders/{so1_id}/lines", headers=auth(token1), json={
            "product_id": prod1, "quantity": "10", "unit_price": "5000",
        })
        so1_line_id = so1_line_resp.json()["id"]
        client.post(f"/api/v1/businesses/{biz1}/sales-orders/{so1_id}/confirm", headers=auth(token1))
        _, dn1_id, dn1_line_id = f59_create_delivered_dn(token1, biz1, so1_id, br1, so1_line_id, 10, cust1)

        token2, _ = register_user("f59_11@test.com")
        biz2 = create_business(token2, "F59 CrossBiz2")
        br2, wh2, loc2, cust2, uid2 = setup_f59_infra(token2, biz2)
        prod2 = f59_product(token2, biz2, uid2)
        f59_stock(token2, biz2, loc2, prod2)
        sales2_id, sline2_id = create_finalized_sales(token2, biz2, br2, prod2, qty="10")

        # Biz2 tries to reference Biz1's DN
        sr_resp = client.post(f"/api/v1/businesses/{biz2}/sales-returns", headers=auth(token2), json={
            "sales_id": sales2_id, "inventory_location_id": loc2,
        })
        sr_id = sr_resp.json()["id"]
        lr = client.post(f"/api/v1/businesses/{biz2}/sales-returns/{sr_id}/lines", headers=auth(token2), json={
            "sales_line_id": sline2_id, "quantity": "2",
            "delivery_note_id": dn1_id, "delivery_note_line_id": dn1_line_id,
        })
        assert lr.status_code in (400, 404)


# ====================================================================
# FEATURE #59 — ATOMICITY / ROLLBACK TESTS
# ====================================================================

class TestFeature59Atomicity:
    """Rollback / zero-net-mutation tests for finalize_return()."""

    @pytest.fixture
    def f59_setup(self):
        """Create a complete F59 test scenario with SO → DN → SalesReturn."""
        token, _ = register_user("f59_atomic@test.com")
        biz_id = create_business(token, "F59 Atomic")
        br_id, wh_id, loc_id, cust_id, uid = setup_f59_infra(token, biz_id)
        prod_id = f59_product(token, biz_id, uid)
        f59_stock(token, biz_id, loc_id, prod_id)
        sales_id, sline_id = create_finalized_sales(token, biz_id, br_id, prod_id, qty="10")

        # Create SO + DN (delivered via Feature #58)
        so_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders", headers=auth(token), json={
            "customer_id": cust_id, "branch_id": br_id, "warehouse_id": wh_id,
            "order_date": datetime.now(timezone.utc).isoformat(),
        })
        so_id = so_resp.json()["id"]
        so_line_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/lines", headers=auth(token), json={
            "product_id": prod_id, "quantity": "10", "unit_price": "5000",
        })
        so_line_id = so_line_resp.json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/sales-orders/{so_id}/confirm", headers=auth(token))
        dn_json, dn_id, dn_line_id = f59_create_delivered_dn(token, biz_id, so_id, br_id, so_line_id, 10, cust_id)

        # Create SalesReturn with DN-linked line
        sr_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-returns", headers=auth(token), json={
            "sales_id": sales_id, "inventory_location_id": loc_id, "notes": "Atomic test",
        })
        sr_id = sr_resp.json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id}/lines", headers=auth(token), json={
            "sales_line_id": sline_id, "quantity": "3",
            "delivery_note_id": dn_id, "delivery_note_line_id": dn_line_id,
        })

        return {
            "token": token, "biz_id": biz_id, "br_id": br_id, "loc_id": loc_id,
            "prod_id": prod_id, "sales_id": sales_id, "sline_id": sline_id,
            "so_id": so_id, "so_line_id": so_line_id, "dn_id": dn_id,
            "dn_line_id": dn_line_id, "sr_id": sr_id,
        }

    def _noclient(self):
        """TestClient that does NOT re-raise server exceptions — returns status 500."""
        return TestClient(app, raise_server_exceptions=False)

    def _snapshot_repos(self, biz_id):
        """Capture pre-finalization state of all mutable repositories."""
        from app.modules.accounting.repository import accounting_repository
        from app.modules.inventory.repository import (
            stock_balance_repository, stock_movement_repository, inventory_cost_repository
        )
        from app.modules.sales_return.repository import sales_return_repository

        return {
            "sr_returns": {k: v.model_copy() for k, v in sales_return_repository._returns.items()},
            "sr_lines": {k: v.model_copy() for k, v in sales_return_repository._lines.items()},
            "journals": {k: v.model_copy() for k, v in accounting_repository._journals.items()},
            "journal_lines": {k: v.model_copy() for k, v in accounting_repository._journal_lines.items()},
            "acct_sequences": dict(accounting_repository._sequences),
            "balances": {k: v.model_copy() for k, v in stock_balance_repository._balances.items()},
            "movements": {k: v.model_copy() for k, v in stock_movement_repository._movements.items()},
            "movement_lines": [l.model_copy() for l in stock_movement_repository._lines],
            "cost_states": {k: v.model_copy() for k, v in inventory_cost_repository._cost_states.items()},
            "cost_movements": [l.model_copy() for l in inventory_cost_repository._cost_movements],
        }

    def _assert_repos_equal(self, before, after, msg="Repository state mismatch"):
        """Assert all repository collections are exactly equal to pre-state."""
        assert before["sr_returns"] == after["sr_returns"], f"{msg}: sr_returns"
        assert before["sr_lines"] == after["sr_lines"], f"{msg}: sr_lines"
        assert before["journals"] == after["journals"], f"{msg}: journals"
        assert before["journal_lines"] == after["journal_lines"], f"{msg}: journal_lines"
        assert before["acct_sequences"] == after["acct_sequences"], f"{msg}: acct_sequences"
        assert before["balances"] == after["balances"], f"{msg}: balances"
        assert before["movements"] == after["movements"], f"{msg}: movements"
        assert before["movement_lines"] == after["movement_lines"], f"{msg}: movement_lines"
        assert before["cost_states"] == after["cost_states"], f"{msg}: cost_states"
        assert before["cost_movements"] == after["cost_movements"], f"{msg}: cost_movements"

    # TEST 1: Accounting succeeds → inventory fails
    def test_rollback_accounting_then_inventory_fail(self, f59_setup):
        token = f59_setup["token"]
        biz_id = f59_setup["biz_id"]
        sr_id = f59_setup["sr_id"]

        pre = self._snapshot_repos(biz_id)

        # Inject failure in return_sales_stock AFTER accounting succeeds
        from app.modules.inventory.service import inventory_service

        async def failing_return_stock(*args, **kwargs):
            raise RuntimeError("INJECTED: inventory failure after accounting")

        with patch.object(inventory_service, "return_sales_stock", new=failing_return_stock):
            fin = self._noclient().post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id}/finalize", headers=auth(token))
            assert fin.status_code == 500

        post = self._snapshot_repos(biz_id)
        self._assert_repos_equal(pre, post, "TEST 1: accounting→inventory failure")

        # Return must remain DRAFT
        sr = client.get(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id}", headers=auth(token)).json()
        assert sr["status"] == "DRAFT"

        # Retry succeeds cleanly
        fin2 = client.post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id}/finalize", headers=auth(token))
        assert fin2.status_code == 200
        assert fin2.json()["status"] == "FINALIZED"

    # TEST 2: Accounting + stock succeed → MAC fails (multi-line with two products)
    def test_rollback_accounting_stock_then_mac_fail(self):
        """Use two finalized sales of different products so we can add both lines to one return."""
        token, _ = register_user("f59_mac@test.com")
        biz_id = create_business(token, "F59 MAC")
        br_id, wh_id, loc_id, cust_id, uid = setup_f59_infra(token, biz_id)
        prod1 = f59_product(token, biz_id, uid, "Product1", "P1")
        prod2 = f59_product(token, biz_id, uid, "Product2", "P2")
        f59_stock(token, biz_id, loc_id, prod1)
        f59_stock(token, biz_id, loc_id, prod2)

        # Create two separate finalized sales (one per product)
        sales1_id, sline1_id = create_finalized_sales(token, biz_id, br_id, prod1, qty="10")
        sales2_id, sline2_id = create_finalized_sales(token, biz_id, br_id, prod2, qty="10")

        # Create SalesReturn referencing sales1 (which has prod1 line)
        sr_resp = client.post(f"/api/v1/businesses/{biz_id}/sales-returns", headers=auth(token), json={
            "sales_id": sales1_id, "inventory_location_id": loc_id,
        })
        sr_id = sr_resp.json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id}/lines", headers=auth(token), json={
            "sales_line_id": sline1_id, "quantity": "2",
        })

        # Now manually add a second product line referencing sales2's line (different product)
        # This won't work via API since sales_id mismatch is checked. Instead use two returns:
        # Just test with a single product line - MAC call_count=1 fails.
        # Actually, for multi-line MAC test, create return with TWO lines from same sales
        # by using partial qty each time. But duplicate check prevents same sales_line_id.
        # Solution: use two different products in the same finalized sales.
        # Need to create a multi-line sales BEFORE finalizing.

        # Create a NEW sales with two products before finalizing
        s3_resp = client.post(f"/api/v1/businesses/{biz_id}/sales", headers=auth(token), json={
            "branch_id": br_id, "sales_date": datetime.now(timezone.utc).isoformat(),
        })
        s3_id = s3_resp.json()["id"]
        sl3a = client.post(f"/api/v1/businesses/{biz_id}/sales/{s3_id}/lines", headers=auth(token), json={
            "product_id": prod1, "quantity": "10", "unit_price": "5000",
        }).json()["id"]
        sl3b = client.post(f"/api/v1/businesses/{biz_id}/sales/{s3_id}/lines", headers=auth(token), json={
            "product_id": prod2, "quantity": "10", "unit_price": "6000",
        }).json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/sales/{s3_id}/finalize", headers=auth(token))

        # Create return with two lines from the multi-line sales
        sr_resp2 = client.post(f"/api/v1/businesses/{biz_id}/sales-returns", headers=auth(token), json={
            "sales_id": s3_id, "inventory_location_id": loc_id,
        })
        sr_id2 = sr_resp2.json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id2}/lines", headers=auth(token), json={
            "sales_line_id": sl3a, "quantity": "2",
        })
        client.post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id2}/lines", headers=auth(token), json={
            "sales_line_id": sl3b, "quantity": "2",
        })

        pre = self._snapshot_repos(biz_id)

        # Inject failure on SECOND call to record_cost_inbound
        from app.modules.inventory.service import inventory_service
        original_record_cost = inventory_service.record_cost_inbound
        call_count = {"n": 0}

        async def failing_record_cost(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise RuntimeError("INJECTED: MAC failure on second line")
            return await original_record_cost(*args, **kwargs)

        with patch.object(inventory_service, "record_cost_inbound", new=failing_record_cost):
            fin = self._noclient().post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id2}/finalize", headers=auth(token))
            assert fin.status_code == 500

        post = self._snapshot_repos(biz_id)
        self._assert_repos_equal(pre, post, "TEST 2: accounting+stock→MAC failure")

        sr = client.get(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id2}", headers=auth(token)).json()
        assert sr["status"] == "DRAFT"

        # Retry succeeds
        fin2 = client.post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id2}/finalize", headers=auth(token))
        assert fin2.status_code == 200
        assert fin2.json()["status"] == "FINALIZED"

    # TEST 3: All mutations succeed → final SalesReturn update fails
    def test_rollback_all_then_status_update_fail(self, f59_setup):
        token = f59_setup["token"]
        biz_id = f59_setup["biz_id"]
        sr_id = f59_setup["sr_id"]

        pre = self._snapshot_repos(biz_id)

        # Inject failure ONLY in the final status update by patching after _recalculate_totals
        from app.modules.sales_return.service import sales_return_service
        original_finalize = sales_return_service.finalize_return

        call_step = {"n": 0}
        original_update = None

        # We need a different approach: intercept the specific update_return call
        # that sets status=FINALIZED. Patch update_return to fail only when status arg is FINALIZED.
        from app.modules.sales_return.repository import sales_return_repository
        real_update = sales_return_repository.update_return

        async def selective_update(*args, **kwargs):
            if kwargs.get("status") == SalesReturnStatus.FINALIZED:
                raise RuntimeError("INJECTED: final status update failure")
            return await real_update(*args, **kwargs)

        with patch.object(sales_return_repository, "update_return", new=selective_update):
            fin = self._noclient().post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id}/finalize", headers=auth(token))
            assert fin.status_code == 500

        post = self._snapshot_repos(biz_id)
        self._assert_repos_equal(pre, post, "TEST 3: all→status failure")

        sr = client.get(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id}", headers=auth(token)).json()
        assert sr["status"] == "DRAFT"

        # Retry succeeds
        fin2 = client.post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id}/finalize", headers=auth(token))
        assert fin2.status_code == 200
        assert fin2.json()["status"] == "FINALIZED"

    # TEST 4: Totals mutation rollback
    def test_rollback_recalculate_totals_failure(self, f59_setup):
        token = f59_setup["token"]
        biz_id = f59_setup["biz_id"]
        sr_id = f59_setup["sr_id"]

        pre = self._snapshot_repos(biz_id)

        # Inject failure right after _recalculate_totals mutates totals.
        # The mock calls original which mutates the return, then raises.
        from app.modules.sales_return.service import sales_return_service
        original_recalc = sales_return_service._recalculate_totals

        async def failing_recalc(*args, **kwargs):
            await original_recalc(*args, **kwargs)  # Let totals be mutated
            raise RuntimeError("INJECTED: failure after totals mutation")

        with patch.object(sales_return_service, "_recalculate_totals", new=failing_recalc):
            fin = self._noclient().post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id}/finalize", headers=auth(token))
            assert fin.status_code == 500

        post = self._snapshot_repos(biz_id)
        self._assert_repos_equal(pre, post, "TEST 4: totals mutation rollback")

        sr = client.get(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id}", headers=auth(token)).json()
        assert sr["status"] == "DRAFT"
        # Totals must still equal the pre-finalize value (NOT zero, since add_line already recalculated them)
        assert Decimal(sr["subtotal"]) == Decimal(pre["sr_returns"][sr_id].subtotal)
        assert Decimal(sr["grand_total"]) == Decimal(pre["sr_returns"][sr_id].grand_total)

        # Retry succeeds
        fin2 = client.post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id}/finalize", headers=auth(token))
        assert fin2.status_code == 200
        assert fin2.json()["status"] == "FINALIZED"

    # TEST 5: Exact repository state comparison (comprehensive)
    def test_exact_repository_state_comparison(self, f59_setup):
        """Comprehensive equality check across all 10 collections."""
        token = f59_setup["token"]
        biz_id = f59_setup["biz_id"]
        sr_id = f59_setup["sr_id"]

        pre = self._snapshot_repos(biz_id)

        from app.modules.inventory.service import inventory_service
        async def fail_early(*args, **kwargs):
            raise RuntimeError("INJECTED: early failure")
        with patch.object(inventory_service, "return_sales_stock", new=fail_early):
            self._noclient().post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id}/finalize", headers=auth(token))

        post = self._snapshot_repos(biz_id)
        self._assert_repos_equal(pre, post, "TEST 5: exact repo equality")

    # TEST 6: Successful finalization persists everything
    def test_successful_finalization_persists_all(self, f59_setup):
        token = f59_setup["token"]
        biz_id = f59_setup["biz_id"]
        sr_id = f59_setup["sr_id"]

        fin = client.post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id}/finalize", headers=auth(token))
        assert fin.status_code == 200
        assert fin.json()["status"] == "FINALIZED"

        # Accounting journal exists
        mvts = client.get(f"/api/v1/businesses/{biz_id}/accounting/journals", headers=auth(token)).json()["items"]
        sr_journals = [j for j in mvts if j["reference_id"] == sr_id]
        assert len(sr_journals) == 1
        assert sr_journals[0]["status"] == "POSTED"

        # SALE_RETURN_IN movement exactly once
        movs = client.get(f"/api/v1/businesses/{biz_id}/inventory/movements?movement_type=SALE_RETURN_IN", headers=auth(token)).json()
        sr_movs = [m for m in movs if m["reference_id"] == sr_id]
        assert len(sr_movs) == 1

        # Stock: 200 opening - 10 (sales) - 10 (DN delivery) + 3 (return) = 183
        bal = client.get(f"/api/v1/businesses/{biz_id}/inventory/stock", headers=auth(token)).json()[0]["quantity"]
        assert Decimal(str(bal)) == Decimal("183")

    # TEST 7: Failure then retry produces exactly one of each
    def test_failure_then_retry_single_instance(self, f59_setup):
        token = f59_setup["token"]
        biz_id = f59_setup["biz_id"]
        sr_id = f59_setup["sr_id"]

        # First attempt fails after accounting
        from app.modules.inventory.service import inventory_service
        async def fail_after_acct(*args, **kwargs):
            raise RuntimeError("INJECTED: fail after accounting")
        with patch.object(inventory_service, "return_sales_stock", new=fail_after_acct):
            self._noclient().post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id}/finalize", headers=auth(token))

        # Second attempt succeeds
        fin2 = client.post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id}/finalize", headers=auth(token))
        assert fin2.status_code == 200
        assert fin2.json()["status"] == "FINALIZED"

        # Verify exactly ONE journal, ONE movement, ONE cost movement per line
        journals = client.get(f"/api/v1/businesses/{biz_id}/accounting/journals", headers=auth(token)).json()["items"]
        sr_journals = [j for j in journals if j["reference_id"] == sr_id]
        assert len(sr_journals) == 1

        movs = client.get(f"/api/v1/businesses/{biz_id}/inventory/movements?movement_type=SALE_RETURN_IN", headers=auth(token)).json()
        sr_movs = [m for m in movs if m["reference_id"] == sr_id]
        assert len(sr_movs) == 1

    # TEST 8: Concurrent finalization serialized
    def test_concurrent_finalization_serialized(self, f59_setup):
        token = f59_setup["token"]
        biz_id = f59_setup["biz_id"]
        sr_id = f59_setup["sr_id"]

        results = []

        def attempt_finalize():
            # Each thread gets its own TestClient (raise_server_exceptions=True is fine
            # since concurrent conflict gives 400/409, not 500)
            from fastapi.testclient import TestClient
            from app.main import app
            c = TestClient(app)
            r = c.post(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id}/finalize", headers=auth(token))
            results.append(r.status_code)

        import threading
        t1 = threading.Thread(target=attempt_finalize)
        t2 = threading.Thread(target=attempt_finalize)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # One succeeds (200), other gets conflict (400 or 409)
        assert 200 in results
        assert results.count(200) == 1
        failed = [r for r in results if r != 200]
        assert len(failed) == 1
        assert failed[0] in (400, 409)

        # Final state is FINALIZED exactly once
        sr = client.get(f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id}", headers=auth(token)).json()
        assert sr["status"] == "FINALIZED"

# ====================================================================
# FEATURE #59 — END
# ====================================================================

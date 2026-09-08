import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from app.main import app
from app.modules.authentication.repository import InMemoryUserRepository
from app.modules.account.repository import InMemoryAccountRepository
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

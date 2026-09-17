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
from app.modules.category.repository import InMemoryCategoryRepository
from app.modules.sales.repository import InMemorySalesRepository
from app.modules.sales_return.repository import InMemorySalesReturnRepository
from app.modules.warehouse.repository import InMemoryWarehouseRepository, InMemoryInventoryLocationRepository
from app.modules.inventory.repository import InMemoryStockBalanceRepository, InMemoryStockMovementRepository, InMemoryInventoryCostRepository
from app.modules.pricing.repository import InMemoryPriceListRepository, InMemoryPriceEntryRepository
from app.modules.accounting.repository import InMemoryAccountingRepository

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_repositories():
    InMemoryAccountingRepository.clear()
    InMemoryPriceEntryRepository.clear()
    InMemoryPriceListRepository.clear()
    InMemorySalesReturnRepository.clear()
    InMemoryStockBalanceRepository.clear()
    InMemoryStockMovementRepository.clear()
    InMemoryInventoryCostRepository.clear()
    InMemoryInventoryLocationRepository.clear()
    InMemoryWarehouseRepository.clear()
    InMemorySalesRepository.clear()
    InMemoryProductVariantRepository.clear()
    InMemoryProductRepository.clear()
    InMemoryCategoryRepository.clear()
    InMemoryUnitRepository.clear()
    InMemoryBranchRepository.clear()
    InMemoryCustomerRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryUserRepository.clear()
    yield
    InMemoryAccountingRepository.clear()
    InMemoryPriceEntryRepository.clear()
    InMemoryPriceListRepository.clear()
    InMemorySalesReturnRepository.clear()
    InMemoryStockBalanceRepository.clear()
    InMemoryStockMovementRepository.clear()
    InMemoryInventoryCostRepository.clear()
    InMemoryInventoryLocationRepository.clear()
    InMemoryWarehouseRepository.clear()
    InMemorySalesRepository.clear()
    InMemoryProductVariantRepository.clear()
    InMemoryProductRepository.clear()
    InMemoryCategoryRepository.clear()
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
        json={"email": email, "full_name": name, "password": "Password123", "password_confirmation": "Password123"},
    )
    assert res.status_code == 201
    data = res.json()
    token = data.get("access_token")
    if not token:
        login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123"})
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
    return token, data["id"]


def create_business(token, name="Test Business"):
    res = client.post(
        "/api/v1/businesses",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "legal_name": name, "business_type": "retail", "timezone": "UTC", "locale": "en-US"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_branch(token, bid, name="Branch A", code="BR-A"):
    res = client.post(
        f"/api/v1/businesses/{bid}/branches",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code},
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_unit(token, bid, name="Pcs", code="PCS"):
    res = client.post(
        f"/api/v1/businesses/{bid}/units",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code},
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_product(token, bid, unit_id, name="Product A", code="PRD-A", p_type="GOODS", category_id=None):
    payload = {"name": name, "code": code, "unit_id": unit_id, "product_type": p_type}
    if category_id:
        payload["category_id"] = category_id
    res = client.post(
        f"/api/v1/businesses/{bid}/products",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_category(token, bid, name="Category A", code="CAT-A"):
    res = client.post(
        f"/api/v1/businesses/{bid}/categories",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code},
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_customer(token, bid, name="Customer A", code="CUST-A"):
    res = client.post(
        f"/api/v1/businesses/{bid}/customers",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "customer_type": "ORGANIZATION"},
    )
    assert res.status_code == 201
    cid = res.json()["id"]
    client.put(f"/api/v1/businesses/{bid}/customers/{cid}/credit/limit", headers={"Authorization": f"Bearer {token}"}, json={"credit_limit": "100000000.00"})
    return cid


def setup_warehouse_and_location(token, bid, name="WH 1", code="WH-1", loc_name="LOC 1", loc_code="L1"):
    wh_res = client.post(
        f"/api/v1/businesses/{bid}/warehouses",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code},
    )
    assert wh_res.status_code == 201
    wh_id = wh_res.json()["id"]
    loc_res = client.post(
        f"/api/v1/businesses/{bid}/warehouses/{wh_id}/locations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": loc_name, "code": loc_code, "location_type": "GENERAL"},
    )
    assert loc_res.status_code == 201
    return loc_res.json()["id"]


def add_opening_stock(token, bid, location_id, product_id, variant_id=None, qty="100"):
    res = client.post(
        f"/api/v1/businesses/{bid}/inventory/opening-balance",
        headers={"Authorization": f"Bearer {token}"},
        json={"inventory_location_id": location_id, "product_id": product_id, "variant_id": variant_id, "quantity": qty},
    )
    assert res.status_code == 201


def create_finalized_sales(token, bid, br_id, prod_id, variant_id=None, qty="10", price="50000", cust_id=None):
    payload = {"branch_id": br_id, "sales_date": datetime.now(timezone.utc).isoformat()}
    if cust_id:
        payload["customer_id"] = cust_id
    s_res = client.post(
        f"/api/v1/businesses/{bid}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert s_res.status_code == 201
    sales_id = s_res.json()["id"]

    l_payload = {"product_id": prod_id, "quantity": qty, "unit_price": price}
    if variant_id:
        l_payload["variant_id"] = variant_id
        l_payload["product_id"] = None

    l_res = client.post(
        f"/api/v1/businesses/{bid}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json=l_payload,
    )
    assert l_res.status_code == 201
    sline_id = l_res.json()["id"]

    fin_res = client.post(
        f"/api/v1/businesses/{bid}/sales/{sales_id}/finalize",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fin_res.status_code == 200
    return sales_id, sline_id


def create_finalized_return(token, bid, sales_id, sline_id, return_qty="3"):
    ret_res = client.post(
        f"/api/v1/businesses/{bid}/sales-returns",
        headers={"Authorization": f"Bearer {token}"},
        json={"sales_id": sales_id},
    )
    assert ret_res.status_code == 201
    ret_id = ret_res.json()["id"]
    ret_line_res = client.post(
        f"/api/v1/businesses/{bid}/sales-returns/{ret_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"sales_line_id": sline_id, "quantity": return_qty},
    )
    assert ret_line_res.status_code == 201
    fin_ret = client.post(
        f"/api/v1/businesses/{bid}/sales-returns/{ret_id}/finalize",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fin_ret.status_code == 200
    return ret_id


def get_report(token, bid, **params):
    res = client.get(
        f"/api/v1/businesses/{bid}/reports/product-profitability",
        params=params,
        headers={"Authorization": f"Bearer {token}"},
    )
    return res


# ============================================================
# AUTH TESTS
# ============================================================
class TestAuth:
    def test_unauthenticated_rejected(self):
        res = client.get("/api/v1/businesses/any-id/reports/product-profitability")
        assert res.status_code == 401

    def test_authenticated_allowed(self):
        token, uid = register_user()
        bid = create_business(token)
        res = get_report(token, bid, date_from="2026-01-01", date_to="2026-12-31")
        assert res.status_code == 200

    def test_non_member_rejected(self):
        token, uid = register_user()
        bid = create_business(token)
        token2, _ = register_user(email="other@example.com", name="Other")
        res = get_report(token2, bid, date_from="2026-01-01", date_to="2026-12-31")
        assert res.status_code in (403, 404)


# ============================================================
# DATE TESTS
# ============================================================
class TestDateSemantics:
    def test_empty_when_no_sales(self):
        token, uid = register_user()
        bid = create_business(token)
        res = get_report(token, bid, date_from="2026-01-01", date_to="2026-12-31")
        assert res.status_code == 200
        data = res.json()
        assert data["items"] == []
        assert data["period"]["date_from"] == "2026-01-01"
        assert data["period"]["date_to"] == "2026-12-31"

    def test_date_from_date_to_inclusive(self):
        token, uid = register_user()
        bid = create_business(token)
        br_id = create_branch(token, bid)
        unit_id = create_unit(token, bid)
        prod_id = create_product(token, bid, unit_id)
        wh_loc = setup_warehouse_and_location(token, bid)
        add_opening_stock(token, bid, wh_loc, prod_id, qty="100")
        create_finalized_sales(token, bid, br_id, prod_id, qty="1", price="50000")

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        res = get_report(token, bid, date_from=today, date_to=today)
        assert res.status_code == 200
        assert len(res.json()["items"]) == 1

    def test_only_date_from_rejected(self):
        token, uid = register_user()
        bid = create_business(token)
        res = get_report(token, bid, date_from="2026-01-01")
        assert res.status_code == 422

    def test_only_date_to_rejected(self):
        token, uid = register_user()
        bid = create_business(token)
        res = get_report(token, bid, date_to="2026-12-31")
        assert res.status_code == 422

    def test_date_from_gt_date_to_rejected(self):
        token, uid = register_user()
        bid = create_business(token)
        res = get_report(token, bid, date_from="2026-12-31", date_to="2026-01-01")
        assert res.status_code == 422

    def test_no_dates_no_period_rejected(self):
        token, uid = register_user()
        bid = create_business(token)
        res = client.get(
            f"/api/v1/businesses/{bid}/reports/product-profitability",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 422


# ============================================================
# GROUP-BY TESTS
# ============================================================
class TestGroupBy:
    def test_group_by_product(self):
        token, uid = register_user()
        bid = create_business(token)
        br_id = create_branch(token, bid)
        unit_id = create_unit(token, bid)
        prod_id = create_product(token, bid, unit_id, name="Widget", code="W1")
        wh_loc = setup_warehouse_and_location(token, bid)
        add_opening_stock(token, bid, wh_loc, prod_id, qty="100")
        create_finalized_sales(token, bid, br_id, prod_id, qty="5", price="50000")

        res = get_report(token, bid, date_from="2026-01-01", date_to="2099-12-31", group_by="product")
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 1
        assert items[0]["group_id"] == prod_id
        assert items[0]["group_name"] == "Widget"

    def test_group_by_category(self):
        token, uid = register_user()
        bid = create_business(token)
        br_id = create_branch(token, bid)
        unit_id = create_unit(token, bid)
        cat_id = create_category(token, bid, name="Electronics", code="ELEC")
        prod_id = create_product(token, bid, unit_id, name="Widget", code="W1", category_id=cat_id)
        wh_loc = setup_warehouse_and_location(token, bid)
        add_opening_stock(token, bid, wh_loc, prod_id, qty="100")
        create_finalized_sales(token, bid, br_id, prod_id, qty="5", price="50000")

        res = get_report(token, bid, date_from="2026-01-01", date_to="2099-12-31", group_by="category")
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 1
        assert items[0]["group_id"] == cat_id
        assert items[0]["group_name"] == "Electronics"

    def test_group_by_customer(self):
        token, uid = register_user()
        bid = create_business(token)
        br_id = create_branch(token, bid)
        unit_id = create_unit(token, bid)
        cust_id = create_customer(token, bid, name="PT Maju", code="C1")
        prod_id = create_product(token, bid, unit_id)
        wh_loc = setup_warehouse_and_location(token, bid)
        add_opening_stock(token, bid, wh_loc, prod_id, qty="100")
        create_finalized_sales(token, bid, br_id, prod_id, qty="5", price="50000", cust_id=cust_id)

        res = get_report(token, bid, date_from="2026-01-01", date_to="2099-12-31", group_by="customer")
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 1
        assert items[0]["group_id"] == cust_id
        assert items[0]["group_name"] == "PT Maju"

    def test_invalid_group_by_rejected(self):
        token, uid = register_user()
        bid = create_business(token)
        res = get_report(token, bid, date_from="2026-01-01", date_to="2026-12-31", group_by="invalid")
        assert res.status_code == 422


# ============================================================
# WALK-IN TESTS
# ============================================================
class TestWalkIn:
    def test_walk_in_grouped_correctly(self):
        token, uid = register_user()
        bid = create_business(token)
        br_id = create_branch(token, bid)
        unit_id = create_unit(token, bid)
        prod_id = create_product(token, bid, unit_id)
        wh_loc = setup_warehouse_and_location(token, bid)
        add_opening_stock(token, bid, wh_loc, prod_id, qty="100")
        create_finalized_sales(token, bid, br_id, prod_id, qty="5", price="50000")

        res = get_report(token, bid, date_from="2026-01-01", date_to="2099-12-31", group_by="customer")
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 1
        assert items[0]["group_id"] == "walk-in"
        assert items[0]["group_name"] == "Walk-in / Cash Sales"

    def test_walk_in_filter(self):
        token, uid = register_user()
        bid = create_business(token)
        br_id = create_branch(token, bid)
        unit_id = create_unit(token, bid)
        cust_id = create_customer(token, bid)
        prod_id = create_product(token, bid, unit_id)
        wh_loc = setup_warehouse_and_location(token, bid)
        add_opening_stock(token, bid, wh_loc, prod_id, qty="100")
        create_finalized_sales(token, bid, br_id, prod_id, qty="5", price="50000")
        create_finalized_sales(token, bid, br_id, prod_id, qty="3", price="50000", cust_id=cust_id)

        res = get_report(token, bid, date_from="2026-01-01", date_to="2099-12-31", group_by="customer", customer_id="walk-in")
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 1
        assert items[0]["group_id"] == "walk-in"


# ============================================================
# RETURN TESTS
# ============================================================
class TestReturns:
    def test_finalized_return_reduces_revenue(self):
        token, uid = register_user()
        bid = create_business(token)
        br_id = create_branch(token, bid)
        unit_id = create_unit(token, bid)
        prod_id = create_product(token, bid, unit_id)
        wh_loc = setup_warehouse_and_location(token, bid)
        add_opening_stock(token, bid, wh_loc, prod_id, qty="100")
        sales_id, sline_id = create_finalized_sales(token, bid, br_id, prod_id, qty="10", price="50000")
        create_finalized_return(token, bid, sales_id, sline_id, return_qty="3")

        res = get_report(token, bid, date_from="2026-01-01", date_to="2099-12-31", group_by="product")
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 1
        assert Decimal(items[0]["units_sold"]) == Decimal("10")
        assert Decimal(items[0]["units_returned"]) == Decimal("3")
        assert items[0]["return_count"] == 1

    def test_draft_return_excluded(self):
        token, uid = register_user()
        bid = create_business(token)
        br_id = create_branch(token, bid)
        unit_id = create_unit(token, bid)
        prod_id = create_product(token, bid, unit_id)
        wh_loc = setup_warehouse_and_location(token, bid)
        add_opening_stock(token, bid, wh_loc, prod_id, qty="100")
        sales_id, sline_id = create_finalized_sales(token, bid, br_id, prod_id, qty="10", price="50000")

        ret_res = client.post(
            f"/api/v1/businesses/{bid}/sales-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_id": sales_id},
        )
        assert ret_res.status_code == 201
        ret_id = ret_res.json()["id"]
        client.post(
            f"/api/v1/businesses/{bid}/sales-returns/{ret_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_line_id": sline_id, "quantity": "3"},
        )

        res = get_report(token, bid, date_from="2026-01-01", date_to="2099-12-31", group_by="product")
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 1
        assert Decimal(items[0]["units_returned"]) == Decimal("0")
        assert items[0]["return_count"] == 0

    def test_multiple_returns_unique_count(self):
        token, uid = register_user()
        bid = create_business(token)
        br_id = create_branch(token, bid)
        unit_id = create_unit(token, bid)
        prod_id = create_product(token, bid, unit_id)
        wh_loc = setup_warehouse_and_location(token, bid)
        add_opening_stock(token, bid, wh_loc, prod_id, qty="100")
        sales_id, sline_id = create_finalized_sales(token, bid, br_id, prod_id, qty="10", price="50000")
        create_finalized_return(token, bid, sales_id, sline_id, return_qty="2")
        create_finalized_return(token, bid, sales_id, sline_id, return_qty="2")

        res = get_report(token, bid, date_from="2026-01-01", date_to="2099-12-31", group_by="product")
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 1
        assert Decimal(items[0]["units_returned"]) == Decimal("4")
        assert items[0]["return_count"] == 2

    def test_return_uses_historical_cost_snapshot(self):
        token, uid = register_user()
        bid = create_business(token)
        br_id = create_branch(token, bid)
        unit_id = create_unit(token, bid)
        prod_id = create_product(token, bid, unit_id)
        wh_loc = setup_warehouse_and_location(token, bid)
        add_opening_stock(token, bid, wh_loc, prod_id, qty="100")
        sales_id, sline_id = create_finalized_sales(token, bid, br_id, prod_id, qty="10", price="50000")
        create_finalized_return(token, bid, sales_id, sline_id, return_qty="5")

        res = get_report(token, bid, date_from="2026-01-01", date_to="2099-12-31", group_by="product")
        assert res.status_code == 200
        item = res.json()["items"][0]
        assert Decimal(item["units_sold"]) == Decimal("10")
        assert Decimal(item["units_returned"]) == Decimal("5")
        assert item["return_count"] == 1


# ============================================================
# RETURN ATTRIBUTION TESTS
# ============================================================
class TestReturnAttribution:
    def test_return_attribution_follows_original_product(self):
        token, uid = register_user()
        bid = create_business(token)
        br_id = create_branch(token, bid)
        unit_id = create_unit(token, bid)
        cat_id = create_category(token, bid, name="Cat A", code="CA")
        prod_id = create_product(token, bid, unit_id, name="Widget", code="W1", category_id=cat_id)
        wh_loc = setup_warehouse_and_location(token, bid)
        add_opening_stock(token, bid, wh_loc, prod_id, qty="100")
        sales_id, sline_id = create_finalized_sales(token, bid, br_id, prod_id, qty="10", price="50000")
        create_finalized_return(token, bid, sales_id, sline_id, return_qty="3")

        res = get_report(token, bid, date_from="2026-01-01", date_to="2099-12-31", group_by="product")
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 1
        assert items[0]["group_id"] == prod_id
        assert items[0]["return_count"] == 1


# ============================================================
# FILTER TESTS
# ============================================================
class TestFilters:
    def test_filter_by_branch(self):
        token, uid = register_user()
        bid = create_business(token)
        br1 = create_branch(token, bid, name="Br1", code="B1")
        br2 = create_branch(token, bid, name="Br2", code="B2")
        unit_id = create_unit(token, bid)
        prod_id = create_product(token, bid, unit_id)
        wh_loc = setup_warehouse_and_location(token, bid)
        add_opening_stock(token, bid, wh_loc, prod_id, qty="100")
        create_finalized_sales(token, bid, br1, prod_id, qty="5", price="50000")
        create_finalized_sales(token, bid, br2, prod_id, qty="3", price="50000")

        res = get_report(token, bid, date_from="2026-01-01", date_to="2099-12-31", group_by="product", branch_id=br1)
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 1
        assert Decimal(items[0]["units_sold"]) == Decimal("5")

    def test_filter_by_product(self):
        token, uid = register_user()
        bid = create_business(token)
        br_id = create_branch(token, bid)
        unit_id = create_unit(token, bid)
        p1 = create_product(token, bid, unit_id, name="A", code="A1")
        p2 = create_product(token, bid, unit_id, name="B", code="B1")
        wh_loc = setup_warehouse_and_location(token, bid)
        add_opening_stock(token, bid, wh_loc, p1, qty="100")
        add_opening_stock(token, bid, wh_loc, p2, qty="100")
        create_finalized_sales(token, bid, br_id, p1, qty="5", price="50000")
        create_finalized_sales(token, bid, br_id, p2, qty="3", price="60000")

        res = get_report(token, bid, date_from="2026-01-01", date_to="2099-12-31", group_by="product", product_id=p1)
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 1
        assert items[0]["group_id"] == p1

    def test_filter_by_category(self):
        token, uid = register_user()
        bid = create_business(token)
        br_id = create_branch(token, bid)
        unit_id = create_unit(token, bid)
        cat_id = create_category(token, bid, name="Electronics", code="ELEC")
        p1 = create_product(token, bid, unit_id, name="Widget", code="W1", category_id=cat_id)
        p2 = create_product(token, bid, unit_id, name="Gadget", code="G1")
        wh_loc = setup_warehouse_and_location(token, bid)
        add_opening_stock(token, bid, wh_loc, p1, qty="100")
        add_opening_stock(token, bid, wh_loc, p2, qty="100")
        create_finalized_sales(token, bid, br_id, p1, qty="5", price="50000")
        create_finalized_sales(token, bid, br_id, p2, qty="3", price="60000")

        res = get_report(token, bid, date_from="2026-01-01", date_to="2099-12-31", group_by="product", category_id=cat_id)
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 1
        assert items[0]["group_id"] == p1


# ============================================================
# FINANCIAL ACCURACY TESTS
# ============================================================
class TestFinancial:
    def test_net_revenue_excludes_tax(self):
        token, uid = register_user()
        bid = create_business(token)
        br_id = create_branch(token, bid)
        unit_id = create_unit(token, bid)
        prod_id = create_product(token, bid, unit_id)
        wh_loc = setup_warehouse_and_location(token, bid)
        add_opening_stock(token, bid, wh_loc, prod_id, qty="100")
        create_finalized_sales(token, bid, br_id, prod_id, qty="10", price="50000")

        res = get_report(token, bid, date_from="2026-01-01", date_to="2099-12-31", group_by="product")
        assert res.status_code == 200
        item = res.json()["items"][0]
        assert Decimal(item["net_revenue"]) > Decimal("0")
        assert Decimal(item["total_tax"]) >= Decimal("0")
        gp = Decimal(item["net_revenue"]) - Decimal(item["cogs"])
        assert gp == Decimal(item["gross_profit"])

    def test_margin_null_when_zero_revenue(self):
        token, uid = register_user()
        bid = create_business(token)
        res = get_report(token, bid, date_from="2026-01-01", date_to="2026-12-31")
        assert res.status_code == 200
        assert res.json()["summary"]["overall_gross_margin_percentage"] is None

    def test_summary_matches_items(self):
        token, uid = register_user()
        bid = create_business(token)
        br_id = create_branch(token, bid)
        unit_id = create_unit(token, bid)
        prod_id = create_product(token, bid, unit_id)
        wh_loc = setup_warehouse_and_location(token, bid)
        add_opening_stock(token, bid, wh_loc, prod_id, qty="100")
        create_finalized_sales(token, bid, br_id, prod_id, qty="10", price="50000")

        res = get_report(token, bid, date_from="2026-01-01", date_to="2099-12-31")
        assert res.status_code == 200
        data = res.json()
        assert len(data["items"]) == 1
        item = data["items"][0]
        assert Decimal(data["summary"]["total_net_revenue"]) == Decimal(item["net_revenue"])
        assert data["summary"]["total_sales_count"] == item["sales_count"]

    def test_service_product_included(self):
        token, uid = register_user()
        bid = create_business(token)
        br_id = create_branch(token, bid)
        unit_id = create_unit(token, bid)
        svc_id = create_product(token, bid, unit_id, name="Consulting", code="SVC", p_type="SERVICE")
        res = get_report(token, bid, date_from="2026-01-01", date_to="2099-12-31")
        assert res.status_code == 200
        assert len(res.json()["items"]) == 0


# ============================================================
# SORTING TESTS
# ============================================================
class TestSorting:
    def test_sorted_by_group_name_asc(self):
        token, uid = register_user()
        bid = create_business(token)
        br_id = create_branch(token, bid)
        unit_id = create_unit(token, bid)
        p1 = create_product(token, bid, unit_id, name="Zebra", code="Z1")
        p2 = create_product(token, bid, unit_id, name="Alpha", code="A1")
        wh_loc = setup_warehouse_and_location(token, bid)
        add_opening_stock(token, bid, wh_loc, p1, qty="100")
        add_opening_stock(token, bid, wh_loc, p2, qty="100")
        create_finalized_sales(token, bid, br_id, p1, qty="5", price="50000")
        create_finalized_sales(token, bid, br_id, p2, qty="5", price="50000")

        res = get_report(token, bid, date_from="2026-01-01", date_to="2099-12-31", group_by="product")
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 2
        assert items[0]["group_name"] == "Alpha"
        assert items[1]["group_name"] == "Zebra"


# ============================================================
# READ-ONLY TEST
# ============================================================
class TestReadOnly:
    def test_only_get_allowed(self):
        token, uid = register_user()
        bid = create_business(token)
        res = client.post(
            f"/api/v1/businesses/{bid}/reports/product-profitability",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 405

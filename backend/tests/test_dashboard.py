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
from app.modules.payment.repository import InMemoryPaymentRepository
from app.modules.supplier.repository import InMemorySupplierRepository
from app.modules.cash_account.repository import InMemoryCashAccountRepository
from app.modules.expense.repository import InMemoryExpenseRepository
from app.modules.purchase.repository import InMemoryPurchaseRepository
from app.modules.purchase_return.repository import InMemoryPurchaseReturnRepository

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
    InMemoryPaymentRepository.clear()
    InMemorySupplierRepository.clear()
    InMemoryCashAccountRepository.clear()
    InMemoryExpenseRepository.clear()
    InMemoryPurchaseRepository.clear()
    InMemoryPurchaseReturnRepository.clear()
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
    InMemoryPaymentRepository.clear()
    InMemorySupplierRepository.clear()
    InMemoryCashAccountRepository.clear()
    InMemoryExpenseRepository.clear()
    InMemoryPurchaseRepository.clear()
    InMemoryPurchaseReturnRepository.clear()


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


def create_branch(token, bid, name="Main Branch", code="MB01"):
    res = client.post(
        f"/api/v1/businesses/{bid}/branches",
        json={"name": name, "code": code},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_customer(token, bid, name="Customer A"):
    res = client.post(
        f"/api/v1/businesses/{bid}/customers",
        json={"name": name, "customer_type": "ORGANIZATION"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_unit(token, bid, name="Pcs", code="PCS"):
    res = client.post(
        f"/api/v1/businesses/{bid}/units",
        json={"name": name, "code": code},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_category(token, bid, name="Category A", code="CATA"):
    res = client.post(
        f"/api/v1/businesses/{bid}/categories",
        json={"name": name, "code": code},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_product(token, bid, unit_id, cat_id=None, name="Product A", code="PROD-A"):
    payload = {"name": name, "code": code, "unit_id": unit_id, "product_type": "GOODS"}
    if cat_id:
        payload["category_id"] = cat_id
    res = client.post(
        f"/api/v1/businesses/{bid}/products",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def setup_warehouse_and_location(token, bid):
    wh_res = client.post(
        f"/api/v1/businesses/{bid}/warehouses",
        json={"name": "WH", "code": "WH1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert wh_res.status_code == 201
    wh_id = wh_res.json()["id"]
    loc_res = client.post(
        f"/api/v1/businesses/{bid}/warehouses/{wh_id}/locations",
        json={"name": "Loc", "code": "L1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert loc_res.status_code == 201
    return loc_res.json()["id"]


def add_opening_stock(token, bid, loc_id, prod_id, qty="100"):
    res = client.post(
        f"/api/v1/businesses/{bid}/inventory/opening-balance",
        json={"inventory_location_id": loc_id, "product_id": prod_id, "quantity": qty, "unit_cost": "50000"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201


def create_finalized_sales(token, bid, br_id, prod_id, qty="5", price="100000", sales_date="2026-09-01T00:00:00Z"):
    s_res = client.post(
        f"/api/v1/businesses/{bid}/sales",
        json={"branch_id": br_id, "sales_date": sales_date},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert s_res.status_code == 201
    sales_id = s_res.json()["id"]
    l_res = client.post(
        f"/api/v1/businesses/{bid}/sales/{sales_id}/lines",
        json={"product_id": prod_id, "quantity": qty, "unit_price": price},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert l_res.status_code == 201
    sline_id = l_res.json()["id"]
    fin_res = client.post(
        f"/api/v1/businesses/{bid}/sales/{sales_id}/finalize",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fin_res.status_code == 200
    return sales_id, sline_id


def create_finalized_return(token, bid, sales_id, sline_id, ret_qty="2"):
    ret_res = client.post(
        f"/api/v1/businesses/{bid}/sales-returns",
        json={"sales_id": sales_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ret_res.status_code == 201
    ret_id = ret_res.json()["id"]
    line_res = client.post(
        f"/api/v1/businesses/{bid}/sales-returns/{ret_id}/lines",
        json={"sales_line_id": sline_id, "quantity": ret_qty},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert line_res.status_code == 201
    fin_res = client.post(
        f"/api/v1/businesses/{bid}/sales-returns/{ret_id}/finalize",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fin_res.status_code == 200
    return ret_id


def create_cash_account(token, bid, name="Cash", code="CASH1"):
    res = client.post(
        f"/api/v1/businesses/{bid}/cash-accounts",
        json={"name": name, "code": code, "account_type": "CASH", "currency": "IDR", "opening_balance": "1000000", "is_default": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_expense_category(token, bid):
    res = client.post(
        f"/api/v1/businesses/{bid}/expense-categories",
        json={"name": "Utilities", "code": "UTL"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_finalized_expense(token, bid, cat_id, amount="50000", expense_date="2026-09-01T00:00:00Z"):
    res = client.post(
        f"/api/v1/businesses/{bid}/expenses",
        json={"category_id": cat_id, "amount": amount, "currency": "IDR", "expense_date": expense_date},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    exp_id = res.json()["id"]
    fin = client.post(
        f"/api/v1/businesses/{bid}/expenses/{exp_id}/finalize",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fin.status_code == 200
    return exp_id


def get_report(token, bid, **params):
    res = client.get(
        f"/api/v1/businesses/{bid}/dashboard/operational",
        params=params,
        headers={"Authorization": f"Bearer {token}"},
    )
    return res


# ============================================================
# DATE VALIDATION TESTS
# ============================================================
class TestDateValidation:
    def test_missing_both_dates_rejected(self):
        token, uid = register_user()
        bid = create_business(token)
        res = client.get(
            f"/api/v1/businesses/{bid}/dashboard/operational",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 422

    def test_only_date_from_rejected(self):
        token, uid = register_user()
        bid = create_business(token)
        res = get_report(token, bid, date_from="2026-09-01")
        assert res.status_code == 422

    def test_only_date_to_rejected(self):
        token, uid = register_user()
        bid = create_business(token)
        res = get_report(token, bid, date_to="2026-09-30")
        assert res.status_code == 422

    def test_date_from_gt_date_to_rejected(self):
        token, uid = register_user()
        bid = create_business(token)
        res = get_report(token, bid, date_from="2026-12-31", date_to="2026-01-01")
        assert res.status_code == 422


# ============================================================
# AUTH TESTS
# ============================================================
class TestAuth:
    def test_unauthenticated_returns_401(self):
        token, uid = register_user()
        bid = create_business(token)
        res = client.get(
            f"/api/v1/businesses/{bid}/dashboard/operational",
            params={"date_from": "2026-09-01", "date_to": "2026-09-30"},
        )
        assert res.status_code == 401

    def test_non_member_returns_error(self):
        token, uid = register_user()
        bid = create_business(token)
        token2, _ = register_user(email="other@example.com", name="Other")
        res = get_report(token2, bid, date_from="2026-09-01", date_to="2026-09-30")
        assert res.status_code in (403, 404)


# ============================================================
# EMPTY STATE
# ============================================================
class TestEmptyState:
    def test_empty_business_returns_zeros(self):
        token, uid = register_user()
        bid = create_business(token)
        res = get_report(token, bid, date_from="2026-09-01", date_to="2026-09-30")
        assert res.status_code == 200
        data = res.json()
        assert data["period"]["date_from"] == "2026-09-01"
        assert data["period"]["date_to"] == "2026-09-30"
        assert data["revenue"]["total"] == "0.00"
        assert data["revenue"]["sales_count"] == 0
        assert data["revenue"]["return_count"] == 0
        assert data["expenses"]["total"] == "0.00"
        assert data["expenses"]["expense_count"] == 0
        assert data["net_operating_result"] == "0.00"
        assert data["cash_position"]["account_count"] == 0
        assert data["receivables"]["unpaid_count"] == 0
        assert data["payables"]["unpaid_count"] == 0
        assert data["recent_activity"] == []


# ============================================================
# REVENUE TESTS
# ============================================================
class TestRevenue:
    def test_finalized_sales_in_period(self):
        token, uid = register_user()
        bid = create_business(token)
        br_id = create_branch(token, bid)
        unit_id = create_unit(token, bid)
        cat_id = create_category(token, bid)
        prod_id = create_product(token, bid, unit_id, cat_id)
        loc_id = setup_warehouse_and_location(token, bid)
        add_opening_stock(token, bid, loc_id, prod_id)
        create_finalized_sales(token, bid, br_id, prod_id, qty="5", price="100000")

        res = get_report(token, bid, date_from="2026-09-01", date_to="2026-09-30")
        assert res.status_code == 200
        data = res.json()
        assert data["revenue"]["sales_count"] == 1
        assert Decimal(data["revenue"]["total"]) == Decimal("500000")
        assert Decimal(data["revenue"]["net"]) == Decimal("500000")

    def test_draft_sales_excluded(self):
        token, uid = register_user()
        bid = create_business(token)
        br_id = create_branch(token, bid)
        unit_id = create_unit(token, bid)
        prod_id = create_product(token, bid, unit_id)
        res = get_report(token, bid, date_from="2026-09-01", date_to="2026-09-30")
        assert res.status_code == 200
        assert res.json()["revenue"]["sales_count"] == 0

    def test_sales_outside_period_excluded(self):
        token, uid = register_user()
        bid = create_business(token)
        br_id = create_branch(token, bid)
        unit_id = create_unit(token, bid)
        prod_id = create_product(token, bid, unit_id)
        loc_id = setup_warehouse_and_location(token, bid)
        add_opening_stock(token, bid, loc_id, prod_id)
        create_finalized_sales(token, bid, br_id, prod_id, sales_date="2026-08-31T00:00:00Z")

        res = get_report(token, bid, date_from="2026-09-01", date_to="2026-09-30")
        assert res.status_code == 200
        assert res.json()["revenue"]["sales_count"] == 0

    def test_return_in_period_reduces_revenue(self):
        token, uid = register_user()
        bid = create_business(token)
        br_id = create_branch(token, bid)
        unit_id = create_unit(token, bid)
        prod_id = create_product(token, bid, unit_id)
        loc_id = setup_warehouse_and_location(token, bid)
        add_opening_stock(token, bid, loc_id, prod_id)
        sales_id, sline_id = create_finalized_sales(token, bid, br_id, prod_id, qty="10", price="50000")
        create_finalized_return(token, bid, sales_id, sline_id, ret_qty="3")

        res = get_report(token, bid, date_from="2026-09-01", date_to="2026-09-30")
        assert res.status_code == 200
        data = res.json()
        assert data["revenue"]["sales_count"] == 1
        assert data["revenue"]["return_count"] == 1
        assert Decimal(data["revenue"]["total"]) == Decimal("500000")
        assert Decimal(data["revenue"]["net"]) == Decimal("350000")

    def test_return_count_is_unique_header(self):
        token, uid = register_user()
        bid = create_business(token)
        br_id = create_branch(token, bid)
        unit_id = create_unit(token, bid)
        prod_id = create_product(token, bid, unit_id)
        loc_id = setup_warehouse_and_location(token, bid)
        add_opening_stock(token, bid, loc_id, prod_id)
        sales_id, sline_id = create_finalized_sales(token, bid, br_id, prod_id, qty="10", price="50000")
        create_finalized_return(token, bid, sales_id, sline_id, ret_qty="2")
        create_finalized_return(token, bid, sales_id, sline_id, ret_qty="2")

        res = get_report(token, bid, date_from="2026-09-01", date_to="2026-09-30")
        assert res.status_code == 200
        assert res.json()["revenue"]["return_count"] == 2


# ============================================================
# EXPENSE TESTS
# ============================================================
class TestExpenses:
    def test_finalized_expense_in_period(self):
        token, uid = register_user()
        bid = create_business(token)
        cat_id = create_expense_category(token, bid)
        create_finalized_expense(token, bid, cat_id, amount="50000")

        res = get_report(token, bid, date_from="2026-09-01", date_to="2026-09-30")
        assert res.status_code == 200
        data = res.json()
        assert data["expenses"]["expense_count"] == 1
        assert Decimal(data["expenses"]["total"]) == Decimal("50000")


# ============================================================
# NET OPERATING RESULT
# ============================================================
class TestNetOperatingResult:
    def test_net_result_calculation(self):
        token, uid = register_user()
        bid = create_business(token)
        br_id = create_branch(token, bid)
        unit_id = create_unit(token, bid)
        prod_id = create_product(token, bid, unit_id)
        loc_id = setup_warehouse_and_location(token, bid)
        add_opening_stock(token, bid, loc_id, prod_id)
        create_finalized_sales(token, bid, br_id, prod_id, qty="10", price="50000")
        cat_id = create_expense_category(token, bid)
        create_finalized_expense(token, bid, cat_id, amount="200000")

        res = get_report(token, bid, date_from="2026-09-01", date_to="2026-09-30")
        assert res.status_code == 200
        data = res.json()
        assert Decimal(data["revenue"]["net"]) == Decimal("500000")
        assert Decimal(data["expenses"]["total"]) == Decimal("200000")
        assert Decimal(data["net_operating_result"]) == Decimal("300000")

    def test_negative_net_result(self):
        token, uid = register_user()
        bid = create_business(token)
        unit_id = create_unit(token, bid)
        prod_id = create_product(token, bid, unit_id)
        cat_id = create_expense_category(token, bid)
        create_finalized_expense(token, bid, cat_id, amount="1000000")

        res = get_report(token, bid, date_from="2026-09-01", date_to="2026-09-30")
        assert res.status_code == 200
        data = res.json()
        assert Decimal(data["net_operating_result"]) == Decimal("-1000000.00")


# ============================================================
# CASH TESTS
# ============================================================
class TestCash:
    def test_cash_balance_reflected(self):
        token, uid = register_user()
        bid = create_business(token)
        create_cash_account(token, bid)

        res = get_report(token, bid, date_from="2026-09-01", date_to="2026-09-30")
        assert res.status_code == 200
        data = res.json()
        assert data["cash_position"]["account_count"] == 1
        assert Decimal(data["cash_position"]["total_balance"]) == Decimal("1000000")


# ============================================================
# INVENTORY TESTS
# ============================================================
class TestInventory:
    def test_inventory_valuation_reflected(self):
        token, uid = register_user()
        bid = create_business(token)
        unit_id = create_unit(token, bid)
        cat_id = create_category(token, bid)
        prod_id = create_product(token, bid, unit_id, cat_id)
        loc_id = setup_warehouse_and_location(token, bid)
        add_opening_stock(token, bid, loc_id, prod_id, qty="20")

        res = get_report(token, bid, date_from="2026-09-01", date_to="2026-09-30")
        assert res.status_code == 200
        data = res.json()
        assert data["inventory"]["total_items"] == 1
        assert Decimal(data["inventory"]["total_valuation"]) == Decimal("1000000")


# ============================================================
# RECENT ACTIVITY TESTS
# ============================================================
class TestRecentActivity:
    def test_activity_includes_finalized_sales(self):
        token, uid = register_user()
        bid = create_business(token)
        br_id = create_branch(token, bid)
        unit_id = create_unit(token, bid)
        prod_id = create_product(token, bid, unit_id)
        loc_id = setup_warehouse_and_location(token, bid)
        add_opening_stock(token, bid, loc_id, prod_id)
        create_finalized_sales(token, bid, br_id, prod_id)

        res = get_report(token, bid, date_from="2026-09-01", date_to="2026-09-30")
        assert res.status_code == 200
        data = res.json()
        assert len(data["recent_activity"]) == 1
        assert data["recent_activity"][0]["type"] == "SALE"

    def test_activity_excludes_outside_period(self):
        token, uid = register_user()
        bid = create_business(token)
        br_id = create_branch(token, bid)
        unit_id = create_unit(token, bid)
        prod_id = create_product(token, bid, unit_id)
        loc_id = setup_warehouse_and_location(token, bid)
        add_opening_stock(token, bid, loc_id, prod_id)
        create_finalized_sales(token, bid, br_id, prod_id, sales_date="2026-08-31T00:00:00Z")

        res = get_report(token, bid, date_from="2026-09-01", date_to="2026-09-30")
        assert res.status_code == 200
        assert len(res.json()["recent_activity"]) == 0


# ============================================================
# BRANCH FILTER TESTS
# ============================================================
class TestBranchFilter:
    def test_branch_filter_sales(self):
        token, uid = register_user()
        bid = create_business(token)
        br1 = create_branch(token, bid, name="Br1", code="B1")
        br2 = create_branch(token, bid, name="Br2", code="B2")
        unit_id = create_unit(token, bid)
        prod_id = create_product(token, bid, unit_id)
        loc_id = setup_warehouse_and_location(token, bid)
        add_opening_stock(token, bid, loc_id, prod_id)
        create_finalized_sales(token, bid, br1, prod_id, qty="5", price="100000")
        create_finalized_sales(token, bid, br2, prod_id, qty="3", price="100000")

        res = get_report(token, bid, date_from="2026-09-01", date_to="2026-09-30", branch_id=br1)
        assert res.status_code == 200
        assert res.json()["revenue"]["sales_count"] == 1
        assert Decimal(res.json()["revenue"]["total"]) == Decimal("500000")

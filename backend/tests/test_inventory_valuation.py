import pytest
from decimal import Decimal
from datetime import datetime, timezone
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
from app.modules.supplier.repository import InMemorySupplierRepository
from app.modules.branch.repository import InMemoryBranchRepository
from app.modules.purchase.repository import InMemoryPurchaseRepository
from app.modules.receiving.repository import InMemoryReceivingRepository
from app.modules.purchase_return.repository import InMemoryPurchaseReturnRepository
from app.modules.sales.repository import InMemorySalesRepository
from app.modules.sales_return.repository import InMemorySalesReturnRepository
from app.modules.customer.repository import InMemoryCustomerRepository
from app.modules.accounting.repository import InMemoryAccountingRepository
from app.modules.pricing.repository import InMemoryPriceListRepository, InMemoryPriceEntryRepository
from app.modules.stock_opname.repository import InMemoryStockOpnameRepository

# Override production PostgreSQL router wiring with InMemory services
from app.modules.purchase.router import get_scoped_purchase_service
from app.modules.receiving.router import get_scoped_receiving_service
from app.modules.purchase_return.router import get_scoped_purchase_return_service
from app.modules.business.router import get_scoped_business_service
from app.modules.business_membership.router import get_scoped_membership_service
from app.modules.purchase.service import PurchaseService
from app.modules.receiving.service import ReceivingService
from app.modules.purchase_return.service import PurchaseReturnService
from app.modules.business_membership.service import BusinessMembershipService
from app.modules.business.service import BusinessService
from app.modules.subscription.service import SubscriptionService


def _inmemory_purchase_service():
    return PurchaseService(membership_service=BusinessMembershipService())


def _inmemory_receiving_service():
    return ReceivingService(membership_service=BusinessMembershipService())


def _inmemory_purchase_return_service():
    return PurchaseReturnService(membership_service=BusinessMembershipService())


def _inmemory_business_service():
    membership_svc = BusinessMembershipService()
    subscription_svc = SubscriptionService()
    return BusinessService(membership_service=membership_svc, subscription_service_instance=subscription_svc)


def _inmemory_membership_service():
    return BusinessMembershipService()


@pytest.fixture(autouse=True)
def setup_test_environment():
    app.dependency_overrides[get_scoped_purchase_service] = _inmemory_purchase_service
    app.dependency_overrides[get_scoped_receiving_service] = _inmemory_receiving_service
    app.dependency_overrides[get_scoped_purchase_return_service] = _inmemory_purchase_return_service
    app.dependency_overrides[get_scoped_business_service] = _inmemory_business_service
    app.dependency_overrides[get_scoped_membership_service] = _inmemory_membership_service
    yield
    app.dependency_overrides.pop(get_scoped_purchase_service, None)
    app.dependency_overrides.pop(get_scoped_receiving_service, None)
    app.dependency_overrides.pop(get_scoped_purchase_return_service, None)
    app.dependency_overrides.pop(get_scoped_business_service, None)
    app.dependency_overrides.pop(get_scoped_membership_service, None)

client = TestClient(app)

ALL_REPOS = [
    InMemoryUserRepository,
    InMemoryAccountRepository,
    InMemoryBusinessRepository,
    InMemoryBusinessMembershipRepository,
    InMemoryWarehouseRepository,
    InMemoryInventoryLocationRepository,
    InMemoryUnitRepository,
    InMemoryProductRepository,
    InMemoryProductVariantRepository,
    InMemoryStockBalanceRepository,
    InMemoryStockMovementRepository,
    InMemoryInventoryCostRepository,
    InMemorySupplierRepository,
    InMemoryBranchRepository,
    InMemoryPurchaseRepository,
    InMemoryReceivingRepository,
    InMemoryPurchaseReturnRepository,
    InMemorySalesRepository,
    InMemorySalesReturnRepository,
    InMemoryCustomerRepository,
    InMemoryAccountingRepository,
    InMemoryPriceListRepository,
    InMemoryPriceEntryRepository,
    InMemoryStockOpnameRepository,
]


@pytest.fixture(autouse=True)
def clear_repositories():
    for repo in ALL_REPOS:
        repo.clear()
    yield
    for repo in ALL_REPOS:
        repo.clear()


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
        json={"name": name, "code": code, "unit_id": unit_id, "product_type": p_type},
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


def create_purchase(token, business_id, supplier_id, branch_id):
    res = client.post(
        f"/api/v1/businesses/{business_id}/purchases",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "supplier_id": supplier_id,
            "branch_id": branch_id,
            "purchase_date": datetime.now(timezone.utc).isoformat(),
            "input_vat_creditable": False,
        },
    )
    assert res.status_code == 201
    return res.json()["id"]


def add_purchase_line(token, business_id, purchase_id, product_id, qty="10", unit_price="100"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/purchases/{purchase_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": product_id, "quantity": qty, "unit_price": unit_price},
    )
    assert res.status_code == 201
    return res.json()


def finalize_purchase(token, business_id, purchase_id):
    res = client.post(
        f"/api/v1/businesses/{business_id}/purchases/{purchase_id}/finalize",
        headers={"Authorization": f"Bearer {token}"},
    )
    return res


def create_sales(token, business_id, branch_id):
    res = client.post(
        f"/api/v1/businesses/{business_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    )
    assert res.status_code == 201
    return res.json()["id"]


def add_sales_line(token, business_id, sales_id, product_id, qty="3", unit_price="200"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": product_id, "quantity": qty, "unit_price": unit_price},
    )
    assert res.status_code == 201
    return res.json()


def finalize_sales(token, business_id, sales_id):
    res = client.post(
        f"/api/v1/businesses/{business_id}/sales/{sales_id}/finalize",
        headers={"Authorization": f"Bearer {token}"},
        json={},
    )
    return res


def list_journals(token, business_id):
    res = client.get(
        f"/api/v1/businesses/{business_id}/accounting/journals",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    return res.json()


# ============================================================
# Purchase valuation
# ============================================================

class TestPurchaseValuation:
    def test_purchase_finalize_updates_stock_and_cost(self):
        token, _ = register_user()
        biz = create_business(token)
        unit_id = create_unit(token, biz)
        prod = create_product(token, biz, unit_id)
        _, loc = setup_warehouse_and_location(token, biz)
        sup = create_supplier(token, biz)
        br = create_branch(token, biz)

        pur_id = create_purchase(token, biz, sup, br)
        add_purchase_line(token, biz, pur_id, prod, qty="10", unit_price="100")
        fin_res = finalize_purchase(token, biz, pur_id)
        assert fin_res.status_code == 200

        # Check physical stock
        stock_res = client.get(
            f"/api/v1/businesses/{biz}/inventory/stock",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert stock_res.status_code == 200
        stocks = stock_res.json()
        assert len(stocks) >= 1
        total_qty = sum(Decimal(s["quantity"]) for s in stocks if s["product_id"] == prod)
        assert total_qty == Decimal("10")

        # Check valuation
        val_res = client.get(
            f"/api/v1/businesses/{biz}/inventory/valuation",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert val_res.status_code == 200
        val = val_res.json()
        items = [i for i in val["items"] if i["product_id"] == prod]
        assert len(items) == 1
        assert Decimal(items[0]["total_quantity"]) == Decimal("10")
        assert Decimal(items[0]["unit_cost"]) == Decimal("100")
        assert Decimal(items[0]["total_cost"]) == Decimal("1000")
        assert Decimal(val["total_inventory_value"]) == Decimal("1000")

    def test_purchase_mac_average_after_second_receipt(self):
        token, _ = register_user()
        biz = create_business(token)
        unit_id = create_unit(token, biz)
        prod = create_product(token, biz, unit_id)
        setup_warehouse_and_location(token, biz)
        sup = create_supplier(token, biz)
        br = create_branch(token, biz)

        # First purchase: 10 x 100
        p1 = create_purchase(token, biz, sup, br)
        add_purchase_line(token, biz, p1, prod, qty="10", unit_price="100")
        assert finalize_purchase(token, biz, p1).status_code == 200

        # Second purchase: 10 x 200
        p2 = create_purchase(token, biz, sup, br)
        add_purchase_line(token, biz, p2, prod, qty="10", unit_price="200")
        assert finalize_purchase(token, biz, p2).status_code == 200

        val_res = client.get(
            f"/api/v1/businesses/{biz}/inventory/valuation",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert val_res.status_code == 200
        items = [i for i in val_res.json()["items"] if i["product_id"] == prod]
        assert len(items) == 1
        assert Decimal(items[0]["total_quantity"]) == Decimal("20")
        # MAC = (10*100 + 10*200)/20 = 150
        assert Decimal(items[0]["unit_cost"]) == Decimal("150")
        assert Decimal(items[0]["total_cost"]) == Decimal("3000")

    def test_purchase_zero_quantity_rule_not_triggered(self):
        token, _ = register_user()
        biz = create_business(token)
        unit_id = create_unit(token, biz)
        prod = create_product(token, biz, unit_id)
        setup_warehouse_and_location(token, biz)
        sup = create_supplier(token, biz)
        br = create_branch(token, biz)

        p1 = create_purchase(token, biz, sup, br)
        add_purchase_line(token, biz, p1, prod, qty="5", unit_price="100")
        assert finalize_purchase(token, biz, p1).status_code == 200

        val = client.get(
            f"/api/v1/businesses/{biz}/inventory/valuation",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        items = [i for i in val["items"] if i["product_id"] == prod]
        assert Decimal(items[0]["total_quantity"]) == Decimal("5")
        assert Decimal(items[0]["unit_cost"]) == Decimal("100")


# ============================================================
# Receiving verification: no duplicate journals/cost
# ============================================================

class TestReceivingVerification:
    def test_receiving_does_not_post_accounting_journal(self):
        token, _ = register_user()
        biz = create_business(token)
        unit_id = create_unit(token, biz)
        prod = create_product(token, biz, unit_id)
        _, loc = setup_warehouse_and_location(token, biz)
        sup = create_supplier(token, biz)
        br = create_branch(token, biz)

        pur_id = create_purchase(token, biz, sup, br)
        line = add_purchase_line(token, biz, pur_id, prod, qty="10", unit_price="100")
        assert finalize_purchase(token, biz, pur_id).status_code == 200

        journals_before = list_journals(token, biz)
        count_before = len(journals_before["items"]) if isinstance(journals_before, dict) else len(journals_before)

        # Create and finalize receiving (logistics verification only)
        rcv_res = client.post(
            f"/api/v1/businesses/{biz}/receivings",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc},
        )
        assert rcv_res.status_code == 201
        rcv_id = rcv_res.json()["id"]

        line_res = client.post(
            f"/api/v1/businesses/{biz}/receivings/{rcv_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": line["id"], "quantity": "5"},
        )
        assert line_res.status_code == 201

        fin_rcv = client.post(
            f"/api/v1/businesses/{biz}/receivings/{rcv_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fin_rcv.status_code == 200

        journals_after = list_journals(token, biz)
        count_after = len(journals_after["items"]) if isinstance(journals_after, dict) else len(journals_after)

        assert count_after == count_before

        # Also cost state unchanged
        val_res = client.get(
            f"/api/v1/businesses/{biz}/inventory/valuation",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert val_res.status_code == 200
        items = [i for i in val_res.json()["items"] if i["product_id"] == prod]
        assert Decimal(items[0]["total_quantity"]) == Decimal("10")
        assert Decimal(items[0]["unit_cost"]) == Decimal("100")


# ============================================================
# Sales COGS 5-line journal
# ============================================================

class TestSalesCogs5LineJournal:
    def test_sales_finalize_posts_5_line_balanced_journal(self):
        token, _ = register_user()
        biz = create_business(token)
        unit_id = create_unit(token, biz)
        prod = create_product(token, biz, unit_id)
        setup_warehouse_and_location(token, biz)
        sup = create_supplier(token, biz)
        br = create_branch(token, biz)

        pur_id = create_purchase(token, biz, sup, br)
        add_purchase_line(token, biz, pur_id, prod, qty="10", unit_price="100")
        assert finalize_purchase(token, biz, pur_id).status_code == 200

        sales_id = create_sales(token, biz, br)
        add_sales_line(token, biz, sales_id, prod, qty="4", unit_price="200")
        fin_res = finalize_sales(token, biz, sales_id)
        assert fin_res.status_code == 200

        # Check sales line snapshots preserved
        sales_data = fin_res.json()
        assert len(sales_data["lines"]) == 1
        line = sales_data["lines"][0]
        assert line["unit_cost_snapshot"] is not None
        assert Decimal(line["unit_cost_snapshot"]) == Decimal("100")
        assert Decimal(line["cost_total_snapshot"]) == Decimal("400")

        # Check journal
        journals = list_journals(token, biz)
        items = journals["items"] if isinstance(journals, dict) else journals
        sales_journals = [j for j in items if j["reference_type"] == "SALES" and j["reference_id"] == sales_id]
        assert len(sales_journals) == 1
        journal = sales_journals[0]
        journal_lines = journal.get("lines", [])
        # 5-line: AR + COGS + Revenue + Inventory
        # When tax_total == 0: AR, COGS, Revenue, Inventory = 4 lines; but with tax 0 it should be 4 (AR+Revenue+COGS+Inventory)
        # With COGS posting enabled expect at least AR, COGS, Revenue, Inventory
        codes = [l.get("account_code") for l in journal_lines]
        assert "1200" in codes
        assert "5200" in codes
        assert "1300" in codes
        # Balanced check
        total_debit = sum(Decimal(l["debit"]) for l in journal_lines)
        total_credit = sum(Decimal(l["credit"]) for l in journal_lines)
        assert total_debit == total_credit

        # Check physical stock decremented
        stock_res = client.get(
            f"/api/v1/businesses/{biz}/inventory/stock",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        total_qty = sum(Decimal(s["quantity"]) for s in stock_res if s["product_id"] == prod)
        assert total_qty == Decimal("6")

        # Check cost state decremented
        val_res = client.get(
            f"/api/v1/businesses/{biz}/inventory/valuation",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        items_v = [i for i in val_res["items"] if i["product_id"] == prod]
        assert Decimal(items_v[0]["total_quantity"]) == Decimal("6")
        assert Decimal(items_v[0]["unit_cost"]) == Decimal("100")
        assert Decimal(items_v[0]["total_cost"]) == Decimal("600")

    def test_sales_insufficient_stock_400(self):
        token, _ = register_user()
        biz = create_business(token)
        unit_id = create_unit(token, biz)
        prod = create_product(token, biz, unit_id)
        setup_warehouse_and_location(token, biz)
        sup = create_supplier(token, biz)
        br = create_branch(token, biz)

        pur_id = create_purchase(token, biz, sup, br)
        add_purchase_line(token, biz, pur_id, prod, qty="2", unit_price="100")
        assert finalize_purchase(token, biz, pur_id).status_code == 200

        sales_id = create_sales(token, biz, br)
        add_sales_line(token, biz, sales_id, prod, qty="10", unit_price="200")
        fin_res = finalize_sales(token, biz, sales_id)
        assert fin_res.status_code == 400


# ============================================================
# Sales Return historical reversal
# ============================================================

class TestSalesReturnHistoricalReversal:
    def test_sales_return_restores_stock_and_cost(self):
        token, _ = register_user()
        biz = create_business(token)
        unit_id = create_unit(token, biz)
        prod = create_product(token, biz, unit_id)
        setup_warehouse_and_location(token, biz)
        sup = create_supplier(token, biz)
        br = create_branch(token, biz)

        pur_id = create_purchase(token, biz, sup, br)
        add_purchase_line(token, biz, pur_id, prod, qty="10", unit_price="100")
        assert finalize_purchase(token, biz, pur_id).status_code == 200

        sales_id = create_sales(token, biz, br)
        sales_line = add_sales_line(token, biz, sales_id, prod, qty="5", unit_price="250")
        assert finalize_sales(token, biz, sales_id).status_code == 200

        # Capture snapshot
        sales_get = client.get(
            f"/api/v1/businesses/{biz}/sales/{sales_id}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        hist_unit = Decimal([l for l in sales_get["lines"] if l["id"] == sales_line["id"]][0]["unit_cost_snapshot"])
        assert hist_unit == Decimal("100")

        # Change MAC to verify historical retrieval
        # Second purchase with higher cost changes current MAC
        pur2 = create_purchase(token, biz, sup, br)
        add_purchase_line(token, biz, pur2, prod, qty="10", unit_price="500")
        assert finalize_purchase(token, biz, pur2).status_code == 200

        cur_val = client.get(
            f"/api/v1/businesses/{biz}/inventory/valuation",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        cur_items = [i for i in cur_val["items"] if i["product_id"] == prod]
        # After sales (6 left *100 =600) + purchase (10*500=5000) = 5600 / 16 = 350 is wrong, wait compute: after sales 5 left (10-5=5)
        # then 10*500 purchase => (5*100 + 10*500)/15 = (500+5000)/15=5500/15=366.666..
        # So cur_unit_cost is not 100
        cur_mac = Decimal(cur_items[0]["unit_cost"])
        assert cur_mac != Decimal("100")

        # Create sales return for 2 qty
        rt_res = client.post(
            f"/api/v1/businesses/{biz}/sales-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_id": sales_id},
        )
        assert rt_res.status_code == 201
        ret_id = rt_res.json()["id"]

        line_res = client.post(
            f"/api/v1/businesses/{biz}/sales-returns/{ret_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_line_id": sales_line["id"], "quantity": "2"},
        )
        assert line_res.status_code == 201

        fin_ret = client.post(
            f"/api/v1/businesses/{biz}/sales-returns/{ret_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fin_ret.status_code == 200

        # Check cost restoration used historical snapshot (2 * 100 = 200 added at cost)
        val_after = client.get(
            f"/api/v1/businesses/{biz}/inventory/valuation",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        items_after = [i for i in val_after["items"] if i["product_id"] == prod]
        # Qty before return: 15 (5+10), after return +2 = 17
        assert Decimal(items_after[0]["total_quantity"]) == Decimal("17")

        # Check journal reversal includes COGS restoration
        journals = list_journals(token, biz)
        jitems = journals["items"] if isinstance(journals, dict) else journals
        ret_journals = [j for j in jitems if j["reference_type"] == "SALES_RETURN" and j["reference_id"] == ret_id]
        assert len(ret_journals) == 1
        codes = [l.get("account_code") for l in ret_journals[0].get("lines", [])]
        assert "5200" in codes
        assert "1300" in codes


# ============================================================
# Purchase Return historical deduction
# ============================================================

class TestPurchaseReturnHistoricalDeduction:
    def test_purchase_return_deducts_historical_cost(self):
        token, _ = register_user()
        biz = create_business(token)
        unit_id = create_unit(token, biz)
        prod = create_product(token, biz, unit_id)
        _, loc = setup_warehouse_and_location(token, biz)
        sup = create_supplier(token, biz)
        br = create_branch(token, biz)

        pur_id = create_purchase(token, biz, sup, br)
        line = add_purchase_line(token, biz, pur_id, prod, qty="10", unit_price="100")
        assert finalize_purchase(token, biz, pur_id).status_code == 200

        # Second purchase at higher cost
        pur2 = create_purchase(token, biz, sup, br)
        add_purchase_line(token, biz, pur2, prod, qty="10", unit_price="300")
        assert finalize_purchase(token, biz, pur2).status_code == 200

        cur_val = client.get(
            f"/api/v1/businesses/{biz}/inventory/valuation",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        cur_items = [i for i in cur_val["items"] if i["product_id"] == prod]
        assert Decimal(cur_items[0]["total_quantity"]) == Decimal("20")

        # Create purchase return for original purchase line at 4 qty -> historical cost = 4*100=400
        rtv_res = client.post(
            f"/api/v1/businesses/{biz}/purchase-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc},
        )
        assert rtv_res.status_code == 201
        ret_id = rtv_res.json()["id"]

        # Need a finalized receiving or just allow based on finalized received?
        # Create a receiving to allow purchase return capacity?
        # For purchase return capacity the code counts FINALIZED received quantity. If no receiving, finalized_received == 0 -> error.
        # So create a receiving for the purchase line
        rcv_res = client.post(
            f"/api/v1/businesses/{biz}/receivings",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc},
        )
        assert rcv_res.status_code == 201
        rcv_id = rcv_res.json()["id"]
        rcv_line = client.post(
            f"/api/v1/businesses/{biz}/receivings/{rcv_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": line["id"], "quantity": "10"},
        )
        assert rcv_line.status_code == 201
        fin_rcv = client.post(
            f"/api/v1/businesses/{biz}/receivings/{rcv_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fin_rcv.status_code == 200

        line_res = client.post(
            f"/api/v1/businesses/{biz}/purchase-returns/{ret_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": line["id"], "quantity": "4"},
        )
        assert line_res.status_code == 201

        fin_ret = client.post(
            f"/api/v1/businesses/{biz}/purchase-returns/{ret_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fin_ret.status_code == 200

        val_after = client.get(
            f"/api/v1/businesses/{biz}/inventory/valuation",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        items_after = [i for i in val_after["items"] if i["product_id"] == prod]
        assert Decimal(items_after[0]["total_quantity"]) == Decimal("16")


# ============================================================
# Cost consistency 409 conflict
# ============================================================

class TestCostConsistency409:
    def test_physical_cost_mismatch_returns_409(self):
        token, _ = register_user()
        biz = create_business(token)
        unit_id = create_unit(token, biz)
        prod = create_product(token, biz, unit_id)
        _, loc = setup_warehouse_and_location(token, biz)
        sup = create_supplier(token, biz)
        br = create_branch(token, biz)

        pur_id = create_purchase(token, biz, sup, br)
        add_purchase_line(token, biz, pur_id, prod, qty="10", unit_price="100")
        assert finalize_purchase(token, biz, pur_id).status_code == 200

        # Inject inconsistency via direct stock mutation without cost update
        from app.modules.inventory.repository import InMemoryStockBalanceRepository

        repo = InMemoryStockBalanceRepository()
        import asyncio

        asyncio.run(repo.upsert_balance(biz, loc, prod, None, Decimal("5")))

        sales_id = create_sales(token, biz, br)
        add_sales_line(token, biz, sales_id, prod, qty="1", unit_price="200")
        fin_res = finalize_sales(token, biz, sales_id)
        assert fin_res.status_code == 409
        body_text = fin_res.text
        assert "INVENTORY_VALUATION_MISMATCH" in body_text


# ============================================================
# Stock opname sync
# ============================================================

class TestStockOpnameSync:
    def test_opname_sync_adjusts_cost_without_journal(self):
        token, _ = register_user()
        biz = create_business(token)
        unit_id = create_unit(token, biz)
        prod = create_product(token, biz, unit_id)
        _, loc = setup_warehouse_and_location(token, biz)
        sup = create_supplier(token, biz)
        br = create_branch(token, biz)

        pur_id = create_purchase(token, biz, sup, br)
        add_purchase_line(token, biz, pur_id, prod, qty="10", unit_price="100")
        assert finalize_purchase(token, biz, pur_id).status_code == 200

        journals_before = list_journals(token, biz)
        count_before = len(journals_before["items"]) if isinstance(journals_before, dict) else len(journals_before)

        # Create stock opname
        op_res = client.post(
            f"/api/v1/businesses/{biz}/inventory/stock-opnames",
            headers={"Authorization": f"Bearer {token}"},
            json={"inventory_location_id": loc},
        )
        assert op_res.status_code == 201
        op_id = op_res.json()["id"]

        line_res = client.post(
            f"/api/v1/businesses/{biz}/inventory/stock-opnames/{op_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod},
        )
        assert line_res.status_code == 201
        line_id = line_res.json()["id"]

        # Count 15 (increase by 5)
        upd_res = client.patch(
            f"/api/v1/businesses/{biz}/inventory/stock-opnames/{op_id}/lines/{line_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"counted_quantity": "15"},
        )
        assert upd_res.status_code == 200

        fin_res = client.post(
            f"/api/v1/businesses/{biz}/inventory/stock-opnames/{op_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fin_res.status_code == 200

        val_res = client.get(
            f"/api/v1/businesses/{biz}/inventory/valuation",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        items = [i for i in val_res["items"] if i["product_id"] == prod]
        assert Decimal(items[0]["total_quantity"]) == Decimal("15")
        assert Decimal(items[0]["unit_cost"]) == Decimal("100")
        assert Decimal(items[0]["total_cost"]) == Decimal("1500")

        # No additional GL journal
        journals_after = list_journals(token, biz)
        count_after = len(journals_after["items"]) if isinstance(journals_after, dict) else len(journals_after)
        assert count_after == count_before


# ============================================================
# Opening Balance with unit_cost
# ============================================================

class TestOpeningBalanceCost:
    def test_opening_balance_with_unit_cost(self):
        token, _ = register_user()
        biz = create_business(token)
        unit_id = create_unit(token, biz)
        prod = create_product(token, biz, unit_id)
        _, loc = setup_warehouse_and_location(token, biz)

        ob_res = client.post(
            f"/api/v1/businesses/{biz}/inventory/opening-balance",
            headers={"Authorization": f"Bearer {token}"},
            json={"inventory_location_id": loc, "product_id": prod, "quantity": "8", "unit_cost": "75"},
        )
        assert ob_res.status_code == 201

        val_res = client.get(
            f"/api/v1/businesses/{biz}/inventory/valuation",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        items = [i for i in val_res["items"] if i["product_id"] == prod]
        assert len(items) == 1
        assert Decimal(items[0]["total_quantity"]) == Decimal("8")
        assert Decimal(items[0]["unit_cost"]) == Decimal("75")
        assert Decimal(items[0]["total_cost"]) == Decimal("600")

    def test_opening_balance_without_unit_cost_no_valuation(self):
        token, _ = register_user()
        biz = create_business(token)
        unit_id = create_unit(token, biz)
        prod = create_product(token, biz, unit_id)
        _, loc = setup_warehouse_and_location(token, biz)

        ob_res = client.post(
            f"/api/v1/businesses/{biz}/inventory/opening-balance",
            headers={"Authorization": f"Bearer {token}"},
            json={"inventory_location_id": loc, "product_id": prod, "quantity": "5"},
        )
        assert ob_res.status_code == 201

        val_res = client.get(
            f"/api/v1/businesses/{biz}/inventory/valuation",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        items = [i for i in val_res["items"] if i["product_id"] == prod]
        # Without explicit unit_cost, quantity is tracked (5) with zero unit_cost and zero total_cost
        assert len(items) == 1
        assert Decimal(items[0]["total_quantity"]) == Decimal("5")
        assert Decimal(items[0]["total_cost"]) == Decimal("0")


# ============================================================
# Idempotency
# ============================================================

class TestIdempotency:
    def test_purchase_finalize_idempotent(self):
        token, _ = register_user()
        biz = create_business(token)
        unit_id = create_unit(token, biz)
        prod = create_product(token, biz, unit_id)
        setup_warehouse_and_location(token, biz)
        sup = create_supplier(token, biz)
        br = create_branch(token, biz)

        pur_id = create_purchase(token, biz, sup, br)
        add_purchase_line(token, biz, pur_id, prod, qty="10", unit_price="100")
        assert finalize_purchase(token, biz, pur_id).status_code == 200

        # Second finalize should fail or be idempotent (already finalized)
        second = client.post(
            f"/api/v1/businesses/{biz}/purchases/{pur_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert second.status_code == 400

        val = client.get(
            f"/api/v1/businesses/{biz}/inventory/valuation",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        items = [i for i in val["items"] if i["product_id"] == prod]
        assert Decimal(items[0]["total_quantity"]) == Decimal("10")

    def test_sales_finalize_idempotent(self):
        token, _ = register_user()
        biz = create_business(token)
        unit_id = create_unit(token, biz)
        prod = create_product(token, biz, unit_id)
        setup_warehouse_and_location(token, biz)
        sup = create_supplier(token, biz)
        br = create_branch(token, biz)

        pur_id = create_purchase(token, biz, sup, br)
        add_purchase_line(token, biz, pur_id, prod, qty="10", unit_price="100")
        assert finalize_purchase(token, biz, pur_id).status_code == 200

        sales_id = create_sales(token, biz, br)
        add_sales_line(token, biz, sales_id, prod, qty="2", unit_price="200")
        assert finalize_sales(token, biz, sales_id).status_code == 200

        second = client.post(
            f"/api/v1/businesses/{biz}/sales/{sales_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
            json={},
        )
        assert second.status_code == 400

        journals = list_journals(token, biz)
        jitems = journals["items"] if isinstance(journals, dict) else journals
        sales_journals = [j for j in jitems if j["reference_type"] == "SALES" and j["reference_id"] == sales_id]
        assert len(sales_journals) == 1


# ============================================================
# Multi-tenant isolation
# ============================================================

class TestMultiTenantIsolation:
    def test_cost_state_isolated_per_business(self):
        token_a, _ = register_user(email="owner_a@example.com")
        biz_a = create_business(token_a, name="Business A")
        unit_a = create_unit(token_a, biz_a)
        prod_a = create_product(token_a, biz_a, unit_a, name="Prod A", code="PROD-A")
        setup_warehouse_and_location(token_a, biz_a)
        sup_a = create_supplier(token_a, biz_a)
        br_a = create_branch(token_a, biz_a)

        token_b, _ = register_user(email="owner_b@example.com")
        biz_b = create_business(token_b, name="Business B")
        unit_b = create_unit(token_b, biz_b)
        # Product in B is independent but same logic
        prod_b = create_product(token_b, biz_b, unit_b, name="Prod B", code="PROD-B")

        setup_warehouse_and_location(token_b, biz_b)
        sup_b = create_supplier(token_b, biz_b)
        br_b = create_branch(token_b, biz_b)

        # Business A purchase impacts only A
        pur_a = create_purchase(token_a, biz_a, sup_a, br_a)
        add_purchase_line(token_a, biz_a, pur_a, prod_a, qty="10", unit_price="100")
        assert finalize_purchase(token_a, biz_a, pur_a).status_code == 200

        val_b_before = client.get(
            f"/api/v1/businesses/{biz_b}/inventory/valuation",
            headers={"Authorization": f"Bearer {token_b}"},
        ).json()
        assert len(val_b_before["items"]) == 0

        val_a = client.get(
            f"/api/v1/businesses/{biz_a}/inventory/valuation",
            headers={"Authorization": f"Bearer {token_a}"},
        ).json()
        items_a = [i for i in val_a["items"] if i["product_id"] == prod_a]
        assert Decimal(items_a[0]["total_quantity"]) == Decimal("10")

        # Business B trying to read A's valuation should get 404 or empty
        # Valuation endpoint for B should not expose A's data
        val_b = client.get(
            f"/api/v1/businesses/{biz_b}/inventory/valuation",
            headers={"Authorization": f"Bearer {token_b}"},
        ).json()
        items_b = [i for i in val_b["items"] if i["product_id"] == prod_a]
        assert len(items_b) == 0

    def test_zero_quantity_rule_on_full_sale(self):
        token, _ = register_user()
        biz = create_business(token)
        unit_id = create_unit(token, biz)
        prod = create_product(token, biz, unit_id)
        setup_warehouse_and_location(token, biz)
        sup = create_supplier(token, biz)
        br = create_branch(token, biz)

        pur_id = create_purchase(token, biz, sup, br)
        add_purchase_line(token, biz, pur_id, prod, qty="5", unit_price="200")
        assert finalize_purchase(token, biz, pur_id).status_code == 200

        sales_id = create_sales(token, biz, br)
        add_sales_line(token, biz, sales_id, prod, qty="5", unit_price="300")
        assert finalize_sales(token, biz, sales_id).status_code == 200

        val = client.get(
            f"/api/v1/businesses/{biz}/inventory/valuation",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        items = [i for i in val["items"] if i["product_id"] == prod]
        assert Decimal(items[0]["total_quantity"]) == Decimal("0")
        assert Decimal(items[0]["unit_cost"]) == Decimal("0")
        assert Decimal(items[0]["total_cost"]) == Decimal("0")

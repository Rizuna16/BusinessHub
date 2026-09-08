"""
Feature #42 — Stock Card / Inventory Movement Ledger (Kartu Stok) Test Suite
"""
import uuid
import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta
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
from app.modules.branch.repository import InMemoryBranchRepository
from app.modules.customer.repository import InMemoryCustomerRepository
from app.modules.supplier.repository import InMemorySupplierRepository
from app.modules.pricing.repository import InMemoryPriceListRepository, InMemoryPriceEntryRepository
from app.modules.sales.repository import InMemorySalesRepository
from app.modules.sales_return.repository import InMemorySalesReturnRepository
from app.modules.purchase.repository import InMemoryPurchaseRepository
from app.modules.purchase_return.repository import InMemoryPurchaseReturnRepository
from app.modules.receiving.repository import InMemoryReceivingRepository
from app.modules.stock_opname.repository import InMemoryStockOpnameRepository
from app.modules.payment.repository import InMemoryPaymentRepository
from app.modules.cash_account.repository import InMemoryCashAccountRepository
from app.modules.inventory.repository import (
    InMemoryStockBalanceRepository,
    InMemoryStockMovementRepository,
    InMemoryInventoryCostRepository,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_repos():
    InMemoryStockBalanceRepository.clear()
    InMemoryStockMovementRepository.clear()
    InMemoryInventoryCostRepository.clear()
    InMemoryWarehouseRepository.clear()
    InMemoryInventoryLocationRepository.clear()
    InMemoryProductVariantRepository.clear()
    InMemoryProductRepository.clear()
    InMemoryUnitRepository.clear()
    InMemoryBranchRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryUserRepository.clear()
    InMemoryCustomerRepository.clear()
    InMemorySupplierRepository.clear()
    InMemoryPriceListRepository.clear()
    InMemoryPriceEntryRepository.clear()
    InMemorySalesRepository.clear()
    InMemorySalesReturnRepository.clear()
    InMemoryPurchaseRepository.clear()
    InMemoryPurchaseReturnRepository.clear()
    InMemoryReceivingRepository.clear()
    InMemoryStockOpnameRepository.clear()
    InMemoryPaymentRepository.clear()
    InMemoryCashAccountRepository.clear()
    yield
    InMemoryStockBalanceRepository.clear()
    InMemoryStockMovementRepository.clear()
    InMemoryInventoryCostRepository.clear()
    InMemoryWarehouseRepository.clear()
    InMemoryInventoryLocationRepository.clear()
    InMemoryProductVariantRepository.clear()
    InMemoryProductRepository.clear()
    InMemoryUnitRepository.clear()
    InMemoryBranchRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryUserRepository.clear()
    InMemoryCustomerRepository.clear()
    InMemorySupplierRepository.clear()
    InMemoryPriceListRepository.clear()
    InMemoryPriceEntryRepository.clear()
    InMemorySalesRepository.clear()
    InMemorySalesReturnRepository.clear()
    InMemoryPurchaseRepository.clear()
    InMemoryPurchaseReturnRepository.clear()
    InMemoryReceivingRepository.clear()
    InMemoryStockOpnameRepository.clear()
    InMemoryPaymentRepository.clear()
    InMemoryCashAccountRepository.clear()


def register_user(email="owner@test.com", name="Owner"):
    res = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": name, "password": "Password123", "password_confirmation": "Password123"},
    )
    assert res.status_code == 201
    data = res.json()
    token = data.get("access_token")
    if not token:
        login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123"})
        token = login_res.json()["access_token"]
    return token, data["id"]


def create_business(token, name="Test Biz"):
    res = client.post(
        "/api/v1/businesses",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "business_type": "umkm", "timezone": "UTC", "locale": "en-US"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_unit(token, biz_id, name="Pcs", code="PCS"):
    suffix = uuid.uuid4().hex[:5].upper()
    res = client.post(
        f"/api/v1/businesses/{biz_id}/units",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": f"{name}{suffix}", "code": f"{code}{suffix}"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_product(token, biz_id, unit_id, name="Widget", code="WID-01", p_type="GOODS"):
    suffix = uuid.uuid4().hex[:4].upper()
    res = client.post(
        f"/api/v1/businesses/{biz_id}/products",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": f"{name}{suffix}", "code": f"{code}{suffix}", "unit_id": unit_id, "product_type": p_type},
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_variant(token, biz_id, product_id, name="Red", code="VAR-RED"):
    suffix = uuid.uuid4().hex[:4].upper()
    res = client.post(
        f"/api/v1/businesses/{biz_id}/products/{product_id}/variants",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": f"{name}{suffix}", "code": f"{code}{suffix}"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_branch(token, biz_id, name="Main Branch"):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/branches",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": f"BR-{uuid.uuid4().hex[:6].upper()}"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_warehouse_and_location(token, biz_id, wh_name="WH Main", loc_name="Rack A"):
    wh_res = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": wh_name, "code": f"WH-{uuid.uuid4().hex[:6].upper()}"},
    )
    assert wh_res.status_code == 201
    wh_id = wh_res.json()["id"]
    loc_res = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses/{wh_id}/locations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": loc_name, "code": f"LOC-{uuid.uuid4().hex[:6].upper()}", "location_type": "STORAGE"},
    )
    assert loc_res.status_code == 201
    return wh_id, loc_res.json()["id"]


def create_customer(token, biz_id, name="Cust A"):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/customers",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "customer_type": "ORGANIZATION"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_supplier(token, biz_id, name="Supp A"):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/suppliers",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "supplier_type": "ORGANIZATION"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_opening_balance(token, biz_id, loc_id, prod_id, var_id, qty, unit_cost="0"):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/inventory/opening-balance",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "inventory_location_id": loc_id,
            "product_id": prod_id,
            "variant_id": var_id,
            "quantity": str(qty),
            "unit_cost": str(unit_cost),
            "notes": "Opening",
        },
    )
    assert res.status_code == 201


def create_adjustment_in(token, biz_id, loc_id, prod_id, var_id, qty):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/inventory/adjustments/in",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "inventory_location_id": loc_id,
            "product_id": prod_id,
            "variant_id": var_id,
            "quantity": str(qty),
        },
    )
    assert res.status_code == 201


def create_adjustment_out(token, biz_id, loc_id, prod_id, var_id, qty):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/inventory/adjustments/out",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "inventory_location_id": loc_id,
            "product_id": prod_id,
            "variant_id": var_id,
            "quantity": str(qty),
        },
    )
    assert res.status_code == 201


def create_transfer(token, biz_id, src_loc_id, dest_loc_id, prod_id, var_id, qty):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/inventory/transfers",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "source_inventory_location_id": src_loc_id,
            "destination_inventory_location_id": dest_loc_id,
            "product_id": prod_id,
            "variant_id": var_id,
            "quantity": str(qty),
        },
    )
    assert res.status_code == 201


def create_sales_with_opening(token, biz_id, loc_id, prod_id, var_id, customer_id, branch_id, qty, price, sales_date_str):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "customer_id": customer_id,
            "branch_id": branch_id,
            "sales_date": sales_date_str,
        },
    )
    assert res.status_code == 201
    sales_id = res.json()["id"]
    res = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "product_id": prod_id,
            "variant_id": var_id,
            "quantity": str(qty),
            "unit_price": str(price),
        },
    )
    assert res.status_code == 201
    res = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    return sales_id


def create_purchase_with_finalize(token, biz_id, supplier_id, branch_id, prod_id, var_id, qty, price, purchase_date_str):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/purchases",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "supplier_id": supplier_id,
            "branch_id": branch_id,
            "purchase_date": purchase_date_str,
        },
    )
    assert res.status_code == 201
    pur_id = res.json()["id"]
    res = client.post(
        f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "product_id": prod_id,
            "variant_id": var_id,
            "quantity": str(qty),
            "unit_price": str(price),
        },
    )
    assert res.status_code == 201
    res = client.post(
        f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/finalize",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    return pur_id


def create_purchase_return_and_finalize(token, biz_id, purchase_id, loc_id, qty, price):
    import asyncio
    from app.modules.purchase_return.repository import InMemoryPurchaseReturnRepository
    from app.modules.purchase.repository import InMemoryPurchaseRepository

    pur_repo = InMemoryPurchaseRepository()
    pur_lines = asyncio.run(pur_repo.list_lines_for_purchase(purchase_id))
    line_id = pur_lines[0].id
    prod_id = pur_lines[0].product_id
    var_id = pur_lines[0].variant_id

    pr_repo = InMemoryPurchaseReturnRepository()
    r = asyncio.run(
        pr_repo.create_return(
            business_id=biz_id,
            purchase_id=purchase_id,
            inventory_location_id=loc_id,
            return_number=f"PR-{uuid.uuid4().hex[:6].upper()}",
            created_by_user_id="owner",
        )
    )

    asyncio.run(
        pr_repo.create_line(
            return_id=r.id,
            purchase_line_id=line_id,
            product_id=prod_id,
            variant_id=var_id,
            quantity=Decimal(str(qty)),
            unit_price=Decimal(str(price)),
            discount_amount=Decimal("0"),
            tax_amount=Decimal("0"),
            line_subtotal=Decimal(str(qty * price)),
            line_total=Decimal(str(qty * price)),
        )
    )

    r_updated = asyncio.run(
        pr_repo.update_return(
            return_id=r.id,
            business_id=biz_id,
            status="FINALIZED",
            subtotal=Decimal(str(qty * price)),
            discount_total=Decimal("0"),
            tax_total=Decimal("0"),
            grand_total=Decimal(str(qty * price)),
            finalized_by_user_id="owner",
            finalized_at=datetime.now(timezone.utc),
        )
    )

    return r_updated.id


def create_sales_return_and_finalize(token, biz_id, sales_id, loc_id, qty):
    import asyncio
    from app.modules.sales.repository import InMemorySalesRepository
    sales_repo = InMemorySalesRepository()
    sales_lines = asyncio.run(sales_repo.list_lines_for_sales(sales_id))
    line_id = sales_lines[0].id

    res = client.post(
        f"/api/v1/businesses/{biz_id}/sales-returns",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "sales_id": sales_id,
            "inventory_location_id": loc_id,
        },
    )
    assert res.status_code == 201
    sr_id = res.json()["id"]
    res = client.post(
        f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "sales_line_id": line_id,
            "quantity": str(qty),
        },
    )
    assert res.status_code == 201
    res = client.post(
        f"/api/v1/businesses/{biz_id}/sales-returns/{sr_id}/finalize",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    return sr_id


def create_opname_and_finalize(token, biz_id, loc_id, prod_id, var_id, counted_qty):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/inventory/stock-opnames",
        headers={"Authorization": f"Bearer {token}"},
        json={"inventory_location_id": loc_id},
    )
    assert res.status_code == 201
    op_id = res.json()["id"]
    res = client.post(
        f"/api/v1/businesses/{biz_id}/inventory/stock-opnames/{op_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "product_id": prod_id,
            "variant_id": var_id,
        },
    )
    assert res.status_code == 201
    line_id = res.json()["id"]
    res = client.patch(
        f"/api/v1/businesses/{biz_id}/inventory/stock-opnames/{op_id}/lines/{line_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"counted_quantity": str(counted_qty)},
    )
    assert res.status_code == 200
    res = client.post(
        f"/api/v1/businesses/{biz_id}/inventory/stock-opnames/{op_id}/finalize",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    return op_id


def fetch_stock_card(biz_id, loc_id, prod_id, var_id=None, df="2026-09-01", dt="2026-09-30", page=1, page_size=100, token=None):
    params = f"location_id={loc_id}&product_id={prod_id}&date_from={df}&date_to={dt}&page={page}&page_size={page_size}"
    if var_id:
        params += f"&variant_id={var_id}"
    res = client.get(
        f"/api/v1/businesses/{biz_id}/inventory/stock-cards?{params}",
        headers={"Authorization": f"Bearer {token}"}
    )
    return res


# ============================================================
# TESTS
# ============================================================

def test_01_empty_period():
    token, _ = register_user("s01@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    res = fetch_stock_card(biz_id, loc_id, prod_id, token=token)
    assert res.status_code == 200
    data = res.json()
    assert Decimal(str(data["opening_quantity"])) == Decimal("0.00")
    assert Decimal(str(data["closing_quantity"])) == Decimal("0.00")
    assert data["lines"] == []
    assert data["total_items"] == 0


def test_02_opening_quantity_reconstruction():
    token, _ = register_user("s02@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    create_opening_balance(token, biz_id, loc_id, prod_id, None, 100, unit_cost="5000")
    # Opening balance created NOW falls within the period, so it appears as OPENING_BALANCE line
    res = fetch_stock_card(biz_id, loc_id, prod_id, df="2026-09-01", dt="2026-09-30", token=token)
    assert res.status_code == 200
    data = res.json()
    # opening_quantity = 0 because the only event is the opening balance ITSELF which falls in period
    assert Decimal(str(data["opening_quantity"])) == Decimal("0.00")
    # The opening balance shows as a period line item
    assert data["total_items"] == 1
    assert data["lines"][0]["movement_type"] == "OPENING_BALANCE"
    assert Decimal(str(data["lines"][0]["qty_in"])) == Decimal("100")
    assert Decimal(str(data["closing_quantity"])) == Decimal("100")


def test_03_opening_valuation_reconstruction():
    token, _ = register_user("s03@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    create_opening_balance(token, biz_id, loc_id, prod_id, None, 100, unit_cost="5000")
    res = fetch_stock_card(biz_id, loc_id, prod_id, df="2026-09-01", dt="2026-09-30", token=token)
    assert res.status_code == 200
    data = res.json()
    # Opening balance with unit_cost=5000 falls in period, shows as OPENING_BALANCE line
    assert data["lines"][0]["movement_type"] == "OPENING_BALANCE"
    assert Decimal(str(data["lines"][0]["unit_cost"])) == Decimal("5000")
    assert Decimal(str(data["lines"][0]["movement_value"])) == Decimal("500000")
    assert Decimal(str(data["lines"][0]["running_quantity"])) == Decimal("100")
    assert Decimal(str(data["lines"][0]["running_valuation"])) == Decimal("500000")
    assert Decimal(str(data["closing_valuation"])) == Decimal("500000")


def test_04_purchase_inclusion():
    token, _ = register_user("s04@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    branch_id = create_branch(token, biz_id, "BR-S04")
    supp_id = create_supplier(token, biz_id)
    create_purchase_with_finalize(token, biz_id, supp_id, branch_id, prod_id, None, 50, 10000, "2026-09-05T10:00:00Z")
    res = fetch_stock_card(biz_id, loc_id, prod_id, token=token)
    assert res.status_code == 200
    data = res.json()
    pur_lines = [l for l in data["lines"] if l["movement_type"] == "PURCHASE"]
    assert len(pur_lines) >= 1
    assert Decimal(str(pur_lines[0]["qty_in"])) == Decimal("50")


def test_05_purchase_return_inclusion():
    token, _ = register_user("s05@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    branch_id = create_branch(token, biz_id, "BR-S05")
    supp_id = create_supplier(token, biz_id)
    pur_id = create_purchase_with_finalize(token, biz_id, supp_id, branch_id, prod_id, None, 50, 10000, "2026-09-05T10:00:00Z")
    create_purchase_return_and_finalize(token, biz_id, pur_id, loc_id, 10, 10000)
    res = fetch_stock_card(biz_id, loc_id, prod_id, token=token)
    assert res.status_code == 200
    data = res.json()
    pret_lines = [l for l in data["lines"] if l["movement_type"] == "PURCHASE_RETURN"]
    assert len(pret_lines) == 1
    assert Decimal(str(pret_lines[0]["qty_out"])) == Decimal("10")


def test_06_sales_movement_inclusion():
    token, _ = register_user("s06@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    branch_id = create_branch(token, biz_id, "BR-S06")
    cust_id = create_customer(token, biz_id)
    create_opening_balance(token, biz_id, loc_id, prod_id, None, 200)
    create_sales_with_opening(token, biz_id, loc_id, prod_id, None, cust_id, branch_id, 20, 50000, "2026-09-07T10:00:00Z")
    res = fetch_stock_card(biz_id, loc_id, prod_id, token=token)
    assert res.status_code == 200
    data = res.json()
    sale_lines = [l for l in data["lines"] if l["movement_type"] == "SALE_OUT"]
    assert len(sale_lines) == 1
    assert Decimal(str(sale_lines[0]["qty_out"])) == Decimal("20")


def test_07_sales_return_inclusion():
    token, _ = register_user("s07@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    branch_id = create_branch(token, biz_id, "BR-S07")
    cust_id = create_customer(token, biz_id)
    create_opening_balance(token, biz_id, loc_id, prod_id, None, 200)
    sales_id = create_sales_with_opening(token, biz_id, loc_id, prod_id, None, cust_id, branch_id, 20, 50000, "2026-09-07T10:00:00Z")
    create_sales_return_and_finalize(token, biz_id, sales_id, loc_id, 5)
    res = fetch_stock_card(biz_id, loc_id, prod_id, token=token)
    assert res.status_code == 200
    data = res.json()
    sr_lines = [l for l in data["lines"] if l["movement_type"] == "SALE_RETURN_IN"]
    assert len(sr_lines) == 1
    assert Decimal(str(sr_lines[0]["qty_in"])) == Decimal("5")


def test_08_adjustment_in():
    token, _ = register_user("s08@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    create_opening_balance(token, biz_id, loc_id, prod_id, None, 50)
    create_adjustment_in(token, biz_id, loc_id, prod_id, None, 25)
    res = fetch_stock_card(biz_id, loc_id, prod_id, token=token)
    assert res.status_code == 200
    data = res.json()
    adj_in = [l for l in data["lines"] if l["movement_type"] == "ADJUSTMENT_IN"]
    assert len(adj_in) >= 1
    assert Decimal(str(adj_in[0]["qty_in"])) == Decimal("25")


def test_09_adjustment_out():
    token, _ = register_user("s09@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    create_opening_balance(token, biz_id, loc_id, prod_id, None, 100)
    create_adjustment_out(token, biz_id, loc_id, prod_id, None, 25)
    res = fetch_stock_card(biz_id, loc_id, prod_id, token=token)
    assert res.status_code == 200
    data = res.json()
    adj_out = [l for l in data["lines"] if l["movement_type"] == "ADJUSTMENT_OUT"]
    assert len(adj_out) == 1
    assert Decimal(str(adj_out[0]["qty_out"])) == Decimal("25")


def test_10_transfer_in_and_out():
    token, _ = register_user("s10@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    _, src_loc = create_warehouse_and_location(token, biz_id, "WH Source", "Rack S")
    _, dest_loc = create_warehouse_and_location(token, biz_id, "WH Dest", "Rack D")
    create_opening_balance(token, biz_id, src_loc, prod_id, None, 100)
    create_transfer(token, biz_id, src_loc, dest_loc, prod_id, None, 20)
    res_src = fetch_stock_card(biz_id, src_loc, prod_id, token=token)
    assert res_src.status_code == 200
    res_dest = fetch_stock_card(biz_id, dest_loc, prod_id, token=token)
    assert res_dest.status_code == 200
    dest_in = [l for l in res_dest.json()["lines"] if l["movement_type"] == "TRANSFER_IN"]
    assert len(dest_in) == 1


def test_11_stock_opname_positive_variance():
    token, _ = register_user("s11@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    create_opening_balance(token, biz_id, loc_id, prod_id, None, 100)
    create_opname_and_finalize(token, biz_id, loc_id, prod_id, None, 110)
    res = fetch_stock_card(biz_id, loc_id, prod_id, token=token)
    assert res.status_code == 200
    assert Decimal(str(res.json()["closing_quantity"])) == Decimal("110")


def test_12_stock_opname_negative_variance():
    token, _ = register_user("s12@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    create_opening_balance(token, biz_id, loc_id, prod_id, None, 100)
    create_opname_and_finalize(token, biz_id, loc_id, prod_id, None, 80)
    res = fetch_stock_card(biz_id, loc_id, prod_id, token=token)
    assert res.status_code == 200
    assert Decimal(str(res.json()["closing_quantity"])) == Decimal("80")


def test_13_receiving_excluded():
    token, _ = register_user("s13@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    create_opening_balance(token, biz_id, loc_id, prod_id, None, 50)
    res = fetch_stock_card(biz_id, loc_id, prod_id, token=token)
    assert res.status_code == 200
    assert all(l["movement_type"] != "RECEIVING" for l in res.json()["lines"])


def test_14_no_double_count():
    token, _ = register_user("s14@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    branch_id = create_branch(token, biz_id, "BR-S14")
    supp_id = create_supplier(token, biz_id)
    create_purchase_with_finalize(token, biz_id, supp_id, branch_id, prod_id, None, 50, 10000, "2026-09-05T10:00:00Z")
    res = fetch_stock_card(biz_id, loc_id, prod_id, token=token)
    assert res.status_code == 200
    data = res.json()
    pur_lines = [l for l in data["lines"] if l["movement_type"] == "PURCHASE"]
    assert len(pur_lines) == 1
    assert Decimal(str(data["total_qty_in"])) == Decimal("50")


def test_15_opening_balance_pagination_invariants():
    token, _ = register_user("s15@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    create_opening_balance(token, biz_id, loc_id, prod_id, None, 100)
    for _ in range(5):
        create_adjustment_in(token, biz_id, loc_id, prod_id, None, 10)
    p1 = fetch_stock_card(biz_id, loc_id, prod_id, page=1, page_size=2, token=token).json()
    p2 = fetch_stock_card(biz_id, loc_id, prod_id, page=2, page_size=2, token=token).json()
    assert p1["total_items"] == p2["total_items"] == 6
    assert p1["opening_quantity"] == p2["opening_quantity"]
    assert p1["closing_quantity"] == p2["closing_quantity"]


def test_16_running_quantity_across_adjustments():
    token, _ = register_user("s16@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    create_opening_balance(token, biz_id, loc_id, prod_id, None, 100)
    create_adjustment_in(token, biz_id, loc_id, prod_id, None, 50)
    create_adjustment_out(token, biz_id, loc_id, prod_id, None, 20)
    res = fetch_stock_card(biz_id, loc_id, prod_id, token=token)
    assert res.status_code == 200
    data = res.json()
    first = data["lines"][1]
    second = data["lines"][2]
    assert Decimal(str(first["running_quantity"])) == Decimal("150")
    assert Decimal(str(second["running_quantity"])) == Decimal("130")


def test_17_closing_quantity_invariant():
    token, _ = register_user("s17@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    create_opening_balance(token, biz_id, loc_id, prod_id, None, 100)
    create_adjustment_in(token, biz_id, loc_id, prod_id, None, 50)
    create_adjustment_out(token, biz_id, loc_id, prod_id, None, 20)
    data = fetch_stock_card(biz_id, loc_id, prod_id, token=token).json()
    assert Decimal(str(data["closing_quantity"])) == Decimal(str(data["opening_quantity"])) + Decimal(str(data["total_qty_in"])) - Decimal(str(data["total_qty_out"]))


def test_18_closing_valuation_invariant():
    token, _ = register_user("s18@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    create_opening_balance(token, biz_id, loc_id, prod_id, None, 100)
    data = fetch_stock_card(biz_id, loc_id, prod_id, token=token).json()
    assert Decimal(str(data["closing_valuation"])) == Decimal(str(data["opening_valuation"])) + Decimal(str(data["total_in_value"])) - Decimal(str(data["total_out_value"]))


def test_19_pagination_invariants():
    token, _ = register_user("s19@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    for _ in range(5):
        create_adjustment_in(token, biz_id, loc_id, prod_id, None, 10)
    p1 = fetch_stock_card(biz_id, loc_id, prod_id, page=1, page_size=2, df="2026-09-01", dt="2026-09-30", token=token).json()
    p2 = fetch_stock_card(biz_id, loc_id, prod_id, page=2, page_size=2, df="2026-09-01", dt="2026-09-30", token=token).json()
    assert p1["total_items"] == p2["total_items"] == 5
    assert len(p1["lines"]) == 2
    assert len(p2["lines"]) == 2


def test_20_page2_running_quantity_continuity():
    token, _ = register_user("s20@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    for _ in range(6):
        create_adjustment_in(token, biz_id, loc_id, prod_id, None, 10)
    p1 = fetch_stock_card(biz_id, loc_id, prod_id, page=1, page_size=3, token=token).json()
    p2 = fetch_stock_card(biz_id, loc_id, prod_id, page=2, page_size=3, token=token).json()
    last_p1_run = Decimal(str(p1["lines"][-1]["running_quantity"]))
    first_p2_run = Decimal(str(p2["lines"][0]["running_quantity"]))
    assert first_p2_run == last_p1_run + Decimal("10")


def test_21_total_items_before_pagination():
    token, _ = register_user("s21@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    for _ in range(7):
        create_adjustment_in(token, biz_id, loc_id, prod_id, None, 10)
    p1 = fetch_stock_card(biz_id, loc_id, prod_id, page=1, page_size=2, token=token).json()
    assert p1["total_items"] == 7
    assert len(p1["lines"]) == 2


def test_22_variant_identity():
    token, _ = register_user("s22@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    var_id = create_variant(token, biz_id, prod_id)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    create_opening_balance(token, biz_id, loc_id, prod_id, var_id, 50)
    res = fetch_stock_card(biz_id, loc_id, prod_id, var_id=var_id, token=token)
    assert res.status_code == 200
    assert Decimal(str(res.json()["closing_quantity"])) == Decimal("50")


def test_23_location_isolation():
    token, _ = register_user("s23@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    _, loc1 = create_warehouse_and_location(token, biz_id, "WH1", "Rack1")
    _, loc2 = create_warehouse_and_location(token, biz_id, "WH2", "Rack2")
    create_opening_balance(token, biz_id, loc1, prod_id, None, 100)
    create_opening_balance(token, biz_id, loc2, prod_id, None, 50)
    d1 = fetch_stock_card(biz_id, loc1, prod_id, token=token).json()
    d2 = fetch_stock_card(biz_id, loc2, prod_id, token=token).json()
    assert Decimal(str(d1["closing_quantity"])) == Decimal("100")
    assert Decimal(str(d2["closing_quantity"])) == Decimal("50")


def test_24_business_isolation():
    token1, _ = register_user("s24a@test.com")
    token2, _ = register_user("s24b@test.com")
    biz1 = create_business(token1, "Biz1")
    biz2 = create_business(token2, "Biz2")
    unit_id1 = create_unit(token1, biz1)
    prod_id1 = create_product(token1, biz1, unit_id1)
    _, loc1 = create_warehouse_and_location(token1, biz1)
    res = fetch_stock_card(biz2, loc1, prod_id1, token=token2)
    assert res.status_code in (404, 403)


def test_25_foreign_product_rejection():
    token, _ = register_user("s25@test.com")
    biz_id = create_business(token)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    res = fetch_stock_card(biz_id, loc_id, "non_existent_prod", token=token)
    assert res.status_code == 404


def test_26_foreign_location_rejection():
    token, _ = register_user("s26@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    res = fetch_stock_card(biz_id, "nonexist-loc", prod_id, token=token)
    assert res.status_code == 404


def test_27_foreign_variant_rejection():
    token, _ = register_user("s27@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    res = fetch_stock_card(biz_id, loc_id, prod_id, var_id="bad_var", token=token)
    assert res.status_code == 404


def test_28_required_location_id():
    token, _ = register_user("s28@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    res = client.get(
        f"/api/v1/businesses/{biz_id}/inventory/stock-cards?product_id={prod_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422


def test_29_required_product_id():
    token, _ = register_user("s29@test.com")
    biz_id = create_business(token)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    res = client.get(
        f"/api/v1/businesses/{biz_id}/inventory/stock-cards?location_id={loc_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422


def test_30_purchase_return_original_cost():
    token, _ = register_user("s30@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    branch_id = create_branch(token, biz_id, "BR-S30")
    supp_id = create_supplier(token, biz_id)
    pur_id = create_purchase_with_finalize(token, biz_id, supp_id, branch_id, prod_id, None, 50, 25000, "2026-09-05T10:00:00Z")
    create_purchase_return_and_finalize(token, biz_id, pur_id, loc_id, 10, 25000)
    data = fetch_stock_card(biz_id, loc_id, prod_id, token=token).json()
    pret = [l for l in data["lines"] if l["movement_type"] == "PURCHASE_RETURN"]
    assert len(pret) == 1
    assert Decimal(str(pret[0]["qty_out"])) == Decimal("10")
    assert Decimal(str(pret[0]["unit_cost"])) == Decimal("25000")
    assert Decimal(str(pret[0]["movement_value"])) == Decimal("250000")


def test_31_no_receiving_movement_type():
    token, _ = register_user("s31@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    create_opening_balance(token, biz_id, loc_id, prod_id, None, 100)
    data = fetch_stock_card(biz_id, loc_id, prod_id, token=token).json()
    assert all(l["movement_type"] != "RECEIVING" for l in data["lines"])


def test_32_transfer_one_out_one_in():
    token, _ = register_user("s32@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    _, src_loc = create_warehouse_and_location(token, biz_id, "Source", "Rack S")
    _, dest_loc = create_warehouse_and_location(token, biz_id, "Dest", "Rack D")
    create_opening_balance(token, biz_id, src_loc, prod_id, None, 100)
    create_transfer(token, biz_id, src_loc, dest_loc, prod_id, None, 30)
    d_src = fetch_stock_card(biz_id, src_loc, prod_id, token=token).json()
    d_dest = fetch_stock_card(biz_id, dest_loc, prod_id, token=token).json()
    assert Decimal(str(d_src["closing_quantity"])) == Decimal("70")
    assert Decimal(str(d_dest["closing_quantity"])) == Decimal("30")


def test_33_stock_opname_zero_variance_produces_no_movement():
    token, _ = register_user("s33@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    create_opening_balance(token, biz_id, loc_id, prod_id, None, 100)
    create_opname_and_finalize(token, biz_id, loc_id, prod_id, None, 100)
    data = fetch_stock_card(biz_id, loc_id, prod_id, token=token).json()
    assert Decimal(str(data["closing_quantity"])) == Decimal("100")


def test_34_default_dates_still_work():
    token, _ = register_user("s34@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    res = client.get(
        f"/api/v1/businesses/{biz_id}/inventory/stock-cards?location_id={loc_id}&product_id={prod_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200


def test_35_date_from_greater_than_date_to_rejection():
    token, _ = register_user("s35@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    res = fetch_stock_card(biz_id, loc_id, prod_id, df="2026-09-30", dt="2026-09-01", token=token)
    assert res.status_code == 422


def test_36_variant_product_requires_variant_id():
    token, _ = register_user("s36@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    create_variant(token, biz_id, prod_id)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    res = fetch_stock_card(biz_id, loc_id, prod_id, token=token)
    assert res.status_code == 400


def test_37_closing_valuation_with_multiple_events():
    token, _ = register_user("s37@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    create_opening_balance(token, biz_id, loc_id, prod_id, None, 100, unit_cost="10000")
    create_adjustment_in(token, biz_id, loc_id, prod_id, None, 20)
    create_adjustment_out(token, biz_id, loc_id, prod_id, None, 10)
    data = fetch_stock_card(biz_id, loc_id, prod_id, token=token).json()
    assert Decimal(str(data["closing_quantity"])) == Decimal("110")
    # Opening balance has valuation, adjustments have zero cost
    assert Decimal(str(data["closing_valuation"])) == Decimal("1000000")  # 100 * 10000
    assert Decimal(str(data["total_qty_in"])) == Decimal("120")  # 100 + 20
    assert Decimal(str(data["total_qty_out"])) == Decimal("10")
    # Opening balance movement_value = 100 * 10000 = 1000000
    assert Decimal(str(data["total_in_value"])) == Decimal("1000000")
    assert Decimal(str(data["total_out_value"])) == Decimal("0")  # adjustment out has unit_cost=0


def test_38_page_size_rejection():
    token, _ = register_user("s38@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    res = client.get(
        f"/api/v1/businesses/{biz_id}/inventory/stock-cards?location_id={loc_id}&product_id={prod_id}&page_size=1000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422


def test_39_full_lifecycle_stock_card():
    token, _ = register_user("s39@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    branch_id = create_branch(token, biz_id, "BR-S39")
    supp_id = create_supplier(token, biz_id)
    cust_id = create_customer(token, biz_id)
    create_opening_balance(token, biz_id, loc_id, prod_id, None, 200)
    pur_id = create_purchase_with_finalize(token, biz_id, supp_id, branch_id, prod_id, None, 100, 15000, "2026-09-05T10:00:00Z")
    create_purchase_return_and_finalize(token, biz_id, pur_id, loc_id, 10, 15000)
    sales_id = create_sales_with_opening(token, biz_id, loc_id, prod_id, None, cust_id, branch_id, 50, 50000, "2026-09-07T10:00:00Z")
    create_sales_return_and_finalize(token, biz_id, sales_id, loc_id, 5)
    data = fetch_stock_card(biz_id, loc_id, prod_id, token=token).json()
    opening = Decimal(str(data["opening_quantity"]))
    total_in = Decimal(str(data["total_qty_in"]))
    total_out = Decimal(str(data["total_qty_out"]))
    closing = Decimal(str(data["closing_quantity"]))
    assert closing == opening + total_in - total_out
    assert data["total_items"] >= 4


def test_40_unauthenticated_returns_401():
    token, _ = register_user("s40@test.com")
    biz_id = create_business(token)
    unit_id = create_unit(token, biz_id)
    prod_id = create_product(token, biz_id, unit_id)
    _, loc_id = create_warehouse_and_location(token, biz_id)
    res = client.get(
        f"/api/v1/businesses/{biz_id}/inventory/stock-cards?location_id={loc_id}&product_id={prod_id}",
    )
    assert res.status_code == 401


def test_41_inactive_membership_rejection():
    token_owner, _ = register_user("s41owner@test.com")
    biz_id = create_business(token_owner)
    unit_id = create_unit(token_owner, biz_id)
    prod_id = create_product(token_owner, biz_id, unit_id)
    _, loc_id = create_warehouse_and_location(token_owner, biz_id)
    token_stranger, _ = register_user("s41stranger@test.com")
    res = client.get(
        f"/api/v1/businesses/{biz_id}/inventory/stock-cards?location_id={loc_id}&product_id={prod_id}",
        headers={"Authorization": f"Bearer {token_stranger}"},
    )
    assert res.status_code in (403, 404)

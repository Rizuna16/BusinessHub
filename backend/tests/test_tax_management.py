"""
Feature #37 — PPN / Tax Management Test Suite
Comprehensive coverage for Tax Configuration, Calculation Engine, Integration, and Reports.
"""
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from app.main import app
from app.modules.authentication.repository import InMemoryUserRepository
from app.modules.account.repository import InMemoryAccountRepository
from app.modules.business.repository import InMemoryBusinessRepository
from app.modules.business_membership.repository import InMemoryBusinessMembershipRepository
from app.modules.accounting.repository import InMemoryAccountingRepository
from app.modules.sales.repository import InMemorySalesRepository
from app.modules.purchase.repository import InMemoryPurchaseRepository
from app.modules.payment.repository import InMemoryPaymentRepository
from app.modules.cash_account.repository import InMemoryCashAccountRepository
from app.modules.expense.repository import InMemoryExpenseRepository
from app.modules.inventory.repository import InMemoryStockBalanceRepository, InMemoryStockMovementRepository, InMemoryInventoryCostRepository
from app.modules.warehouse.repository import InMemoryWarehouseRepository, InMemoryInventoryLocationRepository
from app.modules.customer.repository import InMemoryCustomerRepository
from app.modules.supplier.repository import InMemorySupplierRepository
from app.modules.product.repository import InMemoryProductRepository
from app.modules.product_variant.repository import InMemoryProductVariantRepository
from app.modules.category.repository import InMemoryCategoryRepository
from app.modules.unit.repository import InMemoryUnitRepository
from app.modules.pricing.repository import InMemoryPriceListRepository, InMemoryPriceEntryRepository
from app.modules.barcode.repository import InMemoryBarcodeRepository
from app.modules.receiving.repository import InMemoryReceivingRepository
from app.modules.supplier_catalog.repository import InMemorySupplierCatalogRepository
from app.modules.branch.repository import InMemoryBranchRepository
from app.modules.stock_opname.repository import InMemoryStockOpnameRepository
from app.modules.sales_payment.repository import InMemorySalesPaymentRepository
from app.modules.accounting.schemas import TaxTreatment, PricingMode
from app.modules.accounting.tax_calculation import tax_calculation_service
from app.modules.sales_return.repository import InMemorySalesReturnRepository
from app.modules.purchase_return.repository import InMemoryPurchaseReturnRepository

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_repositories():
    InMemoryAccountingRepository.clear()
    InMemorySalesRepository.clear()
    InMemorySalesReturnRepository.clear()
    InMemoryPurchaseRepository.clear()
    InMemoryPurchaseReturnRepository.clear()
    InMemoryPaymentRepository.clear()
    InMemoryCashAccountRepository.clear()
    InMemoryExpenseRepository.clear()
    InMemoryStockBalanceRepository.clear()
    InMemoryStockMovementRepository.clear()
    InMemoryInventoryCostRepository.clear()
    InMemoryInventoryLocationRepository.clear()
    InMemoryWarehouseRepository.clear()
    InMemoryCustomerRepository.clear()
    InMemorySupplierRepository.clear()
    InMemoryProductRepository.clear()
    InMemoryProductVariantRepository.clear()
    InMemoryCategoryRepository.clear()
    InMemoryUnitRepository.clear()
    InMemoryPriceListRepository.clear()
    InMemoryPriceEntryRepository.clear()
    InMemoryBarcodeRepository.clear()
    InMemoryReceivingRepository.clear()
    InMemorySupplierCatalogRepository.clear()
    InMemoryBranchRepository.clear()
    InMemoryStockOpnameRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryUserRepository.clear()
    InMemorySalesPaymentRepository.clear()
    yield
    InMemoryAccountingRepository.clear()
    InMemorySalesRepository.clear()
    InMemorySalesReturnRepository.clear()
    InMemoryPurchaseRepository.clear()
    InMemoryPurchaseReturnRepository.clear()
    InMemoryPaymentRepository.clear()
    InMemoryCashAccountRepository.clear()
    InMemoryExpenseRepository.clear()
    InMemoryStockBalanceRepository.clear()
    InMemoryStockMovementRepository.clear()
    InMemoryInventoryCostRepository.clear()
    InMemoryInventoryLocationRepository.clear()
    InMemoryWarehouseRepository.clear()
    InMemoryCustomerRepository.clear()
    InMemorySupplierRepository.clear()
    InMemoryProductRepository.clear()
    InMemoryProductVariantRepository.clear()
    InMemoryCategoryRepository.clear()
    InMemoryUnitRepository.clear()
    InMemoryPriceListRepository.clear()
    InMemoryPriceEntryRepository.clear()
    InMemoryBarcodeRepository.clear()
    InMemoryReceivingRepository.clear()
    InMemorySupplierCatalogRepository.clear()
    InMemoryBranchRepository.clear()
    InMemoryStockOpnameRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryUserRepository.clear()
    InMemorySalesPaymentRepository.clear()


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


def add_member(token, biz_id, member_token, role="MEMBER"):
    member_user_id = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {member_token}"}
    ).json()["id"]
    res = client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": member_user_id, "role": role},
    )
    assert res.status_code == 201
    return res.json()


def create_branch(token, biz_id):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/branches",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Main Branch", "code": "MB"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_unit(token, biz_id, name=None, code="PCS"):
    import uuid
    unique_id = uuid.uuid4().hex[:6].upper()
    unit_name = name if name else f"Unit_{unique_id}"
    unique_code = f"U{unique_id}"
    res = client.post(
        f"/api/v1/businesses/{biz_id}/units",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": unit_name, "code": unique_code},
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_product(token, biz_id, name="Product 1", ptype="SERVICE", tax_treatment="STANDARD_NON_LUXURY"):
    unit_id = create_unit(token, biz_id)
    res = client.post(
        f"/api/v1/businesses/{biz_id}/products",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": name,
            "code": f"PRD-{name.replace(' ', '-').upper()}",
            "product_type": ptype,
            "unit_id": unit_id,
            "tax_treatment": tax_treatment,
        },
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_customer(token, biz_id, name="Customer 1"):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/customers",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "customer_type": "INDIVIDUAL"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_supplier(token, biz_id, name="Supplier 1"):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/suppliers",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "supplier_type": "ORGANIZATION"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def setup_warehouse_and_location(token, biz_id):
    wh_res = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Main Warehouse", "code": "WH-MAIN"},
    )
    assert wh_res.status_code == 201
    wh_id = wh_res.json()["id"]
    loc_res = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses/{wh_id}/locations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Main Location", "code": "LOC-MAIN", "location_type": "GENERAL"},
    )
    assert loc_res.status_code == 201
    return loc_res.json()["id"]


def add_opening_stock(token, biz_id, location_id, product_id, qty="100"):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/inventory/opening-balance",
        headers={"Authorization": f"Bearer {token}"},
        json={"inventory_location_id": location_id, "product_id": product_id, "quantity": qty},
    )
    assert res.status_code == 201


def create_finalized_receiving(token, biz_id, pur_id, pline_id, loc_id, rcv_qty=100):
    rcv_res = client.post(
        f"/api/v1/businesses/{biz_id}/receivings",
        headers={"Authorization": f"Bearer {token}"},
        json={"purchase_id": pur_id, "inventory_location_id": loc_id},
    )
    assert rcv_res.status_code == 201
    rcv_id = rcv_res.json()["id"]
    line_res = client.post(
        f"/api/v1/businesses/{biz_id}/receivings/{rcv_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"purchase_line_id": pline_id, "quantity": rcv_qty},
    )
    assert line_res.status_code == 201
    fin_res = client.post(
        f"/api/v1/businesses/{biz_id}/receivings/{rcv_id}/finalize",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fin_res.status_code == 200
    return rcv_id


# ═══════════════════════════════════════════════════
# 1. TAX CONFIGURATION TESTS (1-6)
# ═══════════════════════════════════════════════════

class TestTaxConfiguration:
    def test_get_default_tax_config_lazy_creation(self):
        token, _ = register_user()
        biz_id = create_business(token)

        res = client.get(
            f"/api/v1/businesses/{biz_id}/accounting/tax-config",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["tax_enabled"] is False
        assert data["pricing_mode"] == "TAX_EXCLUSIVE"
        assert data["default_tax_treatment"] == "STANDARD_NON_LUXURY"

    def test_owner_can_update_tax_config(self):
        token, _ = register_user()
        biz_id = create_business(token)

        res = client.patch(
            f"/api/v1/businesses/{biz_id}/accounting/tax-config",
            headers={"Authorization": f"Bearer {token}"},
            json={"tax_enabled": True, "pricing_mode": "TAX_INCLUSIVE"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["tax_enabled"] is True
        assert data["pricing_mode"] == "TAX_INCLUSIVE"

    def test_admin_can_update_tax_config(self):
        owner_token, _ = register_user("owner@test.com")
        biz_id = create_business(owner_token)

        admin_token, _ = register_user("admin@test.com", "Admin User")
        add_member(owner_token, biz_id, admin_token, role="ADMIN")

        res = client.patch(
            f"/api/v1/businesses/{biz_id}/accounting/tax-config",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"tax_enabled": True},
        )
        assert res.status_code == 200
        assert res.json()["tax_enabled"] is True

    def test_member_cannot_update_tax_config(self):
        owner_token, _ = register_user("owner@test.com")
        biz_id = create_business(owner_token)

        member_token, _ = register_user("member@test.com", "Member User")
        add_member(owner_token, biz_id, member_token, role="MEMBER")

        res = client.patch(
            f"/api/v1/businesses/{biz_id}/accounting/tax-config",
            headers={"Authorization": f"Bearer {member_token}"},
            json={"tax_enabled": True},
        )
        assert res.status_code == 403

    def test_cross_business_tax_config_isolation(self):
        t1, _ = register_user("a@test.com")
        t2, _ = register_user("b@test.com")
        biz1 = create_business(t1)
        biz2 = create_business(t2)

        res = client.patch(
            f"/api/v1/businesses/{biz2}/accounting/tax-config",
            headers={"Authorization": f"Bearer {t2}"},
            json={"tax_enabled": True},
        )
        assert res.status_code == 200
        assert res.json()["business_id"] == biz2

        res1 = client.get(
            f"/api/v1/businesses/{biz1}/accounting/tax-config",
            headers={"Authorization": f"Bearer {t1}"},
        )
        assert res1.json()["tax_enabled"] is False

    def test_unauthenticated_tax_config_rejected(self):
        res = client.get("/api/v1/businesses/biz-123/accounting/tax-config")
        assert res.status_code == 401


# ═══════════════════════════════════════════════════
# 2. PRODUCT TAX TREATMENT TESTS (15-16)
# ═══════════════════════════════════════════════════

class TestProductTaxTreatment:
    def test_product_created_with_tax_treatment(self):
        token, _ = register_user()
        biz_id = create_business(token)
        prod_id = create_product(token, biz_id, name="Exempt Item", tax_treatment="NON_TAXABLE")

        res = client.get(
            f"/api/v1/businesses/{biz_id}/products/{prod_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert res.json()["tax_treatment"] == "NON_TAXABLE"

    def test_product_tax_treatment_default(self):
        token, _ = register_user()
        biz_id = create_business(token)
        prod_id = create_product(token, biz_id, name="Standard Item")

        res = client.get(
            f"/api/v1/businesses/{biz_id}/products/{prod_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert res.json()["tax_treatment"] == "STANDARD_NON_LUXURY"


# ═══════════════════════════════════════════════════
# 3. SALES VAT ACCOUNTING INTEGRATION TESTS (17-23)
# ═══════════════════════════════════════════════════

class TestSalesVatAccounting:
    def test_taxable_sale_finalized_journal_split(self):
        """
        Tax enabled + STANDARD_NON_LUXURY product.
        Sale: 10 units × 100,000 = 1,000,000 commercial amount
        Exclusive tax: DPP = 916,666.67, PPN = 110,000.00, Gross = 1,110,000.00
        Journal entry:
          Dr 1200 AR = 1,110,000
          Cr 4100 Revenue = 1,000,000
          Cr 2200 Output VAT = 110,000
        """
        token, _ = register_user()
        biz_id = create_business(token)
        branch_id = create_branch(token, biz_id)
        cust_id = create_customer(token, biz_id)
        prod_id = create_product(token, biz_id, name="Taxable Service")

        # Enable PPN
        client.patch(
            f"/api/v1/businesses/{biz_id}/accounting/tax-config",
            headers={"Authorization": f"Bearer {token}"},
            json={"tax_enabled": True, "pricing_mode": "TAX_EXCLUSIVE"},
        )

        sales_res = client.post(
            f"/api/v1/businesses/{biz_id}/sales",
            headers={"Authorization": f"Bearer {token}"},
            json={"customer_id": cust_id, "branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
        )
        sales_id = sales_res.json()["id"]

        client.post(
            f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": 10, "unit_price": 100000},
        )

        fin = client.post(
            f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fin.status_code == 200

        # Inspect generated journal
        journals = client.get(
            f"/api/v1/businesses/{biz_id}/accounting/journals",
            headers={"Authorization": f"Bearer {token}"},
        ).json()["items"]

        sale_j = next((j for j in journals if j.get("reference_type") == "SALES" and j.get("reference_id") == sales_id), None)
        assert sale_j is not None
        assert len(sale_j["lines"]) == 3

        lines = {l["account_code"]: (Decimal(str(l["debit"])), Decimal(str(l["credit"]))) for l in sale_j["lines"]}
        assert lines["1200"] == (Decimal("1110000"), Decimal("0"))
        assert lines["4100"] == (Decimal("0"), Decimal("1000000"))
        assert lines["2200"] == (Decimal("0"), Decimal("110000"))

    def test_non_taxable_sale_no_vat_line(self):
        token, _ = register_user()
        biz_id = create_business(token)
        branch_id = create_branch(token, biz_id)
        cust_id = create_customer(token, biz_id)
        prod_id = create_product(token, biz_id, name="Exempt Service", tax_treatment="NON_TAXABLE")

        client.patch(
            f"/api/v1/businesses/{biz_id}/accounting/tax-config",
            headers={"Authorization": f"Bearer {token}"},
            json={"tax_enabled": True},
        )

        sales_res = client.post(
            f"/api/v1/businesses/{biz_id}/sales",
            headers={"Authorization": f"Bearer {token}"},
            json={"customer_id": cust_id, "branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
        )
        sales_id = sales_res.json()["id"]

        client.post(
            f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": 5, "unit_price": 100000},
        )

        client.post(
            f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )

        journals = client.get(
            f"/api/v1/businesses/{biz_id}/accounting/journals",
            headers={"Authorization": f"Bearer {token}"},
        ).json()["items"]

        sale_j = next((j for j in journals if j.get("reference_type") == "SALES" and j.get("reference_id") == sales_id), None)
        assert sale_j is not None
        assert len(sale_j["lines"]) == 2
        assert "2200" not in [l["account_code"] for l in sale_j["lines"]]


# ═══════════════════════════════════════════════════
# 4. PURCHASE VAT ACCOUNTING INTEGRATION TESTS (24-28)
# ═══════════════════════════════════════════════════

class TestPurchaseVatAccounting:
    def test_creditable_purchase_finalized_journal_split(self):
        """
        Creditable purchase: input_vat_creditable=True, tax_enabled=True
        Purchase: 10 units × 50,000 = 500,000 net commercial
        Tax: 55,000. Gross = 555,000.
        Journal:
          Dr 1300 Inventory Assets = 500,000
          Dr 1400 Input VAT = 55,000
          Cr 2100 Accounts Payable = 555,000
        """
        token, _ = register_user()
        biz_id = create_business(token)
        branch_id = create_branch(token, biz_id)
        sup_id = create_supplier(token, biz_id)
        prod_id = create_product(token, biz_id, name="Taxable Goods", ptype="GOODS")

        client.patch(
            f"/api/v1/businesses/{biz_id}/accounting/tax-config",
            headers={"Authorization": f"Bearer {token}"},
            json={"tax_enabled": True, "pricing_mode": "TAX_EXCLUSIVE"},
        )

        pur_res = client.post(
            f"/api/v1/businesses/{biz_id}/purchases",
            headers={"Authorization": f"Bearer {token}"},
            json={"supplier_id": sup_id, "branch_id": branch_id, "purchase_date": datetime.now(timezone.utc).isoformat(), "input_vat_creditable": True},
        )
        pur_id = pur_res.json()["id"]

        client.post(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": 10, "unit_price": 50000},
        )

        fin = client.post(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fin.status_code == 200

        journals = client.get(
            f"/api/v1/businesses/{biz_id}/accounting/journals",
            headers={"Authorization": f"Bearer {token}"},
        ).json()["items"]

        pur_j = next((j for j in journals if j.get("reference_type") == "PURCHASE" and j.get("reference_id") == pur_id), None)
        assert pur_j is not None
        assert len(pur_j["lines"]) == 3

        lines = {l["account_code"]: (Decimal(str(l["debit"])), Decimal(str(l["credit"]))) for l in pur_j["lines"]}
        assert lines["1300"] == (Decimal("500000"), Decimal("0"))
        assert lines["1400"] == (Decimal("55000"), Decimal("0"))
        assert lines["2100"] == (Decimal("0"), Decimal("555000"))

    def test_non_creditable_purchase_absorbs_vat(self):
        """
        Non-creditable purchase: input_vat_creditable=False
        Gross = 555,000 absorbs VAT into 1300 Inventory Assets. No 1400 Input VAT line.
        """
        token, _ = register_user()
        biz_id = create_business(token)
        branch_id = create_branch(token, biz_id)
        sup_id = create_supplier(token, biz_id)
        prod_id = create_product(token, biz_id, name="Non-Creditable Goods", ptype="GOODS")

        client.patch(
            f"/api/v1/businesses/{biz_id}/accounting/tax-config",
            headers={"Authorization": f"Bearer {token}"},
            json={"tax_enabled": True},
        )

        pur_res = client.post(
            f"/api/v1/businesses/{biz_id}/purchases",
            headers={"Authorization": f"Bearer {token}"},
            json={"supplier_id": sup_id, "branch_id": branch_id, "purchase_date": datetime.now(timezone.utc).isoformat(), "input_vat_creditable": False},
        )
        pur_id = pur_res.json()["id"]

        client.post(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": 10, "unit_price": 50000},
        )

        client.post(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )

        journals = client.get(
            f"/api/v1/businesses/{biz_id}/accounting/journals",
            headers={"Authorization": f"Bearer {token}"},
        ).json()["items"]

        pur_j = next((j for j in journals if j.get("reference_type") == "PURCHASE" and j.get("reference_id") == pur_id), None)
        assert pur_j is not None
        assert len(pur_j["lines"]) == 2
        assert "1400" not in [l["account_code"] for l in pur_j["lines"]]


# ═══════════════════════════════════════════════════
# 5. TAX SUMMARY AGGREGATION TESTS (36-43)
# ═══════════════════════════════════════════════════

class TestTaxSummaryReport:
    def test_get_tax_summary_empty(self):
        token, _ = register_user()
        biz_id = create_business(token)

        res = client.get(
            f"/api/v1/businesses/{biz_id}/accounting/reports/tax-summary?year=2026&month=1",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["year"] == 2026
        assert data["month"] == 1
        assert Decimal(str(data["output_vat"])) == Decimal("0")
        assert Decimal(str(data["input_vat"])) == Decimal("0")
        assert Decimal(str(data["net_vat"])) == Decimal("0")
        assert data["taxable_sales_count"] == 0
        assert data["taxable_purchase_count"] == 0

    def test_tax_summary_aggregates_output_and_input_vat(self):
        token, _ = register_user()
        biz_id = create_business(token)
        branch_id = create_branch(token, biz_id)
        cust_id = create_customer(token, biz_id)
        sup_id = create_supplier(token, biz_id)
        prod_sale = create_product(token, biz_id, name="Sale Item", ptype="SERVICE")
        prod_pur = create_product(token, biz_id, name="Pur Item", ptype="GOODS")

        client.patch(
            f"/api/v1/businesses/{biz_id}/accounting/tax-config",
            headers={"Authorization": f"Bearer {token}"},
            json={"tax_enabled": True},
        )

        now_iso = datetime.now(timezone.utc).isoformat()

        # Sale: 1,000,000 → Output VAT = 110,000
        sales_res = client.post(
            f"/api/v1/businesses/{biz_id}/sales",
            headers={"Authorization": f"Bearer {token}"},
            json={"customer_id": cust_id, "branch_id": branch_id, "sales_date": now_iso},
        )
        s_id = sales_res.json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/sales/{s_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_sale, "quantity": 10, "unit_price": 100000},
        )
        client.post(
            f"/api/v1/businesses/{biz_id}/sales/{s_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Purchase: 500,000 creditable → Input VAT = 55,000
        pur_res = client.post(
            f"/api/v1/businesses/{biz_id}/purchases",
            headers={"Authorization": f"Bearer {token}"},
            json={"supplier_id": sup_id, "branch_id": branch_id, "purchase_date": now_iso, "input_vat_creditable": True},
        )
        p_id = pur_res.json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/purchases/{p_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_pur, "quantity": 10, "unit_price": 50000},
        )
        client.post(
            f"/api/v1/businesses/{biz_id}/purchases/{p_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )

        now = datetime.now(timezone.utc)
        res = client.get(
            f"/api/v1/businesses/{biz_id}/accounting/reports/tax-summary?year={now.year}&month={now.month}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert Decimal(str(data["output_vat"])) == Decimal("110000")
        assert Decimal(str(data["input_vat"])) == Decimal("55000")
        assert Decimal(str(data["net_vat"])) == Decimal("55000")
        assert data["taxable_sales_count"] == 1
        assert data["taxable_purchase_count"] == 1

    def test_unauthenticated_tax_summary_rejected(self):
        res = client.get("/api/v1/businesses/biz-123/accounting/reports/tax-summary?year=2026&month=1")
        assert res.status_code == 401

    def test_member_can_read_tax_summary(self):
        owner_token, _ = register_user("owner@test.com")
        biz_id = create_business(owner_token)

        member_token, _ = register_user("member@test.com", "Member")
        add_member(owner_token, biz_id, member_token, role="MEMBER")

        res = client.get(
            f"/api/v1/businesses/{biz_id}/accounting/reports/tax-summary?year=2026&month=1",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert res.status_code == 200
        assert res.json()["year"] == 2026


# ═══════════════════════════════════════════════════
# 6. DEFECT FIXES — TAX SNAPSHOT, RETURN VAT REVERSALS
# ═══════════════════════════════════════════════════

class TestPurchaseTaxSnapshotFreeze:
    """Defect #1: Purchase finalization must freeze TaxSnapshot on each line."""

    def test_purchase_finalization_freezes_tax_snapshot(self):
        token, _ = register_user()
        biz_id = create_business(token)
        branch_id = create_branch(token, biz_id)
        sup_id = create_supplier(token, biz_id)
        prod_id = create_product(token, biz_id, name="Taxable Goods", ptype="GOODS")

        client.patch(
            f"/api/v1/businesses/{biz_id}/accounting/tax-config",
            headers={"Authorization": f"Bearer {token}"},
            json={"tax_enabled": True, "pricing_mode": "TAX_EXCLUSIVE"},
        )

        pur_res = client.post(
            f"/api/v1/businesses/{biz_id}/purchases",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "supplier_id": sup_id,
                "branch_id": branch_id,
                "purchase_date": datetime.now(timezone.utc).isoformat(),
                "input_vat_creditable": True,
            },
        )
        pur_id = pur_res.json()["id"]

        client.post(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": 10, "unit_price": 50000},
        )

        fin = client.post(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fin.status_code == 200

        # Verify purchase lines have tax_snapshot frozen
        pur_doc = client.get(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        lines = pur_doc["lines"]
        assert len(lines) == 1
        line = lines[0]
        assert line["tax_snapshot"] is not None
        assert "tax_amount" in line["tax_snapshot"]
        assert Decimal(str(line["tax_snapshot"]["tax_amount"])) == Decimal("55000")
        assert line["tax_snapshot"]["tax_treatment"] == "STANDARD_NON_LUXURY"
        assert line["tax_snapshot"]["pricing_mode"] == "TAX_EXCLUSIVE"

    def test_purchase_tax_snapshot_historical_safety(self):
        """After finalization, changing TaxConfiguration/Product must not mutate historical snapshot."""
        token, _ = register_user()
        biz_id = create_business(token)
        branch_id = create_branch(token, biz_id)
        sup_id = create_supplier(token, biz_id)
        prod_id = create_product(token, biz_id, name="Taxable Goods", ptype="GOODS")

        client.patch(
            f"/api/v1/businesses/{biz_id}/accounting/tax-config",
            headers={"Authorization": f"Bearer {token}"},
            json={"tax_enabled": True, "pricing_mode": "TAX_EXCLUSIVE"},
        )

        pur_res = client.post(
            f"/api/v1/businesses/{biz_id}/purchases",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "supplier_id": sup_id,
                "branch_id": branch_id,
                "purchase_date": datetime.now(timezone.utc).isoformat(),
                "input_vat_creditable": True,
            },
        )
        pur_id = pur_res.json()["id"]

        client.post(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": 10, "unit_price": 50000},
        )

        fin = client.post(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fin.status_code == 200

        # Capture original snapshot tax_amount
        pur_before = client.get(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        lines_before = pur_before["lines"]
        original_tax = Decimal(str(lines_before[0]["tax_snapshot"]["tax_amount"]))

        # Change TaxConfiguration to TAX_INCLUSIVE
        client.patch(
            f"/api/v1/businesses/{biz_id}/accounting/tax-config",
            headers={"Authorization": f"Bearer {token}"},
            json={"tax_enabled": True, "pricing_mode": "TAX_INCLUSIVE"},
        )

        # Change product tax treatment
        client.patch(
            f"/api/v1/businesses/{biz_id}/products/{prod_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"tax_treatment": "NON_TAXABLE"},
        )

        # Snapshot must remain unchanged
        pur_after = client.get(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        lines_after = pur_after["lines"]
        assert lines_after[0]["tax_snapshot"]["tax_amount"] == str(original_tax)
        assert lines_after[0]["tax_snapshot"]["tax_treatment"] == "STANDARD_NON_LUXURY"
        assert lines_after[0]["tax_snapshot"]["pricing_mode"] == "TAX_EXCLUSIVE"


class TestSalesReturnOutputVatReversal:
    """Defect #2: Sales Return must reverse Output VAT (account 2200) using historical snapshot."""

    def test_taxable_sales_return_reverses_output_vat(self):
        """
        Original taxable sale:
          net  = 1,000,000
          VAT  =   110,000
          gross = 1,110,000
        50% return:
          Dr 4100 Sales Revenue = 500,000
          Dr 2200 Output VAT    =  55,000
          Cr 1200 AR            = 555,000
        """
        token, _ = register_user()
        biz_id = create_business(token)
        branch_id = create_branch(token, biz_id)
        cust_id = create_customer(token, biz_id)
        prod_id = create_product(token, biz_id, name="Taxable Goods", ptype="GOODS")
        loc_id = setup_warehouse_and_location(token, biz_id)
        add_opening_stock(token, biz_id, loc_id, prod_id, qty="100")

        client.patch(
            f"/api/v1/businesses/{biz_id}/accounting/tax-config",
            headers={"Authorization": f"Bearer {token}"},
            json={"tax_enabled": True, "pricing_mode": "TAX_EXCLUSIVE"},
        )

        # Create and finalize original sale
        sales_res = client.post(
            f"/api/v1/businesses/{biz_id}/sales",
            headers={"Authorization": f"Bearer {token}"},
            json={"customer_id": cust_id, "branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
        )
        sales_id = sales_res.json()["id"]

        client.post(
            f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": 10, "unit_price": 100000},
        )
        client.post(
            f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Get the sales line ID
        sales_doc = client.get(
            f"/api/v1/businesses/{biz_id}/sales/{sales_id}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        sales_lines = sales_doc["lines"]
        sales_line_id = sales_lines[0]["id"]

        # Create 50% sales return (5 units)
        ret_res = client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_id": sales_id, "inventory_location_id": loc_id},
        )
        assert ret_res.status_code == 201
        ret_id = ret_res.json()["id"]

        client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns/{ret_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_line_id": sales_line_id, "quantity": 5},
        )

        # Finalize return
        fin = client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns/{ret_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fin.status_code == 200

        # Inspect generated journal for the return
        journals = client.get(
            f"/api/v1/businesses/{biz_id}/accounting/journals",
            headers={"Authorization": f"Bearer {token}"},
        ).json()["items"]

        ret_j = next((j for j in journals if j.get("reference_type") == "SALES_RETURN" and j.get("reference_id") == ret_id), None)
        assert ret_j is not None, "Sales Return journal not found"

        # Should have 3 lines: Dr 4100, Dr 2200, Cr 1200
        lines = {l["account_code"]: (Decimal(str(l["debit"])), Decimal(str(l["credit"]))) for l in ret_j["lines"]}
        assert lines["4100"] == (Decimal("500000"), Decimal("0")), "Dr 4100 Sales Revenue net return"
        assert lines["2200"] == (Decimal("55000"), Decimal("0")), "Dr 2200 Output VAT reversal"
        assert lines["1200"] == (Decimal("0"), Decimal("555000")), "Cr 1200 AR gross return"

    def test_sales_return_historical_safety(self):
        """After finalizing original sale, changing config must not affect return VAT."""
        token, _ = register_user()
        biz_id = create_business(token)
        branch_id = create_branch(token, biz_id)
        cust_id = create_customer(token, biz_id)
        prod_id = create_product(token, biz_id, name="Taxable Goods", ptype="GOODS")
        loc_id = setup_warehouse_and_location(token, biz_id)
        add_opening_stock(token, biz_id, loc_id, prod_id, qty="100")

        client.patch(
            f"/api/v1/businesses/{biz_id}/accounting/tax-config",
            headers={"Authorization": f"Bearer {token}"},
            json={"tax_enabled": True, "pricing_mode": "TAX_EXCLUSIVE"},
        )

        sales_res = client.post(
            f"/api/v1/businesses/{biz_id}/sales",
            headers={"Authorization": f"Bearer {token}"},
            json={"customer_id": cust_id, "branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
        )
        sales_id = sales_res.json()["id"]

        client.post(
            f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": 10, "unit_price": 100000},
        )
        client.post(
            f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )

        sales_doc = client.get(
            f"/api/v1/businesses/{biz_id}/sales/{sales_id}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        sales_lines = sales_doc["lines"]
        sales_line_id = sales_lines[0]["id"]

        # Change config BEFORE creating return
        client.patch(
            f"/api/v1/businesses/{biz_id}/accounting/tax-config",
            headers={"Authorization": f"Bearer {token}"},
            json={"tax_enabled": True, "pricing_mode": "TAX_INCLUSIVE"},
        )
        client.patch(
            f"/api/v1/businesses/{biz_id}/products/{prod_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"tax_treatment": "NON_TAXABLE"},
        )

        # Create and finalize return
        ret_res = client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_id": sales_id, "inventory_location_id": loc_id},
        )
        assert ret_res.status_code == 201
        ret_id = ret_res.json()["id"]

        client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns/{ret_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_line_id": sales_line_id, "quantity": 5},
        )
        client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns/{ret_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Return VAT must still use original historical rates
        journals = client.get(
            f"/api/v1/businesses/{biz_id}/accounting/journals",
            headers={"Authorization": f"Bearer {token}"},
        ).json()["items"]

        ret_j = next((j for j in journals if j.get("reference_type") == "SALES_RETURN" and j.get("reference_id") == ret_id), None)
        assert ret_j is not None
        lines = {l["account_code"]: (Decimal(str(l["debit"])), Decimal(str(l["credit"]))) for l in ret_j["lines"]}
        # Original exclusive 11% VAT on 500,000 net = 55,000
        assert lines["2200"] == (Decimal("55000"), Decimal("0")), "Output VAT reversal must use historical snapshot"


class TestPurchaseReturnInputVatReversal:
    """Defect #3: Purchase Return must reverse Input VAT (account 1400) for creditable purchases."""

    def test_creditable_purchase_return_reverses_input_vat(self):
        """
        Original creditable purchase:
          net  = 500,000
          VAT  =  55,000
          gross = 555,000
        50% return:
          Dr 2100 AP           = 277,500
          Cr 1300 Inventory    = 250,000
          Cr 1400 Input VAT    =  27,500
        """
        token, _ = register_user()
        biz_id = create_business(token)
        branch_id = create_branch(token, biz_id)
        sup_id = create_supplier(token, biz_id)
        prod_id = create_product(token, biz_id, name="Taxable Goods", ptype="GOODS")
        loc_id = setup_warehouse_and_location(token, biz_id)

        client.patch(
            f"/api/v1/businesses/{biz_id}/accounting/tax-config",
            headers={"Authorization": f"Bearer {token}"},
            json={"tax_enabled": True, "pricing_mode": "TAX_EXCLUSIVE"},
        )

        # Create and finalize creditable purchase
        pur_res = client.post(
            f"/api/v1/businesses/{biz_id}/purchases",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "supplier_id": sup_id,
                "branch_id": branch_id,
                "purchase_date": datetime.now(timezone.utc).isoformat(),
                "input_vat_creditable": True,
            },
        )
        pur_id = pur_res.json()["id"]

        pur_line = client.post(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": 10, "unit_price": 50000},
        ).json()
        pur_line_id = pur_line["id"]

        client.post(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Finalize receiving to unlock returns
        create_finalized_receiving(token, biz_id, pur_id, pur_line_id, loc_id, rcv_qty=10)

        # Create 50% purchase return (5 units)
        ret_res = client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        )
        assert ret_res.status_code == 201
        ret_id = ret_res.json()["id"]

        client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns/{ret_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": pur_line_id, "quantity": 5},
        )

        # Finalize return
        fin = client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns/{ret_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fin.status_code == 200

        # Inspect generated journal for the return
        journals = client.get(
            f"/api/v1/businesses/{biz_id}/accounting/journals",
            headers={"Authorization": f"Bearer {token}"},
        ).json()["items"]

        ret_j = next((j for j in journals if j.get("reference_type") == "PURCHASE_RETURN" and j.get("reference_id") == ret_id), None)
        assert ret_j is not None, "Purchase Return journal not found"

        # Should have 3 lines: Dr 2100, Cr 1300, Cr 1400
        lines = {l["account_code"]: (Decimal(str(l["debit"])), Decimal(str(l["credit"]))) for l in ret_j["lines"]}
        assert lines["2100"] == (Decimal("277500"), Decimal("0")), "Dr 2100 AP gross return"
        assert lines["1300"] == (Decimal("0"), Decimal("250000")), "Cr 1300 Inventory net return"
        assert lines["1400"] == (Decimal("0"), Decimal("27500")), "Cr 1400 Input VAT reversal"

    def test_non_creditable_purchase_return_has_no_input_vat_reversal(self):
        """
        Non-creditable purchase return:
          Dr 2100 AP = gross_return
          Cr 1300 Inventory = gross_return
          No 1400 line
        """
        token, _ = register_user()
        biz_id = create_business(token)
        branch_id = create_branch(token, biz_id)
        sup_id = create_supplier(token, biz_id)
        prod_id = create_product(token, biz_id, name="Non-Creditable Goods", ptype="GOODS")
        loc_id = setup_warehouse_and_location(token, biz_id)

        client.patch(
            f"/api/v1/businesses/{biz_id}/accounting/tax-config",
            headers={"Authorization": f"Bearer {token}"},
            json={"tax_enabled": True, "pricing_mode": "TAX_EXCLUSIVE"},
        )

        pur_res = client.post(
            f"/api/v1/businesses/{biz_id}/purchases",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "supplier_id": sup_id,
                "branch_id": branch_id,
                "purchase_date": datetime.now(timezone.utc).isoformat(),
                "input_vat_creditable": False,
            },
        )
        pur_id = pur_res.json()["id"]

        pur_line = client.post(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": 10, "unit_price": 50000},
        ).json()
        pur_line_id = pur_line["id"]

        client.post(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Finalize receiving
        create_finalized_receiving(token, biz_id, pur_id, pur_line_id, loc_id, rcv_qty=10)

        ret_res = client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        )
        assert ret_res.status_code == 201
        ret_id = ret_res.json()["id"]

        client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns/{ret_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": pur_line_id, "quantity": 5},
        )

        fin = client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns/{ret_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fin.status_code == 200

        journals = client.get(
            f"/api/v1/businesses/{biz_id}/accounting/journals",
            headers={"Authorization": f"Bearer {token}"},
        ).json()["items"]

        ret_j = next((j for j in journals if j.get("reference_type") == "PURCHASE_RETURN" and j.get("reference_id") == ret_id), None)
        assert ret_j is not None

        lines = {l["account_code"]: (Decimal(str(l["debit"])), Decimal(str(l["credit"]))) for l in ret_j["lines"]}
        assert "1400" not in [l["account_code"] for l in ret_j["lines"]], "Non-creditable return must not create Input VAT line"
        assert lines["2100"] == (Decimal("277500"), Decimal("0"))
        assert lines["1300"] == (Decimal("0"), Decimal("277500"))

    def test_purchase_return_uses_historical_tax_snapshot(self):
        """After finalizing original purchase, changing config must not affect return VAT."""
        token, _ = register_user()
        biz_id = create_business(token)
        branch_id = create_branch(token, biz_id)
        sup_id = create_supplier(token, biz_id)
        prod_id = create_product(token, biz_id, name="Taxable Goods", ptype="GOODS")
        loc_id = setup_warehouse_and_location(token, biz_id)

        client.patch(
            f"/api/v1/businesses/{biz_id}/accounting/tax-config",
            headers={"Authorization": f"Bearer {token}"},
            json={"tax_enabled": True, "pricing_mode": "TAX_EXCLUSIVE"},
        )

        pur_res = client.post(
            f"/api/v1/businesses/{biz_id}/purchases",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "supplier_id": sup_id,
                "branch_id": branch_id,
                "purchase_date": datetime.now(timezone.utc).isoformat(),
                "input_vat_creditable": True,
            },
        )
        pur_id = pur_res.json()["id"]

        pur_line = client.post(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": 10, "unit_price": 50000},
        ).json()
        pur_line_id = pur_line["id"]

        client.post(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Finalize receiving
        create_finalized_receiving(token, biz_id, pur_id, pur_line_id, loc_id, rcv_qty=10)

        # Change config BEFORE creating return
        client.patch(
            f"/api/v1/businesses/{biz_id}/accounting/tax-config",
            headers={"Authorization": f"Bearer {token}"},
            json={"tax_enabled": True, "pricing_mode": "TAX_INCLUSIVE"},
        )
        client.patch(
            f"/api/v1/businesses/{biz_id}/products/{prod_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"tax_treatment": "NON_TAXABLE"},
        )

        ret_res = client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        )
        assert ret_res.status_code == 201
        ret_id = ret_res.json()["id"]
        ret_id = ret_res.json()["id"]

        client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns/{ret_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": pur_line_id, "quantity": 5},
        )

        # Finalize return
        fin = client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns/{ret_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fin.status_code == 200

        # Inspect generated journal for the return
        journals = client.get(
            f"/api/v1/businesses/{biz_id}/accounting/journals",
            headers={"Authorization": f"Bearer {token}"},
        ).json()["items"]

        ret_j = next((j for j in journals if j.get("reference_type") == "PURCHASE_RETURN" and j.get("reference_id") == ret_id), None)
        assert ret_j is not None, "Purchase Return journal not found"

        # Should have 3 lines: Dr 2100, Cr 1300, Cr 1400
        lines = {l["account_code"]: (Decimal(str(l["debit"])), Decimal(str(l["credit"]))) for l in ret_j["lines"]}
        assert lines["2100"] == (Decimal("277500"), Decimal("0")), "Dr 2100 AP gross return"
        assert lines["1300"] == (Decimal("0"), Decimal("250000")), "Cr 1300 Inventory net return"
        assert lines["1400"] == (Decimal("0"), Decimal("27500")), "Cr 1400 Input VAT reversal"



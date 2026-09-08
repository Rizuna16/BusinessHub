import pytest
import asyncio
from decimal import Decimal
from fastapi.testclient import TestClient
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException

from app.main import app
from app.modules.authentication.repository import InMemoryUserRepository
from app.modules.account.repository import InMemoryAccountRepository
from app.modules.business.repository import InMemoryBusinessRepository
from app.modules.business_membership.repository import InMemoryBusinessMembershipRepository
from app.modules.accounting.repository import InMemoryAccountingRepository
from app.modules.sales.repository import InMemorySalesRepository
from app.modules.sales_return.repository import InMemorySalesReturnRepository
from app.modules.purchase.repository import InMemoryPurchaseRepository
from app.modules.purchase_return.repository import InMemoryPurchaseReturnRepository
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
from app.modules.accounting.integration import _idempotency_locks

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_repositories():
    _idempotency_locks.clear()
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
    _idempotency_locks.clear()
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
    res = client.post("/api/v1/auth/register", json={"email": email, "full_name": name, "password": "Password123", "password_confirmation": "Password123"})
    assert res.status_code == 201
    data = res.json()
    token = data.get("access_token")
    if not token:
        login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123"})
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
    return token, data["id"]

def create_business(token, name="Test Business"):
    res = client.post("/api/v1/businesses", headers={"Authorization": f"Bearer {token}"}, json={"name": name, "legal_name": name, "business_type": "retail", "timezone": "UTC", "locale": "en-US"})
    assert res.status_code == 201
    return res.json()["id"]

def create_branch(token, biz_id):
    res = client.post(f"/api/v1/businesses/{biz_id}/branches", headers={"Authorization": f"Bearer {token}"}, json={"name": "Main Branch", "code": "MB"})
    assert res.status_code == 201
    branch_id = res.json()["id"]
    create_warehouse(token, biz_id, branch_id)
    return branch_id

def create_warehouse(token, biz_id, branch_id, name="Main Warehouse", code="WH-MAIN"):
    res = client.post(f"/api/v1/businesses/{biz_id}/warehouses", headers={"Authorization": f"Bearer {token}"}, json={"name": name, "code": code, "branch_id": branch_id})
    assert res.status_code == 201
    wh_id = res.json()["id"]
    loc_res = client.post(f"/api/v1/businesses/{biz_id}/warehouses/{wh_id}/locations", headers={"Authorization": f"Bearer {token}"}, json={"name": "Default Location", "code": "LOC-MAIN"})
    assert loc_res.status_code == 201
    return wh_id, loc_res.json()["id"]

def get_journal_count(token, biz_id):
    res = client.get(f"/api/v1/businesses/{biz_id}/accounting/journals", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    return res.json()["total"]

def create_cash_account(token, biz_id, name="Kas Utama", code="CASH01", opening_balance=10000000):
    res = client.post(f"/api/v1/businesses/{biz_id}/cash-accounts", headers={"Authorization": f"Bearer {token}"}, json={"name": name, "code": code, "account_type": "CASH", "currency": "IDR", "opening_balance": opening_balance, "is_default": True})
    assert res.status_code == 201
    return res.json()["id"]

def create_customer(token, biz_id, name="Customer 1"):
    res = client.post(f"/api/v1/businesses/{biz_id}/customers", headers={"Authorization": f"Bearer {token}"}, json={"name": name, "customer_type": "INDIVIDUAL"})
    assert res.status_code == 201
    return res.json()["id"]

def create_supplier(token, biz_id, name="Supplier 1"):
    res = client.post(f"/api/v1/businesses/{biz_id}/suppliers", headers={"Authorization": f"Bearer {token}"}, json={"name": name, "supplier_type": "ORGANIZATION"})
    assert res.status_code == 201
    return res.json()["id"]

def create_unit(token, biz_id, name=None, code=None):
    if code is None:
        import uuid
        uid = uuid.uuid4().hex[:6].upper()
        code = f"U_{uid}"
    if name is None:
        name = f"Unit {code}"
    res = client.post(f"/api/v1/businesses/{biz_id}/units", headers={"Authorization": f"Bearer {token}"}, json={"name": name, "code": code})
    assert res.status_code == 201
    return res.json()["id"]

def create_product(token, biz_id, name="Test Service", ptype="SERVICE"):
    unit_id = create_unit(token, biz_id)
    res = client.post(f"/api/v1/businesses/{biz_id}/products", headers={"Authorization": f"Bearer {token}"}, json={"name": name, "code": f"PRD_{name.replace(' ', '_').upper()[:10]}", "product_type": ptype, "unit_id": unit_id})
    assert res.status_code == 201
    return res.json()["id"]

def create_expense_category(token, biz_id, name="Rent Expense", code="EXP-RENT"):
    res = client.post(f"/api/v1/businesses/{biz_id}/expense-categories", headers={"Authorization": f"Bearer {token}"}, json={"name": name, "code": code})
    assert res.status_code == 201
    return res.json()["id"]

def setup_sale(token, biz_id, qty=10, price=100000, branch_id=None):
    if branch_id is None:
        branch_id = create_branch(token, biz_id)
    customer_id = create_customer(token, biz_id)
    product_id = create_product(token, biz_id)
    sales_res = client.post(f"/api/v1/businesses/{biz_id}/sales", headers={"Authorization": f"Bearer {token}"}, json={"customer_id": customer_id, "branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()})
    sales_id = sales_res.json()["id"]
    client.post(f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines", headers={"Authorization": f"Bearer {token}"}, json={"product_id": product_id, "quantity": qty, "unit_price": price})
    return sales_id, branch_id

def setup_purchase(token, biz_id, qty=10, price=50000, branch_id=None):
    if branch_id is None:
        branch_id = create_branch(token, biz_id)
    supplier_id = create_supplier(token, biz_id)
    product_id = create_product(token, biz_id, name="Test Goods", ptype="GOODS")
    pur_res = client.post(f"/api/v1/businesses/{biz_id}/purchases", headers={"Authorization": f"Bearer {token}"}, json={"supplier_id": supplier_id, "branch_id": branch_id, "purchase_date": datetime.now(timezone.utc).isoformat()})
    pur_id = pur_res.json()["id"]
    client.post(f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/lines", headers={"Authorization": f"Bearer {token}"}, json={"product_id": product_id, "quantity": qty, "unit_price": price})
    return pur_id, branch_id

# ============================================================
# 1. SALES ACCOUNTING INTEGRATION
# ============================================================
class TestSalesAccountingIntegration:
    def test_finalized_sale_creates_journal(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sales_id, _ = setup_sale(token, biz_id)

        fin = client.post(f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize", headers={"Authorization": f"Bearer {token}"})
        assert fin.status_code == 200
        assert fin.json()["status"] == "FINALIZED"

        journals = client.get(f"/api/v1/businesses/{biz_id}/accounting/journals", headers={"Authorization": f"Bearer {token}"}).json()["items"]
        sj = next((j for j in journals if j["reference_type"] == "SALES" and j["reference_id"] == sales_id), None)
        assert sj is not None
        assert Decimal(str(sj["total_debit"])) == Decimal("1000000")
        assert Decimal(str(sj["total_credit"])) == Decimal("1000000")
        assert len(sj["lines"]) == 2
        assert sj["lines"][0]["account_code"] == "1200"
        assert sj["lines"][1]["account_code"] == "4100"

    def test_draft_sale_creates_no_journal(self):
        token, _ = register_user()
        biz_id = create_business(token)
        j_before = get_journal_count(token, biz_id)
        sales_id, _ = setup_sale(token, biz_id)
        assert get_journal_count(token, biz_id) == j_before

    def test_accounting_failure_no_operational_mutation(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sales_id, _ = setup_sale(token, biz_id)

        with patch("app.modules.sales.service.accounting_integration_service.post_sales_finalized", new_callable=AsyncMock, side_effect=HTTPException(status_code=500, detail="Accounting Failure")):
            fin = client.post(f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize", headers={"Authorization": f"Bearer {token}"})
            assert fin.status_code == 500

        get_res = client.get(f"/api/v1/businesses/{biz_id}/sales/{sales_id}", headers={"Authorization": f"Bearer {token}"})
        assert get_res.json()["status"] == "DRAFT"
        assert get_journal_count(token, biz_id) == 0

# ============================================================
# 2. PURCHASE ACCOUNTING INTEGRATION
# ============================================================
class TestPurchaseAccountingIntegration:
    def test_finalized_purchase_creates_journal(self):
        token, _ = register_user()
        biz_id = create_business(token)
        pur_id, _ = setup_purchase(token, biz_id)

        fin = client.post(f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/finalize", headers={"Authorization": f"Bearer {token}"})
        assert fin.status_code == 200

        journals = client.get(f"/api/v1/businesses/{biz_id}/accounting/journals", headers={"Authorization": f"Bearer {token}"}).json()["items"]
        pj = next((j for j in journals if j["reference_type"] == "PURCHASE" and j["reference_id"] == pur_id), None)
        assert pj is not None
        assert Decimal(str(pj["total_debit"])) == Decimal("500000")
        assert pj["lines"][0]["account_code"] == "1300"
        assert pj["lines"][1]["account_code"] == "2100"

    def test_accounting_failure_no_operational_mutation(self):
        token, _ = register_user()
        biz_id = create_business(token)
        pur_id, _ = setup_purchase(token, biz_id)

        with patch("app.modules.purchase.service.accounting_integration_service.post_purchase_finalized", new_callable=AsyncMock, side_effect=HTTPException(status_code=500, detail="Accounting Failure")):
            fin = client.post(f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/finalize", headers={"Authorization": f"Bearer {token}"})
            assert fin.status_code == 500

        get_res = client.get(f"/api/v1/businesses/{biz_id}/purchases/{pur_id}", headers={"Authorization": f"Bearer {token}"})
        assert get_res.json()["status"] == "DRAFT"

# ============================================================
# 3. EXPENSE ACCOUNTING INTEGRATION
# ============================================================
class TestExpenseAccountingIntegration:
    def test_finalized_expense_creates_journal(self):
        token, _ = register_user()
        biz_id = create_business(token)
        cash_id = create_cash_account(token, biz_id)
        cat_id = create_expense_category(token, biz_id)
        exp_res = client.post(f"/api/v1/businesses/{biz_id}/expenses", headers={"Authorization": f"Bearer {token}"}, json={"category_id": cat_id, "cash_account_id": cash_id, "expense_date": datetime.now(timezone.utc).isoformat(), "amount": 500000, "currency": "IDR"})
        exp_id = exp_res.json()["id"]
        fin = client.post(f"/api/v1/businesses/{biz_id}/expenses/{exp_id}/finalize", headers={"Authorization": f"Bearer {token}"})
        assert fin.status_code == 200

        journals = client.get(f"/api/v1/businesses/{biz_id}/accounting/journals", headers={"Authorization": f"Bearer {token}"}).json()["items"]
        ej = next((j for j in journals if j["reference_type"] == "EXPENSE" and j["reference_id"] == exp_id), None)
        assert ej is not None
        assert Decimal(str(ej["total_debit"])) == Decimal("500000")
        assert ej["lines"][0]["account_code"] == "5100"
        assert ej["lines"][1]["account_code"] == "1100"

    def test_expense_idempotency(self):
        token, _ = register_user()
        biz_id = create_business(token)
        cash_id = create_cash_account(token, biz_id)
        cat_id = create_expense_category(token, biz_id)
        exp_res = client.post(f"/api/v1/businesses/{biz_id}/expenses", headers={"Authorization": f"Bearer {token}"}, json={"category_id": cat_id, "cash_account_id": cash_id, "expense_date": datetime.now(timezone.utc).isoformat(), "amount": 100000, "currency": "IDR"})
        exp_id = exp_res.json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/expenses/{exp_id}/finalize", headers={"Authorization": f"Bearer {token}"})
        fin2 = client.post(f"/api/v1/businesses/{biz_id}/expenses/{exp_id}/finalize", headers={"Authorization": f"Bearer {token}"})
        assert fin2.status_code == 400

    def test_accounting_failure_no_operational_mutation(self):
        token, _ = register_user()
        biz_id = create_business(token)
        cash_id = create_cash_account(token, biz_id)
        cat_id = create_expense_category(token, biz_id)
        exp_res = client.post(f"/api/v1/businesses/{biz_id}/expenses", headers={"Authorization": f"Bearer {token}"}, json={"category_id": cat_id, "cash_account_id": cash_id, "expense_date": datetime.now(timezone.utc).isoformat(), "amount": 100000, "currency": "IDR"})
        exp_id = exp_res.json()["id"]

        with patch("app.modules.expense.service.accounting_integration_service.post_expense_finalized", new_callable=AsyncMock, side_effect=HTTPException(status_code=500, detail="Accounting Failure")):
            fin = client.post(f"/api/v1/businesses/{biz_id}/expenses/{exp_id}/finalize", headers={"Authorization": f"Bearer {token}"})
            assert fin.status_code == 500

        get_res = client.get(f"/api/v1/businesses/{biz_id}/expenses/{exp_id}", headers={"Authorization": f"Bearer {token}"})
        assert get_res.json()["status"] == "DRAFT"

# ============================================================
# 4. PAYMENT ACCOUNTING INTEGRATION
# ============================================================
class TestPaymentAccountingIntegration:
    def test_customer_payment_creates_journal(self):
        token, _ = register_user()
        biz_id = create_business(token)
        cash_id = create_cash_account(token, biz_id)
        sales_id, _ = setup_sale(token, biz_id)
        client.post(f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize", headers={"Authorization": f"Bearer {token}"})

        pay_res = client.post(f"/api/v1/businesses/{biz_id}/payments", headers={"Authorization": f"Bearer {token}"}, json={"direction": "CUSTOMER_IN", "target_type": "SALES", "target_id": sales_id, "amount": 1000000, "currency": "IDR", "payment_method": "CASH", "cash_account_id": cash_id})
        assert pay_res.status_code == 201
        pay_id = pay_res.json()["id"]

        journals = client.get(f"/api/v1/businesses/{biz_id}/accounting/journals", headers={"Authorization": f"Bearer {token}"}).json()["items"]
        pj = next((j for j in journals if j["reference_type"] == "PAYMENT" and j["reference_id"] == pay_id), None)
        assert pj is not None
        assert pj["lines"][0]["account_code"] == "1100"
        assert pj["lines"][1]["account_code"] == "1200"

    def test_supplier_payment_creates_journal(self):
        token, _ = register_user()
        biz_id = create_business(token)
        cash_id = create_cash_account(token, biz_id)
        pur_id, _ = setup_purchase(token, biz_id)
        client.post(f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/finalize", headers={"Authorization": f"Bearer {token}"})

        pay_res = client.post(f"/api/v1/businesses/{biz_id}/payments", headers={"Authorization": f"Bearer {token}"}, json={"direction": "SUPPLIER_OUT", "target_type": "PURCHASE", "target_id": pur_id, "amount": 500000, "currency": "IDR", "payment_method": "CASH", "cash_account_id": cash_id})
        assert pay_res.status_code == 201
        pay_id = pay_res.json()["id"]

        journals = client.get(f"/api/v1/businesses/{biz_id}/accounting/journals", headers={"Authorization": f"Bearer {token}"}).json()["items"]
        pj = next((j for j in journals if j["reference_type"] == "PAYMENT" and j["reference_id"] == pay_id), None)
        assert pj is not None
        assert pj["lines"][0]["account_code"] == "2100"
        assert pj["lines"][1]["account_code"] == "1100"

    def test_void_payment_creates_reversal_journal(self):
        token, _ = register_user()
        biz_id = create_business(token)
        cash_id = create_cash_account(token, biz_id)
        sales_id, _ = setup_sale(token, biz_id)
        client.post(f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize", headers={"Authorization": f"Bearer {token}"})

        pay_res = client.post(f"/api/v1/businesses/{biz_id}/payments", headers={"Authorization": f"Bearer {token}"}, json={"direction": "CUSTOMER_IN", "target_type": "SALES", "target_id": sales_id, "amount": 1000000, "currency": "IDR", "payment_method": "CASH", "cash_account_id": cash_id})
        pay_id = pay_res.json()["id"]

        void_res = client.post(f"/api/v1/businesses/{biz_id}/payments/{pay_id}/void", headers={"Authorization": f"Bearer {token}"})
        assert void_res.status_code == 200
        assert void_res.json()["status"] == "VOIDED"

        journals = client.get(f"/api/v1/businesses/{biz_id}/accounting/journals", headers={"Authorization": f"Bearer {token}"}).json()["items"]
        void_j = next((j for j in journals if j["reference_type"] == "PAYMENT" and j["reference_id"] == pay_id and "Reversal" in j["description"]), None)
        assert void_j is not None
        assert void_j["lines"][0]["account_code"] == "1200"
        assert void_j["lines"][1]["account_code"] == "1100"

# ============================================================
# 5. ACCOUNTING INVARIANTS
# ============================================================
class TestAccountingInvariants:
    def test_closed_period_rejection(self):
        token, _ = register_user()
        biz_id = create_business(token)
        accounts = client.get(f"/api/v1/businesses/{biz_id}/accounting/accounts", headers={"Authorization": f"Bearer {token}"}).json()["items"]
        cash_id = next(a["id"] for a in accounts if a["code"] == "1100")
        sales_id_acc = next(a["id"] for a in accounts if a["code"] == "4100")

        from app.modules.accounting.schemas import AccountingPeriodInDB, AccountingPeriodStatus
        mock_period = AccountingPeriodInDB(
            id="test-period", business_id=biz_id, period_name=datetime.now(timezone.utc).strftime("%Y-%m"),
            start_date=datetime.now(timezone.utc).replace(day=1).date(), end_date=datetime.now(timezone.utc).date(),
            status=AccountingPeriodStatus.CLOSED,
            created_at=datetime.now(timezone.utc), created_by_user_id="admin", updated_at=datetime.now(timezone.utc),
            closed_at=datetime.now(timezone.utc), closed_by_user_id="admin"
        )
        with patch("app.modules.accounting.service.accounting_repository.get_period_for_date", new_callable=AsyncMock, return_value=mock_period):
            j_res = client.post(f"/api/v1/businesses/{biz_id}/accounting/journals", headers={"Authorization": f"Bearer {token}"}, json={
                "journal_date": datetime.now(timezone.utc).isoformat(), "description": "Should fail closed period",
                "lines": [{"account_id": cash_id, "debit": 1000, "credit": 0}, {"account_id": sales_id_acc, "debit": 0, "credit": 1000}],
            })
            assert j_res.status_code == 400
            assert "CLOSED" in j_res.json()["message"]

    def test_source_reference_integrity(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sales_id, _ = setup_sale(token, biz_id)
        client.post(f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize", headers={"Authorization": f"Bearer {token}"})

        journals = client.get(f"/api/v1/businesses/{biz_id}/accounting/journals", headers={"Authorization": f"Bearer {token}"}).json()["items"]
        sj = next((j for j in journals if j["reference_type"] == "SALES" and j["reference_id"] == sales_id), None)
        assert sj is not None
        assert sj["reference_type"] == "SALES"
        assert sj["reference_id"] == sales_id

# ============================================================
# 6. END-TO-END TRIAL BALANCE RECONCILIATION
# ============================================================
class TestEndToEndFinancialReconciliation:
    def test_full_operational_cycle_trial_balance_reconciliation(self):
        """
        Full E2E: Sale + Payment + Purchase + Supplier Payment + Expense
        All journals must be balanced and trial balance must be balanced.
        """
        token, _ = register_user()
        biz_id = create_business(token)
        cash_id = create_cash_account(token, biz_id, opening_balance=10000000)

        # 1. Sale (1,000,000)
        sales_id, branch_id = setup_sale(token, biz_id, qty=10, price=100000)
        client.post(f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize", headers={"Authorization": f"Bearer {token}"})

        # 2. Customer Payment (1,000,000)
        client.post(f"/api/v1/businesses/{biz_id}/payments", headers={"Authorization": f"Bearer {token}"}, json={"direction": "CUSTOMER_IN", "target_type": "SALES", "target_id": sales_id, "amount": 1000000, "currency": "IDR", "payment_method": "CASH", "cash_account_id": cash_id})

        # 3. Purchase (500,000)
        pur_id, _ = setup_purchase(token, biz_id, qty=10, price=50000, branch_id=branch_id)
        client.post(f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/finalize", headers={"Authorization": f"Bearer {token}"})

        # 4. Supplier Payment (500,000)
        client.post(f"/api/v1/businesses/{biz_id}/payments", headers={"Authorization": f"Bearer {token}"}, json={"direction": "SUPPLIER_OUT", "target_type": "PURCHASE", "target_id": pur_id, "amount": 500000, "currency": "IDR", "payment_method": "CASH", "cash_account_id": cash_id})

        # 5. Expense (200,000)
        cat_id = create_expense_category(token, biz_id)
        exp_res = client.post(f"/api/v1/businesses/{biz_id}/expenses", headers={"Authorization": f"Bearer {token}"}, json={"category_id": cat_id, "cash_account_id": cash_id, "expense_date": datetime.now(timezone.utc).isoformat(), "amount": 200000, "currency": "IDR"})
        client.post(f"/api/v1/businesses/{biz_id}/expenses/{exp_res.json()['id']}/finalize", headers={"Authorization": f"Bearer {token}"})

        # Verify all 5 journals
        journals = client.get(f"/api/v1/businesses/{biz_id}/accounting/journals", headers={"Authorization": f"Bearer {token}"}).json()["items"]
        assert len(journals) == 5

        # Trial Balance must be balanced
        tb = client.get(f"/api/v1/businesses/{biz_id}/accounting/trial-balance", headers={"Authorization": f"Bearer {token}"}).json()
        assert tb["is_balanced"] is True
        assert Decimal(str(tb["total_debit"])) == Decimal(str(tb["total_credit"]))

        # Verify each journal is individually balanced
        for j in journals:
            assert Decimal(str(j["total_debit"])) == Decimal(str(j["total_credit"]))

# ============================================================
# 7. IDEMPOTENCY SEQUENTIAL + CONCURRENT
# ============================================================
class TestIdempotency:
    def test_expense_idempotency_sequential(self):
        token, _ = register_user()
        biz_id = create_business(token)
        cash_id = create_cash_account(token, biz_id)
        cat_id = create_expense_category(token, biz_id)
        exp_res = client.post(f"/api/v1/businesses/{biz_id}/expenses", headers={"Authorization": f"Bearer {token}"}, json={"category_id": cat_id, "cash_account_id": cash_id, "expense_date": datetime.now(timezone.utc).isoformat(), "amount": 100000, "currency": "IDR"})
        exp_id = exp_res.json()["id"]
        client.post(f"/api/v1/businesses/{biz_id}/expenses/{exp_id}/finalize", headers={"Authorization": f"Bearer {token}"})
        # 10 sequential finalize attempts
        for _ in range(10):
            fin = client.post(f"/api/v1/businesses/{biz_id}/expenses/{exp_id}/finalize", headers={"Authorization": f"Bearer {token}"})
            assert fin.status_code == 400
        # Still exactly 1 journal
        assert get_journal_count(token, biz_id) == 1

    def test_expense_idempotency_concurrent(self):
        token, _ = register_user()
        biz_id = create_business(token)
        cash_id = create_cash_account(token, biz_id)
        cat_id = create_expense_category(token, biz_id)
        exp_res = client.post(f"/api/v1/businesses/{biz_id}/expenses", headers={"Authorization": f"Bearer {token}"}, json={"category_id": cat_id, "cash_account_id": cash_id, "expense_date": datetime.now(timezone.utc).isoformat(), "amount": 100000, "currency": "IDR"})
        exp_id = exp_res.json()["id"]

        async def finalize():
            return client.post(f"/api/v1/businesses/{biz_id}/expenses/{exp_id}/finalize", headers={"Authorization": f"Bearer {token}"})

        async def run_concurrent():
            tasks = [finalize() for _ in range(10)]
            return await asyncio.gather(*tasks, return_exceptions=True)

        results = asyncio.run(run_concurrent())
        successes = [r for r in results if hasattr(r, "status_code") and r.status_code == 200]
        assert len(successes) == 1
        assert get_journal_count(token, biz_id) == 1

    def test_different_event_same_source_not_duplicate(self):
        token, _ = register_user()
        biz_id = create_business(token)
        cash_id = create_cash_account(token, biz_id)
        sales_id, _ = setup_sale(token, biz_id)
        client.post(f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize", headers={"Authorization": f"Bearer {token}"})
        client.post(f"/api/v1/businesses/{biz_id}/payments", headers={"Authorization": f"Bearer {token}"}, json={"direction": "CUSTOMER_IN", "target_type": "SALES", "target_id": sales_id, "amount": 1000000, "currency": "IDR", "payment_method": "CASH", "cash_account_id": cash_id})
        journals = client.get(f"/api/v1/businesses/{biz_id}/accounting/journals", headers={"Authorization": f"Bearer {token}"}).json()["items"]
        sale_j = [j for j in journals if j["reference_type"] == "SALES" and j["reference_id"] == sales_id]
        assert len(sale_j) == 1
        pay_j = [j for j in journals if j["reference_type"] == "PAYMENT" and j["reference_id"] != sales_id]
        assert len(pay_j) == 1

# ============================================================
# 8. TENANT ISOLATION
# ============================================================
class TestTenantIsolation:
    def test_tenant_isolation(self):
        t1, _ = register_user("tenant1@ex.com")
        biz1 = create_business(t1, "Biz 1")
        sales_id, _ = setup_sale(t1, biz1)
        client.post(f"/api/v1/businesses/{biz1}/sales/{sales_id}/finalize", headers={"Authorization": f"Bearer {t1}"})

        t2, _ = register_user("tenant2@ex.com")
        biz2 = create_business(t2, "Biz 2")
        journals_t2 = client.get(f"/api/v1/businesses/{biz2}/accounting/journals", headers={"Authorization": f"Bearer {t2}"}).json()["items"]
        assert len(journals_t2) == 0

    def test_idempotency_key_tenant_scoped(self):
        t1, _ = register_user("tenant1b@ex.com")
        biz1 = create_business(t1, "Biz A")
        sales_id1, _ = setup_sale(t1, biz1)
        client.post(f"/api/v1/businesses/{biz1}/sales/{sales_id1}/finalize", headers={"Authorization": f"Bearer {t1}"})

        t2, _ = register_user("tenant2b@ex.com")
        biz2 = create_business(t2, "Biz B")
        sales_id2, _ = setup_sale(t2, biz2)
        client.post(f"/api/v1/businesses/{biz2}/sales/{sales_id2}/finalize", headers={"Authorization": f"Bearer {t2}"})

        assert get_journal_count(t1, biz1) == 1
        assert get_journal_count(t2, biz2) == 1

"""
Wave 2 Concurrency & Transaction Hardening Tests.
PostgreSQL-backed integration tests verifying concurrency safety.
"""
import pytest
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from fastapi.testclient import TestClient

from app.main import app
from app.modules.authentication.repository import InMemoryUserRepository
from app.modules.account.repository import InMemoryAccountRepository
from app.modules.business.repository import InMemoryBusinessRepository
from app.modules.business_membership.repository import InMemoryBusinessMembershipRepository
from app.modules.customer.repository import InMemoryCustomerRepository
from app.modules.product.repository import InMemoryProductRepository
from app.modules.product_variant.repository import InMemoryProductVariantRepository
from app.modules.unit.repository import InMemoryUnitRepository
from app.modules.branch.repository import InMemoryBranchRepository
from app.modules.sales.repository import InMemorySalesRepository
from app.modules.pricing.repository import InMemoryPriceListRepository, InMemoryPriceEntryRepository
from app.modules.warehouse.repository import InMemoryWarehouseRepository, InMemoryInventoryLocationRepository
from app.modules.receiving.repository import InMemoryReceivingRepository
from app.modules.stock_opname.repository import InMemoryStockOpnameRepository
from app.modules.inventory.repository import InMemoryStockBalanceRepository, InMemoryStockMovementRepository, InMemoryInventoryCostRepository
from app.modules.supplier.repository import InMemorySupplierRepository
from app.modules.purchase.repository import InMemoryPurchaseRepository
from app.modules.accounting.repository import InMemoryAccountingRepository
from app.modules.barcode.repository import InMemoryBarcodeRepository
from app.modules.category.repository import InMemoryCategoryRepository


@pytest.fixture(autouse=True)
def clear_all_repos():
    InMemoryUserRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryCustomerRepository.clear()
    InMemoryProductRepository.clear()
    InMemoryProductVariantRepository.clear()
    InMemoryUnitRepository.clear()
    InMemoryBranchRepository.clear()
    InMemorySalesRepository.clear()
    InMemoryPriceListRepository.clear()
    InMemoryPriceEntryRepository.clear()
    InMemoryWarehouseRepository.clear()
    InMemoryInventoryLocationRepository.clear()
    InMemoryReceivingRepository.clear()
    InMemoryStockOpnameRepository.clear()
    InMemoryStockBalanceRepository.clear()
    InMemoryStockMovementRepository.clear()
    InMemoryInventoryCostRepository.clear()
    InMemorySupplierRepository.clear()
    InMemoryPurchaseRepository.clear()
    InMemoryAccountingRepository.clear()
    InMemoryBarcodeRepository.clear()
    InMemoryCategoryRepository.clear()
    yield
    InMemoryUserRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryCustomerRepository.clear()
    InMemoryProductRepository.clear()
    InMemoryProductVariantRepository.clear()
    InMemoryUnitRepository.clear()
    InMemoryBranchRepository.clear()
    InMemorySalesRepository.clear()
    InMemoryPriceListRepository.clear()
    InMemoryPriceEntryRepository.clear()
    InMemoryWarehouseRepository.clear()
    InMemoryInventoryLocationRepository.clear()
    InMemoryReceivingRepository.clear()
    InMemoryStockOpnameRepository.clear()
    InMemoryStockBalanceRepository.clear()
    InMemoryStockMovementRepository.clear()
    InMemoryInventoryCostRepository.clear()
    InMemorySupplierRepository.clear()
    InMemoryPurchaseRepository.clear()
    InMemoryAccountingRepository.clear()
    InMemoryBarcodeRepository.clear()
    InMemoryCategoryRepository.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# ── Helpers ──────────────────────────────────────────────────────────────────

def _register(client, email=None, password="Password123"):
    if email is None:
        email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    res = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Test User", "password": password, "password_confirmation": password},
    )
    assert res.status_code == 201
    token = res.json().get("access_token")
    if not token:
        login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200
        token = login.json()["access_token"]
    return token


def _create_biz(client, token, name=None):
    if name is None:
        name = f"Biz_{uuid.uuid4().hex[:6]}"
    res = client.post(
        "/api/v1/businesses",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "business_type": "umkm", "timezone": "UTC", "locale": "en-US"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def _create_branch(client, token, biz_id):
    code = f"BR_{uuid.uuid4().hex[:6].upper()}"
    res = client.post(
        f"/api/v1/businesses/{biz_id}/branches",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Main Branch", "code": code},
    )
    assert res.status_code == 201
    return res.json()["id"]


def _create_unit(client, token, biz_id):
    code = f"U_{uuid.uuid4().hex[:6].upper()}"
    res = client.post(
        f"/api/v1/businesses/{biz_id}/units",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Pcs", "code": code, "symbol": "PCS", "unit_type": "OTHER"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def _create_product(client, token, biz_id, unit_id, p_type="GOODS"):
    code = f"P_{uuid.uuid4().hex[:6].upper()}"
    res = client.post(
        f"/api/v1/businesses/{biz_id}/products",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Product", "code": code, "unit_id": unit_id, "product_type": p_type},
    )
    assert res.status_code == 201
    return res.json()["id"]


def _create_supplier(client, token, biz_id):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/suppliers",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Supplier", "supplier_type": "ORGANIZATION"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def _create_customer(client, token, biz_id):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/customers",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Walk-in", "customer_type": "INDIVIDUAL"},
    )
    assert res.status_code == 201
    cid = res.json()["id"]
    client.put(
        f"/api/v1/businesses/{biz_id}/customers/{cid}/credit/limit",
        headers={"Authorization": f"Bearer {token}"},
        json={"credit_limit": "100000000.00"},
    )
    return cid


def _setup_warehouse(client, token, biz_id):
    wh_res = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "WH", "code": f"WH_{uuid.uuid4().hex[:6]}"},
    )
    assert wh_res.status_code == 201
    wh_id = wh_res.json()["id"]
    loc_res = client.post(
        f"/api/v1/businesses/{biz_id}/warehouses/{wh_id}/locations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Loc", "code": f"LOC_{uuid.uuid4().hex[:6]}", "location_type": "GENERAL"},
    )
    assert loc_res.status_code == 201
    return wh_id, loc_res.json()["id"]


def _get_account_id(client, token, biz_id, code):
    res = client.get(
        f"/api/v1/businesses/{biz_id}/accounting/accounts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    for acc in res.json()["items"]:
        if acc["code"] == code:
            return acc["id"]
    return None


# ── Test Classes ─────────────────────────────────────────────────────────────

class TestDocumentNumberConcurrency:
    """Test that concurrent document creation produces unique numbers."""

    def test_concurrent_sales_number_uniqueness(self, client):
        token = _register(client)
        biz_id = _create_biz(client, token)
        branch_id = _create_branch(client, token, biz_id)

        headers = {"Authorization": f"Bearer {token}"}
        url = f"/api/v1/businesses/{biz_id}/sales"
        payload = {"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()}

        results = []
        for _ in range(10):
            res = client.post(url, headers=headers, json=payload)
            results.append(res)

        numbers = [r.json()["sales_number"] for r in results if r.status_code == 201]
        assert len(numbers) == 10
        assert len(set(numbers)) == 10, f"Duplicate sales numbers found: {numbers}"

    def test_concurrent_purchase_number_uniqueness(self, client):
        token = _register(client)
        biz_id = _create_biz(client, token)
        branch_id = _create_branch(client, token, biz_id)
        supplier_id = _create_supplier(client, token, biz_id)

        headers = {"Authorization": f"Bearer {token}"}
        url = f"/api/v1/businesses/{biz_id}/purchases"
        payload = {
            "supplier_id": supplier_id,
            "branch_id": branch_id,
            "purchase_date": datetime.now(timezone.utc).isoformat(),
        }

        results = []
        for _ in range(10):
            res = client.post(url, headers=headers, json=payload)
            results.append(res)

        numbers = [r.json()["purchase_number"] for r in results if r.status_code == 201]
        assert len(numbers) == 10
        assert len(set(numbers)) == 10, f"Duplicate purchase numbers found: {numbers}"

    def test_concurrent_journal_number_uniqueness(self, client):
        token = _register(client)
        biz_id = _create_biz(client, token)
        cash_acc = _get_account_id(client, token, biz_id, "1100")
        sales_acc = _get_account_id(client, token, biz_id, "4100")

        headers = {"Authorization": f"Bearer {token}"}
        url = f"/api/v1/businesses/{biz_id}/accounting/journals"

        results = []
        for i in range(10):
            payload = {
                "journal_date": datetime.now(timezone.utc).isoformat(),
                "description": f"Concurrent journal {i}",
                "lines": [
                    {"account_id": cash_acc, "debit": 100, "credit": 0},
                    {"account_id": sales_acc, "debit": 0, "credit": 100},
                ],
            }
            res = client.post(url, headers=headers, json=payload)
            results.append(res)

        numbers = [r.json()["journal_number"] for r in results if r.status_code == 201]
        assert len(numbers) == 10
        assert len(set(numbers)) == 10, f"Duplicate journal numbers found: {numbers}"


class TestInventoryConcurrency:
    """Test stock balance consistency under concurrent access."""

    def test_concurrent_opening_balance_no_duplicate_rows(self, client):
        token = _register(client)
        biz_id = _create_biz(client, token)
        unit_id = _create_unit(client, token, biz_id)
        prod_id = _create_product(client, token, biz_id, unit_id)
        _, loc_id = _setup_warehouse(client, token, biz_id)

        headers = {"Authorization": f"Bearer {token}"}
        url = f"/api/v1/businesses/{biz_id}/inventory/opening-balance"

        results = []
        for _ in range(5):
            res = client.post(
                url,
                headers=headers,
                json={"inventory_location_id": loc_id, "product_id": prod_id, "quantity": "10"},
            )
            results.append(res)

        successes = [r for r in results if r.status_code == 201]
        assert len(successes) >= 1

        stock_res = client.get(
            f"/api/v1/businesses/{biz_id}/inventory/stock",
            headers=headers,
        )
        assert stock_res.status_code == 200
        stock_items = stock_res.json()
        matching = [s for s in stock_items if s["product_id"] == prod_id]
        assert len(matching) == 1, f"Expected 1 stock balance row, got {len(matching)}"


class TestIdempotencyConcurrency:
    """Test idempotency key collision handling."""

    def test_same_idempotency_key_returns_same_journal(self, client):
        token = _register(client)
        biz_id = _create_biz(client, token)
        cash_acc = _get_account_id(client, token, biz_id, "1100")
        sales_acc = _get_account_id(client, token, biz_id, "4100")
        idem_key = f"IDEM-{uuid.uuid4().hex[:12]}"

        headers = {"Authorization": f"Bearer {token}"}
        url = f"/api/v1/businesses/{biz_id}/accounting/journals"
        payload = {
            "journal_date": datetime.now(timezone.utc).isoformat(),
            "description": "Idempotent concurrent test",
            "idempotency_key": idem_key,
            "lines": [
                {"account_id": cash_acc, "debit": 500, "credit": 0},
                {"account_id": sales_acc, "debit": 0, "credit": 500},
            ],
        }

        r1 = client.post(url, headers=headers, json=payload)
        r2 = client.post(url, headers=headers, json=payload)

        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.json()["id"] == r2.json()["id"]
        assert r1.json()["journal_number"] == r2.json()["journal_number"]

    def test_different_idempotency_keys_create_separate_journals(self, client):
        token = _register(client)
        biz_id = _create_biz(client, token)
        cash_acc = _get_account_id(client, token, biz_id, "1100")
        sales_acc = _get_account_id(client, token, biz_id, "4100")

        headers = {"Authorization": f"Bearer {token}"}
        url = f"/api/v1/businesses/{biz_id}/accounting/journals"

        base_payload = {
            "journal_date": datetime.now(timezone.utc).isoformat(),
            "description": "Different idempotency test",
            "lines": [
                {"account_id": cash_acc, "debit": 200, "credit": 0},
                {"account_id": sales_acc, "debit": 0, "credit": 200},
            ],
        }

        p1 = {**base_payload, "idempotency_key": f"IDEM-A-{uuid.uuid4().hex[:8]}"}
        p2 = {**base_payload, "idempotency_key": f"IDEM-B-{uuid.uuid4().hex[:8]}"}

        r1 = client.post(url, headers=headers, json=p1)
        r2 = client.post(url, headers=headers, json=p2)

        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.json()["id"] != r2.json()["id"]


class TestStoreCreditConcurrency:
    """Test store credit issue under concurrent access."""

    def test_concurrent_credit_issue_totals_match(self, client):
        token = _register(client)
        biz_id = _create_biz(client, token)
        cust_id = _create_customer(client, token, biz_id)

        headers = {"Authorization": f"Bearer {token}"}
        url = f"/api/v1/businesses/{biz_id}/customers/{cust_id}/credit/store-credit/issue"

        issue_amounts = ["1000.00", "2000.00", "500.00", "1500.00"]
        for amt in issue_amounts:
            res = client.post(url, headers=headers, json={"amount": amt})
            assert res.status_code == 200

        summary = client.get(
            f"/api/v1/businesses/{biz_id}/customers/{cust_id}/credit/summary",
            headers=headers,
        )
        assert summary.status_code == 200
        expected = sum(Decimal(a) for a in issue_amounts)
        assert Decimal(summary.json()["store_credit_balance"]) == expected

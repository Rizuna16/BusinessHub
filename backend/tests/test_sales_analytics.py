import pytest
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
from app.modules.unit.repository import InMemoryUnitRepository
from app.modules.branch.repository import InMemoryBranchRepository
from app.modules.category.repository import InMemoryCategoryRepository
from app.modules.sales.repository import InMemorySalesRepository
from app.modules.sales_return.repository import InMemorySalesReturnRepository
from app.modules.pricing.repository import InMemoryPriceListRepository, InMemoryPriceEntryRepository
from app.modules.warehouse.repository import InMemoryWarehouseRepository, InMemoryInventoryLocationRepository
from app.modules.inventory.repository import (
    InMemoryStockBalanceRepository,
    InMemoryStockMovementRepository,
    InMemoryInventoryCostRepository,
)


@pytest.fixture(autouse=True)
def clear_all_repos():
    for repo in [
        InMemoryUserRepository, InMemoryAccountRepository, InMemoryBusinessRepository,
        InMemoryBusinessMembershipRepository, InMemoryCustomerRepository,
        InMemoryProductRepository, InMemoryUnitRepository, InMemoryBranchRepository,
        InMemoryCategoryRepository, InMemorySalesRepository, InMemorySalesReturnRepository,
        InMemoryPriceListRepository, InMemoryPriceEntryRepository,
        InMemoryWarehouseRepository, InMemoryInventoryLocationRepository,
        InMemoryStockBalanceRepository, InMemoryStockMovementRepository,
        InMemoryInventoryCostRepository,
    ]:
        repo.clear()
    yield
    for repo in [
        InMemoryUserRepository, InMemoryAccountRepository, InMemoryBusinessRepository,
        InMemoryBusinessMembershipRepository, InMemoryCustomerRepository,
        InMemoryProductRepository, InMemoryUnitRepository, InMemoryBranchRepository,
        InMemoryCategoryRepository, InMemorySalesRepository, InMemorySalesReturnRepository,
        InMemoryPriceListRepository, InMemoryPriceEntryRepository,
        InMemoryWarehouseRepository, InMemoryInventoryLocationRepository,
        InMemoryStockBalanceRepository, InMemoryStockMovementRepository,
        InMemoryInventoryCostRepository,
    ]:
        repo.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────

def _reg(c, email="owner@example.com"):
    r = c.post("/api/v1/auth/register", json={"email": email, "full_name": "Owner", "password": "Password123", "password_confirmation": "Password123"})
    assert r.status_code == 201
    tok = r.json().get("access_token")
    if not tok:
        r2 = c.post("/api/v1/auth/login", json={"email": email, "password": "Password123"})
        tok = r2.json()["access_token"]
    return tok


def _biz(c, tok, name="Biz"):
    r = c.post("/api/v1/businesses", headers={"Authorization": f"Bearer {tok}"}, json={"name": name, "business_type": "umkm", "timezone": "UTC", "locale": "en-US"})
    assert r.status_code == 201
    return r.json()["id"]


def _unit(c, tok, biz):
    r = c.post(f"/api/v1/businesses/{biz}/units", headers={"Authorization": f"Bearer {tok}"}, json={"name": "Pcs", "code": "PCS", "symbol": "pcs", "unit_type": "OTHER"})
    assert r.status_code == 201
    return r.json()["id"]


_branch_counter = 0

def _branch(c, tok, biz, code=None):
    global _branch_counter
    _branch_counter += 1
    if code is None:
        code = f"BR{_branch_counter}"
    r = c.post(f"/api/v1/businesses/{biz}/branches", headers={"Authorization": f"Bearer {tok}"}, json={"name": f"Branch {_branch_counter}", "code": code})
    assert r.status_code == 201
    return r.json()["id"]


def _cust(c, tok, biz, name="C"):
    r = c.post(f"/api/v1/businesses/{biz}/customers", headers={"Authorization": f"Bearer {tok}"}, json={"name": name, "customer_type": "INDIVIDUAL"})
    assert r.status_code == 201
    return r.json()["id"]


def _cat(c, tok, biz, name="C1", code="C1"):
    r = c.post(f"/api/v1/businesses/{biz}/categories", headers={"Authorization": f"Bearer {tok}"}, json={"name": name, "code": code})
    assert r.status_code == 201
    return r.json()["id"]


def _prod(c, tok, biz, unit_id, name="P", code="P1", cat_id=None):
    p = {"name": name, "code": code, "unit_id": unit_id, "product_type": "GOODS"}
    if cat_id:
        p["category_id"] = cat_id
    r = c.post(f"/api/v1/businesses/{biz}/products", headers={"Authorization": f"Bearer {tok}"}, json=p)
    assert r.status_code == 201
    return r.json()["id"]


def _plist(c, tok, biz, code="PL"):
    r = c.post(f"/api/v1/businesses/{biz}/price-lists", headers={"Authorization": f"Bearer {tok}"}, json={"name": "P", "code": code, "currency": "IDR"})
    assert r.status_code == 201
    return r.json()["id"]


def _pentry(c, tok, biz, pl_id, prod_id, amt="100000"):
    now = datetime.now(timezone.utc).isoformat()
    r = c.post(f"/api/v1/businesses/{biz}/price-lists/{pl_id}/prices", headers={"Authorization": f"Bearer {tok}"}, json={"product_id": prod_id, "amount": amt, "effective_from": now})
    assert r.status_code == 201


_stock_counter = 0

def _stock(c, tok, biz, prod_id):
    global _stock_counter
    _stock_counter += 1
    wh_code = f"WH{_stock_counter}"
    loc_code = f"L{_stock_counter}"
    wh = c.post(f"/api/v1/businesses/{biz}/warehouses", headers={"Authorization": f"Bearer {tok}"}, json={"name": f"Warehouse {_stock_counter}", "code": wh_code})
    assert wh.status_code == 201
    loc = c.post(f"/api/v1/businesses/{biz}/warehouses/{wh.json()['id']}/locations", headers={"Authorization": f"Bearer {tok}"}, json={"name": f"Loc {_stock_counter}", "code": loc_code, "location_type": "GENERAL"})
    assert loc.status_code == 201
    lid = loc.json()["id"]
    c.post(f"/api/v1/businesses/{biz}/inventory/opening-balance", headers={"Authorization": f"Bearer {tok}"}, json={"inventory_location_id": lid, "product_id": prod_id, "quantity": "10000"})
    return lid


def _sale(c, tok, biz, branch_id, prod_id, s_date, amt="200000", cust_id=None, qty="2"):
    p = {"branch_id": branch_id, "sales_date": s_date}
    if cust_id:
        p["customer_id"] = cust_id
    s = c.post(f"/api/v1/businesses/{biz}/sales", headers={"Authorization": f"Bearer {tok}"}, json=p)
    assert s.status_code == 201
    sid = s.json()["id"]
    c.post(f"/api/v1/businesses/{biz}/sales/{sid}/lines", headers={"Authorization": f"Bearer {tok}"}, json={"product_id": prod_id, "quantity": qty, "unit_price": amt})
    lid = _stock(c, tok, biz, prod_id)
    c.post(f"/api/v1/businesses/{biz}/sales/{sid}/finalize?inventory_location_id={lid}", headers={"Authorization": f"Bearer {tok}"})
    return sid


def _ret(c, tok, biz, sale_id, line_id, qty="1", loc_id="x"):
    """Create a finalized sales return. return_date is auto-set to sales.sales_date."""
    r = c.post(f"/api/v1/businesses/{biz}/sales-returns", headers={"Authorization": f"Bearer {tok}"}, json={"sales_id": sale_id, "inventory_location_id": loc_id})
    assert r.status_code == 201
    rid = r.json()["id"]
    c.post(f"/api/v1/businesses/{biz}/sales-returns/{rid}/lines", headers={"Authorization": f"Bearer {tok}"}, json={"sales_line_id": line_id, "quantity": qty})
    c.post(f"/api/v1/businesses/{biz}/sales-returns/{rid}/finalize", headers={"Authorization": f"Bearer {tok}"})
    return rid


def _s(c, tok, biz, df="2026-09-01T00:00:00Z", dt="2026-09-30T23:59:59Z", **kw):
    params = f"?date_from={df}&date_to={dt}"
    for k, v in kw.items():
        if v is not None:
            params += f"&{k}={v}"
    return c.get(f"/api/v1/businesses/{biz}/sales/analytics/summary{params}", headers={"Authorization": f"Bearer {tok}"})


def _cat_resp(c, tok, biz, df="2026-09-01T00:00:00Z", dt="2026-09-30T23:59:59Z", **kw):
    params = f"?date_from={df}&date_to={dt}"
    for k, v in kw.items():
        if v is not None:
            params += f"&{k}={v}"
    return c.get(f"/api/v1/businesses/{biz}/sales/analytics/by-category{params}", headers={"Authorization": f"Bearer {tok}"})


def _cust_resp(c, tok, biz, df="2026-09-01T00:00:00Z", dt="2026-09-30T23:59:59Z", **kw):
    params = f"?date_from={df}&date_to={dt}"
    for k, v in kw.items():
        if v is not None:
            params += f"&{k}={v}"
    return c.get(f"/api/v1/businesses/{biz}/sales/analytics/by-customer{params}", headers={"Authorization": f"Bearer {tok}"})


# ──────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────

class TestSalesAnalytics:

    def test_finalized_sale_included(self, client):
        t = _reg(client); b = _biz(client, t); u = _unit(client, t, b); br = _branch(client, t, b)
        c1 = _cat(client, t, b); p = _prod(client, t, b, u, cat_id=c1)
        pl = _plist(client, t, b); _pentry(client, t, b, pl, p)
        _sale(client, t, b, br, p, "2026-09-15T10:00:00Z", amt="100000")
        r = _s(client, t, b)
        assert r.status_code == 200
        d = r.json()
        assert Decimal(str(d["gross_sales"])) > 0
        assert d["transaction_count"] == 1

    def test_draft_excluded(self, client):
        t = _reg(client); b = _biz(client, t); u = _unit(client, t, b); br = _branch(client, t, b)
        p = _prod(client, t, b, u); pl = _plist(client, t, b); _pentry(client, t, b, pl, p)
        s = client.post(f"/api/v1/businesses/{b}/sales", headers={"Authorization": f"Bearer {t}"}, json={"branch_id": br, "sales_date": "2026-09-15T10:00:00Z"}).json()
        client.post(f"/api/v1/businesses/{b}/sales/{s['id']}/lines", headers={"Authorization": f"Bearer {t}"}, json={"product_id": p, "quantity": "1", "unit_price": "100000"})
        assert _s(client, t, b).json()["transaction_count"] == 0

    def test_cancelled_excluded(self, client):
        t = _reg(client); b = _biz(client, t); u = _unit(client, t, b); br = _branch(client, t, b)
        p = _prod(client, t, b, u); pl = _plist(client, t, b); _pentry(client, t, b, pl, p)
        s = client.post(f"/api/v1/businesses/{b}/sales", headers={"Authorization": f"Bearer {t}"}, json={"branch_id": br, "sales_date": "2026-09-15T10:00:00Z"}).json()
        client.post(f"/api/v1/businesses/{b}/sales/{s['id']}/lines", headers={"Authorization": f"Bearer {t}"}, json={"product_id": p, "quantity": "1", "unit_price": "100000"})
        client.post(f"/api/v1/businesses/{b}/sales/{s['id']}/cancel", headers={"Authorization": f"Bearer {t}"})
        assert _s(client, t, b).json()["transaction_count"] == 0

    def test_multiple_finalized_sales(self, client):
        t = _reg(client); b = _biz(client, t); u = _unit(client, t, b); br = _branch(client, t, b)
        c1 = _cat(client, t, b); p = _prod(client, t, b, u, cat_id=c1)
        pl = _plist(client, t, b); _pentry(client, t, b, pl, p)
        _sale(client, t, b, br, p, "2026-09-10T10:00:00Z", amt="100000")
        _sale(client, t, b, br, p, "2026-09-20T10:00:00Z", amt="200000")
        d = _s(client, t, b).json()
        assert d["transaction_count"] == 2
        assert Decimal(str(d["average_transaction_value"])) == Decimal(str(d["gross_sales"])) / 2

    def test_zero_sales(self, client):
        t = _reg(client); b = _biz(client, t)
        d = _s(client, t, b).json()
        assert Decimal(str(d["gross_sales"])) == 0
        assert d["transaction_count"] == 0
        assert Decimal(str(d["average_transaction_value"])) == 0

    def test_gross_sales_formula(self, client):
        t = _reg(client); b = _biz(client, t); u = _unit(client, t, b); br = _branch(client, t, b)
        c1 = _cat(client, t, b); p = _prod(client, t, b, u, cat_id=c1)
        pl = _plist(client, t, b); _pentry(client, t, b, pl, p)
        _sale(client, t, b, br, p, "2026-09-10T10:00:00Z", amt="150000", qty="3")
        _sale(client, t, b, br, p, "2026-09-20T10:00:00Z", amt="250000", qty="1")
        d = _s(client, t, b).json()
        gross = Decimal(str(d["gross_sales"]))
        assert gross > 0
        assert Decimal(str(d["net_sales"])) == gross

    def test_transaction_count(self, client):
        t = _reg(client); b = _biz(client, t); u = _unit(client, t, b); br = _branch(client, t, b)
        p = _prod(client, t, b, u); pl = _plist(client, t, b); _pentry(client, t, b, pl, p)
        for d in ["2026-09-10T10:00:00Z", "2026-09-15T10:00:00Z", "2026-09-20T10:00:00Z"]:
            _sale(client, t, b, br, p, d)
        assert _s(client, t, b).json()["transaction_count"] == 3

    def test_average_transaction_value(self, client):
        t = _reg(client); b = _biz(client, t); u = _unit(client, t, b); br = _branch(client, t, b)
        p = _prod(client, t, b, u); pl = _plist(client, t, b); _pentry(client, t, b, pl, p)
        _sale(client, t, b, br, p, "2026-09-10T10:00:00Z", amt="300000")
        _sale(client, t, b, br, p, "2026-09-20T10:00:00Z", amt="100000")
        d = _s(client, t, b).json()
        assert Decimal(str(d["average_transaction_value"])) == Decimal(str(d["gross_sales"])) / 2

    def test_date_from_boundary(self, client):
        t = _reg(client); b = _biz(client, t); u = _unit(client, t, b); br = _branch(client, t, b)
        p = _prod(client, t, b, u); pl = _plist(client, t, b); _pentry(client, t, b, pl, p)
        _sale(client, t, b, br, p, "2026-09-01T00:00:00Z")
        assert _s(client, t, b).json()["transaction_count"] == 1

    def test_date_to_boundary(self, client):
        t = _reg(client); b = _biz(client, t); u = _unit(client, t, b); br = _branch(client, t, b)
        p = _prod(client, t, b, u); pl = _plist(client, t, b); _pentry(client, t, b, pl, p)
        _sale(client, t, b, br, p, "2026-09-30T23:59:59Z")
        assert _s(client, t, b).json()["transaction_count"] == 1

    def test_before_range_excluded(self, client):
        t = _reg(client); b = _biz(client, t); u = _unit(client, t, b); br = _branch(client, t, b)
        p = _prod(client, t, b, u); pl = _plist(client, t, b); _pentry(client, t, b, pl, p)
        _sale(client, t, b, br, p, "2026-08-31T23:59:59Z")
        assert _s(client, t, b).json()["transaction_count"] == 0

    def test_after_range_excluded(self, client):
        t = _reg(client); b = _biz(client, t); u = _unit(client, t, b); br = _branch(client, t, b)
        p = _prod(client, t, b, u); pl = _plist(client, t, b); _pentry(client, t, b, pl, p)
        _sale(client, t, b, br, p, "2026-10-01T00:00:00Z")
        assert _s(client, t, b).json()["transaction_count"] == 0

    def test_reversed_range_422(self, client):
        t = _reg(client); b = _biz(client, t)
        r = client.get(f"/api/v1/businesses/{b}/sales/analytics/summary?date_from=2026-09-30T00:00:00Z&date_to=2026-09-01T00:00:00Z", headers={"Authorization": f"Bearer {t}"})
        assert r.status_code in (400, 422)

    def test_incomplete_dates_422(self, client):
        t = _reg(client); b = _biz(client, t)
        r = client.get(f"/api/v1/businesses/{b}/sales/analytics/summary?date_from=2026-09-01T00:00:00Z", headers={"Authorization": f"Bearer {t}"})
        assert r.status_code == 422

    def test_return_included(self, client):
        t = _reg(client); b = _biz(client, t); u = _unit(client, t, b); br = _branch(client, t, b)
        c1 = _cat(client, t, b); p = _prod(client, t, b, u, cat_id=c1)
        pl = _plist(client, t, b); _pentry(client, t, b, pl, p)
        sid = _sale(client, t, b, br, p, "2026-09-10T10:00:00Z", amt="100000")
        sale_detail = client.get(f"/api/v1/businesses/{b}/sales/{sid}", headers={"Authorization": f"Bearer {t}"}).json()
        line_id = sale_detail["lines"][0]["id"]
        locs = client.get(f"/api/v1/businesses/{b}/warehouses", headers={"Authorization": f"Bearer {t}"}).json()
        loc_id = client.get(f"/api/v1/businesses/{b}/warehouses/{locs[0]['id']}/locations", headers={"Authorization": f"Bearer {t}"}).json()[0]["id"]
        _ret(client, t, b, sid, line_id, loc_id=loc_id)
        d = _s(client, t, b).json()
        assert Decimal(str(d["sales_returns"])) > 0
        assert Decimal(str(d["net_sales"])) == Decimal(str(d["gross_sales"])) - Decimal(str(d["sales_returns"]))

    def test_draft_return_excluded(self, client):
        t = _reg(client); b = _biz(client, t); u = _unit(client, t, b); br = _branch(client, t, b)
        p = _prod(client, t, b, u); pl = _plist(client, t, b); _pentry(client, t, b, pl, p)
        sid = _sale(client, t, b, br, p, "2026-09-10T10:00:00Z", amt="100000")
        client.post(f"/api/v1/businesses/{b}/sales-returns", headers={"Authorization": f"Bearer {t}"}, json={"sales_id": sid, "inventory_location_id": "x", "return_date": "2026-09-15T10:00:00Z"})
        assert Decimal(str(_s(client, t, b).json()["sales_returns"])) == 0

    def test_category_aggregation(self, client):
        t = _reg(client); b = _biz(client, t); u = _unit(client, t, b); br = _branch(client, t, b)
        c1 = _cat(client, t, b, name="A", code="A"); c2 = _cat(client, t, b, name="B", code="B")
        p1 = _prod(client, t, b, u, name="P1", code="P1", cat_id=c1)
        p2 = _prod(client, t, b, u, name="P2", code="P2", cat_id=c2)
        pl = _plist(client, t, b); _pentry(client, t, b, pl, p1); _pentry(client, t, b, pl, p2)
        _sale(client, t, b, br, p1, "2026-09-10T10:00:00Z", amt="100000")
        _sale(client, t, b, br, p2, "2026-09-15T10:00:00Z", amt="200000")
        r = _cat_resp(client, t, b)
        assert r.status_code == 200
        cats = r.json()["categories"]
        assert len(cats) == 2
        assert Decimal(str(cats[0]["net_sales"])) >= Decimal(str(cats[1]["net_sales"]))

    def test_category_filter(self, client):
        t = _reg(client); b = _biz(client, t); u = _unit(client, t, b); br = _branch(client, t, b)
        c1 = _cat(client, t, b, name="A", code="A"); c2 = _cat(client, t, b, name="B", code="B")
        p1 = _prod(client, t, b, u, name="P1", code="P1", cat_id=c1)
        p2 = _prod(client, t, b, u, name="P2", code="P2", cat_id=c2)
        pl = _plist(client, t, b); _pentry(client, t, b, pl, p1); _pentry(client, t, b, pl, p2)
        _sale(client, t, b, br, p1, "2026-09-10T10:00:00Z")
        _sale(client, t, b, br, p2, "2026-09-15T10:00:00Z")
        d = _s(client, t, b, category_id=c1).json()
        assert d["transaction_count"] == 1

    def test_foreign_category_404(self, client):
        t1 = _reg(client, "u1@e.com"); b1 = _biz(client, t1, "B1")
        t2 = _reg(client, "u2@e.com"); b2 = _biz(client, t2, "B2"); c2 = _cat(client, t2, b2)
        r = client.get(f"/api/v1/businesses/{b1}/sales/analytics/summary?date_from=2026-09-01T00:00:00Z&date_to=2026-09-30T23:59:59Z&category_id={c2}", headers={"Authorization": f"Bearer {t1}"})
        assert r.status_code == 404

    def test_category_reconciliation(self, client):
        t = _reg(client); b = _biz(client, t); u = _unit(client, t, b); br = _branch(client, t, b)
        c1 = _cat(client, t, b, name="A", code="A"); c2 = _cat(client, t, b, name="B", code="B")
        p1 = _prod(client, t, b, u, name="P1", code="P1", cat_id=c1)
        p2 = _prod(client, t, b, u, name="P2", code="P2", cat_id=c2)
        pl = _plist(client, t, b); _pentry(client, t, b, pl, p1); _pentry(client, t, b, pl, p2)
        _sale(client, t, b, br, p1, "2026-09-10T10:00:00Z", amt="100000")
        _sale(client, t, b, br, p2, "2026-09-15T10:00:00Z", amt="200000")
        sm = _s(client, t, b).json(); cm = _cat_resp(client, t, b).json()
        cat_net = sum(Decimal(str(c["net_sales"])) for c in cm["categories"])
        assert cat_net == Decimal(str(sm["net_sales"]))

    def test_customer_aggregation(self, client):
        t = _reg(client); b = _biz(client, t); u = _unit(client, t, b); br = _branch(client, t, b)
        cu1 = _cust(client, t, b, name="A"); cu2 = _cust(client, t, b, name="B")
        p = _prod(client, t, b, u); pl = _plist(client, t, b); _pentry(client, t, b, pl, p)
        _sale(client, t, b, br, p, "2026-09-10T10:00:00Z", amt="100000", cust_id=cu1)
        _sale(client, t, b, br, p, "2026-09-15T10:00:00Z", amt="300000", cust_id=cu2)
        r = _cust_resp(client, t, b)
        assert r.status_code == 200
        custs = r.json()["customers"]
        assert len(custs) == 2
        assert Decimal(str(custs[0]["net_sales"])) >= Decimal(str(custs[1]["net_sales"]))

    def test_customer_filter(self, client):
        t = _reg(client); b = _biz(client, t); u = _unit(client, t, b); br = _branch(client, t, b)
        cu1 = _cust(client, t, b, name="A"); cu2 = _cust(client, t, b, name="B")
        p = _prod(client, t, b, u); pl = _plist(client, t, b); _pentry(client, t, b, pl, p)
        _sale(client, t, b, br, p, "2026-09-10T10:00:00Z", amt="100000", cust_id=cu1)
        _sale(client, t, b, br, p, "2026-09-15T10:00:00Z", amt="300000", cust_id=cu2)
        r = _cust_resp(client, t, b, customer_id=cu1)
        assert r.status_code == 200
        assert len(r.json()["customers"]) == 1

    def test_walk_in_handling(self, client):
        t = _reg(client); b = _biz(client, t); u = _unit(client, t, b); br = _branch(client, t, b)
        p = _prod(client, t, b, u); pl = _plist(client, t, b); _pentry(client, t, b, pl, p)
        _sale(client, t, b, br, p, "2026-09-10T10:00:00Z", amt="150000")
        custs = _cust_resp(client, t, b).json()["customers"]
        assert len(custs) == 1
        assert custs[0]["customer_id"] is None
        assert custs[0]["customer_name"] == "WALK_IN"

    def test_foreign_customer_404(self, client):
        t1 = _reg(client, "u1@e.com"); b1 = _biz(client, t1, "B1")
        t2 = _reg(client, "u2@e.com"); b2 = _biz(client, t2, "B2"); cu2 = _cust(client, t2, b2)
        r = client.get(f"/api/v1/businesses/{b1}/sales/analytics/by-customer?date_from=2026-09-01T00:00:00Z&date_to=2026-09-30T23:59:59Z&customer_id={cu2}", headers={"Authorization": f"Bearer {t1}"})
        assert r.status_code == 404

    def test_customer_reconciliation(self, client):
        t = _reg(client); b = _biz(client, t); u = _unit(client, t, b); br = _branch(client, t, b)
        cu1 = _cust(client, t, b, name="A"); cu2 = _cust(client, t, b, name="B")
        p = _prod(client, t, b, u); pl = _plist(client, t, b); _pentry(client, t, b, pl, p)
        _sale(client, t, b, br, p, "2026-09-10T10:00:00Z", amt="100000", cust_id=cu1)
        _sale(client, t, b, br, p, "2026-09-15T10:00:00Z", amt="300000", cust_id=cu2)
        sm = _s(client, t, b).json(); cm = _cust_resp(client, t, b).json()
        cust_net = sum(Decimal(str(c["net_sales"])) for c in cm["customers"])
        assert cust_net == Decimal(str(sm["net_sales"]))

    def test_branch_filter(self, client):
        t = _reg(client); b = _biz(client, t); u = _unit(client, t, b)
        br1 = _branch(client, t, b, code="B1"); br2 = _branch(client, t, b, code="B2")
        p = _prod(client, t, b, u); pl = _plist(client, t, b); _pentry(client, t, b, pl, p)
        _sale(client, t, b, br1, p, "2026-09-10T10:00:00Z", amt="100000")
        _sale(client, t, b, br2, p, "2026-09-15T10:00:00Z", amt="300000")
        d = _s(client, t, b, branch_id=br1).json()
        assert d["transaction_count"] == 1

    def test_foreign_branch_404(self, client):
        t1 = _reg(client, "u1@e.com"); b1 = _biz(client, t1, "B1")
        t2 = _reg(client, "u2@e.com"); b2 = _biz(client, t2, "B2"); br2 = _branch(client, t2, b2)
        r = client.get(f"/api/v1/businesses/{b1}/sales/analytics/summary?date_from=2026-09-01T00:00:00Z&date_to=2026-09-30T23:59:59Z&branch_id={br2}", headers={"Authorization": f"Bearer {t1}"})
        assert r.status_code == 404

    def test_unauthenticated_401(self, client):
        r = client.get("/api/v1/businesses/x/sales/analytics/summary?date_from=2026-09-01T00:00:00Z&date_to=2026-09-30T23:59:59Z")
        assert r.status_code == 401

    def test_cross_business_denied(self, client):
        t1 = _reg(client, "u1@e.com"); b1 = _biz(client, t1, "B1")
        t2 = _reg(client, "u2@e.com"); b2 = _biz(client, t2, "B2")
        r = client.get(f"/api/v1/businesses/{b2}/sales/analytics/summary?date_from=2026-09-01T00:00:00Z&date_to=2026-09-30T23:59:59Z", headers={"Authorization": f"Bearer {t1}"})
        assert r.status_code == 404

    def test_decimal_aggregation(self, client):
        t = _reg(client); b = _biz(client, t); u = _unit(client, t, b); br = _branch(client, t, b)
        p = _prod(client, t, b, u); pl = _plist(client, t, b); _pentry(client, t, b, pl, p)
        _sale(client, t, b, br, p, "2026-09-10T10:00:00Z", amt="33333.33")
        _sale(client, t, b, br, p, "2026-09-15T10:00:00Z", amt="66666.67")
        r = _s(client, t, b)
        assert r.status_code == 200
        gross = str(r.json()["gross_sales"])
        assert "e" not in gross.lower()

    def test_category_ordering_deterministic(self, client):
        t = _reg(client); b = _biz(client, t); u = _unit(client, t, b); br = _branch(client, t, b)
        c1 = _cat(client, t, b, name="ZZZ", code="ZZ"); c2 = _cat(client, t, b, name="AAA", code="AA")
        p1 = _prod(client, t, b, u, name="P1", code="P1", cat_id=c1)
        p2 = _prod(client, t, b, u, name="P2", code="P2", cat_id=c2)
        pl = _plist(client, t, b); _pentry(client, t, b, pl, p1); _pentry(client, t, b, pl, p2)
        _sale(client, t, b, br, p1, "2026-09-10T10:00:00Z", amt="100000")
        _sale(client, t, b, br, p2, "2026-09-15T10:00:00Z", amt="100000")
        cats = _cat_resp(client, t, b).json()["categories"]
        assert cats[0]["category_name"] == "AAA"
        assert cats[1]["category_name"] == "ZZZ"

    def test_customer_ordering_deterministic(self, client):
        t = _reg(client); b = _biz(client, t); u = _unit(client, t, b); br = _branch(client, t, b)
        cu1 = _cust(client, t, b, name="ZZZ"); cu2 = _cust(client, t, b, name="AAA")
        p = _prod(client, t, b, u); pl = _plist(client, t, b); _pentry(client, t, b, pl, p)
        _sale(client, t, b, br, p, "2026-09-10T10:00:00Z", amt="100000", cust_id=cu1)
        _sale(client, t, b, br, p, "2026-09-15T10:00:00Z", amt="100000", cust_id=cu2)
        custs = _cust_resp(client, t, b).json()["customers"]
        assert custs[0]["customer_name"] == "AAA"
        assert custs[1]["customer_name"] == "ZZZ"

    def test_return_in_different_period(self, client):
        # NOTE: In current domain, return_date = sales.sales_date, so returns are always
        # in the same period as the original sale. This test documents that behavior.
        t = _reg(client); b = _biz(client, t); u = _unit(client, t, b); br = _branch(client, t, b)
        c1 = _cat(client, t, b); p = _prod(client, t, b, u, cat_id=c1)
        pl = _plist(client, t, b); _pentry(client, t, b, pl, p)
        sid = _sale(client, t, b, br, p, "2026-09-10T10:00:00Z", amt="100000")
        sale_detail = client.get(f"/api/v1/businesses/{b}/sales/{sid}", headers={"Authorization": f"Bearer {t}"}).json()
        line_id = sale_detail["lines"][0]["id"]
        locs = client.get(f"/api/v1/businesses/{b}/warehouses", headers={"Authorization": f"Bearer {t}"}).json()
        loc_id = client.get(f"/api/v1/businesses/{b}/warehouses/{locs[0]['id']}/locations", headers={"Authorization": f"Bearer {t}"}).json()[0]["id"]
        _ret(client, t, b, sid, line_id, loc_id=loc_id)
        # Returns always same period as sale, so September analytics include this return
        d = _s(client, t, b).json()
        assert Decimal(str(d["sales_returns"])) > 0
        assert d["transaction_count"] == 1

    def test_empty_categories_list(self, client):
        t = _reg(client); b = _biz(client, t)
        r = _cat_resp(client, t, b)
        assert r.status_code == 200
        assert r.json()["categories"] == []

    def test_empty_customers_list(self, client):
        t = _reg(client); b = _biz(client, t)
        r = _cust_resp(client, t, b)
        assert r.status_code == 200
        assert r.json()["customers"] == []

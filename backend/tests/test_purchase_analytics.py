import pytest
from datetime import datetime, timezone
from decimal import Decimal
from fastapi.testclient import TestClient

from app.main import app
from app.modules.authentication.repository import InMemoryUserRepository
from app.modules.account.repository import InMemoryAccountRepository
from app.modules.business.repository import InMemoryBusinessRepository
from app.modules.business_membership.repository import InMemoryBusinessMembershipRepository
from app.modules.supplier.repository import InMemorySupplierRepository
from app.modules.branch.repository import InMemoryBranchRepository
from app.modules.unit.repository import InMemoryUnitRepository
from app.modules.product.repository import InMemoryProductRepository
from app.modules.category.repository import InMemoryCategoryRepository
from app.modules.purchase.repository import InMemoryPurchaseRepository
from app.modules.purchase_return.repository import InMemoryPurchaseReturnRepository
from app.modules.receiving.repository import InMemoryReceivingRepository
from app.modules.warehouse.repository import InMemoryWarehouseRepository, InMemoryInventoryLocationRepository
from app.modules.inventory.repository import (
    InMemoryStockBalanceRepository, InMemoryStockMovementRepository, InMemoryInventoryCostRepository,
)
from app.modules.pricing.repository import InMemoryPriceListRepository, InMemoryPriceEntryRepository

_counter = 0

def _inc():
    global _counter
    _counter += 1
    return _counter


@pytest.fixture(autouse=True)
def clear_repos():
    global _counter
    _counter = 0
    for repo in [
        InMemoryUserRepository, InMemoryAccountRepository, InMemoryBusinessRepository,
        InMemoryBusinessMembershipRepository, InMemorySupplierRepository, InMemoryBranchRepository,
        InMemoryUnitRepository, InMemoryProductRepository, InMemoryCategoryRepository,
        InMemoryPurchaseRepository, InMemoryPurchaseReturnRepository, InMemoryReceivingRepository,
        InMemoryWarehouseRepository, InMemoryInventoryLocationRepository,
        InMemoryStockBalanceRepository, InMemoryStockMovementRepository, InMemoryInventoryCostRepository,
        InMemoryPriceListRepository, InMemoryPriceEntryRepository,
    ]:
        repo.clear()
    yield
    for repo in [
        InMemoryUserRepository, InMemoryAccountRepository, InMemoryBusinessRepository,
        InMemoryBusinessMembershipRepository, InMemorySupplierRepository, InMemoryBranchRepository,
        InMemoryUnitRepository, InMemoryProductRepository, InMemoryCategoryRepository,
        InMemoryPurchaseRepository, InMemoryPurchaseReturnRepository, InMemoryReceivingRepository,
        InMemoryWarehouseRepository, InMemoryInventoryLocationRepository,
        InMemoryStockBalanceRepository, InMemoryStockMovementRepository, InMemoryInventoryCostRepository,
        InMemoryPriceListRepository, InMemoryPriceEntryRepository,
    ]:
        repo.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# ── Helpers ──────────────────────────────────────────────────

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
    n = _inc()
    r = c.post(f"/api/v1/businesses/{biz}/units", headers={"Authorization": f"Bearer {tok}"}, json={"name": f"Unit{n}", "code": f"U{n}", "symbol": "pcs", "unit_type": "OTHER"})
    assert r.status_code == 201
    return r.json()["id"]

def _branch(c, tok, biz):
    n = _inc()
    r = c.post(f"/api/v1/businesses/{biz}/branches", headers={"Authorization": f"Bearer {tok}"}, json={"name": f"Branch{n}", "code": f"BR{n}"})
    assert r.status_code == 201
    return r.json()["id"]

def _sup(c, tok, biz, name=None):
    n = _inc()
    r = c.post(f"/api/v1/businesses/{biz}/suppliers", headers={"Authorization": f"Bearer {tok}"}, json={"name": name or f"Sup{n}", "supplier_type": "ORGANIZATION"})
    assert r.status_code == 201
    return r.json()["id"]

def _cat(c, tok, biz, name=None, code=None):
    n = _inc()
    r = c.post(f"/api/v1/businesses/{biz}/categories", headers={"Authorization": f"Bearer {tok}"}, json={"name": name or f"Cat{n}", "code": code or f"C{n}"})
    assert r.status_code == 201
    return r.json()["id"]

def _prod(c, tok, biz, unit_id, name=None, code=None, cat_id=None):
    n = _inc()
    p = {"name": name or f"Prod{n}", "code": code or f"P{n}", "unit_id": unit_id, "product_type": "GOODS"}
    if cat_id:
        p["category_id"] = cat_id
    r = c.post(f"/api/v1/businesses/{biz}/products", headers={"Authorization": f"Bearer {tok}"}, json=p)
    assert r.status_code == 201
    return r.json()["id"]

def _stock(c, tok, biz, prod_id):
    n = _inc()
    wh = c.post(f"/api/v1/businesses/{biz}/warehouses", headers={"Authorization": f"Bearer {tok}"}, json={"name": f"WH{n}", "code": f"WH{n}"})
    assert wh.status_code == 201
    loc = c.post(f"/api/v1/businesses/{biz}/warehouses/{wh.json()['id']}/locations", headers={"Authorization": f"Bearer {tok}"}, json={"name": f"Loc{n}", "code": f"L{n}", "location_type": "GENERAL"})
    assert loc.status_code == 201
    lid = loc.json()["id"]
    c.post(f"/api/v1/businesses/{biz}/inventory/opening-balance", headers={"Authorization": f"Bearer {tok}"}, json={"inventory_location_id": lid, "product_id": prod_id, "quantity": "10000"})
    return lid

def _purchase(c, tok, biz, sup_id, br_id, p_date, amt="100000", cat_id=None, qty="2"):
    r = c.post(f"/api/v1/businesses/{biz}/purchases", headers={"Authorization": f"Bearer {tok}"}, json={"supplier_id": sup_id, "branch_id": br_id, "purchase_date": p_date})
    assert r.status_code == 201
    pid = r.json()["id"]
    u = _unit(c, tok, biz)
    p = _prod(c, tok, biz, u, cat_id=cat_id)
    c.post(f"/api/v1/businesses/{biz}/purchases/{pid}/lines", headers={"Authorization": f"Bearer {tok}"}, json={"product_id": p, "quantity": qty, "unit_price": amt})
    lid = _stock(c, tok, biz, p)
    fin = c.post(f"/api/v1/businesses/{biz}/purchases/{pid}/finalize", headers={"Authorization": f"Bearer {tok}"})
    assert fin.status_code == 200
    return pid, p, lid

def _purchase_raw(c, tok, biz, sup_id, br_id, p_date):
    r = c.post(f"/api/v1/businesses/{biz}/purchases", headers={"Authorization": f"Bearer {tok}"}, json={"supplier_id": sup_id, "branch_id": br_id, "purchase_date": p_date})
    assert r.status_code == 201
    return r.json()["id"]

def _purch_ret(c, tok, biz, pur_id, line_id, loc_id, qty="1"):
    rcv = c.post(f"/api/v1/businesses/{biz}/receivings", headers={"Authorization": f"Bearer {tok}"}, json={"purchase_id": pur_id, "inventory_location_id": loc_id})
    assert rcv.status_code == 201
    rcv_id = rcv.json()["id"]
    c.post(f"/api/v1/businesses/{biz}/receivings/{rcv_id}/lines", headers={"Authorization": f"Bearer {tok}"}, json={"purchase_line_id": line_id, "quantity": qty})
    c.post(f"/api/v1/businesses/{biz}/receivings/{rcv_id}/finalize", headers={"Authorization": f"Bearer {tok}"})
    r = c.post(f"/api/v1/businesses/{biz}/purchase-returns", headers={"Authorization": f"Bearer {tok}"}, json={"purchase_id": pur_id, "inventory_location_id": loc_id})
    assert r.status_code == 201
    rid = r.json()["id"]
    c.post(f"/api/v1/businesses/{biz}/purchase-returns/{rid}/lines", headers={"Authorization": f"Bearer {tok}"}, json={"purchase_line_id": line_id, "quantity": qty})
    fin = c.post(f"/api/v1/businesses/{biz}/purchase-returns/{rid}/finalize", headers={"Authorization": f"Bearer {tok}"})
    assert fin.status_code == 200
    return rid

def _s(c, tok, biz, df="2026-09-01T00:00:00Z", dt="2026-09-30T23:59:59Z", **kw):
    params = f"?date_from={df}&date_to={dt}"
    for k, v in kw.items():
        if v is not None:
            params += f"&{k}={v}"
    return c.get(f"/api/v1/businesses/{biz}/purchases/analytics/summary{params}", headers={"Authorization": f"Bearer {tok}"})

def _sup_resp(c, tok, biz, df="2026-09-01T00:00:00Z", dt="2026-09-30T23:59:59Z", **kw):
    params = f"?date_from={df}&date_to={dt}"
    for k, v in kw.items():
        if v is not None:
            params += f"&{k}={v}"
    return c.get(f"/api/v1/businesses/{biz}/purchases/analytics/by-supplier{params}", headers={"Authorization": f"Bearer {tok}"})

def _cat_resp(c, tok, biz, df="2026-09-01T00:00:00Z", dt="2026-09-30T23:59:59Z", **kw):
    params = f"?date_from={df}&date_to={dt}"
    for k, v in kw.items():
        if v is not None:
            params += f"&{k}={v}"
    return c.get(f"/api/v1/businesses/{biz}/purchases/analytics/by-category{params}", headers={"Authorization": f"Bearer {tok}"})


# ── Tests ────────────────────────────────────────────────────

class TestPurchaseAnalytics:

    # ═══ PURCHASE INCLUSION / EXCLUSION ═══════════════════════

    # 1. finalized included
    def test_finalized_included(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b); sup = _sup(client, t, b)
        _purchase(client, t, b, sup, br, "2026-09-15T10:00:00Z", amt="100000")
        d = _s(client, t, b).json()
        assert d["purchase_count"] == 1
        assert Decimal(str(d["gross_purchases"])) > 0

    # 2. draft excluded
    def test_draft_excluded(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b); sup = _sup(client, t, b)
        _purchase_raw(client, t, b, sup, br, "2026-09-15T10:00:00Z")
        assert _s(client, t, b).json()["purchase_count"] == 0

    # 3. cancelled excluded
    def test_cancelled_excluded(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b); sup = _sup(client, t, b)
        pid = _purchase_raw(client, t, b, sup, br, "2026-09-15T10:00:00Z")
        client.post(f"/api/v1/businesses/{b}/purchases/{pid}/cancel", headers={"Authorization": f"Bearer {t}"})
        assert _s(client, t, b).json()["purchase_count"] == 0

    # 4. multiple finalized
    def test_multiple_finalized(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b); sup = _sup(client, t, b)
        _purchase(client, t, b, sup, br, "2026-09-10T10:00:00Z", amt="100000")
        _purchase(client, t, b, sup, br, "2026-09-20T10:00:00Z", amt="200000")
        d = _s(client, t, b).json()
        assert d["purchase_count"] == 2

    # 5. empty period
    def test_zero_purchases(self, client):
        t = _reg(client); b = _biz(client, t)
        d = _s(client, t, b).json()
        assert Decimal(str(d["gross_purchases"])) == 0
        assert d["purchase_count"] == 0

    # ═══ FINANCIAL METRICS ═══════════════════════════════════

    # 6. gross purchases
    def test_gross_purchases(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b); sup = _sup(client, t, b)
        _purchase(client, t, b, sup, br, "2026-09-15T10:00:00Z", amt="250000")
        d = _s(client, t, b).json()
        assert Decimal(str(d["gross_purchases"])) == Decimal("500000")

    # 7. net purchases formula
    def test_net_purchases_formula(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b); sup = _sup(client, t, b)
        _purchase(client, t, b, sup, br, "2026-09-10T10:00:00Z", amt="100000")
        d = _s(client, t, b).json()
        assert Decimal(str(d["net_purchases"])) == Decimal(str(d["gross_purchases"]))

    # 8. average purchase value single
    def test_average_single(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b); sup = _sup(client, t, b)
        _purchase(client, t, b, sup, br, "2026-09-15T10:00:00Z", amt="125000")
        d = _s(client, t, b).json()
        assert Decimal(str(d["average_purchase_value"])) == Decimal("250000")

    # 9. average purchase value multiple
    def test_average_multiple(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b); sup = _sup(client, t, b)
        _purchase(client, t, b, sup, br, "2026-09-10T10:00:00Z", amt="150000")
        _purchase(client, t, b, sup, br, "2026-09-20T10:00:00Z", amt="50000")
        d = _s(client, t, b).json()
        assert Decimal(str(d["average_purchase_value"])) == Decimal("200000")

    # 10. average purchase zero division
    def test_average_zero_purchases(self, client):
        t = _reg(client); b = _biz(client, t)
        d = _s(client, t, b).json()
        assert Decimal(str(d["average_purchase_value"])) == 0

    # ═══ DATE BOUNDARIES ═════════════════════════════════════

    # 11. date_from boundary included
    def test_date_from_boundary(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b); sup = _sup(client, t, b)
        _purchase(client, t, b, sup, br, "2026-09-01T00:00:00Z")
        assert _s(client, t, b).json()["purchase_count"] == 1

    # 12. date_to boundary included
    def test_date_to_boundary(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b); sup = _sup(client, t, b)
        _purchase(client, t, b, sup, br, "2026-09-30T23:59:59Z")
        assert _s(client, t, b).json()["purchase_count"] == 1

    # 13. before range excluded
    def test_before_range_excluded(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b); sup = _sup(client, t, b)
        _purchase(client, t, b, sup, br, "2026-08-31T23:59:59Z")
        assert _s(client, t, b).json()["purchase_count"] == 0

    # 14. after range excluded
    def test_after_range_excluded(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b); sup = _sup(client, t, b)
        _purchase(client, t, b, sup, br, "2026-10-01T00:00:00Z")
        assert _s(client, t, b).json()["purchase_count"] == 0

    # 15. reversed range -> 400
    def test_reversed_range(self, client):
        t = _reg(client); b = _biz(client, t)
        r = _s(client, t, b, df="2026-09-30T00:00:00Z", dt="2026-09-01T00:00:00Z")
        assert r.status_code == 400

    # 16. incomplete dates -> 422
    def test_incomplete_dates(self, client):
        t = _reg(client); b = _biz(client, t)
        r = client.get(f"/api/v1/businesses/{b}/purchases/analytics/summary?date_from=2026-09-01T00:00:00Z", headers={"Authorization": f"Bearer {t}"})
        assert r.status_code == 422

    # 17. same day range
    def test_same_day_range(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b); sup = _sup(client, t, b)
        _purchase(client, t, b, sup, br, "2026-09-15T12:00:00Z")
        d = _s(client, t, b, df="2026-09-15T00:00:00Z", dt="2026-09-15T23:59:59Z").json()
        assert d["purchase_count"] == 1

    # ═══ PURCHASE RETURNS ═════════════════════════════════════

    # 18. finalized return included
    def test_return_included(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b); sup = _sup(client, t, b); c1 = _cat(client, t, b)
        pid, prod, lid = _purchase(client, t, b, sup, br, "2026-09-10T10:00:00Z", amt="100000", cat_id=c1)
        pur_detail = client.get(f"/api/v1/businesses/{b}/purchases/{pid}", headers={"Authorization": f"Bearer {t}"}).json()
        line_id = pur_detail["lines"][0]["id"]
        _purch_ret(client, t, b, pid, line_id, lid)
        d = _s(client, t, b).json()
        assert Decimal(str(d["purchase_returns"])) > 0
        assert Decimal(str(d["net_purchases"])) == Decimal(str(d["gross_purchases"])) - Decimal(str(d["purchase_returns"]))

    # 19. draft return excluded
    def test_draft_return_excluded(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b); sup = _sup(client, t, b)
        pid, prod, lid = _purchase(client, t, b, sup, br, "2026-09-10T10:00:00Z", amt="100000")
        pur_detail = client.get(f"/api/v1/businesses/{b}/purchases/{pid}", headers={"Authorization": f"Bearer {t}"}).json()
        line_id = pur_detail["lines"][0]["id"]
        client.post(f"/api/v1/businesses/{b}/purchase-returns", headers={"Authorization": f"Bearer {t}"}, json={"purchase_id": pid, "inventory_location_id": lid})
        assert Decimal(str(_s(client, t, b).json()["purchase_returns"])) == 0

    # 20. cancelled return excluded
    def test_cancelled_return_excluded(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b); sup = _sup(client, t, b)
        pid, prod, lid = _purchase(client, t, b, sup, br, "2026-09-10T10:00:00Z", amt="100000")
        pur_detail = client.get(f"/api/v1/businesses/{b}/purchases/{pid}", headers={"Authorization": f"Bearer {t}"}).json()
        line_id = pur_detail["lines"][0]["id"]
        rcv = client.post(f"/api/v1/businesses/{b}/receivings", headers={"Authorization": f"Bearer {t}"}, json={"purchase_id": pid, "inventory_location_id": lid}).json()
        client.post(f"/api/v1/businesses/{b}/receivings/{rcv['id']}/lines", headers={"Authorization": f"Bearer {t}"}, json={"purchase_line_id": line_id, "quantity": "1"})
        client.post(f"/api/v1/businesses/{b}/receivings/{rcv['id']}/finalize", headers={"Authorization": f"Bearer {t}"})
        ret = client.post(f"/api/v1/businesses/{b}/purchase-returns", headers={"Authorization": f"Bearer {t}"}, json={"purchase_id": pid, "inventory_location_id": lid}).json()
        client.post(f"/api/v1/businesses/{b}/purchase-returns/{ret['id']}/lines", headers={"Authorization": f"Bearer {t}"}, json={"purchase_line_id": line_id, "quantity": "1"})
        client.post(f"/api/v1/businesses/{b}/purchase-returns/{ret['id']}/cancel", headers={"Authorization": f"Bearer {t}"})
        assert Decimal(str(_s(client, t, b).json()["purchase_returns"])) == 0

    # 21. return does not decrement purchase count
    def test_return_does_not_decrement_count(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b); sup = _sup(client, t, b); c1 = _cat(client, t, b)
        pid, prod, lid = _purchase(client, t, b, sup, br, "2026-09-10T10:00:00Z", amt="100000", cat_id=c1)
        pur_detail = client.get(f"/api/v1/businesses/{b}/purchases/{pid}", headers={"Authorization": f"Bearer {t}"}).json()
        line_id = pur_detail["lines"][0]["id"]
        _purch_ret(client, t, b, pid, line_id, lid)
        d = _s(client, t, b).json()
        assert d["purchase_count"] == 1

    # ═══ SUPPLIER ═════════════════════════════════════════════

    # 22. supplier aggregation
    def test_supplier_aggregation(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b)
        sup1 = _sup(client, t, b, name="Sup A"); sup2 = _sup(client, t, b, name="Sup B")
        _purchase(client, t, b, sup1, br, "2026-09-10T10:00:00Z", amt="100000")
        _purchase(client, t, b, sup2, br, "2026-09-15T10:00:00Z", amt="300000")
        sups = _sup_resp(client, t, b).json()["suppliers"]
        assert len(sups) == 2

    # 23. supplier filter
    def test_supplier_filter(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b)
        sup1 = _sup(client, t, b, name="Sup A"); sup2 = _sup(client, t, b, name="Sup B")
        _purchase(client, t, b, sup1, br, "2026-09-10T10:00:00Z", amt="100000")
        _purchase(client, t, b, sup2, br, "2026-09-15T10:00:00Z", amt="300000")
        d = _s(client, t, b, supplier_id=sup1).json()
        assert d["purchase_count"] == 1

    # 24. foreign supplier -> 404
    def test_foreign_supplier_404(self, client):
        t1 = _reg(client, "u1@e.com"); b1 = _biz(client, t1, "B1")
        t2 = _reg(client, "u2@e.com"); b2 = _biz(client, t2, "B2")
        sup2 = _sup(client, t2, b2)
        r = _s(client, t1, b1, supplier_id=sup2)
        assert r.status_code == 404

    # 25. supplier ordering deterministic
    def test_supplier_ordering_deterministic(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b)
        sup1 = _sup(client, t, b, name="ZZZ"); sup2 = _sup(client, t, b, name="AAA")
        _purchase(client, t, b, sup1, br, "2026-09-10T10:00:00Z", amt="100000")
        _purchase(client, t, b, sup2, br, "2026-09-15T10:00:00Z", amt="100000")
        sups = _sup_resp(client, t, b).json()["suppliers"]
        assert sups[0]["supplier_name"] == "AAA"
        assert sups[1]["supplier_name"] == "ZZZ"

    # 26. supplier reconciliation
    def test_supplier_reconciliation(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b)
        sup1 = _sup(client, t, b, name="Sup A"); sup2 = _sup(client, t, b, name="Sup B")
        _purchase(client, t, b, sup1, br, "2026-09-10T10:00:00Z", amt="100000")
        _purchase(client, t, b, sup2, br, "2026-09-15T10:00:00Z", amt="300000")
        sm = _s(client, t, b).json()
        sm_resp = _sup_resp(client, t, b).json()
        sup_net = sum(Decimal(str(s["net_purchases"])) for s in sm_resp["suppliers"])
        assert sup_net == Decimal(str(sm["net_purchases"]))

    # 27. empty suppliers
    def test_empty_suppliers(self, client):
        t = _reg(client); b = _biz(client, t)
        assert _sup_resp(client, t, b).json()["suppliers"] == []

    # ═══ CATEGORY ═════════════════════════════════════════════

    # 28. category aggregation
    def test_category_aggregation(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b); sup = _sup(client, t, b)
        c1 = _cat(client, t, b, name="A", code="A"); c2 = _cat(client, t, b, name="B", code="B")
        _purchase(client, t, b, sup, br, "2026-09-10T10:00:00Z", amt="100000", cat_id=c1)
        _purchase(client, t, b, sup, br, "2026-09-15T10:00:00Z", amt="200000", cat_id=c2)
        cats = _cat_resp(client, t, b).json()["categories"]
        assert len(cats) == 2

    # 29. category filter
    def test_category_filter(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b); sup = _sup(client, t, b)
        c1 = _cat(client, t, b, name="A", code="A"); c2 = _cat(client, t, b, name="B", code="B")
        _purchase(client, t, b, sup, br, "2026-09-10T10:00:00Z", amt="100000", cat_id=c1)
        _purchase(client, t, b, sup, br, "2026-09-15T10:00:00Z", amt="200000", cat_id=c2)
        d = _s(client, t, b, category_id=c1).json()
        assert d["purchase_count"] == 1

    # 30. foreign category -> 404
    def test_foreign_category_404(self, client):
        t1 = _reg(client, "u1@e.com"); b1 = _biz(client, t1, "B1")
        t2 = _reg(client, "u2@e.com"); b2 = _biz(client, t2, "B2")
        c2 = _cat(client, t2, b2)
        r = _s(client, t1, b1, category_id=c2)
        assert r.status_code == 404

    # 31. category ordering deterministic
    def test_category_ordering_deterministic(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b); sup = _sup(client, t, b)
        c1 = _cat(client, t, b, name="ZZZ", code="ZZ"); c2 = _cat(client, t, b, name="AAA", code="AA")
        _purchase(client, t, b, sup, br, "2026-09-10T10:00:00Z", amt="100000", cat_id=c1)
        _purchase(client, t, b, sup, br, "2026-09-15T10:00:00Z", amt="100000", cat_id=c2)
        cats = _cat_resp(client, t, b).json()["categories"]
        assert cats[0]["category_name"] == "AAA"
        assert cats[1]["category_name"] == "ZZZ"

    # 32. category reconciliation
    def test_category_reconciliation(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b); sup = _sup(client, t, b)
        c1 = _cat(client, t, b, name="A", code="A"); c2 = _cat(client, t, b, name="B", code="B")
        _purchase(client, t, b, sup, br, "2026-09-10T10:00:00Z", amt="100000", cat_id=c1)
        _purchase(client, t, b, sup, br, "2026-09-15T10:00:00Z", amt="200000", cat_id=c2)
        sm = _s(client, t, b).json()
        cm = _cat_resp(client, t, b).json()
        cat_net = sum(Decimal(str(c["net_purchases"])) for c in cm["categories"])
        assert cat_net == Decimal(str(sm["net_purchases"]))

    # 33. category gross reconciliation
    def test_category_gross_reconciliation(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b); sup = _sup(client, t, b)
        c1 = _cat(client, t, b, name="A", code="A")
        _purchase(client, t, b, sup, br, "2026-09-10T10:00:00Z", amt="100000", cat_id=c1)
        _purchase(client, t, b, sup, br, "2026-09-15T10:00:00Z", amt="200000", cat_id=c1)
        sm = _s(client, t, b).json()
        cm = _cat_resp(client, t, b).json()
        cat_gross = sum(Decimal(str(c["gross_purchases"])) for c in cm["categories"])
        assert cat_gross == Decimal(str(sm["gross_purchases"]))

    # 34. empty categories
    def test_empty_categories(self, client):
        t = _reg(client); b = _biz(client, t)
        assert _cat_resp(client, t, b).json()["categories"] == []

    # ═══ BRANCH ═══════════════════════════════════════════════

    # 35. branch filter
    def test_branch_filter(self, client):
        t = _reg(client); b = _biz(client, t)
        br1 = _branch(client, t, b); br2 = _branch(client, t, b)
        sup = _sup(client, t, b)
        _purchase(client, t, b, sup, br1, "2026-09-10T10:00:00Z", amt="100000")
        _purchase(client, t, b, sup, br2, "2026-09-15T10:00:00Z", amt="300000")
        d = _s(client, t, b, branch_id=br1).json()
        assert d["purchase_count"] == 1

    # 36. foreign branch -> 404
    def test_foreign_branch_404(self, client):
        t1 = _reg(client, "u1@e.com"); b1 = _biz(client, t1, "B1")
        t2 = _reg(client, "u2@e.com"); b2 = _biz(client, t2, "B2")
        br2 = _branch(client, t2, b2)
        r = _s(client, t1, b1, branch_id=br2)
        assert r.status_code == 404

    # ═══ SECURITY ═════════════════════════════════════════════

    # 37. unauthenticated -> 401
    def test_unauthenticated_401(self, client):
        r = client.get("/api/v1/businesses/x/purchases/analytics/summary?date_from=2026-09-01T00:00:00Z&date_to=2026-09-30T23:59:59Z")
        assert r.status_code == 401

    # 38. cross-business isolation
    def test_cross_business_denied(self, client):
        t1 = _reg(client, "u1@e.com"); b1 = _biz(client, t1, "B1")
        t2 = _reg(client, "u2@e.com"); b2 = _biz(client, t2, "B2")
        r = _s(client, t1, b2)
        assert r.status_code == 404

    # 39. member can read
    def test_member_can_read(self, client):
        t1 = _reg(client); b1 = _biz(client, t1, "B1")
        t2 = _reg(client, "mem@e.com")
        uid2 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {t2}"}).json()["id"]
        client.post(f"/api/v1/businesses/{b1}/members", headers={"Authorization": f"Bearer {t1}"}, json={"user_id": uid2, "role": "MEMBER"})
        r = _s(client, t2, b1)
        assert r.status_code == 200

    # ═══ DECIMAL / NUMERIC ════════════════════════════════════

    # 40. decimal aggregation
    def test_decimal_aggregation(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b); sup = _sup(client, t, b)
        _purchase(client, t, b, sup, br, "2026-09-10T10:00:00Z", amt="16666.67")
        _purchase(client, t, b, sup, br, "2026-09-15T10:00:00Z", amt="33333.33")
        d = _s(client, t, b).json()
        gross = str(d["gross_purchases"])
        assert "e" not in gross.lower()
        assert Decimal(str(d["gross_purchases"])) == Decimal("100000.00")

    # 41. large amounts
    def test_large_amounts(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b); sup = _sup(client, t, b)
        _purchase(client, t, b, sup, br, "2026-09-15T10:00:00Z", amt="500000000")
        d = _s(client, t, b).json()
        assert Decimal(str(d["gross_purchases"])) == Decimal("1000000000")

    # ═══ RECONCILIATION INVARIANTS ════════════════════════════

    # 42. supplier gross reconciliation
    def test_supplier_gross_reconciliation(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b)
        sup1 = _sup(client, t, b, name="A"); sup2 = _sup(client, t, b, name="B")
        _purchase(client, t, b, sup1, br, "2026-09-10T10:00:00Z", amt="100000")
        _purchase(client, t, b, sup2, br, "2026-09-15T10:00:00Z", amt="200000")
        sm = _s(client, t, b).json()
        sm_resp = _sup_resp(client, t, b).json()
        sup_gross = sum(Decimal(str(s["gross_purchases"])) for s in sm_resp["suppliers"])
        assert sup_gross == Decimal(str(sm["gross_purchases"]))

    # 43. supplier returns reconciliation
    def test_supplier_returns_reconciliation(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b); sup = _sup(client, t, b); c1 = _cat(client, t, b)
        pid, prod, lid = _purchase(client, t, b, sup, br, "2026-09-10T10:00:00Z", amt="100000", cat_id=c1)
        pur_detail = client.get(f"/api/v1/businesses/{b}/purchases/{pid}", headers={"Authorization": f"Bearer {t}"}).json()
        line_id = pur_detail["lines"][0]["id"]
        _purch_ret(client, t, b, pid, line_id, lid)
        sm = _s(client, t, b).json()
        sm_resp = _sup_resp(client, t, b).json()
        sup_ret = sum(Decimal(str(s["purchase_returns"])) for s in sm_resp["suppliers"])
        assert sup_ret == Decimal(str(sm["purchase_returns"]))

    # ═══ CATEGORY + SUPPLIER COMBINATION ══════════════════════

    # 44. category filter with supplier filter
    def test_category_supplier_filter(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b)
        sup1 = _sup(client, t, b, name="A"); sup2 = _sup(client, t, b, name="B")
        c1 = _cat(client, t, b, name="X", code="X"); c2 = _cat(client, t, b, name="Y", code="Y")
        _purchase(client, t, b, sup1, br, "2026-09-10T10:00:00Z", amt="100000", cat_id=c1)
        _purchase(client, t, b, sup2, br, "2026-09-15T10:00:00Z", amt="200000", cat_id=c2)
        d = _s(client, t, b, category_id=c1, supplier_id=sup1).json()
        assert d["purchase_count"] == 1

    # 45. branch + supplier combination
    def test_branch_supplier_filter(self, client):
        t = _reg(client); b = _biz(client, t)
        br1 = _branch(client, t, b); br2 = _branch(client, t, b)
        sup = _sup(client, t, b)
        _purchase(client, t, b, sup, br1, "2026-09-10T10:00:00Z", amt="100000")
        _purchase(client, t, b, sup, br2, "2026-09-15T10:00:00Z", amt="200000")
        d = _s(client, t, b, branch_id=br1, supplier_id=sup).json()
        assert d["purchase_count"] == 1

    # ═══ RETURN CATEGORY ATTRIBUTION ══════════════════════════

    # 46. return attributed to correct category in breakdown
    def test_return_category_attribution(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b); sup = _sup(client, t, b); c1 = _cat(client, t, b)
        pid, prod, lid = _purchase(client, t, b, sup, br, "2026-09-10T10:00:00Z", amt="100000", cat_id=c1)
        pur_detail = client.get(f"/api/v1/businesses/{b}/purchases/{pid}", headers={"Authorization": f"Bearer {t}"}).json()
        line_id = pur_detail["lines"][0]["id"]
        _purch_ret(client, t, b, pid, line_id, lid)
        cm = _cat_resp(client, t, b).json()
        assert len(cm["categories"]) == 1
        cat = cm["categories"][0]
        assert cat["category_id"] == c1
        assert Decimal(str(cat["purchase_returns"])) > 0

    # ═══ RETURN SUPPLIER ATTRIBUTION ══════════════════════════

    # 47. return attributed to correct supplier in breakdown
    def test_return_supplier_attribution(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b); sup = _sup(client, t, b); c1 = _cat(client, t, b)
        pid, prod, lid = _purchase(client, t, b, sup, br, "2026-09-10T10:00:00Z", amt="100000", cat_id=c1)
        pur_detail = client.get(f"/api/v1/businesses/{b}/purchases/{pid}", headers={"Authorization": f"Bearer {t}"}).json()
        line_id = pur_detail["lines"][0]["id"]
        _purch_ret(client, t, b, pid, line_id, lid)
        sm_resp = _sup_resp(client, t, b).json()
        assert len(sm_resp["suppliers"]) == 1
        s = sm_resp["suppliers"][0]
        assert s["supplier_id"] == sup
        assert Decimal(str(s["purchase_returns"])) > 0

    # ═══ MULTIPLE RETURNS ═════════════════════════════════════

    # 48. multiple returns against same purchase
    def test_multiple_returns(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b); sup = _sup(client, t, b); c1 = _cat(client, t, b)
        pid, prod, lid = _purchase(client, t, b, sup, br, "2026-09-10T10:00:00Z", amt="100000", cat_id=c1, qty="5")
        pur_detail = client.get(f"/api/v1/businesses/{b}/purchases/{pid}", headers={"Authorization": f"Bearer {t}"}).json()
        line_id = pur_detail["lines"][0]["id"]
        _purch_ret(client, t, b, pid, line_id, lid, qty="2")
        _purch_ret(client, t, b, pid, line_id, lid, qty="1")
        d = _s(client, t, b).json()
        assert Decimal(str(d["purchase_returns"])) > 0

    # ═══ EMPTY DATA ═══════════════════════════════════════════

    # 49. empty summary with zero values
    def test_empty_summary_zero_values(self, client):
        t = _reg(client); b = _biz(client, t)
        d = _s(client, t, b).json()
        assert d["gross_purchases"] == "0" or d["gross_purchases"] == 0 or Decimal(str(d["gross_purchases"])) == 0
        assert d["purchase_returns"] == "0" or d["purchase_returns"] == 0 or Decimal(str(d["purchase_returns"])) == 0
        assert d["net_purchases"] == "0" or d["net_purchases"] == 0 or Decimal(str(d["net_purchases"])) == 0
        assert d["discount_total"] == "0" or d["discount_total"] == 0 or Decimal(str(d["discount_total"])) == 0
        assert d["tax_total"] == "0" or d["tax_total"] == 0 or Decimal(str(d["tax_total"])) == 0
        assert d["purchase_count"] == 0
        assert Decimal(str(d["average_purchase_value"])) == 0

    # ═══ MULTI-LINE PURCHASE ══════════════════════════════════

    # 50. multi-line purchase
    def test_multi_line_purchase(self, client):
        t = _reg(client); b = _biz(client, t)
        br = _branch(client, t, b); sup = _sup(client, t, b)
        c1 = _cat(client, t, b, name="A", code="A"); c2 = _cat(client, t, b, name="B", code="B")
        u = _unit(client, t, b)
        p1 = _prod(client, t, b, u, cat_id=c1)
        p2 = _prod(client, t, b, u, cat_id=c2)
        lid1 = _stock(client, t, b, p1)
        lid2 = _stock(client, t, b, p2)
        pr = client.post(f"/api/v1/businesses/{b}/purchases", headers={"Authorization": f"Bearer {t}"}, json={"supplier_id": sup, "branch_id": br, "purchase_date": "2026-09-15T10:00:00Z"}).json()
        client.post(f"/api/v1/businesses/{b}/purchases/{pr['id']}/lines", headers={"Authorization": f"Bearer {t}"}, json={"product_id": p1, "quantity": "3", "unit_price": "100000"})
        client.post(f"/api/v1/businesses/{b}/purchases/{pr['id']}/lines", headers={"Authorization": f"Bearer {t}"}, json={"product_id": p2, "quantity": "2", "unit_price": "200000"})
        client.post(f"/api/v1/businesses/{b}/purchases/{pr['id']}/finalize", headers={"Authorization": f"Bearer {t}"})
        d = _s(client, t, b).json()
        assert d["purchase_count"] == 1
        assert Decimal(str(d["gross_purchases"])) == Decimal("700000")
        cats = _cat_resp(client, t, b).json()["categories"]
        assert len(cats) == 2

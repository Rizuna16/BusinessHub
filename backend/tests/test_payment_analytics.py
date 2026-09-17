import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from app.main import app
from app.modules.authentication.repository import InMemoryUserRepository
from app.modules.account.repository import InMemoryAccountRepository
from app.modules.business.repository import InMemoryBusinessRepository
from app.modules.business_membership.repository import InMemoryBusinessMembershipRepository
from app.modules.supplier.repository import InMemorySupplierRepository
from app.modules.customer.repository import InMemoryCustomerRepository
from app.modules.branch.repository import InMemoryBranchRepository
from app.modules.unit.repository import InMemoryUnitRepository
from app.modules.product.repository import InMemoryProductRepository
from app.modules.purchase.repository import InMemoryPurchaseRepository
from app.modules.receiving.repository import InMemoryReceivingRepository
from app.modules.purchase_return.repository import InMemoryPurchaseReturnRepository
from app.modules.sales.repository import InMemorySalesRepository
from app.modules.cash_account.repository import InMemoryCashAccountRepository
from app.modules.payment.repository import InMemoryPaymentRepository
from app.modules.warehouse.repository import InMemoryWarehouseRepository, InMemoryInventoryLocationRepository
from app.modules.inventory.repository import InMemoryStockBalanceRepository, InMemoryStockMovementRepository, InMemoryInventoryCostRepository
from app.modules.pricing.repository import InMemoryPriceListRepository, InMemoryPriceEntryRepository

client = TestClient(app)

_counter = 0

def _inc():
    global _counter
    _counter += 1
    return _counter


@pytest.fixture(autouse=True)
def clear_repositories():
    global _counter
    _counter = 0
    for repo in [
        InMemoryPaymentRepository, InMemoryCashAccountRepository,
        InMemorySalesRepository, InMemoryPurchaseReturnRepository,
        InMemoryReceivingRepository, InMemoryPurchaseRepository,
        InMemoryProductRepository, InMemoryUnitRepository,
        InMemoryBranchRepository, InMemoryCustomerRepository,
        InMemorySupplierRepository, InMemoryBusinessMembershipRepository,
        InMemoryBusinessRepository, InMemoryAccountRepository,
        InMemoryUserRepository, InMemoryWarehouseRepository,
        InMemoryInventoryLocationRepository, InMemoryStockBalanceRepository,
        InMemoryStockMovementRepository, InMemoryInventoryCostRepository,
        InMemoryPriceListRepository, InMemoryPriceEntryRepository,
    ]:
        repo.clear()
    yield
    for repo in [
        InMemoryPaymentRepository, InMemoryCashAccountRepository,
        InMemorySalesRepository, InMemoryPurchaseReturnRepository,
        InMemoryReceivingRepository, InMemoryPurchaseRepository,
        InMemoryProductRepository, InMemoryUnitRepository,
        InMemoryBranchRepository, InMemoryCustomerRepository,
        InMemorySupplierRepository, InMemoryBusinessMembershipRepository,
        InMemoryBusinessRepository, InMemoryAccountRepository,
        InMemoryUserRepository, InMemoryWarehouseRepository,
        InMemoryInventoryLocationRepository, InMemoryStockBalanceRepository,
        InMemoryStockMovementRepository, InMemoryInventoryCostRepository,
        InMemoryPriceListRepository, InMemoryPriceEntryRepository,
    ]:
        repo.clear()


# ── Helpers ──────────────────────────────────────────────

def _reg(email="owner@example.com"):
    r = client.post("/api/v1/auth/register", json={"email": email, "full_name": "Owner", "password": "Password123", "password_confirmation": "Password123"})
    assert r.status_code == 201
    tok = r.json().get("access_token")
    if not tok:
        r2 = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123"})
        tok = r2.json()["access_token"]
    return tok


def _biz(tok, name="TestBiz"):
    r = client.post("/api/v1/businesses", headers={"Authorization": f"Bearer {tok}"}, json={"name": name, "business_type": "umkm", "timezone": "UTC", "locale": "en-US"})
    assert r.status_code == 201
    return r.json()["id"]


def _br(tok, biz):
    n = _inc()
    r = client.post(f"/api/v1/businesses/{biz}/branches", headers={"Authorization": f"Bearer {tok}"}, json={"name": f"Branch{n}", "code": f"BR{n}"})
    assert r.status_code == 201
    return r.json()["id"]


def _cu(tok, biz, name=None):
    n = _inc()
    r = client.post(f"/api/v1/businesses/{biz}/customers", headers={"Authorization": f"Bearer {tok}"}, json={"name": name or f"Customer{n}", "customer_type": "INDIVIDUAL"})
    assert r.status_code == 201
    return r.json()["id"]


def _sup(tok, biz, name=None):
    n = _inc()
    r = client.post(f"/api/v1/businesses/{biz}/suppliers", headers={"Authorization": f"Bearer {tok}"}, json={"name": name or f"Supplier{n}", "supplier_type": "ORGANIZATION"})
    assert r.status_code == 201
    return r.json()["id"]


def _u(tok, biz):
    n = _inc()
    r = client.post(f"/api/v1/businesses/{biz}/units", headers={"Authorization": f"Bearer {tok}"}, json={"name": f"Unit{n}", "code": f"U{n}", "symbol": "pcs", "unit_type": "OTHER"})
    assert r.status_code == 201
    return r.json()["id"]


def _p(tok, biz, uid):
    n = _inc()
    r = client.post(f"/api/v1/businesses/{biz}/products", headers={"Authorization": f"Bearer {tok}"}, json={"name": f"Prod{n}", "code": f"P{n}", "unit_id": uid, "product_type": "GOODS"})
    assert r.status_code == 201
    return r.json()["id"]


def _stock(tok, biz, pid):
    n = _inc()
    wh = client.post(f"/api/v1/businesses/{biz}/warehouses", headers={"Authorization": f"Bearer {tok}"}, json={"name": f"W{n}", "code": f"W{n}"}).json()["id"]
    loc = client.post(f"/api/v1/businesses/{biz}/warehouses/{wh}/locations", headers={"Authorization": f"Bearer {tok}"}, json={"name": f"L{n}", "code": f"L{n}", "location_type": "GENERAL"}).json()["id"]
    client.post(f"/api/v1/businesses/{biz}/inventory/opening-balance", headers={"Authorization": f"Bearer {tok}"}, json={"inventory_location_id": loc, "product_id": pid, "quantity": "10000"})
    return loc


def _cash(tok, biz, bal=100000):
    n = _inc()
    r = client.post(f"/api/v1/businesses/{biz}/cash-accounts", headers={"Authorization": f"Bearer {tok}"}, json={"name": f"Cash{n}", "code": f"C{n}", "account_type": "CASH", "currency": "IDR", "opening_balance": bal})
    assert r.status_code == 201
    return r.json()["id"]


def _cat(tok, biz, name=None, code=None):
    n = _inc()
    r = client.post(f"/api/v1/businesses/{biz}/categories", headers={"Authorization": f"Bearer {tok}"}, json={"name": name or f"Cat{n}", "code": code or f"C{n}"})
    assert r.status_code == 201
    return r.json()["id"]


def _product(tok, biz, name=None, code=None, cat_id=None):
    uid = _u(tok, biz)
    pid = _p(tok, biz, uid)
    return pid


def _make_sale(tok, biz, cu_id, br_id, pid, price="1000", qty="10", sale_date="2026-09-15T10:00:00Z"):
    s = client.post(f"/api/v1/businesses/{biz}/sales", headers={"Authorization": f"Bearer {tok}"}, json={"customer_id": cu_id, "branch_id": br_id, "sales_date": sale_date})
    assert s.status_code == 201
    sid = s.json()["id"]
    client.post(f"/api/v1/businesses/{biz}/sales/{sid}/lines", headers={"Authorization": f"Bearer {tok}"}, json={"product_id": pid, "quantity": qty, "unit_price": price})
    loc = _stock(tok, biz, pid)
    client.post(f"/api/v1/businesses/{biz}/sales/{sid}/finalize?inventory_location_id={loc}", headers={"Authorization": f"Bearer {tok}"})
    return sid


def _make_purchase(tok, biz, sup_id, br_id, pid, price="1000", qty="10"):
    pr = client.post(f"/api/v1/businesses/{biz}/purchases", headers={"Authorization": f"Bearer {tok}"}, json={"supplier_id": sup_id, "branch_id": br_id, "purchase_date": datetime.now(timezone.utc).isoformat()})
    assert pr.status_code == 201
    pur_id = pr.json()["id"]
    client.post(f"/api/v1/businesses/{biz}/purchases/{pur_id}/lines", headers={"Authorization": f"Bearer {tok}"}, json={"product_id": pid, "quantity": qty, "unit_price": price})
    loc = _stock(tok, biz, pid)
    client.post(f"/api/v1/businesses/{biz}/purchases/{pur_id}/finalize?inventory_location_id={loc}", headers={"Authorization": f"Bearer {tok}"})
    return pur_id


def _pay(tok, biz, direction, target_type, target_id, cash_id, amount="5000", method="CASH", payment_date="2026-09-15T12:00:00Z"):
    r = client.post(f"/api/v1/businesses/{biz}/payments", headers={"Authorization": f"Bearer {tok}"}, json={
        "direction": direction, "target_type": target_type, "target_id": target_id,
        "amount": amount, "currency": "IDR", "payment_method": method,
        "cash_account_id": cash_id, "payment_date": payment_date,
    })
    assert r.status_code == 201, f"Payment failed: {r.status_code} {r.text}"
    return r.json()["id"]


def _void(tok, biz, pid):
    r = client.post(f"/api/v1/businesses/{biz}/payments/{pid}/void", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    return r.json()["id"]


def _as(tok, biz, **kw):
    params = "?date_from=2026-09-01T00:00:00Z&date_to=2026-09-30T23:59:59Z"
    for k, v in kw.items():
        if v is not None:
            params += f"&{k}={v}"
    return client.get(f"/api/v1/businesses/{biz}/payments/analytics/summary{params}", headers={"Authorization": f"Bearer {tok}"})


def _ad(tok, biz, **kw):
    params = "?date_from=2026-09-01T00:00:00Z&date_to=2026-09-30T23:59:59Z"
    for k, v in kw.items():
        if v is not None:
            params += f"&{k}={v}"
    return client.get(f"/api/v1/businesses/{biz}/payments/analytics/by-direction{params}", headers={"Authorization": f"Bearer {tok}"})


def _am(tok, biz, **kw):
    params = "?date_from=2026-09-01T00:00:00Z&date_to=2026-09-30T23:59:59Z"
    for k, v in kw.items():
        if v is not None:
            params += f"&{k}={v}"
    return client.get(f"/api/v1/businesses/{biz}/payments/analytics/by-method{params}", headers={"Authorization": f"Bearer {tok}"})


# ── Helper: full payment setup ──────────────────────────
def _setup_full(tok, biz, direction="CUSTOMER_IN", method="CASH", amount="5000", payment_date="2026-09-15T12:00:00Z"):
    uid = _u(tok, biz)
    pid = _p(tok, biz, uid)
    br_id = _br(tok, biz)
    ca = _cash(tok, biz)
    if direction == "CUSTOMER_IN":
        cu = _cu(tok, biz)
        sid = _make_sale(tok, biz, cu, br_id, pid)
        pay_id = _pay(tok, biz, "CUSTOMER_IN", "SALES", sid, ca, amount=amount, method=method, payment_date=payment_date)
        return sid, pay_id
    else:
        su = _sup(tok, biz)
        purid = _make_purchase(tok, biz, su, br_id, pid)
        pay_id = _pay(tok, biz, "SUPPLIER_OUT", "PURCHASE", purid, ca, amount=amount, method=method, payment_date=payment_date)
        return purid, pay_id


class TestPaymentAnalytics:

    # ═══ INCLUSION / EXCLUSION ═══════════════════════════════

    # 1. recorded included
    def test_recorded_included(self):
        t = _reg(); b = _biz(t)
        _, pid = _setup_full(t, b)
        d = _as(t, b).json()
        assert Decimal(str(d["gross_recorded"])) > 0
        assert d["payment_count"] == 1

    # 2. voided excluded
    def test_voided_excluded(self):
        t = _reg(); b = _biz(t)
        _, pid = _setup_full(t, b)
        _void(t, b, pid)
        d = _as(t, b).json()
        assert Decimal(str(d["gross_recorded"])) == 0
        assert d["voided_count"] == 1
        assert Decimal(str(d["voided_amount"])) > 0

    # 3. multiple recorded
    def test_multiple_recorded(self):
        t = _reg(); b = _biz(t)
        _setup_full(t, b, amount="1000")
        _setup_full(t, b, amount="2000")
        d = _as(t, b).json()
        assert d["payment_count"] == 2
        assert Decimal(str(d["gross_recorded"])) == Decimal("3000")

    # 4. empty period
    def test_empty_period(self):
        t = _reg(); b = _biz(t)
        d = _as(t, b).json()
        assert Decimal(str(d["gross_recorded"])) == 0
        assert d["payment_count"] == 0

    # ═══ DATE BOUNDARIES ═══════════════════════════════════

    # 5. date_from boundary
    def test_date_from_boundary(self):
        t = _reg(); b = _biz(t)
        _setup_full(t, b, payment_date="2026-09-01T00:00:00Z")
        d = client.get(f"/api/v1/businesses/{b}/payments/analytics/summary?date_from=2026-09-01T00:00:00Z&date_to=2026-09-30T23:59:59Z", headers={"Authorization": f"Bearer {t}"}).json()
        assert d["payment_count"] == 1

    # 6. date_to boundary
    def test_date_to_boundary(self):
        t = _reg(); b = _biz(t)
        _setup_full(t, b, payment_date="2026-09-30T23:59:59Z")
        d = client.get(f"/api/v1/businesses/{b}/payments/analytics/summary?date_from=2026-09-01T00:00:00Z&date_to=2026-09-30T23:59:59Z", headers={"Authorization": f"Bearer {t}"}).json()
        assert d["payment_count"] == 1

    # 7. before excluded
    def test_before_excluded(self):
        t = _reg(); b = _biz(t)
        _setup_full(t, b, payment_date="2026-08-31T23:59:59Z")
        assert _as(t, b).json()["payment_count"] == 0

    # 8. after excluded
    def test_after_excluded(self):
        t = _reg(); b = _biz(t)
        _setup_full(t, b, payment_date="2026-10-01T00:00:00Z")
        assert _as(t, b).json()["payment_count"] == 0

    # 9. same-day range
    def test_same_day_range(self):
        t = _reg(); b = _biz(t)
        _setup_full(t, b, payment_date="2026-09-15T12:00:00Z")
        d = client.get(f"/api/v1/businesses/{b}/payments/analytics/summary?date_from=2026-09-15T00:00:00Z&date_to=2026-09-15T23:59:59Z", headers={"Authorization": f"Bearer {t}"}).json()
        assert d["payment_count"] == 1

    # 10. reversed range
    def test_reversed_range(self):
        t = _reg(); b = _biz(t)
        r = _as(t, b, date_from="2026-09-30T00:00:00Z", date_to="2026-09-01T00:00:00Z")
        assert r.status_code == 400

    # 11. missing date_from
    def test_missing_date_from(self):
        t = _reg(); b = _biz(t)
        r = client.get(f"/api/v1/businesses/{b}/payments/analytics/summary?date_to=2026-09-30T23:59:59Z", headers={"Authorization": f"Bearer {t}"})
        assert r.status_code == 422

    # 12. missing date_to
    def test_missing_date_to(self):
        t = _reg(); b = _biz(t)
        r = client.get(f"/api/v1/businesses/{b}/payments/analytics/summary?date_from=2026-09-01T00:00:00Z", headers={"Authorization": f"Bearer {t}"})
        assert r.status_code == 422

    # ═══ DIRECTION ═══════════════════════════════════════════

    # 13. customer_in
    def test_customer_in(self):
        t = _reg(); b = _biz(t)
        _setup_full(t, b, direction="CUSTOMER_IN", amount="5000")
        d = _as(t, b).json()
        assert Decimal(str(d["customer_in_total"])) == Decimal("5000")
        assert Decimal(str(d["supplier_out_total"])) == 0

    # 14. supplier_out
    def test_supplier_out(self):
        t = _reg(); b = _biz(t)
        _setup_full(t, b, direction="SUPPLIER_OUT", amount="3000")
        d = _as(t, b).json()
        assert Decimal(str(d["supplier_out_total"])) == Decimal("3000")
        assert Decimal(str(d["customer_in_total"])) == 0

    # 15. direction reconciliation
    def test_direction_reconciliation(self):
        t = _reg(); b = _biz(t)
        _setup_full(t, b, direction="CUSTOMER_IN", amount="5000")
        _setup_full(t, b, direction="SUPPLIER_OUT", amount="3000")
        d = _as(t, b).json()
        assert Decimal(str(d["gross_recorded"])) == Decimal(str(d["customer_in_total"])) + Decimal(str(d["supplier_out_total"]))

    # 16. direction reconciliation count
    def test_direction_count_reconciliation(self):
        t = _reg(); b = _biz(t)
        _setup_full(t, b, direction="CUSTOMER_IN", amount="1000")
        _setup_full(t, b, direction="SUPPLIER_OUT", amount="2000")
        d = _as(t, b).json()
        dd = _ad(t, b).json()
        dir_count = sum(di["payment_count"] for di in dd["directions"])
        assert dir_count == d["payment_count"]

    # ═══ METHOD ═════════════════════════════════════════════

    # 17. all 7 methods
    def test_all_7_methods(self):
        t = _reg(); b = _biz(t)
        for m in ["CASH", "BANK_TRANSFER", "DEBIT_CARD", "CREDIT_CARD", "QRIS", "E_WALLET", "OTHER"]:
            _setup_full(t, b, method=m, amount="1000")
        d = _as(t, b).json()
        assert d["payment_count"] == 7
        dm = _am(t, b).json()
        assert len(dm["methods"]) == 7

    # 18. method filter
    def test_method_filter(self):
        t = _reg(); b = _biz(t)
        _setup_full(t, b, method="CASH", amount="1000")
        _setup_full(t, b, method="BANK_TRANSFER", amount="2000")
        d = _as(t, b, payment_method="CASH").json()
        assert d["payment_count"] == 1
        assert Decimal(str(d["gross_recorded"])) == Decimal("1000")

    # 19. method reconciliation
    def test_method_reconciliation(self):
        t = _reg(); b = _biz(t)
        _setup_full(t, b, method="CASH", amount="1000")
        _setup_full(t, b, method="BANK_TRANSFER", amount="2000")
        d = _as(t, b).json()
        dm = _am(t, b).json()
        method_sum = sum(Decimal(str(m["amount"])) for m in dm["methods"])
        assert method_sum == Decimal(str(d["gross_recorded"]))

    # 20. method count reconciliation
    def test_method_count_reconciliation(self):
        t = _reg(); b = _biz(t)
        _setup_full(t, b, method="CASH", amount="1000")
        _setup_full(t, b, method="BANK_TRANSFER", amount="2000")
        d = _as(t, b).json()
        dm = _am(t, b).json()
        method_count = sum(m["payment_count"] for m in dm["methods"])
        assert method_count == d["payment_count"]

    # ═══ FILTERS ═══════════════════════════════════════════

    # 21. branch filter
    def test_branch_filter(self):
        t = _reg(); b = _biz(t)
        br1 = _br(t, b); br2 = _br(t, b)
        cu = _cu(t, b); uid = _u(t, b); pid = _p(t, b, uid)
        ca = _cash(t, b)
        sid1 = _make_sale(t, b, cu, br1, pid)
        _pay(t, b, "CUSTOMER_IN", "SALES", sid1, ca, payment_date="2026-09-15T12:00:00Z")
        sid2 = _make_sale(t, b, cu, br2, pid)
        _pay(t, b, "CUSTOMER_IN", "SALES", sid2, ca, payment_date="2026-09-15T12:00:00Z")
        d = _as(t, b, branch_id=br1).json()
        assert d["payment_count"] == 1

    # 22. direction filter
    def test_direction_filter(self):
        t = _reg(); b = _biz(t)
        _setup_full(t, b, direction="CUSTOMER_IN", amount="5000")
        _setup_full(t, b, direction="SUPPLIER_OUT", amount="3000")
        d = _as(t, b, direction="CUSTOMER_IN").json()
        assert d["payment_count"] == 1
        assert Decimal(str(d["gross_recorded"])) == Decimal("5000")

    # 23. combined filters
    def test_combined_filters(self):
        t = _reg(); b = _biz(t)
        _setup_full(t, b, direction="CUSTOMER_IN", method="CASH", amount="1000")
        _setup_full(t, b, direction="SUPPLIER_OUT", method="BANK_TRANSFER", amount="2000")
        d = _as(t, b, direction="CUSTOMER_IN", payment_method="CASH").json()
        assert d["payment_count"] == 1
        assert Decimal(str(d["gross_recorded"])) == Decimal("1000")

    # ═══ METRICS ═══════════════════════════════════════════

    # 24. payment count
    def test_payment_count(self):
        t = _reg(); b = _biz(t)
        _setup_full(t, b); _setup_full(t, b); _setup_full(t, b)
        assert _as(t, b).json()["payment_count"] == 3

    # 25. average payment
    def test_average_payment(self):
        t = _reg(); b = _biz(t)
        _setup_full(t, b, amount="1000")
        _setup_full(t, b, amount="2000")
        d = _as(t, b).json()
        assert Decimal(str(d["average_payment_value"])) == Decimal("1500")

    # 26. zero average
    def test_zero_average(self):
        t = _reg(); b = _biz(t)
        assert Decimal(str(_as(t, b).json()["average_payment_value"])) == 0

    # 27. net payment flow
    def test_net_payment_flow(self):
        t = _reg(); b = _biz(t)
        _setup_full(t, b, direction="CUSTOMER_IN", amount="10000")
        _setup_full(t, b, direction="SUPPLIER_OUT", amount="4000")
        d = _as(t, b).json()
        assert Decimal(str(d["net_payment_flow"])) == Decimal("6000")

    # 28. decimal precision
    def test_decimal_precision(self):
        t = _reg(); b = _biz(t)
        _setup_full(t, b, amount="5000.50")
        _setup_full(t, b, amount="4999.50")
        d = _as(t, b).json()
        assert "e" not in str(d["gross_recorded"]).lower()
        assert Decimal(str(d["gross_recorded"])) == Decimal("10000")

    # ═══ DETERMINISTIC ORDERING ═════════════════════════════

    # 29. direction ordering
    def test_direction_ordering(self):
        t = _reg(); b = _biz(t)
        _setup_full(t, b, direction="SUPPLIER_OUT", amount="5000")
        _setup_full(t, b, direction="CUSTOMER_IN", amount="10000")
        d = _ad(t, b).json()
        assert d["directions"][0]["direction"] == "CUSTOMER_IN"
        assert d["directions"][1]["direction"] == "SUPPLIER_OUT"

    # 30. method ordering
    def test_method_ordering(self):
        t = _reg(); b = _biz(t)
        _setup_full(t, b, method="CASH", amount="1000")
        _setup_full(t, b, method="BANK_TRANSFER", amount="5000")
        _setup_full(t, b, method="QRIS", amount="2000")
        d = _am(t, b).json()
        ms = d["methods"]
        assert ms[0]["payment_method"] == "BANK_TRANSFER"
        assert Decimal(str(ms[0]["amount"])) == Decimal("5000")
        assert ms[1]["payment_method"] == "QRIS"
        assert ms[2]["payment_method"] == "CASH"

    # ═══ PAYMENT DATE SEMANTICS ═════════════════════════════

    # 31. payment_date anchored, not created_at
    def test_payment_date_anchoring(self):
        t = _reg(); b = _biz(t)
        _setup_full(t, b, payment_date="2026-09-15T12:00:00Z")
        _setup_full(t, b, payment_date="2026-10-01T12:00:00Z")
        assert _as(t, b).json()["payment_count"] == 1
        assert client.get(f"/api/v1/businesses/{b}/payments/analytics/summary?date_from=2026-10-01T00:00:00Z&date_to=2026-10-31T23:59:59Z", headers={"Authorization": f"Bearer {t}"}).json()["payment_count"] == 1

    # ═══ SECURITY ═══════════════════════════════════════════

    # 32. unauthenticated
    def test_unauthenticated(self):
        r = client.get("/api/v1/businesses/x/payments/analytics/summary?date_from=2026-09-01T00:00:00Z&date_to=2026-09-30T23:59:59Z")
        assert r.status_code == 401

    # 33. cross-business
    def test_cross_business(self):
        t1 = _reg("a@e.com"); b1 = _biz(t1)
        t2 = _reg("b@e.com"); b2 = _biz(t2)
        _setup_full(t2, b2)
        assert _as(t1, b2).status_code == 404

    # 34. foreign branch
    def test_foreign_branch(self):
        t1 = _reg("a@e.com"); b1 = _biz(t1)
        t2 = _reg("b@e.com"); b2 = _biz(t2)
        br2 = _br(t2, b2)
        assert _as(t1, b1, branch_id=br2).status_code == 404

    # 35. cross-business branch
    def test_cross_business_branch(self):
        t1 = _reg("a@e.com"); b1 = _biz(t1)
        t2 = _reg("b@e.com"); b2 = _biz(t2)
        br1 = _br(t1, b1)
        assert _as(t2, b2, branch_id=br1).status_code == 404

    # 36. owner can read
    def test_owner_can_read(self):
        t = _reg(); b = _biz(t)
        assert _as(t, b).status_code == 200

    # 37. admin can read
    def test_admin_can_read(self):
        t1 = _reg(); b = _biz(t1)
        t2 = _reg("admin@e.com")
        uid = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {t2}"}).json()["id"]
        client.post(f"/api/v1/businesses/{b}/members", headers={"Authorization": f"Bearer {t1}"}, json={"user_id": uid, "role": "ADMIN"})
        _setup_full(t1, b)
        assert _as(t2, b).status_code == 200

    # 38. member can read
    def test_member_can_read(self):
        t1 = _reg(); b = _biz(t1)
        t2 = _reg("mem@e.com")
        uid = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {t2}"}).json()["id"]
        client.post(f"/api/v1/businesses/{b}/members", headers={"Authorization": f"Bearer {t1}"}, json={"user_id": uid, "role": "MEMBER"})
        _setup_full(t1, b)
        assert _as(t2, b).status_code == 200

    # ═══ RECONCILIATION INVARIANTS ═══════════════════════════

    # 39. direction sum matches
    def test_direction_sum_matches(self):
        t = _reg(); b = _biz(t)
        _setup_full(t, b, direction="CUSTOMER_IN", amount="3000")
        _setup_full(t, b, direction="SUPPLIER_OUT", amount="1000")
        sm = _as(t, b).json()
        dr = _ad(t, b).json()
        dir_sum = sum(Decimal(str(d["amount"])) for d in dr["directions"])
        assert dir_sum == Decimal(str(sm["gross_recorded"]))

    # 40. method sum matches
    def test_method_sum_matches(self):
        t = _reg(); b = _biz(t)
        _setup_full(t, b, method="CASH", amount="1000")
        _setup_full(t, b, method="BANK_TRANSFER", amount="2000")
        sm = _as(t, b).json()
        mm = _am(t, b).json()
        method_sum = sum(Decimal(str(m["amount"])) for m in mm["methods"])
        assert method_sum == Decimal(str(sm["gross_recorded"]))

    # 41. direction count matches
    def test_direction_count_matches(self):
        t = _reg(); b = _biz(t)
        _setup_full(t, b, direction="CUSTOMER_IN")
        _setup_full(t, b, direction="SUPPLIER_OUT")
        sm = _as(t, b).json()
        dr = _ad(t, b).json()
        dir_count = sum(d["payment_count"] for d in dr["directions"])
        assert dir_count == sm["payment_count"]

    # 42. method count matches
    def test_method_count_matches(self):
        t = _reg(); b = _biz(t)
        _setup_full(t, b, method="CASH")
        _setup_full(t, b, method="BANK_TRANSFER")
        sm = _as(t, b).json()
        mm = _am(t, b).json()
        method_count = sum(m["payment_count"] for m in mm["methods"])
        assert method_count == sm["payment_count"]

    # ═══ EMPTY STATES ═══════════════════════════════════════

    # 43. empty direction breakdown
    def test_empty_direction_breakdown(self):
        t = _reg(); b = _biz(t)
        d = _ad(t, b).json()
        assert d["directions"] == []
        assert d["gross_recorded"] == "0"

    # 44. empty method breakdown
    def test_empty_method_breakdown(self):
        t = _reg(); b = _biz(t)
        d = _am(t, b).json()
        assert d["methods"] == []
        assert d["gross_recorded"] == "0"

    # ═══ READ-ONLY ══════════════════════════════════════════

    # 45. idempotent reads
    def test_idempotent_reads(self):
        t = _reg(); b = _biz(t)
        _setup_full(t, b)
        d1 = _as(t, b).json()
        d2 = _as(t, b).json()
        assert d1 == d2

    # ═══ EDGE CASES ═════════════════════════════════════════

    # 46. large amount
    def test_large_amount(self):
        t = _reg(); b = _biz(t)
        # Create sale with large grand_total to allow large payment
        uid = _u(t, b)
        pid = _p(t, b, uid)
        br_id = _br(t, b)
        ca = _cash(t, b, bal=50000000)
        cu = _cu(t, b)
        sid = _make_sale(t, b, cu, br_id, pid, price="50000", qty="1000")
        _pay(t, b, "CUSTOMER_IN", "SALES", sid, ca, amount="10000000", payment_date="2026-09-15T12:00:00Z")
        d = _as(t, b).json()
        assert Decimal(str(d["gross_recorded"])) == Decimal("10000000")

    # 47. single method breakdown
    def test_single_method_breakdown(self):
        t = _reg(); b = _biz(t)
        _setup_full(t, b, method="CASH", amount="1000")
        dm = _am(t, b).json()
        assert len(dm["methods"]) == 1
        assert dm["methods"][0]["payment_method"] == "CASH"
        assert dm["methods"][0]["payment_count"] == 1
        assert Decimal(str(dm["methods"][0]["amount"])) == Decimal("1000")

    # 48. single direction breakdown
    def test_single_direction_breakdown(self):
        t = _reg(); b = _biz(t)
        _setup_full(t, b, direction="CUSTOMER_IN", amount="1000")
        dd = _ad(t, b).json()
        assert len(dd["directions"]) == 1
        assert dd["directions"][0]["direction"] == "CUSTOMER_IN"

    # 49. voided reported as operational only
    def test_voided_operational_stats(self):
        t = _reg(); b = _biz(t)
        _, pid1 = _setup_full(t, b, amount="1000")
        _, pid2 = _setup_full(t, b, amount="2000")
        _void(t, b, pid1)
        d = _as(t, b).json()
        assert Decimal(str(d["gross_recorded"])) == Decimal("2000")
        assert d["payment_count"] == 1
        assert d["voided_count"] == 1
        assert Decimal(str(d["voided_amount"])) == Decimal("1000")

    # 50. combined by-direction and by-method consistency
    def test_direction_method_consistency(self):
        t = _reg(); b = _biz(t)
        _setup_full(t, b, direction="CUSTOMER_IN", method="CASH", amount="1000")
        _setup_full(t, b, direction="SUPPLIER_OUT", method="BANK_TRANSFER", amount="2000")
        sm = _as(t, b).json()
        dd = _ad(t, b).json()
        mm = _am(t, b).json()
        # Both direction and method sums must match summary
        assert sum(Decimal(str(d["amount"])) for d in dd["directions"]) == Decimal(str(sm["gross_recorded"]))
        assert sum(Decimal(str(m["amount"])) for m in mm["methods"]) == Decimal(str(sm["gross_recorded"]))
        # Both count to summary count
        assert sum(d["payment_count"] for d in dd["directions"]) == sm["payment_count"]
        assert sum(m["payment_count"] for m in mm["methods"]) == sm["payment_count"]

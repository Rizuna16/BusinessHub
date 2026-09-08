import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from urllib.parse import quote
from fastapi.testclient import TestClient

from app.main import app
from app.modules.authentication.repository import InMemoryUserRepository
from app.modules.account.repository import InMemoryAccountRepository
from app.modules.business.repository import InMemoryBusinessRepository
from app.modules.business_membership.repository import InMemoryBusinessMembershipRepository
from app.modules.customer.repository import InMemoryCustomerRepository
from app.modules.supplier.repository import InMemorySupplierRepository
from app.modules.branch.repository import InMemoryBranchRepository
from app.modules.unit.repository import InMemoryUnitRepository
from app.modules.product.repository import InMemoryProductRepository
from app.modules.sales.repository import InMemorySalesRepository
from app.modules.sales_payment.repository import InMemorySalesPaymentRepository
from app.modules.sales_return.repository import InMemorySalesReturnRepository
from app.modules.purchase.repository import InMemoryPurchaseRepository
from app.modules.purchase_return.repository import InMemoryPurchaseReturnRepository
from app.modules.payment.repository import InMemoryPaymentRepository
from app.modules.cash_account.repository import InMemoryCashAccountRepository
from app.modules.warehouse.repository import InMemoryWarehouseRepository, InMemoryInventoryLocationRepository
from app.modules.inventory.repository import InMemoryStockBalanceRepository, InMemoryStockMovementRepository, InMemoryInventoryCostRepository

client = TestClient(app)


def dt_iso(dt):
    return quote(dt.isoformat())


@pytest.fixture(autouse=True)
def clear_repositories():
    InMemorySalesReturnRepository.clear()
    InMemorySalesPaymentRepository.clear()
    InMemorySalesRepository.clear()
    InMemoryPurchaseReturnRepository.clear()
    InMemoryPurchaseRepository.clear()
    InMemoryPaymentRepository.clear()
    InMemoryCashAccountRepository.clear()
    InMemoryStockBalanceRepository.clear()
    InMemoryStockMovementRepository.clear()
    InMemoryInventoryCostRepository.clear()
    InMemoryInventoryLocationRepository.clear()
    InMemoryWarehouseRepository.clear()
    InMemoryProductRepository.clear()
    InMemoryUnitRepository.clear()
    InMemoryBranchRepository.clear()
    InMemorySupplierRepository.clear()
    InMemoryCustomerRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryUserRepository.clear()
    yield
    InMemorySalesReturnRepository.clear()
    InMemorySalesPaymentRepository.clear()
    InMemorySalesRepository.clear()
    InMemoryPurchaseReturnRepository.clear()
    InMemoryPurchaseRepository.clear()
    InMemoryPaymentRepository.clear()
    InMemoryCashAccountRepository.clear()
    InMemoryStockBalanceRepository.clear()
    InMemoryStockMovementRepository.clear()
    InMemoryInventoryCostRepository.clear()
    InMemoryInventoryLocationRepository.clear()
    InMemoryWarehouseRepository.clear()
    InMemoryProductRepository.clear()
    InMemoryUnitRepository.clear()
    InMemoryBranchRepository.clear()
    InMemorySupplierRepository.clear()
    InMemoryCustomerRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryUserRepository.clear()


def register_user(email="owner@example.com", name="Owner Test"):
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": name,
            "password": "Password123",
            "password_confirmation": "Password123",
        },
    )
    assert res.status_code == 201
    data = res.json()
    token = data.get("access_token")
    if not token:
        login_res = client.post(
            "/api/v1/auth/login", json={"email": email, "password": "Password123"}
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
    return token, data["id"]


def create_business(token, name="Test Business"):
    res = client.post(
        "/api/v1/businesses",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": name,
            "legal_name": name,
            "business_type": "retail",
            "timezone": "UTC",
            "locale": "en-US",
        },
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


def create_customer(token, business_id, name="Customer A"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/customers",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "customer_type": "INDIVIDUAL"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_supplier(token, business_id, name="Supplier A"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/suppliers",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "supplier_type": "ORGANIZATION"},
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


def create_product(token, business_id, unit_id, name="Product A", code="PROD-A", p_type="GOODS"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/products",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code, "unit_id": unit_id, "product_type": p_type},
    )
    assert res.status_code == 201
    return res.json()["id"]


def setup_warehouse_and_location(token, business_id, name="WH 1", code="WH-1", loc_name="LOC 1", loc_code="L1"):
    wh_res = client.post(
        f"/api/v1/businesses/{business_id}/warehouses",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code},
    )
    assert wh_res.status_code == 201
    wh_id = wh_res.json()["id"]

    loc_res = client.post(
        f"/api/v1/businesses/{business_id}/warehouses/{wh_id}/locations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": loc_name, "code": loc_code, "location_type": "GENERAL"},
    )
    assert loc_res.status_code == 201
    return loc_res.json()["id"]


def add_opening_stock(token, business_id, location_id, product_id, qty="100"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/inventory/opening-balance",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "inventory_location_id": location_id,
            "product_id": product_id,
            "quantity": qty,
        },
    )
    assert res.status_code == 201


def create_cash_account(token, business_id, name="Main Cash", opening_balance=50000000):
    import uuid
    code = f"CASH-{uuid.uuid4().hex[:8].upper()}"
    res = client.post(
        f"/api/v1/businesses/{business_id}/cash-accounts",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": name,
            "code": code,
            "account_type": "CASH",
            "currency": "IDR",
            "opening_balance": opening_balance,
        },
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_finalized_sales(token, business_id, br_id, prod_id, customer_id=None, qty="10", price="100000", sales_date=None):
    s_date = sales_date or datetime.now(timezone.utc).isoformat()
    s_res = client.post(
        f"/api/v1/businesses/{business_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "branch_id": br_id,
            "customer_id": customer_id,
            "sales_date": s_date,
        },
    )
    assert s_res.status_code == 201
    sales_id = s_res.json()["id"]

    l_res = client.post(
        f"/api/v1/businesses/{business_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_id, "quantity": qty, "unit_price": price},
    )
    assert l_res.status_code == 201

    fin_res = client.post(
        f"/api/v1/businesses/{business_id}/sales/{sales_id}/finalize",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fin_res.status_code == 200
    return sales_id


def create_finalized_purchase(token, business_id, br_id, prod_id, supplier_id, qty="10", price="100000", purchase_date=None):
    p_date = purchase_date or datetime.now(timezone.utc).isoformat()
    p_res = client.post(
        f"/api/v1/businesses/{business_id}/purchases",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "branch_id": br_id,
            "supplier_id": supplier_id,
            "purchase_date": p_date,
        },
    )
    assert p_res.status_code == 201
    purchase_id = p_res.json()["id"]

    l_res = client.post(
        f"/api/v1/businesses/{business_id}/purchases/{purchase_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_id, "quantity": qty, "unit_price": price},
    )
    assert l_res.status_code == 201

    fin_res = client.post(
        f"/api/v1/businesses/{business_id}/purchases/{purchase_id}/finalize",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fin_res.status_code == 200
    return purchase_id


def record_payment(token, business_id, target_type, target_id, amount="500000", direction="CUSTOMER_IN", cash_account_id=None, payment_date=None):
    if cash_account_id is None:
        cash_account_id = create_cash_account(token, business_id)

    payload = {
        "direction": direction,
        "target_type": target_type,
        "target_id": target_id,
        "amount": amount,
        "currency": "IDR",
        "payment_method": "CASH",
        "cash_account_id": cash_account_id,
    }
    if payment_date:
        payload["payment_date"] = payment_date

    p_res = client.post(
        f"/api/v1/businesses/{business_id}/payments",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert p_res.status_code == 201
    return p_res.json()["id"]


def create_finalized_receiving(token, business_id, purchase_id, location_id, qty="10"):
    rcv_res = client.post(
        f"/api/v1/businesses/{business_id}/receivings",
        headers={"Authorization": f"Bearer {token}"},
        json={"purchase_id": purchase_id, "inventory_location_id": location_id},
    )
    assert rcv_res.status_code == 201
    rcv_id = rcv_res.json()["id"]

    p_line = client.get(
        f"/api/v1/businesses/{business_id}/purchases/{purchase_id}",
        headers={"Authorization": f"Bearer {token}"},
    ).json()["lines"][0]["id"]

    client.post(
        f"/api/v1/businesses/{business_id}/receivings/{rcv_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"purchase_line_id": p_line, "quantity": qty},
    )
    client.post(
        f"/api/v1/businesses/{business_id}/receivings/{rcv_id}/finalize",
        headers={"Authorization": f"Bearer {token}"},
    )
    return rcv_id


class TestARAgingFeature:

    # 1. Unpaid invoice
    def test_unpaid_ar_aging(self):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)
        cust_id = create_customer(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        add_opening_stock(token, biz_id, loc_id, prod_id)

        now = datetime.now(timezone.utc)
        sales_id = create_finalized_sales(token, biz_id, br_id, prod_id, customer_id=cust_id, qty="10", price="100000", sales_date=now.isoformat())

        res = client.get(
            f"/api/v1/businesses/{biz_id}/receivables/aging?as_of_date={dt_iso(now)}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["summary"]["total_outstanding"] == "1000000"
        assert data["summary"]["current"] == "1000000"
        assert len(data["invoices"]) == 1
        assert data["invoices"][0]["aging_bucket"] == "CURRENT"
        assert data["invoices"][0]["aging_days"] == 0

    # 2. Fully paid invoice excluded
    def test_fully_paid_ar_aging_excluded(self):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)
        cust_id = create_customer(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        add_opening_stock(token, biz_id, loc_id, prod_id)

        now = datetime.now(timezone.utc)
        sales_id = create_finalized_sales(token, biz_id, br_id, prod_id, customer_id=cust_id, qty="10", price="100000", sales_date=now.isoformat())
        record_payment(token, biz_id, "SALES", sales_id, amount="1000000", direction="CUSTOMER_IN", payment_date=now.isoformat())

        res = client.get(
            f"/api/v1/businesses/{biz_id}/receivables/aging?as_of_date={dt_iso(now)}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["summary"]["total_outstanding"] == "0"
        assert len(data["invoices"]) == 0

    # 3. Partial payment
    def test_partially_paid_ar_aging(self):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)
        cust_id = create_customer(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        add_opening_stock(token, biz_id, loc_id, prod_id)

        now = datetime.now(timezone.utc)
        sales_id = create_finalized_sales(token, biz_id, br_id, prod_id, customer_id=cust_id, qty="10", price="100000", sales_date=now.isoformat())
        record_payment(token, biz_id, "SALES", sales_id, amount="400000", direction="CUSTOMER_IN", payment_date=now.isoformat())

        res = client.get(
            f"/api/v1/businesses/{biz_id}/receivables/aging?as_of_date={dt_iso(now)}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["summary"]["total_outstanding"] == "600000"
        assert data["invoices"][0]["outstanding_amount"] == "600000"
        assert data["invoices"][0]["paid_amount"] == "400000"

    # 4. Voided payment excluded
    def test_voided_payment_excluded_from_ar_aging(self):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)
        cust_id = create_customer(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        add_opening_stock(token, biz_id, loc_id, prod_id)

        now = datetime.now(timezone.utc)
        sales_id = create_finalized_sales(token, biz_id, br_id, prod_id, customer_id=cust_id, qty="10", price="100000", sales_date=now.isoformat())
        pay_id = record_payment(token, biz_id, "SALES", sales_id, amount="1000000", direction="CUSTOMER_IN")

        # Void the payment
        client.post(f"/api/v1/businesses/{biz_id}/payments/{pay_id}/void", headers={"Authorization": f"Bearer {token}"})

        res = client.get(
            f"/api/v1/businesses/{biz_id}/receivables/aging?as_of_date={dt_iso(now)}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["summary"]["total_outstanding"] == "1000000"
        assert data["invoices"][0]["paid_amount"] == "0"

    # 5. Sales return reduces aging
    def test_sales_return_reduces_ar_aging(self):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)
        cust_id = create_customer(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        add_opening_stock(token, biz_id, loc_id, prod_id)

        base_date = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        sales_id = create_finalized_sales(token, biz_id, br_id, prod_id, customer_id=cust_id, qty="10", price="100000", sales_date=base_date.isoformat())
        sline_id = client.get(f"/api/v1/businesses/{biz_id}/sales/{sales_id}", headers={"Authorization": f"Bearer {token}"}).json()["lines"][0]["id"]

        # Sales Return
        ret_id = client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_id": sales_id, "inventory_location_id": loc_id},
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns/{ret_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_line_id": sline_id, "quantity": "3"},
        )
        client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns/{ret_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )

        as_of = datetime.now(timezone.utc) + timedelta(minutes=1)
        res = client.get(
            f"/api/v1/businesses/{biz_id}/receivables/aging?as_of_date={dt_iso(as_of)}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert Decimal(data["summary"]["total_outstanding"]) == Decimal("700000")
        assert Decimal(data["invoices"][0]["return_adjustment"]) == Decimal("300000")

    # 6 & 7. Future payment / return excluded from historical report
    def test_future_events_excluded_from_historical_ar_report(self):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)
        cust_id = create_customer(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        add_opening_stock(token, biz_id, loc_id, prod_id)

        base_date = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        future_date = datetime(2026, 1, 10, 10, 0, 0, tzinfo=timezone.utc)

        sales_id = create_finalized_sales(token, biz_id, br_id, prod_id, customer_id=cust_id, qty="10", price="100000", sales_date=base_date.isoformat())

        # Future payment
        record_payment(token, biz_id, "SALES", sales_id, amount="500000", direction="CUSTOMER_IN", payment_date=future_date.isoformat())

        # Check as-of base_date (future payment should be excluded!)
        res = client.get(
            f"/api/v1/businesses/{biz_id}/receivables/aging?as_of_date={dt_iso(base_date)}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["summary"]["total_outstanding"] == "1000000"
        assert data["invoices"][0]["paid_amount"] == "0"

        # Check as-of future_date (future payment included!)
        res_fut = client.get(
            f"/api/v1/businesses/{biz_id}/receivables/aging?as_of_date={dt_iso(future_date)}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_fut.status_code == 200
        data_fut = res_fut.json()
        assert data_fut["summary"]["total_outstanding"] == "500000"
        assert data_fut["invoices"][0]["paid_amount"] == "500000"

    # 8 & 9. Draft & cancelled sales excluded
    def test_draft_and_cancelled_sales_excluded_from_ar_aging(self):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)

        # Draft sale
        client.post(
            f"/api/v1/businesses/{biz_id}/sales",
            headers={"Authorization": f"Bearer {token}"},
            json={"branch_id": br_id, "sales_date": datetime.now(timezone.utc).isoformat()},
        )

        # Cancelled sale
        s_canc = client.post(
            f"/api/v1/businesses/{biz_id}/sales",
            headers={"Authorization": f"Bearer {token}"},
            json={"branch_id": br_id, "sales_date": datetime.now(timezone.utc).isoformat()},
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/sales/{s_canc}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )

        res = client.get(
            f"/api/v1/businesses/{biz_id}/receivables/aging",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert res.json()["summary"]["total_outstanding"] == "0"
        assert len(res.json()["invoices"]) == 0

    # 10 & 11. Walk-in sale and Customer aggregation
    def test_walkin_and_customer_aggregation(self):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)
        cust_id = create_customer(token, biz_id, name="Cust Alpha")
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        add_opening_stock(token, biz_id, loc_id, prod_id)

        now = datetime.now(timezone.utc)
        # Cust sale
        s1 = create_finalized_sales(token, biz_id, br_id, prod_id, customer_id=cust_id, qty="5", price="100000", sales_date=now.isoformat())
        # Walk-in sale
        s2 = create_finalized_sales(token, biz_id, br_id, prod_id, customer_id=None, qty="2", price="100000", sales_date=now.isoformat())

        res = client.get(
            f"/api/v1/businesses/{biz_id}/receivables/aging?as_of_date={dt_iso(now)}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["summary"]["total_outstanding"] == "700000"
        assert len(data["customers"]) == 2

        alpha_c = next(c for c in data["customers"] if c["customer_id"] == cust_id)
        assert alpha_c["total_outstanding"] == "500000"

        walkin_c = next(c for c in data["customers"] if c["customer_id"] is None)
        assert walkin_c["customer_name"] == "Walk-in Customer"
        assert walkin_c["total_outstanding"] == "200000"

    # 13–26. Bucket boundaries testing for AR (0, 1, 30, 31, 60, 61, 90, 91, 120, 121)
    @pytest.mark.parametrize(
        "days_old,expected_bucket",
        [
            (0, "CURRENT"),
            (1, "1_30"),
            (30, "1_30"),
            (31, "31_60"),
            (60, "31_60"),
            (61, "61_90"),
            (90, "61_90"),
            (91, "91_120"),
            (120, "91_120"),
            (121, "OVER_120"),
        ],
    )
    def test_ar_aging_bucket_boundaries(self, days_old, expected_bucket):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        add_opening_stock(token, biz_id, loc_id, prod_id)

        as_of = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        sales_date = as_of - timedelta(days=days_old)

        s_id = create_finalized_sales(token, biz_id, br_id, prod_id, qty="1", price="100000", sales_date=sales_date.isoformat())

        res = client.get(
            f"/api/v1/businesses/{biz_id}/receivables/aging?as_of_date={dt_iso(as_of)}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data["invoices"]) == 1
        inv = data["invoices"][0]
        assert inv["aging_days"] == days_old
        assert inv["aging_bucket"] == expected_bucket

    # 28-32. Filters, RBAC, Cross-business IDOR
    def test_ar_aging_filters_rbac_and_cross_business(self):
        token1, _ = register_user(email="owner1@example.com")
        biz1 = create_business(token1, name="Biz 1")
        br1 = create_branch(token1, biz1)
        cust1 = create_customer(token1, biz1, name="Cust 1")
        unit1 = create_unit(token1, biz1)
        prod1 = create_product(token1, biz1, unit1)
        loc1 = setup_warehouse_and_location(token1, biz1)
        add_opening_stock(token1, biz1, loc1, prod1)

        token2, _ = register_user(email="owner2@example.com")
        biz2 = create_business(token2, name="Biz 2")

        as_of = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        s1 = create_finalized_sales(token1, biz1, br1, prod1, customer_id=cust1, qty="1", price="100000", sales_date=as_of.isoformat())

        # Customer filter match
        res_cust = client.get(
            f"/api/v1/businesses/{biz1}/receivables/aging?customer_id={cust1}",
            headers={"Authorization": f"Bearer {token1}"},
        )
        assert res_cust.status_code == 200
        assert len(res_cust.json()["invoices"]) == 1

        # Foreign customer ID rejected (404)
        res_foreign_cust = client.get(
            f"/api/v1/businesses/{biz2}/receivables/aging?customer_id={cust1}",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert res_foreign_cust.status_code == 404

        # Cross business IDOR rejected
        res_cross = client.get(
            f"/api/v1/businesses/{biz1}/receivables/aging",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert res_cross.status_code in (403, 404)


class TestAPAgingFeature:

    # 1. Unpaid purchase
    def test_unpaid_ap_aging(self):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)
        sup_id = create_supplier(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)

        now = datetime.now(timezone.utc)
        pur_id = create_finalized_purchase(token, biz_id, br_id, prod_id, supplier_id=sup_id, qty="10", price="100000", purchase_date=now.isoformat())

        res = client.get(
            f"/api/v1/businesses/{biz_id}/purchases/payables/aging?as_of_date={dt_iso(now)}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["summary"]["total_outstanding"] == "1000000"
        assert data["summary"]["current"] == "1000000"
        assert len(data["purchases"]) == 1
        assert data["purchases"][0]["aging_bucket"] == "CURRENT"
        assert data["purchases"][0]["aging_days"] == 0

    # 2. Fully paid purchase excluded
    def test_fully_paid_ap_aging_excluded(self):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)
        sup_id = create_supplier(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)

        now = datetime.now(timezone.utc)
        pur_id = create_finalized_purchase(token, biz_id, br_id, prod_id, supplier_id=sup_id, qty="10", price="100000", purchase_date=now.isoformat())
        record_payment(token, biz_id, "PURCHASE", pur_id, amount="1000000", direction="SUPPLIER_OUT", payment_date=now.isoformat())

        res = client.get(
            f"/api/v1/businesses/{biz_id}/purchases/payables/aging?as_of_date={dt_iso(now)}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["summary"]["total_outstanding"] == "0"
        assert len(data["purchases"]) == 0

    # 3. Partial payment
    def test_partially_paid_ap_aging(self):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)
        sup_id = create_supplier(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)

        now = datetime.now(timezone.utc)
        pur_id = create_finalized_purchase(token, biz_id, br_id, prod_id, supplier_id=sup_id, qty="10", price="100000", purchase_date=now.isoformat())
        record_payment(token, biz_id, "PURCHASE", pur_id, amount="400000", direction="SUPPLIER_OUT", payment_date=now.isoformat())

        res = client.get(
            f"/api/v1/businesses/{biz_id}/purchases/payables/aging?as_of_date={dt_iso(now)}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["summary"]["total_outstanding"] == "600000"
        assert data["purchases"][0]["outstanding_amount"] == "600000"
        assert data["purchases"][0]["paid_amount"] == "400000"

    # 4. Voided payment excluded
    def test_voided_payment_excluded_from_ap_aging(self):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)
        sup_id = create_supplier(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)

        now = datetime.now(timezone.utc)
        pur_id = create_finalized_purchase(token, biz_id, br_id, prod_id, supplier_id=sup_id, qty="10", price="100000", purchase_date=now.isoformat())
        pay_id = record_payment(token, biz_id, "PURCHASE", pur_id, amount="1000000", direction="SUPPLIER_OUT", payment_date=now.isoformat())

        # Void the payment
        client.post(f"/api/v1/businesses/{biz_id}/payments/{pay_id}/void", headers={"Authorization": f"Bearer {token}"})

        res = client.get(
            f"/api/v1/businesses/{biz_id}/purchases/payables/aging?as_of_date={dt_iso(now)}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["summary"]["total_outstanding"] == "1000000"
        assert data["purchases"][0]["paid_amount"] == "0"

    # 5. Purchase return reduces AP aging
    def test_purchase_return_reduces_ap_aging(self):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)
        sup_id = create_supplier(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token, biz_id)

        base_date = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        pur_id = create_finalized_purchase(token, biz_id, br_id, prod_id, supplier_id=sup_id, qty="10", price="100000", purchase_date=base_date.isoformat())

        # Create receiving first (required for purchase returns)
        create_finalized_receiving(token, biz_id, pur_id, loc_id, qty="10")

        pline_id = client.get(f"/api/v1/businesses/{biz_id}/purchases/{pur_id}", headers={"Authorization": f"Bearer {token}"}).json()["lines"][0]["id"]

        # Purchase Return
        ret_id = client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_id": pur_id, "inventory_location_id": loc_id},
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns/{ret_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"purchase_line_id": pline_id, "quantity": "4", "unit_price": "100000"},
        )
        client.post(
            f"/api/v1/businesses/{biz_id}/purchase-returns/{ret_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )

        as_of = datetime.now(timezone.utc) + timedelta(minutes=1)
        res = client.get(
            f"/api/v1/businesses/{biz_id}/purchases/payables/aging?as_of_date={dt_iso(as_of)}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert Decimal(data["summary"]["total_outstanding"]) == Decimal("600000")
        assert Decimal(data["purchases"][0]["return_adjustment"]) == Decimal("400000")

    # 12. Bucket boundaries testing for AP (0, 1, 30, 31, 60, 61, 90, 91, 120, 121)
    @pytest.mark.parametrize(
        "days_old,expected_bucket",
        [
            (0, "CURRENT"),
            (1, "1_30"),
            (30, "1_30"),
            (31, "31_60"),
            (60, "31_60"),
            (61, "61_90"),
            (90, "61_90"),
            (91, "91_120"),
            (120, "91_120"),
            (121, "OVER_120"),
        ],
    )
    def test_ap_aging_bucket_boundaries(self, days_old, expected_bucket):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)
        sup_id = create_supplier(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)

        as_of = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        purchase_date = as_of - timedelta(days=days_old)

        pur_id = create_finalized_purchase(token, biz_id, br_id, prod_id, supplier_id=sup_id, qty="1", price="100000", purchase_date=purchase_date.isoformat())

        res = client.get(
            f"/api/v1/businesses/{biz_id}/purchases/payables/aging?as_of_date={dt_iso(as_of)}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data["purchases"]) == 1
        pur = data["purchases"][0]
        assert pur["aging_days"] == days_old
        assert pur["aging_bucket"] == expected_bucket

    # Invariants test
    def test_aging_summary_and_aggregation_invariants(self):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)
        cust_id = create_customer(token, biz_id, name="Cust Inv")
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        add_opening_stock(token, biz_id, loc_id, prod_id)

        as_of = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

        # 3 sales at different dates
        s1 = create_finalized_sales(token, biz_id, br_id, prod_id, customer_id=cust_id, qty="1", price="100000", sales_date=(as_of - timedelta(days=5)).isoformat())
        s2 = create_finalized_sales(token, biz_id, br_id, prod_id, customer_id=cust_id, qty="2", price="100000", sales_date=(as_of - timedelta(days=45)).isoformat())
        s3 = create_finalized_sales(token, biz_id, br_id, prod_id, customer_id=None, qty="3", price="100000", sales_date=(as_of - timedelta(days=100)).isoformat())

        res = client.get(
            f"/api/v1/businesses/{biz_id}/receivables/aging?as_of_date={dt_iso(as_of)}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        summary = data["summary"]

        # Invariant 1: total_outstanding == sum of bucket totals
        bucket_sum = (
            Decimal(summary["current"])
            + Decimal(summary["bucket_1_30"])
            + Decimal(summary["bucket_31_60"])
            + Decimal(summary["bucket_61_90"])
            + Decimal(summary["bucket_91_120"])
            + Decimal(summary["bucket_over_120"])
        )
        assert Decimal(summary["total_outstanding"]) == bucket_sum

        # Invariant 2: sum of invoice outstanding == total_outstanding
        invoice_sum = sum(Decimal(i["outstanding_amount"]) for i in data["invoices"])
        assert invoice_sum == Decimal(summary["total_outstanding"])

        # Invariant 3: sum of customer totals == total_outstanding
        customer_sum = sum(Decimal(c["total_outstanding"]) for c in data["customers"])
        assert customer_sum == Decimal(summary["total_outstanding"])

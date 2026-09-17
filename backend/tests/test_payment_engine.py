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
from app.modules.product_variant.repository import InMemoryProductVariantRepository
from app.modules.purchase.repository import InMemoryPurchaseRepository
from app.modules.receiving.repository import InMemoryReceivingRepository
from app.modules.purchase_return.repository import InMemoryPurchaseReturnRepository
from app.modules.sales.repository import InMemorySalesRepository
from app.modules.cash_account.repository import InMemoryCashAccountRepository
from app.modules.payment.repository import InMemoryPaymentRepository
from app.modules.cashier_shift.repository import InMemoryCashierShiftRepository

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_repositories():
    InMemoryPaymentRepository.clear()
    InMemoryCashAccountRepository.clear()
    InMemorySalesRepository.clear()
    InMemoryPurchaseReturnRepository.clear()
    InMemoryReceivingRepository.clear()
    InMemoryPurchaseRepository.clear()
    InMemoryProductVariantRepository.clear()
    InMemoryProductRepository.clear()
    InMemoryUnitRepository.clear()
    InMemoryBranchRepository.clear()
    InMemoryCustomerRepository.clear()
    InMemorySupplierRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryUserRepository.clear()
    InMemoryCashierShiftRepository.clear()
    yield
    InMemoryPaymentRepository.clear()
    InMemoryCashAccountRepository.clear()
    InMemorySalesRepository.clear()
    InMemoryPurchaseReturnRepository.clear()
    InMemoryReceivingRepository.clear()
    InMemoryPurchaseRepository.clear()
    InMemoryProductVariantRepository.clear()
    InMemoryProductRepository.clear()
    InMemoryUnitRepository.clear()
    InMemoryBranchRepository.clear()
    InMemoryCustomerRepository.clear()
    InMemorySupplierRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryUserRepository.clear()
    InMemoryCashierShiftRepository.clear()


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


def create_supplier(token, business_id, name="Supplier A"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/suppliers",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "supplier_type": "ORGANIZATION"},
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


def create_branch(token, business_id, name="Branch A", code="BR-A"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/branches",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code},
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


def create_product(token, business_id, unit_id, name="Product A", code="PROD-A"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/products",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code, "unit_id": unit_id, "product_type": "GOODS"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_warehouse(token, business_id, name="Warehouse A", code="WH-A"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/warehouses",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code},
    )
    assert res.status_code == 201
    wh_id = res.json()["id"]
    loc_res = client.post(
        f"/api/v1/businesses/{business_id}/warehouses/{wh_id}/locations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": f"Loc {name}", "code": f"LOC-{code}"},
    )
    assert loc_res.status_code == 201
    return wh_id, loc_res.json()["id"]


def create_cash_account(token, business_id, name="Main Cash", code="CASH-1", opening_balance=50000, currency="IDR"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/cash-accounts",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": name,
            "code": code,
            "account_type": "CASH",
            "currency": currency,
            "opening_balance": opening_balance,
        },
    )
    assert res.status_code == 201
    return res.json()["id"]


def setup_finalized_sales(token, biz_id, cust_id, br_id, prod_id, price=1000, qty=10):
    loc_id = setup_warehouse_and_location(token, biz_id)
    add_opening_stock(token, biz_id, loc_id, prod_id, qty="1000")

    client.put(
        f"/api/v1/businesses/{biz_id}/customers/{cust_id}/credit/limit",
        headers={"Authorization": f"Bearer {token}"},
        json={"credit_limit": "999999999.00"},
    )

    s_res = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "customer_id": cust_id,
            "branch_id": br_id,
            "sales_date": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert s_res.status_code == 201
    sales_id = s_res.json()["id"]

    client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_id, "quantity": qty, "unit_price": price},
    )

    fin_res = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fin_res.status_code == 200
    return sales_id


def setup_finalized_sales_draft(token, biz_id, cust_id, br_id, prod_id, price=1000, qty=10):
    loc_id = setup_warehouse_and_location(token, biz_id)
    add_opening_stock(token, biz_id, loc_id, prod_id, qty="1000")

    s_res = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "customer_id": cust_id,
            "branch_id": br_id,
            "sales_date": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert s_res.status_code == 201
    sales_id = s_res.json()["id"]

    client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_id, "quantity": qty, "unit_price": price},
    )
    return sales_id # DRAFT sales


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


def add_opening_stock(token, business_id, location_id, product_id, variant_id=None, qty="100"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/inventory/opening-balance",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "inventory_location_id": location_id,
            "product_id": product_id,
            "variant_id": variant_id,
            "quantity": qty,
        },
    )
    assert res.status_code == 201


def setup_finalized_purchase(token, biz_id, sup_id, br_id, prod_id, price=1000, qty=10):
    p_res = client.post(
        f"/api/v1/businesses/{biz_id}/purchases",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "supplier_id": sup_id,
            "branch_id": br_id,
            "purchase_date": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert p_res.status_code == 201
    pur_id = p_res.json()["id"]

    client.post(
        f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_id, "quantity": qty, "unit_price": price},
    )

    fin_res = client.post(
        f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/finalize",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fin_res.status_code == 200
    return pur_id


def open_shift(token, biz_id, branch_id, cash_account_id):
    """Open a valid cashier shift for CASH payment tests."""
    res = client.post(
        f"/api/v1/businesses/{biz_id}/shifts",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "branch_id": branch_id,
            "cash_account_id": cash_account_id,
            "opening_balance": 0,
        },
    )
    assert res.status_code == 201
    return res.json()["id"]


class TestPaymentEngineCore:
    def test_customer_payment_success_and_cash_posting(self):
        token, _ = register_user()
        biz_id = create_business(token)
        cust_id = create_customer(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        cash_acc_id = create_cash_account(token, biz_id, opening_balance=1000)
        shift_id = open_shift(token, biz_id, br_id, cash_acc_id)

        sales_id = setup_finalized_sales(token, biz_id, cust_id, br_id, prod_id, price=1000, qty=10) # 10,000

        # Customer Payment 4,000
        pay_res = client.post(
            f"/api/v1/businesses/{biz_id}/payments",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "direction": "CUSTOMER_IN",
                "target_type": "SALES",
                "target_id": sales_id,
                "amount": 4000,
                "currency": "IDR",
                "payment_method": "CASH",
                "cash_account_id": cash_acc_id,
                "shift_id": shift_id,
            },
        )
        assert pay_res.status_code == 201
        pay_data = pay_res.json()
        assert pay_data["status"] == "RECORDED"
        assert pay_data["payment_number"] == "PMT-000001"

        # Check Cash Account balance increases by 4,000 -> 5,000
        cash_res = client.get(
            f"/api/v1/businesses/{biz_id}/cash-accounts/{cash_acc_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert cash_res.status_code == 200
        assert Decimal(str(cash_res.json()["current_balance"])) == Decimal("5000")

        # Check Sales Receivable integration
        rec_res = client.get(
            f"/api/v1/businesses/{biz_id}/receivables/{sales_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert rec_res.status_code == 200
        assert Decimal(str(rec_res.json()["paid_amount"])) == Decimal("4000")
        assert Decimal(str(rec_res.json()["outstanding_amount"])) == Decimal("6000")
        assert rec_res.json()["status"] == "PARTIALLY_PAID"

    def test_supplier_payment_success_and_cash_posting(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        cash_acc_id = create_cash_account(token, biz_id, opening_balance=20000)

        pur_id = setup_finalized_purchase(token, biz_id, sup_id, br_id, prod_id, price=1000, qty=10) # 10,000

        # Supplier Payment 6,000
        pay_res = client.post(
            f"/api/v1/businesses/{biz_id}/payments",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "direction": "SUPPLIER_OUT",
                "target_type": "PURCHASE",
                "target_id": pur_id,
                "amount": 6000,
                "currency": "IDR",
                "payment_method": "BANK_TRANSFER",
                "cash_account_id": cash_acc_id,
            },
        )
        assert pay_res.status_code == 201

        # Check Cash Account balance decreases by 6,000 -> 14,000
        cash_res = client.get(
            f"/api/v1/businesses/{biz_id}/cash-accounts/{cash_acc_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert cash_res.status_code == 200
        assert Decimal(str(cash_res.json()["current_balance"])) == Decimal("14000")

        # Check Purchase Payable integration
        pay_detail = client.get(
            f"/api/v1/businesses/{biz_id}/purchases/payables/{pur_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert pay_detail.status_code == 200
        assert Decimal(str(pay_detail.json()["paid_amount"])) == Decimal("6000")
        assert Decimal(str(pay_detail.json()["outstanding_amount"])) == Decimal("4000")
        assert pay_detail.json()["status"] == "PARTIALLY_PAID"

    def test_overpayment_rejected(self):
        token, _ = register_user()
        biz_id = create_business(token)
        cust_id = create_customer(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        cash_acc_id = create_cash_account(token, biz_id)

        sales_id = setup_finalized_sales(token, biz_id, cust_id, br_id, prod_id, price=1000, qty=10) # 10,000

        # Attempt to pay 12,000 (> 10,000)
        pay_res = client.post(
            f"/api/v1/businesses/{biz_id}/payments",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "direction": "CUSTOMER_IN",
                "target_type": "SALES",
                "target_id": sales_id,
                "amount": 12000,
                "currency": "IDR",
                "payment_method": "CASH",
                "cash_account_id": cash_acc_id,
            },
        )
        assert pay_res.status_code == 400

    def test_idempotency_key(self):
        token, _ = register_user()
        biz_id = create_business(token)
        cust_id = create_customer(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        cash_acc_id = create_cash_account(token, biz_id, opening_balance=0)
        shift_id = open_shift(token, biz_id, br_id, cash_acc_id)

        sales_id = setup_finalized_sales(token, biz_id, cust_id, br_id, prod_id, price=1000, qty=10)

        payload = {
            "direction": "CUSTOMER_IN",
            "target_type": "SALES",
            "target_id": sales_id,
            "amount": 3000,
            "currency": "IDR",
            "payment_method": "CASH",
            "cash_account_id": cash_acc_id,
            "idempotency_key": "UNIQUE-KEY-12345",
            "shift_id": shift_id,
        }

        # First call
        res1 = client.post(
            f"/api/v1/businesses/{biz_id}/payments",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        assert res1.status_code == 201
        p1_id = res1.json()["id"]

        # Duplicate call with same idempotency key
        res2 = client.post(
            f"/api/v1/businesses/{biz_id}/payments",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        assert res2.status_code == 200 or res2.status_code == 201
        assert res2.json()["id"] == p1_id

        # Cash balance should be 3,000 (NOT 6,000 double posted!)
        cash_res = client.get(
            f"/api/v1/businesses/{biz_id}/cash-accounts/{cash_acc_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert Decimal(str(cash_res.json()["current_balance"])) == Decimal("3000")

    def test_void_payment_and_cash_reversal(self):
        token, _ = register_user()
        biz_id = create_business(token)
        cust_id = create_customer(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        cash_acc_id = create_cash_account(token, biz_id, opening_balance=5000)
        shift_id = open_shift(token, biz_id, br_id, cash_acc_id)

        sales_id = setup_finalized_sales(token, biz_id, cust_id, br_id, prod_id, price=1000, qty=10)

        pay_res = client.post(
            f"/api/v1/businesses/{biz_id}/payments",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "direction": "CUSTOMER_IN",
                "target_type": "SALES",
                "target_id": sales_id,
                "amount": 4000,
                "currency": "IDR",
                "payment_method": "CASH",
                "cash_account_id": cash_acc_id,
                "shift_id": shift_id,
            },
        )
        p_id = pay_res.json()["id"]

        # Balance after payment: 5,000 + 4,000 = 9,000
        cash1 = client.get(f"/api/v1/businesses/{biz_id}/cash-accounts/{cash_acc_id}", headers={"Authorization": f"Bearer {token}"}).json()["current_balance"]
        assert Decimal(str(cash1)) == Decimal("9000")

        # Void payment
        void_res = client.post(
            f"/api/v1/businesses/{biz_id}/payments/{p_id}/void",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert void_res.status_code == 200
        assert void_res.json()["status"] == "VOIDED"

        # Balance after void: 9,000 - 4,000 = 5,000
        cash2 = client.get(f"/api/v1/businesses/{biz_id}/cash-accounts/{cash_acc_id}", headers={"Authorization": f"Bearer {token}"}).json()["current_balance"]
        assert Decimal(str(cash2)) == Decimal("5000")

        # Receivable should revert back to UNPAID (paid_amount = 0)
        rec_res = client.get(
            f"/api/v1/businesses/{biz_id}/receivables/{sales_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert Decimal(str(rec_res.json()["paid_amount"])) == Decimal("0")
        assert rec_res.json()["status"] == "UNPAID"

    def test_tenant_isolation_and_idor(self):
        token_a, _ = register_user("a@test.com")
        biz_a = create_business(token_a, "Biz A")
        cust_a = create_customer(token_a, biz_a)
        br_a = create_branch(token_a, biz_a)
        unit_a = create_unit(token_a, biz_a)
        prod_a = create_product(token_a, biz_a, unit_a)
        cash_a = create_cash_account(token_a, biz_a)
        sales_a = setup_finalized_sales(token_a, biz_a, cust_a, br_a, prod_a)

        token_b, _ = register_user("b@test.com")
        biz_b = create_business(token_b, "Biz B")

        # User B trying to make payment for Biz A sales -> 404 / 403
        pay_res = client.post(
            f"/api/v1/businesses/{biz_a}/payments",
            headers={"Authorization": f"Bearer {token_b}"},
            json={
                "direction": "CUSTOMER_IN",
                "target_type": "SALES",
                "target_id": sales_a,
                "amount": 1000,
                "currency": "IDR",
                "payment_method": "CASH",
                "cash_account_id": cash_a,
            },
        )
        assert pay_res.status_code == 404 or pay_res.status_code == 403

    def test_rbac_member_read_only(self):
        owner_token, _ = register_user("owner_rbac@test.com")
        biz_id = create_business(owner_token)
        cust_id = create_customer(owner_token, biz_id)
        br_id = create_branch(owner_token, biz_id)
        unit_id = create_unit(owner_token, biz_id)
        prod_id = create_product(owner_token, biz_id, unit_id)
        cash_id = create_cash_account(owner_token, biz_id)
        sales_id = setup_finalized_sales(owner_token, biz_id, cust_id, br_id, prod_id)

        member_token, member_id = register_user("member_rbac@test.com")
        client.post(
            f"/api/v1/businesses/{biz_id}/members",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"user_id": member_id, "role": "MEMBER"},
        )

        # Member list payments -> 200 OK
        list_res = client.get(
            f"/api/v1/businesses/{biz_id}/payments",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert list_res.status_code == 200

        # Member create payment -> 403 Forbidden
        create_res = client.post(
            f"/api/v1/businesses/{biz_id}/payments",
            headers={"Authorization": f"Bearer {member_token}"},
            json={
                "direction": "CUSTOMER_IN",
                "target_type": "SALES",
                "target_id": sales_id,
                "amount": 1000,
                "currency": "IDR",
                "payment_method": "CASH",
                "cash_account_id": cash_id,
            },
        )
        assert create_res.status_code == 403

    def test_invalid_amount_rejection(self):
        token, _ = register_user()
        biz_id = create_business(token)
        cust_id = create_customer(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        cash_id = create_cash_account(token, biz_id)

        sales_id = setup_finalized_sales(token, biz_id, cust_id, br_id, prod_id)

        # Zero amount
        zero_res = client.post(
            f"/api/v1/businesses/{biz_id}/payments",
            headers={"Authorization": f"Bearer {token}"},
            json={"direction": "CUSTOMER_IN", "target_type": "SALES", "target_id": sales_id, "amount": 0, "currency": "IDR", "payment_method": "CASH", "cash_account_id": cash_id}
        )
        assert zero_res.status_code == 422

        # Negative amount
        neg_res = client.post(
            f"/api/v1/businesses/{biz_id}/payments",
            headers={"Authorization": f"Bearer {token}"},
            json={"direction": "CUSTOMER_IN", "target_type": "SALES", "target_id": sales_id, "amount": -100, "currency": "IDR", "payment_method": "CASH", "cash_account_id": cash_id}
        )
        assert neg_res.status_code == 422

    def test_invalid_target_status_rejection(self):
        token, _ = register_user()
        biz_id = create_business(token)
        cust_id = create_customer(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        cash_id = create_cash_account(token, biz_id)

        # DRAFT Sales
        sales_id = setup_finalized_sales_draft(token, biz_id, cust_id, br_id, prod_id)
        res = client.post(
            f"/api/v1/businesses/{biz_id}/payments",
            headers={"Authorization": f"Bearer {token}"},
            json={"direction": "CUSTOMER_IN", "target_type": "SALES", "target_id": sales_id, "amount": 100, "currency": "IDR", "payment_method": "CASH", "cash_account_id": cash_id}
        )
        assert res.status_code == 400
        assert "FINALIZED" in res.json()["message"]

    def test_mismatched_currency_rejection(self):
        token, _ = register_user()
        biz_id = create_business(token)
        cust_id = create_customer(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        # Cash account is USD
        cash_id = create_cash_account(token, biz_id, currency="USD")

        sales_id = setup_finalized_sales(token, biz_id, cust_id, br_id, prod_id)

        # Payment is IDR
        res = client.post(
            f"/api/v1/businesses/{biz_id}/payments",
            headers={"Authorization": f"Bearer {token}"},
            json={"direction": "CUSTOMER_IN", "target_type": "SALES", "target_id": sales_id, "amount": 1000, "currency": "IDR", "payment_method": "CASH", "cash_account_id": cash_id}
        )
        assert res.status_code == 400
        assert "currency" in res.json()["message"].lower()

    def test_purchase_return_effect_on_payable_limit(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        cash_id = create_cash_account(token, biz_id, opening_balance=20000)
        shift_id = open_shift(token, biz_id, br_id, cash_id)

        # Purchase 10,000
        pur_id = setup_finalized_purchase(token, biz_id, sup_id, br_id, prod_id, price=1000, qty=10)

        # Return 3,000 (Net Payable should be 7,000)
        # We just create a finalized return via API if possible, or mock it in repo
        from app.modules.purchase_return.repository import InMemoryPurchaseReturnRepository
        from app.modules.purchase_return.schemas import PurchaseReturnInDB, PurchaseReturnStatus
        from datetime import datetime
        now = datetime.now(timezone.utc)
        ret = PurchaseReturnInDB(
            id="fake-ret-id", business_id=biz_id, purchase_id=pur_id, inventory_location_id="fake-loc",
            return_number="PRT-000001", status=PurchaseReturnStatus.FINALIZED, notes=None,
            subtotal=Decimal("3000"), discount_total=Decimal("0"), tax_total=Decimal("0"),
            grand_total=Decimal("3000"), created_by_user_id="system", finalized_by_user_id="system",
            cancelled_by_user_id=None, is_deleted=False, created_at=now, updated_at=now,
            finalized_at=now, cancelled_at=None
        )
        InMemoryPurchaseReturnRepository._returns[ret.id] = ret

        # Attempt to pay 8,000 (> 7,000 net payable)
        res_over = client.post(
            f"/api/v1/businesses/{biz_id}/payments",
            headers={"Authorization": f"Bearer {token}"},
            json={"direction": "SUPPLIER_OUT", "target_type": "PURCHASE", "target_id": pur_id, "amount": 8000, "currency": "IDR", "payment_method": "CASH", "cash_account_id": cash_id, "shift_id": shift_id}
        )
        assert res_over.status_code == 400
        assert "exceeds remaining outstanding" in res_over.json()["message"]

        # Attempt to pay exactly 7,000
        res_ok = client.post(
            f"/api/v1/businesses/{biz_id}/payments",
            headers={"Authorization": f"Bearer {token}"},
            json={"direction": "SUPPLIER_OUT", "target_type": "PURCHASE", "target_id": pur_id, "amount": 7000, "currency": "IDR", "payment_method": "CASH", "cash_account_id": cash_id, "shift_id": shift_id}
        )
        assert res_ok.status_code == 201

        # Payable should be PAID
        pay_detail = client.get(
            f"/api/v1/businesses/{biz_id}/purchases/payables/{pur_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert pay_detail.json()["status"] == "PAID"
        assert Decimal(str(pay_detail.json()["paid_amount"])) == Decimal("7000")
        assert Decimal(str(pay_detail.json()["outstanding_amount"])) == Decimal("0")

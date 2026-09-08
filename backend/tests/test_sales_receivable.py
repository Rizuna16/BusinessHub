import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from app.main import app
from app.modules.authentication.repository import InMemoryUserRepository
from app.modules.account.repository import InMemoryAccountRepository
from app.modules.business.repository import InMemoryBusinessRepository
from app.modules.business_membership.repository import InMemoryBusinessMembershipRepository
from app.modules.customer.repository import InMemoryCustomerRepository
from app.modules.branch.repository import InMemoryBranchRepository
from app.modules.unit.repository import InMemoryUnitRepository
from app.modules.product.repository import InMemoryProductRepository
from app.modules.product_variant.repository import InMemoryProductVariantRepository
from app.modules.sales.repository import InMemorySalesRepository
from app.modules.sales_payment.repository import InMemorySalesPaymentRepository
from app.modules.sales_return.repository import InMemorySalesReturnRepository
from app.modules.warehouse.repository import InMemoryWarehouseRepository, InMemoryInventoryLocationRepository
from app.modules.inventory.repository import InMemoryStockBalanceRepository, InMemoryStockMovementRepository, InMemoryInventoryCostRepository

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_repositories():
    InMemorySalesReturnRepository.clear()
    InMemorySalesPaymentRepository.clear()
    InMemorySalesRepository.clear()
    InMemoryStockBalanceRepository.clear()
    InMemoryStockMovementRepository.clear()
    InMemoryInventoryCostRepository.clear()
    InMemoryInventoryLocationRepository.clear()
    InMemoryWarehouseRepository.clear()
    InMemoryProductVariantRepository.clear()
    InMemoryProductRepository.clear()
    InMemoryUnitRepository.clear()
    InMemoryBranchRepository.clear()
    InMemoryCustomerRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryUserRepository.clear()
    yield
    InMemorySalesReturnRepository.clear()
    InMemorySalesPaymentRepository.clear()
    InMemorySalesRepository.clear()
    InMemoryStockBalanceRepository.clear()
    InMemoryStockMovementRepository.clear()
    InMemoryInventoryCostRepository.clear()
    InMemoryInventoryLocationRepository.clear()
    InMemoryWarehouseRepository.clear()
    InMemoryProductVariantRepository.clear()
    InMemoryProductRepository.clear()
    InMemoryUnitRepository.clear()
    InMemoryBranchRepository.clear()
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


def create_finalized_sales(token, business_id, br_id, prod_id, customer_id=None, qty="10", price="100000"):
    s_res = client.post(
        f"/api/v1/businesses/{business_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "branch_id": br_id,
            "customer_id": customer_id,
            "sales_date": datetime.now(timezone.utc).isoformat(),
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


def create_cash_account(token, business_id, name="Main Cash", opening_balance=50000000, currency="IDR"):
    import uuid
    code = f"CASH-{uuid.uuid4().hex[:8].upper()}"
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


def record_payment(token, business_id, sales_id, amount="500000", method="CASH", cash_account_id=None):
    if cash_account_id is None:
        cash_account_id = create_cash_account(token, business_id)

    p_res = client.post(
        f"/api/v1/businesses/{business_id}/payments",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "direction": "CUSTOMER_IN",
            "target_type": "SALES",
            "target_id": sales_id,
            "amount": amount,
            "currency": "IDR",
            "payment_method": method,
            "cash_account_id": cash_account_id,
        },
    )
    assert p_res.status_code == 201
    return p_res.json()["id"]


class TestSalesReceivableFeature:

    # 1. Unauthenticated access rejected
    def test_unauthenticated_access_rejected(self):
        res = client.get("/api/v1/businesses/biz123/receivables")
        assert res.status_code == 401

    # 2. Finalized unpaid sales -> UNPAID status
    def test_unpaid_receivable_calculation(self):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)
        cust_id = create_customer(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        add_opening_stock(token, biz_id, loc_id, prod_id, qty="100")

        sales_id = create_finalized_sales(token, biz_id, br_id, prod_id, customer_id=cust_id, qty="10", price="100000")

        res = client.get(
            f"/api/v1/businesses/{biz_id}/receivables/{sales_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["sales_total"] == "1000000"
        assert data["paid_amount"] == "0"
        assert data["outstanding_amount"] == "1000000"
        assert data["status"] == "UNPAID"
        assert data["payment_count"] == 0

    # 3. Partially paid sales -> PARTIALLY_PAID status
    def test_partially_paid_receivable_calculation(self):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        add_opening_stock(token, biz_id, loc_id, prod_id, qty="100")

        sales_id = create_finalized_sales(token, biz_id, br_id, prod_id, qty="10", price="100000")
        record_payment(token, biz_id, sales_id, amount="400000")

        res = client.get(
            f"/api/v1/businesses/{biz_id}/receivables/{sales_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["sales_total"] == "1000000"
        assert data["paid_amount"] == "400000"
        assert data["outstanding_amount"] == "600000"
        assert data["status"] == "PARTIALLY_PAID"
        assert data["payment_count"] == 1

    # 4. Fully paid sales -> PAID status
    def test_fully_paid_receivable_calculation(self):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        add_opening_stock(token, biz_id, loc_id, prod_id, qty="100")

        sales_id = create_finalized_sales(token, biz_id, br_id, prod_id, qty="10", price="100000")
        record_payment(token, biz_id, sales_id, amount="600000")
        record_payment(token, biz_id, sales_id, amount="400000")

        res = client.get(
            f"/api/v1/businesses/{biz_id}/receivables/{sales_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["sales_total"] == "1000000"
        assert data["paid_amount"] == "1000000"
        assert data["outstanding_amount"] == "0"
        assert data["status"] == "PAID"
        assert data["payment_count"] == 2

    # 5. Cancelled payment excluded from active paid
    def test_cancelled_payment_excluded(self):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        add_opening_stock(token, biz_id, loc_id, prod_id, qty="100")

        sales_id = create_finalized_sales(token, biz_id, br_id, prod_id, qty="10", price="100000")
        pay1_id = record_payment(token, biz_id, sales_id, amount="500000")

        # Cancel pay1
        client.post(
            f"/api/v1/businesses/{biz_id}/payments/{pay1_id}/void",
            headers={"Authorization": f"Bearer {token}"},
        )

        res = client.get(
            f"/api/v1/businesses/{biz_id}/receivables/{sales_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["paid_amount"] == "0"
        assert data["outstanding_amount"] == "1000000"
        assert data["status"] == "UNPAID"
        assert data["payment_count"] == 0
        # Historical payments includes cancelled item
        assert len(data["payments"]) == 1
        assert data["payments"][0]["status"] == "VOIDED"

    # 6. Draft & Cancelled Sales excluded from receivables list
    def test_draft_and_cancelled_sales_excluded(self):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)

        # Draft sales
        s_draft = client.post(
            f"/api/v1/businesses/{biz_id}/sales",
            headers={"Authorization": f"Bearer {token}"},
            json={"branch_id": br_id, "sales_date": datetime.now(timezone.utc).isoformat()},
        ).json()["id"]

        # Cancelled sales
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
            f"/api/v1/businesses/{biz_id}/receivables",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert res.json()["total"] == 0

        # Attempting get_receivable for DRAFT sales -> 400 Bad Request
        get_res = client.get(
            f"/api/v1/businesses/{biz_id}/receivables/{s_draft}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_res.status_code == 400

    # 7. Receivable Summary metrics
    def test_receivable_summary(self):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        add_opening_stock(token, biz_id, loc_id, prod_id, qty="100")

        # Sales 1: Unpaid (1,000,000)
        s1 = create_finalized_sales(token, biz_id, br_id, prod_id, qty="10", price="100000")

        # Sales 2: Partially paid (1,000,000, paid 300,000)
        s2 = create_finalized_sales(token, biz_id, br_id, prod_id, qty="10", price="100000")
        record_payment(token, biz_id, s2, amount="300000")

        # Sales 3: Fully paid (1,000,000, paid 1,000,000)
        s3 = create_finalized_sales(token, biz_id, br_id, prod_id, qty="10", price="100000")
        record_payment(token, biz_id, s3, amount="1000000")

        sum_res = client.get(
            f"/api/v1/businesses/{biz_id}/receivables/summary",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert sum_res.status_code == 200
        data = sum_res.json()
        assert data["total_sales_amount"] == "3000000"
        assert data["total_paid_amount"] == "1300000"
        assert data["total_outstanding_amount"] == "1700000"
        assert data["unpaid_count"] == 1
        assert data["partially_paid_count"] == 1
        assert data["paid_count"] == 1

    # 8. Customer Receivable Summary
    def test_customer_receivable_summary(self):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)
        cust_id = create_customer(token, biz_id, name="Cust Beta")
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        add_opening_stock(token, biz_id, loc_id, prod_id, qty="100")

        # Customer sale
        s1 = create_finalized_sales(token, biz_id, br_id, prod_id, customer_id=cust_id, qty="5", price="100000")
        record_payment(token, biz_id, s1, amount="200000")

        # Walk-in sale
        s2 = create_finalized_sales(token, biz_id, br_id, prod_id, customer_id=None, qty="2", price="100000")

        cust_res = client.get(
            f"/api/v1/businesses/{biz_id}/receivables/customer-summary",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert cust_res.status_code == 200
        items = cust_res.json()["items"]
        assert len(items) == 2

        beta_item = next(i for i in items if i["customer_id"] == cust_id)
        assert beta_item["total_sales"] == "500000"
        assert beta_item["total_paid"] == "200000"
        assert beta_item["total_outstanding"] == "300000"

    # 9. Cross-tenant isolation & IDOR
    def test_cross_tenant_isolation(self):
        token1, _ = register_user(email="owner1@example.com")
        biz1 = create_business(token1, name="Biz 1")

        token2, _ = register_user(email="owner2@example.com")
        biz2 = create_business(token2, name="Biz 2")
        br2 = create_branch(token2, biz2)
        unit2 = create_unit(token2, biz2)
        prod2 = create_product(token2, biz2, unit2)
        loc2 = setup_warehouse_and_location(token2, biz2)
        add_opening_stock(token2, biz2, loc2, prod2, qty="100")
        s2 = create_finalized_sales(token2, biz2, br2, prod2, qty="5")

        # Owner 1 attempts to read Biz 2 sales receivable from Biz 1 context
        res = client.get(
            f"/api/v1/businesses/{biz1}/receivables/{s2}",
            headers={"Authorization": f"Bearer {token1}"},
        )
        assert res.status_code == 404

    # 10. RBAC: Owner, Admin, Member access; Suspended/Removed denied
    def test_rbac_authorization(self):
        token_owner, _ = register_user(email="owner_rbac@example.com")
        biz_id = create_business(token_owner, name="RBAC Biz")
        br_id = create_branch(token_owner, biz_id)
        cust_id = create_customer(token_owner, biz_id)
        unit_id = create_unit(token_owner, biz_id)
        prod_id = create_product(token_owner, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token_owner, biz_id)
        add_opening_stock(token_owner, biz_id, loc_id, prod_id, qty="100")

        sales_id = create_finalized_sales(token_owner, biz_id, br_id, prod_id, customer_id=cust_id, qty="10", price="100000")

        # Owner can access
        res = client.get(
            f"/api/v1/businesses/{biz_id}/receivables/{sales_id}",
            headers={"Authorization": f"Bearer {token_owner}"},
        )
        assert res.status_code == 200

        # Register admin & add member via client
        token_admin, admin_user_id = register_user(email="admin_rbac@example.com", name="Admin Test")
        res_add = client.post(
            f"/api/v1/businesses/{biz_id}/members",
            headers={"Authorization": f"Bearer {token_owner}"},
            json={"user_id": admin_user_id, "role": "ADMIN"},
        )
        assert res_add.status_code == 201

        # Admin can access
        res = client.get(
            f"/api/v1/businesses/{biz_id}/receivables/{sales_id}",
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert res.status_code == 200

        # Register member & add member via client
        token_member, member_user_id = register_user(email="member_rbac@example.com", name="Member Test")
        res_add = client.post(
            f"/api/v1/businesses/{biz_id}/members",
            headers={"Authorization": f"Bearer {token_owner}"},
            json={"user_id": member_user_id, "role": "MEMBER"},
        )
        assert res_add.status_code == 201

        # Member can access
        res = client.get(
            f"/api/v1/businesses/{biz_id}/receivables/{sales_id}",
            headers={"Authorization": f"Bearer {token_member}"},
        )
        assert res.status_code == 200

        # Register suspended user & add member via client
        token_susp, susp_user_id = register_user(email="susp_rbac@example.com", name="Suspended Test")
        res_add = client.post(
            f"/api/v1/businesses/{biz_id}/members",
            headers={"Authorization": f"Bearer {token_owner}"},
            json={"user_id": susp_user_id, "role": "MEMBER"},
        )
        assert res_add.status_code == 201
        mem_id = res_add.json()["id"]
        # Suspend member
        client.patch(
            f"/api/v1/businesses/{biz_id}/members/{mem_id}",
            headers={"Authorization": f"Bearer {token_owner}"},
            json={"status": "SUSPENDED"},
        )

        # Suspended membership denied (404/403 anti-enumeration response)
        res = client.get(
            f"/api/v1/businesses/{biz_id}/receivables/{sales_id}",
            headers={"Authorization": f"Bearer {token_susp}"},
        )
        assert res.status_code in (403, 404)

        # Register removed user
        token_rem, rem_user_id = register_user(email="rem_rbac@example.com", name="Removed Test")
        res_add = client.post(
            f"/api/v1/businesses/{biz_id}/members",
            headers={"Authorization": f"Bearer {token_owner}"},
            json={"user_id": rem_user_id, "role": "MEMBER"},
        )
        assert res_add.status_code == 201
        mem2_id = res_add.json()["id"]
        # Remove member
        client.delete(
            f"/api/v1/businesses/{biz_id}/members/{mem2_id}",
            headers={"Authorization": f"Bearer {token_owner}"},
        )

        # Removed membership denied (404/403 anti-enumeration response)
        res = client.get(
            f"/api/v1/businesses/{biz_id}/receivables/{sales_id}",
            headers={"Authorization": f"Bearer {token_rem}"},
        )
        assert res.status_code in (403, 404)

    # 11. Sales Return boundary (Return does not alter payment/receivable directly)
    def test_sales_return_boundary(self):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)
        loc_id = setup_warehouse_and_location(token, biz_id)
        add_opening_stock(token, biz_id, loc_id, prod_id, qty="100")

        sales_id = create_finalized_sales(token, biz_id, br_id, prod_id, qty="10", price="100000")
        sline_id = client.get(f"/api/v1/businesses/{biz_id}/sales/{sales_id}", headers={"Authorization": f"Bearer {token}"}).json()["lines"][0]["id"]

        # Create and finalize a sales return of 2 items
        ret_id = client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_id": sales_id, "inventory_location_id": loc_id},
        ).json()["id"]
        client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns/{ret_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"sales_line_id": sline_id, "quantity": "2"},
        )
        client.post(
            f"/api/v1/businesses/{biz_id}/sales-returns/{ret_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Sales grand_total and Receivable derived amounts remain based on Sales + Payments
        rec_res = client.get(
            f"/api/v1/businesses/{biz_id}/receivables/{sales_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert rec_res.status_code == 200
        data = rec_res.json()
        assert data["sales_total"] == "1000000"
        assert data["outstanding_amount"] == "1000000"

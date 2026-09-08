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
from app.modules.branch.repository import InMemoryBranchRepository
from app.modules.unit.repository import InMemoryUnitRepository
from app.modules.product.repository import InMemoryProductRepository
from app.modules.product_variant.repository import InMemoryProductVariantRepository
from app.modules.purchase.repository import InMemoryPurchaseRepository

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_repositories():
    InMemoryPurchaseRepository.clear()
    InMemoryProductVariantRepository.clear()
    InMemoryProductRepository.clear()
    InMemoryUnitRepository.clear()
    InMemoryBranchRepository.clear()
    InMemorySupplierRepository.clear()
    InMemoryBusinessMembershipRepository.clear()
    InMemoryBusinessRepository.clear()
    InMemoryAccountRepository.clear()
    InMemoryUserRepository.clear()
    yield
    InMemoryPurchaseRepository.clear()
    InMemoryProductVariantRepository.clear()
    InMemoryProductRepository.clear()
    InMemoryUnitRepository.clear()
    InMemoryBranchRepository.clear()
    InMemorySupplierRepository.clear()
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


def create_supplier(token, business_id, name="Supplier A", status="ACTIVE"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/suppliers",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "supplier_type": "ORGANIZATION"},
    )
    assert res.status_code == 201
    sup_id = res.json()["id"]
    if status == "INACTIVE":
        client.post(
            f"/api/v1/businesses/{business_id}/suppliers/{sup_id}/deactivate",
            headers={"Authorization": f"Bearer {token}"},
        )
    elif status == "ARCHIVED":
        client.delete(
            f"/api/v1/businesses/{business_id}/suppliers/{sup_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    return sup_id


def create_branch(token, business_id, name="Branch A", code="BR-A", status="ACTIVE"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/branches",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code},
    )
    assert res.status_code == 201
    branch_id = res.json()["id"]
    if status == "SUSPENDED":
        client.post(
            f"/api/v1/businesses/{business_id}/branches/{branch_id}/suspend",
            headers={"Authorization": f"Bearer {token}"},
        )
    elif status == "ARCHIVED":
        client.delete(
            f"/api/v1/businesses/{business_id}/branches/{branch_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    return branch_id


def create_unit(token, business_id, name="Pcs", code="PCS"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/units",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code},
    )
    assert res.status_code == 201
    return res.json()["id"]


def create_product(token, business_id, unit_id, name="Product A", code="PROD-A", p_type="GOODS", status="ACTIVE"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/products",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code, "unit_id": unit_id, "product_type": p_type},
    )
    assert res.status_code == 201
    prod_id = res.json()["id"]
    if status == "ARCHIVED":
        client.delete(
            f"/api/v1/businesses/{business_id}/products/{prod_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    return prod_id


def create_variant(token, business_id, product_id, name="Variant Red", code="VAR-RED"):
    res = client.post(
        f"/api/v1/businesses/{business_id}/products/{product_id}/variants",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code},
    )
    assert res.status_code == 201
    return res.json()["id"]


class TestPurchaseFeature:
    def test_create_purchase_success(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)

        res = client.post(
            f"/api/v1/businesses/{biz_id}/purchases",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "supplier_id": sup_id,
                "branch_id": br_id,
                "purchase_date": datetime.now(timezone.utc).isoformat(),
                "notes": "Initial purchase test",
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "DRAFT"
        assert data["purchase_number"] == "PUR-000001"
        assert data["supplier_id"] == sup_id
        assert data["branch_id"] == br_id
        assert data["notes"] == "Initial purchase test"

    def test_unique_purchase_number_per_business(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)

        res1 = client.post(
            f"/api/v1/businesses/{biz_id}/purchases",
            headers={"Authorization": f"Bearer {token}"},
            json={"supplier_id": sup_id, "branch_id": br_id, "purchase_date": datetime.now(timezone.utc).isoformat()},
        )
        res2 = client.post(
            f"/api/v1/businesses/{biz_id}/purchases",
            headers={"Authorization": f"Bearer {token}"},
            json={"supplier_id": sup_id, "branch_id": br_id, "purchase_date": datetime.now(timezone.utc).isoformat()},
        )
        assert res1.json()["purchase_number"] == "PUR-000001"
        assert res2.json()["purchase_number"] == "PUR-000002"

    def test_supplier_and_branch_required(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)

        # Missing supplier
        res = client.post(
            f"/api/v1/businesses/{biz_id}/purchases",
            headers={"Authorization": f"Bearer {token}"},
            json={"branch_id": br_id, "purchase_date": datetime.now(timezone.utc).isoformat()},
        )
        assert res.status_code == 422

        # Missing branch
        res = client.post(
            f"/api/v1/businesses/{biz_id}/purchases",
            headers={"Authorization": f"Bearer {token}"},
            json={"supplier_id": sup_id, "purchase_date": datetime.now(timezone.utc).isoformat()},
        )
        assert res.status_code == 422

    def test_supplier_validation_rules(self):
        token, _ = register_user()
        biz_id = create_business(token)
        br_id = create_branch(token, biz_id)

        inactive_sup = create_supplier(token, biz_id, name="Inc", status="INACTIVE")
        archived_sup = create_supplier(token, biz_id, name="Arch", status="ARCHIVED")

        # Inactive supplier rejected
        res = client.post(
            f"/api/v1/businesses/{biz_id}/purchases",
            headers={"Authorization": f"Bearer {token}"},
            json={"supplier_id": inactive_sup, "branch_id": br_id, "purchase_date": datetime.now(timezone.utc).isoformat()},
        )
        assert res.status_code == 400

        # Archived supplier rejected
        res = client.post(
            f"/api/v1/businesses/{biz_id}/purchases",
            headers={"Authorization": f"Bearer {token}"},
            json={"supplier_id": archived_sup, "branch_id": br_id, "purchase_date": datetime.now(timezone.utc).isoformat()},
        )
        assert res.status_code == 400

    def test_branch_validation_rules(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)

        suspended_br = create_branch(token, biz_id, name="Susp", code="SUS", status="SUSPENDED")
        archived_br = create_branch(token, biz_id, name="ArchBr", code="ARB", status="ARCHIVED")

        # Suspended branch rejected
        res = client.post(
            f"/api/v1/businesses/{biz_id}/purchases",
            headers={"Authorization": f"Bearer {token}"},
            json={"supplier_id": sup_id, "branch_id": suspended_br, "purchase_date": datetime.now(timezone.utc).isoformat()},
        )
        assert res.status_code == 400

        # Archived branch rejected
        res = client.post(
            f"/api/v1/businesses/{biz_id}/purchases",
            headers={"Authorization": f"Bearer {token}"},
            json={"supplier_id": sup_id, "branch_id": archived_br, "purchase_date": datetime.now(timezone.utc).isoformat()},
        )
        assert res.status_code == 400

    def test_product_and_variant_validation_rules(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)

        goods_prod = create_product(token, biz_id, unit_id, name="Goods", code="GDS", p_type="GOODS")
        service_prod = create_product(token, biz_id, unit_id, name="Service", code="SRV", p_type="SERVICE")
        archived_prod = create_product(token, biz_id, unit_id, name="ArchProd", code="ARP", status="ARCHIVED")

        p_res = client.post(
            f"/api/v1/businesses/{biz_id}/purchases",
            headers={"Authorization": f"Bearer {token}"},
            json={"supplier_id": sup_id, "branch_id": br_id, "purchase_date": datetime.now(timezone.utc).isoformat()},
        )
        pur_id = p_res.json()["id"]

        # SERVICE rejected
        res_srv = client.post(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": service_prod, "quantity": 1, "unit_price": 10},
        )
        assert res_srv.status_code == 400

        # Archived product rejected
        res_arc = client.post(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": archived_prod, "quantity": 1, "unit_price": 10},
        )
        assert res_arc.status_code == 400

        # Valid goods accepted
        res_ok = client.post(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": goods_prod, "quantity": 5, "unit_price": 100, "discount_amount": 10, "tax_amount": 5},
        )
        assert res_ok.status_code == 201
        line_data = res_ok.json()
        assert Decimal(str(line_data["line_subtotal"])) == Decimal("500")
        assert Decimal(str(line_data["line_total"])) == Decimal("495") # 500 - 10 + 5

    def test_line_quantity_and_price_validation(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)

        p_res = client.post(
            f"/api/v1/businesses/{biz_id}/purchases",
            headers={"Authorization": f"Bearer {token}"},
            json={"supplier_id": sup_id, "branch_id": br_id, "purchase_date": datetime.now(timezone.utc).isoformat()},
        )
        pur_id = p_res.json()["id"]

        # Zero quantity rejected
        res_q0 = client.post(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": 0, "unit_price": 10},
        )
        assert res_q0.status_code == 422

        # Negative quantity rejected
        res_qn = client.post(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": -2, "unit_price": 10},
        )
        assert res_qn.status_code == 422

        # Discount > subtotal rejected
        res_disc = client.post(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": 2, "unit_price": 10, "discount_amount": 25},
        )
        assert res_disc.status_code == 400

    def test_purchase_lifecycle_and_totals(self):
        token, _ = register_user()
        biz_id = create_business(token)
        sup_id = create_supplier(token, biz_id)
        br_id = create_branch(token, biz_id)
        unit_id = create_unit(token, biz_id)
        prod_id = create_product(token, biz_id, unit_id)

        p_res = client.post(
            f"/api/v1/businesses/{biz_id}/purchases",
            headers={"Authorization": f"Bearer {token}"},
            json={"supplier_id": sup_id, "branch_id": br_id, "purchase_date": datetime.now(timezone.utc).isoformat()},
        )
        pur_id = p_res.json()["id"]

        # Add two lines
        client.post(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": 2, "unit_price": 100, "discount_amount": 10, "tax_amount": 5},
        ) # sub 200, disc 10, tax 5 -> total 195
        client.post(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": 1, "unit_price": 300, "discount_amount": 0, "tax_amount": 30},
        ) # sub 300, disc 0, tax 30 -> total 330

        # Check purchase totals: sub = 500, disc = 10, tax = 35, grand = 525
        detail_res = client.get(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        p_data = detail_res.json()
        assert Decimal(str(p_data["subtotal"])) == Decimal("500")
        assert Decimal(str(p_data["discount_total"])) == Decimal("10")
        assert Decimal(str(p_data["tax_total"])) == Decimal("35")
        assert Decimal(str(p_data["grand_total"])) == Decimal("525")

        # Finalize purchase
        fin_res = client.post(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fin_res.status_code == 200
        assert fin_res.json()["status"] == "FINALIZED"
        assert fin_res.json()["finalized_by_user_id"] is not None

        # Finalized immutable (cannot add line)
        add_res = client.post(
            f"/api/v1/businesses/{biz_id}/purchases/{pur_id}/lines",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": prod_id, "quantity": 1, "unit_price": 50},
        )
        assert add_res.status_code == 400

    def test_authorization_matrix(self):
        owner_token, _ = register_user("owner@test.com")
        biz_id = create_business(owner_token)
        sup_id = create_supplier(owner_token, biz_id)
        br_id = create_branch(owner_token, biz_id)

        member_token, member_id = register_user("member@test.com")
        client.post(
            f"/api/v1/businesses/{biz_id}/members",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"user_id": member_id, "role": "MEMBER"},
        )

        # Member can list/read
        list_res = client.get(
            f"/api/v1/businesses/{biz_id}/purchases",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert list_res.status_code == 200

        # Member cannot create purchase -> 403
        create_res = client.post(
            f"/api/v1/businesses/{biz_id}/purchases",
            headers={"Authorization": f"Bearer {member_token}"},
            json={"supplier_id": sup_id, "branch_id": br_id, "purchase_date": datetime.now(timezone.utc).isoformat()},
        )
        assert create_res.status_code == 403

    def test_tenant_isolation(self):
        token_a, _ = register_user("a@test.com")
        biz_a = create_business(token_a, "Biz A")
        sup_a = create_supplier(token_a, biz_a)
        br_a = create_branch(token_a, biz_a)

        token_b, _ = register_user("b@test.com")
        biz_b = create_business(token_b, "Biz B")

        p_res = client.post(
            f"/api/v1/businesses/{biz_a}/purchases",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"supplier_id": sup_a, "branch_id": br_a, "purchase_date": datetime.now(timezone.utc).isoformat()},
        )
        pur_id = p_res.json()["id"]

        # User B accessing Biz A purchase -> 404 anti-enumeration
        res_b = client.get(
            f"/api/v1/businesses/{biz_a}/purchases/{pur_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert res_b.status_code == 404

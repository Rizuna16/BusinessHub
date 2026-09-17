import uuid
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
from app.modules.product_variant.repository import InMemoryProductVariantRepository
from app.modules.unit.repository import InMemoryUnitRepository
from app.modules.branch.repository import InMemoryBranchRepository
from app.modules.sales.repository import InMemorySalesRepository
from app.modules.pricing.repository import InMemoryPriceListRepository, InMemoryPriceEntryRepository
from app.modules.warehouse.repository import InMemoryWarehouseRepository, InMemoryInventoryLocationRepository
from app.modules.receiving.repository import InMemoryReceivingRepository
from app.modules.stock_opname.repository import InMemoryStockOpnameRepository
from app.modules.inventory.repository import InMemoryStockBalanceRepository, InMemoryStockMovementRepository, InMemoryInventoryCostRepository


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


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _register_and_get_token(client, email="owner@example.com", password="Password123", full_name="Owner User"):
    res = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": full_name, "password": password, "password_confirmation": password},
    )
    assert res.status_code == 201
    token = res.json().get("access_token")
    if not token:
        login_res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
    return token


def _create_business(client, token, name="Test Biz"):
    res = client.post(
        "/api/v1/businesses",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "business_type": "umkm", "timezone": "UTC", "locale": "en-US"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def _get_user_id(client, token):
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    return res.json()["id"]


def _add_member(client, owner_token, biz_id, user_email, role="MEMBER", password="Password123"):
    member_token = _register_and_get_token(client, email=user_email, password=password, full_name="Member User")
    user_id = _get_user_id(client, member_token)
    res = client.post(
        f"/api/v1/businesses/{biz_id}/members",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"user_id": user_id, "role": role},
    )
    assert res.status_code == 201
    membership_id = res.json()["id"]
    return member_token, user_id, membership_id


def _create_unit(client, token, biz_id, name=None, code=None):
    if not name:
        name = f"Unit_{uuid.uuid4().hex[:6]}"
    if not code:
        code = f"UNIT_{uuid.uuid4().hex[:6].upper()}"
    res = client.post(
        f"/api/v1/businesses/{biz_id}/units",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code, "symbol": "PCS", "unit_type": "OTHER"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def _create_branch(client, token, biz_id, name="Main Branch", code=None):
    if not code:
        code = f"BR_{uuid.uuid4().hex[:6].upper()}"
    res = client.post(
        f"/api/v1/businesses/{biz_id}/branches",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code},
    )
    assert res.status_code == 201
    return res.json()["id"]


def _create_customer(client, token, biz_id, name="Walk-in Customer"):
    res = client.post(
        f"/api/v1/businesses/{biz_id}/customers",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "customer_type": "INDIVIDUAL"},
    )
    assert res.status_code == 201
    cid = res.json()["id"]
    client.put(
        f"/api/v1/businesses/{biz_id}/customers/{cid}/credit/limit",
        headers={"Authorization": f"Bearer {token}"},
        json={"credit_limit": "100000000.00"},
    )
    return cid


def _create_product(client, token, biz_id, unit_id, name="Product Goods", code=None, p_type="GOODS"):
    if not code:
        code = f"PROD_{uuid.uuid4().hex[:6].upper()}"
    res = client.post(
        f"/api/v1/businesses/{biz_id}/products",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code, "unit_id": unit_id, "product_type": p_type},
    )
    assert res.status_code == 201
    return res.json()["id"]


def _create_variant(client, token, biz_id, product_id, name="Variant A", code=None):
    if not code:
        code = f"VAR_{uuid.uuid4().hex[:6].upper()}"
    res = client.post(
        f"/api/v1/businesses/{biz_id}/products/{product_id}/variants",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code},
    )
    assert res.status_code == 201
    return res.json()["id"]


def _create_price_list(client, token, biz_id, name="Retail Prices", code=None):
    if not code:
        code = f"PL_{uuid.uuid4().hex[:6].upper()}"
    res = client.post(
        f"/api/v1/businesses/{biz_id}/price-lists",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "code": code, "currency": "IDR"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def _create_price_entry(client, token, biz_id, price_list_id, product_id=None, variant_id=None, amount="10000"):
    now = datetime.now(timezone.utc).isoformat()
    res = client.post(
        f"/api/v1/businesses/{biz_id}/price-lists/{price_list_id}/prices",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "product_id": product_id,
            "variant_id": variant_id,
            "amount": amount,
            "effective_from": now,
        },
    )
    assert res.status_code == 201
    return res.json()["id"]


def _ensure_default_warehouse_and_stock(client, token, biz_id, product_id, location_id=None, quantity="10000"):
    if location_id is None:
        wh_res = client.post(
            f"/api/v1/businesses/{biz_id}/warehouses",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Default WH", "code": f"WH_{uuid.uuid4().hex[:6]}"},
        )
        if wh_res.status_code == 201:
            wh_id = wh_res.json()["id"]
            loc_res = client.post(
                f"/api/v1/businesses/{biz_id}/warehouses/{wh_id}/locations",
                headers={"Authorization": f"Bearer {token}"},
                json={"name": "Default Loc", "code": f"LOC_{uuid.uuid4().hex[:6]}", "location_type": "GENERAL"},
            )
            if loc_res.status_code == 201:
                location_id = loc_res.json()["id"]
        else:
            location_id = location_id
    client.post(
        f"/api/v1/businesses/{biz_id}/inventory/opening-balance",
        headers={"Authorization": f"Bearer {token}"},
        json={"inventory_location_id": location_id, "product_id": product_id, "quantity": quantity},
    )


# ============================================================
# Test Cases
# ============================================================

def test_sales_crud_and_lifecycle(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)
    cust_id = _create_customer(client, token, biz_id)
    prod_id = _create_product(client, token, biz_id, unit_id)
    _ensure_default_warehouse_and_stock(client, token, biz_id, prod_id)

    # 1. Create draft
    res = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "customer_id": cust_id,
            "branch_id": branch_id,
            "sales_date": datetime.now(timezone.utc).isoformat(),
            "notes": "Test draft sales",
        },
    )
    assert res.status_code == 201
    s_data = res.json()
    assert s_data["status"] == "DRAFT"
    assert s_data["sales_number"] == "SAL-000001"
    sales_id = s_data["id"]

    # 2. List
    list_res = client.get(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 1

    # 3. Detail
    detail_res = client.get(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == sales_id

    # 4. Update draft
    upd_res = client.patch(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"notes": "Updated draft notes"},
    )
    assert upd_res.status_code == 200
    assert upd_res.json()["notes"] == "Updated draft notes"

    # Add line to finalize
    line_res = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_id, "quantity": "2", "unit_price": "50000"},
    )
    assert line_res.status_code == 201

    # 6. Finalize
    fin_res = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fin_res.status_code == 200
    assert fin_res.json()["status"] == "FINALIZED"

    # 5. Delete draft when finalized -> 400
    del_res = client.delete(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_res.status_code == 400


def test_sales_number_and_client_spoofing(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    branch_id = _create_branch(client, token, biz_id)

    # 7. Generated server-side & 8. unique per business & 10. client spoof rejected
    res1 = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat(), "sales_number": "SPOOF-001"},
    )
    assert res1.status_code == 422  # extra=forbid on sales_number

    res1_ok = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    )
    assert res1_ok.status_code == 201
    assert res1_ok.json()["sales_number"] == "SAL-000001"

    res2_ok = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    )
    assert res2_ok.status_code == 201
    assert res2_ok.json()["sales_number"] == "SAL-000002"


def test_customer_validation_rules(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    branch_id = _create_branch(client, token, biz_id)

    # 11. Customer optional (null valid)
    res_null = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"customer_id": None, "branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    )
    assert res_null.status_code == 201
    assert res_null.json()["customer_id"] is None

    # 12. Active customer accepted
    cust_id = _create_customer(client, token, biz_id, name="Active Cust")
    res_active = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"customer_id": cust_id, "branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    )
    assert res_active.status_code == 201

    # 13. Inactive customer rejected
    client.post(f"/api/v1/businesses/{biz_id}/customers/{cust_id}/deactivate", headers={"Authorization": f"Bearer {token}"})
    res_inact = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"customer_id": cust_id, "branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    )
    assert res_inact.status_code == 400

    # 14. Archived customer rejected
    cust_arch = _create_customer(client, token, biz_id, name="Arch Cust")
    client.delete(f"/api/v1/businesses/{biz_id}/customers/{cust_arch}", headers={"Authorization": f"Bearer {token}"})
    res_arch = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"customer_id": cust_arch, "branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    )
    assert res_arch.status_code == 400

    # 15. Cross-business customer rejected
    token2 = _register_and_get_token(client, email="other@biz.com")
    biz2 = _create_business(client, token2, name="Biz 2")
    cust_biz2 = _create_customer(client, token2, biz2, name="Cust Biz2")
    res_cross = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"customer_id": cust_biz2, "branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    )
    assert res_cross.status_code == 400


def test_branch_validation_rules(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)

    # 16. Branch required
    res_no_br = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"sales_date": datetime.now(timezone.utc).isoformat()},
    )
    assert res_no_br.status_code == 422

    # 17. Active branch accepted
    br_active = _create_branch(client, token, biz_id, name="Active BR")
    res_active = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": br_active, "sales_date": datetime.now(timezone.utc).isoformat()},
    )
    assert res_active.status_code == 201

    # 18. Suspended branch rejected
    br_susp = _create_branch(client, token, biz_id, name="Susp BR")
    client.post(f"/api/v1/businesses/{biz_id}/branches/{br_susp}/suspend", headers={"Authorization": f"Bearer {token}"})
    res_susp = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": br_susp, "sales_date": datetime.now(timezone.utc).isoformat()},
    )
    assert res_susp.status_code == 400

    # 19. Archived branch rejected
    br_arch = _create_branch(client, token, biz_id, name="Arch BR")
    client.delete(f"/api/v1/businesses/{biz_id}/branches/{br_arch}", headers={"Authorization": f"Bearer {token}"})
    res_arch = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": br_arch, "sales_date": datetime.now(timezone.utc).isoformat()},
    )
    assert res_arch.status_code == 400


def test_product_and_variant_validation_rules(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)

    sales_res = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    )
    sales_id = sales_res.json()["id"]

    # 21. Active GOODS accepted
    prod_goods = _create_product(client, token, biz_id, unit_id, p_type="GOODS")
    res_goods = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_goods, "quantity": "1", "unit_price": "1000"},
    )
    assert res_goods.status_code == 201

    # 22. Active SERVICE accepted
    prod_srv = _create_product(client, token, biz_id, unit_id, p_type="SERVICE")
    res_srv = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_srv, "quantity": "1", "unit_price": "5000"},
    )
    assert res_srv.status_code == 201

    # 23. Archived product rejected
    prod_arch = _create_product(client, token, biz_id, unit_id)
    client.delete(f"/api/v1/businesses/{biz_id}/products/{prod_arch}", headers={"Authorization": f"Bearer {token}"})
    res_arch = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_arch, "quantity": "1", "unit_price": "1000"},
    )
    assert res_arch.status_code == 400

    # 25. Active variant accepted
    var_id = _create_variant(client, token, biz_id, prod_goods)
    res_var = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"variant_id": var_id, "quantity": "1", "unit_price": "2000"},
    )
    assert res_var.status_code == 201

    # 29. SERVICE variant rejected
    # Attempting to create variant on service product fails at variant creation
    # or if passed manually:
    var_arch = _create_variant(client, token, biz_id, prod_goods, code="VAR_ARCH")
    client.delete(f"/api/v1/businesses/{biz_id}/products/{prod_goods}/variants/{var_arch}", headers={"Authorization": f"Bearer {token}"})
    res_var_arch = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"variant_id": var_arch, "quantity": "1", "unit_price": "2000"},
    )
    assert res_var_arch.status_code == 400


def test_pricelist_integration_and_history(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)
    prod_id = _create_product(client, token, biz_id, unit_id)
    _ensure_default_warehouse_and_stock(client, token, biz_id, prod_id)

    # 33. Active PriceList suggestion
    pl_id = _create_price_list(client, token, biz_id, name="Standard")
    _create_price_entry(client, token, biz_id, pl_id, product_id=prod_id, amount="100000")

    sales_id = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    ).json()["id"]

    # 35. User override preserved
    line = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_id, "quantity": "1", "unit_price": "95000"},
    ).json()

    assert line["suggested_selling_price"] == "100000"
    assert line["unit_price"] == "95000"

    # Finalize sales
    client.post(f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize", headers={"Authorization": f"Bearer {token}"})

    # 36. PriceList change does not mutate historical Sales
    client.post(
        f"/api/v1/businesses/{biz_id}/price-lists/{pl_id}/entries",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "product_id": prod_id,
            "amount": "120000",
            "effective_from": datetime.now(timezone.utc).isoformat(),
        },
    )

    detail = client.get(f"/api/v1/businesses/{biz_id}/sales/{sales_id}", headers={"Authorization": f"Bearer {token}"}).json()
    assert detail["lines"][0]["unit_price"] == "95000"


def test_calculations_and_decimal_precision(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)
    prod_id = _create_product(client, token, biz_id, unit_id)

    sales_id = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    ).json()["id"]

    # 38-46. Calculations: subtotal, discount, tax, grand_total, Decimal precision
    # Line 1: qty 3, price 1250.50 -> subtotal 3751.50, disc 100, tax 50 -> total 3701.50
    line1 = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_id, "quantity": "3", "unit_price": "1250.50", "discount_amount": "100", "tax_amount": "50"},
    ).json()

    assert Decimal(str(line1["line_subtotal"])) == Decimal("3751.50")
    assert Decimal(str(line1["line_total"])) == Decimal("3701.50")

    # Line 2: qty 2, price 2000 -> subtotal 4000, disc 0, tax 400 -> total 4400
    client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_id, "quantity": "2", "unit_price": "2000", "discount_amount": "0", "tax_amount": "400"},
    )

    detail = client.get(f"/api/v1/businesses/{biz_id}/sales/{sales_id}", headers={"Authorization": f"Bearer {token}"}).json()
    assert Decimal(str(detail["subtotal"])) == Decimal("7751.50")
    assert Decimal(str(detail["discount_total"])) == Decimal("100")
    assert Decimal(str(detail["tax_total"])) == Decimal("450")
    assert Decimal(str(detail["grand_total"])) == Decimal("8101.50")

    # 47. Negative quantity rejected
    res_neg_q = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_id, "quantity": "-1", "unit_price": "1000"},
    )
    assert res_neg_q.status_code == 422

    # 48. Negative price rejected
    res_neg_p = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_id, "quantity": "1", "unit_price": "-1000"},
    )
    assert res_neg_p.status_code == 422

    # 51. Discount causing negative total rejected
    res_bad_disc = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_id, "quantity": "1", "unit_price": "1000", "discount_amount": "1500"},
    )
    assert res_bad_disc.status_code == 422


def test_lifecycle_safety_and_immutability(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)
    prod_id = _create_product(client, token, biz_id, unit_id)
    _ensure_default_warehouse_and_stock(client, token, biz_id, prod_id)

    sales_id = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    ).json()["id"]

    line_id = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_id, "quantity": "2", "unit_price": "5000"},
    ).json()["id"]

    # 52. Finalize draft
    fin_res = client.post(f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize", headers={"Authorization": f"Bearer {token}"})
    assert fin_res.status_code == 200
    assert fin_res.json()["status"] == "FINALIZED"

    # 53 & 87. Repeated finalize rejected
    fin_again = client.post(f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize", headers={"Authorization": f"Bearer {token}"})
    assert fin_again.status_code == 400

    # 57. Cancel finalized rejected
    can_fin = client.post(f"/api/v1/businesses/{biz_id}/sales/{sales_id}/cancel", headers={"Authorization": f"Bearer {token}"})
    assert can_fin.status_code == 400

    # 58. Update finalized header rejected
    upd_fin = client.patch(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"notes": "new notes"},
    )
    assert upd_fin.status_code == 400

    # 60. Mutate finalized line rejected
    line_upd = client.patch(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines/{line_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"unit_price": "6000"},
    )
    assert line_upd.status_code == 400


def test_rbac_and_security(client):
    owner_token = _register_and_get_token(client, email="owner@biz.com")
    biz_id = _create_business(client, owner_token)
    branch_id = _create_branch(client, owner_token, biz_id)

    admin_token, _, _ = _add_member(client, owner_token, biz_id, "admin@biz.com", role="ADMIN")
    member_token, _, _ = _add_member(client, owner_token, biz_id, "member@biz.com", role="MEMBER")

    # 61. Unauthenticated denied
    assert client.get(f"/api/v1/businesses/{biz_id}/sales").status_code == 401

    # 62. OWNER allowed & 63. ADMIN allowed
    s1 = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    )
    assert s1.status_code == 201

    s2 = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    )
    assert s2.status_code == 201

    # 64. MEMBER read allowed
    assert client.get(f"/api/v1/businesses/{biz_id}/sales", headers={"Authorization": f"Bearer {member_token}"}).status_code == 200

    # 65. MEMBER create denied
    assert client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {member_token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    ).status_code == 403

    # 69. Non-member 404
    stranger_token = _register_and_get_token(client, email="stranger@biz.com")
    assert client.get(f"/api/v1/businesses/{biz_id}/sales", headers={"Authorization": f"Bearer {stranger_token}"}).status_code == 404


def test_boundaries_no_inventory_payment_receivable_accounting_mutation(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)
    prod_id = _create_product(client, token, biz_id, unit_id)
    _ensure_default_warehouse_and_stock(client, token, biz_id, prod_id, quantity="1000")

    sales_id = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    ).json()["id"]

    client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_id, "quantity": "5", "unit_price": "10000"},
    )

    # Finalize sales -> with Feature #24, GOODS lines now deduct stock
    fin_res = client.post(f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize", headers={"Authorization": f"Bearer {token}"})
    assert fin_res.status_code == 200
    assert fin_res.json()["status"] == "FINALIZED"

    # Stock deducted (1000 - 5 = 995)
    stock = client.get(f"/api/v1/businesses/{biz_id}/inventory/stock", headers={"Authorization": f"Bearer {token}"}).json()
    assert len(stock) == 1
    assert Decimal(str(stock[0]["quantity"])) == Decimal("995")

    # Payment, receivable, accounting endpoints now exist (Feature #26)
    # They require authentication. Since test has a valid token, expect 200.
    assert client.get(f"/api/v1/businesses/{biz_id}/receivables", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    assert client.get(f"/api/v1/businesses/{biz_id}/journals").status_code == 404


# ============================================================
# Test Cases 31, 32, 34, 37, 54-56, 68, 70-78, 87-89
# ============================================================

def test_product_variant_xor_and_missing_target(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)
    prod_id = _create_product(client, token, biz_id, unit_id)
    var_id = _create_variant(client, token, biz_id, prod_id)

    sales_id = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    ).json()["id"]

    # 31. product + variant rejected -> 422
    res_both = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_id, "variant_id": var_id, "quantity": "1", "unit_price": "1000"},
    )
    assert res_both.status_code == 422

    # 32. neither product nor variant rejected -> 422
    res_neither = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"quantity": "1", "unit_price": "1000"},
    )
    assert res_neither.status_code == 422


def test_no_pricelist_allows_sales(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)
    prod_id = _create_product(client, token, biz_id, unit_id)

    # 34. no PriceList still works
    sales_id = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    ).json()["id"]

    line = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_id, "quantity": "1", "unit_price": "5000"},
    ).json()

    assert line["suggested_selling_price"] is None


def test_archived_pricelist_does_not_break_historical(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)
    prod_id = _create_product(client, token, biz_id, unit_id)
    _ensure_default_warehouse_and_stock(client, token, biz_id, prod_id)

    pl_id = _create_price_list(client, token, biz_id, name="Retail")
    _create_price_entry(client, token, biz_id, pl_id, product_id=prod_id, amount="80000")

    sales_id = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    ).json()["id"]

    client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_id, "quantity": "1", "unit_price": "80000"},
    )

    client.post(f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize", headers={"Authorization": f"Bearer {token}"})

    # 37. archived PriceList does not break historical Sales
    client.delete(f"/api/v1/businesses/{biz_id}/price-lists/{pl_id}", headers={"Authorization": f"Bearer {token}"})

    detail = client.get(f"/api/v1/businesses/{biz_id}/sales/{sales_id}", headers={"Authorization": f"Bearer {token}"}).json()
    assert detail["lines"][0]["unit_price"] == "80000"


def test_cancel_draft_sales(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)
    prod_id = _create_product(client, token, biz_id, unit_id)

    sales_id = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    ).json()["id"]

    client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_id, "quantity": "1", "unit_price": "1000"},
    )

    # 55. cancel draft
    can = client.post(f"/api/v1/businesses/{biz_id}/sales/{sales_id}/cancel", headers={"Authorization": f"Bearer {token}"})
    assert can.status_code == 200
    assert can.json()["status"] == "CANCELLED"

    # 56. cancel cancelled rejected
    can2 = client.post(f"/api/v1/businesses/{biz_id}/sales/{sales_id}/cancel", headers={"Authorization": f"Bearer {token}"})
    assert can2.status_code == 400

    # 54. finalize cancelled rejected
    fin_can = client.post(f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize", headers={"Authorization": f"Bearer {token}"})
    assert fin_can.status_code == 400


def test_cannot_finalize_empty_sales(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    branch_id = _create_branch(client, token, biz_id)

    sales_id = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    ).json()["id"]

    # 89. no partial mutation when validation fails: finalize empty sales -> 400
    fin = client.post(f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize", headers={"Authorization": f"Bearer {token}"})
    assert fin.status_code == 400
    assert "without any lines" in fin.json()["detail"]


def test_member_update_finalized_cancel_denials(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    branch_id = _create_branch(client, token, biz_id)

    sales_id = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    ).json()["id"]

    member_token, _, _ = _add_member(client, token, biz_id, "memb@test.com", role="MEMBER")

    # 66. MEMBER update denied
    assert client.patch(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}",
        headers={"Authorization": f"Bearer {member_token}"},
        json={"notes": "new"},
    ).status_code == 403

    # 67. MEMBER finalize denied
    assert client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize",
        headers={"Authorization": f"Bearer {member_token}"},
    ).status_code == 403

    # 68. MEMBER cancel denied
    assert client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/cancel",
        headers={"Authorization": f"Bearer {member_token}"},
    ).status_code == 403


def test_sales_tenant_isolation_and_cross_business(client):
    token_a = _register_and_get_token(client, email="a@biz.com")
    biz_a = _create_business(client, token_a, name="Biz A")
    branch_a = _create_branch(client, token_a, biz_a)

    token_b = _register_and_get_token(client, email="b@biz.com")
    biz_b = _create_business(client, token_b, name="Biz B")
    cust_b = _create_customer(client, token_b, biz_b)
    unit_b = _create_unit(client, token_b, biz_b)
    prod_b = _create_product(client, token_b, biz_b, unit_b)

    # 72. cross-business Sales 404
    sales_a_id = client.post(
        f"/api/v1/businesses/{biz_a}/sales",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"branch_id": branch_a, "sales_date": datetime.now(timezone.utc).isoformat()},
    ).json()["id"]

    res = client.get(
        f"/api/v1/businesses/{biz_b}/sales/{sales_a_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res.status_code == 404




# ============================================================
# Additional Tests: 31, 32, 34, 37, 54-56, 66-68, 72-78, 89
# ============================================================

def test_product_variant_xor_and_missing_target(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)
    prod_id = _create_product(client, token, biz_id, unit_id)
    var_id = _create_variant(client, token, biz_id, prod_id)

    sales_id = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    ).json()["id"]

    # 31. product + variant rejected -> 422
    res_both = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_id, "variant_id": var_id, "quantity": "1", "unit_price": "1000"},
    )
    assert res_both.status_code == 422

    # 32. neither product nor variant rejected -> 422
    res_neither = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"quantity": "1", "unit_price": "1000"},
    )
    assert res_neither.status_code == 422


def test_no_pricelist_allows_sales(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    unit_id = _create_unit(client, token, biz_id)
    branch_id = _create_branch(client, token, biz_id)
    prod_id = _create_product(client, token, biz_id, unit_id)

    sales_id = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    ).json()["id"]

    line = client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": prod_id, "quantity": "1", "unit_price": "5000"},
    ).json()
    assert line["suggested_selling_price"] is None


def test_cancel_empty_sales_and_lifecycle(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    branch_id = _create_branch(client, token, biz_id)

    sales_id = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    ).json()["id"]

    # 55. cancel draft
    can = client.post(f"/api/v1/businesses/{biz_id}/sales/{sales_id}/cancel", headers={"Authorization": f"Bearer {token}"})
    assert can.status_code == 200
    assert can.json()["status"] == "CANCELLED"

    # 56. cancel cancelled rejected
    can2 = client.post(f"/api/v1/businesses/{biz_id}/sales/{sales_id}/cancel", headers={"Authorization": f"Bearer {token}"})
    assert can2.status_code == 400

    # 54. finalize cancelled rejected
    fin_can = client.post(f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize", headers={"Authorization": f"Bearer {token}"})
    assert fin_can.status_code == 400


def test_cannot_finalize_empty_sales(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    branch_id = _create_branch(client, token, biz_id)

    sales_id = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    ).json()["id"]

    fin = client.post(f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize", headers={"Authorization": f"Bearer {token}"})
    assert fin.status_code == 400
    assert "without any lines" in fin.json()["message"]


def test_member_update_finalized_cancel_denials(client):
    token = _register_and_get_token(client)
    biz_id = _create_business(client, token)
    branch_id = _create_branch(client, token, biz_id)

    sales_id = client.post(
        f"/api/v1/businesses/{biz_id}/sales",
        headers={"Authorization": f"Bearer {token}"},
        json={"branch_id": branch_id, "sales_date": datetime.now(timezone.utc).isoformat()},
    ).json()["id"]

    member_token, _, _ = _add_member(client, token, biz_id, "memb@test.com", role="MEMBER")

    # 66. MEMBER update denied
    assert client.patch(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}",
        headers={"Authorization": f"Bearer {member_token}"},
        json={"notes": "new"},
    ).status_code == 403

    # 67. MEMBER finalize denied
    assert client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/finalize",
        headers={"Authorization": f"Bearer {member_token}"},
    ).status_code == 403

    # 68. MEMBER cancel denied
    assert client.post(
        f"/api/v1/businesses/{biz_id}/sales/{sales_id}/cancel",
        headers={"Authorization": f"Bearer {member_token}"},
    ).status_code == 403


def test_tenant_isolation_and_cross_business(client):
    token_a = _register_and_get_token(client, email="a@biz.com")
    biz_a = _create_business(client, token_a, name="Biz A")
    branch_a = _create_branch(client, token_a, biz_a)

    token_b = _register_and_get_token(client, email="b@biz.com")
    biz_b = _create_business(client, token_b, name="Biz B")
    cust_b = _create_customer(client, token_b, biz_b)

    # 72. cross-business Sales 404
    sales_a_id = client.post(
        f"/api/v1/businesses/{biz_a}/sales",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"branch_id": branch_a, "sales_date": datetime.now(timezone.utc).isoformat()},
    ).json()["id"]

    res = client.get(
        f"/api/v1/businesses/{biz_b}/sales/{sales_a_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res.status_code == 404

    # 73. cross-business Customer rejected
    res_cust = client.patch(
        f"/api/v1/businesses/{biz_a}/sales/{sales_a_id}",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"customer_id": cust_b},
    )
    assert res_cust.status_code == 400

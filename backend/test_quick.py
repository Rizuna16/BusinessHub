import sys, os
os.chdir('E:/BusinessHub/backend')
sys.path.insert(0, 'E:/BusinessHub/backend')
from app.main import app
from fastapi.testclient import TestClient

c = TestClient(app)

r = c.post('/api/v1/auth/register', json={'email': 'owner@test.com', 'full_name': 'Owner', 'password': 'Password123', 'password_confirmation': 'Password123'})
token = r.json().get('access_token')
if not token:
    lr = c.post('/api/v1/auth/login', json={'email': 'owner@test.com', 'password': 'Password123'})
    token = lr.json()['access_token']
t = token

b = c.post('/api/v1/businesses', headers={'Authorization': f'Bearer {t}'}, json={'name': 'Biz', 'business_type': 'umkm', 'timezone': 'UTC', 'locale': 'en-US'}).json()['id']
cu = c.post(f'/api/v1/businesses/{b}/customers', headers={'Authorization': f'Bearer {t}'}, json={'name': 'Cust', 'customer_type': 'INDIVIDUAL'}).json()['id']
br = c.post(f'/api/v1/businesses/{b}/branches', headers={'Authorization': f'Bearer {t}'}, json={'name': 'Branch', 'code': 'BR'}).json()['id']
u = c.post(f'/api/v1/businesses/{b}/units', headers={'Authorization': f'Bearer {t}'}, json={'name': 'Unit', 'code': 'UN', 'symbol': 'pcs', 'unit_type': 'OTHER'}).json()['id']
p = c.post(f'/api/v1/businesses/{b}/products', headers={'Authorization': f'Bearer {t}'}, json={'name': 'Prod', 'code': 'PRD', 'unit_id': u, 'product_type': 'GOODS'}).json()['id']
wh = c.post(f'/api/v1/businesses/{b}/warehouses', headers={'Authorization': f'Bearer {t}'}, json={'name': 'Warehouse', 'code': 'WH'}).json()['id']
loc = c.post(f'/api/v1/businesses/{b}/warehouses/{wh}/locations', headers={'Authorization': f'Bearer {t}'}, json={'name': 'Location', 'code': 'LOC', 'location_type': 'GENERAL'}).json()['id']
c.post(f'/api/v1/businesses/{b}/inventory/opening-balance', headers={'Authorization': f'Bearer {t}'}, json={'inventory_location_id': loc, 'product_id': p, 'quantity': '10000'})
cash = c.post(f'/api/v1/businesses/{b}/cash-accounts', headers={'Authorization': f'Bearer {t}'}, json={'name': 'Cash', 'code': 'CASH', 'account_type': 'CASH', 'currency': 'IDR', 'opening_balance': 100000}).json()['id']

sid = c.post(f'/api/v1/businesses/{b}/sales', headers={'Authorization': f'Bearer {t}'}, json={'customer_id': cu, 'branch_id': br, 'sales_date': '2026-09-15T10:00:00Z'}).json()['id']
c.post(f'/api/v1/businesses/{b}/sales/{sid}/lines', headers={'Authorization': f'Bearer {t}'}, json={'product_id': p, 'quantity': '10', 'unit_price': '10000'})
c.post(f'/api/v1/businesses/{b}/sales/{sid}/finalize?inventory_location_id={loc}', headers={'Authorization': f'Bearer {t}'})

# Test payments with different methods
for method in ['CASH', 'BANK_TRANSFER', 'QRIS']:
    r = c.post(f'/api/v1/businesses/{b}/payments', headers={'Authorization': f'Bearer {t}'}, json={
        'direction': 'CUSTOMER_IN', 'target_type': 'SALES', 'target_id': sid,
        'amount': '1000', 'currency': 'IDR', 'payment_method': method,
        'cash_account_id': cash, 'payment_date': '2026-09-15T12:00:00Z',
    })
    print(f'{method}: status={r.status_code} recorded_method={r.json().get("payment_method")}')

r = c.get(f'/api/v1/businesses/{b}/payments', headers={'Authorization': f'Bearer {t}'})
for item in r.json()['items']:
    print(f'Listed: {item["payment_number"]} method={item["payment_method"]} amount={item["amount"]}')

r = c.get(f'/api/v1/businesses/{b}/payments/analytics/summary?date_from=2026-09-01T00:00:00Z&date_to=2026-09-30T23:59:59Z', headers={'Authorization': f'Bearer {t}'})
print(f'Summary: count={r.json()["payment_count"]} gross={r.json()["gross_recorded"]}')

r = c.get(f'/api/v1/businesses/{b}/payments/analytics/by-method?date_from=2026-09-01T00:00:00Z&date_to=2026-09-30T23:59:59Z', headers={'Authorization': f'Bearer {t}'})
for m in r.json()['methods']:
    print(f'Method: {m["payment_method"]} amount={m["amount"]} count={m["payment_count"]}')

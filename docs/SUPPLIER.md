# SUPPLIER FOUNDATION MODULE DOCUMENTATION

## 1. Domain Model
The Supplier Foundation module manages master vendor/supplier data across multi-tenant Business contexts.

### Fields
- `id` (string, UUID): Primary key.
- `business_id` (string): Tenant identifier boundary.
- `supplier_type` (Enum): `INDIVIDUAL` | `ORGANIZATION`.
- `code` (string): Auto-generated unique code per business (e.g. `SUP-000001`). Immutable after creation.
- `name` (string): Required supplier name (trimmed, 1-150 chars). Non-unique.
- `legal_name` (string, optional): Formal legal or company name (1-150 chars).
- `phone` (string, optional): Contact phone number stored as string.
- `email` (string, optional): Validated email address format.
- `address` (string, optional): Plain text address line.
- `city` (string, optional): City name.
- `province` (string, optional): State or province name.
- `postal_code` (string, optional): Postal/ZIP code.
- `country` (string, optional): Country name.
- `notes` (string, optional): Plain text notes.
- `status` (Enum): `ACTIVE` | `INACTIVE` | `ARCHIVED`.
- `created_at` (datetime ISO 8601): Server generated creation timestamp.
- `updated_at` (datetime ISO 8601): Server generated update timestamp.

---

## 2. Supplier Lifecycle
```text
ACTIVE ↔ INACTIVE
ACTIVE → ARCHIVED
INACTIVE → ARCHIVED
ARCHIVED = terminal (soft delete, cannot reactivate/deactivate)
```

---

## 3. Authorization & Tenant Isolation Matrix

| Operation | Path | OWNER | ADMIN | MEMBER | Non-Member / Suspended |
| :--- | :--- | :---: | :---: | :---: | :---: |
| Create Supplier | `POST /api/v1/businesses/{biz}/suppliers` | ✅ | ✅ | ❌ (403) | ❌ (404/401) |
| List Suppliers | `GET /api/v1/businesses/{biz}/suppliers` | ✅ | ✅ | ✅ | ❌ (404/401) |
| Get Supplier | `GET /api/v1/businesses/{biz}/suppliers/{id}` | ✅ | ✅ | ✅ | ❌ (404/401) |
| Update Supplier | `PATCH /api/v1/businesses/{biz}/suppliers/{id}` | ✅ | ✅ | ❌ (403) | ❌ (404/401) |
| Activate Supplier | `POST /api/v1/businesses/{biz}/suppliers/{id}/activate` | ✅ | ✅ | ❌ (403) | ❌ (404/401) |
| Deactivate Supplier | `POST /api/v1/businesses/{biz}/suppliers/{id}/deactivate` | ✅ | ✅ | ❌ (403) | ❌ (404/401) |
| Archive Supplier | `DELETE /api/v1/businesses/{biz}/suppliers/{id}` | ✅ | ✅ | ❌ (403) | ❌ (404/401) |

---

## 4. Search, Filtering & Pagination
- **Search Query**: `?search=...` performs partial, case-insensitive matches against `code`, `name`, `legal_name`, `phone`, and `email`.
- **Filtering**: `?status=ACTIVE` and/or `?supplier_type=ORGANIZATION` filter by enum values.
- **Pagination**: `?page=1&page_size=20` returns deterministic results ordered by `created_at ASC`, `id ASC`. Response format:
```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0
}
```

---

## 5. Repository Architecture & Future PostgreSQL Considerations
- Abstract Repository: `AbstractSupplierRepository`
- In-Memory Repository: `InMemorySupplierRepository`
- Designed for Future PostgreSQL indexing and constraints:
  - Unique index: `UNIQUE (business_id, lower(code))`
  - Indexes: `(business_id)`, `(status)`, `(supplier_type)`, `(business_id, code)`, `(business_id, name)`

---

## 6. Out-of-Scope Items
The following modules/features remain strictly out-of-scope for Feature #16:
- Purchase Orders / Goods Receipts / Accounts Payable (AP)
- Supplier Invoices / Supplier Pricing / Supplier Ratings & Catalog
- CRM / Accounting / Tax / Billing / Subscriptions
- Redis / Docker / PostgreSQL migrations

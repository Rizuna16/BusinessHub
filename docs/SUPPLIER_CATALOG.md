# Feature #20 — Supplier Catalog & Supplier Pricing

## 1. Purpose

The Supplier Catalog module serves as the procurement master and reference data foundation connecting:
`Supplier ↔ Product / Product Variant`

It stores suggested purchase prices, currencies, minimum order quantities (MOQ), lead times, and preferred supplier designations without coupling or mutating transactional engines (Purchase, Inventory, Financial).

---

## 2. Domain Model

Entity: `SupplierCatalogItem`

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | UUID (string) | Yes | Unique identifier for catalog item |
| `business_id` | UUID (string) | Yes | Tenant isolation identifier |
| `supplier_id` | UUID (string) | Yes | Reference to Supplier |
| `product_id` | UUID (string) | Optional (XOR) | Reference to target Product |
| `variant_id` | UUID (string) | Optional (XOR) | Reference to target ProductVariant |
| `supplier_code` | string | Optional | Supplier's external SKU/code |
| `supplier_product_name` | string | Optional | Supplier's product title |
| `purchase_price` | Decimal (>= 0) | Yes | Suggested procurement price |
| `currency` | string | Yes | Supported: `IDR`, `USD`, `SGD`, `MYR`, `EUR`, `JPY` |
| `minimum_order_quantity` | Decimal (> 0) | Optional | Minimum order quantity requirement |
| `lead_time_days` | integer (>= 0) | Optional | Estimated procurement lead time in days |
| `is_preferred` | boolean | Yes | Whether this supplier is preferred for this product/variant |
| `status` | Enum | Yes | `ACTIVE`, `INACTIVE`, `ARCHIVED` |
| `notes` | string | Optional | Additional procurement remarks |
| `created_at` | DateTime (UTC) | Yes | Creation timestamp |
| `updated_at` | DateTime (UTC) | Yes | Last update timestamp |

---

## 3. Core Validation & Association Rules

1. **Target XOR Rule**:
   - `product_id XOR variant_id` is strictly enforced.
   - Both populated or both null/empty is rejected with validation error (422).
2. **Product Validation**:
   - Must belong to the same business tenant.
   - Product status must be `ACTIVE`.
   - `product_type` must be `GOODS`. Service products are rejected.
3. **Variant Validation**:
   - Must belong to the same business tenant and be `ACTIVE`.
   - Parent product must be `ACTIVE` and `GOODS`.
4. **Supplier Validation**:
   - Must belong to the same business tenant.
   - Must be `ACTIVE` when creating catalog items.
5. **Preferred Supplier Invariant**:
   - For a given business and target product or variant, only ONE supplier catalog item can have `is_preferred = True`.
   - When marking an item preferred, any existing preferred supplier for that target in the tenant has `is_preferred` automatically unset to `False`.
6. **Unique Identity**:
   - Duplicate catalog item for the same `(business_id, supplier_id, target)` is strictly rejected with 400 Bad Request.
7. **Monetary and Numerical Precision**:
   - Uses `Decimal` arithmetic for `purchase_price` and `minimum_order_quantity`.

---

## 4. Lifecycle

- `ACTIVE` → `INACTIVE`
- `ACTIVE` → `ARCHIVED`
- `INACTIVE` → `ACTIVE`
- `INACTIVE` → `ARCHIVED`
- `ARCHIVED` → Terminal state (immutable, cannot reactivate or update)
- `DELETE` endpoint executes soft archiving.

---

## 5. API Endpoints

All endpoints scoped under `/api/v1/businesses/{business_id}/supplier-catalog`:

- `POST /` — Create a supplier catalog item (OWNER, ADMIN)
- `GET /` — List supplier catalog items with filters: `search`, `supplier_id`, `product_id`, `variant_id`, `status`, `is_preferred`, `page`, `page_size` (OWNER, ADMIN, MEMBER)
- `GET /{catalog_id}` — Get detail of a catalog item (OWNER, ADMIN, MEMBER)
- `PATCH /{catalog_id}` — Update catalog item details (OWNER, ADMIN)
- `DELETE /{catalog_id}` — Soft archive catalog item (OWNER, ADMIN)
- `POST /{catalog_id}/activate` — Activate catalog item (OWNER, ADMIN)
- `POST /{catalog_id}/deactivate` — Deactivate catalog item (OWNER, ADMIN)

---

## 6. Tenant Isolation & Security

- Strictly scoped by `business_id` from URL path / auth context.
- Cross-tenant or non-member resource access returns `404 Not Found` (anti-enumeration pattern).
- Request payloads use `extra="forbid"` to prevent client spoofing of server-controlled fields (`business_id`, `status`, `created_at`, `updated_at`).

---

## 7. Boundary Guarantees

- **Purchase Engine Boundary**: Supplier Catalog is reference data only. Changes to `purchase_price` do not mutate existing purchase lines or retroactively change purchase transactions.
- **Inventory Boundary**: No `StockBalance` mutation, no `StockMovement` creation, no `InventoryService` invocation.
- **Financial Boundary**: No Accounts Payable, payments, journals, ledgers, tax computations, or automatic FX conversions are performed.

---

## 8. Future PostgreSQL Constraints & Migration

When moving from InMemory repository to PostgreSQL:
```sql
CREATE TABLE supplier_catalog_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    supplier_id UUID NOT NULL REFERENCES suppliers(id) ON DELETE RESTRICT,
    product_id UUID REFERENCES products(id) ON DELETE RESTRICT,
    variant_id UUID REFERENCES product_variants(id) ON DELETE RESTRICT,
    supplier_code VARCHAR(100),
    supplier_product_name VARCHAR(255),
    purchase_price NUMERIC(15, 4) NOT NULL CHECK (purchase_price >= 0),
    currency VARCHAR(10) NOT NULL,
    minimum_order_quantity NUMERIC(15, 4) CHECK (minimum_order_quantity > 0),
    lead_time_days INTEGER CHECK (lead_time_days >= 0),
    is_preferred BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    notes VARCHAR(1000),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- XOR Constraint
    CONSTRAINT chk_target_xor CHECK (
        (product_id IS NOT NULL AND variant_id IS NULL) OR
        (product_id IS NULL AND variant_id IS NOT NULL)
    )
);

-- Unique relationship per product target
CREATE UNIQUE INDEX uq_supplier_catalog_product
ON supplier_catalog_items (business_id, supplier_id, product_id)
WHERE product_id IS NOT NULL;

-- Unique relationship per variant target
CREATE UNIQUE INDEX uq_supplier_catalog_variant
ON supplier_catalog_items (business_id, supplier_id, variant_id)
WHERE variant_id IS NOT NULL;

-- Unique preferred supplier per product
CREATE UNIQUE INDEX uq_preferred_supplier_product
ON supplier_catalog_items (business_id, product_id)
WHERE is_preferred = TRUE AND product_id IS NOT NULL;

-- Unique preferred supplier per variant
CREATE UNIQUE INDEX uq_preferred_supplier_variant
ON supplier_catalog_items (business_id, variant_id)
WHERE is_preferred = TRUE AND variant_id IS NOT NULL;
```

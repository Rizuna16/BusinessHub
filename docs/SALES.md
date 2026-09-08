# Feature #22 — Sales Foundation

## 1. Purpose & Scope

The Sales Foundation module establishes the core sales transaction engine in BusinessHub. It represents sales transactions linking customers (optional) and branches to product and variant lines.

Sales Foundation operates as a standalone transaction layer without hard dependencies on Payment (#23), Inventory (#24), Receivable (#26), Accounting (#33), or Sales Return (#25).

---

## 2. Sales Domain Model

### Sales Header (`Sales`)

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | UUID (string) | Yes | Unique identifier |
| `business_id` | UUID (string) | Yes | Business tenant boundary |
| `customer_id` | UUID (string) | Optional | Reference to Customer (null for walk-in sales) |
| `branch_id` | UUID (string) | Yes | Mandatory reference to active Branch |
| `sales_number` | string | Yes | Server-generated sequence `SAL-000001` |
| `sales_date` | DateTime (UTC) | Yes | Transaction date |
| `notes` | string | Optional | Customer or internal notes |
| `status` | Enum | Yes | `DRAFT`, `FINALIZED`, `CANCELLED` |
| `subtotal` | Decimal | Yes | `SUM(line_subtotal)` |
| `discount_total` | Decimal | Yes | `SUM(discount_amount)` |
| `tax_total` | Decimal | Yes | `SUM(tax_amount)` |
| `grand_total` | Decimal | Yes | `subtotal - discount_total + tax_total` |
| `created_by_user_id` | string | Yes | Creator user ID |
| `finalized_by_user_id` | string | Optional | User ID who finalized |
| `cancelled_by_user_id` | string | Optional | User ID who cancelled |
| `created_at` | DateTime (UTC) | Yes | Creation timestamp |
| `updated_at` | DateTime (UTC) | Yes | Last update timestamp |
| `finalized_at` | DateTime (UTC) | Optional | Finalization timestamp |
| `cancelled_at` | DateTime (UTC) | Optional | Cancellation timestamp |

### Sales Line (`SalesLine`)

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | UUID (string) | Yes | Line item ID |
| `sales_id` | UUID (string) | Yes | Reference to parent Sales |
| `product_id` | UUID (string) | Optional (XOR) | Reference to target Product |
| `variant_id` | UUID (string) | Optional (XOR) | Reference to target ProductVariant |
| `description` | string | Optional | Line description |
| `quantity` | Decimal (> 0) | Yes | Item quantity sold |
| `unit_price` | Decimal (>= 0) | Yes | Transaction unit price |
| `discount_amount` | Decimal (>= 0) | Yes | Line discount amount |
| `tax_amount` | Decimal (>= 0) | Yes | Line tax amount |
| `line_subtotal` | Decimal | Yes | `quantity * unit_price` |
| `line_total` | Decimal | Yes | `line_subtotal - discount_amount + tax_amount` |
| `created_at` | DateTime (UTC) | Yes | Creation timestamp |
| `updated_at` | DateTime (UTC) | Yes | Last update timestamp |

---

## 3. Business & Validation Rules

1. **Customer Integration**:
   - `customer_id` is optional (supports walk-in customers).
   - If specified, Customer must be in the same business and status `ACTIVE`. `INACTIVE` or `ARCHIVED` customers are rejected.
2. **Branch Integration**:
   - `branch_id` is mandatory.
   - Branch must be in the same business and status `ACTIVE`. `SUSPENDED` or `ARCHIVED` branches are rejected.
3. **Product & Variant Target Rules**:
   - Target is `product_id XOR variant_id`. Both specified or both null is rejected (`422 Unprocessable Entity`).
   - `Product` target can be `GOODS` or `SERVICE`. Product must be `ACTIVE` and in the same business.
   - `Variant` target is supported only for `GOODS` parent products. Parent product and variant must be `ACTIVE` and in the same business.
4. **Price List Suggestion Integration**:
   - Active `PriceList` and `PriceEntry` records matching the business, date, and product/variant are queried for price suggestion.
   - Price entry `amount` is exposed as `suggested_selling_price` on `SalesLineResponse`.
   - `unit_price` is snapshot upon line creation. Price list changes or archival **never** retroactively alter historical `SalesLine.unit_price`.
5. **Calculations & Precision**:
   - All calculations use `Decimal` precision.
   - Client-calculated totals are ignored and recalculated server-side.
   - `quantity` > 0, `unit_price` ≥ 0, `discount_amount` ≥ 0, `tax_amount` ≥ 0.
   - Line total cannot be negative (`discount_amount` ≤ `line_subtotal`).
6. **Lifecycle & Immutability**:
   - `DRAFT` → `FINALIZED`
   - `DRAFT` → `CANCELLED`
   - `FINALIZED` and `CANCELLED` are terminal states. Mutating lines or headers of non-draft sales is strictly rejected.

---

## 4. API Endpoints

All endpoints scoped under `/api/v1/businesses/{business_id}/sales`:

- `POST /` — Create sales draft (OWNER, ADMIN)
- `GET /` — List sales with filters: `search`, `customer_id`, `branch_id`, `status`, `page`, `page_size` (OWNER, ADMIN, MEMBER)
- `GET /{sales_id}` — Get sales detail with lines (OWNER, ADMIN, MEMBER)
- `PATCH /{sales_id}` — Update sales draft header (OWNER, ADMIN)
- `DELETE /{sales_id}` — Soft delete sales draft (OWNER, ADMIN)
- `POST /{sales_id}/lines` — Add line item to draft sales (OWNER, ADMIN)
- `PATCH /{sales_id}/lines/{line_id}` — Update line item in draft sales (OWNER, ADMIN)
- `DELETE /{sales_id}/lines/{line_id}` — Delete line item from draft sales (OWNER, ADMIN)
- `POST /{sales_id}/finalize` — Finalize draft sales (OWNER, ADMIN)
- `POST /{sales_id}/cancel` — Cancel draft sales (OWNER, ADMIN)

---

## 5. Security & Tenant Isolation

- JWT required for all endpoints.
- Scoped strictly by `business_id` from URL path.
- Non-member access or cross-tenant resource access returns `404 Not Found` (anti-enumeration pattern).
- Client body payload uses `extra="forbid"` to reject spoofing of server-controlled fields (`sales_number`, `status`, `created_by_user_id`, timestamps, calculated totals).

---

## 6. Boundary Guarantees

- **Inventory Boundary**: Finalizing sales does **not** mutate `StockBalance`, create `StockMovement`, or invoke `InventoryService` (deferred to Feature #24).
- **Payment Boundary**: Does **not** create payments, payment methods, or cash balances (deferred to Feature #23).
- **Receivable Boundary**: Does **not** create Accounts Receivable or customer debt records (deferred to Feature #26).
- **Accounting Boundary**: Does **not** post journals or ledgers (deferred to Feature #33).

---

## 7. PostgreSQL Future Considerations

When transitioning to PostgreSQL:
```sql
CREATE TABLE sales (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    customer_id UUID REFERENCES customers(id) ON DELETE RESTRICT,
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE RESTRICT,
    sales_number VARCHAR(50) NOT NULL,
    sales_date TIMESTAMPTZ NOT NULL,
    notes VARCHAR(1000),
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    subtotal NUMERIC(15, 4) NOT NULL DEFAULT 0,
    discount_total NUMERIC(15, 4) NOT NULL DEFAULT 0,
    tax_total NUMERIC(15, 4) NOT NULL DEFAULT 0,
    grand_total NUMERIC(15, 4) NOT NULL DEFAULT 0,
    created_by_user_id UUID NOT NULL,
    finalized_by_user_id UUID,
    cancelled_by_user_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finalized_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,

    CONSTRAINT uq_sales_number_per_business UNIQUE (business_id, sales_number),
    CONSTRAINT chk_sales_status CHECK (status IN ('DRAFT', 'FINALIZED', 'CANCELLED'))
);

CREATE TABLE sales_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sales_id UUID NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE RESTRICT,
    variant_id UUID REFERENCES product_variants(id) ON DELETE RESTRICT,
    description VARCHAR(1000),
    quantity NUMERIC(15, 4) NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(15, 4) NOT NULL CHECK (unit_price >= 0),
    discount_amount NUMERIC(15, 4) NOT NULL DEFAULT 0 CHECK (discount_amount >= 0),
    tax_amount NUMERIC(15, 4) NOT NULL DEFAULT 0 CHECK (tax_amount >= 0),
    line_subtotal NUMERIC(15, 4) NOT NULL,
    line_total NUMERIC(15, 4) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_sales_line_target_xor CHECK (
        (product_id IS NOT NULL AND variant_id IS NULL) OR
        (product_id IS NULL AND variant_id IS NOT NULL)
    )
);
```

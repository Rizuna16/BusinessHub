# Purchase Foundation (Feature #17)

## Overview

Purchase Foundation provides structured purchase transaction recording capabilities for BusinessHub. It establishes multi-tenant, membership-aware purchase transactions linking Businesses, Suppliers, Branches, Products, and Variants without directly mutating inventory stock or posting financial journals.

## Domain Model

### Purchase
- `id`: UUID string
- `business_id`: UUID string (Tenant isolation)
- `supplier_id`: UUID string (Active supplier reference)
- `branch_id`: UUID string (Active operational branch reference)
- `purchase_number`: Server-generated identifier (`PUR-000001`, unique per business)
- `purchase_date`: Timezone-aware ISO Datetime
- `notes`: Optional plain text notes
- `status`: `DRAFT` | `FINALIZED` | `CANCELLED`
- `subtotal`: Decimal (`Σ line_subtotal`)
- `discount_total`: Decimal (`Σ discount_amount`)
- `tax_total`: Decimal (`Σ tax_amount`)
- `grand_total`: Decimal (`subtotal - discount_total + tax_total`)
- `created_by_user_id`: JWT-authenticated user ID
- `finalized_by_user_id`: Optional user ID upon finalization
- `cancelled_by_user_id`: Optional user ID upon cancellation
- `is_deleted`: Boolean (Soft-delete flag for DRAFT purchases)
- `created_at`, `updated_at`, `finalized_at`, `cancelled_at`: ISO Datetime strings

### Purchase Line
- `id`: UUID string
- `purchase_id`: Foreign reference to parent Purchase
- `product_id`: Product reference (must be ACTIVE GOODS product in same business)
- `variant_id`: Optional Variant reference (must belong to parent Product, ACTIVE)
- `description`: Optional plain text transaction line description
- `quantity`: Decimal > 0
- `unit_price`: Decimal >= 0
- `discount_amount`: Decimal >= 0 (must not exceed line subtotal)
- `tax_amount`: Decimal >= 0
- `line_subtotal`: Decimal (`quantity * unit_price`)
- `line_total`: Decimal (`line_subtotal - discount_amount + tax_amount`)

## Lifecycle & Transition Rules

```text
DRAFT
 ├── FINALIZED (Terminal: read-only immutable record)
 └── CANCELLED (Terminal: read-only immutable record)
```

1. **DRAFT**: Header & lines mutable by OWNER/ADMIN. Line calculation and header total recalculation handled server-side.
2. **FINALIZED**: Terminal status. Must contain at least 1 line. Immutability enforced for header, lines, prices, and totals.
3. **CANCELLED**: Terminal status. Cancelled from DRAFT state. Read-only.

## Inventory & Financial Boundaries

- **Stock Mutation**: Purchase finalization in Feature #17 **does NOT** update stock balances or create stock movements (`StockBalance`, `StockMovement`, `InventoryService`, `StockOpname` are isolated).
- **Financial Posting**: Purchase totals are transaction totals only. No Accounts Payable, Payment, or Accounting Journals are posted.
- **Tax/Discount Engine**: No tax rates, tax rules, discount percentage, vouchers, or promotion engine involved. Plain Decimal amounts passed per line.

## API Endpoints

- `POST /api/v1/businesses/{business_id}/purchases` — Create DRAFT purchase
- `GET /api/v1/businesses/{business_id}/purchases` — List purchases (search/filter/pagination)
- `GET /api/v1/businesses/{business_id}/purchases/{purchase_id}` — Get purchase detail with lines
- `PATCH /api/v1/businesses/{business_id}/purchases/{purchase_id}` — Update DRAFT purchase header
- `DELETE /api/v1/businesses/{business_id}/purchases/{purchase_id}` — Soft delete DRAFT purchase
- `POST /api/v1/businesses/{business_id}/purchases/{purchase_id}/lines` — Add line to DRAFT purchase
- `PATCH /api/v1/businesses/{business_id}/purchases/{purchase_id}/lines/{line_id}` — Update line in DRAFT purchase
- `DELETE /api/v1/businesses/{business_id}/purchases/{purchase_id}/lines/{line_id}` — Delete line from DRAFT purchase
- `POST /api/v1/businesses/{business_id}/purchases/{purchase_id}/finalize` — Finalize DRAFT purchase
- `POST /api/v1/businesses/{business_id}/purchases/{purchase_id}/cancel` — Cancel DRAFT purchase

## Authorization Matrix

- **OWNER / ADMIN**: Create, Read, Update DRAFT, Delete DRAFT, Add/Update/Delete Line, Finalize, Cancel.
- **MEMBER**: Read-only.
- **Non-member / Suspended**: Anti-enumeration denial (404 Not Found).

## Future PostgreSQL Schema & Index Recommendations

```sql
-- Constraints
UNIQUE (business_id, purchase_number)

-- Recommended Indexes
CREATE INDEX idx_purchase_business ON purchases (business_id);
CREATE INDEX idx_purchase_status ON purchases (business_id, status);
CREATE INDEX idx_purchase_supplier ON purchases (business_id, supplier_id);
CREATE INDEX idx_purchase_branch ON purchases (business_id, branch_id);
CREATE INDEX idx_purchase_date ON purchases (business_id, purchase_date DESC);
CREATE INDEX idx_purchase_lines_purchase ON purchase_lines (purchase_id);
```

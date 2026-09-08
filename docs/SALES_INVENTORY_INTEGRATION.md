# Feature #24 — Sales → Inventory Integration

## 1. Domain Responsibility
Feature #24 integrates finalized Sales transactions with the existing Inventory Foundation. When a Sales order transitions from `DRAFT` to `FINALIZED`, stock is automatically deducted for all eligible `GOODS` lines via `InventoryService`.

Key rules:
- `GOODS` product and variant lines deduct physical inventory stock balance.
- `SERVICE` product lines do **NOT** affect inventory and create no stock movements.
- Service-only sales orders finalize without requiring inventory locations or stock availability.
- Payment foundation (#23) remains 100% decoupled from inventory mutations.

Out-of-scope capabilities:
- COGS, inventory valuation, Moving Average Costing, FIFO — subsequently implemented in Feature #38.
- Sales Return (#25), stock reversals, refunds.
- Customer Receivables (#26), Accounting (#33), or Payment Gateways (#32, #50).

---

## 2. Location Resolution Architecture

Target `InventoryLocation` for `GOODS` stock deduction is resolved deterministically:

1. **Priority 1 — Explicit `inventory_location_id`**: If supplied during finalization, validated to be `ACTIVE`, non-quarantine/damaged, and belonging to the active business tenant.
2. **Priority 2 — Branch Default Warehouse + Location**: Resolves the `ACTIVE` default warehouse associated with `Sales.branch_id` and its `ACTIVE` default inventory location (`is_default=True`).
3. **Priority 3 — Business Default Warehouse + Location**: Resolves the business-level default warehouse (`is_default=True`) and its `ACTIVE` default location (`is_default=True`).
4. **No Arbitrary Fallback**: If no active default location can be resolved for `GOODS` items, finalization fails (HTTP 400), and `Sales` remains `DRAFT`.

---

## 3. Stock Movement & Identity Mapping

- **Movement Type**: `SALE_OUT`
- **Reference Type**: `SALES`
- **Reference ID**: `sales.id`
- **Movement Notes**: `Stock deduction for Sales {sales.sales_number}`
- **Structure**: Exactly **one** `StockMovement` per finalized Sales order containing multiple `StockMovementLine` entries for all `GOODS` lines.

Stock Identity Mapping:
- **Product without Variant**: `(business_id, location_id, product_id, variant_id=None)`
- **Product with Variant**: `(business_id, location_id, parent_product_id, variant_id)`

---

## 4. Pre-flight Validation & Atomicity

- Aggregates required quantities by `(product_id, variant_id)` before mutation to handle multiple sales lines targeting the same item.
- Validates that `available_stock >= total_required_quantity` for ALL `GOODS` items at the resolved location.
- If stock is insufficient or location invalid:
  - Operation returns HTTP 400.
  - Zero stock balances are mutated.
  - No orphan stock movements are created.
  - `Sales` remains in `DRAFT` status.
- Prevents duplicate inventory posting by verifying no prior `SALE_OUT` movement exists with `reference_type=SALES` and `reference_id=sales.id`.

---

## 5. Security & Isolation

- Finalization requires `OWNER` or `ADMIN` role in active business membership (`sales.update` / `sales.finalize`).
- `MEMBER` role cannot finalize sales orders and thus cannot trigger stock deductions.
- Strict multi-tenant isolation enforces matching `business_id` across `Sales`, `Warehouse`, `InventoryLocation`, and `StockBalance`.

---

## 6. Concurrency & Future PostgreSQL Strategy

Currently implemented via atomic in-memory repository calls. For future PostgreSQL migration:

```sql
BEGIN;
-- Lock stock balance rows for all target items
SELECT * FROM stock_balance
WHERE business_id = :business_id
  AND inventory_location_id = :location_id
  AND (product_id, COALESCE(variant_id, '')) IN (...)
FOR UPDATE;

-- Validate availability
-- Insert SALE_OUT StockMovement + StockMovementLines
-- Update stock_balance quantities
-- Update Sales status to FINALIZED
COMMIT;
```

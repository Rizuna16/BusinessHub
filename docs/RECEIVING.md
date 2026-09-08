# Receiving Foundation (Feature #18)

## Overview

Receiving Foundation establishes the receiving domain as an independent layer between Purchase and future Inventory integration. It tracks physical receipt of goods against Purchase Orders without mutating stock balances or creating accounting entries.

## Domain Model

### Receiving
- `id`: UUID string
- `business_id`: UUID string (tenant isolation)
- `purchase_id`: UUID string (must reference FINALIZED Purchase in same business)
- `inventory_location_id`: UUID string (must reference ACTIVE InventoryLocation in same business)
- `receiving_number`: Server-generated identifier (`RCV-000001`, unique per business)
- `status`: `DRAFT` | `FINALIZED` | `CANCELLED`
- `notes`: Optional plain text notes
- `created_by_user_id`: JWT-authenticated user ID
- `finalized_by_user_id`: Optional user ID upon finalization
- `cancelled_by_user_id`: Optional user ID upon cancellation
- `is_deleted`: Boolean (soft-delete flag for DRAFT receivings)
- `created_at`, `updated_at`, `finalized_at`, `cancelled_at`: ISO Datetime strings

### Receiving Line
- `id`: UUID string
- `receiving_id`: Parent reference
- `purchase_line_id`: Must reference a PurchaseLine belonging to the parent Purchase
- `product_id`: Derived from PurchaseLine (immutable)
- `variant_id`: Derived from PurchaseLine (immutable, optional)
- `quantity`: Decimal > 0
- `created_at`, `updated_at`: ISO Datetime strings

## Lifecycle & Transition Rules

```text
DRAFT
 ├── FINALIZED (Terminal: read-only immutable record)
 └── CANCELLED (Terminal: read-only immutable record)
```

1. **DRAFT**: Lines mutable by OWNER/ADMIN. Over-receiving validation on add/update.
2. **FINALIZED**: Terminal status. Must contain at least 1 line. Over-receiving re-validated across all receivings for same PurchaseLine. Immutability enforced for lines, quantities, and totals.
3. **CANCELLED**: Terminal status. Cancelled from DRAFT state. Quantities excluded from received totals.

## Quantity Integrity & Partial Receiving

### Core Invariant
For every PurchaseLine:
```
Σ(ReceivingLine.quantity WHERE status ∈ {DRAFT, FINALIZED})
≤
PurchaseLine.quantity
```

### Partial Receiving Support
- Multiple Receivings per PurchaseLine (N:1)
- Each Receiving references specific PurchaseLine via `purchase_line_id`
- Service recalculates received totals from repository data at every add/update/finalize
- CANCELLED receiving quantities excluded from received totals
- Finalization re-validates across all Receivings for same PurchaseLine

### Example
```
PurchaseLine: ordered = 100
Receiving A (DRAFT → FINALIZED): 60
Receiving B (DRAFT → FINALIZED): 40
Total received = 100 ✓

Receiving C (attempts 10): REJECTED (over-receiving)
```

## Inventory & Financial Boundaries

- **Stock Mutation**: Receiving finalization in Feature #18 does **NOT** update stock balances or create stock movements (`StockBalance`, `StockMovement`, `InventoryService`, `StockOpname` remain isolated).
- **Financial Posting**: No Accounts Payable, Payment, or Accounting Journals are posted.
- **Supplier Return / Purchase Return**: Out of scope.

## API Endpoints

- `POST /api/v1/businesses/{business_id}/receivings` — Create DRAFT receiving (requires FINALIZED purchase)
- `GET /api/v1/businesses/{business_id}/receivings` — List (search/filter/pagination)
- `GET /api/v1/businesses/{business_id}/receivings/{receiving_id}` — Get detail with lines
- `PATCH /api/v1/businesses/{business_id}/receivings/{receiving_id}` — Update DRAFT notes
- `DELETE /api/v1/businesses/{business_id}/receivings/{receiving_id}` — Soft delete DRAFT
- `POST /api/v1/businesses/{business_id}/receivings/{receiving_id}/lines` — Add line (validates over-receiving)
- `PATCH /api/v1/businesses/{business_id}/receivings/{receiving_id}/lines/{line_id}` — Update line quantity (validates over-receiving)
- `DELETE /api/v1/businesses/{business_id}/receivings/{receiving_id}/lines/{line_id}` — Delete line from DRAFT
- `POST /api/v1/businesses/{business_id}/receivings/{receiving_id}/finalize` — Finalize (re-validates over-receiving across all receivings)
- `POST /api/v1/businesses/{business_id}/receivings/{receiving_id}/cancel` — Cancel DRAFT receiving

## Authorization Matrix

- **OWNER / ADMIN**: Create, Read, Update DRAFT, Delete DRAFT, Add/Update/Delete Line, Finalize, Cancel.
- **MEMBER**: Read-only.
- **Non-member / Suspended**: Anti-enumeration denial (404 Not Found).

## Inventory Boundary Verification

| Check | Result |
|-------|--------|
| StockBalance mutated? | **NO** |
| StockMovement created? | **NO** |
| InventoryService.adjust_in called? | **NO** |
| ReferenceType.RECEIVING added? | **NO** |

## Future Database Schema Recommendations

```sql
-- Constraints
UNIQUE (business_id, receiving_number)
FOREIGN KEY (purchase_id) REFERENCES purchases(id)
FOREIGN KEY (inventory_location_id) REFERENCES inventory_locations(id)
FOREIGN KEY (purchase_line_id) REFERENCES purchase_lines(id)

-- Recommended Indexes
CREATE INDEX idx_receiving_business ON receivings (business_id);
CREATE INDEX idx_receiving_status ON receivings (business_id, status);
CREATE INDEX idx_receiving_purchase ON receivings (business_id, purchase_id);
CREATE INDEX idx_receiving_location ON receivings (business_id, inventory_location_id);
CREATE INDEX idx_receiving_lines_receiving ON receiving_lines (receiving_id);
CREATE INDEX idx_receiving_lines_purchase_line ON receiving_lines (purchase_line_id);
```

## Future Inventory Integration Point

When Receiving → Inventory integration is implemented (separate feature):

1. Add `ReferenceType.RECEIVING` to `inventory/schemas.py`
2. `InventoryService.adjust_in()` already accepts `reference_type` and `reference_id` parameters
3. Receiving finalization hook will call `InventoryService.adjust_in()` with:
   - `reference_type: ReferenceType.RECEIVING`
   - `reference_id: receiving.id`
4. Inventory mutation will remain in its own feature with explicit test coverage

This design ensures clean separation of concerns and prevents accidental inventory mutation during Feature #18.
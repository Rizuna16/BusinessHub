# Purchase Return Foundation (Feature #19)

## Overview

Purchase Return Foundation provides structured return transaction recording capabilities for goods purchased and received from suppliers. It validates that returns only occur against **FINALIZED Purchases** with **FINALIZED Receivings**, strictly preventing over-returning while maintaining independent domain boundaries that do not directly mutate stock balances or create accounting ledger entries.

## Domain Model

### Purchase Return
- `id`: UUID string
- `business_id`: UUID string (tenant isolation)
- `purchase_id`: UUID string (references FINALIZED Purchase in same business)
- `inventory_location_id`: UUID string (references ACTIVE InventoryLocation in same business)
- `return_number`: Server-generated sequence identifier (`PRT-000001`, unique per business)
- `status`: `DRAFT` | `FINALIZED` | `CANCELLED`
- `notes`: Optional plain text notes
- `subtotal`: Decimal (`Σ line_subtotal`)
- `discount_total`: Decimal (`Σ discount_amount`)
- `tax_total`: Decimal (`Σ tax_amount`)
- `grand_total`: Decimal (`subtotal - discount_total + tax_total`)
- `created_by_user_id`: JWT-authenticated user ID
- `finalized_by_user_id`: Optional user ID upon finalization
- `cancelled_by_user_id`: Optional user ID upon cancellation
- `is_deleted`: Boolean (soft-delete flag for DRAFT returns)
- `created_at`, `updated_at`, `finalized_at`, `cancelled_at`: ISO Datetime strings

### Purchase Return Line
- `id`: UUID string
- `return_id`: Parent reference
- `purchase_line_id`: Must reference a PurchaseLine belonging to the parent Purchase
- `product_id`: Inherited from PurchaseLine (immutable)
- `variant_id`: Inherited from PurchaseLine (immutable, optional)
- `quantity`: Decimal > 0
- `unit_price`: Decimal >= 0 (defaults to PurchaseLine unit price if not specified)
- `discount_amount`: Decimal >= 0
- `tax_amount`: Decimal >= 0
- `line_subtotal`: Decimal (`quantity * unit_price`)
- `line_total`: Decimal (`line_subtotal - discount_amount + tax_amount`)
- `created_at`, `updated_at`: ISO Datetime strings

## Reference Rules

- `PurchaseReturn` references `Purchase`.
- `PurchaseReturnLine` references `PurchaseLine`.
- **Supplier** is derived through: `PurchaseReturn -> Purchase -> supplier_id`.
- **Product and Variant** are derived through: `PurchaseReturnLine -> PurchaseLine -> product_id, variant_id`.

## Lifecycle & Transition Rules

```text
DRAFT
 ├── FINALIZED (Terminal: read-only immutable record)
 └── CANCELLED (Terminal: read-only immutable record)
```

1. **DRAFT**: Lines and notes mutable by OWNER/ADMIN. Over-return validation enforced on line add/update.
2. **FINALIZED**: Terminal status. Must contain at least 1 line. Immutability enforced for header, lines, quantities, and totals. Over-return re-validated across all returns for the same PurchaseLine.
3. **CANCELLED**: Terminal status. Cancelled from DRAFT state. Quantities released and excluded from returned totals.

## Quantity Integrity & Formula

For every `PurchaseLine`:

### Finalized Received Quantity
```
finalized_received_quantity = 
  SUM(ReceivingLine.quantity 
      WHERE ReceivingLine.purchase_line_id == PurchaseLine.id 
        AND Receiving.status == FINALIZED 
        AND Receiving.is_deleted == False)
```

### Cumulative Returned Quantity
```
cumulative_returned_quantity = 
  SUM(PurchaseReturnLine.quantity 
      WHERE PurchaseReturnLine.purchase_line_id == PurchaseLine.id 
        AND PurchaseReturn.status IN (DRAFT, FINALIZED) 
        AND PurchaseReturn.is_deleted == False)
```

### Core Invariant
```
cumulative_returned_quantity + proposed_quantity <= finalized_received_quantity
```

### Key Rules
- Only **FINALIZED** and non-deleted Receivings contribute to returnable quantity.
- **DRAFT** Receivings do NOT contribute to returnable quantity.
- **CANCELLED** Receivings do NOT contribute to returnable quantity.
- **DRAFT** Purchase Returns consume return capacity to prevent double-return allocation.
- **CANCELLED** Purchase Returns release capacity.

## Inventory & Financial Boundaries

- **Stock Mutation**: Purchase Return finalization in Feature #19 does **NOT** update stock balances or create stock movements (`StockBalance`, `StockMovement`, `InventoryService`, `StockOpname` remain isolated).
- **Financial Posting**: No Accounts Payable, Payment, Supplier Credit, or Accounting Journals are posted.
- **Tax/Discount Engines**: Line totals compute transaction amounts for accuracy without external engines.

## API Endpoints

- `POST /api/v1/businesses/{business_id}/purchase-returns` — Create DRAFT return (requires FINALIZED purchase)
- `GET /api/v1/businesses/{business_id}/purchase-returns` — List returns (search, filters, pagination)
- `GET /api/v1/businesses/{business_id}/purchase-returns/{return_id}` — Get detail with lines
- `PATCH /api/v1/businesses/{business_id}/purchase-returns/{return_id}` — Update DRAFT notes
- `DELETE /api/v1/businesses/{business_id}/purchase-returns/{return_id}` — Soft delete DRAFT return
- `POST /api/v1/businesses/{business_id}/purchase-returns/{return_id}/lines` — Add line (validates over-returning)
- `PATCH /api/v1/businesses/{business_id}/purchase-returns/{return_id}/lines/{line_id}` — Update line quantity (validates over-returning)
- `DELETE /api/v1/businesses/{business_id}/purchase-returns/{return_id}/lines/{line_id}` — Delete line from DRAFT
- `POST /api/v1/businesses/{business_id}/purchase-returns/{return_id}/finalize` — Finalize (re-validates over-returning against current finalized receipts)
- `POST /api/v1/businesses/{business_id}/purchase-returns/{return_id}/cancel` — Cancel DRAFT return

## Authorization Matrix

- **OWNER / ADMIN**: Create, Read, Update DRAFT, Delete DRAFT, Add/Update/Delete Line, Finalize, Cancel.
- **MEMBER**: Read-only (`list_returns`, `get_return`).
- **Non-member / Suspended**: Anti-enumeration denial (404 Not Found).

## Concurrency Note

Under in-memory storage, return quantities are calculated dynamically at the service layer at each add/update/finalize step. When transitioning to PostgreSQL, row-level locks or transaction isolation (`SERIALIZABLE` or `SELECT ... FOR UPDATE` on `purchase_lines`) should be used to guarantee atomicity during concurrent return creation.

## Inventory Boundary Verification

| Check | Result |
|-------|--------|
| StockBalance mutated? | **NO** |
| StockMovement created? | **NO** |
| InventoryService called? | **NO** |
| ReferenceType.PURCHASE_RETURN added? | **NO** |

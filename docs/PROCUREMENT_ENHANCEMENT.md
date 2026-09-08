# Feature #21 — Procurement Enhancement

## 1. Purpose & Scope

The Procurement Enhancement layer builds on top of:
- Feature #17 — Purchase
- Feature #18 — Purchase Receiving
- Feature #19 — Purchase Return
- Feature #20 — Supplier Catalog & Supplier Pricing

It provides an operational enhancement layer for procurement workflows without changing existing domain lifecycles, financial rules, or inventory boundaries.

---

## 2. Supplier Catalog → Purchase Price Suggestion

- **Lookup Logic**: When adding or fetching a purchase line for a supplier and product/variant target, active `SupplierCatalogItem` records (`status == ACTIVE`, matching `business_id`, `supplier_id`, and target product/variant) are queried.
- **Suggestion Exposure**: The active catalog item's `purchase_price` is exposed as `suggested_supplier_price` on `PurchaseLineResponse`.
- **Historical Price Snapshot**: The transaction price (`PurchaseLine.unit_price`) is set snapshot-style upon line creation. User overrides are preserved. Any subsequent modification or archival of the `SupplierCatalogItem` **never** retroactively alters existing `PurchaseLine.unit_price` values.
- **Independence**: Catalog item existence is optional; Purchase creation remains fully executable without a catalog.

---

## 3. Derived Receiving Progress & Receiving Summary

For every `PurchaseLine`:
- `ordered_quantity`: Ordered quantity defined on the purchase line (`quantity`).
- `received_quantity`: Sum of quantity from **FINALIZED** `ReceivingLine` items referencing that purchase line. Draft and Cancelled receivings are strictly excluded.
- `remaining_quantity`: `ordered_quantity - received_quantity`.

For the overall `Purchase`:
- Exposes `receiving_summary`:
  - `total_ordered`: Sum of ordered quantities across lines.
  - `total_received`: Sum of received quantities across lines.
  - `total_remaining`: Sum of remaining quantities across lines.
  - `status`: Derived receiving status enum:
    - `NOT_RECEIVED`: `total_ordered > 0` and `total_received == 0`
    - `PARTIALLY_RECEIVED`: `total_received > 0` and `total_received < total_ordered`
    - `FULLY_RECEIVED`: `total_ordered > 0` and `total_received >= total_ordered`

- **Important Note**: `DerivedReceivingStatus` is a derived read model projection. It does **not** alter `PurchaseStatus` (`DRAFT`, `FINALIZED`, `CANCELLED`).

---

## 4. Enhanced Search & Filters

`GET /api/v1/businesses/{business_id}/purchases` supports:
- `search`: Substring search on `purchase_number` or notes.
- `supplier_id`: Filter by supplier ID.
- `branch_id`: Filter by branch ID.
- `status`: Filter by `PurchaseStatus` (`DRAFT`, `FINALIZED`, `CANCELLED`).
- `receiving_status`: Filter by `DerivedReceivingStatus` (`NOT_RECEIVED`, `PARTIALLY_RECEIVED`, `FULLY_RECEIVED`).
- `page` & `page_size`: Pagination parameters.

---

## 5. Double Submit & Lifecycle Safety

Server-authoritative state checks strictly guard state transitions:
- `POST /{purchase_id}/finalize`:
  - Repeated finalize on `FINALIZED` purchase → rejected (`400 Bad Request: Purchase is already FINALIZED.`).
  - Finalize attempt on `CANCELLED` purchase → rejected (`400 Bad Request: Cannot finalize a CANCELLED purchase.`).
- `POST /{purchase_id}/cancel`:
  - Repeated cancel on `CANCELLED` purchase → rejected (`400 Bad Request: Purchase is already CANCELLED.`).
  - Cancel attempt on `FINALIZED` purchase → rejected (`400 Bad Request: Cannot cancel a FINALIZED purchase.`).

---

## 6. Boundary Enforcements

- **Inventory Boundary**: Enhancement layer does **not** mutate `StockBalance`, create `StockMovement`, or invoke `InventoryService`. All stock movements remain driven solely by Receiving finalization (Feature #18).
- **Financial Boundary**: No Accounts Payable, Payment, Refund, Accounting Journal, Ledger, Expense, or FX engine is introduced.
- **Purchase Return Compatibility**: Feature #19 Purchase Return capacity calculations continue to draw from finalized receiving lines and remain unaffected.

---

## 7. PostgreSQL Future Considerations

When transitioning from InMemory repository to PostgreSQL:
1. **Concurrency Protection**: Use row-level locking (`SELECT ... FOR UPDATE`) or transactional isolation when finalizing receivings to prevent concurrent over-receiving race conditions.
2. **Read Model Performance**: Create database views or indexed derived columns for receiving progress summaries on large datasets.
3. **Atomic State Transitions**: Ensure lifecycle state updates (`DRAFT` → `FINALIZED`/`CANCELLED`) execute within atomic database transactions.

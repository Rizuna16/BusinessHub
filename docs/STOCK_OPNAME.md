# Feature #14 — Inventory Stock Opname Documentation

## 1. Purpose
Stock Opname provides a robust physical inventory reconciliation mechanism to match **System Stock** against **Physical Stock** counts, calculate variances, and post automatic adjustment movements (`ADJUSTMENT_IN` / `ADJUSTMENT_OUT`) through the existing Inventory movement engine without modifying `StockBalance` directly.

---

## 2. Domain Model
*   **StockOpname**:
    *   `id`: UUID
    *   `business_id`: Tenant identifier
    *   `inventory_location_id`: Active storage/location scope
    *   `status`: `DRAFT` or `FINALIZED`
    *   `notes`: Optional description
    *   `created_by_user_id`: Creator user ID
    *   `finalized_by_user_id`: Finalizer user ID (nullable)
    *   `created_at`, `updated_at`, `finalized_at`

*   **StockOpnameLine**:
    *   `id`: UUID
    *   `opname_id`: Parent opname reference
    *   `inventory_location_id`: Inherited from opname location
    *   `product_id`: GOODS product (SERVICE products forbidden)
    *   `variant_id`: Optional active variant
    *   `system_quantity`: Snapshot of StockBalance quantity at line creation time
    *   `counted_quantity`: Physical count entered by user (Decimal, >= 0, nullable)
    *   `variance`: Server-calculated as `counted_quantity - system_quantity`

---

## 3. Opname Lifecycle
1.  **DRAFT**:
    *   Session is created in `DRAFT` status for an `ACTIVE` inventory location.
    *   Lines can be added (capturing current `system_quantity` snapshot).
    *   Physical counts can be updated via `PATCH`.
    *   Duplicate product/variant lines are rejected.
    *   Draft sessions can be deleted.
2.  **FINALIZED**:
    *   Triggered via `/finalize` endpoint by `OWNER` or `ADMIN`.
    *   Requires all lines to have `counted_quantity` entered.
    *   Performs stale-stock validation against current DB balance.
    *   Generates automatic adjustment movements (`ADJUSTMENT_IN` or `ADJUSTMENT_OUT` with `reference_type = STOCK_OPNAME`).
    *   Updates `StockBalance` atomically through the Inventory engine.
    *   Locks opname as strictly immutable (read-only audit record).

---

## 4. Snapshot Semantics
When an opname line is created, `system_quantity` captures the exact stock balance at that moment. Subsequent inventory movements or sales do not alter the snapshot.

---

## 5. Variance & Adjustment Integration
*   `variance = counted_quantity - system_quantity`
*   `variance > 0` $\rightarrow$ Generates `ADJUSTMENT_IN`
*   `variance < 0` $\rightarrow$ Generates `ADJUSTMENT_OUT`
*   `variance == 0` $\rightarrow$ No movement generated

---

## 6. Stale Stock Protection
Before finalization, the system checks whether the current stock balance matches `system_quantity`. If stock has changed since the snapshot was captured, finalization is rejected with **409 Conflict** to prevent accidental overwrites.

---

## 7. Authorization & Tenant Isolation
*   **OWNER / ADMIN**: Full create, count, finalize, and read rights.
*   **MEMBER**: Read-only access; mutations return `403 Forbidden`.
*   **Non-member / Cross-business**: Returns `404 Not Found` (anti-enumeration pattern).

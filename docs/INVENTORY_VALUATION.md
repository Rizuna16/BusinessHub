# Feature #38 — Inventory Valuation & COGS

**Status:** LOCKED

## 1. Purpose & Scope

Feature #38 implements perpetual Moving Average Costing (MAC) for inventory valuation and Cost of Goods Sold (COGS) calculation. It provides a cost-state tracking layer that sits alongside the existing physical inventory engine (#13), recording the financial cost impact of every inventory transaction.

## 2. Dependencies

| Dependency | Feature # | Relationship |
|---|---|---|
| Inventory Stock Foundation | #13 | Required — physical stock movements |
| Purchase Foundation | #17 | Required — purchase line pricing |
| Purchase Return Foundation | #19 | Required — return cost reversal |
| Receiving Foundation | #18 | Required — receiving does NOT post cost (boundary) |
| Sales Foundation | #22 | Required — sales line COGS derivation |
| Sales Return Foundation | #25 | Required — return cost restoration |
| Sales → Inventory Integration | #24 | Required — sale movement triggers COGS |
| Stock Opname | #14 | Required — opname cost sync |
| Accounting Integration | #34 | Required — journal posting for sales/purchase finalization |

## 3. Architecture Boundary

Feature #38 is a **cost valuation layer** that runs alongside physical inventory movements. It:

- Records cost state changes for every inventory-affecting transaction.
- Provides Moving Average Cost (MAC) for COGS derivation on sales.
- Provides historical cost snapshots for sales returns and purchase returns.
- Does NOT own physical stock movements (owned by #13, #24).
- Does NOT own journal entries (owned by #34).
- Does NOT own fiscal period logic (owned by #35).

## 4. Core Entities

### 4.1 InventoryCostState

**Schema:** `InventoryCostStateInDB` (`backend/app/modules/inventory/schemas.py` line 251)

| Field | Type | Description |
|---|---|---|
| `id` | `str` | UUID |
| `business_id` | `str` | Tenant scope |
| `product_id` | `str` | Product |
| `variant_id` | `Optional[str]` | Variant (nullable for product-level) |
| `quantity` | `Decimal` | Valuation quantity (mirrors physical stock) |
| `total_cost` | `Decimal` | Total cost of quantity on hand |
| `unit_cost` | `Decimal` | Moving Average Cost per unit |
| `created_at` | `datetime` | |
| `updated_at` | `datetime` | |

**Composite key:** `(business_id, product_id, variant_id)` — enforced by in-memory repository.

### 4.2 InventoryCostMovement

**Schema:** `InventoryCostMovementInDB` (`backend/app/modules/inventory/schemas.py` line 274)

| Field | Type | Description |
|---|---|---|
| `id` | `str` | UUID |
| `business_id` | `str` | Tenant scope |
| `product_id` | `str` | Product |
| `variant_id` | `Optional[str]` | Variant |
| `movement_type` | `InventoryCostMovementType` | Type of cost event |
| `reference_type` | `Optional[str]` | Source entity type |
| `reference_id` | `Optional[str]` | Source entity ID |
| `quantity_delta` | `Decimal` | Quantity change |
| `cost_delta` | `Decimal` | Cost change |
| `unit_cost_at_time` | `Decimal` | MAC at the time of this movement |
| `created_at` | `datetime` | |

**Movement Types:**

| Type | Meaning |
|---|---|
| `PURCHASE_IN` | Purchase finalization adds inventory |
| `PURCHASE_RETURN_OUT` | Purchase return removes inventory |
| `SALE_OUT` | Sale finalization removes inventory |
| `SALE_RETURN_IN` | Sales return adds inventory back |
| `OPENING_BALANCE` | Initial stock with optional unit cost |
| `OPNAME_SYNC` | Stock opname adjustment |

### 4.3 ValuationSummaryItem / ValuationSummaryResponse

**Schema:** `backend/app/modules/inventory/schemas.py` lines 290–302

Used by the valuation summary endpoint. Contains `product_id`, `product_name`, `variant_id`, `variant_name`, `total_quantity`, `unit_cost`, `total_cost`, and `total_inventory_value`.

## 5. Moving Average Cost (MAC) Formula

### 5.1 Inbound (Purchase / Opening Balance / Sales Return)

```
inbound_total_cost = inbound_qty × inbound_unit_cost
new_qty = current_qty + inbound_qty
new_total_cost = current_total_cost + inbound_total_cost
new_mac = new_total_cost / new_qty  (if new_qty > 0, else 0)
```

**Source:** `record_cost_inbound` in `backend/app/modules/inventory/service.py` lines 835–883.

### 5.2 Outbound (Sale / Purchase Return)

```
cost_deduction = outbound_qty × unit_cost
new_qty = current_qty - outbound_qty
new_total_cost = current_total_cost - cost_deduction
```

If `new_qty <= 0`: `new_qty = 0`, `new_total_cost = 0`.
If `new_total_cost < 0` but `new_qty > 0`: `new_total_cost = 0` (MAC preserved from current state).

**Source:** `record_cost_outbound` in `backend/app/modules/inventory/service.py` lines 885–935.

### 5.3 Stock Opname Sync

When stock opname finalizes, the cost state quantity is synchronized to the new physical quantity:

```
new_total_cost = new_physical_qty × current_mac
```

If `new_physical_qty <= 0` or `mac <= 0`: `new_total_cost = 0`.

**Source:** `sync_opname_cost_state` in `backend/app/modules/inventory/service.py` lines 937–976.

## 6. Transaction Boundaries

### 6.1 Purchase Finalization

When a purchase is finalized:
1. Physical stock is increased (Feature #13/17).
2. Cost state is updated via `record_cost_inbound` with type `PURCHASE_IN`.
3. Accounting journal is posted (Feature #34): `Dr 1300 Inventory / Cr 2100 AP`.

**Receiving does NOT post cost.** Receiving is a physical receipt boundary; cost is tracked only at purchase finalization.

### 6.2 Sale Finalization

When a sale is finalized:
1. Physical stock is decreased (Feature #24).
2. COGS is computed using the current MAC at the time of sale.
3. Cost state is updated via `record_cost_outbound` with type `SALE_OUT`.
4. Accounting journal is posted (Feature #34): `Dr 1200 AR / Cr 4100 Revenue`, `Dr 5200 COGS / Cr 1300 Inventory`.

**SalesLine cost snapshot:** Each `SalesLineInDB` stores `unit_cost_snapshot` and `cost_total_snapshot` at finalization time, preserving historical cost even if MAC changes subsequently.

### 6.3 Sales Return

When a sales return is finalized:
1. Physical stock is restored (Feature #25).
2. Cost state is updated via `record_cost_inbound` with type `SALE_RETURN_IN`.
3. The historical cost (from the original `SalesLine.unit_cost_snapshot`) is used for the cost restoration.
4. Accounting journal is posted (Feature #34): reverses revenue and COGS.

### 6.4 Purchase Return

When a purchase return is finalized:
1. Physical stock is reduced.
2. Cost state is updated via `record_cost_outbound` with type `PURCHASE_RETURN_OUT`.
3. The historical acquisition cost (from the original purchase line) is used for cost deduction.
4. Accounting journal is posted (Feature #34): `Dr 2100 AP / Cr 1300 Inventory`.

### 6.5 Stock Opname

When a stock opname is finalized:
1. Physical stock is adjusted via variance movements.
2. Cost state quantity is synced via `sync_opname_cost_state`.
3. **No accounting journal is posted for opname.** Cost sync is operational only.

### 6.6 Opening Balance

When opening balance is created:
1. Physical stock is set.
2. Cost state is initialized:
   - If `unit_cost > 0`: `record_cost_inbound` with type `OPENING_BALANCE`.
   - If `unit_cost` not provided or 0: cost state is initialized with `unit_cost = 0.0000`.

## 7. Physical/Cost Identity

Physical stock identity: `(business_id, inventory_location_id, product_id, variant_id)` — per location.

Cost state identity: `(business_id, product_id, variant_id)` — per product, NOT per location.

This means cost is aggregated across locations. If the same product exists in multiple locations, the MAC is shared.

## 8. Mismatch Protection

`validate_physical_cost_consistency` (`backend/app/modules/inventory/service.py` line 814) enforces that the cost state quantity matches the physical stock quantity. If they differ when a cost state exists, it raises HTTP 409 Conflict with `INVENTORY_VALUATION_MISMATCH`.

## 9. Idempotency

Purchase and sale finalization include idempotency checks:
- Purchase: Verifies no prior `PURCHASE_IN` cost movement exists for the same `reference_id`.
- Sale: Verifies no prior `SALE_OUT` cost movement exists for the same `reference_id`.

Duplicate finalization attempts are rejected without double-counting.

## 10. Business Scoping

All cost states and cost movements are scoped to `business_id`. Cross-business cost access is rejected.

## 11. Frontend

- **Valuation Summary Page:** `frontend/src/pages/Inventory.tsx` includes valuation summary display.
- **API Method:** `apiClient.getValuationSummary(businessId)` → `GET /api/v1/businesses/{business_id}/inventory/valuation`
- **Types:** `ValuationSummaryResponse` and `ValuationSummaryItem` in `frontend/src/types/inventory.ts`.

## 12. Tests

**File:** `backend/tests/test_inventory_valuation.py`

| # | Test Name | Coverage |
|---|---|---|
| 1 | `test_purchase_finalize_updates_stock_and_cost` | Purchase inbound cost |
| 2 | `test_purchase_mac_average_after_second_receipt` | MAC recalculation |
| 3 | `test_purchase_zero_quantity_rule_not_triggered` | Zero quantity boundary |
| 4 | `test_receiving_does_not_post_accounting_journal` | Receiving boundary |
| 5 | `test_sales_finalize_posts_5_line_balanced_journal` | Sales COGS journal |
| 6 | `test_sales_insufficient_stock_400` | Stock validation |
| 7 | `test_sales_return_restores_stock_and_cost` | Sales return cost |
| 8 | `test_purchase_return_deducts_historical_cost` | Purchase return cost |
| 9 | `test_physical_cost_mismatch_returns_409` | Mismatch protection |
| 10 | `test_opname_sync_adjusts_cost_without_journal` | Opname cost sync |
| 11 | `test_opening_balance_with_unit_cost` | Opening balance with cost |
| 12 | `test_opening_balance_without_unit_cost_no_valuation` | Opening balance without cost |
| 13 | `test_purchase_finalize_idempotent` | Purchase idempotency |
| 14 | `test_sales_finalize_idempotent` | Sale idempotency |
| 15 | `test_cost_state_isolated_per_business` | Business isolation |
| 16 | `test_zero_quantity_rule_on_full_sale` | Full sale zero quantity |

**Total:** 16 tests

## 13. Limitations

- **No FIFO or Weighted Average**: Only Moving Average Costing is implemented.
- **No location-level costing**: Cost is aggregated per product/variant across all locations.
- **No multi-currency costing**: Currency defaults to IDR.
- **No batch/expiry/serial tracking**: Not in scope.
- **PostgreSQL runtime not verified**: In-memory execution only.
- **Opname does not post accounting journals**: Cost sync is operational only.

## 14. Source References

| Component | File | Lines |
|---|---|---|
| InventoryCostState schema | `backend/app/modules/inventory/schemas.py` | 251–262 |
| InventoryCostMovement schema | `backend/app/modules/inventory/schemas.py` | 265–287 |
| ValuationSummaryItem schema | `backend/app/modules/inventory/schemas.py` | 290–298 |
| MAC inbound formula | `backend/app/modules/inventory/service.py` | 835–883 |
| MAC outbound formula | `backend/app/modules/inventory/service.py` | 885–935 |
| Opname cost sync | `backend/app/modules/inventory/service.py` | 937–976 |
| Mismatch validation | `backend/app/modules/inventory/service.py` | 814–827 |
| Valuation summary | `backend/app/modules/inventory/service.py` | 978–1010 |
| Cost repository (abstract) | `backend/app/modules/inventory/repository.py` | 115–159 |
| Cost repository (in-memory) | `backend/app/modules/inventory/repository.py` | 393–489 |
| Tests | `backend/tests/test_inventory_valuation.py` | 1–920 |

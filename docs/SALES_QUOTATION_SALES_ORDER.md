# Sales Quotation & Sales Order (Feature #53)

## Overview
Feature #53 introduces pre-sales quotation and sales order workflows with **Hard Available-Stock Reservation** to BusinessHub. It establishes formal commercial lifecycle management from initial prospect engagement to confirmed commitments and physical fulfillment.

## Core Principles
1. **Hard Allocation:** Confirmed Sales Orders reserve inventory. Reserved inventory cannot be consumed by ad-hoc retail POS checkout or direct sales.
2. **Canonical Formula:** `available_to_sell = physical_on_hand - active_reserved_quantity` (`>= 0`).
3. **Quotation Exemption:** Quotations are purely commercial proposals and **never** reserve inventory or create accounting entries.
4. **Zero Impact on Valuation & Stock Cards:** Reservations do not generate `StockMovement` records or affect MAC / COGS calculations.
5. **Concurrency Protection:** Process-wide `threading.RLock()` ensures thread-safe TOCTOU execution across checkouts, sales, confirmations, fulfillments, returns, and opnames.

---

## Hard Reservation Enforcement

Every physical-stock OUT consumer enforces the reservation invariant:

| Consumer | Behavior |
|---|---|
| **Checkout / Direct Sales** | Validates `available_to_sell` before physical deduction. Rejects if insufficient. |
| **Sales Order Confirmation** | Validates `available_to_sell` under shared lock, then creates reservation. |
| **Sales Order Fulfillment** | Deducts physical stock and fulfills/releases reservation atomically. |
| **Sales Order Cancellation** | Releases all active reservations, restoring available stock. |
| **Purchase Return** | Validates `available_to_sell` before physical deduction. Rejects if insufficient. |
| **Stock Opname (negative)** | Rejects if `new_physical < active_reserved_quantity`. |

### Reservation Invariants
- `active_reserved_quantity <= physical_on_hand`
- `available_to_sell >= 0`
- Reservation never creates `StockMovement`, valuation movement, or accounting entry.
- No silent reservation reduction/proration by Stock Opname.

---

## Quotation Domain
- **Lifecycle:** `DRAFT` → `SENT` → `ACCEPTED` | `REJECTED` | `EXPIRED` → `CANCELLED` → `CONVERTED`.
- **Immutability:** Once `ACCEPTED`, `REJECTED`, `EXPIRED`, `CANCELLED`, or `CONVERTED`, quotations are strictly immutable.
- **Conversion:** Accepted quotations convert into exactly one Sales Order idempotently.

---

## Sales Order Domain & Hard Reservation
- **Lifecycle:** `DRAFT` → `CONFIRMED` → `PARTIALLY_FULFILLED` → `FULFILLED` | `CANCELLED`.
- **Confirmation:** Transitioning an order to `CONFIRMED` validates stock availability against `available_to_sell`, creates `SalesOrderReservation` records (`ACTIVE`), and locks the committed stock.
- **Cancellation:** Cancelling a confirmed order releases all active reservations, instantly restoring available-to-sell stock.
- **Fulfillment:** Fulfilling order lines deducts physical inventory via existing sales integration, posts accounting journals, and fulfills/releases active reservations.

---

## Concurrency

All physical stock mutations and reservation checks acquire a process-wide `threading.RLock()` to protect the TOCTOU sequence:

```
READ physical stock
→ READ reservations
→ VALIDATE available >= requested
→ MUTATE (deduct physical or create reservation)
```

This prevents concurrent checkout and order confirmation from double-allocating the same stock.

**In-memory limitation:** The lock only persists for the current process lifetime. After a server restart, all reservations are lost. This is an acceptable limitation for the current in-memory architecture.

---

## Accounting Boundary
- Quotation: **zero accounting**
- Sales Order creation: **zero accounting**
- Sales Order confirmation: **zero accounting**
- Reservation: **zero accounting**
- Only fulfillment/finalized Sale creates existing economic effects
- Purchase Return and Stock Opname preserve their existing accounting semantics

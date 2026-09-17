# Delivery Note / Surat Jalan (Feature #54)

## Overview

Feature #54 introduces a logistics and document tracking layer for Sales Orders. It enables multi-batch partial and full delivery tracking without modifying inventory balances, valuations, stock cards, accounting, or reservations.

## Core Principles

1. **Document Layer Only:** Delivery Note is purely a logistics and dispatch document. It does NOT create inventory deductions, StockMovement records, InventoryCostState mutations, COGS, revenue, accounting entries, or reservation mutations.
2. **Sales Order Driven:** Delivery Notes are created against a confirmed Sales Order. Quantities are limited to the already-fulfilled quantity.
3. **Multi-Batch Support:** One Sales Order may have multiple Delivery Notes representing different dispatch batches.
4. **Zero Economic Impact:** Creating, readying, delivering, or cancelling a Delivery Note has zero impact on inventory, accounting, or reservations.

## Domain Model

### Delivery Note

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Unique identifier |
| `business_id` | `str` | Tenant scope |
| `branch_id` | `str` | Branch scope |
| `delivery_number` | `str` | Sequential document number (DN-XXXXXX) |
| `sales_order_id` | `str` | Linked Sales Order |
| `customer_id` | `str` | Optional customer |
| `delivery_date` | `datetime` | Dispatch date |
| `status` | `DeliveryNoteStatus` | Lifecycle state |
| `shipping_address` | `str` | Destination address |
| `recipient_name` | `str` | Recipient contact |
| `recipient_phone` | `str` | Recipient phone |
| `notes` | `str` | Admin notes |
| `lines` | `List[DeliveryNoteLine]` | Line items |
| `created_at` | `datetime` | Creation timestamp |
| `updated_at` | `datetime` | Last update timestamp |

### Delivery Note Line

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Unique identifier |
| `delivery_note_id` | `str` | Parent Delivery Note |
| `sales_order_line_id` | `str` | Reference to Sales Order line |
| `product_id` | `str` | Product identifier |
| `variant_id` | `str` | Optional variant |
| `product_name_snapshot` | `str` | Historical product name |
| `variant_snapshot` | `str` | Historical variant info |
| `ordered_quantity_snapshot` | `Decimal` | Snapshot of ordered quantity |
| `fulfilled_quantity_snapshot` | `Decimal` | Snapshot of fulfilled quantity |
| `delivery_quantity` | `Decimal` | Quantity being delivered |
| `unit` | `str` | Unit symbol |
| `notes` | `str` | Line notes |

## Lifecycle

```
DRAFT → READY → DELIVERED
DRAFT → CANCELLED
READY → CANCELLED
```

### States

- **DRAFT**: Editable header and lines. Lines and quantities can be modified.
- **READY**: Prepared for dispatch. Lines are frozen. Critical fields immutable.
- **DELIVERED**: Finalized logistics record. Fully immutable.
- **CANCELLED**: Terminal state. Fully immutable. Document number preserved.

### Transitions

| From | To | Allowed |
|------|----|---------|
| DRAFT | READY | Yes |
| DRAFT | CANCELLED | Yes |
| READY | DELIVERED | Yes |
| READY | CANCELLED | Yes |
| DELIVERED | * | No (terminal) |
| CANCELLED | * | No (terminal) |

No DELETE endpoint. Cancellation preserves the record.

## Sales Order Relationship

- One Sales Order → Many Delivery Notes
- A Delivery Note references exactly one Sales Order
- Eligible Sales Order statuses: `CONFIRMED`, `PARTIALLY_FULFILLED`, `FULFILLED`

## Quantity Model

For each Sales Order line:

```
active_documented_quantity = sum(delivery_quantity for non-CANCELLED Delivery Notes)
remaining_delivery_quantity = fulfilled_quantity - active_documented_quantity
```

### Invariants

```
0 <= active_documented_quantity <= fulfilled_quantity <= ordered_quantity
```

New Delivery Note quantity must satisfy:

```
0 < requested_quantity <= remaining_delivery_quantity
```

### Example

```
Sales Order: 10 ordered, 8 fulfilled
Delivery Note #1: 3 delivered (active)
Delivery Note #2: 2 delivered (active)
Remaining: 8 - 5 = 3

Delivery Note #3 (requested 4): REJECTED (exceeds remaining 3)
Delivery Note #3 (requested 3): ACCEPTED

If Delivery Note #1 is CANCELLED:
Active: 2
Remaining: 8 - 2 = 6
```

## Cancellation Behavior

- Cancelled Delivery Notes do NOT count toward active documented quantity
- Their quantities become available for new Delivery Notes
- Historical record is preserved with delivery number intact

## Inventory Boundary

**ZERO inventory mutation.**

Delivery Note does NOT:
- Call `InventoryService.deduct_sales_stock`
- Create `StockMovement` records
- Mutate `StockBalance`
- Record `InventoryCostMovement`
- Mutate `InventoryCostState`

Physical inventory deduction occurs exclusively at Sales Order fulfillment.

## Accounting Boundary

**ZERO accounting.**

Delivery Note does NOT create:
- Revenue journals
- COGS entries
- AR postings
- Tax calculations
- Payment records

Accounting occurs exclusively when the underlying Sales Order is fulfilled.

## Reservation Boundary

**ZERO reservation mutation.**

Delivery Note does NOT:
- Create reservations
- Consume reservations
- Release reservations
- Modify available stock

Reservations remain exclusively managed by Feature #53.

## Stock Card Boundary

**Zero StockMovement.**

Only physical inventory events create StockMovement records. Delivery Notes are logistics documents only.

## Valuation Boundary

**Zero InventoryCostMovement.**

MAC (Moving Average Cost) calculations remain bound to fulfillment. Delivery Notes do not affect product valuation.

## Document Numbering

Sequential per business using the existing in-memory repository pattern:

- Prefix: `DN-`
- Format: `DN-000001`, `DN-000002`, etc.
- Business-scoped (no cross-business collision)
- No reuse after cancellation

## Security / RBAC

### Required

- Authenticated account
- Active business membership
- Business scope (`business_id` verified on all operations)

### Roles

| Role | Create | Edit (DRAFT) | Ready | Deliver | Cancel | Read |
|------|--------|--------------|-------|---------|--------|------|
| OWNER | Yes | Yes | Yes | Yes | Yes | Yes |
| ADMIN | Yes | Yes | Yes | Yes | Yes | Yes |
| MEMBER | No | No | No | No | No | Yes |

### IDOR Prevention

Every operation validates that all referenced entities belong to the active business:
- Sales Order ID
- Sales Order Line ID
- Customer ID
- Branch ID
- Delivery Note ID

## Concurrency

Protected by the shared process-wide `threading.RLock()` to prevent concurrent over-delivery race conditions. The lock protects the entire read → calculate → validate → create sequence for Delivery Note quantity allocation.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/businesses/{business_id}/delivery-notes` | List delivery notes |
| `POST` | `/api/v1/businesses/{business_id}/delivery-notes` | Create delivery note |
| `GET` | `/api/v1/businesses/{business_id}/delivery-notes/{delivery_note_id}` | Get delivery note |
| `PUT` | `/api/v1/businesses/{business_id}/delivery-notes/{delivery_note_id}` | Update delivery note |
| `POST` | `/api/v1/businesses/{business_id}/delivery-notes/{delivery_note_id}/lines` | Add line |
| `DELETE` | `/api/v1/businesses/{business_id}/delivery-notes/{delivery_note_id}/lines/{line_id}` | Delete line |
| `POST` | `/api/v1/businesses/{business_id}/delivery-notes/{delivery_note_id}/ready` | Mark as READY |
| `POST` | `/api/v1/businesses/{business_id}/delivery-notes/{delivery_note_id}/deliver` | Mark as DELIVERED |
| `POST` | `/api/v1/businesses/{business_id}/delivery-notes/{delivery_note_id}/cancel` | Cancel |

## Error Codes

| Code | Description |
|------|-------------|
| `DELIVERY_NOTE_NOT_FOUND` | Delivery Note not found |
| `DELIVERY_NOTE_INVALID_STATUS` | Invalid status transition |
| `DELIVERY_NOTE_LINE_NOT_FOUND` | Line not found |
| `DELIVERY_NOTE_INVALID_QUANTITY` | Quantity must be positive |
| `DELIVERY_NOTE_QUANTITY_EXCEEDS_REMAINING` | Exceeds remaining deliverable quantity |
| `DELIVERY_NOTE_SALES_ORDER_INVALID` | Sales Order status not eligible |
| `DELIVERY_NOTE_ALREADY_CANCELLED` | Already cancelled |
| `DELIVERY_NOTE_BUSINESS_MISMATCH` | Cross-business access attempt |

## Limitations

- **In-memory persistence:** All data is lost on server restart. Active reservations, delivery notes, and sequences reset.
- **No parallel batch processing:** Sequential document creation is protected by a process-wide lock but does not scale horizontally.
- **No PDF generation:** Printable view uses browser print styling only.
- **No external shipping integration:** No courier API, barcode scanning, or route optimization.

## Architecture Compliance

- ✅ No PostgreSQL/SQLAlchemy/Prisma/Alembic
- ✅ No DATABASE_URL
- ✅ No microservices
- ✅ FastAPI + Python + In-memory repositories
- ✅ Existing BusinessHub patterns
- ✅ No Feature #53 redesign
- ✅ Zero inventory/accounting/reservation impact

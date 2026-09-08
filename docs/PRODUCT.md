# BusinessHub — Product Master (Feature #9)

## Overview

The Product Master module provides the core definition of goods and services owned by a Business (tenant). It serves as the master foundation for future modules such as Inventory, Purchase, Sales, Hotel, Retail, UMKM, and Production without coupling or pre-implementing business logic for those downstream modules.

---

## Domain Model

- **Product**:
  - `id`: Unique UUID
  - `business_id`: Tenant boundary
  - `category_id`: Optional reference to a Feature #8 Category belonging to the same business
  - `unit_id`: Mandatory reference to a Feature #8 Unit belonging to the same business
  - `name`: Non-empty product name (trimmed)
  - `code`: Business-scoped, case-insensitive unique product code (e.g., `PRD-001`)
  - `description`: Optional plain text description
  - `product_type`: `GOODS` or `SERVICE`
  - `status`: `ACTIVE` or `ARCHIVED`
  - `created_at`: Timestamp
  - `updated_at`: Timestamp

---

## Product Types

1. **GOODS**: Physical items that can conceptually hold inventory in future modules.
2. **SERVICE**: Non-physical offerings (e.g., laundry, consultation, breakfast package).

---

## Lifecycle & Status

- **ACTIVE → ARCHIVED**: Soft archive via `DELETE /api/v1/businesses/{business_id}/products/{product_id}`.
- Archived products are preserved with their IDs and business associations but are excluded from default active listings and cannot be used as new active references.

---

## Product Code Rules

- Required, normalized, and case-insensitive unique within the same business.
- Stable and server-validated; does not change automatically when the product name changes.

---

## Relationship Semantics

- **Category**: Optional single category classification. Must belong to the same business and be active.
- **Unit**: Mandatory default operational unit definition. Must belong to the same business and be active. No unit conversion engine is implemented in Feature #9.

---

## Security & Authorization

- **Authentication**: JWT Bearer token required.
- **Membership**: Requires active `BusinessMembership`.
- **Role Permissions**:
  - `OWNER` / `ADMIN`: Create, Read, Update, Archive
  - `MEMBER`: Read only
  - `SUSPENDED` / `REMOVED` / No Membership: Denied
- **Tenant Isolation**: Strictly enforced via path `business_id`. Cross-business reference assignments (categories/units) and path spoofing are blocked.

---

## API Endpoints

- `POST /api/v1/businesses/{business_id}/products`
- `GET /api/v1/businesses/{business_id}/products`
- `GET /api/v1/businesses/{business_id}/products/{product_id}`
- `PATCH /api/v1/businesses/{business_id}/products/{product_id}`
- `DELETE /api/v1/businesses/{business_id}/products/{product_id}`

---

## Explicitly Deferred Features (Not Implemented)

- Product Variant
- Barcode
- SKU Generation Engine
- Pricing Engine / Price List
- Promotion / Discount Engine
- Inventory / Stock / Warehouse
- Purchase / Sales / Transactions
- Customer / Supplier
- Tax Engine / Accounting / BOM
- Subscription / Billing / Midtrans

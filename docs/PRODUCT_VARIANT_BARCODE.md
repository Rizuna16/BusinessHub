# BusinessHub — Product Variant & Barcode (Feature #10)

## Overview

The Product Variant & Barcode module extends the core Product Master domain by adding concrete product variations and external barcode identifiers for Business tenants, while maintaining modularity and preventing scope creep into inventory or pricing engines.

---

## Domain Models

### Product Variant
- `id`: Unique UUID
- `business_id`: Tenant boundary
- `product_id`: Reference to parent Product
- `name`: Variant display name (e.g. `Black / Small`)
- `code`: Business-scoped, case-insensitive unique variant code (e.g. `TSHIRT-BLK-S`)
- `attributes`: Flexible JSON dictionary (e.g. `{"color": "Black", "size": "S"}`) for descriptive metadata
- `status`: `ACTIVE` or `ARCHIVED`
- `created_at`: Timestamp
- `updated_at`: Timestamp

### Barcode
- `id`: Unique UUID
- `business_id`: Tenant boundary
- `product_id`: Optional reference to Product (Product-level barcode)
- `variant_id`: Optional reference to Product Variant (Variant-level barcode)
- `code`: Business-scoped, case-insensitive unique barcode string preserving leading zeros
- `barcode_type`: `EAN13`, `EAN8`, `UPC_A`, `CODE128`, `OTHER`
- `status`: `ACTIVE` or `ARCHIVED`
- `created_at`: Timestamp
- `updated_at`: Timestamp

---

## Domain Rules & Restrictions

1. **GOODS-Only Variants**: Product Variants can ONLY be created for products where `product_type == "GOODS"`. Attempting to create variants for `SERVICE` products is rejected with HTTP 400.
2. **Barcode Target Exclusivity**: A Barcode MUST point to EXACTLY ONE target: either `product_id` OR `variant_id`. Creating a barcode with both or neither target is rejected.
3. **Leading Zeros**: Barcode `code` values are preserved as exact strings (e.g. `0123456789012`).
4. **Independent Lifecycle**: Soft archive (`ACTIVE → ARCHIVED`) via `DELETE` endpoints. Archiving a Product does not automatically cascade to variants, but prevents creating new active variants or assigning archived targets.

---

## Security & Authorization

- **Authentication**: Mandatory JWT Bearer token.
- **Role Permissions**:
  - `OWNER` / `ADMIN`: Create, Read, Update, Archive
  - `MEMBER`: Read only
  - `SUSPENDED` / `REMOVED` / No Membership: Access denied
- **Tenant & Path Boundary Validation**: All requests validate full hierarchy (`Business -> Product -> Variant` and `Business -> Target -> Barcode`). Cross-business targets and path spoofing are prevented.

---

## API Endpoints

### Product Variant
- `POST /api/v1/businesses/{business_id}/products/{product_id}/variants`
- `GET /api/v1/businesses/{business_id}/products/{product_id}/variants`
- `GET /api/v1/businesses/{business_id}/products/{product_id}/variants/{variant_id}`
- `PATCH /api/v1/businesses/{business_id}/products/{product_id}/variants/{variant_id}`
- `DELETE /api/v1/businesses/{business_id}/products/{product_id}/variants/{variant_id}`

### Barcode
- `POST /api/v1/businesses/{business_id}/barcodes`
- `GET /api/v1/businesses/{business_id}/barcodes`
- `GET /api/v1/businesses/{business_id}/barcodes/{barcode_id}`
- `PATCH /api/v1/businesses/{business_id}/barcodes/{barcode_id}`
- `DELETE /api/v1/businesses/{business_id}/barcodes/{barcode_id}`

---

## Explicitly Deferred Features

- Pricing Engine / Price List
- Inventory / Stock / Warehouse
- Barcode Scanner / Generator Engine
- Purchase / Sales / Promotions / Discounts
- BOM / Production / Subscription / Billing

# BusinessHub — Product Pricing & Price List (Feature #11)

## Overview

The Product Pricing & Price List module provides a structured, multi-tenant pricing foundation for BusinessHub. It allows businesses to organize product and variant prices into currency-aware price lists with effective periods and strict tenant isolation.

---

## Domain Concepts

### 1. Price List
A container or group of prices within a Business (e.g. Retail, Wholesale, Marketplace).
- `id`: Unique UUID
- `business_id`: Tenant boundary
- `name`: Display name (non-empty)
- `code`: Business-scoped, case-insensitive unique code (e.g. `RETAIL`)
- `description`: Optional plain text
- `currency`: Supported ISO currency code (IDR, USD, SGD, MYR, EUR, JPY). Default: `IDR`
- `status`: `ACTIVE` or `ARCHIVED`
- `is_default`: Boolean indicating the default price list for the business. Automatically assigned to the first active list created. When default is archived, reassigns deterministically to the oldest active list.

### 2. Price Entry
An individual price record associated with a specific Price List.
- `id`: Unique UUID
- `business_id`: Tenant boundary
- `price_list_id`: Parent Price List ID
- `product_id`: Optional reference to Product (Product price)
- `variant_id`: Optional reference to Product Variant (Variant price)
- `amount`: Non-negative Decimal value (stored and processed without floating point errors)
- `currency`: Currency inherited from parent Price List
- `effective_from`: Timezone-aware start timestamp
- `effective_to`: Optional end timestamp (`effective_to >= effective_from`)
- `status`: `ACTIVE` or `ARCHIVED`

---

## Domain Rules & Invariants

1. **Target Exclusivity**: Each Price Entry must point to EXACTLY ONE target (`product_id XOR variant_id`).
2. **Variant Pricing Constraints**: Variant target pricing is restricted to active variants whose parent product is an active `GOODS` product in the same business.
3. **Currency Consistency**: Price Entries inherit and match the currency of their parent Price List. Changing currency on a Price List with existing entries is forbidden.
4. **Overlap Protection**: Active price entries for the same target and price list CANNOT have overlapping effective periods.
5. **Historical Integrity**: Hard deletes are forbidden. Soft archiving (`ACTIVE → ARCHIVED`) preserves complete historical pricing records.
6. **Immutable Fields**: Target (`product_id`, `variant_id`), `price_list_id`, and `business_id` are immutable on existing price entries.

---

## Security & Authorization

- **Authentication**: Mandatory JWT Bearer token.
- **Role Matrix**:
  - `OWNER` / `ADMIN`: Full CRUD on Price Lists and Price Entries.
  - `MEMBER`: Read-only.
  - `SUSPENDED` / `REMOVED` / Non-Member: Access denied.
- **Tenant Isolation**: Strictly enforced via path `/businesses/{business_id}/...`. All cross-business target assignments and path spoofing are blocked.

---

## API Endpoints

### Price Lists
- `POST /api/v1/businesses/{business_id}/price-lists`
- `GET /api/v1/businesses/{business_id}/price-lists`
- `GET /api/v1/businesses/{business_id}/price-lists/{price_list_id}`
- `PATCH /api/v1/businesses/{business_id}/price-lists/{price_list_id}`
- `DELETE /api/v1/businesses/{business_id}/price-lists/{price_list_id}`

### Price Entries
- `POST /api/v1/businesses/{business_id}/price-lists/{price_list_id}/prices`
- `GET /api/v1/businesses/{business_id}/price-lists/{price_list_id}/prices`
- `GET /api/v1/businesses/{business_id}/price-lists/{price_list_id}/prices/{price_id}`
- `PATCH /api/v1/businesses/{business_id}/price-lists/{price_list_id}/prices/{price_id}`
- `DELETE /api/v1/businesses/{business_id}/price-lists/{price_list_id}/prices/{price_id}`

---

## Explicitly Deferred Features (Out of Scope)

- Sales Checkout / Cashier / Cart engine
- Discount Engine / Promotions / Vouchers
- Tax Engine / Dynamic Pricing
- Customer-specific or Loyalty Pricing
- Currency Conversion / Exchange Rate Engine

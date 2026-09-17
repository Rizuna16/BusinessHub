# WAREHOUSE & INVENTORY LOCATION FOUNDATION

> Feature #12 — Warehouse & Inventory Location. Location foundation only.
> **DOES NOT** contain stock, inventory movement, or any stock-related features.

---

## 1. Overview

Feature #12 builds the foundation of storage locations for BusinessHub.  
It defines:

- **Warehouse** — operational location where inventory will eventually reside.
- **Inventory Location** — a sub-location inside a Warehouse used to classify
  where items are physically stored (e.g. RACK-A, RECEIVING, STORAGE).

This feature establishes the full relationship chain:

```
Business
   ↓
Branch (optional)
   ↓
Warehouse
   ↓
Inventory Location
```

And also supports the simpler relationship without a branch:

```
Business
   ↓
Warehouse
   ↓
Inventory Location
```

---

## 2. Domain Model

### 2.1 Warehouse

| Field        | Type             | Notes                            |
|--------------|------------------|----------------------------------|
| id           | string (UUID)    | Auto-generated                   |
| business_id  | string           | Required — from authenticated context |
| branch_id    | string or null   | Optional — nullable              |
| name         | string           | Required, trimmed, max 100 chars |
| code         | string           | Required, trimmed, upper-cased, max 50 chars, case-insensitive unique within Business |
| description  | string or null   | Max 500 chars                    |
| address      | string or null   | Max 500 chars                    |
| phone        | string or null   | Max 30 chars                     |
| email        | string or null   | Max 100 chars                    |
| status       | enum             | `ACTIVE` / `SUSPENDED` / `ARCHIVED` |
| is_default   | boolean          | Controlled by service logic only |
| created_at   | datetime         | Auto-generated                   |
| updated_at   | datetime         | Auto-updated                     |

### 2.2 Inventory Location

| Field         | Type              | Notes                                   |
|---------------|-------------------|-----------------------------------------|
| id            | string (UUID)     | Auto-generated                          |
| business_id   | string            | Required — verified to match Warehouse.business_id |
| warehouse_id  | string            | Required — links to a Warehouse         |
| name          | string            | Required, trimmed, max 100 chars        |
| code          | string            | Required, trimmed, upper-cased, max 50 chars, case-insensitive unique within Warehouse |
| description   | string or null    | Max 500 chars                            |
| location_type | enum              | `GENERAL` / `RECEIVING` / `STORAGE` / `PICKING` / `SHIPPING` / `DAMAGED` / `QUARANTINE` / `OTHER` |
| status        | enum              | `ACTIVE` / `ARCHIVED`                   |
| is_default    | boolean           | Controlled by service logic only        |
| created_at    | datetime          | Auto-generated                          |
| updated_at    | datetime          | Auto-updated                            |

---

## 3. Business Relationship

- Every **Warehouse** must belong to exactly one **Business**.
- `business_id` is always derived from the authenticated route path
  (`/businesses/{business_id}/...`).
- The request body **cannot** provide `business_id`.
  If an attacker sends `business_id` in the body, it is **ignored**.

## 4. Branch Relationship

A Warehouse may or may not be tied to a Branch:

| Option | Diagram |
|--------|---------|
| A — Warehouse under Branch | Business → Branch → Warehouse → Location |
| B — Independent Warehouse | Business → Warehouse → Location |

If `branch_id` is provided in the create/update payload:

- Branch **must exist**.
- Branch **must be ACTIVE**.
- Branch `business_id` must equal Warehouse `business_id`.
- Cross-business Branch assignment is **rejected**.

## 5. Code Uniqueness

- **Warehouse code** is case-insensitive unique within the same Business.
- **Location code** is case-insensitive unique within the same Warehouse.
- Codes are normalized (trimmed + upper-cased) on write.
- Codes are **immutable** after creation.

Example:

```
Business A
  WH-MAIN
  wh-main  → rejected (same as WH-MAIN)
```

```
Warehouse A
  MAIN
  RACK-A
Warehouse B
  MAIN     → allowed (different warehouse)
```

## 6. Name Uniqueness

- Warehouse **name** is NOT globally unique but is **not** required to be.
- Duplicate codes within the same Business are rejected.

## 7. Default Warehouse & Location

### 7.1 Defaults — Business → Warehouse

Rules:

- Exactly **one** active default Warehouse per Business.
- The first active Warehouse created becomes the default.
- If the default Warehouse is **suspended or archived**, the next active
  Warehouse is deterministically chosen using:
  `created_at ASC, id ASC`.
- If no active Warehouse remains, `is_default = false` for all.

### 7.2 Defaults — Warehouse → Location

Rules:

- Exactly **one** active default Location per Warehouse.
- The first active Location created becomes the default.
- If the default Location is archived, the next active Location is chosen:
  `created_at ASC, id ASC`.
- If none remain, all `is_default = false`.

> Default fields are **never** accepted from the API request body.
> They are computed by the service layer.

## 8. Lifecycle

### 8.1 Warehouse Lifecycle

```
ACTIVE ──> SUSPENDED ──> ACTIVE
    │
    └──> ARCHIVED     (terminal)
```

Rules:

- **SUSPENDED** → can be re-activated via the `/activate` endpoint.
- **ARCHIVED** → is a soft-delete; cannot be reactivated via normal update.
- No hard delete is ever performed.

### 8.2 Inventory Location Lifecycle

```
ACTIVE ──> ARCHIVED   (terminal)
```

- Location archive is a soft-delete.
- Archived locations are excluded from active listing endpoints.

### 8.3 Warehouse Archive Behavior

When a Warehouse is archived:

- Existing Inventory Locations are **not** archived (historical kept).
- **No new locations** can be created under the archived Warehouse.
- **No locations** can be activated or updated under the archived Warehouse.

## 9. Location Type Classification

| Type        | Meaning (classification only — no inventory logic) |
|-------------|----------------------------------------------------|
| GENERAL     | Default general-purpose location                   |
| RECEIVING   | Goods receipt area                                |
| STORAGE     | Bulk storage area                                  |
| PICKING     | Order-picking zone                                |
| SHIPPING    | Dispatch/loading area                             |
| DAMAGED     | Damaged or defective goods                        |
| QUARANTINE  | Quarantine / inspection area                      |
| OTHER       | Any other custom location                         |

This is **classification only**. It does not trigger any inventory logic.

---

## 10. Membership Authorization

Reuses the existing `BusinessMembership` service with roles:

| Role   | Warehouse Action            | Location Action              |
|--------|-----------------------------|------------------------------|
| OWNER  | create, read, update, suspend, archive, default | create, read, update, archive, default |
| ADMIN  | create, read, update, suspend, archive, default | create, read, update, archive, default |
| MEMBER | read only                   | read only                    |

- **SUSPENDED** or **REMOVED** memberships are denied.
- **Non-members** are denied.

No new RBAC system is introduced.

---

## 11. Tenant Isolation

Strict tenant isolation is enforced on every endpoint:

- All routes include `/businesses/{business_id}` as the tenant boundary.
- JWT carries identity.
- `BusinessMembership` carries authorization.
- `request.body` carries data only — never authority.

Isolation guarantees:

| Scenario | Result        |
|----------|---------------|
| Business A reads Business B's Warehouse A | Rejected (404) |
| Path Business B / Warehouse A (owned by A) | Rejected (404) |
| Business A / Warehouse B / Location A (owned by A) | Rejected (404) |
| Body `{"business_id": "BUSINESS_B"}` | Ignored — server-derived context wins |

---

## 12. Security Test Matrix

| Scenario | Request                                         | Result |
|----------|-------------------------------------------------|--------|
| A        | Business B user → GET Warehouse A (in Biz A)    | Rejected |
| B        | Business B path / Warehouse A (owned by A)      | Rejected |
| C        | Business A path / Warehouse B / Location A (owned by A) | Rejected |
| D        | Body `{"business_id": "BUSINESS_B"}`            | Ignored |
| E        | Business A tries to assign Branch B (owned by Biz B) | Rejected |

---

## 13. Data Integrity Audit

Verified invariants:

1. `Warehouse.business_id != null`
2. If `Warehouse.branch_id` set → `Branch.business_id == Warehouse.business_id`
3. `InventoryLocation.business_id == Warehouse.business_id`
4. `InventoryLocation.warehouse_id → Warehouse` (must match and belong to same Business)
5. `Business → max 1 active default Warehouse`
6. `Warehouse → max 1 active default Location`
7. Lifecycle transitions never create invalid defaults.
8. Archived entities reject further mutations.
9. Immutable fields (`id`, `business_id`, `code`, `created_at`) cannot be spoofed via body.

---

## 14. API Endpoints

### Warehouse

| Method   | Path                                              | Purpose                  |
|----------|---------------------------------------------------|--------------------------|
| `POST`   | `/api/v1/businesses/{business_id}/warehouses`     | Create warehouse         |
| `GET`    | `/api/v1/businesses/{business_id}/warehouses`     | List warehouses          |
| `GET`    | `/api/v1/businesses/{business_id}/warehouses/{warehouse_id}` | Detail warehouse |
| `PATCH`  | `/api/v1/businesses/{business_id}/warehouses/{warehouse_id}` | Update         |
| `DELETE` | `/api/v1/businesses/{business_id}/warehouses/{warehouse_id}` | Archive        |
| `POST`   | `/api/v1/businesses/{business_id}/warehouses/{warehouse_id}/suspend` | Suspend |
| `POST`   | `/api/v1/businesses/{business_id}/warehouses/{warehouse_id}/activate` | Activate |

### Inventory Location

| Method   | Path                                                                          | Purpose              |
|----------|-------------------------------------------------------------------------------|----------------------|
| `POST`   | `/api/v1/businesses/{business_id}/warehouses/{warehouse_id}/locations`      | Create location      |
| `GET`    | `/api/v1/businesses/{business_id}/warehouses/{warehouse_id}/locations`        | List locations       |
| `GET`    | `/api/v1/businesses/{business_id}/warehouses/{warehouse_id}/locations/{location_id}` | Detail location |
| `PATCH`  | `/api/v1/businesses/{business_id}/warehouses/{warehouse_id}/locations/{location_id}` | Update       |
| `DELETE` | `/api/v1/businesses/{business_id}/warehouses/{warehouse_id}/locations/{location_id}` | Archive      |

### Request Body Authority Rules

- Create Warehouse body excludes: `business_id`, `status`, `is_default`, `id`, timestamps.
- Create Location body excludes: `business_id`, `warehouse_id`, `status`, `is_default`, `id`, timestamps.

---

## 15. Frontend

### Files

- `frontend/src/types/warehouse.ts` — type definitions.
- `frontend/src/pages/Warehouses.tsx` — list + create + edit + suspend/activate + archive.
- `frontend/src/pages/WarehouseDetail.tsx` — view warehouse + manage locations.
- `frontend/src/services/apiClient.ts` — added warehouse/location API methods.
- `frontend/src/app/routes.tsx` — added route constants + ProtectedRoute entries.

### Navigation Integration

- `BusinessDetail.tsx` includes a **Warehouse** button linking to:
  `/businesses/:businessId/warehouses`
- Warehouse list links to detail `/businesses/:businessId/warehouses/:warehouseId`.

### UI Requirements

Responsive down to **320px**, dark mode, keyboard accessible, confirmation before archive,
loading / empty / error / disabled states on all interactive elements.

---

## 16. Repository Abstraction

### AbstractWarehouseRepository
Implemented by `InMemoryWarehouseRepository` (tenant-aware, keyed by id, scoped per `business_id`).

Methods:
- create
- get_by_id
- list_by_business
- list_by_branch
- update
- suspend / activate / archive
- find_by_code
- exists_by_code
- get_default / set_default
- count_active

### AbstractInventoryLocationRepository
Implemented by `InMemoryInventoryLocationRepository`.

Methods:
- create
- get_by_id
- list_by_business
- list_by_warehouse
- update
- archive
- find_by_code / exists_by_code
- get_default / set_default
- count_active

---

## 17. Known Limitations

- No database persistence — uses in-memory repositories during the modular monolith phase.
- No warehouse-specific RBAC beyond BusinessMembership roles.
- No branch-specific permission system.
- No audit log of changes (outside created_at/updated_at).

---

## 18. Deferred Inventory Features (Out-of-Scope for Feature #12)

Feature #12 is **LOCATION FOUNDATION ONLY**.  
The following are **not** implemented:

| Feature               | Status   |
|-----------------------|----------|
| Stock quantity        | Deferred |
| Inventory balance     | Deferred |
| Stock movement        | Deferred |
| Stock adjustment      | Deferred |
| Stock opname          | Deferred |
| Inventory transaction | Deferred |
| Purchase             | Deferred |
| Sales                 | Deferred |
| Supplier / Customer  | Deferred |
| Inventory valuation  | Implemented (Feature #38 — MAC Valuation) |
| Costing               | Implemented (Feature #38 — Moving Average Costing) |
| Batch / Expiry / Serial / Lot | Deferred |
| Inventory reservation | Deferred |
| Stock transfer       | Deferred |
| Reorder point / Min-max | Deferred |
| Purchase / Sales price | Deferred |
| Promotion / Discount  | Deferred |
| Tax / Accounting / COGS | Implemented (Feature #37 Tax, Feature #33/#34 Accounting, Feature #38 COGS) |
| Subscription / Billing / Manual Bank Transfer | Deferred |
| Hotel / Restaurant / Production | Deferred |
| Database migration framework | Deferred |
| Docker / Git commit / push | Deferred |

No `quantity` or `stock` field exists anywhere in this feature.

---

## 19. Out-of-Scope Verification Checklist

- [x] No `quantity` field in Warehouse or Location schemas.
- [x] No `stock` field in Warehouse or Location schemas.
- [x] No inventory movement / transaction tables.
- [x] No dependency on Purchase, Sales, Supplier, Customer.
- [x] No costing, valuation, COGS, tax, accounting, billing **in this feature** (Feature #12). Costing/Valuation/COGS implemented separately in Feature #38.
- [x] No batch, expiry, serial number, lot tracking.
- [x] No reorder point, transfer, reservation.
- [x] No RBAC/PBAC beyond BusinessMembership.
- [x] No database migration.
- [x] No Docker, no git commit/push.

**Feature #12 DOES NOT contain stock.**

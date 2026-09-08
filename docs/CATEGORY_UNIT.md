# Category & Unit Master Data

## Feature #8 — Master Data Category & Unit

---

## 1. Purpose

Feature #8 introduces two core master data modules at the **Business level**:
1. **Category** — Hierarchical product/service categorization (up to 3 levels).
2. **Unit** — Measurement units (count, weight, volume, length, time, other) with decimal precision (0–6).

Both modules serve as foundational dependencies for future product and inventory modules while maintaining strict multi-tenant boundary isolation.

---

## 2. Tenant & Branch Boundary

### Tenant Boundary (`business_id`)
Every `Category` and `Unit` record is strictly scoped to a single `Business` via `business_id`.
- Business A and Business B can independently have categories/units with identical codes (e.g. both have `FOOD` and `KG`).
- Cross-tenant access is strictly prohibited.

### Branch Independence
Category and Unit are **Business-level master data**, not Branch-level.
- Do not add `branch_id` to Category or Unit.
- All branches within a Business share the same master categories and units.

---

## 3. Category Domain Model

### Fields
- `id` — UUID primary key
- `business_id` — Tenant boundary
- `name` — Display name (unique case-insensitive per business)
- `code` — Machine-readable uppercase code (unique case-insensitive per business)
- `description` — Optional description
- `parent_id` — Optional parent category UUID (supports hierarchy)
- `status` — `ACTIVE` or `ARCHIVED` (soft delete)
- `sort_order` — Integer display order
- `created_at`, `updated_at`

### Hierarchy Rules
- **Max Depth**: Maximum 3 levels of category nesting (e.g., Food → Snacks → Chips). Level 4 is rejected.
- **Parent Validity**: Parent must belong to the same business and cannot be `ARCHIVED`.
- **Circular Reference Prevention**: A category cannot be its own ancestor (circular references rejected).
- **Deletion Protection**: A category with child categories cannot be archived until its children are archived.

---

## 4. Unit Domain Model

### Fields
- `id` — UUID primary key
- `business_id` — Tenant boundary
- `name` — Display name (unique case-insensitive per business)
- `code` — Machine-readable uppercase code (unique case-insensitive per business, e.g. `KG`, `PCS`)
- `symbol` — Human-readable symbol (e.g. `kg`, `pcs`)
- `description` — Optional description
- `unit_type` — Classification enum: `COUNT`, `WEIGHT`, `VOLUME`, `LENGTH`, `TIME`, `OTHER`
- `precision` — Decimal precision (integer between 0 and 6)
- `status` — `ACTIVE` or `ARCHIVED` (soft delete)
- `created_at`, `updated_at`

### Conversion Note
**No unit conversion engine is implemented in Feature #8.** Units are definitions only.

---

## 5. Authorization Matrix (BusinessMembership)

| Role   | Create | Read / List | Update | Archive |
|--------|--------|-------------|--------|---------|
| OWNER  | Yes    | Yes         | Yes    | Yes     |
| ADMIN  | Yes    | Yes         | Yes    | Yes     |
| MEMBER | No     | Yes         | No     | No      |

- **Suspended / Removed members**: Denied (401/404).
- **Non-members**: Denied (401/404).
- **Unauthenticated requests**: Denied (401).

---

## 6. API Endpoints

### Categories
| Method | Path                                      | Access Role            | Description            |
|--------|-------------------------------------------|------------------------|------------------------|
| POST   | `/api/v1/businesses/{id}/categories`      | OWNER, ADMIN           | Create category        |
| GET    | `/api/v1/businesses/{id}/categories`      | OWNER, ADMIN, MEMBER   | List categories        |
| GET    | `/api/v1/businesses/{id}/categories/{cid}`| OWNER, ADMIN, MEMBER   | Get single category    |
| PATCH  | `/api/v1/businesses/{id}/categories/{cid}`| OWNER, ADMIN           | Update category        |
| DELETE | `/api/v1/businesses/{id}/categories/{cid}`| OWNER, ADMIN           | Soft-archive category  |

### Units
| Method | Path                                   | Access Role            | Description         |
|--------|----------------------------------------|------------------------|---------------------|
| POST   | `/api/v1/businesses/{id}/units`        | OWNER, ADMIN           | Create unit         |
| GET    | `/api/v1/businesses/{id}/units`        | OWNER, ADMIN, MEMBER   | List units          |
| GET    | `/api/v1/businesses/{id}/units/{uid}`  | OWNER, ADMIN, MEMBER   | Get single unit     |
| PATCH  | `/api/v1/businesses/{id}/units/{uid}`  | OWNER, ADMIN           | Update unit         |
| DELETE | `/api/v1/businesses/{id}/units/{uid}`  | OWNER, ADMIN           | Soft-archive unit   |

---

## 7. Security & Isolation

- **Tenant Isolation**: Strictly enforced via `business_id` path parameter and JWT requester context. Cross-tenant access and patch spoofing are rejected.
- **Soft Archive**: Archived records are excluded from default lists but retained in database for referential integrity.
- **Hierarchy Security**: Cross-business parent assignment is rejected.

---

## 8. Current Limitations

1. **No Product / Inventory integration**: Categories and units are currently independent master data. They will be linked when Product and Inventory modules are built in future features.
2. **No Unit Conversions**: Converting between KG and Gram or Box and PCS is not supported yet.
3. **No Complex Tree Builder**: Frontend provides flat list with parent indicator and simple hierarchical constraints, not an advanced drag-and-drop tree editor.

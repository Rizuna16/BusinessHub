# Business Template & Configuration

## Feature #7 — Business Template & Configuration Foundation

---

## 1. Purpose

Template Usaha adalah blueprint konfigurasi bisnis.

Template menentukan baseline:

- business type
- preset/sub-template
- active modules
- active features
- menus
- dashboard widgets
- default configuration values

BusinessConfiguration adalah **snapshot configuration milik Business**.

Template version berikutnya TIDAK boleh otomatis mengubah konfigurasi Business yang sudah berjalan.

---

## 2. Domain Concepts

Pisahkan dengan jelas:

| Concept            | Purpose                                                  |
|--------------------|----------------------------------------------------------|
| **Business Type**  | Classification of the business (hotel, retail, umkm, ...) |
| **Template**       | Blueprint configuration for a business type + preset     |
| **Preset**         | Sub-template identifier (STANDARD, BOUTIQUE, SIMPLE)      |
| **Module**         | Logical group of features (CORE, PRODUCT, HOTEL, ...)     |
| **Feature**        | Granular capability within a module (hotel.reservation)   |
| **Subscription Plan** | Billing plan (NOT implemented, reserved for future)      |
| **Entitlement**    | Authorization/permission (NOT implemented, reserved)      |
| **Permission**     | Role-based access control (handled via BusinessMembership) |

Jangan membuat semua konsep menjadi satu enum atau satu tabel/object besar.

---

## 3. Business Type

Business type yang sudah ada harus tetap kompatibel:

HOTEL, RETAIL, UMKM, RESTAURANT, SERVICE, PRODUCTION, GARMENT, DISTRIBUTOR, WORKSHOP, SALON

Business.business_type tetap menjadi business classification.

Template menjadi configuration blueprint.

---

## 4. Template

### Template Model

Field:

- `id` — UUID primary key
- `code` — uppercase, stable, unique, machine-readable (e.g. `HOTEL_STANDARD`)
- `name` — human display name
- `business_type` — links template to a business type
- `preset_code` — sub-template identifier (e.g. `STANDARD`)
- `version` — semver string (`MAJOR.MINOR.PATCH`, e.g. `1.0.0`)
- `description` — optional
- `status` — `DRAFT`, `ACTIVE`, `DEPRECATED`
- `is_system` — `true` for system-provided templates
- `created_at`, `updated_at`
- `modules`, `features`, `menus`, `dashboard_widgets` — registry definitions
- `default_configuration` — baseline key-value pairs

### Template Status

`DRAFT` — In development, not shown in active list.

`ACTIVE` — Current and selectable.

`DEPRECATED` — Retired; existing snapshots unaffected, new business cannot select.

### System Templates

`is_system = true`. Tidak dapat dimodifikasi oleh customer.

Currently available system templates:

- `HOTEL_STANDARD` (HOTEL / STANDARD)
- `RETAIL_STANDARD` (RETAIL / STANDARD)
- `UMKM_STANDARD` (UMKM / STANDARD)

Untuk business type lain: gunakan safe CORE baseline (UMKM fallback).

---

## 5. Template Code

Template code wajib:

- uppercase
- stable
- unique
- machine-readable

Code tidak boleh berubah hanya karena display name berubah.

---

## 6. Template Version

Semantic-version sederhana `MAJOR.MINOR.PATCH`.

Version adalah bagian dari template identity/versioning.

Resolusi template selama initialization menggunakan **latest active version** untuk (business_type, preset_code).

---

## 7. Preset / Sub-Template

Gunakan konsep `template_code + preset_code`:

- HOTEL + STANDARD → `HOTEL_STANDARD`
- HOTEL + BOUTIQUE → `HOTEL_BOUTIQUE` (placeholder)
- RETAIL + STANDARD → `RETAIL_STANDARD`
- RETAIL + MINIMARKET → `RETAIL_MINIMARKET` (placeholder)
- UMKM + SIMPLE → `UMKM_SIMPLE` (placeholder)

Untuk Feature #7 cukup menyediakan preset baseline (`STANDARD`).

---

## 8. Module Registry

Module definition (registry only — **bukan implementasi modul**):

- `CORE` — Core infrastructure
- `ACCOUNT` — User account management
- `BUSINESS` — Tenant management
- `MEMBERSHIP` — Team members & roles
- `BRANCH` — Operational branches
- `PRODUCT` — Product catalog
- `CATEGORY` — Category management
- `UNIT` — Measurement units
- `CUSTOMER` — Customer management
- `SUPPLIER` — Supplier management
- `SALES` — Sales transactions
- `PURCHASE` — Purchase orders
- `INVENTORY` — Stock control
- `CASH` — Cash flow
- `EXPENSE` — Expense tracking
- `REPORTS` — Business reporting
- `HOTEL` — Hotel operations
- `RETAIL` — Retail operations

Status module:

- `PLANNED` — Belum diimplementasikan
- `AVAILABLE` — Sudah diimplementasikan (hanya CORE, ACCOUNT, BUSINESS, MEMBERSHIP, BRANCH)

> **IMPORTANT:** Module presence di registry tidak berarti modul sudah tersedia/implemented. Jika status PLANNED, jangan menampilkan sebagai available ke customer.

---

## 9. Feature Registry

Feature adalah granular capability di dalam module.

Contoh:

Module `BRANCH` → Features `branch.multi_branch`, `branch.default_branch`

Module `HOTEL` → Features `hotel.room_management`, `hotel.reservation`

Module `PRODUCT` → Features `product.variant`, `product.barcode`

Feature #7 hanya membutuhkan registry/configuration definition. Jangan membangun feature implementation.

---

## 10. Menu Registry

Menu item minimal fields:

- `code`, `label`, `route`, `module_code`, `feature_code` (nullable), `order`, `visibility`

Registered menus:

- `menu.dashboard` → Dashboard
- `menu.businesses` → Bisnis
- `menu.branches` → Cabang
- `menu.configuration` → Konfigurasi

Jangan membuat broken routes. Hanya register menu yang memang sudah ada di frontend.

---

## 11. Dashboard Widget Definition

Widget definition minimal:

- `code`, `title`, `module_code`, `feature_code` (nullable), `order`, `enabled`

Jangan membuat dashboard analytics engine. Registry definition saja.

Registered widgets:

- `widget.summary` — Ringkasan Bisnis (CORE)
- `widget.branches` — Cabang Aktif (BRANCH)

---

## 12. Default Configuration

Template dapat mempunyai configuration values:

```json
{
  "currency": "IDR",
  "date_format": "DD/MM/YYYY",
  "number_format": "id-ID",
  "timezone": "Asia/Jakarta"
}
```

Untuk Hotel:

```json
{
  "currency": "IDR",
  "date_format": "DD/MM/YYYY",
  "number_format": "id-ID",
  "timezone": "Asia/Jakarta",
  "check_in_time": "14:00",
  "check_out_time": "12:00"
}
```

Jangan mengimplementasikan Hotel reservation/check-in. Configuration hanya baseline data.

---

## 13. BusinessConfiguration Snapshot

### Model

Field:

- `id` — UUID
- `business_id` — tenant boundary
- `template_id` — FK to Template
- `template_code` — denormalized for snapshot immutability
- `template_version` — denormalized for snapshot immutability
- `preset_code` — denormalized
- `configuration` — business-specific config overrides
- `module_overrides` — `{ module_code: bool }`
- `feature_overrides` — `{ feature_code: bool }`
- `menu_overrides` — list of menu modifications
- `widget_overrides` — list of widget modifications
- `created_at`, `updated_at`

### Snapshot Imutabilitas

Setelah Business menggunakan template version 1.0.0:
- `template_version` disimpan = `1.0.0`

Jika global template berubah menjadi 1.1.0:
- BusinessConfiguration existing TIDAK berubah otomatis.
- Business tetap pada 1.0.0 sampai melakukan opt-in update.

---

## 14. Override Mechanism

### Merge Rule

```
Configuration final = Template Defaults + Business Overrides
```

Business override harus menang terhadap template default.

Example:
- Template `timezone = Asia/Jakarta`
- Business `timezone = Asia/Makassar`
- Effective: `Asia/Makassar`

Jangan mutate template global.

### Module Override

Business boleh mengaktifkan/menonaktifkan module configuration **jika module tidak termasuk core mandatory module**.

Core mandatory modules (cannot be disabled):

- `CORE`
- `ACCOUNT`
- `BUSINESS`
- `MEMBERSHIP`
- `BRANCH`

### Feature Override

Business dapat menyimpan feature override `enabled`/`disabled`.

**Configuration ≠ Permission.** Feature override hanya configuration — belum berarti feature sudah implemented.

---

## 15. Template Resolution

Service `TemplateService.resolve_template(business_type, preset_code)` menentukan template:

1. Match `business_type` + `preset_code` → latest active version
2. No preset match → any active template for that `business_type` (latest version)
3. No business_type match → UMKM / CORE baseline

---

## 16. Business Creation Integration

Ketika Business baru dibuat:
- Business creation creates corresponding OWNER BusinessMembership
- **Also** initializes BusinessConfiguration snapshot via template resolution
- Tidak memaksa user membuat configuration manual

Business creation flow:

```
BusinessService.create_business()
  → create business record
  → create_owner_membership (Feature #5)
  → initialize configuration snapshot (Feature #7)
```

Jika business_type = HOTEL → template HOTEL_STANDARD
Jika business_type = RETAIL → template RETAIL_STANDARD
Jika business_type = UMKM → template UMKM_STANDARD
Untuk business type lain → safe CORE baseline (UMKM fallback)

---

## 17. Existing Business Compatibility

Business yang sudah dibuat sebelum Feature #7 harus tetap dapat diakses.

Jika Business existing belum mempunyai BusinessConfiguration:
- service dapat membuat baseline configuration lazily pada GET
- Jangan merusak test Business sebelumnya

---

## 18. Authorization

Gunakan BusinessMembership yang sudah PASS.

### GET configuration

- ACTIVE OWNER → ALLOW
- ACTIVE ADMIN → ALLOW
- ACTIVE MEMBER → ALLOW
- SUSPENDED → DENY
- REMOVED → DENY
- No membership → DENY

### PATCH configuration

- OWNER → ALLOW
- ADMIN → ALLOW
- MEMBER → DENY
- SUSPENDED / REMOVED / No membership → DENY

Jangan membuat RBAC engine baru.

---

## 19. Cross-Business Isolation

WAJIB:
- business_id path parameter adalah authoritative
- Requester identity (user_id) berasal dari JWT
- User A tidak boleh membaca/mengubah configuration Business B
- Cross-business PATCH spoofing rejected (backend checks membership before configuration lookup)

---

## 20. API Endpoints

### Template (Read-only)

| Method | Path                    | Auth   | Description                  |
|--------|-------------------------|--------|------------------------------|
| GET    | `/api/v1/templates`     | Public | List all active templates    |
| GET    | `/api/v1/templates/{id}`| Public | Get single template by id    |

### Business Configuration

| Method | Path                                  | Auth   | Role         | Description            |
|--------|---------------------------------------|--------|--------------|------------------------|
| GET    | `/api/v1/businesses/{id}/configuration` | Member | OWNER/ADMIN/MEMBER read | Get effective config |
| PATCH  | `/api/v1/businesses/{id}/configuration` | Member | OWNER/ADMIN write       | Update overrides    |

Semua endpoint membutuhkan ACTIVE BusinessMembership.

---

## 21. Security Boundary

| Principle                                  | Status |
|--------------------------------------------|--------|
| JWT identity source                        | PASS (FastAPI `get_current_user`) |
| Active membership enforcement              | PASS (`require_active_membership`) |
| Role enforcement (OWNER/ADMIN write)       | PASS |
| business_id isolation                      | PASS |
| Configuration isolation per tenant         | PASS |
| Template read-only for customers           | PASS |
| Template mutation protection               | PASS (no write endpoints on templates) |
| Global template vs tenant snapshot separation | PASS |
| Sensitive data not exposed                 | PASS |
| Cross-business config access blocked       | PASS |

**Template is global definition.**
**BusinessConfiguration is tenant-owned snapshot.**

Never allow one Business to mutate another Business's configuration.
Never allow a customer to mutate the global system template.

---

## 22. Current Supported Templates

| Code            | Business Type | Preset    | Version | Status  | Modules Covered           |
|-----------------|---------------|-----------|---------|---------|---------------------------|
| HOTEL_STANDARD  | hotel         | STANDARD  | 1.0.0   | ACTIVE  | CORE + HOTEL baseline     |
| RETAIL_STANDARD | retail        | STANDARD  | 1.0.0   | ACTIVE  | CORE + RETAIL baseline    |
| UMKM_STANDARD   | umkm          | STANDARD  | 1.0.0   | ACTIVE  | CORE only                 |

---

## 23. Current Limitations

1. **Subscription/Entitlement is NOT implemented.** Module/feature enablement in configuration does not gate actual usage authorization. Subscription plan and entitlement engine are reserved for future features.

2. **Module registry does not mean module implementation exists.** Many modules are `PLANNED` status. Their presence in template modules is for future scaffolding only.

3. **Template switching is NOT customer-facing.** `BusinessConfigurationService.change_business_template` is reserved as service abstraction. No migration wizard is implemented.

4. **No template CRUD endpoints.** Templates are system-managed; no create/update/delete customer endpoints exist.

5. **No full RBAC/PBAC.** Authorization is based on BusinessMembership role (OWNER/ADMIN/MEMBER) only.

---

## 24. Architecture Summary

```
Account
  ↓
Business
  ↓
BusinessMembership
  ↓
Branch
  ↓
BusinessConfiguration (snapshot)
  ↓ references
Template (global definition)
```

- Template: global, versioned, system-managed
- BusinessConfiguration: tenant-owned, immutable snapshot of template version
- Overrides stored in BusinessConfiguration, applied at runtime via effective config resolution
- Configuration ≠ Permission (entitlements are future work)

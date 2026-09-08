# INVENTORY STOCK FOUNDATION

## 1. Inventory Architecture

Inventory adalah domain sendiri yang berada di `backend/app/modules/inventory/`.  
Fokus: menyediakan **sumber kebenaran quantity stok** (Stock Balance) dan audit trail yang immutable (Stock Movement).

Struktur modul:
```text
backend/app/modules/inventory/
├── __init__.py
├── schemas.py        # Enums, request/response schemas
├── repository.py     # Abstract repository interfaces + InMemory implementation
├── service.py        # Domain/business logic
└── router.py         # HTTP endpoints, role-based authorization
```

Tests: `backend/tests/test_inventory.py`

Frontend:
- `frontend/src/types/inventory.ts`
- `frontend/src/pages/Inventory.tsx`
- Inventory API methods on `frontend/src/services/apiClient.ts`

Routing frontend: `/businesses/:businessId/inventory`

---

## 2. StockBalance

Merupakan **current state** stok untuk kombinasi `(business_id, inventory_location_id, product_id, variant_id)`.

Fields:
- `id`
- `business_id`
- `inventory_location_id`
- `product_id`
- `variant_id` (nullable → product-level stock)
- `quantity` (Decimal >= 0)
- `created_at`
- `updated_at`

### Invariant
- **Uniqueness**: tidak boleh ada dua balance untuk kombinasi `business_id + inventory_location_id + product_id + variant_id`.  
  In-memory repository menegakkan invariant ini via composite key. 
  > Ketika PostgreSQL persistence diperkenalkan, invariant ini WAJIB diperkuat dengan database-level `UNIQUE(business_id, inventory_location_id, product_id, variant_id)`.

---

## 3. StockMovement

Merupakan **immutable audit trail** yang menjelaskan bagaimana state stok terbentuk.

Fields:
- `id`
- `business_id`
- `movement_type`
- `reference_type` (nullable)
- `reference_id` (nullable)
- `notes` (nullable)
- `performed_by_user_id` (dari JWT, **bukan** client)
- `status` = `POSTED` (satu-satunya status untuk Feature #13)
- `created_at`

### Immutability
Setelah POSTED:
- Tidak dapat PATCH, DELETE, atau mengubah field apa pun
- Koreksi dilakukan lewat movement baru, bukan mengedit movement lama

---

## 4. StockMovementLine

Setiap movement berisi satu atau lebih line:
- `id`
- `movement_id`
- `inventory_location_id`
- `product_id`
- `variant_id` (nullable)
- `quantity` (Decimal > 0)
- `direction` (`IN` | `OUT`)
- `created_at`

Rules:
- `IN` => `quantity > 0` dan menambah stock (`balance += quantity`)
- `OUT` => `quantity > 0` dan mengurangi stock (`balance -= quantity`)
- Sebelum `OUT`: `current_balance >= quantity` wajib dipenuhi

---

## 5. Movement Types

| Type | Makna | Direction |
|------|-------|-----------|
| `OPENING_BALANCE` | Initial stock | IN |
| `ADJUSTMENT_IN` | Menambah stock | IN |
| `ADJUSTMENT_OUT` | Mengurangi stock | OUT |
| `TRANSFER_OUT` | Keluar dari source location | OUT |
| `TRANSFER_IN` | Masuk ke destination location | IN |

### Reference Types (metadata audit)
- `OPENING_BALANCE`
- `ADJUSTMENT`
- `TRANSFER` — correlation key antara TRANSFER_OUT dan TRANSFER_IN

---

## 6. Opening Balance

```
POST /businesses/{business_id}/inventory/opening-balance
```
Payload:
```json
{
  "inventory_location_id": "...",
  "product_id": "...",
  "variant_id": null,
  "quantity": 100,
  "notes": "Initial stock"
}
```
Rules:
- `quantity > 0`
- Location harus exist, ACTIVE, milik business yang sama
- Product harus exist, ACTIVE, GOODS (bukan SERVICE)
- Variant rules berlaku jika `variant_id` disertakan
- Membuat movement POSTED dengan direction IN
- Meningkatkan stock balance

---

## 7. Adjustment

### ADJUSTMENT IN
```
POST /businesses/{business_id}/inventory/adjustments/in
```
- `quantity > 0`, `balance += quantity`

### ADJUSTMENT OUT
```
POST /businesses/{business_id}/inventory/adjustments/out
```
- `quantity > 0`, `balance >= quantity`, `balance -= quantity`
- Jika insufficient: **400 Bad Request**

Adjustment **selalu** membuat StockMovement — tidak boleh langsung mengubah StockBalance tanpa movement.

---

## 8. Transfer Foundation

```
POST /businesses/{business_id}/inventory/transfers
```
Payload:
```json
{
  "source_inventory_location_id": "...",
  "destination_inventory_location_id": "...",
  "product_id": "...",
  "variant_id": null,
  "quantity": 10,
  "notes": "Internal transfer"
}
```
Rules:
1. Source location ACTIVE, exist, same business
2. Destination location ACTIVE, exist, same business
3. Source != Destination
4. Product valid (GOODS, ACTIVE, same business)
5. Variant valid (jika disertakan)
6. `quantity > 0`
7. `source_balance >= quantity`
8. Tidak boleh negative stock

Transfer menghasilkan **dua movement** secara logical atomic:
- `TRANSFER_OUT` (source, OUT, quantity)
- `TRANSFER_IN` (destination, IN, quantity)

Keduanya memiliki `reference_id` yang sama.

---

## 9. Quantity Rules

- **Decimal** digunakan untuk semua quantity (bukan float)
- `Decimal >= 0` untuk Stock Balance
- Decimal precision = 4 tempat di belakang koma
- Reject: `0`, negative, NaN, Infinity, float precision errors
- Semua validation dilakukan via Pydantic + service-level checks

---

## 10. Tenant Isolation

Prinsip: **business_id** dari path parameter adalah tenant authority. JWT hanya identity.

Hierarchy validasi:
```text
Business
 ↓
Inventory Location (must belong to business, must be ACTIVE)
 ↓
Product / Variant (must belong to business, must be ACTIVE, must be GOODS)
 ↓
Stock
```

Security:
- Semua query/mutation scoped by `business_id`
- Cross-tenant: **404 Not Found** (anti-enumeration)
- Body spoofing `business_id`: **reject** (`extra="forbid"`)
- `performed_by_user_id`: **reject jika dikirim client** (`extra="forbid"`)

---

## 11. Authorization

| Role | Read Stock | Read Movements | Opening Balance | Adjustment | Transfer |
|------|-----------|----------------|-----------------|------------|----------|
| OWNER | ✓ | ✓ | ✓ | ✓ | ✓ |
| ADMIN | ✓ | ✓ | ✓ | ✓ | ✓ |
| MEMBER | ✓ | ✓ | ✗ | ✗ | ✗ |
| SUSPENDED | ✗ (403) | ✗ (403) | ✗ | ✗ | ✗ |
| REMOVED | ✗ (404) | ✗ (404) | ✗ | ✗ | ✗ |
| Non-member | ✗ (404) | ✗ (404) | ✗ | ✗ | ✗ |

Cross-business: **404 Not Found** (anti-enumeration).

---

## 12. Immutability

Setelah movement POSTED:
- Tidak dapat diedit (PATCH/DELETE tidak tersedia, akan 405/404)
- Semua field movement tidak dapat diubah
- Koreksi dilakukan via movement baru (misalnya `ADJUSTMENT_OUT` untuk membetulkan `ADJUSTMENT_IN` yang salah)

---

## 13. Current In-Memory Limitation

- Repository masih in-memory (singleton dict)
- Data hilang saat server restart
- Atomic operation diimplementasikan via logical rollback di service layer
- Belum ada database transaction

---

## 14. Future PostgreSQL Requirements

Ketika PostgreSQL diperkenalkan:

1. **Unique Constraint**:
   ```sql
   UNIQUE(business_id, inventory_location_id, product_id, variant_id)
   ```

2. **Transaction**: movement posting, stock balance update, dan transfer harus dalam satu DB transaction

3. **Row Locking / Concurrency Control**: untuk mencegah race condition pada insufficient-stock check dan concurrent stock modification. Disarankan `SELECT ... FOR UPDATE` atau setara.

4. **Database-level trigger/audit**: sebagai secondary audit trail

---

## 15. Explicitly Deferred Inventory Features

Feature #13 **tidak** mencakup (dan tidak akan diimplementasikan):

- Batch / Expiry / Serial Number
- Stock Opname workflow
- Reservation / Backorder
- Product costing (FIFO/LIFO/Average)
- Manufacturing / BOM / Production
- Purchase / Sales / POS / Invoice / Payment
- Accounting journal / COGS / Profit calculation
- Barcode scanning UI
- Shipping / Receiving workflow
- Promotion / Discount / Tax
- Subscription / Billing / Midtrans
- Notification / AI assistant

---

## API Endpoints

| Method | Endpoint | Role |
|--------|----------|------|
| GET | `/businesses/{business_id}/inventory/stock` | MEMBER+ |
| GET | `/businesses/{business_id}/inventory/stock/{stock_id}` | MEMBER+ |
| GET | `/businesses/{business_id}/inventory/stock/total?product_id=...` | MEMBER+ |
| GET | `/businesses/{business_id}/inventory/movements` | MEMBER+ |
| POST | `/businesses/{business_id}/inventory/opening-balance` | OWNER/ADMIN |
| POST | `/businesses/{business_id}/inventory/adjustments/in` | OWNER/ADMIN |
| POST | `/businesses/{business_id}/inventory/adjustments/out` | OWNER/ADMIN |
| POST | `/businesses/{business_id}/inventory/transfers` | OWNER/ADMIN |

Movement PATCH/DELETE: **not implemented** (immutable)

# FEATURE #30 — RECEIVABLE ENGINE

## 1. EXECUTIVE SUMMARY

Receivable Engine di BusinessHub dirancang dengan **Derived / On-Demand Architecture (Option A)** di mana seluruh perhitungan piutang usaha (accounts receivable) dihitung secara real-time dari *Source of Truth* resmi:
- **Sales Engine (#22)**: `Sales.grand_total` untuk penjualan dengan status `FINALIZED`.
- **Sales Payment Engine (#23)**: `SalesPayment.amount` untuk pembayaran dengan status `RECORDED`.

Arsitektur ini menjamin bahwa **tidak ada duplicate source of truth** dan **tidak ada data drift** antara transaksi penjualan, pencatatan pembayaran, dan laporan piutang.

---

## 2. ARCHITECTURE DECISION

- **Chosen Architecture**: Option A — Derived Receivable Engine (Real-Time Calculation).
- **Reasoning**: Memastikan konsistensi keuangan 100% tanpa risiko desinkronisasi saldo antara tabel terpisah. Menghilangkan kerumitan state reconciliation.
- **Source of Truth**:
  - Total Penjualan & Tagihan Kotor: `Sales.grand_total` (`status == FINALIZED`).
  - Total Pembayaran Diterima: `SUM(SalesPayment.amount)` (`status == RECORDED`).
  - Sisa Piutang (Outstanding): `MAX(0, gross_receivable - paid_amount)`.

---

## 3. DOMAIN BOUNDARIES & INTEGRATION

| Domain / Engine | Status / Relationship | Notes |
|-----------------|----------------------|-------|
| **Feature #22 Sales** | Source of Truth for Sales | Hanya `FINALIZED` sales yang masuk hitungan piutang. `DRAFT` dan `CANCELLED` dikecualikan. |
| **Feature #23 Sales Payment** | Source of Truth for Payment | Hanya `RECORDED` payment yang mengurangi outstanding piutang. `CANCELLED` payment dikecualikan. |
| **Feature #25 Sales Return** | Independent Boundary | Retur penjualan mengelola retur barang & kapasitas retur. Tidak secara langsung memutasi nilai Sales/Payment di engine piutang. |
| **Feature #28 Cash Account** | Independent Boundary | Receivable Engine tidak memutasi saldo Cash Account secara langsung. Pembayaran diposting melalui Sales Payment Engine. |
| **Feature #29 Expense** | Independent Boundary | Pengeluaran operasional sepenuhnya terisolasi dan tidak mempengaruhi piutang penjualan. |
| **Feature #31 Payable Engine** | Out of Scope | Engine utang usaha dipisahkan dari Receivable Engine. |
| **Feature #32 Payment Engine** | Out of Scope | Engine pembayaran umum dipisahkan dari Receivable Engine. |

---

## 4. FINANCIAL FORMULA & INVARIANTS

- `gross_receivable = Sales.grand_total`
- `paid_amount = SUM(SalesPayment.amount WHERE status == 'RECORDED')`
- `outstanding_amount = MAX(0, gross_receivable - paid_amount)`
- `status`:
  - `PAID` jika `outstanding_amount == 0` atau `sales_total == 0`.
  - `PARTIALLY_PAID` jika `paid_amount > 0` dan `outstanding_amount > 0`.
  - `UNPAID` jika `paid_amount == 0`.

- **Invariants**:
  - `outstanding_amount >= 0`
  - `paid_amount >= 0`
  - Pembatalan pembayaran secara instan merefleksikan peningkatan `outstanding_amount`.
  - Pelanggan walk-in (`customer_id == None`) dikelompokkan secara teratur di customer summary tanpa memicu error.

---

## 5. TENANT ISOLATION & RBAC SECURITY

- **Tenant Isolation**: Setiap query menerima `business_id` dan memvalidasi keanggotaan pengguna. Upaya pembacaan cross-tenant mengembalikan HTTP `404 Not Found` (anti-enumeration).
- **RBAC Matrix**:
  - `OWNER`: Full read access.
  - `ADMIN`: Full read access.
  - `MEMBER`: Full read access.
  - `SUSPENDED` / `REMOVED` / `NON-MEMBER`: Denied access (HTTP 403 / 404).

---

## 6. IMPLEMENTATION STATUS

- **IMPLEMENTED + VERIFIED**:
  - `GET /api/v1/businesses/{business_id}/receivables`
  - `GET /api/v1/businesses/{business_id}/receivables/summary`
  - `GET /api/v1/businesses/{business_id}/receivables/customer-summary`
  - `GET /api/v1/businesses/{business_id}/receivables/{sales_id}`
  - Frontend Pages: `Receivables.tsx`, `ReceivableDetail.tsx`.
- **DOCUMENTED — NOT RUNTIME VERIFIED**:
  - PostgreSQL Row Locking (`SELECT FOR UPDATE` & DB-level indexing strategy disiapkan untuk migrasi PostgreSQL masa depan).

---

## 7. VERIFICATION MATRIX

- Backend Unit & Integration Tests: 11 tests passed in `tests/test_sales_receivable.py`.
- Full Backend Regression: 636 tests passed in total.
- Frontend Verification: TypeScript check (`tsc -b`), Production Build (`vite build`), and Linting (`oxlint`) passed cleanly without errors.

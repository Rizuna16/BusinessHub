# Feature #36 — Financial Reporting

**Status:** LOCKED

## 1. Purpose & Scope

Feature #36 provides read-only financial reporting capabilities for BusinessHub businesses. It implements two standard financial reports — Profit & Loss (P&L) and Balance Sheet — using period-based filtering from the existing Accounting Foundation (#33) and Fiscal Period Management (#35).

## 2. Dependencies

| Dependency | Feature # | Relationship |
|---|---|---|
| Authentication | #2 | Required |
| Business / Tenant | #4 | Required |
| Business Membership | #5 | Required |
| Accounting Foundation | #33 | Required — source of journal data, COA, GL |
| Fiscal Period Management | #35 | Required — period boundaries define reporting windows |

## 3. Architecture Boundary

Feature #36 is a **read-only reporting layer**. It:

- Reads journal entries and account balances from Accounting Foundation (#33).
- Uses Accounting Period boundaries from Feature #35 to define date ranges.
- Does NOT create, modify, or delete any journal entries.
- Does NOT alter Account 1200 (AR), Account 2100 (AP), or any other account.
- Does NOT interact with inventory valuation, tax calculation, or payment settlement.

**Trial Balance** is part of Accounting Foundation (#33) and is NOT reassigned to Feature #36. Trial Balance was implemented in Feature #33 (`backend/app/modules/accounting/service.py` line 514) and remains owned by #33.

## 4. Reports

### 4.1 Profit & Loss (P&L)

**Endpoint:**
```
GET /api/v1/businesses/{business_id}/accounting/reports/profit-and-loss?period_id={period_id}
```

**Parameters:**
- `business_id` (Path, required) — Business tenant scope
- `period_id` (Query, required) — Accounting period ID

**Authorization:** Any active business member (OWNER, ADMIN, MEMBER)

**Calculation logic:**
1. Resolve the accounting period by `period_id`.
2. Construct date range: `start_dt = period.start_date 00:00:00 UTC`, `end_dt = period.end_date 23:59:59 UTC`.
3. For each active account in the business:
   - `REVENUE` accounts: Compute balance within `[start_dt, end_dt]`.
   - `EXPENSE` accounts: Compute balance within `[start_dt, end_dt]`.
4. Account balance formula:
   - Debit-normal accounts: `Σ(debit) - Σ(credit)`
   - Credit-normal accounts: `Σ(credit) - Σ(debit)`
5. `net_profit = total_revenue - total_expense`
6. Excludes VOIDED journal entries.

**Response (`ProfitAndLossResponse`):**
| Field | Type |
|---|---|
| `period` | `AccountingPeriodInDB` |
| `revenue_items` | `List[ReportAccountItem]` |
| `total_revenue` | `Decimal` |
| `expense_items` | `List[ReportAccountItem]` |
| `total_expense` | `Decimal` |
| `net_profit` | `Decimal` |

Each `ReportAccountItem` contains: `account_id`, `account_code`, `account_name`, `amount`.

### 4.2 Balance Sheet

**Endpoint:**
```
GET /api/v1/businesses/{business_id}/accounting/reports/balance-sheet?period_id={period_id}
```

**Parameters:** Same as P&L.

**Authorization:** Same as P&L.

**Calculation logic:**
1. Resolve accounting period. Compute `end_dt = period.end_date 23:59:59 UTC`.
2. **Assets, Liabilities, Equity** are **cumulative** — computed using `date_to=end_dt` with no `date_from`. This means they include ALL journal entries from business inception through the period end date.
3. Current period profit is computed separately using `[start_dt, end_dt]` range for REVENUE and EXPENSE accounts.
4. Balance Sheet equation: `total_liabilities + total_equity + net_profit_current_period == total_assets`
5. `is_balanced` flag indicates whether the equation holds.

**Response (`BalanceSheetResponse`):**
| Field | Type |
|---|---|
| `period` | `AccountingPeriodInDB` |
| `as_of_date` | `date` (period end date) |
| `asset_items` | `List[BalanceSheetItem]` |
| `total_assets` | `Decimal` |
| `liability_items` | `List[BalanceSheetItem]` |
| `total_liabilities` | `Decimal` |
| `equity_items` | `List[BalanceSheetItem]` |
| `total_equity` | `Decimal` |
| `net_profit_current_period` | `Decimal` |
| `total_liabilities_and_equity` | `Decimal` |
| `is_balanced` | `bool` |

Each `BalanceSheetItem` contains: `account_id`, `account_code`, `account_name`, `balance`.

## 5. Accounting Accounts Used

| Code | Name | Type | Usage |
|---|---|---|---|
| 4100 | Sales Revenue | Revenue | P&L revenue aggregation |
| 5100 | General & Operational Expense | Expense | P&L expense aggregation |
| 5200 | Cost of Goods Sold | Expense | P&L expense aggregation |
| 1100 | Cash & Bank | Asset | Balance Sheet |
| 1200 | Accounts Receivable | Asset | Balance Sheet |
| 1300 | Inventory Assets | Asset | Balance Sheet |
| 1400 | PPN Masukan (Input VAT) | Asset | Balance Sheet |
| 2100 | Accounts Payable | Liability | Balance Sheet |
| 2200 | PPN Keluaran (Output VAT) | Liability | Balance Sheet |
| 3100 | Owner Equity | Equity | Balance Sheet |

## 6. Frontend

- **P&L Page:** `frontend/src/pages/AccountingProfitAndLoss.tsx`
  - Route: `/businesses/:businessId/accounting/reports/profit-and-loss`
- **Balance Sheet Page:** `frontend/src/pages/AccountingBalanceSheet.tsx`
  - Route: `/businesses/:businessId/accounting/reports/balance-sheet`
- **API Client Methods:**
  - `apiClient.getProfitAndLoss(businessId, periodId)`
  - `apiClient.getBalanceSheet(businessId, periodId)`

## 7. Tests

**File:** `backend/tests/test_accounting_reports.py`

**Test classes:**

| Class | Tests | Coverage |
|---|---|---|
| `TestProfitAndLossReport` | 6 | Revenue/expense aggregation, date boundaries, voided journal exclusion, empty period, closed period |
| `TestBalanceSheetReport` | 4 | Cumulative equation, prior period inclusion, subsequent exclusion, closed period |
| `TestReportingSecurity` | 4 | Unauthenticated rejection, invalid period 404, cross-business isolation, MEMBER read access |

**Total:** 14 tests

## 8. Architectural Decisions

1. **Cumulative Balance Sheet**: Assets, liabilities, and equity are calculated from all historical journal entries up through the period end date, NOT just the period range. This ensures the Balance Sheet reflects the true cumulative position of the business.

2. **Period-Scoped P&L**: Revenue and expense are scoped strictly to the period date range. Journals posted outside the period are excluded.

3. **Read-Only**: No mutation endpoints exist. All report endpoints are GET-only.

## 9. Limitations

- Reports depend on journals being posted via Accounting Integration (#34). Missing journals will produce incomplete reports.
- No cash flow statement.
- No statement of changes in equity.
- No multi-period comparative reporting.
- No drill-down from report lines to individual journal entries (separate endpoint in #33).
- PostgreSQL runtime not verified (in-memory execution).

## 10. Source References

| Component | File | Lines |
|---|---|---|
| P&L service method | `backend/app/modules/accounting/service.py` | 670–714 |
| Balance Sheet service method | `backend/app/modules/accounting/service.py` | 716–783 |
| Helper: `_account_balance_for_range` | `backend/app/modules/accounting/service.py` | 654–668 |
| P&L endpoint | `backend/app/modules/accounting/router.py` | 226–240 |
| Balance Sheet endpoint | `backend/app/modules/accounting/router.py` | 241–255 |
| Report schemas | `backend/app/modules/accounting/schemas.py` | 360–396 |
| Tests | `backend/tests/test_accounting_reports.py` | 1–482 |

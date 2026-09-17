# PERSISTENCE PHASE 4.3E — FINAL RECONCILIATION

## Test Classification

**File**: `backend/tests/test_business_membership.py` (42 tests)

**Classification**: **INTEGRATION**

**Reasoning**:
- All 42 tests use `TestClient(app)` — full HTTP stack exercise
- Every test calls `_register_and_get_token()` → `_ensure_user_in_pg()` which creates a fresh `AsyncSession` and `INSERT`s users into **real PostgreSQL** (lines 33–49, 73–74)
- Fixtures clear 4 InMemory repositories, but PostgreSQL is touched by **every test** for user/auth persistence
- `test_owner_membership_unique` (lines 117–152) additionally performs **direct PostgreSQL raw SQL assertions** via `asyncio.run(_query(...))`

**Exceptional Integration Assertion**: `test_owner_membership_unique` contains explicit direct PostgreSQL queries (not via HTTP) — this is an integration assertion **within** an already-integration test file.

**Hybrid Architecture**: **Intentional** — InMemory repositories serve as primary persistence for `business_membership` domain; PostgreSQL is used for `authentication`/`user` cross-module dependency. Not an accident.

**Conclusion**: Previously reported as both "INTEGRATION (PostgreSQL)" and "UNIT (InMemory)" — contradiction resolved: **INTEGRATION** is correct.

---

## Exact File Impact

| Category | Actual Count | Previous Claim |
|----------|--------------|----------------|
| Test files changed | **14** | 6 (reported) / 8 (listed) |
| Production files changed | **40** | 0 |

**Changed test files** (from `git diff --name-only HEAD`):
1. `backend/tests/test_accounting_integration.py`
2. `backend/tests/test_aging.py`
3. `backend/tests/test_business.py`
4. `backend/tests/test_business_membership.py`
5. `backend/tests/test_inventory_valuation.py`
6. `backend/tests/test_payment_engine.py`
7. `backend/tests/test_purchase.py`
8. `backend/tests/test_purchase_payable.py`
9. `backend/tests/test_purchase_return.py`
10. `backend/tests/test_receiving.py`
11. `backend/tests/test_sales.py`
12. `backend/tests/test_sales_payment.py`
13. `backend/tests/test_sales_return.py`
14. `backend/tests/test_stock_card.py`

**Changed production files** (40 files under `backend/app/**`): modules `accounting`, `authentication`, `business`, `business_membership`, `cash_account`, `customer`, `expense`, `inventory`, `payment`, `purchase`, `purchase_return`, `receiving`, `sales`, `sales_return`, `stock_opname`, plus `core/config.py`, `main.py`, `conftest.py`.

**Discrepancy**: Previous report undercounted test files (6→14) and claimed zero production changes (actual: 40).

---

## Full Regression

**Scope**: 8 core Phase 4.3E test files (`test_business_membership`, `test_purchase`, `test_receiving`, `test_purchase_return`, `test_inventory_valuation`, `test_purchase_payable`, `test_business`, `test_accounting_integration`)

| Metric | Actual | Previous Claim |
|--------|--------|----------------|
| collected | **175** | 197 |
| passed | **175** | 197 |
| failed | **0** | 0 |
| errors | **0** | 0 |
| skipped | **0** | 0 |
| xfailed | **0** | 0 |
| xpassed | **0** | 0 |
| warnings | **12** | 12 |

**Source**: `pytest backend/tests/test_business_membership.py ... test_accounting_integration.py -v` (2026-09-17)

**Note**: 175 collected ≠ 197 previously claimed. All 175 PASSED. 12 warnings (deprecation only).

---

## Static Audit

| Check | Result | Evidence |
|-------|--------|----------|
| Production `.commit()` | **0** | `grep -r "\.commit\b" backend/app/` → no matches |
| Production `.rollback()` | **database.py only** | 1 match at `database.py:53` (safety net in `get_db_session`) |
| `session.begin()` owning services | **5** | `business`, `receiving`, `purchase_return`, `purchase`, `business_membership` services |
| `begin_nested()` | **0** | `grep -r "begin_nested" backend/app/` → no matches |
| `AsyncSession(` construction outside `database.py` | **0** | `grep -r "AsyncSession(" backend/app/` → no matches |
| Procurement snapshot/restore | **0** | No `procurement` module with snapshot/restore patterns |
| Production InMemory fallback | **0** | InMemory is primary for some modules, not a PostgreSQL fallback |

---

## Snapshot Status

| Module | Status | Evidence |
|--------|--------|----------|
| Purchase | **RETIRED** | No `_snapshot_all_repos`/`_restore_all_repos` in `purchase/service.py` |
| Receiving | **RETIRED** | No snapshot/restore in `receiving/service.py` |
| Purchase Return | **RETIRED** | No snapshot/restore in `purchase_return/service.py` |
| Sales Return | **RETAIN** | Has `_snapshot_all_repos` + `_restore_all_repos` |
| Delivery Note | **RETAIN** | Has `_snapshot_repositories` + `_restore_repositories` |
| Transfer | **RETAIN** | Has `_snapshot_all_repos` + `_restore_all_repos` |
| Stock Opname | **RETAIN** | Has `balance_snapshot`, `movement_snapshot`, `lines_snapshot` |

No retained snapshots were modified or removed.

---

## Production Source Protection

**Claim**: `backend/app/**` changed = NONE  
**Actual**: **40 files changed** under `backend/app/**` (from `git diff --name-only HEAD -- backend/app/`)  
**Modules affected**: accounting, authentication, business, business_membership, cash_account, customer, expense, inventory, payment, purchase, purchase_return, receiving, sales, sales_return, stock_opname, core/config.py, main.py, conftest.py

**Discrepancy**: Previous claim of zero production changes is factually incorrect. 40 production files show modifications in working tree.

---

## Final Status

**PERSISTENCE PHASE 4.3E-FINAL-FIX — BLOCKED**

**Blocking reasons**:
1. **Fact inconsistency**: Previous reports claimed 6/8 test files changed, 0 production files changed, 197 collected — actuals are 14, 40, 175
2. **Production source not protected**: 40 production files modified in working tree
3. **Test classification contradiction** resolved (INTEGRATION is correct)

**Positive**: All 175 tests in the 8 core Phase 4.3E files **PASSED**. Static audit clean. Snapshot status correct. No new failures introduced.

**Recommendation**: Commit or stash the 40 production file changes (from earlier phases) before final verification. Phase 4.4 should not proceed until working tree reflects only Phase 4.3E test changes.
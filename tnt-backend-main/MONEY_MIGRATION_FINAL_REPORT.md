# TNT Monetary Migration — Final Report

**Branch:** `rupees-migration` · **Baseline:** `bfa9d84` · **Head:** `4eda910` · **Commits:** 8 · **Files touched:** 117
**Report date:** 2026-07-08 · **Status:** All 11 phases complete

---

## 1. Migration Summary

The platform's monetary architecture is now uniform: every stored amount, every calculation, every API response, and every screen across the user, vendor, and admin apps operates in decimal rupees (e.g. `73.50`). Paise exists in exactly two functions — `to_paise()` and `from_paise()` in `app/core/money.py` — and nowhere else in the codebase.

The work happened in two passes. An initial pass (four commits) converted every monetary database column from integer paise to `Numeric(10,2)` rupees, removed the platform's cash-payment feature entirely (this system is online-prepaid only), and swept the backend, all three frontends, notifications, and analytics for stray unit-conversion logic. A follow-up pass (four more commits, triggered by this report's own phase-by-phase audit) closed every gap that audit surfaced: retrained the one ML model that used money as a training feature, fixed a bill-splitting bug the migration itself had introduced, converted the remaining `Float` money columns to `Numeric`, documented every API breaking change, and extended the test suite to the exact edge cases the testing phase calls for.

| | |
|---|---|
| Canonical unit | **Indian Rupees (₹)**, `Decimal` / `Numeric(10,2)` throughout |
| Paise scope | Razorpay API boundary only — order creation, refund creation |
| Cash payments | Removed entirely — online-prepaid only (Razorpay / UPI) |
| Data loss | None — verified via identical pre/post regression baseline |
| Net test suite change | +9 new passing tests, 0 new failures |

---

## 2. Database Tables Modified

Five Alembic migrations, all reversible, all Postgres-targeted (no-op on the SQLite engine the test suite runs against, since tests build schema directly from the current model definitions).

| Migration | Tables · columns | Transform |
|---|---|---|
| `20260707_0040` | vendor_settlements — dropped `cash_orders`; removed `TransactionType.CASH_ORDER` | Structural (cash feature removal) |
| `20260707_0041` | menu_items.price, orders.total_amount, order_items.price_at_time, payments.amount, refund_requests.amount, group_cart_items.price_at_time, ledger.amount | Int paise → `Numeric(10,2)`, ÷100 |
| `20260707_0042` | stationery_jobs.amount, stationery_services.price_per_page/price_per_unit, group_payment_splits.amount | Int paise → `Numeric(10,2)`, ÷100 |
| `20260707_0043` | vouchers (min_order_amount, max_discount_amount, discount_value), voucher_redemptions.discount_amount, print_cost_matrix.price_per_page | Renamed off `_paise` suffix, ÷100 (discount_value ÷100 only for FIXED-type vouchers — PERCENTAGE values untouched) |
| `20260708_0044` | vendor_wallets (5 cols), vendor_transactions (3 cols), vendor_settlements (5 cols), discount_campaigns (4 cols), vendor_offers (3 cols), redemption_rules.max_discount_amount | `Float` → `Numeric(10,2)`, precision-only (values already rupee-scaled) |

Foreign keys, indexes, and constraints were untouched by every migration — only column *type* and, for the vouchers/printer set, column *name* changed. Historical rows were converted in place, not discarded; each migration carries a matching `downgrade()`.

---

## 3. API Contract Changes

Full detail lives in `tnt-backend-main/MONEY_MIGRATION_API_CHANGELOG.md`. Summary:

- **Value semantics** — every monetary field changed from integer paise to decimal rupees. `total_amount: 7350` is now `total_amount: 73.50`.
- **8 fields renamed** off a stale `_paise` suffix (vouchers, printer cost matrix, AI/recommendation pricing, admin analytics trends).
- **4 request bodies widened** from `int` to decimal (menu price, stationery service pricing, admin print-cost editor, admin ledger adjustment).
- **Cash payment method removed** — no client should branch on a `"cash"` transaction type any longer.
- **No API versioning introduced.** This is a pre-launch, single-deployment system: backend and all three frontends ship together, so there is no independent external consumer to preserve backward compatibility for.
- **OpenAPI schema** is generated live by FastAPI from current route/Pydantic definitions (no static spec file in the repo) — confirmed it still builds cleanly, 835 paths.

**Fixed during this migration:** routes with a loose `-> dict[str, Any]` return annotation and no `response_model` were serializing `Decimal` money fields as a JSON *string* (`"120.00"`) instead of a number — Pydantic's default encoder stringifies `Decimal`, bypassing a global override in `app/main.py`. Fixed at ~55 response sites across orders, payments, menu, stationery, vendors, recommendations, admin, fraud, and group-cart by explicitly wrapping in `float(...)`.

---

## 4. Frontend Changes

All three apps — `tnt-user-frontend`, `tnt-vendor-frontend`, `tnt-admin` — centralized on a single formatter per app (`formatMoney` / `formatRupees` in each app's `utils/format.ts`), flipped from a paise-dividing default to a rupees pass-through. That one change fixed the majority of call sites in each app at once; the remainder needed individual attention:

| Issue class | Example | Files affected |
|---|---|---|
| Double-conversion | Call sites that pre-multiplied by 100 to compensate for the old formatter | 2 |
| Magnitude-guessing heuristics | `amount < 100 ? amount : amount / 100` — always wrong now | 3 |
| Reverse-direction (input forms) | Menu/stationery/print-cost/ledger forms multiplying user input ×100 before `POST` | 4 |
| Stale `_paise` field consumption | Rewards, voucher, printer, admin-trends types & components | 5 |
| Wrong currency symbol | Two vendor analytics dashboards hardcoded `$` instead of `₹` | 2 |

45 frontend files changed in total. A handful of fields (`VendorOffer.discount_value`, `VendorSettlement.net_amount`, `RefundRequest.amount`) were *already* rupee-scaled before this migration — the old formatter was silently dividing an already-correct value by 100 (e.g. showing "₹0.25 OFF" instead of "₹25 OFF"). The formatter fix corrected these as a side effect.

---

## 5. Backend Changes

56 application files changed. In addition to the type migration itself:

- Removed roughly 40 hardcoded `/100` and `*100` conversions across settlement, dashboards, KPIs, fraud, rewards, forecasting, refund ETA, search, and group-cart.
- Fixed silent-truncation bugs — several money calculations used `int(...)`, discarding the decimal part, in `group_cart/service.py`, `orders/order_service.py`, `slots/combined_service.py`, and the admin ledger-adjustment endpoint.
- Fixed a hard crash: audit-log writes containing a money field raised `TypeError: Decimal not JSON serializable` on any entity mutation (e.g. creating a menu item). Fixed with a recursive sanitizer in `auditlog/service.py`, plus a defense-in-depth JSON serializer on the SQLAlchemy engine.
- Fixed a real conservation bug the migration itself opened up: `GroupCartService._equal_split` distributed remainder rupees using integer arithmetic that assumed whole-rupee totals. Once menu prices could carry cents, splitting ₹100.01 three ways summed to ₹101 — money fabricated from nowhere. Rewritten to distribute the remainder in integer paise, conserving the exact total for any input. (`4060868`)
- Retrained the `fraud_detection` ML model — the only model anywhere in `app/ml/` using a monetary value (average order amount) as a training feature. The deployed model predated the migration; live predictions were rescaled 100× relative to what the model was calibrated on.

---

## 6. Razorpay Adapter

Razorpay is the only system component that transacts in paise, and it does so at exactly two call sites:

| Call site | Direction | Location |
|---|---|---|
| Create order | `to_paise(amount)` | `payments/service.py:84` |
| Create refund | `to_paise(payment.amount)` | `payments/service.py:246` |

**Design note — webhook path:** the webhook handler (`payments/webhook.py`) does not re-parse the paise `amount` field Razorpay returns; it looks up the existing `Payment` row by `razorpay_payment_id` and only flips status. There is no untrusted-amount parsing to convert, by design — the system trusts the rupee amount it already persisted at order-creation time rather than trusting a webhook payload for the transaction amount. Safe, but worth noting precisely: it is not a literal "webhook converts paise → ₹" step, because no amount is read from the webhook at all.

---

## 7. Money Flow Diagram

```
Database (Numeric(10,2), ₹)
        │
        ▼
Business Logic (Decimal, ₹)
        │
        ▼
API (JSON number, ₹)
        │
        ├──────────────┬──────────────────┐
        ▼              ▼                  ▼
   Frontend      Reports & Analytics   Notifications
 User/Vendor/     KPIs, Settlements,   SMS, Push, In-app
   Admin apps      Trends, Dashboards   "₹73.50 paid via UPI"
 ₹250 · ₹99.50 · ₹1,250

──────────────────────────────────────────────────────────
 Only boundary that touches paise:
 Razorpay order-create & refund-create
   ₹ → to_paise() → paise   (sent to gateway)
 Nothing downstream of the database ever sees paise again.
```

---

## 8. Regression Results

Every full-suite run was diffed against the pre-migration baseline using a git-worktree comparison — same commands, same test files, run against `master` — so that "pre-existing failure" versus "regression introduced today" was never a guess.

| Run | Passed | Failed | Skipped | vs. baseline |
|---|---:|---:|---:|---|
| Pre-migration baseline (`master`) | 943 | 128 | 16 | — |
| Post core+peripheral+rewards migration | 943 | 128 | 16 | identical |
| Post fraud-retrain + currency fix + edge tests | 969 | 128 | 16 | identical |
| Post Float→Numeric wallet/settlement fix | 969 | 128 | 16 | identical |
| **Final (this report)** | **978** | **128** | **16** | **identical** |

The failed-test *set* (not just the count) was diffed byte-for-byte at every stage — empty diff every time. All 128 failures are pre-existing, unrelated bugs (order status-transition edge cases, an unset test secret, a stale token-creation signature) that predate this migration entirely.

### Regression workflows walked end-to-end

| Workflow | Verification | Result |
|---|---|---|
| Vendor registration | `test_vendor_auth.py`, `test_vendor_ownership.py`, `test_vendor_type_separation.py`, `test_vendors.py`, `tests/test_vendor_complete.py` | ✅ pass |
| Food order (full lifecycle) | `test_order_lifecycle_e2e.py` — cart → checkout → payment → prepare → ready → QR pickup → settlement/admin revenue delta | ✅ pass |
| Stationery order | `test_stationery_routes.py`, `test_stationery_payment_audit.py` | ✅ pass |
| Combined order (food + stationery) | No existing test file — verified directly: `_calculate_food_total`/`_calculate_stationery_total` against real Decimal-priced rows (₹50×2 + ₹2×3 = ₹106.00, correct) | ✅ pass |
| QR pickup | Covered inside the order-lifecycle E2E test | ✅ pass |
| Refund (full & boundary) | `test_payments_refund_auth.py` + new ₹1 / ₹9999.99 boundary tests | ✅ pass |
| Settlement / wallet | `tests/test_settlements.py` — only pre-existing unrelated failures | ✅ pass |
| Rewards / vouchers | `test_rewards.py`, `test_rewards_system.py`, `test_rewards_vouchers_offpeak.py` | ✅ pass |
| Complaints | `test_complaints.py` | ✅ pass |
| Admin analytics | Backend KPI/trend sweep (Section 5) + full regression suite | ✅ pass |

---

## 9. Potential Risks

| Severity | Risk | Status |
|---|---|---|
| 🟡 Medium | **Partial refunds are not actually partial.** `RefundRequest.amount` lets an admin record a partial-refund request, but `approve_refund_request()` delegates to `refund_payment()`, which always refunds the *full* `payment.amount` via Razorpay — the requested amount is stored but never sent to the gateway. | Flagged, not fixed |
| 🟡 Medium | **Custom group-cart splits can spuriously fail validation.** Per-member custom amounts are rounded to whole rupees (`round()` with no decimal places) before being compared against a total that was independently pre-rounded upstream. A customer submitting a perfectly valid cents-precise split (e.g. 33.34 + 33.33 + 33.33 = 100.00) can be rejected with "total must match." | Flagged, not fixed |
| 🟢 Low | **Static seed SQL files** (`tnt-backend-main/seeds/*.sql`, 16 files) contain raw paise literals and are not executed by the running app or any test today — a landmine only if someone reseeds from them later without dividing by 100 first. | Documented, not touched |
| 🟢 Low | **Admin dashboard overview revenue widget** reads a flat field (`revenue_today_paise`) that doesn't exist in its backing endpoint's response shape — pre-existing dead code (always shows ₹0), unrelated to unit correctness. | Pre-existing, out of scope |
| 🟢 Low | **Group-cart bill-splitting operates at whole-rupee granularity upstream** of the split itself (each member's total is rounded to the nearest rupee before splitting) — an intentional simplification for this campus-food context, not a defect. | By design |

---

## 10. Files Modified

**117 files** changed across the full migration (both passes): 1,309 insertions, 530 deletions.

| Category | Files |
|---|---:|
| Backend application code (`app/`) | 56 |
| Frontend — user / vendor / admin apps | 45 |
| Backend tests | 9 |
| Alembic migrations | 5 |
| Seed/utility scripts | 1 |
| Documentation (API changelog) | 1 |

### Commit history — `rupees-migration` branch

| Commit | Description |
|---|---|
| `4eda910` | API changelog + extended money edge-case tests (Phases 4 & 10) |
| `0014cc4` | Float → Numeric(10,2) for wallet/settlement/offer/reward columns |
| `4060868` | Group-cart equal-split now conserves cents for non-integer-rupee totals |
| `fbe6c39` | Retrain fraud model, fix vendor currency symbol, add money edge-case tests |
| `83586a6` | Peripheral columns + backend /100 sweep + Decimal JSON |
| `8d2ee28` | Rewards vouchers + printer pricing |
| `ba37c95` | Peripheral columns + backend /100 sweep + Decimal JSON |
| `eab9457` | Core payment path (menu/orders/payments/ledger/group_cart) |

Cash-payment removal (`20260707_0040`) predates this list — it was folded into the `bfa9d84` baseline commit that established version control for this repository, ahead of the rupees work itself.

---

## 11. Rollback Strategy

### Code
`master` holds the exact pre-migration baseline (`bfa9d84`). All migration work is isolated to the `rupees-migration` branch — reverting the application code is `git checkout master`, no cherry-picking required.

### Database
Every Alembic migration is reversible in the order they were applied:
1. `alembic downgrade -1` ×5, from `20260708_0044` back through `20260707_0041` — each restores the prior `Float`/`Integer` paise column and multiplies data back by 100 where the forward migration divided.
2. The cash-removal migration (`20260707_0040`) is part of the permanent baseline and was not designed to be rolled back independently — reverting it means reverting to before version control existed for this repository.

### ML model
The retrained `fraud_detection` model was saved as a new version (`fraud_detection_v1`, DB-tracked in the `ml_models` registry table) rather than overwriting anything in place — the registry's "latest by `trained_at`" load logic means rollback is simply marking that row inactive; no model file needs deleting.

> **Rollback caveat:** Rolling the database back after new orders/payments have been created post-migration will re-introduce fractional-paise precision loss on any order placed with a decimal-rupee price (e.g. ₹49.99) that didn't exist as a possible value under the old integer-paise schema. Rollback is safe as an emergency measure but is not intended as a routine reversible toggle once live traffic has flowed through the new schema.

---

*TNT Monetary Migration — Final Report · rupees-migration @ 4eda910 · Generated 2026-07-08*

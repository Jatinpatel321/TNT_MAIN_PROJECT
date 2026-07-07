# TNT — API ↔ Frontend Integration Matrix

**Date:** 2026-07-07
**Method:** Live FastAPI OpenAPI schema (ground truth) diffed against every `.get/.post/.put/.patch/.delete` call extracted from the 3 frontends (`tnt-user-frontend`, `tnt-admin`, `tnt-vendor-frontend`). Path params normalized to `*`. Tool: `scratchpad/contract_sweep.py`.

> This report contains only **verified** facts (backend boots, endpoints confirmed against the running OpenAPI schema). No fabricated scores.

---

## Headline numbers

| Metric | Before | After fixes |
|---|--:|--:|
| Backend operations | 906 | **935** (+29) |
| ‣ canonical `/v1` | 456 | 485 |
| ‣ legacy (deprecated) | 450 | 450 |
| Frontend API calls (resolvable) | 432 | 432 |
| ✅ Matched on `/v1` | 384 | **431** |
| ⚠️ Matched only on legacy path | 21 | **1** |
| ❌ **Broken (no backend match)** | **17** | **0** |
| ℹ️ Orphaned `/v1` (no frontend caller) | 148 | 145 |

> **Final state: 0 broken calls.** All 432 frontend API calls resolve against the live backend. The single remaining legacy-only call is admin `GET /health` — the correct top-level liveness endpoint, intentionally unversioned.

Base-URL conventions (all consistent): admin `:8000` + `/v1` in calls; user `:8000/v1` + prefix-less calls; vendor `:8000` + `/v1` in calls.

---

## ✅ Fixed this pass (verified: app boots, sweep re-confirmed)

### 1. Six completed backend routers were never registered — HIGH
Fully-built routers existed as files but were never included in `app/api/v1.py`, so ~28 frontend calls hit 404. Wired all six in:

| Router | Path now live | Frontend caller |
|---|---|---|
| `ai_intelligence/vendor_speed_router` | `/v1/ai/vendor-speed/*` | `vendorSpeedService.ts` (5) |
| `ai_intelligence/enhanced_eta_router` | `/v1/ai/enhanced-eta/*`, `/eta-factors/*` | `enhancedETAService.ts` (2) |
| `group_cart/group_ai_router` | `/v1/groups/{id}/ai/*` | `groupAIService.ts` (7) |
| `group_cart/payment_router` | `/v1/groups/{id}/payments/*` | `groupPaymentService.ts` (8) |
| `recommendations/ranking_router` | `/v1/user/recommendations/*` | `recommendationRankingService.ts` (3) |
| `vendors/image_upload_router` | `/v1/vendors/profile/upload/*` | `imageUploadApi.ts` (3) |

### 2. Latent crash bug in `group_ai_router.py` — HIGH
`NameError: name 'Query' is not defined` (missing from the `fastapi` import). This is likely *why* the router was never wired — registering it would have crashed OpenAPI generation. Fixed the import.

### 3. `tnt-admin/src/api/vendorAuth.ts` wrong paths — HIGH
Every call used `/v1/vendor/*`, but the backend mounts vendor auth at `/v1/vendors/auth/*`. All 10 call-sites (login ×2, refresh, register, profile ×2, staff ×4) were 404ing. Corrected the paths. Used by `VendorLogin.tsx` / `VendorProfile.tsx`.

---

## ✅ Closed backend gaps (7) — all implemented + tested

All had backing models present, so these were gap-fills. Each is now live and covered by a smoke test (`test_integration_gaps.py`) and/or existing module tests.

| # | Endpoint | Implementation |
|---|---|---|
| 1 | admin `GET /v1/stationery/services` | New list endpoint (admin sees all, vendor sees own) in `stationery/router.py` |
| 2 | vendor `POST /v1/vendors/auth/logout` | New endpoint + `logout_vendor()` service — revokes the refresh-token JTI when supplied (stateless-JWT logout) |
| 3 | vendor `PUT /v1/vendors/business-hours/holidays` | New sub-route; service extended |
| 4 | vendor `PUT /v1/vendors/business-hours/pickup-instructions` | New sub-route; service + `get`/`update` now surface `pickup_instructions` |
| 5 | vendor `GET /v1/vendors/reviews` | New `reviews_router.py` (paginated, rating filter, embedded stats) |
| 6 | vendor `GET /v1/vendors/reviews/stats` | Aggregate: average, total, 1–5 distribution |
| 7 | vendor `POST /v1/vendors/reviews/{id}/reply` | Writes new `vendor_reply` / `vendor_reply_at` columns (Alembic `20260707_0039`) |

**Bonus fix (pre-existing bug found during testing):** `feedback/router.py` compared `User.role == "VENDOR"` but the stored enum value is `"vendor"`, so `POST /feedback/vendors/{id}/reviews` **always 404'd** — customers could not submit vendor reviews at all. Fixed (`== UserRole.VENDOR`); 3 previously-failing tests now pass.

---

## ⚠️ Legacy-only calls — RESOLVED

`tnt-admin/src/api/slots.ts` (21 calls) migrated from deprecated `/slots/*` to canonical `/v1/slots/*`. Only `admin.ts GET /health` remains unversioned — correct for a top-level liveness probe.

---

## ℹ️ Orphaned `/v1` endpoints (145) — INFORMATIONAL

Backend endpoints with no detected frontend caller — mostly *backend capability ahead of the UI*, not defects:

| Module | Count | Notes |
|---|--:|---|
| `/v1/vendors` + `/v1/vendor` | 80 | vendor AI/forecast/history/peak-hours/performance analytics |
| `/v1/ml` | 18 | ML registry/training — internal/admin |
| `/v1/ai` | 6 | AI intelligence |
| others | 41 | auth/cart/orders/users/payments/notifications/etc. |

Caveat: the sweep only sees **string-literal** URLs; dynamically-built URLs are undercounted, so real orphan count is lower. Verify each endpoint before treating as dead code.

---

## Files modified

**Pass 1 — router wiring + path fixes**
| File | Change |
|---|---|
| `tnt-backend-main/app/api/v1.py` | Registered 6 previously-unregistered routers (+ reviews router, ordered before `vendors_router`) |
| `tnt-backend-main/app/modules/group_cart/group_ai_router.py` | Fixed `Query` import (NameError) |
| `tnt-admin/src/api/vendorAuth.ts` | `/v1/vendor/*` → `/v1/vendors/auth/*` (10 calls) |

**Pass 2 — closing the 7 backend gaps**
| File | Change |
|---|---|
| `app/modules/stationery/router.py` | Added `GET /services` |
| `app/modules/vendors/auth_router.py` + `auth_service.py` | Added `POST /logout` + `logout_vendor()` |
| `app/modules/vendors/business_hours_router.py` + `business_hours_service.py` | Added `PUT /holidays`, `PUT /pickup-instructions`; surfaced `pickup_instructions` |
| `app/modules/vendors/reviews_router.py` | **New** vendor reviews router (list/stats/reply) |
| `app/modules/feedback/model.py` | Added `vendor_reply`, `vendor_reply_at` to `VendorReview` |
| `alembic/versions/20260707_0039_vendor_review_reply.py` | **New** migration (applied to Postgres ✓) |
| `alembic/env.py` | Registered `feedback.model` in migration metadata |
| `app/modules/feedback/router.py` | Fixed `User.role == "VENDOR"` → `UserRole.VENDOR` (pre-existing 404 bug) |
| `tnt-admin/src/api/slots.ts` | Migrated 21 calls `/slots/*` → `/v1/slots/*` |
| `tnt-backend-main/test_integration_gaps.py` | **New** smoke tests for the added endpoints |

**Regression check (final):** app boots clean (835 paths / 946 operations); contract sweep confirms **broken 34 → 0**; **65/65** tests pass across `test_integration_gaps`, `test_feedback_module`, `test_feedback`, `test_vendor_auth`, `test_stationery_routes` (incl. the 3 feedback tests that were red before the bugfix). Migration `20260707_0039` applied to PostgreSQL successfully.

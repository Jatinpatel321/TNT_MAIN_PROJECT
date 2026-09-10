# TNT codebase audit — verdict and defect report

**Verdict: NO-GO for production release.**

**Reviewed:** `TNT_MAIN_PROJECT-main (9).zip` • **Report date:** 9 September 2026

The supplied snapshot contains exploitable authentication and payment design defects, broken active backend paths, and a user-app deployment configuration that points to the device itself. The Admin, vendor and user interfaces should not be considered production-ready on the evidence of this snapshot. Passing Python syntax checks and having a substantial feature set do not resolve these defects.

This is a repository-wide static audit with targeted manual tracing and isolated local reproductions. It is **not** a completed live penetration test, full dependency-backed test run, or certification that every bug has been found. No application source was changed and no external system was contacted to exercise vulnerabilities.

## 1. Scope and coverage

All four application directories were inventoried. Automated checks covered Python syntax, local frontend import resolution, backend model/enum references, local Python import candidates, literal frontend API paths, and the migration dependency graph. Manual review concentrated on authentication, roles, staff permissions, payments/refunds, group features, uploads, analytics, recommendation contracts, and client configuration.

| Component | Files | Source files¹ | Source lines¹ | Assessment |
|---|---:|---:|---:|---|
| Backend — `tnt-backend-main` | 546 | 460 | 112,622 | Release blocked by security, money-flow and runtime defects |
| Admin — `tnt-admin` | 107 | 90 | 20,138 | Release blocked by ineffective backend 2FA; finance and analytics defects |
| Vendor — `tnt-vendor-frontend` | 153 | 107 | 19,821 | Release blocked by vendor-token security and incomplete permission enforcement |
| User — `tnt-user-frontend` | 210 | 109 | 21,368 | Release blocked by mock checkout and production API configuration |

¹ `.py`, `.ts`, `.tsx`, `.js`; includes tests and support scripts, not just production code. Root-level reports/assets account for the remainder of the **1,065 files** inventoried by `rg --files`. Existing project audit/completion documents were not accepted as proof of correctness.

**Recorded findings: 22 — 3 Critical, 10 High, 8 Medium, 1 Low.** Severity is an engineering risk judgment, not a calculated CVSS score. Related defects are grouped where they share a repair boundary.

## 2. Findings at a glance

| ID | Severity | Affected area | Finding |
|---|---|---|---|
| F01 | Critical | Backend / user checkout | Always-successful mock payment is publicly routed in production code |
| F02 | Critical | Vendor authentication | Vendor JWT signing key is hardcoded |
| F03 | Critical | Admin authentication | Fully privileged tokens issued before TOTP verification |
| F04 | High | Vendor registration | Unauthenticated registration can bind to another user's phone and change their role |
| F05 | High | Vendor / staff authorization | General guard bypasses vendor/staff status and module permissions |
| F06 | High | Admin / shared authorization | Role changes do not invalidate the authority in existing sessions |
| F07 | High | Group APIs | Authentication without group membership/actor authorization |
| F08 | High | Group payments | Service depends on nonexistent persisted payment fields and enum member |
| F09 | High | Group payments | Gateway order creation and signature verification are placeholders |
| F10 | High | Refunds | Owner can request a refund without order-state eligibility checks |
| F11 | Medium | Refund tracking | Estimated completion becomes asserted bank completion |
| F12 | High | User recommendations | Dict/object mismatch and missing `await` break ranking endpoints |
| F13 | Medium | Recommendation scoring | Imports a nonexistent `MenuItemReview` model |
| F14 | Medium | Admin analytics | Wastage query references nonexistent `User.username` |
| F15 | Medium | Vendor forecasting | Vendor-type forecast references nonexistent profile fields |
| F16 | Medium | Vendor promotions | Disabling a campaign uses nonexistent enum value |
| F17 | Medium | Admin finance | Cancelling rejection prompt still submits rejection |
| F18 | High | User release configuration | API URL always points at localhost over HTTP |
| F19 | Medium | User type checking | Included navigation file imports a missing screen and undeclared dependency |
| F20 | High | Stationery uploads | Customer documents are served through an unauthenticated static mount |
| F21 | Medium | Stationery uploads | PDF helper trusts client MIME type and reads without a size bound |
| F22 | Low | Backend routing | Complete v1 router registered twice |

**Evidence labels used below:** “source-confirmed” means the defect follows from the supplied source and a traced call path; “isolated reproduction” means a source expression/function was executed locally with controlled stand-ins where needed. Neither label means a deployed endpoint was tested.

## 3. Detailed findings

### F01 — Always-successful mock checkout [Critical]

**Locations:** `tnt-backend-main/app/modules/payments/router.py:26–109` (`mock_payment`); `app/api/v1.py` includes `payments_router` unconditionally; `app/main.py:358` also mounts its legacy routes. Client callers: `tnt-user-frontend/src/screens/slots/SlotSelectionScreen.tsx:181` and `src/screens/groups/GroupDetailScreen.tsx:361`.

The route `/v1/payments/mock` checks login and order ownership but never checks the environment or verifies funds. It marks payment SUCCESS and unconditionally sets the order to CONFIRMED. The caller can supply a negative amount, choose WALLET without a wallet debit, and replay the action against an already cancelled or completed order. The function does not use the real payment finalization/ledger pipeline.

**Observed:** Executing the actual function body with a fake session, an owned CANCELLED order worth 100 and `amount=-1` returned SUCCESS, amount `-1.0`, changed the order to CONFIRMED, and committed once. The fake session verifies control flow, not SQL behavior.

**Impact:** A logged-in customer can confirm an order without payment; accounting, stock and order-state invariants may diverge. The user app depends on this route, so simply removing it also requires fixing checkout.

**Fix / acceptance:** Exclude the route from production entirely. Connect both client checkout paths to real gateway initiation and verification; implement actual wallet debits if offered. Derive amounts server-side, enforce transitions, and finalize idempotently through one transaction boundary. In a production-configured integration test the mock route must be absent; payment failure must never confirm an order.

### F02 — Hardcoded vendor JWT signing key [Critical]

**Location:** `tnt-backend-main/app/modules/vendors/auth_service.py:44–47`, token creation at `:67–99`, verification at `:139–176`; vendor-key fallback also exists in `app/core/security.py`.

The HMAC signing key is a fixed source literal, rather than an environment secret. The same literal is used for minting and checking vendor JWTs. Configuring the normal user `SECRET_KEY` does not replace this separate key. The literal is intentionally not repeated in this report.

**Impact / reproduction:** With this source, an attacker can sign a vendor-owner access token for an existing active vendor ID. The vendor guard accepts the signature and relies on the claimed owner role. This is a vendor-account impersonation vulnerability; it does not establish arbitrary admin impersonation.

**Fix / acceptance:** Replace the constant with a mandatory independently managed secret, reject insecure defaults at startup, rotate it before deployment and invalidate all old vendor sessions. Test that a token signed with the shipped literal fails validation.

**Evidence:** Source-confirmed; no forged token was sent to any service.

### F03 — Admin TOTP can be skipped [Critical]

**Locations:** `tnt-backend-main/app/modules/auth/router.py:161–186` and `:256–272`; `app/core/security.py`, `get_current_user` / `require_role`.

OTP verification creates ordinary admin access and refresh tokens before calculating `requires_2fa`. The flag only informs the client. Admin route guards do not require a verified second-factor claim or session state. The TOTP endpoint merely returns `fully_authenticated: true`; it does not elevate a restricted token to a privileged token.

**Reproduction:** For an active admin with TOTP enabled, complete the phone OTP step, take the returned access token and call an admin endpoint without calling the TOTP endpoint. The guards check the token role and active user, not completion of TOTP. The returned refresh token also carries the admin role.

**Fix / acceptance:** Issue a short-lived, restricted challenge credential after OTP. Issue privileged access/refresh tokens only after TOTP succeeds; exclude challenge credentials from all normal guards and refresh flows. Integration tests must deny every protected admin operation before TOTP.

**Evidence:** Source-confirmed. This bypass still requires obtaining the first factor; it does not bypass phone OTP itself.

### F04 — Vendor registration trusts someone else's phone [High]

**Locations:** `tnt-backend-main/app/modules/vendors/auth_router.py:57–77`; `app/modules/vendors/auth_service.py:192–243`.

The registration route has no authentication dependency. `register_vendor` looks up the submitted `owner_phone`, assigns that existing user as owner, accepts the submitted vendor password, and changes a non-vendor role to VENDOR. There is no proof the caller owns that phone.

**Reproduction / impact:** Submit a known existing user's phone that does not already own a vendor. The endpoint can create a pending business attached to that user and change their role. Choosing an admin's eligible phone can also alter their account role. Vendor activation remains a separate prerequisite for ordinary vendor login; registration alone does not activate the business.

**Fix / acceptance:** Require verified authentication and derive `owner_id` from the session. Enforce eligible source roles and move exceptional role changes into an audited admin workflow. Requests naming another user's phone must not mutate their account.

### F05 — Staff restrictions are not enforced consistently [High]

**Locations:** `tnt-backend-main/app/core/security.py:141–178` (vendor branch); `app/modules/vendors/auth_service.py:166–181` (stricter alternative guard); `app/modules/menu/router.py:34–72,96–150`; `tnt-vendor-frontend/src/context/PermissionsContext.tsx:34–75`.

The general `get_current_user` vendor branch checks that the vendor exists and its owner is active, but does not check vendor status or the staff record. It maps a vendor-staff token to the owner's user ID and general role `vendor`. Menu mutations use `require_role("vendor")` and do not check the staff member's `menu` permission. Other routes use a different, stricter guard, so enforcement varies by endpoint.

**Reproduction:** Give an active staff member no menu permission and call a menu mutation directly with their vendor token. The UI restriction is absent from this server path. Repeat with an already-issued token after disabling/deleting that staff member: the general guard still never looks up the staff record. A suspended business with an active owner has the same status-check gap.

**Fix / acceptance:** Centralize vendor authentication, check current vendor and staff status on every request, retain staff identity, and enforce required permissions server-side for every mutation. Test an owner, permitted staff, unpermitted staff, disabled staff, deleted staff and suspended vendor against each route family.

**Evidence:** Source-confirmed. Owner-only checks already present in some staff-management endpoints do not fix menu and other general-guard endpoints.

### F06 — Demoted users retain token privileges [High]

**Locations:** `tnt-backend-main/app/modules/admin/router.py:1294–1340`; `app/core/security.py`, end of `get_current_user`; `app/modules/auth/refresh_router.py:96–113`.

Role updates modify the database but the general auth guard returns `role` from the JWT instead of the current database role. Refresh reads the old role from its stored payload and issues it again. The role-update path does not revoke these sessions.

**Reproduction / impact:** Demote an active admin to student. Their existing admin token continues to satisfy the admin guard; their existing refresh token can mint further admin access tokens until revoked or expired. Updating the admin UI's role display cannot remove this authority.

**Fix / acceptance:** Authorize against current database roles, and revoke/version sessions on role changes. Refresh must use current account attributes. Verify immediate denial of the old access token and correct role after refresh.

### F07 — Group APIs do not authorize the caller against the group [High]

**Locations:** `tnt-backend-main/app/modules/group_cart/payment_router.py:64–284`; `group_ai_router.py`, group-specific handlers; `payment_service.py:163–225`.

The routes obtain an authenticated user but do not pass their identity into the group services for membership checks. Payment mutations instead accept `request.user_id`; the service checks that submitted target ID is a member, not that the caller is authorized. Group AI routes similarly look up a supplied group ID without membership authorization.

**Reproduction / impact:** An authenticated non-member can request another group's AI/payment details and invoke group-targeted actions. On payment paths, F08 currently causes runtime errors for common data states; fixing that model without fixing authorization would expose arbitrary-member payment mutation.

**Fix / acceptance:** Check caller membership before reads and owner/actor permission before mutations. Derive the paying user from the session. Authorize reminders and split changes explicitly. Cross-group tests must return 403/404 and produce no state changes or notifications.

**Evidence:** Source-confirmed; this report does not claim a successful forged persisted group payment in the currently broken model.

### F08 — Group payment service and schema disagree [High]

**Locations:** `tnt-backend-main/app/modules/group_cart/model.py:37–40,109–124`; `payment_service.py:219–248,276–308,351`; split branch at `:113`.

`GroupPaymentSplit` has no mapped `amount_paid`, `payment_status`, `paid_at`, `payment_method`, or `razorpay_payment_id`. The service reads these fields directly and also queries `GroupPaymentSplit.payment_method`. Normal ORM-loaded rows cannot supply them. Merely assigning extra Python attributes would not persist them as columns. The service also references `PaymentSplitType.PERCENTAGE`, while the enum provides EQUAL, CUSTOM and UNIFIED.

**Reproduction:** Load an existing split and request payment status or record a payment: reading `amount_paid` fails. Request contributions: the class-level payment-method query fails. Calculate a valid `unified` split: the subsequent nonexistent PERCENTAGE comparison raises an AttributeError. A `percentage` input is not a valid enum value in the request model.

**Observed:** Local inspection/execution against the supplied class declarations confirmed all five missing fields and the missing enum member.

**Fix / acceptance:** Define one supported split contract, add real model columns and migrations, update serializers and calculations, and use Decimal-safe amount handling. Test persisted rows across sessions, not objects embellished by mocks. Verify equal/custom/unified behavior and explicit rejection or support of percentage splitting.

### F09 — Group gateway implementation is unfinished [High]

**Location:** `tnt-backend-main/app/modules/group_cart/payment_service.py:554–638`.

Gateway-order creation manufactures a string rather than calling Razorpay. Verification assigns `verified = True` and never verifies the supplied signature. The separate record path accepts an optional gateway payment ID and directly updates the split.

**Impact:** Returned order IDs do not represent real gateway orders. Once F08 is repaired, the verification path would accept unverified payment claims on a payable split. The current model crash must not be treated as a security control.

**Fix / acceptance:** Use the real gateway adapter, server-computed outstanding amounts, stored gateway-order associations, signature verification and idempotent event handling. Disable these routes until implemented. Invalid signatures and invented order IDs must fail without payment-state changes.

**Evidence:** Source-confirmed placeholder implementation; no real gateway test performed.

### F10 — Refund eligibility ignores order lifecycle [High]

**Location:** `tnt-backend-main/app/modules/payments/service.py:226–277`.

`refund_payment` authorizes the payment owner or admin and requires payment SUCCESS, then calls the gateway refund API. It does not first restrict the linked order's state or require an approved refund request. After refunding, it attempts a cancellation; if that transition raises, it forcibly sets CANCELLED.

**Reproduction / impact:** A customer with a successfully paid, already fulfilled order can request the direct refund endpoint. The code attempts the monetary refund before any order-transition check, then can overwrite a terminal order state. This bypasses the separate administrative refund-review workflow.

**Fix / acceptance:** Apply explicit refund eligibility and review policy before any gateway side effect. Enforce authorized lifecycle transitions instead of overriding failures. Test fulfilled, cancelled, refunded and pending orders, repeated requests, and gateway-success/database-failure recovery.

**Evidence:** Source-confirmed; whether a particular deployed payment is refundable also depends on gateway rules. No financial operation was executed.

### F11 — Refund estimate is reported as confirmed completion [Medium]

**Locations:** `tnt-backend-main/app/modules/ai_intelligence/planners/refund_eta_engine.py`, `progress`; `app/modules/payments/service.py:351–392`.

Once local time passes `estimated_refund_at`, `progress` changes persisted status to COMPLETED and tells the user the refund has completed. It checks no gateway or bank confirmation. The status endpoint commits this mutation.

**Observed:** Executing the actual function body with a processing refund whose ETA had passed returned `completed`, 100%, and “Your refund has been completed,” without any gateway input.

**Fix / acceptance:** Keep estimated progress separate from confirmed financial status. Only verified provider events or reconciliation should complete the refund. A delayed refund must remain processing/overdue after the estimate passes.

### F12 — Recommendation ranking routes cannot use their auth/service contracts [High]

**Locations:** `tnt-backend-main/app/modules/recommendations/ranking_router.py:59–83,105,125`; `smart_engine.py:85`; auth return value in `app/core/security.py`.

`get_current_user` returns a dictionary. The ranking handlers access `user.id`, so authenticated requests raise AttributeError. In `/ranked`, `engine.get_recommendations` is asynchronous but is called without `await`; fixing the ID access alone leaves `base_recs` as a coroutine and `.get(...)` fails.

**Reproduction:** Call `/v1/user/recommendations/ranked`, `/insights/{item_id}`, or `/rank` with an authenticated account. The first defect is independent of database content. After fixing dictionary access, exercise `/ranked` to expose the missing await.

**Fix / acceptance:** Use a consistent typed auth context and await the engine. Test all three routes with real dependency injection and nonempty recommendation data.

**Evidence:** Source-confirmed. Corresponding client methods exist in `tnt-user-frontend/src/services/recommendationRankingService.ts`.

### F13 — Popularity scoring imports a nonexistent model [Medium]

**Location:** `tnt-backend-main/app/modules/recommendations/ranking_service.py:143–154`; model source: `app/modules/feedback/model.py`.

The scoring method imports `MenuItemReview`, which is not defined/exported by the feedback model. A popularity calculation that reaches this statement raises ImportError. F12 masks this defect in some API paths.

**Fix / acceptance:** Use the actual review schema, with a valid item-rating join if needed, or introduce the intended model and migration. Test popularity scoring on both unrated and rated items after repairing the outer routes.

### F14 — Admin wastage dashboard queries a missing field [Medium]

**Locations:** `tnt-backend-main/app/modules/admin/kpi_service.py:754,762`; route at `app/modules/admin/router.py:829`; `app/modules/users/model.py:17` onward.

The vendor breakdown groups by `User.username`; the User model has `name`, not `username`. The expression raises AttributeError before the vendor-wastage query executes, breaking `/v1/admin/analytics/wastage` under otherwise normal database operation.

**Observed:** The missing class attribute was confirmed against the supplied model declaration.

**Fix / acceptance:** Use the correct display field and group by stable vendor identity as well as label, so vendors with identical names do not merge. Exercise the dashboard with cancelled orders and duplicate display names.

### F15 — Vendor-type forecasting uses nonexistent profile attributes [Medium]

**Locations:** `tnt-backend-main/app/modules/vendors/enhanced_forecasting_service.py:763–774`; caller `enhanced_forecasting_router.py:188`; `profile_models.py:11` onward.

`forecast_by_vendor_type` filters on `VendorProfile.user_id`, which does not exist. The model is keyed by business `vendor_id`. The next classification reads `vendor.vendor_type`, also not defined on that profile model. User IDs and business vendor IDs are separate namespaces elsewhere in the project.

**Observed:** The absent `user_id` class attribute was confirmed from the supplied declaration.

**Fix / acceptance:** Resolve owner-user ID to business vendor ID through Vendor, and read type/category from its actual authoritative model. Test vendors whose business ID differs from owner ID, including stationery vendors.

### F16 — Deactivating a campaign raises AttributeError [Medium]

**Locations:** `tnt-backend-main/app/modules/vendors/promotion_router.py:94–96`; `retention_models.py:20–26`.

Toggling an active campaign off sets `CampaignStatus.INACTIVE`, but the enum contains DRAFT, ACTIVE, PAUSED, COMPLETED and CANCELLED. The failure occurs before the commit.

**Observed:** Evaluating the referenced enum member against the supplied enum raises AttributeError.

**Fix / acceptance:** Adopt the intended existing state, likely PAUSED, or migrate a deliberately introduced state. Verify both toggle directions and consistency between `status` and `is_active`.

### F17 — “Cancel” still rejects the refund [Medium]

**Location:** `tnt-admin/src/pages/finance/Finance.tsx:89–95`, `rejectRefund`.

`window.prompt(...) || ''` turns the cancellation value `null` into an empty string before `if (note === null) return`. Consequently the cancellation guard never fires and the rejection request is submitted with an empty note.

**Observed:** Node evaluation of the exact expression with `null` produced an empty string and `cancelGuard=false`.

**Fix / acceptance:** Preserve the raw prompt return, check for null, then validate/normalize the note. Clicking Cancel must produce no API call and no state change.

### F18 — User release builds call the device's localhost [High]

**Location:** `tnt-user-frontend/src/constants/api.ts:14–15`, consumed by `src/services/apiClient.ts`.

The user app always uses `http://localhost:8000`; it has no production switch. `localhost` on a distributed mobile app refers to the device itself. The comments describe an `adb reverse` development setup, which does not exist on ordinary customer devices.

**Reproduction / impact:** Install a release build on a device without a local server or USB reverse tunnel. Authentication and API calls cannot reach the intended backend. This blocks normal deployment even if server defects are fixed.

**Fix / acceptance:** Inject an HTTPS production URL per build environment and validate release configuration. Smoke-test the release build on a physical device over ordinary Wi-Fi/mobile data without developer tunnels.

### F19 — User typecheck includes a broken navigation module [Medium]

**Locations:** `tnt-user-frontend/src/navigation/AppTabs.tsx:3,8`; `tsconfig.json` includes `src/**/*`; `package.json`.

`AppTabs.tsx` imports `../screens/OrdersScreen`, but that target is absent. It also imports `@expo/vector-icons`, which is not declared in the user application's dependencies. The absent local screen is independently sufficient for a TypeScript module-resolution failure when this included file is checked.

**Evidence:** Repository-wide relative-import resolution found the missing screen. Full TypeScript checking could not run because project dependencies/compiler were unavailable.

**Fix / acceptance:** Remove obsolete navigation code or point it to the real screen and the intended icon package. Run the user project's typecheck on a clean install. This finding does **not** establish that the active Metro navigation graph imports this file or that every launch crashes.

### F20 — Printing documents are publicly retrievable by URL [High]

**Locations:** `tnt-backend-main/app/core/file_upload_stationery.py:6–23`; `app/modules/stationery/router.py:158`; `app/main.py:404`.

Customer PDFs are stored under `uploads/stationery`, and the entire uploads tree is exposed through `StaticFiles` without an authentication dependency. Possession of the document URL is enough to retrieve it; UUID filenames reduce guessing but are not user/vendor authorization.

**Reproduction / impact:** Obtain a document URL from an authorized job response, then request the same URL with no bearer token. The supplied app routes it to the public static handler. Private customer print documents can remain accessible through shared/leaked URLs.

**Fix / acceptance:** Store print documents outside public assets and expose an authorized download route or narrowly scoped expiring access link. Verify owner/assigned-vendor access, denial for unrelated and anonymous users, and retention/deletion behavior. An external reverse proxy could alter exposure; none was validated in this review.

### F21 — Printing upload helper has no content/size enforcement [Medium]

**Location:** `tnt-backend-main/app/core/file_upload_stationery.py:9–21`.

The helper accepts the declared `application/pdf` MIME value and writes `file.file.read()` wholesale. It does not inspect PDF bytes or enforce a size limit. The job route calls this helper. UploadFile spooling does not prevent the subsequent unbounded read into memory.

**Reproduction / impact:** A non-PDF payload labeled as PDF is accepted by this helper; a sufficiently large authenticated upload can consume substantial memory and disk. A reverse proxy may impose a limit in deployment, but no such runtime protection was established here.

**Fix / acceptance:** Stream with a hard server-side byte cap, validate content independently of client MIME, reject malformed inputs and clean up partial files. Test wrong-content and over-limit uploads. Keep quota/rate limits appropriate to authenticated users.

### F22 — v1 routes are registered twice [Low]

**Location:** `tnt-backend-main/app/main.py:293,349`.

`app.include_router(api_v1_router)` appears twice unconditionally. The first matching route normally handles a request; this does not mean a handler runs twice. It does duplicate routing entries and can duplicate operation IDs/schema warnings, making the route table and generated client contract less reliable.

**Fix / acceptance:** Remove the duplicate include and assert unique method/path and operation-ID combinations after registration.

## 4. Validation results and limitations

| Check | Result | Meaning / limitation |
|---|---|---|
| Python parsing | All 463 Python files parsed; no syntax failures | Does not import dependencies or prove startup; three invalid-escape SyntaxWarnings observed |
| Frontend relative imports | One unresolved relative import found in user AppTabs | Text-based import resolution, not a full TS compiler or Metro build |
| API contract sweep | 442 literal client calls examined: Admin 183, user 125, vendor 134; 514 backend HTTP declarations indexed | Initial unmatched checkout/upload candidates were explained by router-specific prefixes; no blanket claim of missing routes from this check |
| Model/enum sweep | Confirmed missing fields/imports listed above | Alias/local-enum false positives were manually excluded |
| Alembic graph | 51 revisions; one head `20260729_0050`; no missing parent IDs | Graph check only; schema upgrades/downgrades were not executed |
| Isolated mock payment execution | SUCCESS for `amount=-1`; cancelled order became CONFIRMED | Actual function body, controlled fake ORM/session, no gateway |
| Group model checks | Five payment fields missing; PERCENTAGE missing | Checked supplied declarations; no live ORM session |
| Admin/vendor enum and field checks | Missing username, profile user_id, INACTIVE confirmed | Does not assert the rest of each query succeeds |
| Refund ETA execution | Past ETA marked refund completed without provider input | Actual progress body with controlled clock/payment object |
| Admin Cancel expression | Cancellation still proceeds | Executed exact JavaScript expression; no browser/API action |
| Existing backend test suite | 75 top-level `test_*.py` files found; not run | `python -m pytest --collect-only -q` failed: pytest is not installed; FastAPI and SQLAlchemy also unavailable |
| Frontend builds/typechecks | Not completed | No module has node_modules; compiler dependencies unavailable; attempted npm command was blocked by environment approval/network handling |
| Frontend test discovery | No `.test.` or `.spec.` filenames in the three source trees | Filename scan only, not proof that no differently named tests exist |
| Live infrastructure | Not tested | No configured database, Redis, payment gateway, SMS/FCM, device/emulator or deployed URL was exercised |

No dependency vulnerability audit, package-version availability check, load test, end-to-end payment settlement test, Android/iOS release build, browser UI run, or migration execution was completed. The report makes no claims that those checks passed. Dependency lockfiles are absent for the frontend applications and most backend requirements are unpinned, so reproducibility also needs attention before a release. No claim about a particular external package vulnerability is made.

The review does not manually certify every one of the roughly 174,000 source lines. It applies broad automated checks to the snapshot and deeper human-style tracing to high-risk paths. Database constraints, concurrency under load, native platform setup, notifications, backup/restore and the many ML features require further dependency-backed integration validation; absence of an item in the findings table is not an assurance that it is defect-free.

## 5. Repair order and release gates

### Immediate containment

1. Remove production access to mock checkout and unfinished group-payment endpoints. Replace the app's dependency on mock checkout with the real payment flow.
2. Rotate the vendor JWT secret and invalidate existing vendor tokens.
3. Enforce server-side second-factor authentication before granting admin tokens.
4. Restrict vendor registration, staff actions and group access using authenticated identity and current database state.
5. Restrict direct refunds by approved policy and lifecycle state; stop inferring settlement from time estimates.
6. Protect customer printing documents with authorization.

### Functional repairs

Repair group-payment persistence/contracts before enabling those endpoints. Fix recommendation auth/async/model mismatches, admin wastage, vendor forecasting, campaign state transitions and the finance cancellation path. Configure a real production user-app URL and repair included navigation imports. Bound and validate uploads; remove duplicate route registration.

### Required evidence before changing the verdict

- A clean dependency installation with reproducible versions, successful backend startup and successful frontend builds/typechecks.
- Real database migration upgrade from an empty database and from the currently deployed schema, with rollback/recovery rehearsed.
- Automated authorization tests for admin TOTP, demotion, vendor suspension, staff permissions/deactivation, cross-group requests and private downloads.
- Payment tests covering invalid signatures, wrong amounts, retries, duplicate callbacks, terminal order states, refund eligibility and reconciliation after partial failures. Every order confirmation must correspond to a verified charge or a properly debited wallet.
- Integration tests using real ORM-loaded group split rows across separate sessions; no invented mock-only payment fields.
- Physical-device user/vendor release smoke tests and browser-based Admin testing, including all defects recorded here.
- Existing backend regression suite executed and failures resolved; concurrency tests for stock, slot capacity, checkout and refund duplication.

**Final assessment:** The repository has extensive implemented functionality, but its security boundaries and financial state transitions are not dependable enough for production. Fix the Critical and High findings first, then demonstrate the release gates above. Do not treat the existing completion reports or syntax-only success as release approval.

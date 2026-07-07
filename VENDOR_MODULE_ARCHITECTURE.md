# Vendor Module Architecture Plan

## Executive Summary

This document analyzes the existing codebase and provides a comprehensive architecture plan for implementing a full-featured Vendor Module. Currently, vendors are implemented as `User` records with `role == VENDOR` — there is **no dedicated vendor table**, **no onboarding flow**, **no profile management**, **no working-hours configuration**, and **no payout/commission system**. All areas that will be touched are identified below.

---

## 1. Existing User Authentication System

| File | Role | What it does |
|------|------|--------------|
| `app/modules/auth/router.py` | Auth routes | OTP send/verify, auto-register new users |
| `app/modules/auth/otp_service.py` | OTP logic | Generate/store/verify OTP in Redis, SMS delivery |
| `app/modules/auth/schemas.py` | Auth schemas | `LoginRequest`, `VerifyOTPRequest` |
| `app/core/security.py` | JWT + guards | `create_access_token`, `get_current_user`, `require_role()` |
| `app/core/deps.py` | DB session | `get_db` dependency |
| `app/modules/users/model.py` | User model | `User` table — `role` enum includes `VENDOR` |

**Impact for Vendor Module:**
- `require_role("vendor")` already works as a dependency guard
- `get_current_user` returns `{id, phone, role, is_active}` — sufficient for vendor auth
- Vendor registration will use the existing OTP flow + role upgrade
- **No changes needed** to auth core

---

## 2. Existing Vendor-Related Tables & Code

### 2.1 Database Schema
```
users (id, phone, name, full_name, role, vendor_type, is_active, is_approved, …)
   ↑                                                                         
   └── vendors are User records with role=VENDOR, no dedicated vendor table   
                                                                             
vendor_profiles (queried via raw SQL in vendors/router.py) — used by vendors router
```

### 2.2 Existing Vendor Module (`app/modules/vendors/`)

| File | Lines | Purpose |
|------|-------|---------|
| `router.py` | ~280 | GET `/vendors/`, GET `/vendors/{id}`, GET `/vendors/{id}/menu`, GET `/vendors/{id}/slots` |
| `schemas.py` | ~55 | `VendorResponse`, `VendorMenuItemResponse`, `VendorSlotResponse`, `VendorSlotListResponse` |
| `model.py` | — | **DOES NOT EXIST** — vendors use `User` model |

### 2.3 Files Touching Vendors

| File | How it touches vendors |
|------|----------------------|
| `app/modules/users/model.py` | `User.role` enum includes `VENDOR` |
| `app/modules/users/schemas.py` | `vendor_type` field in `UserResponse` |
| `app/modules/admin/router.py` | `GET /admin/vendors`, `POST /admin/vendors/{id}/approve`, `POST /admin/vendors/{id}/reject`, `POST /admin/users/{id}/toggle` |
| `app/modules/admin/service.py` | User listing with role=VENDOR filter |
| `app/modules/orders/order_service.py` | `get_vendor_orders`, `get_vendor_analytics`, vendor auth checks |
| `app/modules/orders/service.py` | Vendor role check in `update_order_status` |
| `app/modules/orders/model.py` | `Order.vendor_id` FK → `users.id` |
| `app/modules/menu/model.py` | `MenuItem.vendor_id` FK → `users.id` |
| `app/modules/menu/router.py` | `require_role("vendor")` on menu CRUD, checks `vendor_type` |
| `app/modules/slots/model.py` | `Slot.vendor_id` FK → `users.id` |
| `app/modules/slots/service.py` | Slot generation per vendor |
| `app/modules/payments/service.py` | Payment links to order, order links to vendor |
| `app/modules/feedback/model.py` | `VendorReview` table with `vendor_id` |
| `app/modules/complaints/model.py` | `Complaint.vendor_id` |
| `app/modules/ai_intelligence/service.py` | `get_ai_recommendations`, vendor ranking, load analysis |
| `app/modules/ai_intelligence/analytics_service.py` | Vendor recommendations, popularity, load |
| `app/modules/ai_intelligence/planners/vendor_ranker.py` | Vendor ranking AI |
| `app/modules/ai_intelligence/planners/demand_planner.py` | Vendor demand planning |
| `app/modules/notifications/service.py` | Send notifications to vendor users |
| `app/modules/auditlog/service.py` | Audit actions: `VENDOR_APPROVED`, `VENDOR_REJECTED`, `VENDOR_SUSPENDED` |
| `app/modules/rewards/service.py` | `process_order_completion_rewards` triggers on order status |
| `app/modules/ledger/service.py` | Ledger entries for payments/refunds |
| `app/modules/stationery/service_model.py` | `StationeryService.vendor_id` FK → `users.id` |
| `app/modules/stationery/job_model.py` | `StationeryJob.vendor_id` FK → `users.id` |
| `app/modules/admin/export_service.py` | CSV export of vendors |
| `app/api/v1.py` | Includes vendors router |
| `app/main.py` | Includes vendors router at both `/v1/vendors` and `/vendors` |
| `app/database/init_db.py` | Imports all models (does NOT import a vendor model) |

### 2.4 Areas NOT currently touched

| Area | Status |
|------|--------|
| Vendor registration/onboarding | ❌ Missing |
| Vendor profile editing | ❌ Missing |
| Vendor working hours config | ❌ Missing |
| Vendor payout/commission | ❌ Missing |
| Vendor bank details | ❌ Missing |
| Vendor business documents | ❌ Missing |
| Vendor menu categories/tags | ❌ Missing |
| Vendor order history in-app | ✅ Basic (via `/orders/vendor`) |
| Vendor analytics dashboard | ✅ Basic (via `/orders/vendor/analytics`) |
| Vendor notification prefs | ❌ Missing |

---

## 3. Database Dependency Map

```
┌──────────────────────────────────────────────────────────────────┐
│                          NEW TABLES                               │
├──────────────────────────────────────────────────────────────────┤
│ vendor_profiles     ─── vendor_id → users.id (FK)                │
│   ├ category, description, rating, location, logo_url, cover_url │
│   ├ working_hours (JSON), time_slot_duration                     │
│   ├ prep_time_minutes, service_radius, delivery_available        │
│   └ fssai_license, gst_number, pan_number, bank_details (JSON)   │
│                                                                    │
│ vendor_documents    ─── vendor_id → users.id (FK)                │
│   ├ document_type (enum: FSSAI, GST, PAN, BANK, ID_PROOF)       │
│   ├ file_url, verification_status, verified_at, verified_by      │
│   └ uploaded_at                                                   │
│                                                                    │
│ vendor_payouts      ─── vendor_id → users.id (FK)                │
│   ├ amount, commission_pct, commission_amount, net_amount        │
│   ├ period_start, period_end, status (PENDING/PAID/FAILED)       │
│   ├ payment_ref, paid_at, bank_account_used                      │
│   └ notes                                                         │
│                                                                    │
│ vendor_schedules    ─── vendor_id → users.id (FK)                │
│   ├ day_of_week (1-7), is_off_day                                │
│   ├ open_time, close_time, break_start, break_end                │
│   └ max_orders_per_slot                                           │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                    EXISTING TABLES (touched)                      │
├──────────────────────────────────────────────────────────────────┤
│ users          ── Add: vendor_type specific fields & onboarded    │
│ menu_items     ── Add: category, tags, is_popular, is_signature  │
│ orders         ── Add: vendor_note                                │
│ slots          ── Already linked to vendor_id                     │
│ feedback       ── VendorReview already exists                     │
│ complaints     ── Already linked to vendor_id                     │
│ ledger         ── Already linked via order → vendor               │
│ reward_points  ── Vendors act as users already                    │
└──────────────────────────────────────────────────────────────────┘
```

### Column Changes Needed

**`users` table (add columns):**
```python
is_onboarded = Column(Boolean, default=False)  # has completed onboarding
onboarded_at = Column(DateTime, nullable=True)
gst_number = Column(String, nullable=True)
fssai_license = Column(String, nullable=True)
```

**`menu_items` table (add columns):**
```python
category = Column(String, nullable=True)        # eg "main_course", "snacks", "beverages"
tags = Column(JSON, default=list)                # eg ["spicy", "popular", "veg"]
is_signature = Column(Boolean, default=False)
prep_time_minutes = Column(Integer, default=10)
```

**`orders` table (add column):**
```python
vendor_note = Column(String, nullable=True)   # vendor's internal note
```

---

## 4. API Dependency Map

### 4.1 New Vendor Endpoints

```
VENDOR MODULE API MAP
=====================

GET    /vendors/                          ─ Existing (list by type)
GET    /vendors/{id}                      ─ Existing (single vendor)
GET    /vendors/{id}/menu                 ─ Existing
GET    /vendors/{id}/slots                ─ Existing

POST   /vendors/register                  ─ NEW: Vendor onboarding
PUT    /vendors/profile                   ─ NEW: Update vendor profile
GET    /vendors/profile                   ─ NEW: Get own profile

PUT    /vendors/working-hours             ─ NEW: Set working hours schedule
GET    /vendors/working-hours             ─ NEW: Get working hours

POST   /vendors/documents                 ─ NEW: Upload document
GET    /vendors/documents                 ─ NEW: List documents

GET    /vendors/analytics                 ─ NEW: Enhanced analytics (with revenue trends)
GET    /vendors/orders                    ─ EXISTING: /orders/vendor
GET    /vendors/orders/stats              ─ NEW: Order stats for today/week

GET    /vendors/payouts                   ─ NEW: Payout history
GET    /vendors/payouts/{id}              ─ NEW: Single payout detail

POST   /vendors/menu                      ─ EXISTING: /menu/ (add item)
PUT    /vendors/menu/{item_id}            ─ EXISTING: /menu/{item_id}
DELETE /vendors/menu/{item_id}            ─ NEW: Remove menu item

GET    /vendors/reviews                   ─ NEW: Vendor reviews
GET    /vendors/complaints                ─ NEW: Vendor complaints
```

### 4.2 New Admin Endpoints

```
POST   /admin/vendors/{id}/documents/verify  ─ NEW: Verify vendor document
POST   /admin/vendors/{id}/suspend           ─ NEW: Suspend vendor
POST   /admin/vendors/{id}/unsuspend         ─ NEW: Unsuspend vendor
GET    /admin/vendors/onboarding-pending     ─ NEW: Pending onboarding requests
POST   /admin/vendors/{id}/payout            ─ NEW: Initiate payout
GET    /admin/vendors/payouts                ─ NEW: All payout history
```

### 4.3 Affected Existing Endpoints

| Endpoint | Change Required | Reason |
|----------|----------------|--------|
| `POST /admin/vendors/{id}/approve` | Extend to also mark `is_onboarded` status | Approval should trigger document review check |
| `POST /admin/vendors/{id}/reject` | Add rejection reason field | Better vendor communication |
| `GET /admin/vendors` | Add onboarding status filter | Admin needs to see onboarded vs pending |
| `GET /admin/analytics` | Add vendor onboarding funnel metrics | Track vendor registration pipeline |
| `GET /orders/vendor/analytics` | Extend with trend data and comparisons | Vendors need week-over-week comparison |
| `GET /vendors/{id}/slots` | Add working-hours integration | Slots should respect vendor schedule |
| `POST /menu/` | Add category/tags validation | New menu item fields |

---

## 5. User ↔ Vendor Integration Map

```
USER SYSTEM                    VENDOR SYSTEM
═══════════                    ═════════════

┌─────────────────┐           ┌──────────────────────────────────┐
│  Auth Module     │           │  Vendor Module (NEW)             │
│  ─────────────   │           │  ──────────────────────          │
│  POST /send-otp  │──────────→│  Step 1: User logs in            │
│  POST /verify-otp│           │  (uses existing OTP flow)         │
│                  │           │  If new user → STUDENT by default │
│  User model      │           │                                  │
│  ────────────    │           │  Step 2: Upgrade to vendor        │
│  role = VENDOR   │←──────────│  POST /vendors/register           │
│  is_approved     │           │  Changes role to VENDOR           │
│  vendor_type     │           │  Creates vendor_profiles record   │
│  is_onboarded ▲  │           │  Creates initial vendor_schedules │
│               │  │           │                                  │
│               │  │           │  Step 3: Document upload          │
│               │  │           │  POST /vendors/documents           │
│               │  │           │  Adds documents, marks pending   │
│               │  │           │                                  │
│               │  │           │  Step 4: Admin approval            │
│               │  │           │  POST /admin/vendors/{id}/approve │
│               │  │           │  Sets is_approved=True            │
│               │  │           │  Sets is_onboarded=True  ▲─────────┘
│               │  │           │                                  │
│               ▼  │           │  Step 5: Vendor active            │
│  ┌─────────────┐  │           │  Can manage menu, see orders     │
│  │ JWT Payload │  │           │  Can access vendor endpoints     │
│  │ sub, role,  │──│──────────→│  require_role("vendor") gates    │
│  │ phone       │  │           │                                  │
│  └─────────────┘  │           │                                  │
└─────────────────┘              └──────────────────────────────────┘

INTEGRATION POINTS
==================

1. Order → Vendor:
   - Order.vendor_id references users.id
   - Vendor sees orders via /orders/vendor (existing)
   - Status transitions (confirm → preparing → ready) are vendor-only
   - QR pickup scanned by vendor user

2. Menu → Vendor:
   - MenuItem.vendor_id references users.id
   - Only vendor can CRUD own menu items
   - Menu items visible through /vendors/{id}/menu (public)

3. Slots → Vendor:
   - Slot.vendor_id references users.id
   - Slots generated per vendor schedule
   - Slot recommendations consider vendor load

4. Payment → Vendor:
   - Payment linked to Order → Order.vendor_id
   - Ledger tracks per-order transactions
   - Payouts aggregate from ledger (NEW)

5. Notifications → Vendor:
   - notify_user() called with vendor user_id
   - Vendor gets order notifications (new, cancel)
   - Notification types: ORDER_ACCEPTED, DELAY_ALERT, etc.

6. Reviews → Vendor:
   - VendorReview table references vendor_id
   - Visible on vendor detail page

7. Complaints → Vendor:
   - Complaint.vendor_id, assigned_to_vendor_id
   - Vendor can view and respond to complaints
```

---

## 6. Redis Integration Plan

### 6.1 Current Redis Usage

| Key Pattern | Purpose | TTL |
|-------------|---------|-----|
| `otp:{phone}` | OTP code storage | 300s |
| `otp:send_count:{phone}` | OTP rate limit | 600s |
| `otp:attempts:{phone}` | OTP brute force guard | 300s |
| `slot_lock:{slot_id}` | Distributed slot booking lock | 5s |
| `tnt:cart:user:{user_id}` | User shopping cart data | 12h |
| `tnt:notifications:queue` | Notification push queue | 24h |
| `idempotency:order:{phone}:{key}` | Idempotency guard | 3600s |
| `webhook:razorpay:{event}:{id}` | Webhook dedup | 3600s |

### 6.2 New Redis Keys for Vendor Module

| Key Pattern | Purpose | TTL | Priority |
|-------------|---------|-----|----------|
| `vendor:session:{vendor_id}` | Vendor dashboard session cache | 15min | High |
| `vendor:daily_stats:{vendor_id}:{date}` | Cached daily order/revenue stats | 10min | High |
| `vendor:weekly_stats:{vendor_id}:{week}` | Cached weekly stats | 1h | Medium |
| `vendor:load:{vendor_id}` | Real-time vendor load indicator | 30s | High |
| `vendor:active_orders:{vendor_id}` | Count of active (non-terminal) orders | 30s | High |
| `vendor:menu_cache:{vendor_id}` | Cached menu items for vendor | 5min | Medium |
| `vendor:today_revenue:{vendor_id}` | Running today's revenue cache | End of day | High |
| `idempotency:vendor:register:{phone}` | Vendor registration idempotency | 300s | Medium |
| `vendor:notification:prefs:{vendor_id}` | In-memory notification prefs | 1h | Low |
| `payout:lock:{vendor_id}:{period}` | Payout processing distributed lock | 30s | High |

### 6.3 Cache Invalidation Strategy

| Event | Keys to Invalidate |
|-------|-------------------|
| Order status changes for vendor | `vendor:daily_stats`, `vendor:active_orders`, `vendor:load` |
| Menu item created/updated/deleted | `vendor:menu_cache` |
| New payment for vendor order | `vendor:today_revenue`, `vendor:daily_stats` |
| Vendor profile updated | `vendor:session` |
| Working hours update | `vendor:load` (slots regenerated) |
| Payout processed | `payout:lock` |

### 6.4 Redis Data Flow Diagram

```
                    ┌───────────────┐
                    │   Redis       │
                    │   Cluster     │
                    └───────┬───────┘
                            │
          ┌─────────────────┼──────────────────┐
          │                 │                   │
          ▼                 ▼                   ▼
   ┌────────────┐   ┌──────────────┐   ┌──────────────┐
   │ Vendor     │   │ Cache Layer  │   │ Rate Limit   │
   │ Dashboard  │   │ (stats,menu) │   │ & Locking    │
   │ (live)     │   │ (TTL-based)  │   │ (slot_lock,  │
   │            │   │              │   │  idempo.)    │
   └────────────┘   └──────────────┘   └──────────────┘
```

---

## 7. Notification Integration Plan

### 7.1 Current Notification Types

```python
ORDER_ACCEPTED    → "Your order #{id} has been confirmed."          (student)
ORDER_PREPARING   → "Your order #{id} is being prepared."           (student)
ORDER_READY       → "Your order #{id} is ready for pickup!"         (student)
PICKUP_REMINDER   → "Reminder: order #{id} pickup slot starts..."   (student)
DELAY_ALERT       → "Your order #{id} is running about X min late." (student)
ORDER_CANCELLED   → "Your order #{id} has been cancelled."          (student)
ORDER_PLACED      → "Your order #{id} has been placed successfully."(student)
PROMO             → Admin broadcast                                 (all users)
SYSTEM            → Admin broadcast                                 (all users)
```

### 7.2 New Vendor Notification Types

```python
# Add to NotificationType enum in notifications/model.py
NEW_ORDER          = "new_order"           # New order placed at vendor
ORDER_CANCELLED    = "order_cancelled"     # Student cancelled order
PICKUP_CONFIRMED   = "pickup_confirmed"    # QR pickup completed
PAYOUT_ISSUED      = "payout_issued"       # Weekly payout processed
LOW_STOCK_ALERT    = "low_stock_alert"     # Menu item low (future)
REVIEW_RECEIVED    = "review_received"     # New review/rating
COMPLAINT_ASSIGNED = "complaint_assigned"  # Complaint forwarded to vendor
VENDOR_APPROVED    = "vendor_approved"     # Admin approved vendor
VENDOR_REJECTED    = "vendor_rejected"     # Admin rejected vendor
DOCUMENT_VERIFIED  = "document_verified"   # Document verified by admin
BONUS_AWARDED      = "bonus_awarded"       # Performance bonus
```

### 7.3 Notification Flow for Vendors

```
┌─────────────┐     ┌────────────────────┐     ┌─────────────────┐
│  Event      │     │  order_service.py   │     │  notifications/ │
│  Occurs     │────→│  (or vendor_service)│────→│  service.py     │
└─────────────┘     └────────────────────┘     │  notify_user()   │
                                                │                  │
                                                ├─────────────────┤
                                                │  1. DB Insert    │
                                                │  2. Push (sim.)  │
                                                │  3. Redis Queue  │
                                                │  4. SMS (opt.)   │
                                                └─────────────────┘
```

### 7.4 Where Notifications Are Sent (Trigger Map)

| Trigger | Current File | New Vendor Notification? | File to Modify |
|---------|-------------|------------------------|----------------|
| Order placed (student) | `order_service.py:place_order` | ✅ New order → vendor | `order_service.py` |
| Order cancelled (student) | `order_service.py:cancel_order` | ✅ Order cancelled → vendor | `order_service.py` |
| Order confirmed (vendor) | `order_service.py:confirm_order` | ✅ (existing student notify) | Already works |
| Order preparing (vendor) | `order_service.py:mark_order_preparing` | ✅ (existing student notify) | Already works |
| Order ready (vendor) | `order_service.py:mark_order_ready` | ✅ (existing student notify) | Already works |
| Payment successful | `payments/service.py:finalize_payment` | ✅ Payment received → vendor | `payments/service.py` |
| QR pickup confirmed | `order_service.py:confirm_qr_pickup` | ✅ Pickup → vendor | `order_service.py` |
| Vendor approved | `admin/router.py:approve_vendor` | ✅ In existing approve_vendor | Already has notify |
| Vendor rejected | `admin/router.py:reject_vendor` | ✅ In existing reject_vendor | Already has notify |

---

## 8. Implementation Plan — File Changes & New Files

### 8.1 Files to CREATE

```
app/modules/vendors/model.py              — VendorProfile, VendorDocument, VendorPayout, VendorSchedule
app/modules/vendors/profile_service.py    — Vendor profile CRUD logic
app/modules/vendors/registration_service.py — Vendor registration/onboarding flow
app/modules/vendors/document_service.py   — Document upload & verification logic
app/modules/vendors/payout_service.py     — Payout calculation & processing
app/modules/vendors/schedule_service.py   — Working hours management
app/modules/vendors/review_service.py     — Vendor review aggregation
app/modules/vendors/__init__.py           — Package init (update existing)
```

### 8.2 Files to MODIFY

| File | Changes |
|------|---------|
| `app/modules/vendors/router.py` | Add all new vendor endpoints; refactor into thin adapter delegating to service files |
| `app/modules/vendors/schemas.py` | Add VendorRegisterRequest, VendorProfileUpdate, VendorDocument, VendorPayout, VendorSchedule schemas |
| `app/modules/users/model.py` | Add `is_onboarded`, `onboarded_at`, `gst_number`, `fssai_license` columns to User model |
| `app/modules/users/schemas.py` | Add new fields to UserResponse |
| `app/modules/menu/model.py` | Add `category`, `tags`, `is_signature`, `prep_time_minutes` to MenuItem |
| `app/modules/menu/schemas.py` | Add new fields to MenuItemCreate, MenuItemResponse |
| `app/modules/menu/router.py` | Accept new fields in add/update menu item |
| `app/modules/menu/service.py` | Handle new fields |
| `app/modules/orders/model.py` | Add `vendor_note` column |
| `app/modules/orders/order_service.py` | Add vendor notifications for new order, cancel, pickup; enhance analytics |
| `app/modules/orders/router.py` | Minor: add vendor note support |
| `app/modules/notifications/model.py` | Add new `NotificationType` enum values |
| `app/modules/payments/service.py` | Add vendor notification on payment success |
| `app/modules/admin/router.py` | Add document verification, payout initiation, onboarding list endpoints |
| `app/modules/admin/service.py` | Add onboarding status filter support |
| `app/modules/admin/schemas.py` | Add document verification, payout schemas |
| `app/modules/ai_intelligence/analytics_service.py` | Use new vendor profile fields for ranking |
| `app/modules/slots/service.py` | Integrate vendor working hours in slot generation |
| `app/modules/slots/schemas.py` | Minor: add working-hours context |
| `app/modules/feedback/model.py` | (No changes needed, already has VendorReview) |
| `app/database/init_db.py` | Import new vendor models |
| `app/api/v1.py` | (No changes needed — vendors router already included) |
| `app/main.py` | (No changes needed — vendors router already included) |
| `app/core/redis.py` | (No changes needed) |

### 8.3 Database Migration (Alembic)

New migration file in `alembic/versions/`:
- Create `vendor_profiles` table
- Create `vendor_documents` table
- Create `vendor_payouts` table
- Create `vendor_schedules` table
- Add columns to `users` (is_onboarded, onboarded_at, gst_number, fssai_license)
- Add columns to `menu_items` (category, tags, is_signature, prep_time_minutes)
- Add column to `orders` (vendor_note)

### 8.4 Migration Execution Order

1. New tables first (vendor_profiles, vendor_documents, vendor_payouts, vendor_schedules)
2. User model columns (is_onboarded, onboarded_at)
3. MenuItem columns (category, tags, is_signature, prep_time_minutes)
4. Order column (vendor_note)
5. Seed default schedules for existing vendors
6. Migrate existing `vendor_profiles` raw table to ORM model

### 8.5 Test Files to Create/Modify

| File | Purpose |
|------|---------|
| `test_vendor_registration.py` | Test vendor onboarding flow |
| `test_vendor_profile.py` | Test profile CRUD |
| `test_vendor_documents.py` | Test document upload/verification |
| `test_vendor_payouts.py` | Test payout calculation/processing |
| `test_vendor_schedules.py` | Test working hours management |
| `test_vendors.py` (modify) | Update existing tests for new v2 endpoint |
| `test_vendor_ownership.py` (modify) | Extend ownership tests |

---

## 9. Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Raw SQL `vendor_profiles` table breaks | High | Medium | Add migration to convert to SQLAlchemy ORM; keep raw fallback during transition |
| Existing vendors have no profile data | Medium | High | Seed default profiles for all existing vendors in migration |
| Breaking changes to mobile API | High | Low | Keep existing `/vendors/{id}` response shape; extend with new fields as optional |
| Multiple DB sessions in one request | Medium | Low | Use existing `@transactional` decorator pattern consistently |
| Redis key naming collision | Low | Low | Follow existing `tnt:` prefix convention |
| Payout calculation errors | High | Low | Double-entry validation; manual admin override available |

---

## 10. Architecture Diagram — Full Vendor Module

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           VENDOR MODULE                                  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  API LAYER (router.py)                                           │   │
│  │  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ ┌──────────┐  │   │
│  │  │Vendor   │ │Profile   │ │Document  │ │Schedule│ │Payout    │  │   │
│  │  │Registration│Management│ │Management│ │Manager │ │Manager   │  │   │
│  │  └────┬────┘ └────┬─────┘ └────┬─────┘ └───┬────┘ └────┬─────┘  │   │
│  └───────┼───────────┼────────────┼────────────┼───────────┼────────┘   │
│          │           │            │            │           │            │
│  ┌───────┴───────────┴────────────┴────────────┴───────────┴────────┐   │
│  │  SERVICE LAYER (profile_service, registration_service, etc.)      │   │
│  │  ┌─────────────────────────────────────────────────────────┐     │   │
│  │  │  Business Logic, Validation, Orchestration               │     │   │
│  │  └─────────────────────────────────────────────────────────┘     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│  ┌─────────────────────────────────┼─────────────────────────────────┐   │
│  │  DATA LAYER (model.py)          │                                 │   │
│  │  ┌───────────┐ ┌──────────────┐ │ ┌──────────┐ ┌──────────────┐  │   │
│  │  │Vendor     │ │Vendor        │ │ │Vendor    │ │Vendor        │  │   │
│  │  │Profile    │ │Document      │ │ │Payout    │ │Schedule      │  │   │
│  │  └─────┬─────┘ └──────┬───────┘ │ └────┬─────┘ └──────┬───────┘  │   │
│  │        │              │         │      │              │          │   │
│  │        └──────┬───────┘         │      └──────┬───────┘          │   │
│  │               │                 │              │                 │   │
│  │         ┌─────▼─────────────────▼──────────────▼──────┐          │   │
│  │         │              users.id (FK)                  │          │   │
│  │         └─────────────────────────────────────────────┘          │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  INTEGRATIONS:                                                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐   │
│  │Orders    │ │Menu      │ │Slots     │ │Payments  │ │AI Engine   │   │
│  │Module    │ │Module    │ │Module    │ │Module    │ │Module      │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────────┘   │
│                                                                          │
│  INFRASTRUCTURE:                                                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                               │
│  │Redis     │ │PostgreSQL│ │RabbitMQ  │                               │
│  │(cache,   │ │(primary) │ │(future   │                               │
│  │ rate-lmt,│ │          │ │ eventbus)│                               │
│  │ session) │ │          │ │          │                               │
│  └──────────┘ └──────────┘ └──────────┘                               │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 11. Suggested Implementation Order

| Phase | Items | Estimated Effort |
|-------|-------|-----------------|
| **Phase 1: Data Layer** | Create models, migration, Alembic version | 1-2 days |
| **Phase 2: Registration & Profile** | Onboarding flow, profile CRUD, document upload | 2-3 days |
| **Phase 3: Schedule & Slots** | Working hours, slot integration | 1-2 days |
| **Phase 4: Order Integration** | Vendor notifications, enhanced analytics | 1-2 days |
| **Phase 5: Payouts & Commission** | Payout calculation, processing, history | 2-3 days |
| **Phase 6: Admin Extensions** | Document verification, payout admin, reports | 1-2 days |
| **Phase 7: Testing** | Unit tests, integration tests, migration tests | 2-3 days |
| **Total** | | **10-17 days** |

---

## 12. Key Design Decisions

1. **Dedicated vendor_profiles table** instead of columns on `users` — avoids bloating the User model while enabling rich profile data. User model keeps role, is_approved, is_onboarded as the vendor identity; everything else (description, location, business details, working hours) goes in the profile table.

2. **Vendor registration is a multi-step process** — Step 1: User logs in via OTP (existing flow). Step 2: POST `/vendors/register` upgrades role to VENDOR and creates profile. Step 3: Document upload. Step 4: Admin approval → `is_onboarded=True`.

3. **Payouts based on ledger** — Instead of tracking vendor balances, compute payouts from the ledger. A scheduled job aggregates CREDIT entries per vendor per period, deducts commission, and creates payout records.

4. **Backward compatibility** — All existing endpoints continue to work. New fields are added as optional in response schemas. The old `vendor_profiles` raw SQL table read is migrated to the new ORM model with a backward-compat fallback.

5. **Cache-always for dashboard** — Vendor dashboard stats (today's revenue, active orders, load) are cached in Redis with short TTLs (30s–10min) to handle high-frequency polling from the vendor mobile app.

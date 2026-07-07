# FastAPI Backend Production Review

**Date:** February 9, 2026  
**Reviewer:** Senior Backend Engineer  
**Project:** TNT Backend (Tap N Take)

---

## EXECUTIVE SUMMARY

**Production Readiness Score: 3/10**

This codebase has **CRITICAL ERRORS** that will prevent it from running in production. Multiple security vulnerabilities, broken business logic, and missing vendor isolation make this system unsafe for deployment without significant fixes.

---

## 🔴 CRITICAL ERRORS (Will Break System)

### 1. **Broken User Model** (`app/modules/users/model.py`)
**Lines:** 1-42  
**Issue:** Model definition is syntactically broken. `is_active` and `is_approved` are defined outside the class, duplicate imports, and `StationeryService` is incorrectly defined in the users model file.

**Impact:** Database migrations will fail, User model won't work.

**Fix Required:**
```python
# Move is_active and is_approved INSIDE User class
# Remove duplicate imports
# Remove StationeryService from this file (it's already in stationery/service_model.py)
```

---

### 2. **Missing Import: OrderItem Model** (`app/modules/orders/details_service.py`)
**Line:** 5  
**Issue:** Imports `from app.modules.orders.item_model import OrderItem` but the actual file is `app/modules/orders/model.py` where `OrderItem` is defined.

**Impact:** Runtime ImportError when accessing vendor order details.

**Fix:** Change to `from app.modules.orders.model import OrderItem`

---

### 3. **Missing StationeryJob Fields** (`app/modules/stationery/job_model.py`)
**Lines:** 14-27  
**Issue:** `StationeryJob` model missing `amount` and `is_paid` fields that are referenced in `stationery/payment_router.py` (lines 28, 70).

**Impact:** Runtime AttributeError when processing stationery payments.

**Fix:** Add:
```python
amount = Column(Integer, nullable=True)  # Calculated when ready
is_paid = Column(Boolean, default=False)
```

---

### 4. **Empty Config File** (`app/core/config.py`)
**Issue:** File is completely empty. No configuration management.

**Impact:** No centralized config, hardcoded values scattered, no environment variable management.

**Fix:** Implement proper config with pydantic-settings or similar.

---

### 5. **Broken Menu Router Authorization** (`app/modules/menu/router.py`)
**Line:** 21  
**Issue:** `require_role(user, "vendor")` is called as a function, but `require_role` is a dependency factory that returns a dependency.

**Impact:** Runtime TypeError. Authorization doesn't work.

**Fix:** Change to `user=Depends(require_role("vendor"))` in the route decorator.

---

### 6. **Orphaned Code in Stationery Payment** (`app/modules/stationery/payment_router.py`)
**Lines:** 76-84  
**Issue:** `add_ledger_entry()` call is outside any function, will execute on module import.

**Impact:** Runtime error on server startup.

**Fix:** Move inside `verify_job_payment()` function before `db.commit()`.

---

### 7. **Duplicate Admin Router** (`app/modules/admin/router.py`)
**Issue:** Entire router is duplicated (lines 1-75 and 75-149).

**Impact:** Duplicate route registrations, potential conflicts.

**Fix:** Remove duplicate code.

---

### 8. **Missing User Active Check**
**Issue:** `is_active` field exists but is never checked in authentication or authorization flows.

**Impact:** Blocked users can still access the system.

**Fix:** Add `is_active` check in `get_current_user()` or create middleware.

---

## 🟠 MAJOR ISSUES (Logic/Security Flaws)

### 9. **No Vendor Ownership Verification**
**Files:** `app/modules/orders/router.py` (lines 92-115, 119-142)  
**Issue:** Vendors can confirm/complete ANY order, not just their own. Missing `order.vendor_id == vendor.id` check.

**Impact:** Vendor A can manipulate Vendor B's orders. Critical security breach.

**Fix:**
```python
if order.vendor_id != vendor.id:
    raise HTTPException(status_code=403, detail="Not your order")
```

---

### 10. **Missing Vendor Type Separation**
**Issue:** `VendorType` enum exists but is never used. No enforcement that food vendors can't access stationery endpoints and vice versa.

**Impact:** Food vendors can create stationery services, breaking business logic.

**Fix:** Add `vendor_type` field to User model, check in stationery/menu routers.

---

### 11. **Payment Verification Missing Ownership Check** (`app/modules/payments/service.py`)
**Line:** 45-88  
**Issue:** `verify_payment()` doesn't verify the payment belongs to the requesting user.

**Impact:** User A can verify User B's payment by guessing payment_id.

**Fix:** Add user context check or require order ownership verification.

---

### 12. **Refund Missing Authorization** (`app/modules/payments/router.py`)
**Line:** 28-31  
**Issue:** `/payments/razorpay/refund/{payment_id}` endpoint has no authentication or authorization.

**Impact:** Anyone can refund any payment. Critical security vulnerability.

**Fix:** Add `Depends(get_current_user)` and verify ownership or admin role.

---

### 13. **Race Condition in Payment Verification**
**Files:** `app/modules/payments/service.py` (line 70), `app/modules/payments/webhook.py` (line 41)  
**Issue:** Both `verify_payment()` and webhook can mark payment as SUCCESS simultaneously. No idempotency check.

**Impact:** Double ledger entries, inconsistent state.

**Fix:** Add idempotency check: `if payment.status == PaymentStatus.SUCCESS: return`

---

### 14. **Webhook Missing Ledger Entries** (`app/modules/payments/webhook.py`)
**Lines:** 40-52  
**Issue:** Webhook updates payment/order status but doesn't create ledger entries like `verify_payment()` does.

**Impact:** Inconsistent ledger state depending on which path processes payment.

**Fix:** Add `add_ledger_entry()` calls in webhook handler.

---

### 15. **Missing Transaction Rollback**
**Issue:** No try/except blocks with `db.rollback()` anywhere. If any operation fails mid-transaction, partial commits occur.

**Impact:** Data corruption, inconsistent state.

**Fix:** Wrap critical operations in try/except with rollback.

---

### 16. **Order Creation Doesn't Check Slot Availability**
**File:** `app/modules/orders/service.py` (line 9-26)  
**Issue:** `create_order()` doesn't verify slot is available or not full before creating order.

**Impact:** Orders can be created for full slots.

**Fix:** Check `slot.status != SlotStatus.FULL` and `slot.current_orders < slot.max_orders`.

---

### 17. **Missing Order Amount Calculation**
**File:** `app/modules/orders/router.py` (line 40)  
**Issue:** `add_items_to_order()` returns total but it's not persisted on Order model. Payment uses hardcoded amount (line 11: `amount=5000`).

**Impact:** Payment amounts are wrong, no way to verify correct amount charged.

**Fix:** Add `total_amount` field to Order model, calculate and store it.

---

### 18. **Stationery Payment Missing Order Link**
**File:** `app/modules/stationery/payment_router.py`  
**Issue:** Stationery payments don't create Payment records or link to orders. Ledger entry has `order_id=None`.

**Impact:** No payment audit trail for stationery, ledger incomplete.

**Fix:** Create Payment records for stationery jobs or create separate payment model.

---

### 19. **Missing Idempotency Keys**
**Issue:** Payment initiation, order creation, refunds have no idempotency protection.

**Impact:** Duplicate payments, duplicate orders on retries.

**Fix:** Add idempotency keys (UUID) to critical operations, check Redis/DB before processing.

---

### 20. **Hardcoded Redis Connection** (`app/core/redis.py`)
**Issue:** Redis host/port hardcoded to localhost.

**Impact:** Won't work in production environments.

**Fix:** Use environment variables.

---

### 21. **SMS Not Implemented** (`app/core/sms.py`)
**Issue:** `send_sms()` just prints, doesn't actually send SMS.

**Impact:** OTP and notifications won't work.

**Fix:** Integrate real SMS provider (Twilio, MSG91, etc.).

---

### 22. **OTP Not Actually Sent**
**File:** `app/modules/auth/router.py` (line 24-31)  
**Issue:** `generate_otp()` creates OTP but never calls `send_sms()`.

**Impact:** Users never receive OTPs, authentication broken.

**Fix:** Call `send_sms()` after generating OTP.

---

### 23. **Missing Database Indexes**
**Issue:** No explicit indexes on foreign keys or frequently queried fields (e.g., `orders.user_id`, `orders.vendor_id`, `payments.order_id`).

**Impact:** Slow queries, poor performance at scale.

**Fix:** Add indexes in model definitions or migrations.

---

### 24. **Missing Input Validation**
**Issue:** Many endpoints accept raw strings/ints without Pydantic validation or length limits.

**Impact:** SQL injection risk (though SQLAlchemy helps), DoS via large inputs.

**Fix:** Use Pydantic models for all inputs, add length limits.

---

### 25. **Webhook Signature Verification Issue**
**File:** `app/modules/payments/webhook.py` (line 20)  
**Issue:** `verify_webhook_signature()` called with `body` (bytes) but then `await request.json()` reads body again, which will be empty.

**Impact:** Webhook signature verification fails or is bypassed.

**Fix:** Store body bytes before JSON parsing, or use `request.body()` correctly.

---

## 🟡 MINOR ISSUES (Cleanup/Refactor)

### 26. **Inconsistent Error Messages**
**Issue:** Some endpoints return generic 404s, others are more specific.

**Fix:** Standardize error response format.

---

### 27. **Missing Response Models**
**Issue:** Many endpoints don't specify `response_model`, making API documentation incomplete.

**Fix:** Add response models to all endpoints.

---

### 28. **Code Duplication**
**Issue:** User lookup by phone repeated in many places.

**Fix:** Create helper function `get_user_by_phone(db, phone)`.

---

### 29. **Missing Type Hints**
**Issue:** Some functions missing return type hints.

**Fix:** Add complete type hints.

---

### 30. **Inconsistent Naming**
**Issue:** Mix of snake_case and inconsistent naming (e.g., `UserRole.STUDENT` vs `UserRole.student` in schemas).

**Fix:** Standardize enum values.

---

### 31. **Missing API Versioning**
**Issue:** No version prefix (`/v1/`) in routes.

**Impact:** Hard to evolve API without breaking clients.

**Fix:** Add version prefix to all routers.

---

### 32. **Missing Request Logging**
**Issue:** No request/response logging for audit trail.

**Fix:** Add middleware for request logging.

---

### 33. **Missing Health Check Endpoint**
**Issue:** No `/health` or `/ready` endpoint for load balancers.

**Fix:** Add health check endpoint.

---

### 34. **Missing CORS Configuration**
**Issue:** No CORS middleware configured in `main.py`.

**Impact:** Frontend requests will be blocked.

**Fix:** Add CORS middleware.

---

### 35. **Missing Rate Limiting**
**Issue:** No rate limiting on authentication or payment endpoints.

**Impact:** Vulnerable to brute force and DoS attacks.

**Fix:** Add rate limiting middleware (slowapi or similar).

---

## 📋 SUGGESTED FIXES (Priority Order)

### Priority 1 (Must Fix Before Deployment):
1. Fix User model structure (`app/modules/users/model.py`)
2. Fix OrderItem import (`app/modules/orders/details_service.py`)
3. Add missing StationeryJob fields (`app/modules/stationery/job_model.py`)
4. Fix menu router authorization (`app/modules/menu/router.py`)
5. Remove orphaned code (`app/modules/stationery/payment_router.py`)
6. Remove duplicate admin router (`app/modules/admin/router.py`)
7. Add vendor ownership checks in order operations
8. Add authentication to refund endpoint
9. Fix webhook body handling
10. Add user active check in authentication

### Priority 2 (Critical Security):
11. Add vendor type separation and enforcement
12. Add payment ownership verification
13. Add idempotency keys
14. Fix race conditions in payment processing
15. Add transaction rollback handling
16. Implement real SMS sending
17. Send OTP via SMS

### Priority 3 (Data Integrity):
18. Add order amount calculation and storage
19. Link stationery payments to payment records
20. Add missing ledger entries in webhook
21. Add slot availability check in order creation
22. Add database indexes

### Priority 4 (Production Readiness):
23. Implement config management
24. Add CORS configuration
25. Add rate limiting
26. Add health check endpoint
27. Add request logging
28. Use environment variables for Redis
29. Add API versioning
30. Standardize error responses

---

## 🔒 SECURITY VULNERABILITIES SUMMARY

1. **Authorization Bypass:** Vendors can access/modify other vendors' orders
2. **Unauthenticated Refunds:** Anyone can refund any payment
3. **Missing Input Validation:** Risk of injection attacks
4. **No Rate Limiting:** Vulnerable to brute force
5. **Missing User Active Check:** Blocked users can still access system
6. **Webhook Signature Bypass:** Potential webhook manipulation
7. **Missing CORS:** Potential XSS/CSRF issues

---

## 📊 FINAL VERDICT

**Production Readiness Score: 3/10**

### Breakdown:
- **Functionality:** 2/10 (Critical runtime errors)
- **Security:** 1/10 (Multiple critical vulnerabilities)
- **Data Integrity:** 2/10 (Missing transactions, race conditions)
- **Scalability:** 3/10 (Missing indexes, blocking operations)
- **Maintainability:** 4/10 (Code duplication, inconsistent patterns)

### Recommendation:
**DO NOT DEPLOY** to production without fixing Priority 1 and Priority 2 issues. The system has fundamental flaws that will cause:
- Runtime crashes
- Security breaches
- Data corruption
- Financial losses (unauthorized refunds)

### Estimated Fix Time:
- Priority 1: 2-3 days
- Priority 2: 3-4 days
- Priority 3: 2-3 days
- Priority 4: 2-3 days
**Total: 9-13 days** of focused development + testing

---

## 📝 NOTES

- The codebase shows good structure and separation of concerns
- SQLAlchemy usage is generally correct
- Redis integration for OTP is well-designed
- However, critical gaps in security and error handling make it unsafe

---

**Review Completed:** February 9, 2026

---

## Addendum (2026-02-14)

### Signals API consolidation into AI module

- Signal endpoints are now canonical under AI:
    - `GET /ai/signals`
    - `GET /ai/signals/rush-hour`
    - `GET /ai/signals/slot-suggestions`
    - `GET /ai/signals/reorder-prompts`
- Legacy `GET /signals/*` routes are removed and expected to return `404`.
- Regression verification at addendum time:
    - Full test suite passed.
    - AI-focused compatibility tests passed for `/ai/signals*` behavior and legacy route removal.

Note: This addendum documents API-surface migration only and does not replace the original full production review scope from 2026-02-09.

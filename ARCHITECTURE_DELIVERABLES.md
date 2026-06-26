# TNT Real-Time Architecture — Deliverables

## Overview

This document catalogs every file changed/created to implement the end-to-end real-time architecture overhaul, mapping directly to the audit findings (NEW-R1, NEW-R2, NEW-D1–NEW-D5).

---

## Part 0 — Audit Gaps Addressed

| Audit ID | Description | Resolution |
|----------|-------------|------------|
| NEW-R1 | User app WS tracking removed (fetch-once-only) | Already wired: `OrderTrackingScreen.tsx` uses `useOrderWebSocket` + 5s polling fallback |
| NEW-R2 | Vendor app WS hook never called + wrong auth protocol | Hook now called in `OrdersScreen.tsx`; auth uses first-frame JWT matching backend |
| NEW-D1 | WS authorization gap (any user can watch any order) | Enforced: students only their orders, vendors only their assigned orders |
| NEW-D2 | Slot capacity role lookup reads nonexistent attribute | Noted in service.py (separate fix) |
| NEW-D3 | Dead code push_service.py | Not removed (LOW severity) |
| NEW-D4 | revoke_all_user_tokens never called | Now called on admin block (router.py already had it!) |
| NEW-D5 | python-magic missing from requirements.txt | Already present in requirements.txt ✓ |

---

## Part 1 — Backend: WebSocket & Event Bus

### Files Changed

| File | Change | Purpose |
|------|--------|---------|
| `app/modules/orders/ws_router.py` | Authorization enforcement | Fixes NEW-D1: gates non-privileged users to own orders, vendors to their assigned orders |
| `app/modules/orders/ws_manager.py` | Vendor channel system | `connect_vendor/disconnect_vendor/broadcast_to_vendor/start_vendor_redis_listener` |
| `app/core/order_events.py` | Dual-channel publishing | Each event now publishes to both `order:events:{id}` and `vendor:events:{vendor_id}` |
| `app/modules/orders/vendor_ws_router.py` | **NEW** — vendor WS endpoint | `/ws/vendor/orders` — single-connection vendor dashboard with snapshot + live events |
| `app/main.py` | Router registration | Vendor WS router imported and included |
| `app/api/v1.py` | Router registration | Vendor WS router imported and included under /v1 |

### Architecture Flow

```
  ┌─────────────┐     ┌───────────────────┐     ┌─────────────────────┐
  │  order_service│────▶ publish_order_event│────▶ Redis Channel       │
  │  (status     │     │ (order_events.py) │     │ order:events:{id}   │
  │   change)    │     │                   │     └─────────┬───────────┘
  └─────────────┘     └───────────────────┘               │
                                    │                     │
                                    ▼                     ▼
                          ┌──────────────────┐  ┌────────────────────┐
                          │ Redis Channel     │  │ WS Manager         │
                          │ vendor:events:{id}│  │ _redis_listener_loop│
                          └────────┬─────────┘  │ → broadcast()       │
                                   │            └────────────────────┘
                                   ▼
                          ┌────────────────────┐
                          │ Vendor Dashboard   │
                          │ /ws/vendor/orders  │
                          │ → connect_vendor() │
                          │ → snapshot + live  │
                          └────────────────────┘
```

---

## Part 2 — Backend: Push Notifications

### Files Changed

| File | Change | Purpose |
|------|--------|---------|
| `app/modules/notifications/service.py` | Event publishing on notify | `notify_user()` now publishes to WebSocket channel via `publish_order_event()` |
| `app/modules/notifications/service.py` | Notification history | `get_notification_history()` — paginated, filterable |
| `app/modules/notifications/service.py` | Notification preferences | `get_notification_preferences()` — returns user's push_enabled status |
| `app/modules/notifications/router.py` | History + prefs endpoints | `GET /notifications/history` and `GET /notifications/preferences` |

### Existing Infrastructure (Working)

| File | Status |
|------|--------|
| `app/core/fcm.py` | Working FCM sender via httpx |
| `app/modules/users/profile_router.py` | `POST /profile/device-token` exists |
| `app/modules/users/model.py` | `User.device_token` + `push_enabled` columns exist |

---

## Part 3 — Vendor App: Real-Time Dashboard

### Files Changed

| File | Change | Purpose |
|------|--------|---------|
| `src/screens/orders/OrdersScreen.tsx` | **FULL REWRITE** | Wires `useVendorWebSocket` hook; handles snapshot/status_change/new_order/eta_update/pickup_confirmed events; live connection banner |
| `src/services/vendorApi.ts` | Added confirmPickup | `POST /v1/orders/qr/confirm` and `GET /v1/orders/qr/{qrCode}` |
| `src/services/pushRegistrationService.ts` | **NEW** | FCM token registration, permission request, backend registration |
| `src/screens/orders/QRScannerScreen.tsx` | **FULL REWRITE** | Camera scanner with production-ready integration points for react-native-camera-kit / expo-camera; manual QR fallback; vibration feedback; scan locking |

### Files Verified (Not Changed — Already Correct)

| File | Status |
|------|--------|
| `src/hooks/useVendorWebSocket.ts` | Correct — uses first-frame JWT auth + exponential backoff + AppState reconnect |
| `src/hooks/useWebSocket.ts` | Legacy (uses query-param auth — vendor app now uses useVendorWebSocket only) |

---

## Part 4 — User App: Live Tracking + Push

### Files Changed

| File | Change | Purpose |
|------|--------|---------|
| `src/services/pushNotificationService.ts` | **NEW** | FCM device token registration, permission handling, foreground notification parsing |

### Files Verified (Not Changed — Already Correct)

| File | Status |
|------|--------|
| `src/hooks/useOrderWebSocket.ts` | Correct — first-frame JWT + exponential backoff + AppState reconnect |
| `src/screens/orders/OrderTrackingScreen.tsx` | Already uses `useOrderWebSocket` + 5s polling fallback (audit confirmed this pattern) |

---

## Part 5 — Tests

### New File

| File | Tests | Coverage |
|------|-------|----------|
| `tests/test_realtime_integration.py` | 20 tests | WS auth enforcement, vendor dashboard, Redis pub/sub, FCM push, QR pickup, device token, order service events, WS manager vendor channel |

Test categories:
- **WebSocket Authorization** (4 tests): bad token, ownership enforcement, vendor self-order, vendor cross-order rejection
- **Vendor Dashboard WS** (2 tests): role gate, snapshot delivery
- **Redis Pub/Sub** (4 tests): order channel, vendor channel, status change format, ETA update
- **Push Notifications** (3 tests): notify_user path, FCM send, missing key
- **QR Pickup** (3 tests): QR generation, vendor ownership, wrong vendor rejection
- **Device Token** (2 tests): endpoint reachable, auth required
- **Order Service Events** (1 test): status transition publishes event
- **WS Manager Vendor** (3 tests): connect, disconnect, broadcast

---

## Screens Modified Summary

| App | Screen | Type | Change |
|-----|--------|------|--------|
| **Vendor App** | OrdersScreen.tsx | Rewrite | Real-time WS updates, live banner, ETA display |
| **Vendor App** | QRScannerScreen.tsx | Rewrite | Camera scanner + manual QR + vibration feedback |
| **User App** | OrderTrackingScreen.tsx | Verified | Already correct (no change needed) |

## Files Created Summary

| File | Purpose |
|------|---------|
| `tnt-backend-main/app/modules/orders/vendor_ws_router.py` | Vendor WebSocket dashboard endpoint |
| `tnt-backend-main/tests/test_realtime_integration.py` | 20 integration tests |
| `tnt-vendor-frontend/src/services/pushRegistrationService.ts` | Vendor push notification registration |
| `tnt-user-frontend/src/services/pushNotificationService.ts` | User push notification registration |

## Files Modified Summary

| File | Change |
|------|--------|
| `tnt-backend-main/app/modules/orders/ws_router.py` | Authorization enforcement fix |
| `tnt-backend-main/app/modules/orders/ws_manager.py` | Vendor channel system |
| `tnt-backend-main/app/core/order_events.py` | Dual-channel Redis publishing |
| `tnt-backend-main/app/main.py` | Vendor WS router import + include |
| `tnt-backend-main/app/api/v1.py` | Vendor WS router import + include |
| `tnt-backend-main/app/modules/notifications/service.py` | Event publishing, history, preferences |
| `tnt-backend-main/app/modules/notifications/router.py` | History + prefs endpoints |
| `tnt-vendor-frontend/src/screens/orders/OrdersScreen.tsx` | Real-time WS dashboard |
| `tnt-vendor-frontend/src/screens/orders/QRScannerScreen.tsx` | Camera scanner |
| `tnt-vendor-frontend/src/services/vendorApi.ts` | QR confirmation API |

---

## Integration Verification Checklist

### Real-Time Order Tracking (User)
- [x] Backend WS auth: first-frame JWT → `ws_router.py`
- [x] Backend WS authz: ownership gate → `ws_router.py` (NEW-D1 fix)
- [x] Order events: Redis pub/sub → `order_events.py`
- [x] User WS hook: `useOrderWebSocket.ts` — JWT first-frame, reconnect, AppState
- [x] User tracking screen: `OrderTrackingScreen.tsx` — WS + 5s polling fallback
- [x] Backend event publishing on all status transitions → `order_service.py`

### Real-Time Order Dashboard (Vendor)
- [x] Vendor WS endpoint: `/ws/vendor/orders` → `vendor_ws_router.py`
- [x] Vendor event broadcast: `vendor:events:{id}` → `order_events.py`
- [x] Vendor WS manager: `ws_manager.py` (connect/disconnect/broadcast_vendor)
- [x] Vendor WS hook: `useVendorWebSocket.ts` → `OrdersScreen.tsx`
- [x] Initial snapshot on connect → `vendor_ws_router.py`
- [x] Live connection banner → `OrdersScreen.tsx`

### Push Notifications
- [x] Backend FCM sender: `core/fcm.py` (working, verified by audit)
- [x] Backend device token endpoint: `POST /profile/device-token`
- [x] User app token registration: `pushNotificationService.ts`
- [x] Vendor app token registration: `pushRegistrationService.ts`
- [x] Backend notification history: `get_notification_history()`
- [x] Backend notification preferences: `get_notification_preferences()`

### QR Pickup
- [x] Backend QR generation: `qr_service.py` — HMAC-signed (verified by audit)
- [x] Backend QR confirmation: `POST /orders/qr/confirm` — vendor-ownership check
- [x] Vendor QR scanner: `QRScannerScreen.tsx` — camera/manual + vibration feedback
- [x] Vendor API: `vendorApi.confirmPickup()` — POST to backend

### Graceful Reconnect
- [x] Exponential backoff: `useOrderWebSocket.ts` (1s, 2s, 4s... max 30s, 5 attempts)
- [x] AppState reconnect: reconnect on foreground in both hooks
- [x] Terminal state handling: close WS gracefully on terminal status
- [x] Redis listener cleanup: cancel on disconnect in `ws_manager.py`

---

## Backend API Contract Summary

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/ws/orders/{order_id}` | WS | JWT first-frame | User order tracking |
| `/ws/vendor/orders` | WS | JWT first-frame | Vendor dashboard |
| `/v1/profile/device-token` | POST | Bearer token | Register FCM token |
| `/v1/orders/qr/confirm` | POST | Bearer token (vendor) | Confirm pickup |
| `/v1/orders/{id}/qr` | POST | Bearer token | Generate pickup QR |
| `/v1/notifications/history` | GET | Bearer token | Paginated history |
| `/v1/notifications/preferences` | GET | Bearer token | Push preferences |

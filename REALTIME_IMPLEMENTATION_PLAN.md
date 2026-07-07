# TNT Real-Time Architecture Implementation Plan

Based on audit findings, here is every gap and the fix:

## Part 1 — Backend WebSocket & Event Bus

| File | Gap | Fix |
|------|-----|-----|
| `ws_router.py` | `is_privileged` computed but never enforced | Add ownership gate after auth |
| `ws_manager.py` | No vendor-wide channel | Add `VendorWSManager` for multi-order vendor dashboard |
| `order_events.py` | No vendor-wide broadcast | Add `publish_to_vendor_channel()` |
| `order_service.py` | Not all transitions publish events | Ensure every status transition publishes |
| `service.py` | Already publishes events | No change needed |

## Part 2 — Push Notifications (Backend)

| File | Gap | Fix |
|------|-----|-----|
| `fcm.py` | Already works | No change needed |
| `notifications/service.py` | No notification history | Add history logging |
| `profile_router.py` | `/device-token` endpoint exists | No change needed |

## Part 3 — User App

| File | Gap | Fix |
|------|-----|-----|
| `useOrderWebSocket.ts` | Already correct (first-frame JWT) | No change needed |
| `OrderTrackingScreen.tsx` | Already uses hook + polling fallback | Add background sync on app foreground |
| Firebase SDK | Not in project | Add `@react-native-firebase/app` + `@react-native-firebase/messaging` |
| Device token registration | Not called anywhere | Register on app start + login |
| `App.tsx` | No notification handler | Add permission + foreground handler |

## Part 4 — Vendor App

| File | Gap | Fix |
|------|-----|-----|
| `useVendorWebSocket.ts` | Already correct (first-frame JWT) | No change needed |
| `OrdersScreen.tsx` | Never uses the WS hook | Wire `useVendorWebSocket` into dashboard |
| `useWebSocket.ts` | Query-param auth (wrong protocol) | Keep as legacy wrapper; vendor app uses `useVendorWebSocket.ts` |
| `QRScannerScreen.tsx` | No camera, manual input only | Add real camera with `react-native-camera-kit` |
| Firebase SDK | Not in project | Add same as user app |
| `vendorApi.ts` | No confirmPickup for QR | Already has it |

## Part 5 — Backend Security Fix

| File | Gap | Fix |
|------|-----|-----|
| `ws_router.py` | NEW-D1: WS authorization gap | Gate non-privileged users to own orders only |

## Implementation Order

1. Backend: Fix WS authorization (NEW-D1)
2. Backend: Add vendor-wide WS channel
3. Backend: Ensure all order transitions publish events
4. User App: Wire existing `useOrderWebSocket` (already done)
5. Vendor App: Wire `useVendorWebSocket` into `OrdersScreen.tsx`
6. Vendor App: Rewrite `QRScannerScreen.tsx` with camera
7. Both Apps: Add Firebase push notifications + device token registration
8. Backend: Add notification history + preferences
9. Tests

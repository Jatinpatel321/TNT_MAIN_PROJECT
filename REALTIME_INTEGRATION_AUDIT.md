# TNT — Realtime / WebSocket Integration Audit (Phase 5)

**Date:** 2026-07-07
**Method:** Mapped every backend WebSocket endpoint + emitted event against every frontend WS client (connection URL, auth frame, and event-name handling) across the 3 apps. Verified route registration functionally via Starlette `TestClient.websocket_connect`.

> Verified facts only. All 5 frontend-targeted WS routes confirmed **registered and accepting connections**; bogus paths are rejected (negative control passed).

---

## WS endpoint ↔ client map

| Backend endpoint | Registered | Frontend client | Auth frame | Event key |
|---|---|---|---|---|
| `/v1/ws/orders/{id}` | ✅ (v1 + legacy) | user `useOrderWebSocket`, admin `useOrderWebSocket` | `{"token"}` | `event` |
| `/v1/ws/vendor/orders` | ✅ | vendor `useVendorWebSocket` | `{"token"}` | `event`/`type` |
| `/v1/ws/groups/{id}` | ✅ (v1 + legacy) | user `useGroupCartWebSocket` | `{"token"}` | `event` |
| `/v1/admin/security/ws` | ✅ | admin `SecurityDashboard` | `{"token"}` | — |
| `/ws/notifications` | ❌ **unregistered** | *(no frontend consumer)* | — | — |

Backend order events (`order_events.py`): `status_change`, `order_updated`, `eta_update`, `pickup_confirmed`, plus WS-level `status` (snapshot), `new_order`, `snapshot`, `terminal`. Group events (`group_events.py`): `group_updated`, `payment_recorded`, `group_picked_up`, and now `order_placed`.

---

## 🔴 Critical bug found + fixed — admin order tracking WS was 100% broken

`tnt-admin/src/hooks/useOrderWebSocket.ts` (powers OrderDetail "Live tracking"):

1. **Auth frame mismatch** — sent the bare token: `ws.send(token)`. The backend does `json.loads(firstFrame)["token"]`, so `json.loads("eyJ…")` threw → server replied `Invalid auth frame` and closed `4001`. **The socket never authenticated.**
2. **Message-shape mismatch** — parsed flat `{status, eta_minutes}`, but the backend sends an envelope `{event, data:{…}}` where status is nested (`data.new_status` for `status_change`, `data.status` for snapshot/`order_updated`). Even post-auth, status was always `undefined`.

**Fix:** send `JSON.stringify({ token })`; parse the envelope by `event` type and read status/eta from `data`; ignore `authenticated`/`error`/`ping`/`pong` control frames. Now matches the user app's working hook and the backend protocol.

---

## 🟡 Gap closed — group `order_placed` event never emitted

`GroupCartService._notify_group` defaults to `event="group_updated"` and no caller overrode it, so **`order_placed` was never published**, even though `GroupDetailScreen` handles it to immediately refresh per-member payment status. Previously self-healed only via the 8-second fallback poll.

**Fix:** group order placement now emits `event="order_placed"` → members' payment status refreshes in realtime.

---

## 🟡 Consistency — user WS hooks migrated to `/v1`

User app connected to legacy root `/ws/orders/{id}` and `/ws/groups/{id}` (worked via the deprecated legacy mounts) while vendor/admin already used `/v1/ws/*`. Migrated both user hooks to `/v1/ws/*` so realtime survives the v2 legacy removal.

---

## ℹ️ Informational

`notifications/websocket_router.py` (`/ws/notifications`) is **unregistered** and has **no frontend consumer** — a dormant orphan, not a break. Left as-is (registering it would add unused surface). Recommend removing or wiring only if a client is built.

---

## Verified consistent (no change needed)

- **User order tracking** — hook forwards `{event, data}`; screen switches on `event` (`status_change`/`eta_update`/`pickup_confirmed`/`status`) — all match backend. ✅
- **Vendor dashboard** — hook robust to `event`/`type`; screen handles `new_order`/`order_updated`/`snapshot`; `new_order` is published on order + group-order creation; status changes arrive via `order_updated`. ✅
- **Group cart** — hook forwards `event`; `payment_recorded` matches; screen `reload()`s on any event. ✅
- **Auth pattern** — all clients send `{"token"}` first frame (after the admin fix); all backend WS handlers authenticate on first frame with 10s timeout. ✅

---

## Files modified

| File | Change |
|---|---|
| `tnt-admin/src/hooks/useOrderWebSocket.ts` | Fixed auth frame + envelope parsing (critical) |
| `tnt-backend-main/app/modules/group_cart/service.py` | Emit `order_placed` on group order placement |
| `tnt-user-frontend/src/hooks/useOrderWebSocket.ts` | `/ws/orders/*` → `/v1/ws/orders/*` |
| `tnt-user-frontend/src/hooks/useGroupCartWebSocket.ts` | `/ws/groups/*` → `/v1/ws/groups/*` |

**Regression check:** backend boots clean; all 5 target WS routes connect via `TestClient.websocket_connect`; `test_websocket_orders`, `test_group_cart`, `test_group_cart_integration`, `test_group_payment_splits` → **34 passed, 2 skipped**.

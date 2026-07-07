# Vendor Frontend Module — Comprehensive Audit Report

**Generated**: July 4, 2026  
**Scope**: Database connections, module structure, gaps analysis, API mapping  
**Modules compared**: User Frontend (`tnt-user-frontend/`), Admin Frontend (`tnt-admin/`), Vendor Frontend (`tnt-vendor-frontend/`)

---

## 1. Architecture Overview

### 1.1 Frontend Stack
| Component | Technology |
|-----------|-----------|
| Framework | React Native 0.73.6 (Expo) |
| Navigation | React Navigation 6 (bottom tabs + native stack) |
| HTTP Client | Axios (custom interceptor for JWT) |
| Auth Storage | Expo SecureStore (encrypted) |
| State | React Context (Auth, Theme, Permissions) |
| Design System | Custom tokens + 15 reusable components |
| WebSocket | Custom hooks (vendor-wide + per-order) |
| Charts | react-native-chart-kit |

### 1.2 Backend Stack (connected)
| Component | Technology |
|-----------|-----------|
| API Framework | FastAPI (Python) |
| Database | PostgreSQL via SQLAlchemy + pg8000 |
| Auth | JWT (vendor-specific auth separate from user auth) |
| Cache | Redis (refresh token JTI storage) |
| ORM | SQLAlchemy declarative models |

### 1.3 API Base URL
- **Dev**: `http://localhost:8000` (with ADB reverse for devices)
- **Production**: `https://api.tnt-campus.com`
- **Version prefix**: `/v1`

---

## 2. Database Connection Map

Every screen in the vendor frontend ultimately queries database tables through backend API routes. The mapping below traces the full path: **Screen → Service → API Route → Controller → Database Table**.

### 2.1 Authentication & Profile

| Screen | Service | API Route(s) | DB Tables | CRUD |
|--------|---------|-------------|-----------|------|
| `LoginScreen` | raw axios | `POST /v1/vendors/auth/login` | `vendors`, `vendor_staff` | R |
| `ProfileScreen` | AuthContext | *(reads cached JWT/secure store)* | — | — |
| `BusinessHoursScreen` | `businessSettingsApi` | `GET/PUT /v1/vendors/profile/` | `vendor_profiles` | R, U |
| `HolidaySettingsScreen` | `businessSettingsApi` | `GET/PUT /v1/vendors/profile/` | `vendor_profiles` | R, U |

### 2.2 Staff Management

| Screen | Service | API Route(s) | DB Tables | CRUD |
|--------|---------|-------------|-----------|------|
| `StaffListScreen` | `staffApi` | `GET /v1/vendors/auth/staff` | `vendor_staff` | R |
| `AddStaffScreen` | `staffApi` | `POST /v1/vendors/auth/staff` | `vendor_staff` | C |
| `EditStaffScreen` | `staffApi` | `PUT /v1/vendors/auth/staff/{id}` | `vendor_staff` | U |
| `StaffPermissionsScreen` | `staffApi` | `PUT /v1/vendors/auth/staff/{id}` | `vendor_staff` | U |

### 2.3 Orders

| Screen | Service | API Route(s) | DB Tables | CRUD |
|--------|---------|-------------|-----------|------|
| `OrdersScreen` | `vendorApi` | `GET /v1/vendors/orders` | `orders`, `order_items` | R |
| | `vendorApi` | `PUT /v1/vendors/orders/{id}/accept\|prepare\|ready\|complete` | `orders` (status update) | U |
| | WebSocket | `ws:///ws/vendor/orders` | — (real-time stream) | — |
| `QRScannerScreen` | `vendorApi` | `GET /v1/orders/qr/{code}` | `orders` | R |
| `QRScanScreen` | `vendorApi` | `POST /v1/orders/qr/pickup/confirm` | `orders` (status update) | U |

### 2.4 Menu

| Screen | Service | API Route(s) | DB Tables | CRUD |
|--------|---------|-------------|-----------|------|
| `MenuScreen` | raw `apiClient` | `GET /v1/menu/items?vendor_id=X` | `menu_items` | R |
| | raw `apiClient` | `GET /v1/vendors/inventory/dashboard` | `inventory_items` | R |
| | raw `apiClient` | `PUT /v1/menu/items/{id}/toggle` | `menu_items` | U |
| | raw `apiClient` | `DELETE /v1/menu/items/{id}` | `menu_items` | D |
| | raw `apiClient` | `POST /v1/menu/inventory/{id}/restock` | `inventory_items` | U |
| `AddEditMenuItemScreen` | raw `apiClient` | `POST/PUT /v1/menu/items` | `menu_items` | C, U |
| `StationeryServicesScreen` | raw `apiClient` | `GET/POST/PUT/DELETE /v1/menu/stationery` | `stationery_services` | CRUD |
| `MenuBulkImportScreen` | raw `apiClient` | `POST /v1/menu/items` (loop) | `menu_items` | C |

### 2.5 Inventory

| Screen | Service | API Route(s) | DB Tables | CRUD |
|--------|---------|-------------|-----------|------|
| `AIInventoryPlanningDashboard` | `vendorApi` | `GET /v1/vendors/inventory/ai/plan` | `inventory_items`, `menu_items`, ML | R |
| | | `GET /v1/vendors/inventory/ai/items-finishing` | | R |
| | | `GET /v1/vendors/inventory/ai/items-restock` | | R |
| | | `GET /v1/vendors/inventory/ai/demand` | | R |
| | | `GET /v1/vendors/inventory/ai/wastage` | | R |
| | | `GET /v1/vendors/inventory/ai/restock-suggestions` | | R |
| | | `GET /v1/vendors/inventory/ai/waste-suggestions` | | R |
| | | `GET /v1/vendors/inventory/ai/purchase-plan` | | R |

### 2.6 Slots

| Screen | Service | API Route(s) | DB Tables | CRUD |
|--------|---------|-------------|-----------|------|
| `SlotDashboardScreen` | `slotApi` | `GET /v1/slots/` | `slots` | R |
| | | `POST /v1/slots/{id}/lock\|unlock` | `slots` | U |
| | | `GET /v1/slots/analytics` | `slots`, `orders` | R |
| `SlotConfigurationScreen` | `slotApi` | `POST/PUT/DELETE /v1/slots/` | `slots` | C, U, D |
| | | `POST /v1/slots/bulk-create` | `slots` | C |
| `CapacitySettingsScreen` | `slotApi` | `GET/POST/PUT/DELETE /v1/slots/capacity-rules` | `capacity_rules` | CRUD |
| `PeakHourSettingsScreen` | `slotApi` | `GET/POST/PUT/DELETE /v1/slots/rules` | `slot_rules` | CRUD |
| `FacultyPrioritySettingsScreen` | `slotApi` | `GET/POST/PUT/DELETE /v1/slots/rules` | `slot_rules` | CRUD |

### 2.7 Analytics

| Screen | Service | API Route(s) | DB Tables | CRUD |
|--------|---------|-------------|-----------|------|
| `AnalyticsDashboard` | `analyticsApi` | `GET /v1/vendors/analytics/dashboard` | `orders`, `order_items` | R |
| | `analyticsApi` | `GET /v1/vendors/analytics/daily?days=X` | | R |
| | `analyticsApi` | `GET /v1/vendors/analytics/weekly` | | R |
| | `analyticsApi` | `GET /v1/vendors/analytics/monthly` | | R |
| | `analyticsApi` | `GET /v1/vendors/analytics/peak-hours` | | R |
| | `analyticsApi` | `GET /v1/vendors/analytics/items` | | R |
| | `analyticsApi` | `GET /v1/vendors/analytics/waste` | | R |
| | `vendorApi` | `GET /v1/vendor/forecast/by-type` | | R |
| `PerformanceIntelligenceDashboard` | `vendorApi` | `GET /v1/vendor/performance/metrics` | `vendor_performance` | R |
| | | `GET /v1/vendor/performance/score` | | R |
| | | `GET /v1/vendor/performance/history` | | R |
| | | `GET /v1/vendor/performance/insights/dashboard` | | R |
| `EnhancedForecastDashboard` | `vendorApi` | `GET /v1/vendor/forecast/comprehensive` | ML + `orders` history | R |
| `SmartDemandDashboard` | `vendorApi` | `GET /v1/vendors/demand-dashboard/` | `orders`, `inventory`, ML | R |

### 2.8 AI / ML

| Screen | Service | API Route(s) | DB Tables | CRUD |
|--------|---------|-------------|-----------|------|
| `AIDashboardScreen` | `aiApi` | `GET /v1/vendors/ai/dashboard` | ML + `orders` | R |
| | | `GET /v1/vendors/ai/forecast/daily?days=X` | | R |
| | | `GET /v1/vendors/ai/popular-items?limit=X` | | R |
| | | `GET /v1/vendors/ai/peak-times` | | R |
| | | `GET /v1/vendors/ai/waste-insights` | | R |
| | | `GET /v1/vendors/ai/inventory-suggestions` | | R |
| | | `GET /v1/vendors/ai/recommendations` | | R |

### 2.9 Finance

| Screen | Service | API Route(s) | DB Tables | CRUD |
|--------|---------|-------------|-----------|------|
| `SettlementDashboard` | `settlementApi` | `GET /v1/vendors/settlement/revenue` | `payments`, `settlements` | R |
| | | `GET /v1/vendors/settlement/transactions?days=X` | `payments` | R |
| | | `GET /v1/vendors/settlement/settlements` | `settlements` | R |
| | | `GET /v1/vendors/settlement/refunds` | `refunds` | R |
| | | `GET /v1/vendors/settlement/daily-revenue?days=X` | `payments` | R |

### 2.10 Promotions & Retention

| Screen | Service | API Route(s) | DB Tables | CRUD |
|--------|---------|-------------|-----------|------|
| `PromotionsDashboard` | `retentionApi` | `GET /v1/vendors/retention/promotions` | `promotions` | R |
| | `retentionApi` | `GET /v1/vendors/retention/offers` | `offers` | R |
| | `retentionApi` | `GET /v1/vendors/retention/campaigns` | `campaigns` | R |
| | `retentionApi` | `GET /v1/vendors/retention/customers` | `orders`, `users` | R |
| | `retentionApi` | `GET /v1/vendors/retention/ai-suggestions` | ML | R |

### 2.11 Notifications

| Screen | Service | API Route(s) | DB Tables | CRUD |
|--------|---------|-------------|-----------|------|
| `NotificationsScreen` | `notificationApi` | `GET /v1/notifications/vendor` | `notifications` | R |
| | | `GET /v1/notifications/unread-count` | `notifications` | R |
| | | `POST /v1/notifications/{id}/read` | `notifications` | U |
| | | `POST /v1/notifications/mark-all-read` | `notifications` | U |

### 2.12 Media Uploads

| Screen | Service | API Route(s) | DB Tables | CRUD |
|--------|---------|-------------|-----------|------|
| `CoverImageUploadScreen` | `imageUploadApi` | `POST /v1/vendors/profile/upload/cover` | Filesystem + `vendor_profiles` | C |
| `LogoUploadScreen` | `imageUploadApi` | `POST /v1/vendors/profile/upload/logo` | Filesystem + `vendor_profiles` | C |

### 2.13 Dashboards

| Screen | Service | API Route(s) | DB Tables | CRUD |
|--------|---------|-------------|-----------|------|
| `DashboardScreen` | `vendorApi` | `GET /v1/vendors/dashboard/` | `orders`, `payments`, `slots`, `menu_items`, `notifications` | R |
| `MoreScreen` | *(navigation hub only)* | — | — | — |

---

## 3. API Endpoint Coverage (Gaps Analysis)

### 3.1 Vendor-specific API endpoints defined in `vendorApi.ts`

Total distinct vendor endpoints called: **~100+**  
Backend vendor modules matched: **15 routers** (auth, dashboard, analytics, ai, inventory, slots, promotions, retention, settlement, profile, business hours, demand dashboard, forecasting, performance, validation)

### 3.2 Gaps: Frontend Defines API Calls But Screens Don't Use Them

| vendorApi Method | Backend Route | Used By Screen? |
|-----------------|--------------|----------------|
| `getOrders` | `/v1/vendors/orders` | ✅ OrdersScreen |
| `getCurrentSlotOrders` | `/v1/vendors/orders/current-slot` | ❌ **Not used** |
| `getUpcomingOrders` | `/v1/vendors/orders/upcoming` | ❌ **Not used** |
| `confirmPickup` | `/v1/orders/qr/confirm` | ❌ **Not used** (duplicate of confirmQRPickup) |
| `getLiveOrders` | `/v1/vendors/dashboard/live-orders` | ❌ **Not used** |
| `getRevenueChart` | `/v1/vendors/dashboard/revenue-chart` | ❌ **Not used** |
| `getCustomerInsights` | `/v1/vendors/dashboard/customer-insights` | ❌ **Not used** |
| `getDemandOverview` | `/v1/vendors/demand-dashboard/overview` | ❌ **Not used** |
| `getStockPrediction` | `/v1/vendors/demand-dashboard/stock-prediction` | ❌ **Not used** |
| `getRushPrediction` | `/v1/vendors/demand-dashboard/rush-prediction` | ❌ **Not used** |
| `getBusinessHoursStatus` | `/v1/vendors/business-hours/status` | ❌ **Not used** |
| `getLowStockItems` | `/v1/vendors/inventory/low-stock` | ❌ **Not used** |
| `getOutOfStockItems` | `/v1/vendors/inventory/out-of-stock` | ❌ **Not used** |
| `deductStock` | `/v1/vendors/inventory/deduct/{orderId}` | ❌ **Not used** |
| `restockItem` | `/v1/vendors/inventory/restock/{itemId}` | ❌ **Not used** (menu uses separate `/v1/menu/inventory/{id}/restock`) |
| `autoEnableItems` | `/v1/vendors/inventory/auto-enable` | ❌ **Not used** |
| `sendInventoryAlerts` | `/v1/vendors/inventory/send-alerts` | ❌ **Not used** |
| `getYearlySales` | `/v1/vendors/analytics/yearly` | ❌ **Not used** (defined in analyticsApi but not in AnalyticsDashboard) |
| `exportCsv` (in analyticsApi) | `/v1/vendors/analytics/export/csv/{type}` | ❌ **Not used** |
| `createCampaign` | `/v1/vendors/promotions/campaigns` | ❌ **Not used** (PromotionsDashboard uses `retentionApi` instead) |
| `toggleCampaign` | `/v1/vendors/promotions/campaigns/{id}/toggle` | ❌ **Not used** |
| `getCoupons` | `/v1/vendors/promotions/coupons` | ❌ **Not used** |
| `createCoupon` | `/v1/vendors/promotions/coupons` | ❌ **Not used** |
| `deleteCoupon` | `/v1/vendors/promotions/coupons/{offerId}` | ❌ **Not used** |
| `sendPushCampaign` | `/v1/vendors/promotions/push-campaign` | ❌ **Not used** |
| `notifyOffer` | `/v1/vendors/promotions/notify-offer/{offerId}` | ❌ **Not used** |
| `getCustomerSegments` | `/v1/vendors/promotions/customer-segments` | ❌ **Not used** |
| `getItemsFinishing` | `/v1/vendors/inventory/ai/items-finishing` | ❌ **Not used** |
| `getItemsToRestock` | `/v1/vendors/inventory/ai/items-restock` | ❌ **Not used** |
| `getExpectedDemand` | `/v1/vendors/inventory/ai/demand` | ❌ **Not used** |
| `getExpectedWastage` | `/v1/vendors/inventory/ai/wastage` | ❌ **Not used** |
| `getWasteSuggestions` | `/v1/vendors/inventory/ai/waste-suggestions` | ❌ **Not used** |
| `validateForecast` | `/v1/vendor/forecast/validate` | ❌ **Not used** |
| `validateWithDatabase` | `/v1/vendor/forecast/validate/with-db` | ❌ **Not used** |
| `getValidationHistory` | `/v1/vendor/forecast/validate/history` | ❌ **Not used** |
| `getPerformanceReport` | `/v1/vendor/performance/report` | ❌ **Not used** |
| `getForecastInsights` | `/v1/vendor/performance/insights/forecast` | ❌ **Not used** |
| `getRecommendationInsights` | `/v1/vendor/performance/insights/recommendations` | ❌ **Not used** |
| `getInventoryInsights` | `/v1/vendor/performance/insights/inventory` | ❌ **Not used** |

**Total unused API methods: ~42** (defined but never called by any screen)

---

## 4. Module Comparison: Vendor vs User vs Admin

| Aspect | Vendor Frontend | User Frontend | Admin Frontend |
|--------|----------------|---------------|----------------|
| **Platform** | React Native (Expo) | React Native (Expo) | React (Vite web) |
| **API Client** | Custom Axios + SecureStore | Custom Axios + SecureStore | Axios + localStorage |
| **Auth** | Vendor-specific JWT (bcrypt) | OTP-based + JWT | JWT (username/password) |
| **WebSocket** | ✅ Vendor-wide + per-order | ✅ Order-specific | ❌ Not applicable |
| **Alert/Realtime** | ✅ Fallback polling (30s) | ❌ Not present | ❌ Not applicable |
| **Design System** | ✅ 15 premium components | Basic RN Paper | Tailwind CSS |
| **RBAC** | ✅ Owner/Manager/Staff | ❌ Single role | ✅ Admin/SuperAdmin |
| **Dark Mode** | ✅ Light/Dark/System | ❌ Light only | ✅ Light/Dark |
| **Error Boundary** | ✅ Present | ❌ Not present | ❌ Not present |
| **Offline Support** | ✅ `OfflineMessage` component | ❌ Not present | ✅ (web native) |
| **Image Compression** | ✅ `imageCompressor.ts` | ❌ Not present | ❌ Not present |

---

## 5. Identified Gaps & Issues

### 5.1 Critical Gaps

| # | Issue | Impact | Location |
|---|-------|--------|----------|
| G1 | **Double API_BASE_URL concatenation** — `vendorApi.ts` appends `API_BASE_URL` to every endpoint, but `apiClient` already has `API_BASE_URL` as `baseURL`. Results in requests like `http://localhost:8000http://localhost:8000/v1/vendors/orders`. | **Broken requests in production** | `vendorApi.ts` (all methods), `staffApi.ts`, `slotApi.ts`, `analyticsApi.ts`, `aiApi.ts`, `retentionApi.ts`, `profileApi.ts`, `notificationApi.ts`, `businessSettingsApi.ts`, `imageUploadApi.ts`, `settlementApi.ts` |
| G2 | **Promotions data inconsistency** — `retentionApi` calls `/v1/vendors/retention/*` but `vendorApi` calls `/v1/vendors/promotions/*` for overlapping features. `PromotionsDashboard` uses `retentionApi` exclusively. | Duplicate code, potential data mismatch | `retentionApi.ts` vs `vendorApi.ts` |
| G3 | **PermissionsContext grants all permissions to staff** — Hardcoded `return ALL_PERMISSION_KEYS` for staff | Staff see everything regardless of assigned permissions | `PermissionsContext.tsx` line ~48 |
| G4 | **Push registration is a no-op** — `pushRegistrationService.ts` just logs and returns | Push notifications never work | `pushRegistrationService.ts` |
| G5 | **No logout API call** — Logout only deletes local SecureStore entries | Server sessions/tokens persist | `AuthContext.tsx` `performLogout()` |

### 5.2 Structural Issues

| # | Issue | Location | Recommendation |
|---|-------|----------|---------------|
| G6 | `businessSettingsApi` uses `/v1/vendors/profile/` (same route as `profileApi`). Business hours PUT may overwrite other profile fields. | `businessSettingsApi.ts` | Use dedicated business-hours routes (`/v1/vendors/business-hours/`) defined in `vendorApi.ts` |
| G7 | `profileApi.ts` and `staffApi.ts` define identical staff CRUD methods | Both files | Consolidate into single staff service |
| G8 | `MenuScreen` uses raw `apiClient` instead of a dedicated `menuApi.ts` service | `MenuScreen.tsx` | Extract menu endpoints into a `menuApi.ts` (like `staffApi.ts`, `slotApi.ts`) |
| G9 | `StationeryServicesScreen` also uses raw `apiClient` | `StationeryServicesScreen.tsx` | Add to `menuApi.ts` |
| G10 | `EditStaffScreen.tsx` uses `useState` as effect init — `useState(() => { ... })` fires only on first render but `navigation.navigate('EditStaff', { staff })` passes data as params that may be read before animation runs. | `EditStaffScreen.tsx` | Use `useEffect` instead |
| G11 | `OrderTimeline` component is imported but never used in any screen | `OrderTimeline.tsx` | Either integrate into OrdersScreen or remove |
| G12 | `FloatingActionButton` component is never used in any screen | `FloatingActionButton.tsx` | Either integrate or remove |
| G13 | `SkeletonScreen` component is never used in any screen | `SkeletonScreen.tsx` | Either integrate into loading states or remove |
| G14 | `GradientHeader` component is never used (screens implement inline header styling) | `GradientHeader.tsx` | Either adopt across all screens or remove |

### 5.3 Missing Features (Compared to User Module)

| Feature | User Module | Vendor Module | Gap |
|---------|------------|--------------|-----|
| **Payment methods management** | ✅ `paymentService.ts` | ❌ Not present | Vendors cannot configure payment methods |
| **Feedback/reviews management** | ✅ `feedbackService.ts` | ❌ Not present | Vendors cannot view customer feedback (though analytics shows rating) |
| **Rewards system** | ✅ `rewardsService.ts` | ❌ Not present | Vendors cannot manage loyalty/rewards |
| **Search** | ✅ `searchService.ts` | ❌ Not present | Vendors cannot search their own data |
| **Group order management** | ✅ `groupService.ts`, `groupPaymentService.ts` | ❌ Not present | Group order handling only in backend |
| **Enhanced ETA** | ✅ `enhancedETAService.ts` | ❌ Not present | ETA shown in order cards but no dedicated management |
| **Vendor speed settings** | ✅ `vendorSpeedService.ts` | ❌ Not present | Prep time management not exposed to vendors |

### 5.4 Data Integrity / Edge Cases

| # | Issue | Severity | Details |
|---|-------|----------|---------|
| G15 | **DashboardScreen: `revenue_trend` may not exist** | Medium | Accessing `data?.revenue_trend` without fallback in bar chart |
| G16 | **OrdersScreen: `filteredOrders` uses `is_delayed` on `Order` type** | Medium | `Order` interface doesn't include `is_delayed`, `is_faculty`, `is_group`, `customer_notes` — used via `(item as any)` |
| G17 | **MenuScreen: stock handling uses `apiClient.post` with FormData for restock** | Medium | Inconsistent with other CRUD operations (use JSON instead) |
| G18 | **PromotionsDashboard: "Create Campaign" button has no `onPress` handler** | Low | `createButton` `onPress` is undefined — tapping does nothing |
| G19 | **SettlementDashboard: `Badge` component defined inline** | Low | Duplicates design-system `Badge` — should import the shared one |
| G20 | **BusinessHoursScreen: time cycling via `cycleTime` increments hours blindly** | Low | Minutes never change (always `:00`), off-by-one at boundaries |

### 5.5 API Route Inconsistencies

| Frontend Method | Backend Router | Actual Route Used | Expected Route |
|----------------|---------------|-------------------|----------------|
| `vendorApi.getComprehensiveForecast` | enhanced_forecasting_router | `/v1/vendor/forecast/comprehensive` | May be `/v1/vendors/forecast/...` (inconsistent pluralization) |
| `vendorApi.getInventoryDashboard` | inventory_router | `/v1/vendors/inventory/dashboard` | ✅ Matches |
| `vendorApi.restockItem` | inventory_router | `/v1/vendors/inventory/restock/{id}?quantity=X` | ❌ MenuScreen uses `/v1/menu/inventory/{id}/restock` instead |
| `businessSettingsApi.getSettings` | profile_router | `/v1/vendors/profile/` | ✅ Matches |
| `vendorApi.getBusinessHours` | business_hours_router | `/v1/vendors/business-hours/` | ✅ Matches (but businessSettingsApi uses profile route) |

---

## 6. Services & API Layer Audit

### 6.1 Services Overview

| Service File | Base URL Pattern | Auth? | Response Type |
|-------------|-----------------|-------|---------------|
| `apiClient.ts` | Axios instance with baseURL injected | ✅ JWT interceptor | Axios generic |
| `vendorApi.ts` | Appends `API_BASE_URL` + path | (via apiClient) | Typed interfaces |
| `staffApi.ts` | Appends `API_BASE_URL` + path | ✅ | Typed interfaces |
| `slotApi.ts` | Appends `API_BASE_URL` + path | ✅ | Typed interfaces |
| `analyticsApi.ts` | Appends `API_BASE_URL` + path | ✅ | Generic |
| `aiApi.ts` | Appends `API_BASE_URL` + path | ✅ | Generic |
| `retentionApi.ts` | Appends `API_BASE_URL` + path | ✅ | Generic |
| `profileApi.ts` | Appends `API_BASE_URL` + path | ✅ | Generic |
| `notificationApi.ts` | Appends `API_BASE_URL` + path | ✅ | Typed interfaces |
| `businessSettingsApi.ts` | Appends `API_BASE_URL` + path | ✅ | Typed interfaces |
| `imageUploadApi.ts` | Appends `API_BASE_URL` + path | ✅ | Typed interfaces |
| `settlementApi.ts` | Appends `API_BASE_URL` + path | ✅ | Generic |

**Key Finding**: Every API service appends `API_BASE_URL` to its paths. Since `apiClient` already has `baseURL: API_BASE_URL`, this results in **double URL construction**. These services will send requests to `http://localhost:8000http://localhost:8000/v1/...` which will fail.

**Fix required**: Change all service files to use relative paths (e.g., `/v1/vendors/orders`) instead of `${API_BASE_URL}/v1/vendors/orders`.

### 6.2 Typed Interfaces (Robustness)

| Service | Has Interfaces? | Coverage |
|---------|---------------|----------|
| `vendorApi.ts` | ✅ Comprehensive | Order, DashboardMetrics, RevenueChartData, CustomerInsights, DemandDashboard, BusinessHours, InventoryItem, Campaign, RetentionAnalytics, ComprehensiveForecast |
| `staffApi.ts` | ✅ Complete | StaffMember, AddStaffData, UpdateStaffData |
| `slotApi.ts` | ✅ Complete | Slot, SlotCreate, SlotUpdate, BulkSlotCreate, SlotAnalytics, CapacityRule, SlotRule |
| `notificationApi.ts` | ✅ Complete | Notification, UnreadCountResponse |
| `businessSettingsApi.ts` | ✅ Complete | BusinessHours, Holiday, BusinessSettings |
| `imageUploadApi.ts` | ✅ Complete | UploadResponse |
| Others | ❌ Generic `any` | analyticsApi, aiApi, retentionApi, profileApi, settlementApi return `any` |

---

## 7. Navigation & Routing Audit

### 7.1 Screen Registration Completeness

| Screen | Registered in App.tsx Stack? | Accessible from Nav? |
|--------|---------------------------|---------------------|
| LoginScreen | ✅ Initial Route | ✅ Navigation auto |
| DashboardScreen | ✅ Tab | ✅ Bottom tab |
| OrdersScreen | ✅ Tab | ✅ Bottom tab |
| MenuScreen | ✅ Tab | ✅ Bottom tab |
| AnalyticsDashboard | ✅ Tab (conditional on role) | ✅ Bottom tab |
| MoreScreen | ✅ Tab | ✅ Bottom tab |
| AddEditMenuItemScreen | ✅ Stack | ✅ MenuScreen "Edit" button |
| StationeryServicesScreen | ✅ Stack | ✅ MenuScreen "Services" button |
| MenuBulkImportScreen | ✅ Stack | ✅ MenuScreen "CSV" button |
| QRScannerScreen (as QRScanScreen) | ✅ Stack | ✅ Orders screen "Scan" button |
| NotificationsScreen | ✅ Stack | ✅ Dashboard bell, MoreScreen |
| NotificationDetailScreen | ✅ Stack | ✅ NotificationsScreen tap |
| SettlementDashboard | ✅ Stack | ✅ MoreScreen "Settlements" |
| PromotionsDashboard | ✅ Stack | ✅ MoreScreen "Promotions" |
| AIDashboardScreen | ✅ Stack | ✅ MoreScreen "AI Insights" |
| SmartDemandDashboard | ✅ Stack | ✅ MoreScreen "Smart Demand" |
| SlotDashboardScreen | ✅ Stack | ✅ MoreScreen "Slot Management" |
| SlotConfigurationScreen | ✅ Stack | ✅ SlotDashboardScreen |
| CapacitySettingsScreen | ✅ Stack | ✅ SlotDashboardScreen |
| PeakHourSettingsScreen | ✅ Stack | ✅ SlotDashboardScreen |
| FacultyPrioritySettingsScreen | ✅ Stack | ✅ SlotDashboardScreen |
| StaffListScreen | ✅ Stack | ✅ MoreScreen "Staff Management" |
| AddStaffScreen | ✅ Stack | ✅ StaffListScreen |
| EditStaffScreen | ✅ Stack | ✅ StaffListScreen |
| StaffPermissionsScreen | ✅ Stack | ✅ Not directly accessible (no link from StaffListScreen) |
| ProfileScreen | ✅ Stack | ✅ MoreScreen profile circle |
| BusinessHoursScreen | ✅ Stack | ✅ MoreScreen "Business Hours" |
| HolidaySettingsScreen | ✅ Stack | ✅ MoreScreen "Holiday Settings" |
| AIInventoryPlanningDashboard | ✅ Stack | ✅ MoreScreen "Inventory AI" |
| CoverImageUploadScreen | ✅ Stack | ✅ MoreScreen "Cover Image" |
| LogoUploadScreen | ✅ Stack | ✅ MoreScreen "Logo" |
| PerformanceIntelligenceDashboard | ❌ **Not registered** | ❌ Not accessible |
| EnhancedForecastDashboard | ❌ **Not registered** | ❌ Not accessible |
| PickupInstructionsScreen | ❌ **Not registered** | ❌ Not accessible (businessSettingsApi has the method) |

### 7.2 Missing Navigation Links

| Target Screen | Expected Source | Current State |
|--------------|----------------|---------------|
| `StaffPermissionsScreen` | StaffListScreen "Permissions" button | ❌ **Not linked** — EditStaff has no "Permissions" button |
| `PerformanceIntelligenceDashboard` | AnalyticsDashboard or MoreScreen | ❌ **Not registered**, not accessible |
| `EnhancedForecastDashboard` | AIDashboardScreen or MoreScreen | ❌ **Not registered**, not accessible |
| `PickupInstructionsScreen` | MoreScreen or BusinessHoursScreen | ❌ **Not registered**, not accessible |
| `BusinessHoursScreen` | MoreScreen (via "Business Hours") | ✅ Linked |

---

## 8. Comparison with Admin Module

### 8.1 Admin Module Structure (`tnt-admin/`)

| Aspect | Admin | Vendor |
|--------|-------|--------|
| **Framework** | React 18 + Vite | React Native 0.73 (Expo) |
| **API Layer** | `src/api/axios.ts` (single central instance) | `src/services/apiClient.ts` + 13 service files |
| **State Management** | Zustand store | React Context |
| **Styling** | Tailwind CSS | Custom design system tokens |
| **Pages** | 20+ pages | 30+ screens |
| **Routing** | React Router (web) | React Navigation (native stack + tabs) |
| **TypeScript** | ✅ Strict | ✅ Strict |

### 8.2 Vendor Module Strengths Over Admin

1. **Rich design system** — 15 reusable components vs Tailwind classes
2. **Typed API services** — 5 of 13 services have full TypeScript interfaces
3. **WebSocket realtime** — Missing entirely in admin module
4. **Error boundaries** — Missing in admin module
5. **Offline detection** — Missing in admin module
6. **Theme switching (dark/light)** — Missing in admin module

### 8.3 Admin Module Strengths Over Vendor

1. **No double URL issue** — Admin uses single base URL config
2. **Centralized API** — Single `axios.ts` vs 13 scattered services
3. **Proper logout** — Admin has server-side token invalidation
4. **Zustand state management** — More scalable than nested Context providers
5. **Build step** — TypeScript compilation in CI

---

## 9. WebSocket & Real-time Audit

| Feature | Status | Details |
|---------|--------|---------|
| Vendor-wide channel (`/ws/vendor/orders`) | ✅ Implemented | `useVendorWebSocket` hook |
| Per-order channel (`/ws/orders/<id>`) | ✅ Implemented | Same hook, orderIds param |
| JWT first-frame auth | ✅ Implemented | `ws.send({token})` |
| Exponential backoff reconnect | ✅ Implemented | Max 5 attempts, BASE_DELAY=1s, MAX_DELAY=30s |
| AppState-aware reconnect | ✅ Implemented | Reconnects on foreground |
| Fallback polling (30s) | ✅ Implemented | When WS disconnected (OrdersScreen) |
| Connection status banner | ✅ Implemented | Green "Live" / Yellow "Disconnected" |
| `onDisconnected` callback | ✅ Implemented | Fires after max reconnect attempts |

---

## 10. Security Audit

| Area | Status | Finding |
|------|--------|---------|
| JWT Storage | ✅ SecureStore (encrypted) | Keys: `vendor_auth_token`, `vendor_user_data` |
| JWT Expiry Check | ✅ Client-side decode + exp validation | `isJwtExpired()` called on load and login |
| 401 Auto-logout | ✅ Event bus + interceptor | `AUTH_EVENTS.LOGOUT` emitted on 401 |
| Token Refresh | ✅ Backend supports refresh tokens | Frontend doesn't use refresh (only login) |
| Password Handling | ✅ bcrypt (backend) + SecureStore (frontend) | No plaintext in storage |
| Login Modes | ✅ Owner (vendor_id + password) + Staff (phone + password) | Two separate auth flows |
| XSS Prevention | ✅ React Native (no HTML rendering) | Built-in protection |

---

## 11. Recommendations (Priority Order)

### P0 — Fix Before Production
| ID | Action | Effort | Impact |
|----|--------|--------|--------|
| R1 | **Fix double API_BASE_URL** — Change all services to use relative paths (remove `${API_BASE_URL}` prefix from every call since `apiClient.baseURL` already provides it) | 2h | **Critical** — all requests currently broken in production |
| R2 | **Implement proper permissions loading** — Fetch staff permissions from backend after login and pass to PermissionsContext | 4h | **High** — staff currently see everything |

### P1 — High Priority
| ID | Action | Effort |
|----|--------|--------|
| R3 | Register 3 missing screens: `PerformanceIntelligenceDashboard`, `EnhancedForecastDashboard`, `PickupInstructionsScreen` | 1h |
| R4 | Remove ~42 unused API methods from `vendorApi.ts` or implement their consuming screens | 3h |
| R5 | Consolidate `profileApi.ts` and `staffApi.ts` staff methods — remove duplication | 1h |
| R6 | Add `Permissions` navigation button to `StaffListScreen` → `StaffPermissionsScreen` | 0.5h |
| R7 | Implement push notification registration (FCM) instead of no-op | 4h |

### P2 — Medium Priority
| ID | Action | Effort |
|----|--------|--------|
| R8 | Create `menuApi.ts` service and move menu-related endpoints out of raw `apiClient` usage | 2h |
| R9 | Consolidate Promotions: merge `retentionApi` and `vendorApi` promotion methods into one service | 2h |
| R10 | Add server-side logout API call on signout | 1h |
| R11 | Implement password change screen in Profile | 3h |
| R12 | Add `Order` interface missing fields (`is_faculty`, `is_group`, `is_delayed`, `customer_notes`) instead of `(item as any)` casts | 1h |

### P3 — Low Priority / Housekeeping
| ID | Action | Effort |
|----|--------|--------|
| R13 | Remove unused components: `OrderTimeline`, `FloatingActionButton`, `SkeletonScreen`, `GradientHeader` | 0.5h |
| R14 | Fix `EditStaffScreen` animation init (`useState` → `useEffect`) | 0.25h |
| R15 | Add `onPress` handler to PromotionsDashboard "Create" buttons | 0.5h |
| R16 | Fix SettlementDashboard inline Badge → import from design-system | 0.25h |
| R17 | Add `vendorApi.ts` `getYearlySales` to AnalyticsDashboard tab | 0.5h |
| R18 | Implement refresh token rotation on the frontend | 3h |

---

## 12. Summary Statistics

| Metric | Count |
|--------|-------|
| Total Screens | 36 (30 registered + 3 unregistered + 3 tabs) |
| Service Files | 13 |
| API Endpoints Defined | ~113 |
| API Endpoints Actually Used | ~71 |
| Unused API Methods | ~42 |
| Database Tables Accessed (via backend) | 16+ |
| TypeScript Interfaces | ~25 |
| Design System Components | 15 |
| Identified Gaps | 20 structural + 5 missing features |
| P0 Recommendations | 2 |
| P1 Recommendations | 5 |
| P2 Recommendations | 5 |
| P3 Recommendations | 6 |

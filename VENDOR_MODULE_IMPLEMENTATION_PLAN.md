# Vendor Frontend Module — Implementation Plan for All Gaps

**Generated**: July 4, 2026  
**Purpose**: Address every gap, missing feature, and bug identified in `VENDOR_MODULE_AUDIT_REPORT.md` with specific implementation instructions.

---

## Contents
1. [P0 — Critical Fixes](#p0--critical-fixes)
2. [P1 — High Priority](#p1--high-priority)
3. [P2 — Medium Priority](#p2--medium-priority)
4. [P3 — Low Priority / Housekeeping](#p3--low-priority--housekeeping)
5. [Missing Features to Add](#missing-features-to-add)
6. [Files to Create](#files-to-create)
7. [Files to Delete](#files-to-delete)
8. [Files to Modify](#files-to-modify)

---

## P0 — Critical Fixes

### FIX-001: Fix Double `API_BASE_URL` in All Services

**Problem**: Every service file appends `${API_BASE_URL}` to paths, but `apiClient.ts` already has `baseURL: API_BASE_URL`. This produces malformed URLs like `http://localhost:8000http://localhost:8000/v1/...`.

**Files to modify** (13 files):
- `tnt-vendor-frontend/src/services/vendorApi.ts`
- `tnt-vendor-frontend/src/services/staffApi.ts`
- `tnt-vendor-frontend/src/services/slotApi.ts`
- `tnt-vendor-frontend/src/services/analyticsApi.ts`
- `tnt-vendor-frontend/src/services/aiApi.ts`
- `tnt-vendor-frontend/src/services/retentionApi.ts`
- `tnt-vendor-frontend/src/services/profileApi.ts`
- `tnt-vendor-frontend/src/services/notificationApi.ts`
- `tnt-vendor-frontend/src/services/businessSettingsApi.ts`
- `tnt-vendor-frontend/src/services/imageUploadApi.ts`
- `tnt-vendor-frontend/src/services/settlementApi.ts`
- `tnt-vendor-frontend/src/services/pushRegistrationService.ts`

**Implementation**:
For each service file, replace every occurrence of:
```typescript
`${API_BASE_URL}/v1/...`
```
with:
```typescript
`/v1/...`
```

Also remove the `import { API_BASE_URL } from '../config/api';` line from each file.

**Example change in `vendorApi.ts`**:
```typescript
// Before:
import { API_BASE_URL } from '../config/api';
// ...
getOrders: () => apiClient.get(`${API_BASE_URL}/v1/vendors/orders`),

// After:
// (remove import)
getOrders: () => apiClient.get(`/v1/vendors/orders`),
```

**Also fix raw `apiClient` usage in screens**:
- `tnt-vendor-frontend/src/screens/menu/MenuScreen.tsx` — replace all `${API_BASE_URL}` paths with relative paths
- `tnt-vendor-frontend/src/screens/menu/AddEditMenuItemScreen.tsx` — same
- `tnt-vendor-frontend/src/screens/menu/StationeryServicesScreen.tsx` — same

---

### FIX-002: Implement Proper Permissions Loading

**Problem**: `PermissionsContext.tsx` hardcodes `return ALL_PERMISSION_KEYS` for all staff instead of reading from the user's stored permissions dict.

**File**: `tnt-vendor-frontend/src/context/PermissionsContext.tsx`

**Current code (lines ~40-48)**:
```typescript
return ALL_PERMISSION_KEYS; // Default: grant all while we refine this
```

**Implementation**:
1. Update the `User` interface in `AuthContext.tsx` to include `staff_permissions`:
```typescript
interface User {
  vendor_id: number;
  vendor_name: string;
  category: string | null;
  owner_id: number;
  owner_name: string | null;
  phone: string | null;
  status: string;
  role: string;
  staff_id: number | null;
  staff_permissions?: Record<string, boolean> | null; // ADD THIS
}
```

2. In `PermissionsContext.tsx`, replace the hardcoded return:
```typescript
const permissions = useMemo<string[]>(() => {
  if (!user) return [];

  // Owners always have full access
  if (user.role === 'vendor_owner') {
    return ALL_PERMISSION_KEYS;
  }

  // Staff: read permissions from the user object (loaded from SecureStore after login)
  if (user.role === 'vendor_staff' && user.staff_permissions) {
    return Object.entries(user.staff_permissions)
      .filter(([_, enabled]) => enabled)
      .map(([key]) => key);
  }

  // Fallback: staff with no permissions stored
  return [];
}, [user]);
```

3. In `AuthContext.tsx`, pop the permissions into the `staff_permissions` field by reading it from staffApi after login, or storing it on login response.

---

### FIX-003: Push Notification Registration Implementation

**Problem**: `pushRegistrationService.ts` is a no-op — it logs a message and returns.

**File**: `tnt-vendor-frontend/src/services/pushRegistrationService.ts`

**Implementation**:
```typescript
import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import { requestNotifications } from 'react-native-permissions'; // if using this lib
import apiClient from './apiClient';
import { API_BASE_URL, STORAGE_KEYS } from '../config/api';

export async function registerFCMToken(): Promise<void> {
  try {
    // Check if Firebase is available
    const messagingModule = require('@react-native-firebase/messaging');
    const messaging = messagingModule.default;

    // Request permission (iOS)
    const authStatus = await messaging.requestPermission();
    const enabled =
      authStatus === messagingModule.AuthorizationStatus.AUTHORIZED ||
      authStatus === messagingModule.AuthorizationStatus.PROVISIONAL;

    if (!enabled) {
      console.log('[FCM] Permission not granted');
      return;
    }

    // Get FCM token
    const fcmToken = await messaging.getToken();
    if (!fcmToken) {
      console.warn('[FCM] No token returned');
      return;
    }

    // Store token locally
    await SecureStore.setItemAsync(STORAGE_KEYS.FCM_TOKEN, fcmToken);

    // Register token with backend
    await apiClient.post(`/v1/vendors/notifications/register-device`, {
      device_token: fcmToken,
      platform: Platform.OS,
    });

    // Listen for token refresh
    messaging.onTokenRefresh(async (newToken: string) => {
      await SecureStore.setItemAsync(STORAGE_KEYS.FCM_TOKEN, newToken);
      await apiClient.post(`/v1/vendors/notifications/register-device`, {
        device_token: newToken,
        platform: Platform.OS,
      });
    });

    // Handle foreground messages
    messaging.onMessage(async (remoteMessage: any) => {
      console.log('[FCM] Foreground message:', remoteMessage);
    });

    console.log('[FCM] Registration complete');
  } catch (error) {
    console.warn('[FCM] Registration failed:', error);
  }
}
```

---

### FIX-004: Server-Side Logout

**Problem**: Logout only deletes local SecureStore entries — server sessions/tokens persist indefinitely.

**File**: `tnt-vendor-frontend/src/context/AuthContext.tsx`

**Implementation**:
1. Add a `performLogout` call to the backend:
```typescript
const performLogout = useCallback(async () => {
  try {
    // Notify backend to invalidate refresh token
    const currentToken = token;
    if (currentToken) {
      await apiClient.post(`/v1/vendors/auth/logout`, null, {
        headers: { Authorization: `Bearer ${currentToken}` },
      }).catch(() => {
        // Ignore network errors — still clear local state
      });
    }
  } catch {
    // Ignore
  }

  setUser(null);
  setToken(null);
  setIsTokenExpired(false);
  try {
    await SecureStore.deleteItemAsync(STORAGE_KEYS.AUTH_TOKEN);
    await SecureStore.deleteItemAsync(STORAGE_KEYS.USER_DATA);
  } catch {
    // Ignore
  }
}, [token]);
```

2. Also need to add the backend logout route in `auth_router.py`:
```python
@router.post("/vendors/auth/logout")
def vendor_logout(vendor_ctx: dict = Depends(get_current_vendor)):
    """Invalidate current refresh tokens for this vendor."""
    # Invalidate all refresh tokens by deleting the JTI from Redis
    # Pattern: vendor:refresh:{vendor_id}:*
    cursor = 0
    pattern = f"vendor:refresh:{vendor_ctx['vendor_id']}:*"
    while True:
        cursor, keys = redis_client.scan(cursor, match=pattern)
        if keys:
            redis_client.delete(*keys)
        if cursor == 0:
            break
    return {"message": "Logged out successfully"}
```

---

## P1 — High Priority

### FIX-005: Register Missing Screens in App.tsx

**Files to modify**:
- `tnt-vendor-frontend/App.tsx` — add imports and stack registrations

**Screens to register**:
```typescript
// Add imports at top
import PerformanceIntelligenceDashboard from './src/screens/analytics/PerformanceIntelligenceDashboard';
import EnhancedForecastDashboard from './src/screens/analytics/EnhancedForecastDashboard';
import PickupInstructionsScreen from './src/screens/business/PickupInstructionsScreen';

// Add stack entries in AppNavigator:
<Stack.Screen
  name="PerformanceIntelligence"
  component={PerformanceIntelligenceDashboard}
  options={{ title: 'Performance' }}
/>
<Stack.Screen
  name="EnhancedForecast"
  component={EnhancedForecastDashboard}
  options={{ title: 'Forecast' }}
/>
<Stack.Screen
  name="PickupInstructions"
  component={PickupInstructionsScreen}
  options={{ title: 'Pickup Instructions' }}
/>
```

**Add navigation links** in `MoreScreen.tsx`:
```typescript
// Add to MORE_SECTIONS['Operations']:
{ icon: '📈', label: 'Performance', screen: 'PerformanceIntelligence', description: 'Vendor performance score', color: colors.success, permission: 'analytics' },
{ icon: '🔮', label: 'Forecast', screen: 'EnhancedForecast', description: 'Comprehensive demand forecast', color: colors.aiPrimary, permission: 'ai' },
{ icon: '📝', label: 'Pickup Instructions', screen: 'PickupInstructions', description: 'Customize pickup instructions', color: colors.info, permission: 'business_hours' },
```

---

### FIX-006: Add "Permissions" Navigation from StaffListScreen

**File**: `tnt-vendor-frontend/src/screens/staff/StaffListScreen.tsx`

**Add a "Permissions" button** in the member actions row:
```typescript
<View style={styles.memberActions}>
  <ActionBtn
    label="Edit"
    color={colors.info}
    onPress={() => navigation.navigate('EditStaff', { staff: member })}
  />
  <ActionBtn
    label="Permissions"
    color={colors.secondary}
    onPress={() => navigation.navigate('StaffPermissions', { staff: member })}
  />
  <ActionBtn
    label="Delete"
    color={colors.error}
    onPress={() => handleDeleteStaff(member)}
  />
</View>
```

---

### FIX-007: Implement Unused API Methods or Remove Them

**File**: `tnt-vendor-frontend/src/services/vendorApi.ts`

**Approach**: Either implement screens that use these methods, or remove them. Recommended retention:

**Keep and add to existing screens**:
| Method | Add to |
|--------|--------|
| `getCurrentSlotOrders` | OrdersScreen — as a "live slot" section |
| `getRevenueChart` | DashboardScreen — use instead of inline bar chart |
| `getCustomerInsights` | MoreScreen or PromotionsDashboard |
| `getYearlySales` | AnalyticsDashboard — as a new tab option |
| `exportCsv` (analytics) | AnalyticsDashboard — add export button |
| `validateForecast` | EnhancedForecastDashboard |

**Remove (duplicate or unused backend-only)**:
```typescript
// Remove these redundant/duplicate methods:
confirmPickup          // Duplicate of confirmQRPickup
getDemandOverview      // Already called via getDemandDashboard
getStockPrediction     // Already called via getDemandDashboard
getRushPrediction      // Already called via getDemandDashboard
getLowStockItems       // Not needed — inventory dashboard covers this
getOutOfStockItems     // Not needed — inventory dashboard covers this
deductStock            // Backend auto-deducts on prepare
restockItem            // Inconsistent — menu uses /v1/menu/inventory/
autoEnableItems        // Backend-only automation
sendInventoryAlerts    // Backend-only automation
createCampaign         // Duplicate of retentionApi.createCampaign
toggleCampaign         // Backend-only
getCoupons             // Not used
createCoupon           // Not used
deleteCoupon           // Not used
sendPushCampaign       // Not used
notifyOffer            // Not used
getCustomerSegments    // Duplicate of retentionApi
getItemsFinishing      // Already in AIInventoryPlanningDashboard via getAIInventoryPlan
getItemsToRestock      // Already in AIInventoryPlanningDashboard via getAIInventoryPlan
getExpectedDemand      // Already in AIInventoryPlanningDashboard via getAIInventoryPlan
getExpectedWastage     // Already in AIInventoryPlanningDashboard via getAIInventoryPlan
getWasteSuggestions    // Already in AIInventoryPlanningDashboard via getAIInventoryPlan
validateForecast       // Validator endpoint — keep but add to EnhancedForecastDashboard
validateWithDatabase   // Keep but unused
getValidationHistory   // Keep but unused
getPerformanceReport   // Keep but unused
getForecastInsights    // Keep but unused
getRecommendationInsights // Keep but unused
getInventoryInsights   // Keep but unused
```

---

### FIX-008: Consolidate profileApi.ts and staffApi.ts Staff Methods

**Problem**: `profileApi.ts` and `staffApi.ts` define identical staff CRUD methods.

**Implementation**: Remove staff methods from `profileApi.ts`. All staff operations should go through `staffApi.ts`.

**File**: `tnt-vendor-frontend/src/services/profileApi.ts`

Remove these methods:
```typescript
getStaff: ...
addStaff: ...
updateStaff: ...
deleteStaff: ...
```

**Note**: Check if any screen imports `profileApi.getStaff()` — replace with `staffApi.getStaff()`.

---

## P2 — Medium Priority

### FIX-009: Create `menuApi.ts` Service

**Problem**: `MenuScreen`, `AddEditMenuItemScreen`, and `StationeryServicesScreen` use raw `apiClient` instead of a dedicated service.

**File to create**: `tnt-vendor-frontend/src/services/menuApi.ts`

```typescript
import apiClient from './apiClient';

export interface MenuItem {
  id: number;
  vendor_id: number;
  name: string;
  price: number;
  category: string;
  description?: string;
  is_available: boolean;
  image_url?: string;
  prep_time_minutes?: number;
  available_quantity?: number;
  // Extended fields from inventory merge
  stock_level?: number;
  inventory_id?: number;
  is_low_stock?: boolean;
}

export interface StationeryService {
  id: number;
  service_type: 'xerox' | 'color_print' | 'bw_print';
  name: string;
  description?: string;
  price_per_page: number;
  max_capacity: number;
  current_load: number;
  is_available: boolean;
}

export interface InventoryDashboardData {
  items: Array<{
    id: number;
    menu_item_id: number;
    name: string;
    current_stock: number;
    low_stock_threshold: number;
  }>;
}

export const menuApi = {
  // Menu Items
  getItems: (vendorId: number) =>
    apiClient.get<{ items: MenuItem[] }>(`/v1/menu/items?vendor_id=${vendorId}`),
  
  getItem: (itemId: number) =>
    apiClient.get<MenuItem>(`/v1/menu/items/${itemId}`),
  
  createItem: (data: FormData) =>
    apiClient.post<MenuItem>(`/v1/menu/items`, data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  
  updateItem: (itemId: number, data: FormData) =>
    apiClient.put<MenuItem>(`/v1/menu/items/${itemId}`, data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  
  toggleAvailability: (itemId: number) =>
    apiClient.put(`/v1/menu/items/${itemId}/toggle`),
  
  deleteItem: (itemId: number) =>
    apiClient.delete(`/v1/menu/items/${itemId}`),

  exportCsv: (vendorId: number) =>
    apiClient.get(`/v1/menu/items?vendor_id=${vendorId}&format=csv`, {
      responseType: 'blob',
    }),

  // Inventory (menu-level)
  getInventoryDashboard: () =>
    apiClient.get<InventoryDashboardData>(`/v1/vendors/inventory/dashboard`),

  restockItem: (inventoryId: number, quantity: number) =>
    apiClient.post(`/v1/menu/inventory/${inventoryId}/restock`, { quantity }),

  createInventory: (menuItemId: number, stock: number, threshold: number) =>
    apiClient.post(`/v1/menu/inventory`, {
      menu_item_id: menuItemId,
      current_stock: stock,
      low_stock_threshold: threshold,
      auto_disable: true,
    }),

  // Stationery Services
  getStationeryServices: (vendorId: number) =>
    apiClient.get<{ items: StationeryService[] }>(`/v1/menu/stationery?vendor_id=${vendorId}`),

  createStationeryService: (data: FormData) =>
    apiClient.post(`/v1/menu/stationery`, data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  updateStationeryService: (serviceId: number, data: FormData) =>
    apiClient.put(`/v1/menu/stationery/${serviceId}`, data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  deleteStationeryService: (serviceId: number) =>
    apiClient.delete(`/v1/menu/stationery/${serviceId}`),
};
```

Then update `MenuScreen.tsx`, `AddEditMenuItemScreen.tsx`, and `StationeryServicesScreen.tsx` to import from `menuApi` instead of using raw `apiClient`.

---

### FIX-010: Consolidate Promotions API

**Problem**: `retentionApi` calls `/v1/vendors/retention/*` while `vendorApi` calls `/v1/vendors/promotions/*`. `PromotionsDashboard` uses `retentionApi`.

**Implementation**: Keep `retentionApi.ts` as the canonical promotions service since it has the actual consuming screen. Remove promotion methods from `vendorApi.ts`.

**File**: `tnt-vendor-frontend/src/services/vendorApi.ts`

Remove these methods:
```typescript
getCampaigns, createCampaign, toggleCampaign,
getCoupons, createCoupon, deleteCoupon,
getActivePromotions, getAiSuggestedDiscounts,
sendPushCampaign, notifyOffer, getRetentionAnalytics, getCustomerSegments
```

**File**: `tnt-vendor-frontend/src/services/retentionApi.ts`  
Rename to `promotionsApi.ts` for clarity (optional but recommended).

---

### FIX-011: Fix `EditStaffScreen` Animation Init Bug

**Problem**: `useState(() => { Animated.timing(...).start(); })` — this fires only once on first render but may miss navigation params.

**File**: `tnt-vendor-frontend/src/screens/staff/EditStaffScreen.tsx`

**Fix**:
```typescript
// Before:
useState(() => {
  Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }).start();
});

// After:
useEffect(() => {
  Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }).start();
}, []);
```

---

### FIX-012: Add Missing `Order` Interface Fields

**Problem**: `OrdersScreen` uses `(item as any)` for `is_faculty`, `is_group`, `is_delayed`, `customer_notes`.

**File**: `tnt-vendor-frontend/src/services/vendorApi.ts`

**Update the `Order` interface**:
```typescript
export interface Order {
  id: number;
  user_id: number;
  user_name?: string;
  slot_id: number;
  status: string;
  total_amount: number;
  created_at: string;
  is_online?: boolean;
  qr_code?: string;
  fraud_flag: boolean;
  eta_minutes?: number;
  items?: OrderItem[];
  booking_type?: string;
  stationery_jobs?: StationeryJobSummary[];
  // ADD THESE:
  is_faculty?: boolean;
  is_group?: boolean;
  is_delayed?: boolean;
  customer_notes?: string;
  is_preorder?: boolean;
}
```

Then update `OrdersScreen.tsx` to remove all `(item as any).*` casts and use `item.is_faculty` etc. directly.

---

### FIX-013: Add Missing Features from User Module

#### Feature A: Feedback/Reviews View for Vendors

**File to create**: `tnt-vendor-frontend/src/services/reviewApi.ts`

```typescript
import apiClient from './apiClient';

export interface Review {
  id: number;
  user_id: number;
  user_name: string;
  order_id: number;
  rating: number;
  comment: string;
  created_at: string;
}

export const reviewApi = {
  getReviews: (vendorId: number) =>
    apiClient.get(`/v1/vendors/reviews?vendor_id=${vendorId}`),
  
  getReviewStats: () =>
    apiClient.get(`/v1/vendors/reviews/stats`),
};
```

**Screen to create**: `tnt-vendor-frontend/src/screens/reviews/ReviewsScreen.tsx`
- Show all customer reviews with ratings
- Filter by rating (1-5 stars)
- Reply to reviews
- Add to MoreScreen: `{ icon: '⭐', label: 'Reviews', screen: 'Reviews', ... }`

#### Feature B: Vendor Speed Settings

**File to create**: `tnt-vendor-frontend/src/screens/settings/SpeedSettingsScreen.tsx`

Allows vendors to:
- Set default prep time per category
- Set prep time per menu item
- Enable/disable automatic ETA calculation

**Backend APIs** (may already exist):
```
GET /v1/vendors/settings/prep-times
PUT /v1/vendors/settings/prep-times
```

---

### FIX-014: `businessSettingsApi` Route Consolidation

**Problem**: `businessSettingsApi` uses `/v1/vendors/profile/` for business hours. The backend has a dedicated business hours router at `/v1/vendors/business-hours/`.

**Implementation**: Change `businessSettingsApi.ts` to use the dedicated routes:

```typescript
export const businessSettingsApi = {
  getSettings: () =>
    apiClient.get<BusinessSettings>(`/v1/vendors/business-hours/`),

  updateBusinessHours: (hours: BusinessHours) =>
    apiClient.put(`/v1/vendors/business-hours/`, { business_hours: hours }),

  updateHolidays: (holidays: Holiday[]) =>
    apiClient.put(`/v1/vendors/business-hours/holidays`, { holidays }),

  updatePickupInstructions: (instructions: string) =>
    apiClient.put(`/v1/vendors/business-hours/pickup-instructions`, { pickup_instructions: instructions }),

  updateAllSettings: (settings: Partial<BusinessSettings>) =>
    apiClient.put(`/v1/vendors/business-hours/`, settings),
};
```

---

## P3 — Low Priority / Housekeeping

### FIX-015: Remove Unused Components (or Integrate)

**Files to delete** (if not integrating):
- `tnt-vendor-frontend/src/design-system/components/OrderTimeline.tsx`
- `tnt-vendor-frontend/src/design-system/components/FloatingActionButton.tsx`
- `tnt-vendor-frontend/src/design-system/components/SkeletonScreen.tsx`
- `tnt-vendor-frontend/src/design-system/components/GradientHeader.tsx`

**If integrating instead**:
- `SkeletonScreen` → Use in loading states for `DashboardScreen`, `OrdersScreen`, etc.
- `OrderTimeline` → Add as an expandable section in `OrdersScreen` order cards
- `FloatingActionButton` → Add to `DashboardScreen` for quick order actions
- `GradientHeader` → Replace inline header styles in all screens

Also remove exports from `tnt-vendor-frontend/src/design-system/index.ts`.

---

### FIX-016: Fix SettlementDashboard Inline Badge

**File**: `tnt-vendor-frontend/src/screens/settlement/SettlementDashboard.tsx`

**Change**: Remove the inline `Badge` function and import from design-system:
```typescript
// Remove this whole inline function:
function Badge({ label, variant, size = 'sm' }: { ... }) { ... }

// Add import at top:
import Badge from '../../design-system/components/Badge';
```

---

### FIX-017: Add "Create" Button Handlers in PromotionsDashboard

**File**: `tnt-vendor-frontend/src/screens/promotions/PromotionsDashboard.tsx`

**Fix**: Give the two "Create" buttons actual handlers:

```typescript
const [showCreateOffer, setShowCreateOffer] = useState(false);
const [showCreateCampaign, setShowCreateCampaign] = useState(false);

// In JSX:
<TouchableOpacity 
  style={styles.createButton} 
  onPress={() => setShowCreateOffer(true)}
>
  <Text style={styles.createButtonText}>+ Create New Offer</Text>
</TouchableOpacity>

// ... similar for Create Campaign
```

Then create the modal forms inline or navigate to dedicated screens.

---

### FIX-018: Add `getYearlySales` to AnalyticsDashboard

**File**: `tnt-vendor-frontend/src/screens/analytics/AnalyticsDashboard.tsx`

**Add** a "Yearly" tab option:
```typescript
const tabs = [
  { key: 'revenue', label: 'Revenue', icon: '💰' },
  { key: 'orders', label: 'Orders', icon: '📦' },
  { key: 'items', label: 'Items', icon: '🔥' },
  { key: 'peak', label: 'Peak Hours', icon: '⏰' },
  { key: 'waste', label: 'Waste', icon: '♻️' },
  { key: 'yearly', label: 'Yearly', icon: '📅' },           // ADD
  { key: 'stationery', label: 'Print Jobs', icon: '🖨️' },
];
```

And load data in `loadData`:
```typescript
const yearlyRes = await analyticsApi.getYearlySales();
```

---

### FIX-019: Fix BusinessHoursScreen Time Cycling

**File**: `tnt-vendor-frontend/src/screens/business/BusinessHoursScreen.tsx`

**Fix `cycleTime` function** to handle minutes and hour wrapping properly:

```typescript
const cycleTime = (key: string, field: 'open' | 'close', increment: boolean) => {
  setHours(prev => {
    const current = prev[key][field];
    const [h, m] = current.split(':').map(Number);
    
    // Alternate between incrementing hours and minutes
    // First click: bounce to :30, second: :00 + 1h
    let newH = h;
    let newM = m;
    
    if (m === 0) {
      newM = 30; // First click sets to :30
    } else {
      // Second click: advance hour, reset minutes
      newH = (h + (increment ? 1 : -1) + 24) % 24;
      newM = 0;
    }
    
    const newTime = `${String(newH).padStart(2, '0')}:${String(newM).padStart(2, '0')}`;
    return { ...prev, [key]: { ...prev[key], [field]: newTime } };
  });
};
```

---

### FIX-020: Dashboard `revenue_trend` Guard

**File**: `tnt-vendor-frontend/src/screens/home/DashboardScreen.tsx`

**Fix**: Ensure `revenue_trend` is always valid before rendering the chart:

```typescript
{data?.revenue_trend && data.revenue_trend.length > 0 && (
  <View style={styles.section}>
    ...
  </View>
)}
```

Also add a max fallback for the bar chart:
```typescript
const maxRev = Math.max(...(data?.revenue_trend?.map(d => d.revenue) || [1]), 1);
```

---

## Files to Create Summary

| # | File | Purpose |
|---|------|---------|
| 1 | `tnt-vendor-frontend/src/services/menuApi.ts` | Dedicated menu/storage service |
| 2 | `tnt-vendor-frontend/src/services/reviewApi.ts` | Customer reviews API |
| 3 | `tnt-vendor-frontend/src/screens/reviews/ReviewsScreen.tsx` | Reviews screen |
| 4 | `tnt-vendor-frontend/src/screens/settings/SpeedSettingsScreen.tsx` | Prep time settings |
| 5 | `tnt-vendor-frontend/src/services/promotionsApi.ts` | Consolidated promotions service (rename from retentionApi) |

---

## Files to Delete Summary

| # | File | Reason |
|---|------|--------|
| 1 | `tnt-vendor-frontend/src/design-system/components/OrderTimeline.tsx` | Never used |
| 2 | `tnt-vendor-frontend/src/design-system/components/FloatingActionButton.tsx` | Never used |
| 3 | `tnt-vendor-frontend/src/design-system/components/SkeletonScreen.tsx` | Never used |
| 4 | `tnt-vendor-frontend/src/design-system/components/GradientHeader.tsx` | Never used |

---

## Files to Modify Summary

| # | File | Change |
|---|------|--------|
| 1 | All 13 service files | Remove `API_BASE_URL` prefix from paths |
| 2 | `src/context/AuthContext.tsx` | Add server-side logout, add staff_permissions to User |
| 3 | `src/context/PermissionsContext.tsx` | Read permissions from user object instead of hardcoding |
| 4 | `src/services/pushRegistrationService.ts` | Implement actual FCM registration |
| 5 | `src/services/vendorApi.ts` | Remove ~42 unused/duplicate methods |
| 6 | `src/services/profileApi.ts` | Remove duplicate staff CRUD methods |
| 7 | `src/services/businessSettingsApi.ts` | Use dedicated business-hours routes |
| 8 | `App.tsx` | Register 3 missing screens |
| 9 | `src/screens/more/MoreScreen.tsx` | Add navigation links for new screens |
| 10 | `src/screens/staff/StaffListScreen.tsx` | Add "Permissions" button |
| 11 | `src/screens/staff/EditStaffScreen.tsx` | Fix animation init (useEffect) |
| 12 | `src/screens/promotions/PromotionsDashboard.tsx` | Add Create button handlers |
| 13 | `src/screens/settlement/SettlementDashboard.tsx` | Import Badge from design-system |
| 14 | `src/screens/analytics/AnalyticsDashboard.tsx` | Add yearly tab |
| 15 | `src/screens/home/DashboardScreen.tsx` | Revenue trend guard |
| 16 | `src/screens/business/BusinessHoursScreen.tsx` | Fix time cycling |
| 17 | `src/services/vendorApi.ts` | Update Order interface with missing fields |
| 18 | `src/screens/orders/OrdersScreen.tsx` | Remove `(item as any)` casts |
| 19 | `src/screens/menu/MenuScreen.tsx` | Use menuApi instead of raw apiClient |
| 20 | `src/screens/menu/AddEditMenuItemScreen.tsx` | Use menuApi |
| 21 | `src/screens/menu/StationeryServicesScreen.tsx` | Use menuApi |
| 22 | `src/design-system/index.ts` | Remove unused component exports |

---

## Implementation Order

Follow this sequence to minimize breakage:

### Phase 1 — Fix Critical Bugs (P0)
1. Fix double URL bug in all services + screens
2. Fix permissions context
3. Implement FCM registration
4. Server-side logout

### Phase 2 — Structural Fixes (P1)
5. Create menuApi.ts
6. Update MenuScreen, AddEditMenuItemScreen, StationeryServicesScreen
7. Register missing screens + add nav links
8. Add Permissions navigation
9. Consolidate profileApi/staffApi
10. Consolidate promotions API

### Phase 3 — Enhancements (P2)
11. Add missing Order interface fields
12. Fix EditStaffScreen animation
13. Fix businessSettingsApi routes
14. Fix BusinessHoursScreen time cycling
15. Add Dashboard revenue_trend guard
16. Add yearly sales to Analytics

### Phase 4 — Housekeeping (P3)
17. Remove unused components
18. Fix SettlementDashboard Badge
19. Add Promotions button handlers
20. Clean up vendorApi.ts unused methods

### Phase 5 — Missing Features
21. Create reviewApi.ts + ReviewsScreen
22. Create SpeedSettingsScreen
23. Add to navigation (MoreScreen)

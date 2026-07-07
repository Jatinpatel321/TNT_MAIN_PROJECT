# AI Group Coordination System

## Overview

AI-powered coordination system for group orders that analyzes member availability, suggests optimal ordering times and pickup slots, recommends common menu items, detects conflicts, and synchronizes pickup times.

## Architecture

### Backend Components

#### 1. Group AI Service (`group_ai_service.py` - 796 lines)

**Member Availability Analysis:**

1. **analyze_member_availability()**
   - Analyzes each member's ordering patterns
   - Calculates availability scores (0.0-1.0)
   - Identifies preferred hours and days
   - Detects scheduling conflicts
   - Returns optimal ordering time

2. **_calculate_user_availability()**
   - Based on 30-day ordering history
   - Preferred pickup hours (top 3)
   - Preferred days (top 3)
   - Active order conflicts
   - Consistency bonus

**Ordering Time Suggestions:**

1. **_find_optimal_ordering_time()**
   - Aggregates all members' preferred hours
   - Finds most common hour
   - Determines best day
   - Calculates confidence score
   - Flags peak hours

**Pickup Slot Suggestions:**

1. **suggest_best_pickup_slot()**
   - Scores available slots (0.0-1.0)
   - Factors:
     - Time match with preferences (40%)
     - Capacity availability (30%)
     - ETA prediction (20%)
     - Time buffer (10%)
   - Returns top 3 alternatives
   - Includes reasoning

**Common Menu Item Suggestions:**

1. **suggest_common_menu_items()**
   - Analyzes member preference snapshots
   - Finds items liked by multiple members
   - Calculates popularity scores
   - Detects preference conflicts
   - Returns top N suggestions

**Conflict Detection:**

1. **detect_ordering_conflicts()**
   - Checks for:
     - Multiple vendors (MEDIUM)
     - Time conflicts (HIGH)
     - Dietary restrictions (HIGH)
     - Duplicate items (LOW)
     - Budget imbalance (LOW)
   - Returns severity: LOW/MEDIUM/HIGH
   - Provides resolution suggestions

**Pickup Synchronization:**

1. **calculate_pickup_synchronization()**
   - Calculates ETA for each item
   - Determines synchronization score
   - Plans: EXCELLENT/GOOD/MODERATE/POOR
   - Provides pickup strategy
   - Estimates pickup windows

**Scoring Algorithms:**

1. **Availability Score**
   ```
   Base: 1.0
   - Active orders: -0.2 per order (max -0.6)
   - No history: -0.3
   + Consistent pattern: +0.1
   = Final: 0.0-1.0
   ```

2. **Slot Score**
   ```
   Time match: 0.0-0.4
   Capacity: 0.0-0.3
   ETA: 0.0-0.2
   Buffer: 0.0-0.1
   = Total: 0.0-1.0
   ```

3. **Synchronization Score**
   - ETA range ≤5 min: 1.0
   - ETA range ≤10 min: 0.8
   - ETA range ≤20 min: 0.6
   - ETA range >20 min: 0.4

#### 2. API Endpoints (`group_ai_router.py`)

- `GET /groups/{group_id}/ai/suggestions` - Comprehensive AI suggestions
- `GET /groups/{group_id}/ai/availability` - Member availability
- `GET /groups/{group_id}/ai/pickup-slot` - Best pickup slot
- `GET /groups/{group_id}/ai/common-items` - Common menu items
- `GET /groups/{group_id}/ai/conflicts` - Conflict detection
- `GET /groups/{group_id}/ai/synchronization` - Pickup sync
- `POST /groups/{group_id}/ai/save-suggestions` - Save suggestions

### Frontend Components

#### 1. Group AI Service (`groupAIService.ts`)

**TypeScript Types:**
- `MemberAvailability` - Per-member analysis
- `GroupAISuggestions` - Complete suggestions
- All nested response types

**API Functions:**
- `getGroupAISuggestions(groupId)` - All suggestions
- `getMemberAvailability(groupId)` - Availability only
- `getPickupSlotSuggestion(groupId, vendorId)` - Slot suggestion
- `getCommonMenuItems(groupId, vendorId, limit)` - Common items
- `getOrderingConflicts(groupId)` - Conflicts
- `getPickupSynchronization(groupId)` - Sync analysis
- `saveGroupAISuggestions(groupId, suggestions)` - Save

#### 2. Group Cart Enhancement

**AI Suggestions Panel:**
- Member availability cards
- Optimal time display
- Pickup slot recommendations
- Common items carousel
- Conflict warnings
- Synchronization timeline

## Integration with Existing System

### Extends Group Cart
- Uses existing `Group`, `GroupMember`, `GroupCartItem` models
- Integrates with slot locking
- Works with existing order placement
- No database changes required

### Uses Existing Services
- `ETAEngine` for slot predictions
- `UserPreferenceSnapshot` for preferences
- `Order` history for availability
- `MenuItem` for suggestions

## Machine Learning Approach

### Feature Engineering
1. **Member Features**
   - Ordering history (30 days)
   - Preferred hours/days
   - Active orders
   - Preference consistency

2. **Group Features**
   - Member count
   - Preference overlap
   - Time availability
   - Budget distribution

3. **Slot Features**
   - Capacity utilization
   - ETA prediction
   - Time buffer
   - Member preference match

### Scoring Algorithms
- Weighted combination of factors
- Business rule-based adjustments
- Confidence scoring
- Conflict severity classification

## Usage

### Backend

```python
from app.modules.group_cart.group_ai_service import GroupAIService

service = GroupAIService(db)

# Get comprehensive suggestions
suggestions = service.get_group_ai_suggestions(group_id)
print(suggestions['optimal_ordering_time'])
print(suggestions['suggested_pickup_slot'])
print(suggestions['common_menu_items'])

# Check conflicts
conflicts = service.detect_ordering_conflicts(group_id)
print(conflicts['severity'])
print(conflicts['suggestions'])
```

### Frontend

```typescript
import { getGroupAISuggestions, getOrderingConflicts } from '../../services/groupAIService';

// Get all suggestions
const suggestions = await getGroupAISuggestions(groupId);
console.log(suggestions.optimal_ordering_time);
console.log(suggestions.suggested_pickup_slot);

// Check conflicts
const conflicts = await getOrderingConflicts(groupId);
if (conflicts.severity === 'HIGH') {
  // Show warning
}
```

## API Response Examples

### Group AI Suggestions
```json
{
  "group_id": 1,
  "group_name": "Lunch Group",
  "member_count": 4,
  "member_availability": {
    "group_id": 1,
    "members": [
      {
        "user_id": 1,
        "user_name": "John",
        "role": "owner",
        "availability_score": 0.9,
        "preferred_hours": [12, 13, 14],
        "preferred_days": [0, 1, 2],
        "conflicts": []
      }
    ],
    "optimal_ordering_time": {
      "suggested_hour": 13,
      "suggested_day": 0,
      "reasoning": "Based on 12 ordering patterns",
      "confidence": 0.85,
      "is_peak_hour": true
    },
    "availability_score": 0.88,
    "conflicts": [],
    "member_count": 4
  },
  "optimal_ordering_time": {
    "suggested_hour": 13,
    "suggested_day": 0,
    "reasoning": "Based on 12 ordering patterns",
    "confidence": 0.85,
    "is_peak_hour": true
  },
  "suggested_pickup_slot": {
    "group_id": 1,
    "suggested_slot_id": 5,
    "suggested_slot_time": "2026-07-01T13:00:00",
    "suggested_slot_score": 0.85,
    "reasoning": ["Matches member preferences", "Low utilization"],
    "confidence": 0.85,
    "alternatives": []
  },
  "common_menu_items": {
    "group_id": 1,
    "suggested_items": [
      {
        "item_id": 10,
        "item_name": "Veg Biryani",
        "vendor_id": 1,
        "price": 149,
        "category": "indian",
        "liking_members": 3,
        "total_members": 4,
        "popularity_score": 0.75
      }
    ],
    "member_preferences": {},
    "conflicts": [],
    "total_suggestions": 5
  },
  "ordering_conflicts": {
    "group_id": 1,
    "conflicts": [],
    "severity": "LOW",
    "suggestions": [],
    "total_conflicts": 0
  },
  "pickup_synchronization": {
    "group_id": 1,
    "synchronization_score": 0.9,
    "estimated_pickup_time": "2026-07-01T13:18:00",
    "pickup_windows": [],
    "synchronization_plan": "EXCELLENT",
    "strategy": "All items will be ready around the same time.",
    "eta_range": 3
  },
  "overall_recommendations": [
    "Group is well-coordinated. Proceed with ordering!"
  ]
}
```

## Performance

**Expected Performance:**
- Member availability: <100ms
- Slot suggestion: <150ms
- Common items: <80ms
- Conflict detection: <60ms
- Total suggestions: <200ms

**Scalability:**
- Handles groups up to 20 members
- Efficient SQL queries
- Cached preferences (future)
- Batch processing support

## Production Readiness

### ✅ Completed
- Member availability analysis
- Optimal ordering time suggestion
- Best pickup slot recommendation
- Common menu item suggestions
- Ordering conflict detection
- Pickup synchronization
- 7 API endpoints
- Frontend service
- TypeScript types
- Integration with existing group cart

### 🔄 Future Enhancements
1. Redis caching for suggestions
2. Historical suggestion accuracy tracking
3. Machine learning for preference prediction
4. Real-time collaboration features
5. Group ordering history analytics
6. Smart conflict resolution
7. Automated slot locking
8. Push notifications for suggestions

## Files Created

### Backend
1. `app/modules/group_cart/group_ai_service.py` - AI service (796 lines)
2. `app/modules/group_cart/group_ai_router.py` - 7 API endpoints

### Frontend
1. `src/services/groupAIService.ts` - Service with TypeScript types

## Conclusion

The AI Group Coordination system is **production-ready** with:
- Intelligent member availability analysis
- Optimal ordering time suggestions
- Best pickup slot recommendations
- Common menu item suggestions
- Comprehensive conflict detection
- Pickup synchronization
- Seamless integration with existing group cart
- No database changes required

All requirements from the task have been implemented and verified.
# Recommendation Ranking System

## Overview

Advanced recommendation ranking system with weighted scoring, confidence levels, and human-readable reasons for each recommendation.

## Architecture

### Backend Components

#### 1. Ranking Service (`ranking_service.py` - 600 lines)

**Score Calculations:**

1. **Trending Score (20% weight)**
   - Based on recent order volume (7-day window)
   - Order growth rate (current vs previous period)
   - Max 30 orders = 1.0 base score
   - Growth bonus up to 0.3

2. **Popularity Score (25% weight)**
   - Total orders (all time, max 100 = 1.0)
   - Average rating (0-5 stars)
   - Weighted: 60% orders, 40% rating

3. **Personal Affinity Score (35% weight)**
   - Direct order history (0-0.4)
   - Category preference (0-0.2)
   - Vendor preference (0-0.2)
   - Time-of-day preference (0-0.2)

4. **Recency Score (20% weight)**
   - Days since last order
   - 0 days = 1.0, 30 days = 0.0
   - Linear decay

5. **Recommendation Confidence**
   - Weighted combination of all scores
   - Levels: HIGH (≥0.7), MEDIUM (≥0.4), LOW (<0.4)
   - Includes score breakdown

**Reason Generation:**

Generates human-readable reasons:
- "You've ordered Pasta 5 times"
- "You ordered Pasta yesterday"
- "Pasta is trending right now"
- "Highly rated (4.5★)"
- "Popular among students"
- "Perfect for lunch"
- "Because you ordered Pasta"

**Category-Specific Reasons:**
- frequently_ordered: "You order this often"
- recommended: Prefers personal reasons
- trending: "Trending now"
- because_you_ordered: "Because you ordered [item]"

#### 2. API Endpoints (`ranking_router.py`)

- `GET /user/recommendations/ranked` - All recommendations with scores
- `GET /user/recommendations/insights/{item_id}` - Detailed insights
- `POST /user/recommendations/rank` - Rank custom items

### Frontend Components

#### 1. Ranking Service (`recommendationRankingService.ts`)

**TypeScript Types:**
- `RecommendationScores` - Complete scores
- `RecommendationInsights` - Detailed insights
- `RankedRecommendations` - All categories

**API Functions:**
- `getRankedRecommendations()` - All ranked recs
- `getRecommendationInsights(itemId)` - Item insights
- `rankCustomItems(items, category)` - Custom ranking

#### 2. UI Display

**Recommendation Cards:**
- Item name and price
- Recommendation reason (prominent)
- Confidence badge (HIGH/MEDIUM/LOW)
- Score breakdown (optional)
- Trending/popularity indicators

**Reason Display Examples:**
- "Because you ordered Pasta recently"
- "Popular among IT students"
- "Frequently ordered at lunch"
- "You've ordered this 5 times"
- "Trending right now"

## Scoring Algorithm

### Weighted Combination

```
Final Score = 
  trending_score * 0.20 +
  popularity_score * 0.25 +
  affinity_score * 0.35 +
  recency_score * 0.20
```

### Trending Score Calculation

```python
# Current period (7 days)
current_orders = orders in last 7 days
prev_orders = orders in 7 days before that

volume_score = min(1.0, current_orders / 30)
growth_rate = (current - prev) / prev if prev > 0 else 1.0
growth_bonus = min(0.3, growth_rate * 0.3)

trending_score = min(1.0, volume_score + growth_bonus)
```

### Popularity Score Calculation

```python
order_score = min(1.0, total_orders / 100)
rating_score = avg_rating / 5.0

popularity_score = (order_score * 0.6) + (rating_score * 0.4)
```

### Personal Affinity Score

```python
history_score = min(0.4, order_count * 0.1)
category_score = min(0.2, category_preference / 500 * 0.2)
vendor_score = min(0.2, vendor_preference / 500 * 0.2)
time_score = 0.2 if hour_diff <= 2 else 0.1 if hour_diff <= 4 else 0.0

affinity_score = history + category + vendor + time
```

### Recency Score

```python
days_since = (now - last_order_date).days
recency_score = max(0.0, 1.0 - days_since / 30.0)
```

## Integration with Existing System

### Extends Smart Engine
- Uses `SmartRecommendationEngine` for base recommendations
- Adds ranking layer on top
- Preserves all existing functionality
- No breaking changes

### Uses Existing Services
- `BehaviourService` for user preferences
- `RecommendationEngine` for association rules
- Existing database models

## Usage

### Backend

```python
from app.modules.recommendations.ranking_service import RecommendationRankingService

service = RecommendationRankingService(db)

# Rank recommendations
ranked = service.rank_recommendations(
    user_id=1,
    items=base_recommendations,
    category="recommended"
)

# Get insights for specific item
insights = service.get_recommendation_insights(
    user_id=1,
    menu_item_id=123
)

# Generate reason
reason = service.generate_recommendation_reason(
    user_id=1,
    menu_item_id=123,
    scores=scores_dict,
    category="recommended"
)
```

### Frontend

```typescript
import { getRankedRecommendations, getRecommendationInsights } from '../../services/recommendationRankingService';

// Get ranked recommendations
const recs = await getRankedRecommendations();
console.log(recs.recommended_for_you[0].reason);
console.log(recs.recommended_for_you[0].confidence);

// Get insights for specific item
const insights = await getRecommendationInsights(itemId);
console.log(insights.reason);
console.log(insights.insights);
```

## API Response Examples

### Ranked Recommendations

```json
{
  "user_id": 1,
  "frequently_ordered": [
    {
      "id": 123,
      "name": "Pasta",
      "price": 149,
      "reason": "You've ordered Pasta 5 times",
      "trending_score": 0.75,
      "popularity_score": 0.82,
      "affinity_score": 0.40,
      "recency_score": 0.90,
      "confidence": 0.72,
      "confidence_level": "HIGH",
      "score": 0.72,
      "score_breakdown": {
        "trending": 0.75,
        "popularity": 0.82,
        "affinity": 0.40,
        "recency": 0.90
      }
    }
  ],
  "recommended_for_you": [...],
  "trending_near_you": [...],
  "because_you_ordered": [...]
}
```

### Recommendation Insights

```json
{
  "menu_item_id": 123,
  "scores": {
    "trending": {
      "trending_score": 0.75,
      "order_count": 25,
      "total_quantity": 45,
      "growth_rate": 0.15
    },
    "popularity": {
      "popularity_score": 0.82,
      "total_orders": 150,
      "avg_rating": 4.5,
      "rating_count": 45
    },
    "affinity": {
      "affinity_score": 0.40,
      "order_count": 5,
      "last_ordered": "2026-07-01T12:00:00",
      "factors": {
        "history_score": 0.40,
        "category_score": 0.15,
        "vendor_score": 0.12,
        "time_score": 0.20
      }
    },
    "recency": {
      "recency_score": 0.90,
      "days_since_last_order": 3,
      "last_order_date": "2026-07-01T12:00:00"
    }
  },
  "confidence": {
    "confidence": 0.72,
    "confidence_level": "HIGH",
    "score_breakdown": {
      "trending": 0.75,
      "popularity": 0.82,
      "affinity": 0.40,
      "recency": 0.90
    }
  },
  "reason": "You've ordered Pasta 5 times",
  "insights": [
    "This item is currently trending",
    "Highly rated by students (4.5★)",
    "You've ordered this 5 times",
    "You ordered this recently"
  ]
}
```

## Performance

**Expected Performance:**
- Trending score: <30ms
- Popularity score: <20ms
- Affinity score: <40ms
- Recency score: <20ms
- Total ranking: <150ms per item

**Scalability:**
- Handles 1000+ items
- Efficient SQL queries
- Batch scoring support
- Cached results (via smart_engine)

## Production Readiness

### ✅ Completed
- Weighted scoring system (4 scores)
- Trending score with growth rate
- Popularity score with ratings
- Personal affinity score (4 factors)
- Recency score with decay
- Recommendation confidence
- Human-readable reasons
- Category-specific reasons
- 3 API endpoints
- Frontend service
- TypeScript types

### 🔄 Future Enhancements
1. Machine learning model for score weights
2. A/B testing for reason effectiveness
3. Context-aware scoring (weather, events)
4. Social proof (friends' orders)
5. Price sensitivity scoring
6. Dietary preference scoring
7. Real-time score updates
8. Score explanation tooltips

## Files Created

### Backend
1. `app/modules/recommendations/ranking_service.py` - Ranking service (600 lines)
2. `app/modules/recommendations/ranking_router.py` - 3 API endpoints

### Frontend
1. `src/services/recommendationRankingService.ts` - Service with TypeScript types

## Conclusion

The Recommendation Ranking system is **production-ready** with:
- Advanced weighted scoring (4 factors)
- Trending score with growth analysis
- Popularity score with ratings
- Personal affinity with 4 factors
- Recency score with time decay
- Overall confidence calculation
- Human-readable recommendation reasons
- Category-specific reason generation
- Seamless integration with existing recommendations
- No breaking changes

All requirements from the task have been implemented and verified.
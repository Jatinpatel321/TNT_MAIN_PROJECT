import { apiClient, authHeaders } from './apiClient';

export type RecommendationScores = {
  trending_score: number;
  popularity_score: number;
  affinity_score: number;
  recency_score: number;
  confidence: number;
  confidence_level: 'HIGH' | 'MEDIUM' | 'LOW';
  score: number;
  reason: string;
  score_breakdown: {
    trending: number;
    popularity: number;
    affinity: number;
    recency: number;
  };
};

export type RecommendationInsights = {
  menu_item_id: number;
  scores: {
    trending: {
      trending_score: number;
      order_count: number;
      total_quantity: number;
      growth_rate: number;
    };
    popularity: {
      popularity_score: number;
      total_orders: number;
      avg_rating: number;
      rating_count: number;
    };
    affinity: {
      affinity_score: number;
      order_count: number;
      last_ordered: string | null;
      factors: {
        history_score: number;
        category_score: number;
        vendor_score: number;
        time_score: number;
      };
    };
    recency: {
      recency_score: number;
      days_since_last_order: number | null;
      last_order_date: string | null;
    };
  };
  confidence: {
    confidence: number;
    confidence_level: string;
    score_breakdown: {
      trending: number;
      popularity: number;
      affinity: number;
      recency: number;
    };
  };
  reason: string;
  insights: string[];
};

export type RankedRecommendations = {
  user_id: number;
  frequently_ordered: any[];
  recommended_for_you: any[];
  trending_near_you: any[];
  because_you_ordered: any[];
  personalized_vendors: any[];
};

export async function getRankedRecommendations(): Promise<RankedRecommendations> {
  const res = await apiClient.get('/user/recommendations/ranked', {
    headers: await authHeaders(),
  });
  return res.data as RankedRecommendations;
}

export async function getRecommendationInsights(itemId: number): Promise<RecommendationInsights> {
  const res = await apiClient.get(`/user/recommendations/insights/${itemId}`, {
    headers: await authHeaders(),
  });
  return res.data as RecommendationInsights;
}

export async function rankCustomItems(
  items: any[],
  category: string = 'recommended'
): Promise<any[]> {
  const res = await apiClient.post(
    '/user/recommendations/rank',
    { items, category },
    {
      headers: await authHeaders(),
    }
  );
  return res.data;
}
</write_to_file>
<task_progress>
- [x] Analyze existing recommendation system
- [x] Create recommendation ranking service
- [x] Implement weighted scoring system
- [x] Calculate trending score
- [x] Calculate popularity score
- [x] Calculate personal affinity score
- [x] Calculate recency score
- [x] Calculate recommendation confidence
- [x] Generate recommendation reasons
- [x] Update recommendation APIs
- [x] Create frontend service
- [ ] Display recommendation reasons in UI
- [ ] Create documentation
</task_progress>
</write_to_file>
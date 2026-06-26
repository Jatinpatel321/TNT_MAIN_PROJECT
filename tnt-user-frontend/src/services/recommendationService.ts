import { apiClient, authHeaders } from './apiClient';

export type RecommendationItem = {
  id?: number | null;
  vendor_id?: number | null;
  name: string;
  price?: number | null;
  image_url?: string | null;
  reason?: string | null;
  score?: number | null;
  is_available?: boolean | null;
  pairs_with?: string[] | null;
};

export type RecommendationsResponse = {
  user_id: number;
  recommended_items: RecommendationItem[];
  trending_items: RecommendationItem[];
  popular_items: RecommendationItem[];
  top_recommended: RecommendationItem[];
  personalized_items: RecommendationItem[];
};

export type VendorRecommendationItem = {
  vendor_id: number;
  vendor_name: string;
  vendor_type: string;
  category: string | null;
  logo_url: string | null;
  rank_score: number;
  live_load: string;
  express_pickup: boolean;
  reason: string;
};

export type VendorRecommendationsResponse = {
  recommendations: VendorRecommendationItem[];
};

export type MenuSuggestionItem = {
  item_id: number;
  item_name: string;
  vendor_id: number;
  vendor_name: string;
  price_paise: number;
  image_url: string | null;
  is_available: boolean;
  reason: string;
  confidence: number;
};

export type MenuSuggestionsResponse = {
  personalized: MenuSuggestionItem[];
  trending: MenuSuggestionItem[];
};

export type SmartReorderItem = {
  item_id: number;
  item_name: string;
  vendor_id: number;
  vendor_name: string;
  price_paise: number;
  image_url: string | null;
  order_count: number;
  last_ordered_at: string;
  suggested_quantity: number;
  suggested_slot_id: number | null;
  suggested_slot_time: string | null;
};

export type SmartReorderResponse = {
  items: SmartReorderItem[];
  best_reorder_time: string;
  best_reorder_slot_id: number | null;
};

export type PickupTimeSlot = {
  slot_id: number;
  vendor_id: number;
  vendor_name: string;
  start_time: string;
  end_time: string;
  eta_minutes: number;
  congestion_level: string;
  delay_risk: string;
  score: number;
};

export type BestPickupTimeResponse = {
  best_slot: PickupTimeSlot | null;
  alternative_slots: PickupTimeSlot[];
  preferred_hour: number;
  preferred_hour_source: string;
};

export type PeakHourPeriod = {
  start_hour: number;
  end_hour: number;
  label: string;
  severity: string;
  avg_wait_minutes: number;
  order_volume: number;
};

export type PeakHourAlertData = {
  is_peak_now: boolean;
  current_period: PeakHourPeriod | null;
  peak_periods_today: PeakHourPeriod[];
  off_peak_windows: { hour: number; label: string; expected_wait_minutes: number }[];
  suggested_action: string;
};

export type PopularNearbyVendor = {
  vendor_id: number;
  vendor_name: string;
  vendor_type: string;
  category: string | null;
  logo_url: string | null;
  order_count: number;
  avg_rating: number;
  live_load: string;
};

export type PopularNearbyResponse = {
  food_vendors: PopularNearbyVendor[];
  stationery_vendors: PopularNearbyVendor[];
};

// ── New Smart Recommendation Types (v2) ─────────────────────────────────

export type SmartRecommendationItem = {
  id: number;
  name: string;
  description: string;
  price: number;
  image_url: string | null;
  vendor_id: number;
  is_available: boolean;
  reason: string;
  score: number;
  order_count?: number;
  co_occurrence?: number;
  pairs_with?: string[] | null;
};

export type SmartVendorItem = {
  vendor_id: number;
  vendor_name: string;
  vendor_type: string;
  logo_url: string | null;
  rank_score: number;
  live_load: string;
  express_pickup: boolean;
  reason: string;
};

export type SmartMenuItem = {
  item_id: number;
  item_name: string;
  description: string;
  price_paise: number;
  vendor_id: number;
  image_url: string | null;
  is_available: boolean;
  reason: string;
  confidence: number;
  ordered_before: boolean;
};

export type SmartRecommendationsResponse = {
  user_id: number;
  frequently_ordered: SmartRecommendationItem[];
  recommended_for_you: SmartRecommendationItem[];
  trending_near_you: SmartRecommendationItem[];
  because_you_ordered: SmartRecommendationItem[];
  personalized_vendors: SmartVendorItem[];
};

// ── Existing API calls ──────────────────────────────────────────────────

export async function getRecommendations(userId: number): Promise<RecommendationsResponse> {
  const res = await apiClient.get(`/recommendations/${userId}`);
  return res.data as RecommendationsResponse;
}

export async function getVendorRecommendations(): Promise<VendorRecommendationsResponse> {
  const res = await apiClient.get('/ai/vendor-recommendations', {
    headers: await authHeaders(),
  });
  return res.data as VendorRecommendationsResponse;
}

export async function getMenuSuggestions(): Promise<MenuSuggestionsResponse> {
  const res = await apiClient.get('/ai/menu-suggestions', {
    headers: await authHeaders(),
  });
  return res.data as MenuSuggestionsResponse;
}

export async function getSmartReorder(): Promise<SmartReorderResponse> {
  const res = await apiClient.get('/ai/smart-reorder', {
    headers: await authHeaders(),
  });
  return res.data as SmartReorderResponse;
}

export async function getBestPickupTime(): Promise<BestPickupTimeResponse> {
  const res = await apiClient.get('/ai/best-pickup-time', {
    headers: await authHeaders(),
  });
  return res.data as BestPickupTimeResponse;
}

export async function getPeakHourAlerts(): Promise<PeakHourAlertData> {
  const res = await apiClient.get('/ai/peak-hour-alerts', {
    headers: await authHeaders(),
  });
  return res.data as PeakHourAlertData;
}

export async function getPopularNearby(): Promise<PopularNearbyResponse> {
  const res = await apiClient.get('/ai/popular-nearby', {
    headers: await authHeaders(),
  });
  return res.data as PopularNearbyResponse;
}

// ── New Smart Recommendation API Calls (v2) ─────────────────────────────

export async function getSmartRecommendations(): Promise<SmartRecommendationsResponse> {
  const res = await apiClient.get('/v1/user/recommendations', {
    headers: await authHeaders(),
  });
  return res.data as SmartRecommendationsResponse;
}

export async function getPersonalizedVendors(limit: number = 10): Promise<SmartVendorItem[]> {
  const res = await apiClient.get(`/v1/user/personalized-vendors?limit=${limit}`, {
    headers: await authHeaders(),
  });
  return res.data as SmartVendorItem[];
}

export async function getPersonalizedMenu(vendorId?: number, limit: number = 10): Promise<SmartMenuItem[]> {
  let url = `/v1/user/personalized-menu?limit=${limit}`;
  if (vendorId) url += `&vendor_id=${vendorId}`;
  const res = await apiClient.get(url, {
    headers: await authHeaders(),
  });
  return res.data as SmartMenuItem[];
}

export async function recordInteraction(
  eventType: string,
  vendorId?: number,
  menuItemId?: number,
): Promise<{ recorded: boolean; event_type: string }> {
  let url = `/v1/user/interactions?event_type=${eventType}`;
  if (vendorId) url += `&vendor_id=${vendorId}`;
  if (menuItemId) url += `&menu_item_id=${menuItemId}`;
  const res = await apiClient.post(url, null, {
    headers: await authHeaders(),
  });
  return res.data as { recorded: boolean; event_type: string };
}

// ── Prediction API Types ──────────────────────────────────────────────────

export type PredictionItem = {
  item_id: number;
  item_name: string;
  vendor_id: number;
  price: number;
  image_url: string | null;
  is_available: boolean;
  reason: string;
};

export type SuggestedReorderResponse = {
  suggested_items: PredictionItem[];
  suggested_time: string;
  preferred_hour: number;
  preferred_day: number;
  confidence: number;
  reasoning: string;
  patterns: {
    weekly: {
      day_distribution: Record<number, number>;
      preferred_days: number[];
      weekly_pattern: string;
    };
    daily: {
      hour_distribution: Record<number, number>;
      preferred_hour: number;
      daily_pattern: string;
    };
    semester: {
      phase: string;
      semester: number;
      order_frequency_change: number;
      preferred_items_this_phase: string[];
    };
  };
};

export type PredictionInsightsResponse = {
  weekly_patterns: {
    day_distribution: Record<number, number>;
    preferred_days: number[];
    weekly_pattern: string;
  };
  daily_patterns: {
    hour_distribution: Record<number, number>;
    preferred_hour: number;
    daily_pattern: string;
  };
  semester_patterns: {
    phase: string;
    semester: number;
    order_frequency_change: number;
    preferred_items_this_phase: string[];
  };
  favourite_vendors: Array<{
    vendor_id: number;
    vendor_name: string;
    vendor_type: string;
    order_count: number;
    confidence: number;
    last_order: string | null;
  }>;
  favourite_foods: Array<{
    item_id: number;
    name: string;
    category: string;
    order_count: number;
    total_quantity: number;
    confidence: number;
  }>;
  favourite_stationery: Array<{
    item_id: number;
    name: string;
    category: string;
    order_count: number;
    total_quantity: number;
    confidence: number;
  }>;
  prediction_accuracy: {
    total_predictions: number;
    correct_predictions: number;
    accuracy: number;
    by_type: Record<string, { total: number; correct: number; accuracy: number }>;
  };
  next_order_prediction: {
    predicted_vendor_id: number | null;
    predicted_menu_item_id: number | null;
    predicted_menu_item_name: string | null;
    predicted_hour: number;
    predicted_day_of_week: number;
    confidence_score: number;
    reasoning: string;
    patterns: {
      weekly: any;
      daily: any;
      semester: any;
    };
  };
};

// ── Prediction API Calls ──────────────────────────────────────────────────

export async function getSuggestedReorder(): Promise<SuggestedReorderResponse> {
  const res = await apiClient.get('/v1/user/predictions/reorder', {
    headers: await authHeaders(),
  });
  return res.data as SuggestedReorderResponse;
}

export async function getPredictionInsights(): Promise<PredictionInsightsResponse> {
  const res = await apiClient.get('/v1/user/predictions/insights', {
    headers: await authHeaders(),
  });
  return res.data as PredictionInsightsResponse;
}

export async function getPredictionAccuracy(days: number = 30): Promise<{
  total_predictions: number;
  correct_predictions: number;
  accuracy: number;
  by_type: Record<string, { total: number; correct: number; accuracy: number }>;
}> {
  const res = await apiClient.get(`/v1/user/predictions/accuracy?days=${days}`, {
    headers: await authHeaders(),
  });
  return res.data;
}

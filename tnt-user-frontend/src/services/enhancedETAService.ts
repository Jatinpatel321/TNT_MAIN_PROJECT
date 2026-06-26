import { apiClient, authHeaders } from './apiClient';

export type EnhancedETAResponse = {
  order_id: number;
  predicted_eta_minutes: number;
  estimated_ready_at: string;
  delay_risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  confidence: number;
  factors: {
    base_eta: number;
    complexity_factor: number;
    workload_factor: number;
    occupancy_factor: number;
    avg_complexity: number;
    vendor_workload: {
      active_orders: number;
      avg_prep_time: number;
      completion_rate: number;
      workload_score: number;
      estimated_capacity: number;
    };
    slot_occupancy: {
      current_orders: number;
      max_capacity: number;
      utilization: number;
      time_factor: number;
      congestion_level: string;
    };
  };
  preparation_progress: {
    total_minutes: number;
    milestones: {
      started_at: string;
      quarter_at: string;
      halfway_at: string;
      final_at: string;
      ready_at: string;
    };
    current_phase: string;
  };
  delay_prediction: {
    delay_probability: number;
    expected_delay_minutes: number;
    risk_factors: string[];
    recommendations: string[];
  };
};

export type ETAFactorsResponse = {
  order_id: number;
  base_prediction: {
    predicted_eta_minutes: number;
    pickup_window_start: string;
    pickup_window_end: string;
    delay_risk_level: string;
  };
  menu_items: Array<{
    menu_item_id: number;
    quantity: number;
    prep_time: {
      avg_prep_time: number | null;
      min_prep_time: number | null;
      max_prep_time: number | null;
      sample_size: number;
      confidence: number;
    };
    complexity: {
      complexity_score: number;
      factors: Record<string, number>;
    };
  }>;
  vendor_workload: {
    active_orders: number;
    avg_prep_time: number;
    completion_rate: number;
    workload_score: number;
    estimated_capacity: number;
  };
  slot_occupancy: {
    current_orders: number;
    max_capacity: number;
    utilization: number;
    time_factor: number;
    congestion_level: string;
  };
  time_factors: {
    current_hour: number;
    peak_hours: string[];
    time_multiplier: number;
  };
};

export async function getEnhancedETA(orderId: number): Promise<EnhancedETAResponse> {
  const res = await apiClient.get(`/ai/enhanced-eta/${orderId}`, {
    headers: await authHeaders(),
  });
  return res.data as EnhancedETAResponse;
}

export async function getETAFactors(orderId: number): Promise<ETAFactorsResponse> {
  const res = await apiClient.get(`/ai/eta-factors/${orderId}`, {
    headers: await authHeaders(),
  });
  return res.data as ETAFactorsResponse;
}
</write_to_file>
<task_progress>
- [x] Find existing ETA implementation
- [x] Analyze current ETA engine
- [x] Enhance ETA prediction with ML
- [x] Add historical preparation times
- [x] Add vendor workload analysis
- [x] Add slot occupancy tracking
- [x] Add menu complexity scoring
- [x] Implement delay prediction
- [x] Create preparation progress tracking
- [x] Extend existing ETA APIs
- [x] Build frontend ETA components
- [x] Create frontend service
- [x] Create documentation
</task_progress>
</write_to_file>
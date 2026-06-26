import { apiClient, authHeaders } from './apiClient';

export type VendorSpeedMetrics = {
  vendor_id: number;
  speed_score: number;
  speed_label: 'FAST' | 'NORMAL' | 'BUSY' | 'VERY_BUSY';
  predicted_waiting_time: number;
  suggested_delay: {
    should_delay: boolean;
    suggested_delay_minutes: number;
    optimal_order_time: string;
    reason: string;
    current_workload: string;
    queue_depth: number;
  };
  measurements: {
    preparation_time: {
      avg_prep_time: number;
      min_prep_time: number;
      max_prep_time: number;
      median_prep_time: number;
      sample_size: number;
      std_deviation: number;
      confidence: number;
    };
    queue: {
      active_orders: number;
      pending_orders: number;
      preparing_orders: number;
      confirmed_orders: number;
      queue_depth: number;
      avg_items_per_order: number;
    };
    completion_rate: {
      total_orders: number;
      completed_orders: number;
      cancelled_orders: number;
      completion_rate: number;
      cancellation_rate: number;
      avg_completion_time: number;
    };
    workload: {
      active_orders: number;
      max_capacity: number;
      utilization: number;
      estimated_capacity: number;
      workload_level: string;
    };
  };
  factors: {
    prep_time_score: number;
    completion_score: number;
    queue_score: number;
    workload_score: number;
  };
  recommendations: string[];
};

export type WaitingTimeResponse = {
  base_wait_time: number;
  queue_wait_time: number;
  workload_multiplier: number;
  total_wait_time: number;
  confidence: number;
};

export type SuggestedDelayResponse = {
  should_delay: boolean;
  suggested_delay_minutes: number;
  optimal_order_time: string;
  reason: string;
  current_workload: string;
  queue_depth: number;
};

export type UpdateETAResponse = {
  order_id: number;
  original_eta: number;
  updated_eta: number;
  speed_label: string;
  adjustment_factor: number;
  speed_score: number;
};

export async function getVendorSpeed(vendorId: number): Promise<VendorSpeedMetrics> {
  const res = await apiClient.get(`/ai/vendor-speed/${vendorId}`, {
    headers: await authHeaders(),
  });
  return res.data as VendorSpeedMetrics;
}

export async function getBatchVendorSpeeds(vendorIds: number[]): Promise<VendorSpeedMetrics[]> {
  const ids = vendorIds.join(',');
  const res = await apiClient.get(`/ai/vendor-speed/batch?vendor_ids=${ids}`, {
    headers: await authHeaders(),
  });
  return res.data as VendorSpeedMetrics[];
}

export async function getWaitingTime(
  vendorId: number,
  orderSize: number = 1
): Promise<WaitingTimeResponse> {
  const res = await apiClient.get(
    `/ai/vendor-speed/waiting-time/${vendorId}?order_size=${orderSize}`,
    {
      headers: await authHeaders(),
    }
  );
  return res.data as WaitingTimeResponse;
}

export async function getSuggestedDelay(vendorId: number): Promise<SuggestedDelayResponse> {
  const res = await apiClient.get(`/ai/vendor-speed/suggested-delay/${vendorId}`, {
    headers: await authHeaders(),
  });
  return res.data as SuggestedDelayResponse;
}

export async function updateETAWithSpeed(orderId: number): Promise<UpdateETAResponse> {
  const res = await apiClient.post(`/ai/vendor-speed/update-eta/${orderId}`, null, {
    headers: await authHeaders(),
  });
  return res.data as UpdateETAResponse;
}
</write_to_file>
<task_progress>
- [x] Create vendor_speed_service backend
- [x] Create vendor speed API endpoints
- [x] Create frontend service
- [ ] Display vendor speed in UI
- [ ] Integrate with existing order APIs
- [ ] Create documentation
</task_progress>
</write_to_file>
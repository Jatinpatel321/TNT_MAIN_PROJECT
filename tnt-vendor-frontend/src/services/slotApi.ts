import apiClient from './apiClient';

export interface Slot {
  id: number;
  vendor_id: number;
  start_time: string;
  end_time: string;
  max_orders: number;
  current_orders: number;
  status: string;
  load_label: string;
  express_pickup_eligible: boolean;
  is_locked: boolean;
  available_capacity: number;
  faculty_priority: boolean;
  queue_size: number;
  estimated_wait: number;
  is_ai_recommended: boolean;
}

export interface SlotCreate {
  start_time: string;
  end_time: string;
  max_orders: number;
}

export interface SlotUpdate {
  start_time?: string;
  end_time?: string;
  max_orders?: number;
  status?: string;
}

export interface BulkSlotCreate {
  start_date: string;
  end_date: string;
  start_time: string;
  end_time: string;
  slot_duration_minutes: number;
  max_orders: number;
  days_of_week: number[];
}

export interface SlotAnalytics {
  total_slots: number;
  active_slots: number;
  blocked_slots: number;
  total_bookings: number;
  avg_bookings_per_slot: number;
  peak_hours: { hour: number; bookings: number }[];
  utilization_rate: number;
}

export interface CapacityRule {
  id: number;
  vendor_id: number;
  rule_type: string;
  rule_config: {
    day_of_week?: number;
    hour_of_day?: number;
    max_capacity?: number;
    duration_minutes?: number;
  };
  is_enabled: boolean;
  priority: number;
  created_at: string;
  updated_at: string;
}

export interface SlotRule {
  id: number;
  vendor_id: number;
  rule_type: string;
  rule_config: {
    auto_block_enabled?: boolean;
    block_threshold?: number;
    peak_hours?: { start: string; end: string; multiplier: number };
    faculty_priority_hours?: { start: number; end: number };
  };
  is_enabled: boolean;
  priority: number;
  created_at: string;
  updated_at: string;
}

export const slotApi = {
  getSlots: (vendorId?: number) =>
    apiClient.get<Slot[]>(`/v1/slots/`, { params: { vendor_id: vendorId } }),

  createSlot: (data: SlotCreate) =>
    apiClient.post<Slot>(`/v1/slots/`, data),

  updateSlot: (slotId: number, data: SlotUpdate) =>
    apiClient.put<Slot>(`/v1/slots/${slotId}`, data),

  deleteSlot: (slotId: number) =>
    apiClient.delete(`/v1/slots/${slotId}`),

  bulkCreateSlots: (data: BulkSlotCreate) =>
    apiClient.post<Slot[]>(`/v1/slots/bulk-create`, data),

  lockSlot: (slotId: number) =>
    apiClient.post(`/v1/slots/${slotId}/lock`),

  unlockSlot: (slotId: number) =>
    apiClient.post(`/v1/slots/${slotId}/unlock`),

  getAnalytics: () =>
    apiClient.get<SlotAnalytics>(`/v1/slots/analytics`),

  getCapacityRules: () =>
    apiClient.get<CapacityRule[]>(`/v1/slots/capacity-rules`),

  createCapacityRule: (data: any) =>
    apiClient.post<CapacityRule>(`/v1/slots/capacity-rules`, data),

  updateCapacityRule: (ruleId: number, data: any) =>
    apiClient.put<CapacityRule>(`/v1/slots/capacity-rules/${ruleId}`, data),

  deleteCapacityRule: (ruleId: number) =>
    apiClient.delete(`/v1/slots/capacity-rules/${ruleId}`),

  getRules: () =>
    apiClient.get<SlotRule[]>(`/v1/slots/rules`),

  createRule: (data: any) =>
    apiClient.post<SlotRule>(`/v1/slots/rules`, data),

  updateRule: (ruleId: number, data: any) =>
    apiClient.put<SlotRule>(`/v1/slots/rules/${ruleId}`, data),

  deleteRule: (ruleId: number) =>
    apiClient.delete(`/v1/slots/rules/${ruleId}`),

  // Apply AI dynamic slot-capacity adjustments for the authenticated vendor.
  applyAiSlotAdjustment: () =>
    apiClient.post<SlotAdjustmentResult>(`/v1/ai/apply-slot-adjustment`),
};

export interface SlotAdjustment {
  type: string;
  slot_id: number;
  previous_capacity: number;
  new_capacity: number;
  action: string;
}

export interface SlotAdjustmentResult {
  vendor_id: number;
  recommended_capacity: number;
  reasoning: string;
  signals_evaluated: number;
  adjustments_applied: number;
  adjustments: SlotAdjustment[];
}

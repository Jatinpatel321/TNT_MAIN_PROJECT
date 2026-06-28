import axios from 'axios';

const API_BASE_URL = 'http://localhost:8001';

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
    axios.get<Slot[]>(`${API_BASE_URL}/v1/slots/`, { params: { vendor_id: vendorId } }),

  createSlot: (data: SlotCreate) =>
    axios.post<Slot>(`${API_BASE_URL}/v1/slots/`, data),

  updateSlot: (slotId: number, data: SlotUpdate) =>
    axios.put<Slot>(`${API_BASE_URL}/v1/slots/${slotId}`, data),

  deleteSlot: (slotId: number) =>
    axios.delete(`${API_BASE_URL}/v1/slots/${slotId}`),

  bulkCreateSlots: (data: BulkSlotCreate) =>
    axios.post<Slot[]>(`${API_BASE_URL}/v1/slots/bulk-create`, data),

  lockSlot: (slotId: number) =>
    axios.post(`${API_BASE_URL}/v1/slots/${slotId}/lock`),

  unlockSlot: (slotId: number) =>
    axios.post(`${API_BASE_URL}/v1/slots/${slotId}/unlock`),

  getAnalytics: () =>
    axios.get<SlotAnalytics>(`${API_BASE_URL}/v1/slots/analytics`),

  getCapacityRules: () =>
    axios.get<CapacityRule[]>(`${API_BASE_URL}/v1/slots/capacity-rules`),

  createCapacityRule: (data: any) =>
    axios.post<CapacityRule>(`${API_BASE_URL}/v1/slots/capacity-rules`, data),

  updateCapacityRule: (ruleId: number, data: any) =>
    axios.put<CapacityRule>(`${API_BASE_URL}/v1/slots/capacity-rules/${ruleId}`, data),

  deleteCapacityRule: (ruleId: number) =>
    axios.delete(`${API_BASE_URL}/v1/slots/capacity-rules/${ruleId}`),

  getRules: () =>
    axios.get<SlotRule[]>(`${API_BASE_URL}/v1/slots/rules`),

  createRule: (data: any) =>
    axios.post<SlotRule>(`${API_BASE_URL}/v1/slots/rules`, data),

  updateRule: (ruleId: number, data: any) =>
    axios.put<SlotRule>(`${API_BASE_URL}/v1/slots/rules/${ruleId}`, data),

  deleteRule: (ruleId: number) =>
    axios.delete(`${API_BASE_URL}/v1/slots/rules/${ruleId}`),
};
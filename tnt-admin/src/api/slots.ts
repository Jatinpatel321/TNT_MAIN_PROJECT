import api from './axios';

export interface Slot {
  id: number;
  vendor_id: number;
  start_time: string;
  end_time: string;
  max_orders: number;
  current_orders: number;
  status: 'available' | 'limited' | 'full' | 'blocked';
  load_label: string;
  express_pickup_eligible: boolean;
  is_locked: boolean;
  available_capacity: number;
  faculty_priority: boolean;
  queue_size: number;
  estimated_wait: number;
  is_ai_recommended: boolean;
  slot_duration_minutes?: number;
  is_peak_hour: boolean;
  is_faculty_priority: boolean;
  auto_block_enabled: boolean;
  dynamic_capacity?: number;
  capacity_notes?: string;
}

export interface SlotCreate {
  start_time: string;
  end_time: string;
  max_orders: number;
  slot_duration_minutes?: number;
  is_peak_hour?: boolean;
  is_faculty_priority?: boolean;
  auto_block_enabled?: boolean;
  dynamic_capacity?: number;
  capacity_notes?: string;
}

export interface SlotUpdate {
  max_orders?: number;
  status?: string;
  is_locked?: boolean;
  slot_duration_minutes?: number;
  is_peak_hour?: boolean;
  is_faculty_priority?: boolean;
  auto_block_enabled?: boolean;
  dynamic_capacity?: number;
  capacity_notes?: string;
}

export interface BulkSlotCreate {
  vendor_id: number;
  start_date: string;
  end_date: string;
  interval_minutes?: number;
  max_orders?: number;
  slot_duration_minutes?: number;
  is_peak_hour?: boolean;
  is_faculty_priority?: boolean;
  auto_block_enabled?: boolean;
}

export interface SlotCapacityRule {
  id: number;
  vendor_id: number;
  rule_name: string;
  day_of_week?: number;
  start_hour: number;
  end_hour: number;
  base_capacity: number;
  peak_capacity?: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SlotRule {
  id: number;
  vendor_id: number;
  rule_type: string;
  rule_config: Record<string, any>;
  is_enabled: boolean;
  priority: number;
  created_at: string;
  updated_at: string;
}

export interface SlotAnalytics {
  total_slots: number;
  available_slots: number;
  limited_slots: number;
  full_slots: number;
  blocked_slots: number;
  total_bookings: number;
  avg_utilization: number;
  peak_hour_slots: number;
  faculty_priority_slots: number;
}

export const slotsApi = {
  list: (vendorId?: number) => api.get<Slot[]>('/slots/', { params: { vendor_id: vendorId } }),
  recommend: (vendorId: number) => api.get(`/slots/recommend/${vendorId}`),
  myBookings: (activeOnly = true) => api.get('/slots/my-bookings', { params: { active_only: activeOnly } }),
  create: (data: SlotCreate) => api.post<Slot>('/slots/', data),
  update: (slotId: number, data: SlotUpdate) => api.put<Slot>(`/slots/${slotId}`, data),
  delete: (slotId: number) => api.delete(`/slots/${slotId}`),
  book: (slotId: number, orderId?: number) => api.post(`/slots/${slotId}/book`, { order_id: orderId }),
  cancel: (slotId: number) => api.post(`/slots/${slotId}/cancel`),
  lock: (slotId: number) => api.post(`/slots/${slotId}/lock`),
  unlock: (slotId: number) => api.post(`/slots/${slotId}/unlock`),
  bulkCreate: (data: BulkSlotCreate) => api.post<Slot[]>('/slots/bulk-create', data),
  analytics: () => api.get<SlotAnalytics>('/slots/analytics'),
  
  // Capacity Rules
  createCapacityRule: (data: Omit<SlotCapacityRule, 'id' | 'vendor_id' | 'created_at' | 'updated_at'>) =>
    api.post<SlotCapacityRule>('/slots/capacity-rules', data),
  getCapacityRules: () => api.get<SlotCapacityRule[]>('/slots/capacity-rules'),
  updateCapacityRule: (ruleId: number, data: Partial<SlotCapacityRule>) =>
    api.put<SlotCapacityRule>(`/slots/capacity-rules/${ruleId}`, data),
  deleteCapacityRule: (ruleId: number) => api.delete(`/slots/capacity-rules/${ruleId}`),
  
  // Slot Rules
  createRule: (data: { rule_type: string; rule_config: Record<string, any>; is_enabled?: boolean; priority?: number }) =>
    api.post<SlotRule>('/slots/rules', data),
  getRules: () => api.get<SlotRule[]>('/slots/rules'),
  updateRule: (ruleId: number, data: Partial<SlotRule>) =>
    api.put<SlotRule>(`/slots/rules/${ruleId}`, data),
  deleteRule: (ruleId: number) => api.delete(`/slots/rules/${ruleId}`),
};
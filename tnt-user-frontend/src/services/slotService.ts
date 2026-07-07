import { apiClient } from './apiClient';

export type Slot = {
  id: number;
  vendor_id: number;
  start_time: string;
  end_time: string;
  max_orders: number;
  current_orders: number;
  status?: string;
  load_label?: string;
  express_pickup_eligible?: boolean;
  queue_size?: number;
  estimated_wait?: number;
  is_ai_recommended?: boolean;
  estimated_ready_time?: string | null;
  is_locked?: boolean;
  available_capacity?: number;
  faculty_priority?: boolean;
};

export type SlotBooking = {
  id: number;
  slot_id: number;
  user_id: number;
  order_id: number | null;
  status: 'confirmed' | 'cancelled';
  booked_at: string | null;
  cancelled_at: string | null;
};

export type BookSlotResponse = {
  message: string;
  slot_id: number;
  booking_id: number;
  current_orders: number;
  available_capacity: number;
  status: string;
  load_label: string;
  express_pickup_eligible: boolean;
};

export type CancelSlotResponse = {
  message: string;
  slot_id: number;
  booking_id: number;
  current_orders: number;
  status: string;
};

export async function getSlots(vendorId?: number): Promise<{ estimated_ready_time?: string | null; slots: Slot[] }> {
  if (!vendorId) {
    const res = await apiClient.get('/slots');
    return { slots: res.data as Slot[], estimated_ready_time: undefined };
  }
  const res = await apiClient.get(`/vendors/${vendorId}/slots`);
  return res.data as { estimated_ready_time?: string | null; slots: Slot[] };
}

export async function bookSlot(slotId: number, orderId?: number): Promise<BookSlotResponse> {
  const payload: Record<string, any> = {};
  if (orderId != null) payload.order_id = orderId;
  const res = await apiClient.post(`/slots/${slotId}/book`, payload);
  return res.data as BookSlotResponse;
}

export async function cancelSlotBooking(slotId: number): Promise<CancelSlotResponse> {
  const res = await apiClient.post(`/slots/${slotId}/cancel`);
  return res.data as CancelSlotResponse;
}

export async function getMyBookings(activeOnly = true): Promise<SlotBooking[]> {
  const res = await apiClient.get('/slots/my-bookings', { params: { active_only: activeOnly } });
  return res.data as SlotBooking[];
}

export async function recommendSlot(vendorId: number): Promise<{ recommended_slot: string; estimated_wait: string; reason: string }> {
  const res = await apiClient.get(`/slots/recommend/${vendorId}`);
  return res.data as any;
}

export type CombinedStationeryItem = {
  service_id: number;
  quantity: number;
  file_url?: string | null;
};

export type CombinedFoodItem = {
  menu_item_id: number;
  quantity: number;
};

export type CombinedBookingResponse = {
  message: string;
  order_id: number;
  stationery_job_ids: number[];
  slot_id: number;
  booking_id: number;
  total_amount: number;
  status: string;
};

export async function combinedBooking(payload: {
  slot_id: number;
  food_items: CombinedFoodItem[];
  stationery_items: CombinedStationeryItem[];
}): Promise<CombinedBookingResponse> {
  const res = await apiClient.post('/slots/combined-booking', payload);
  return res.data as CombinedBookingResponse;
}

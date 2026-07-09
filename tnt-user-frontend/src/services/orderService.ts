import {apiClient, authHeaders} from './apiClient';
import type {Order, OrderHistoryItem, OrderStatusKey} from '../types/models';
import {getItem} from '../utils/storage';
import {STORAGE_KEYS} from '../utils/constants';

async function getStoredUserId(): Promise<number | null> {
  try {
    const raw = await getItem(STORAGE_KEYS.user);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as {id?: unknown};
    const id = Number(parsed?.id);
    return Number.isFinite(id) ? id : null;
  } catch {
    return null;
  }
}

export type OrderItemDetail = {
  name: string;
  image_url?: string | null;
  quantity: number;
  price_at_time: number;
  line_total: number;
};

export type OrderDetail = {
  order_id: number;
  status: OrderStatusKey;
  created_at: string;
  items: OrderItemDetail[];
  total_amount: number;
};

export type ReorderResponse = {
  order_id: number;
  status: string;
  total_amount: number;
  estimated_ready_at: string;
  slot_time: string;
  pickup_load_label: string;
  express_pickup_eligible: boolean;
};

export type OrderEtaResponse = {
  order_id: number;
  status: string;
  estimated_ready_at: string;
  is_delayed: boolean;
  delay_minutes: number;
  pickup_load_label: string;
  express_pickup_eligible: boolean;
};

export const ORDER_STATUS_LABELS: Record<string, string> = {
  placed: 'Pending',
  pending: 'Pending',
  confirmed: 'Accepted',
  preparing: 'Preparing',
  ready: 'Ready for Pickup',
  ready_for_pickup: 'Ready for Pickup',
  picked: 'Collected',
  completed: 'Collected',
  cancelled: 'Cancelled',
};

export const ORDER_STATUS_COLORS: Record<string, string> = {
  placed: '#F59E0B',
  pending: '#F59E0B',
  confirmed: '#3B82F6',
  preparing: '#8B5CF6',
  ready: '#10B981',
  ready_for_pickup: '#10B981',
  picked: '#6B7280',
  completed: '#6B7280',
  cancelled: '#EF4444',
};

export function isActiveOrder(status: string): boolean {
  return [
    'placed',
    'pending',
    'confirmed',
    'preparing',
    'ready',
    'ready_for_pickup',
  ].includes(status);
}

export function isTerminalOrder(status: string): boolean {
  return ['picked', 'completed', 'cancelled'].includes(status);
}

export async function getMyOrders(): Promise<Order[]> {
  const userId = await getStoredUserId();
  if (!userId) {
    const res = await apiClient.get('/orders/my', {
      headers: await authHeaders(),
    });
    return res.data as Order[];
  }
  return getOrdersByUserId(userId);
}

export async function getOrdersByUserId(userId: number): Promise<Order[]> {
  const res = await apiClient.get(`/orders/${userId}`, {
    headers: await authHeaders(),
  });
  return res.data as Order[];
}

export type OrderSort = 'newest' | 'oldest' | 'amount_desc' | 'amount_asc';

export type OrdersQuery = {
  limit?: number;
  offset?: number;
  search?: string;
  date_from?: string;
  date_to?: string;
  vendor_id?: number;
  status?: string;
  order_type?: 'food' | 'stationery' | 'combined';
  sort?: OrderSort;
};

export type OrdersPage = {
  total: number;
  limit: number;
  offset: number;
  items: Order[];
};

export async function getOrdersPaged(query: OrdersQuery = {}): Promise<OrdersPage> {
  const params: Record<string, string | number> = {};
  if (query.limit != null) params.limit = query.limit;
  if (query.offset != null) params.offset = query.offset;
  if (query.search) params.search = query.search;
  if (query.date_from) params.date_from = query.date_from;
  if (query.date_to) params.date_to = query.date_to;
  if (query.vendor_id != null) params.vendor_id = query.vendor_id;
  if (query.status) params.status = query.status;
  if (query.order_type) params.order_type = query.order_type;
  if (query.sort) params.sort = query.sort;
  const res = await apiClient.get('/orders/my', { headers: await authHeaders(), params });
  return res.data as OrdersPage;
}

export async function getVendorOrderDetail(
  orderId: number,
): Promise<OrderDetail> {
  const res = await apiClient.get(`/orders/vendor/${orderId}`, {
    headers: await authHeaders(),
  });
  return res.data as OrderDetail;
}

export async function getOrderTimeline(
  orderId: number,
): Promise<OrderHistoryItem[]> {
  const res = await apiClient.get(`/orders/${orderId}/timeline`, {
    headers: await authHeaders(),
  });
  return res.data as OrderHistoryItem[];
}

export async function getOrderEta(orderId: number): Promise<OrderEtaResponse> {
  const res = await apiClient.get(`/orders/${orderId}/eta`, {
    headers: await authHeaders(),
  });
  return res.data as OrderEtaResponse;
}

export type QrResponse = {
  order_id: number;
  qr_code: string;
  expires_at: string | null;
  expires_in_seconds: number | null;
  status: string;
};

export type PickupStatus = {
  order_id: number;
  status: string;
  is_ready_for_pickup: boolean;
  is_picked: boolean;
  can_generate_qr: boolean;
  vendor_id: number;
  vendor_name: string;
  vendor_location: string | null;
  slot: {id: number; start_time: string | null; end_time: string | null} | null;
  eta_minutes: number | null;
  qr_available: boolean;
  qr_expires_at: string | null;
  qr_expires_in_seconds: number | null;
  pickup_confirmed_at: string | null;
  total_amount: number;
};

export async function generateOrderQr(orderId: number): Promise<QrResponse> {
  const res = await apiClient.post(`/orders/${orderId}/qr`, undefined, {
    headers: await authHeaders(),
  });
  return res.data as QrResponse;
}

export async function refreshOrderQr(orderId: number): Promise<QrResponse> {
  const res = await apiClient.post(`/orders/${orderId}/refresh-qr`, undefined, {
    headers: await authHeaders(),
  });
  return res.data as QrResponse;
}

export async function getPickupStatus(orderId: number): Promise<PickupStatus> {
  const res = await apiClient.get(`/orders/${orderId}/pickup-status`, {
    headers: await authHeaders(),
  });
  return res.data as PickupStatus;
}

export async function cancelOrder(orderId: number): Promise<{message: string}> {
  const res = await apiClient.post(`/orders/${orderId}/cancel`, undefined, {
    headers: await authHeaders(),
  });
  return res.data as {message: string};
}

export async function reorderOrder(orderId: number): Promise<ReorderResponse> {
  const res = await apiClient.post(`/orders/${orderId}/reorder`, undefined, {
    headers: await authHeaders(),
  });
  return res.data as ReorderResponse;
}

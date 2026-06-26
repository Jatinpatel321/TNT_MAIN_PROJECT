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

export async function generateOrderQr(
  orderId: number,
): Promise<{qr_code: string}> {
  const res = await apiClient.post(`/orders/${orderId}/qr`, undefined, {
    headers: await authHeaders(),
  });
  return res.data as {qr_code: string};
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

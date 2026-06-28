import { apiClient } from './apiClient';
import type { Cart } from '../types/models';
import { getItem } from '../utils/storage';
import { STORAGE_KEYS } from '../utils/constants';

async function getStoredUserId(): Promise<number | null> {
  try {
    const raw = await getItem(STORAGE_KEYS.user);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { id?: unknown };
    const id = Number(parsed?.id);
    return Number.isFinite(id) ? id : null;
  } catch {
    return null;
  }
}

export async function getCart(): Promise<Cart> {
  const userId = await getStoredUserId();
  const res = userId ? await apiClient.get(`/cart/${userId}`) : await apiClient.get('/cart');
  return res.data as Cart;
}

export async function getCartByUserId(userId: number): Promise<Cart> {
  const res = await apiClient.get(`/cart/${userId}`);
  return res.data as Cart;
}

export async function addCartItem(menu_item_id: number, quantity: number): Promise<Cart> {
  const res = await apiClient.post('/cart/add', { menu_item_id, quantity });
  return res.data as Cart;
}

export async function updateCartItem(menu_item_id: number, quantity: number): Promise<Cart> {
  const res = await apiClient.post('/cart/update', { menu_item_id, quantity });
  return res.data as Cart;
}

export async function removeCartItem(menu_item_id: number): Promise<Cart> {
  const res = await apiClient.post('/cart/remove', { menu_item_id });
  return res.data as Cart;
}

export async function clearCart(): Promise<{ message: string }> {
  const res = await apiClient.delete('/cart');
  return res.data as { message: string };
}

export type CheckoutResponse = {
  order_id: number;
  pickup_token: string;
  status: string;
  total_amount: number;
  eta_minutes: number;
  payment_method: string;
  pickup_load_label: string;
  express_pickup_eligible: boolean;
};

export async function checkout(
  slotId: number,
  paymentMethod?: string,
  voucherCode?: string,
  pointsToRedeem?: number
): Promise<CheckoutResponse> {
  const res = await apiClient.post('/checkout', {
    slot_id: slotId,
    payment_method: paymentMethod ?? 'UPI',
    voucher_code: voucherCode || undefined,
    points_to_redeem: pointsToRedeem || undefined,
  });
  return res.data as CheckoutResponse;
}

export type CheckoutPayResponse = {
  order_created: boolean;
  payment_initiated: boolean;
  order: CheckoutResponse;
  payment: null | {
    payment_id: number;
    razorpay_order_id: string;
    amount: number;
    key: string | null;
    idempotent?: boolean;
  };
  payment_error: null | {
    status_code: number;
    detail: unknown;
  };
};

export async function checkoutAndPay(slotId: number, checkoutIdempotencyKey?: string): Promise<CheckoutPayResponse> {
  const res = await apiClient.post(`/cart/checkout/${slotId}/pay`, null, {
    params: checkoutIdempotencyKey ? { checkout_idempotency_key: checkoutIdempotencyKey } : undefined,
  });
  return res.data as CheckoutPayResponse;
}

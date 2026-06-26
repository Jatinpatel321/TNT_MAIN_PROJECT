import { apiClient } from './apiClient';

export type PaymentMethod = 'UPI' | 'CARD' | 'WALLET';

export interface MockPaymentResult {
  payment_id: number;
  order_id: number;
  status: 'SUCCESS' | 'FAILED';
  method: PaymentMethod;
  amount: number;
  amount_display: string;
  mock_payment_id: string;
  message: string;
}

/**
 * Mock payment gateway – always succeeds in dev mode.
 * @param orderId   The order to pay for.
 * @param method    'UPI' | 'CARD' | 'WALLET'
 * @param amount    Amount in paise (optional – server uses order total if omitted).
 */
export async function mockPayment(
  orderId: number,
  method: PaymentMethod = 'UPI',
  amount?: number,
): Promise<MockPaymentResult> {
  const body: Record<string, unknown> = { order_id: orderId, method };
  if (amount !== undefined) body.amount = amount;
  const { data } = await apiClient.post<MockPaymentResult>('/payments/mock', body);
  return data;
}

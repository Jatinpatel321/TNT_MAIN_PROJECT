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

export interface RazorpayInitiateResult {
  payment_id: number;
  razorpay_order_id: string;
  amount: number;
  key: string;
  idempotent?: boolean;
}

/**
 * Initiate real Razorpay gateway payment for an order.
 */
export async function initiateRazorpayPayment(
  orderId: number,
  idempotencyKey?: string,
): Promise<RazorpayInitiateResult> {
  const headers: Record<string, string> = {};
  if (idempotencyKey) {
    headers['X-Idempotency-Key'] = idempotencyKey;
  }
  const { data } = await apiClient.post<RazorpayInitiateResult>(
    `/payments/razorpay/initiate/${orderId}`,
    null,
    { headers },
  );
  return data;
}

/**
 * Verify Razorpay payment signature after gateway transaction.
 */
export async function verifyRazorpayPayment(
  paymentId: number,
  razorpayPaymentId: string,
  razorpaySignature: string,
): Promise<{ message: string }> {
  const { data } = await apiClient.post<{ message: string }>(
    `/payments/razorpay/verify/${paymentId}`,
    null,
    {
      params: {
        razorpay_payment_id: razorpayPaymentId,
        razorpay_signature: razorpaySignature,
      },
    },
  );
  return data;
}

export type RefundStatus = 'pending' | 'processing' | 'completed';

export interface RefundStatusResult {
  order_id: number;
  has_refund: boolean;
  payment_id?: number;
  amount?: number;
  refund_status?: RefundStatus;
  progress_percent?: number;
  message?: string;
  refunded_at?: string | null;
  estimated_refund_at?: string | null;
  razorpay_refund_id?: string | null;
}

/**
 * Live refund status + AI-estimated completion time for an order's refund.
 * Returns `has_refund: false` when the order has no refunded payment.
 */
export async function getRefundStatus(orderId: number): Promise<RefundStatusResult> {
  const { data } = await apiClient.get<RefundStatusResult>(
    `/payments/refund-status/order/${orderId}`,
  );
  return data;
}

import { apiClient, authHeaders } from './apiClient';

export type PaymentSplit = {
  user_id: number;
  user_name: string;
  amount: number;
  percentage: number;
  split_type: string;
};

export type PaymentStatus = {
  group_id: number;
  total_amount: number;
  total_paid: number;
  total_pending: number;
  payment_percentage: number;
  members: Array<{
    user_id: number;
    user_name: string;
    role: string;
    amount: number;
    amount_paid: number;
    amount_due: number;
    percentage: number;
    payment_status: string;
    payment_method: string | null;
    paid_at: string | null;
    razorpay_payment_id: string | null;
  }>;
  unpaid_members: Array<{
    user_id: number;
    user_name: string;
    amount_due: number;
    payment_status: string;
  }>;
  unpaid_count: number;
  is_fully_paid: boolean;
};

export type ContributionSummary = {
  group_id: number;
  contributions: any[];
  payment_methods: Record<string, number>;
  timeline: any[];
  statistics: {
    total_members: number;
    paid_members: number;
    partial_members: number;
    pending_members: number;
    avg_payment_amount: number;
    completion_rate: number;
  };
};

export type OutstandingPayments = {
  group_id: number;
  outstanding: any[];
  total_outstanding: number;
  outstanding_count: number;
  reminders_sent: boolean;
  suggested_actions: string[];
  is_fully_paid: boolean;
};

export type PaymentSummary = {
  group_id: number;
  payment_status: PaymentStatus;
  contribution_summary: ContributionSummary;
  outstanding_payments: OutstandingPayments;
  is_fully_paid: boolean;
};

export async function getPaymentSummary(groupId: number): Promise<PaymentSummary> {
  const res = await apiClient.get(`/groups/${groupId}/payments/summary`, {
    headers: await authHeaders(),
  });
  return res.data as PaymentSummary;
}

export async function getPaymentStatus(groupId: number): Promise<PaymentStatus> {
  const res = await apiClient.get(`/groups/${groupId}/payments/status`, {
    headers: await authHeaders(),
  });
  return res.data as PaymentStatus;
}

export async function getContributionSummary(groupId: number): Promise<ContributionSummary> {
  const res = await apiClient.get(`/groups/${groupId}/payments/contributions`, {
    headers: await authHeaders(),
  });
  return res.data as ContributionSummary;
}

export async function getOutstandingPayments(groupId: number): Promise<OutstandingPayments> {
  const res = await apiClient.get(`/groups/${groupId}/payments/outstanding`, {
    headers: await authHeaders(),
  });
  return res.data as OutstandingPayments;
}

export async function calculatePaymentSplit(
  groupId: number,
  splitType: 'EQUAL' | 'CUSTOM' | 'PERCENTAGE',
  totalAmount: number,
  customSplits?: Record<number, number>
): Promise<{ splits: PaymentSplit[]; total_amount: number; split_type: string }> {
  const res = await apiClient.post(
    `/groups/${groupId}/payments/calculate`,
    {
      split_type: splitType,
      total_amount: totalAmount,
      custom_splits: customSplits,
    },
    {
      headers: await authHeaders(),
    }
  );
  return res.data;
}

export async function recordPayment(
  groupId: number,
  userId: number,
  amount: number,
  paymentMethod: string,
  razorpayPaymentId?: string
): Promise<any> {
  const res = await apiClient.post(
    `/groups/${groupId}/payments/record`,
    {
      user_id: userId,
      amount,
      payment_method: paymentMethod,
      razorpay_payment_id: razorpayPaymentId,
    },
    {
      headers: await authHeaders(),
    }
  );
  return res.data;
}

export async function sendPaymentReminder(
  groupId: number,
  userId?: number
): Promise<{ sent: boolean; reminder_count: number }> {
  const url = userId
    ? `/groups/${groupId}/payments/remind?user_id=${userId}`
    : `/groups/${groupId}/payments/remind`;
  
  const res = await apiClient.post(url, null, {
    headers: await authHeaders(),
  });
  return res.data;
}

export async function createRazorpayOrder(
  groupId: number,
  userId: number,
  amount: number
): Promise<{
  group_id: number;
  user_id: number;
  razorpay_order_id: string;
  amount: number;
  currency: string;
  receipt: string;
}> {
  const res = await apiClient.post(
    `/groups/${groupId}/payments/razorpay-order`,
    { user_id: userId, amount },
    {
      headers: await authHeaders(),
    }
  );
  return res.data;
}

export async function verifyRazorpayPayment(
  groupId: number,
  userId: number,
  razorpayPaymentId: string,
  razorpaySignature: string
): Promise<any> {
  const res = await apiClient.post(
    `/groups/${groupId}/payments/verify`,
    {
      user_id: userId,
      razorpay_payment_id: razorpayPaymentId,
      razorpay_signature: razorpaySignature,
    },
    {
      headers: await authHeaders(),
    }
  );
  return res.data;
}
</write_to_file>
<task_progress>
- [x] Explore existing group cart and payment implementation
- [x] Create payment service backend
- [x] Create payment split APIs
- [x] Create frontend service
- [ ] Build split payment screen
- [ ] Create contribution summary component
- [ ] Create outstanding payments component
- [ ] Integrate with Razorpay
- [ ] Create documentation
</task_progress>
</write_to_file>
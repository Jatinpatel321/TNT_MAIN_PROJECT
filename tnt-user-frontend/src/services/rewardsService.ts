import { apiClient, authHeaders } from './apiClient';

export type RewardTypeKey =
  | 'order_completion'
  | 'referral'
  | 'first_order'
  | 'loyalty_milestone'
  | 'off_peak_bonus'
  | 'voucher_redemption';

export type RedemptionTypeKey =
  | 'discount_percentage'
  | 'discount_fixed'
  | 'free_item';

export type RewardTransaction = {
  id: number;
  reward_type: RewardTypeKey;
  points: number;
  description: string;
  order_id: number | null;
  created_at: string;
};

export type RewardRedemption = {
  id: number;
  redemption_type: RedemptionTypeKey;
  points_used: number;
  value: number;
  description: string;
  order_id: number | null;
  created_at: string;
};

export type UserPoints = {
  current_points: number;
  total_earned: number;
  total_redeemed: number;
  recent_transactions: RewardTransaction[];
  recent_redemptions: RewardRedemption[];
};

export type RedemptionRule = {
  id: number;
  redemption_type: RedemptionTypeKey;
  min_points: number;
  max_discount_percentage: number | null;
  max_discount_amount: number | null;
};

export type Voucher = {
  id: number;
  code: string;
  description: string;
  discount_type: 'percentage' | 'fixed';
  discount_value: number;
  min_order_amount_paise: number;
  max_discount_amount_paise: number | null;
  usage_limit: number | null;
  times_redeemed: number;
  expires_at: string;
  is_active: boolean;
};

export async function getPoints(): Promise<UserPoints> {
  const res = await apiClient.get('/rewards/points', {
    headers: await authHeaders(),
  });
  return res.data as UserPoints;
}

export async function getTransactionHistory(
  limit = 50,
  offset = 0,
): Promise<RewardTransaction[]> {
  const res = await apiClient.get('/rewards/transactions', {
    params: { limit, offset },
    headers: await authHeaders(),
  });
  return res.data as RewardTransaction[];
}

export async function getRedemptionHistory(
  limit = 50,
  offset = 0,
): Promise<RewardRedemption[]> {
  const res = await apiClient.get('/rewards/redemptions/history', {
    params: { limit, offset },
    headers: await authHeaders(),
  });
  return res.data as RewardRedemption[];
}

export async function getAvailableRedemptions(): Promise<RedemptionRule[]> {
  const res = await apiClient.get('/rewards/redemptions', {
    headers: await authHeaders(),
  });
  return res.data as RedemptionRule[];
}

export async function redeemPoints(
  redemptionType: RedemptionTypeKey,
  pointsUsed: number,
  value: number,
  orderId?: number,
): Promise<{ message: string; redemption_id: number }> {
  const res = await apiClient.post(
    '/rewards/redeem',
    {
      redemption_type: redemptionType,
      points_used: pointsUsed,
      value,
      order_id: orderId,
    },
    { headers: await authHeaders() },
  );
  return res.data as { message: string; redemption_id: number };
}

export async function getVouchers(): Promise<Voucher[]> {
  const res = await apiClient.get('/rewards/vouchers', {
    headers: await authHeaders(),
  });
  return res.data as Voucher[];
}

export async function redeemVoucher(
  code: string,
  orderId: number,
): Promise<{
  voucher_id: number;
  code: string;
  discount_amount_paise: number;
  updated_order_total_paise: number;
}> {
  const res = await apiClient.post(
    `/rewards/vouchers/${code}/redeem`,
    { order_id: orderId },
    { headers: await authHeaders() },
  );
  return res.data as any;
}

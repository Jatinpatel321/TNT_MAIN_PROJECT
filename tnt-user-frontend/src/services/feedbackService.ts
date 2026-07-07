import { apiClient, authHeaders } from './apiClient';

export type FeedbackPayload = {
  quality_rating: number;
  time_rating: number;
  behavior_rating: number;
  overall_rating?: number;
  comment?: string;
};

export type FeedbackRecord = FeedbackPayload & {
  id: number;
  order_id: number;
  vendor_id: number;
  user_id: number;
  overall_rating: number | null;
  created_at: string;
};

export type VendorReviewPayload = {
  rating: number;
  title?: string;
  review_text?: string;
  is_anonymous?: boolean;
  order_id?: number;
};

export type VendorReview = {
  id: number;
  vendor_id: number;
  user_id: number;
  order_id: number | null;
  rating: number;
  title: string | null;
  review_text: string | null;
  is_anonymous: boolean;
  reviewer_name: string | null;
  created_at: string;
};

export type VendorFeedbackSummary = {
  vendor_id: number;
  total_reviews: number;
  avg_quality_rating: number;
  avg_time_rating: number;
  avg_behavior_rating: number;
  avg_overall_rating: number;
  rating_distribution: Record<number, number>;
};

export async function submitFeedback(
  orderId: number,
  payload: FeedbackPayload,
): Promise<{ feedback_id: number }> {
  const res = await apiClient.post(`/feedback/orders/${orderId}`, payload, {
    headers: await authHeaders(),
  });
  return res.data as { feedback_id: number };
}

export async function getMyFeedback(): Promise<FeedbackRecord[]> {
  const res = await apiClient.get('/feedback/me', {
    headers: await authHeaders(),
  });
  return res.data as FeedbackRecord[];
}

export async function getOrderFeedback(
  orderId: number,
): Promise<FeedbackRecord> {
  const res = await apiClient.get(`/feedback/orders/${orderId}`, {
    headers: await authHeaders(),
  });
  return res.data as FeedbackRecord;
}

export async function submitVendorReview(
  vendorId: number,
  payload: VendorReviewPayload,
): Promise<VendorReview> {
  const res = await apiClient.post(`/feedback/vendors/${vendorId}/reviews`, payload, {
    headers: await authHeaders(),
  });
  return res.data as VendorReview;
}

export async function getVendorReviews(
  vendorId: number,
): Promise<VendorReview[]> {
  const res = await apiClient.get(`/feedback/vendors/${vendorId}/reviews`, {
    headers: await authHeaders(),
  });
  return res.data as VendorReview[];
}

export async function getVendorFeedbackSummary(
  vendorId: number,
): Promise<VendorFeedbackSummary> {
  const res = await apiClient.get(`/feedback/vendors/${vendorId}/summary`, {
    headers: await authHeaders(),
  });
  return res.data as VendorFeedbackSummary;
}

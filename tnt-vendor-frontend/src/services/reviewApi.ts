import apiClient from './apiClient';

export interface Review {
  id: number;
  user_id: number;
  user_name: string;
  order_id: number;
  rating: number;
  comment: string;
  created_at: string;
}

export interface ReviewStats {
  average_rating: number;
  total_reviews: number;
  distribution: Record<number, number>; // { 1: count, 2: count, ... }
}

export const reviewApi = {
  /** Get all reviews for the authenticated vendor */
  getReviews: (params?: { page?: number; per_page?: number; rating?: number }) =>
    apiClient.get<{ reviews: Review[]; total: number; page: number; stats?: ReviewStats }>(
      `/v1/vendors/reviews`,
      { params },
    ),

  /** Get aggregated review stats */
  getReviewStats: () =>
    apiClient.get<ReviewStats>(`/v1/vendors/reviews/stats`),

  /** Reply to a review */
  replyToReview: (reviewId: number, reply: string) =>
    apiClient.post(`/v1/vendors/reviews/${reviewId}/reply`, { reply }),
};

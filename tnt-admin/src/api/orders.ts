import api from './axios';
import type { Order, OrderTimeline, VendorAnalytics } from '../types';

export const ordersApi = {
  getById: (id: number) =>
    api.get<Order>(`/v1/orders/${id}`),

  getTimeline: (id: number) =>
    api.get<OrderTimeline[]>(`/v1/orders/${id}/timeline`),

  confirm: (id: number) =>
    api.post(`/v1/orders/${id}/confirm`),

  markReady: (id: number) =>
    api.post(`/v1/orders/${id}/ready`),

  cancel: (id: number) =>
    api.post(`/v1/orders/${id}/cancel`),

  getVendorAnalytics: (params?: Record<string, unknown>) =>
    api.get<VendorAnalytics>('/v1/orders/vendor/analytics', { params }),
};

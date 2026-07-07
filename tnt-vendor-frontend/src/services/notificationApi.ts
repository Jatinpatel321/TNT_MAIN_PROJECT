import apiClient from './apiClient';

export interface Notification {
  id: number;
  user_id: number;
  title: string;
  message: string;
  notification_type: string;
  reference_id?: number;
  is_read: boolean;
  created_at: string;
}

export interface UnreadCountResponse {
  unread_count: number;
}

export const notificationApi = {
  getNotifications: (unreadOnly?: boolean, type?: string) => {
    const params: any = {};
    if (unreadOnly) params.unread_only = true;
    if (type) params.notification_type = type;
    return apiClient.get(`/v1/notifications/vendor`, { params });
  },
  getUnreadCount: () => apiClient.get<UnreadCountResponse>(`/v1/notifications/unread-count`),
  markAsRead: (notificationId: number) =>
    apiClient.post(`/v1/notifications/${notificationId}/read`),
  markAllAsRead: () => apiClient.post(`/v1/notifications/mark-all-read`),
  notifyDelay: (orderId: number, delayMinutes: number, reason: string) =>
    apiClient.post(`/v1/notifications/vendor/notify-delay`, {
      order_id: orderId,
      delay_minutes: delayMinutes,
      reason,
    }),
  notifyReady: (orderId: number) =>
    apiClient.post(`/v1/notifications/vendor/notify-ready`, { order_id: orderId }),
  notifyCustom: (orderId: number, message: string) =>
    apiClient.post(`/v1/notifications/vendor/notify-custom`, {
      order_id: orderId,
      message,
    }),
};

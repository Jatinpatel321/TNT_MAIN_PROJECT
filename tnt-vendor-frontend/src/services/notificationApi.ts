import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

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
    return axios.get(`${API_BASE_URL}/v1/notifications/vendor`, { params });
  },
  getUnreadCount: () => axios.get<UnreadCountResponse>(`${API_BASE_URL}/v1/notifications/unread-count`),
  markAsRead: (notificationId: number) =>
    axios.post(`${API_BASE_URL}/v1/notifications/${notificationId}/read`),
  markAllAsRead: () => axios.post(`${API_BASE_URL}/v1/notifications/mark-all-read`),
  notifyDelay: (orderId: number, delayMinutes: number, reason: string) =>
    axios.post(`${API_BASE_URL}/v1/notifications/vendor/notify-delay`, {
      order_id: orderId,
      delay_minutes: delayMinutes,
      reason,
    }),
  notifyReady: (orderId: number) =>
    axios.post(`${API_BASE_URL}/v1/notifications/vendor/notify-ready`, { order_id: orderId }),
  notifyCustom: (orderId: number, message: string) =>
    axios.post(`${API_BASE_URL}/v1/notifications/vendor/notify-custom`, {
      order_id: orderId,
      message,
    }),
};
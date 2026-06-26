import {apiClient, authHeaders} from './apiClient';
import type {NotificationItem, NotificationTypeKey} from '../types/models';
import {getItem} from '../utils/storage';
import {STORAGE_KEYS} from '../utils/constants';

async function getStoredUserId(): Promise<number | null> {
  try {
    const raw = await getItem(STORAGE_KEYS.user);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as {id?: unknown};
    const id = Number(parsed?.id);
    return Number.isFinite(id) ? id : null;
  } catch {
    return null;
  }
}

export async function getNotifications(options?: {
  unreadOnly?: boolean;
  type?: NotificationTypeKey;
}): Promise<NotificationItem[]> {
  const userId = await getStoredUserId();
  const params: Record<string, string> = {};
  if (options?.unreadOnly) params.unread_only = 'true';
  if (options?.type) params.notification_type = options.type;

  if (!userId) {
    const res = await apiClient.get('/notifications', {
      params,
      headers: await authHeaders(),
    });
    return res.data as NotificationItem[];
  }
  return getNotificationsByUserId(userId);
}

export async function getNotificationsByUserId(
  userId: number,
): Promise<NotificationItem[]> {
  const res = await apiClient.get(`/notifications/${userId}`, {
    headers: await authHeaders(),
  });
  const data = res.data as any;
  if (Array.isArray(data)) return data as NotificationItem[];
  if (Array.isArray(data?.notifications))
    return data.notifications as NotificationItem[];
  return [];
}

export async function getUnreadCount(): Promise<number> {
  try {
    const res = await apiClient.get('/notifications/unread-count', {
      headers: await authHeaders(),
    });
    return (res.data as {unread_count: number}).unread_count;
  } catch {
    return 0;
  }
}

export async function markNotificationRead(
  notificationId: number,
): Promise<NotificationItem> {
  const res = await apiClient.post(
    `/notifications/${notificationId}/read`,
    undefined,
    {headers: await authHeaders()},
  );
  return res.data as NotificationItem;
}

export async function markAllNotificationsRead(): Promise<{
  updated_count: number;
}> {
  const res = await apiClient.post('/notifications/mark-all-read', undefined, {
    headers: await authHeaders(),
  });
  return res.data as {updated_count: number};
}

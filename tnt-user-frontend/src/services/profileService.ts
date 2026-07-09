import { apiClient, authHeaders } from './apiClient';
import type { DietaryPreference, ResidenceType, User } from '../types/models';

export type ProfileUpdatePayload = {
  full_name?: string;
  university_id?: string;
  department?: string;
  semester?: number;
  email?: string;
  campus?: string;
  residence_type?: ResidenceType;
  dietary_preference?: DietaryPreference;
};

export type ProfileStats = {
  total_orders: number;
  food_orders: number;
  stationery_orders: number;
  group_orders: number;
  total_spent: number;
  loyalty_points: number;
  rewards_earned: number;
  saved_via_offers: number;
  member_since: string | null;
};

export type UserPreferences = {
  dietary_restrictions?: string[];
  cuisine_preferences?: string[];
  spice_level?: number;
  preferred_pickup_hour?: number;
  enable_reorder_suggestions?: boolean;
  enable_offpeak_reminders?: boolean;
  enable_rush_alerts?: boolean;
  enable_ai_recommendations?: boolean;
  preferred_pickup_locations?: string[];
  favourite_categories?: string[];
  dark_mode?: boolean;
};

export type FavoriteVendor = {
  vendor_id: number;
  vendor_name?: string | null;
  vendor_type?: string | null;
  created_at?: string | null;
};

export type FavoriteMenuItem = {
  menu_item_id: number;
  name?: string | null;
  vendor_id?: number | null;
  price?: number | null;
  created_at?: string | null;
};

export async function getProfile(): Promise<User> {
  const res = await apiClient.get('/profile/me', { headers: await authHeaders() });
  return res.data as User;
}

export async function updateProfile(payload: ProfileUpdatePayload): Promise<User> {
  const res = await apiClient.put('/profile/update', payload, { headers: await authHeaders() });
  return res.data as User;
}

export async function uploadProfileImage(fileUri: string, fileName: string, mimeType: string): Promise<{ profile_image: string }> {
  const formData = new FormData();
  formData.append('file', {
    uri: fileUri,
    name: fileName,
    type: mimeType,
  } as any);

  const res = await apiClient.post('/profile/upload-image', formData, {
    headers: {
      ...(await authHeaders()),
      'Content-Type': 'multipart/form-data',
    },
  });
  return res.data as { profile_image: string };
}

export async function getProfileStats(): Promise<ProfileStats> {
  const res = await apiClient.get('/profile/stats', { headers: await authHeaders() });
  return res.data as ProfileStats;
}

export async function getPreferences(): Promise<UserPreferences> {
  const res = await apiClient.get('/users/me/preferences', { headers: await authHeaders() });
  return (res.data?.preferences ?? {}) as UserPreferences;
}

export async function updatePreferences(payload: UserPreferences): Promise<UserPreferences> {
  const res = await apiClient.put('/users/me/preferences', payload, { headers: await authHeaders() });
  return (res.data?.preferences ?? {}) as UserPreferences;
}

export async function deleteAccount(): Promise<void> {
  await apiClient.delete('/profile/me', { headers: await authHeaders() });
}

export async function getFavoriteVendors(): Promise<FavoriteVendor[]> {
  const res = await apiClient.get('/profile/favorites/vendors', { headers: await authHeaders() });
  return res.data as FavoriteVendor[];
}

export async function addFavoriteVendor(vendorId: number): Promise<FavoriteVendor> {
  const res = await apiClient.post(`/profile/favorites/vendors/${vendorId}`, null, { headers: await authHeaders() });
  return res.data as FavoriteVendor;
}

export async function removeFavoriteVendor(vendorId: number): Promise<void> {
  await apiClient.delete(`/profile/favorites/vendors/${vendorId}`, { headers: await authHeaders() });
}

export async function getFavoriteMenuItems(): Promise<FavoriteMenuItem[]> {
  const res = await apiClient.get('/profile/favorites/menu-items', { headers: await authHeaders() });
  return res.data as FavoriteMenuItem[];
}

export async function addFavoriteMenuItem(menuItemId: number): Promise<FavoriteMenuItem> {
  const res = await apiClient.post(`/profile/favorites/menu-items/${menuItemId}`, null, { headers: await authHeaders() });
  return res.data as FavoriteMenuItem;
}

export async function removeFavoriteMenuItem(menuItemId: number): Promise<void> {
  await apiClient.delete(`/profile/favorites/menu-items/${menuItemId}`, { headers: await authHeaders() });
}

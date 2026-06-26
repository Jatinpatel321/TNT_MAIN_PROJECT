import { apiClient, authHeaders } from './apiClient';
import type { User } from '../types/models';

export type ProfileUpdatePayload = {
  full_name?: string;
  university_id?: string;
  department?: string;
  semester?: number;
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

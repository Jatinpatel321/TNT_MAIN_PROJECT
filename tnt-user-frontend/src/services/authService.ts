import { apiClient, authHeaders } from './apiClient';
import type { User } from '../types/models';

export type LoginResponse = {
  success: boolean;
  message: string;
  data: {
    access_token: string;
    token_type: 'bearer';
    user: User;
    is_new_user: boolean;
  };
};

export async function sendOtp(phone: string): Promise<{ message: string; otp?: string }> {
  const endpoint = '/auth/send-otp';
  const payload = { phone };
  console.log('[authService] sendOtp request', { endpoint, payload });

  try {
    const res = await apiClient.post(endpoint, payload);
    console.log('[authService] sendOtp success');
    return res.data as { message: string; otp?: string };
  } catch (error: any) {
    const detail = error?.response?.data ?? error?.message;
    console.error('[authService] sendOtp failed', detail);
    throw error;
  }
}

export async function login(phone: string, otp: string): Promise<LoginResponse> {
  const endpoint = '/auth/verify-otp';
  const payload = { phone, otp };
  console.log('[authService] login request', { endpoint, payload: { phone, hasOtp: Boolean(otp) } });

  try {
    const res = await apiClient.post(endpoint, payload);
    console.log('[authService] login success');
    return res.data as LoginResponse;
  } catch (error: any) {
    const detail = error?.response?.data ?? error?.message;
    console.error('[authService] login failed', detail);
    throw error;
  }
}

export async function signup(payload: {
  phone: string;
  name: string;
  role: 'student' | 'faculty';
  university_id?: string | null;
}): Promise<User> {
  const res = await apiClient.post('/users/register', payload);
  return res.data as User;
}

export async function logout(): Promise<void> {
  // Stateless backend: logout is client-side token removal; nothing to call server-side.
  return Promise.resolve();
}

export async function getProfile(): Promise<User> {
  const res = await apiClient.get('/profile/me', { headers: await authHeaders() });
  return res.data as User;
}

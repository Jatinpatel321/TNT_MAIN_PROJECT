import api from './axios';

export interface VendorProfile {
  vendor_id: number;
  vendor_name: string;
  category: string | null;
  owner_id: number;
  owner_name: string | null;
  owner_phone: string | null;
  status: string;
  created_at: string | null;
}

export interface VendorLoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  vendor: VendorProfile;
}

export interface VendorStaff {
  id: number;
  vendor_id: number;
  name: string;
  role: string;
  phone: string;
  permissions: { [key: string]: unknown } | null;
  is_active: boolean;
  created_at: string | null;
}

export const vendorAuthApi = {
  login: (vendor_id: number, password: string) =>
    api.post<VendorLoginResponse>('/v1/vendor/login', {
      vendor_id,
      password,
    }),

  staffLogin: (staff_phone: string, password: string) =>
    api.post<VendorLoginResponse>('/v1/vendor/login', {
      vendor_id: 0,
      staff_phone,
      password,
    }),

  refresh: (refresh_token: string) =>
    api.post('/v1/vendor/refresh', { refresh_token }),

  register: (
    vendor_name: string,
    category: string,
    owner_phone: string,
    password: string
  ) =>
    api.post('/v1/vendor/register', null, {
      params: { vendor_name, category, owner_phone, password },
    }),

  getProfile: () =>
    api.get<VendorProfile>('/v1/vendor/profile'),

  updateProfile: (data: { vendor_name?: string; category?: string }) =>
    api.put<VendorProfile>('/v1/vendor/profile', data),

  listStaff: () =>
    api.get<VendorStaff[]>('/v1/vendor/staff'),

  createStaff: (data: {
    name: string;
    role: string;
    phone: string;
    password: string;
    permissions?: Record<string, any>;
  }) =>
    api.post<VendorStaff>('/v1/vendor/staff', data),

  updateStaff: (
    staff_id: number,
    data: {
      name?: string;
      role?: string;
      phone?: string;
      is_active?: boolean;
      permissions?: Record<string, any>;
    }
  ) =>
    api.put<VendorStaff>(`/v1/vendor/staff/${staff_id}`, data),

  deleteStaff: (staff_id: number) =>
    api.delete(`/v1/vendor/staff/${staff_id}`),
};

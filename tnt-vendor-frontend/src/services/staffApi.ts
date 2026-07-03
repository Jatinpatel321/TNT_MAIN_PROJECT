import apiClient from './apiClient';
import { API_BASE_URL } from '../config/api';

export interface StaffMember {
  id: number;
  user_id: number;
  name: string;
  phone: string;
  email?: string;
  role: 'owner' | 'manager' | 'staff';
  permissions: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Permission {
  module: string;
  actions: string[];
  description: string;
}

export interface PermissionsResponse {
  permissions: Permission[];
  roles: {
    owner: string[];
    manager: string[];
    staff: string[];
  };
}

export interface AddStaffData {
  name: string;
  phone: string;
  email?: string;
  role: 'owner' | 'manager' | 'staff';
  permissions?: string[];
}

export interface UpdateStaffData {
  name?: string;
  phone?: string;
  email?: string;
  role?: 'owner' | 'manager' | 'staff';
  permissions?: string[];
  is_active?: boolean;
}

export const staffApi = {
  getStaff: () =>
    apiClient.get<{ staff: StaffMember[]; total: number }>(`${API_BASE_URL}/v1/vendors/profile/staff`),

  addStaff: (data: AddStaffData) =>
    apiClient.post<StaffMember>(`${API_BASE_URL}/v1/vendors/profile/staff`, data),

  updateStaff: (staffId: number, data: UpdateStaffData) =>
    apiClient.put<StaffMember>(`${API_BASE_URL}/v1/vendors/profile/staff/${staffId}`, data),

  deleteStaff: (staffId: number) =>
    apiClient.delete(`${API_BASE_URL}/v1/vendors/profile/staff/${staffId}`),

  getPermissions: () =>
    apiClient.get<PermissionsResponse>(`${API_BASE_URL}/v1/vendors/profile/permissions`),
};

import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

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
    axios.get<{ staff: StaffMember[]; total: number }>(`${API_BASE_URL}/v1/vendors/profile/staff`),

  addStaff: (data: AddStaffData) =>
    axios.post<StaffMember>(`${API_BASE_URL}/v1/vendors/profile/staff`, data),

  updateStaff: (staffId: number, data: UpdateStaffData) =>
    axios.put<StaffMember>(`${API_BASE_URL}/v1/vendors/profile/staff/${staffId}`, data),

  deleteStaff: (staffId: number) =>
    axios.delete(`${API_BASE_URL}/v1/vendors/profile/staff/${staffId}`),

  getPermissions: () =>
    axios.get<PermissionsResponse>(`${API_BASE_URL}/v1/vendors/profile/permissions`),
};
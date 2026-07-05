import apiClient from './apiClient';

// ── Mirrors backend VendorStaffResponse ───────────────────────────────────
// Backend: { id, vendor_id, name, role, phone, permissions (dict), is_active, created_at }
export interface StaffMember {
  id: number;
  vendor_id: number;
  name: string;
  phone: string;
  /** 'manager' | 'staff'  — backend pattern is ^(manager|staff)$ */
  role: 'manager' | 'staff';
  /** Backend stores permissions as a JSON dict/object */
  permissions: Record<string, any> | null;
  is_active: boolean;
  created_at: string;
}

// ── Mirrors backend VendorStaffCreate ─────────────────────────────────────
export interface AddStaffData {
  name: string;
  phone: string;
  role?: 'manager' | 'staff';
  /** Password is REQUIRED by backend VendorStaffCreate (min 4 chars) */
  password: string;
  permissions?: Record<string, any>;
}

// ── Mirrors backend VendorStaffUpdate ─────────────────────────────────────
export interface UpdateStaffData {
  name?: string;
  phone?: string;
  role?: 'manager' | 'staff';
  is_active?: boolean;
  permissions?: Record<string, any>;
}

// ── API endpoints ─────────────────────────────────────────────────────────
// Backend staff endpoints live at: /v1/vendors/auth/staff
// (auth_router with prefix="" mounted at /v1/vendors/auth in api/v1.py)

export const staffApi = {
  /** List all staff for the authenticated vendor */
  getStaff: () =>
    apiClient.get<StaffMember[]>(`/v1/vendors/auth/staff`),

  /** Create a new staff member (owner only) */
  addStaff: (data: AddStaffData) =>
    apiClient.post<StaffMember>(`/v1/vendors/auth/staff`, data),

  /** Update a staff member by ID (owner only) */
  updateStaff: (staffId: number, data: UpdateStaffData) =>
    apiClient.put<StaffMember>(`/v1/vendors/auth/staff/${staffId}`, data),

  /** Delete a staff member by ID (owner only) */
  deleteStaff: (staffId: number) =>
    apiClient.delete(`/v1/vendors/auth/staff/${staffId}`),
};

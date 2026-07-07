import apiClient from './apiClient';

// ── Vendor profile endpoints ──────────────────────────────────────────────
// GET  /v1/vendors/auth/profile  → VendorProfileResponse
// PUT  /v1/vendors/auth/profile  → VendorProfileResponse
// Staff endpoints live at /v1/vendors/auth/staff (use staffApi.ts for those)

export const profileApi = {
  /** Get the authenticated vendor's profile */
  getProfile: () => apiClient.get(`/v1/vendors/auth/profile`),

  /** Update vendor profile — name and category (owner only) */
  updateProfile: (data: { vendor_name?: string; category?: string }) =>
    apiClient.put(`/v1/vendors/auth/profile`, data),
};

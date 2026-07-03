import apiClient from './apiClient';
import { API_BASE_URL } from '../config/api';

export const profileApi = {
  getProfile: () => apiClient.get(`${API_BASE_URL}/v1/vendors/profile/`),
  updateProfile: (data: any) => apiClient.put(`${API_BASE_URL}/v1/vendors/profile/`, data),
  getStaff: () => apiClient.get(`${API_BASE_URL}/v1/vendors/profile/staff`),
  addStaff: (data: any) => apiClient.post(`${API_BASE_URL}/v1/vendors/profile/staff`, data),
  updateStaff: (staffId: number, data: any) =>
    apiClient.put(`${API_BASE_URL}/v1/vendors/profile/staff/${staffId}`, data),
  deleteStaff: (staffId: number) =>
    apiClient.delete(`${API_BASE_URL}/v1/vendors/profile/staff/${staffId}`),
  getPermissions: () => apiClient.get(`${API_BASE_URL}/v1/vendors/profile/permissions`),
};

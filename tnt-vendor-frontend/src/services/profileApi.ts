import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

export const profileApi = {
  getProfile: () => axios.get(`${API_BASE_URL}/v1/vendors/profile/`),
  updateProfile: (data: any) => axios.put(`${API_BASE_URL}/v1/vendors/profile/`, data),
  getStaff: () => axios.get(`${API_BASE_URL}/v1/vendors/profile/staff`),
  addStaff: (data: any) => axios.post(`${API_BASE_URL}/v1/vendors/profile/staff`, data),
  updateStaff: (staffId: number, data: any) =>
    axios.put(`${API_BASE_URL}/v1/vendors/profile/staff/${staffId}`, data),
  deleteStaff: (staffId: number) =>
    axios.delete(`${API_BASE_URL}/v1/vendors/profile/staff/${staffId}`),
  getPermissions: () => axios.get(`${API_BASE_URL}/v1/vendors/profile/permissions`),
};
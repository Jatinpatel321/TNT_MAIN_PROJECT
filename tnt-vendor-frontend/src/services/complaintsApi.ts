import apiClient from './apiClient';

export interface Complaint {
  id: number;
  user_id: number;
  order_id?: number;
  vendor_id?: number;
  assigned_to_vendor_id?: number;
  category: string;
  status: string;
  title: string;
  description?: string;
  created_at: string;
}

export const complaintsApi = {
  getComplaints: () => apiClient.get<Complaint[]>('/v1/complaints/vendor'),
  resolveComplaint: (id: number) => apiClient.post(`/v1/complaints/vendor/${id}/resolve`),
};

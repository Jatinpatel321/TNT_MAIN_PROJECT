import api from './axios';
import type { Complaint } from '../types';

export const complaintsApi = {
  getAll: (params?: Record<string, unknown>) =>
    api.get<Complaint[]>('/v1/complaints/', { params }),

  assign: (id: number, vendorId: number) =>
    api.post(`/v1/complaints/${id}/assign`, null, { params: { vendor_id: vendorId } }),

  updateStatus: (id: number, status: string) =>
    api.post(`/v1/complaints/${id}/status`, { status }),

  escalate: (id: number) =>
    api.post(`/v1/complaints/${id}/escalate`),
};

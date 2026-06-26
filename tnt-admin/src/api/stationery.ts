import api from './axios';
import type { PrintJob } from '../types';

export const stationeryApi = {
  getServices: () =>
    api.get('/v1/stationery/services'),

  getJobs: (params?: Record<string, unknown>) =>
    api.get<PrintJob[]>('/v1/stationery/jobs', { params }),

  updateJobStatus: (id: number, status: string) =>
    api.post(`/v1/stationery/jobs/${id}/status`, { status }),
};

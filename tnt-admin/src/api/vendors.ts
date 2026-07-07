import api from './axios';
import type { Vendor, MenuItem, TimeSlot } from '../types';

export const vendorsApi = {
  getAll: (params?: { vendor_type?: 'food' | 'stationery'; search?: string }) =>
    api.get<Vendor[]>('/v1/vendors/', { params }),

  getById: (id: number) =>
    api.get<Vendor>(`/v1/vendors/${id}`),

  getMenu: (id: number) =>
    api.get<MenuItem[]>(`/v1/vendors/${id}/menu`),

  getSlots: (id: number) =>
    api.get<TimeSlot[]>(`/v1/vendors/${id}/slots`),
};

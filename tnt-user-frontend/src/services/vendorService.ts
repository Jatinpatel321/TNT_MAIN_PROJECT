import { apiClient } from './apiClient';
import type { MenuItem, Vendor, VendorSlot, VendorType } from '../types/models';

export async function getVendors(type: VendorType): Promise<Vendor[]> {
  const res = await apiClient.get('/vendors', { params: { type } });
  // Backend returns { total, limit, offset, items: Vendor[] }
  const body = res.data as { items?: Vendor[]; total?: number } | Vendor[];
  if (Array.isArray(body)) {
    return body as Vendor[];
  }
  return (body as { items?: Vendor[] })?.items ?? [];
}

export async function getVendorMenu(vendorId: number): Promise<MenuItem[]> {
  const res = await apiClient.get(`/vendors/${vendorId}/menu`);
  return res.data as MenuItem[];
}

export type VendorSlotListResponse = {
  estimated_ready_time: string | null;
  slots: VendorSlot[];
};

export async function getVendorSlots(vendorId: number): Promise<VendorSlot[]> {
  const res = await apiClient.get(`/vendors/${vendorId}/slots`);
  // Backend returns { estimated_ready_time: string | null, slots: VendorSlot[] }
  const body = res.data as VendorSlotListResponse | VendorSlot[];
  if (Array.isArray(body)) {
    return body;
  }
  return (body as VendorSlotListResponse)?.slots ?? [];
}


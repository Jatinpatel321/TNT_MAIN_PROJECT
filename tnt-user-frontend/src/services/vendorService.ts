import { apiClient } from './apiClient';
import type { MenuItem, Vendor, VendorSlot, VendorType } from '../types/models';

export async function getVendors(type: VendorType): Promise<Vendor[]> {
  const res = await apiClient.get('/vendors', { params: { type } });
  return res.data as Vendor[];
}

export async function getVendorMenu(vendorId: number): Promise<MenuItem[]> {
  const res = await apiClient.get(`/vendors/${vendorId}/menu`);
  return res.data as MenuItem[];
}

export async function getVendorSlots(vendorId: number): Promise<VendorSlot[]> {
  const res = await apiClient.get(`/vendors/${vendorId}/slots`);
  return res.data as VendorSlot[];
}

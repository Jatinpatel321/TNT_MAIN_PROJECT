import { apiClient } from './apiClient';

export type Group = {
  id: number;
  name: string;
  owner_id: number;
  status: string;
  created_at: string;
  members: any[];
  cart_items: any[];
  slot_lock: any | null;
};

export async function createGroup(name: string): Promise<any> {
  const res = await apiClient.post('/groups', { name });
  return res.data;
}

export async function getMyGroups(): Promise<any[]> {
  const res = await apiClient.get('/groups/my-groups');
  return res.data as any[];
}

export async function getGroup(groupId: number): Promise<any> {
  const res = await apiClient.get(`/groups/${groupId}`);
  return res.data;
}

export async function inviteMember(groupId: number, phone: string): Promise<any> {
  const res = await apiClient.post(`/groups/${groupId}/invite`, { phone });
  return res.data;
}

export async function addGroupCartItem(groupId: number, menu_item_id: number, quantity: number): Promise<any> {
  const res = await apiClient.post(`/groups/${groupId}/cart`, { menu_item_id, quantity });
  return res.data;
}

export async function lockGroupSlot(groupId: number, slot_id: number, duration_minutes?: number): Promise<any> {
  const res = await apiClient.post(`/groups/${groupId}/slot/lock`, {
    slot_id,
    duration_minutes,
  });
  return res.data;
}

export async function placeGroupOrder(groupId: number): Promise<any> {
  const res = await apiClient.post(`/groups/${groupId}/order`);
  return res.data;
}

export async function getPaymentSplits(groupId: number): Promise<any> {
  const res = await apiClient.get(`/groups/${groupId}/payment-splits`);
  return res.data;
}

export async function setPaymentSplit(groupId: number, payload: { split_type: string; amount?: number; percentage?: number }): Promise<any> {
  const res = await apiClient.post(`/groups/${groupId}/payment-split`, payload);
  return res.data;
}

export async function removeGroupCartItem(groupId: number, itemId: number): Promise<any> {
  const res = await apiClient.delete(`/groups/${groupId}/cart/${itemId}`);
  return res.data;
}

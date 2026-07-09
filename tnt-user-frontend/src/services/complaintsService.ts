import { apiClient, authHeaders } from './apiClient';

export type ComplaintCategory = 'late_order' | 'wrong_item' | 'quality_issue' | 'other';

export type Complaint = {
  id: number;
  order_id: number | null;
  vendor_id: number | null;
  assigned_to_vendor_id: number | null;
  category: string;
  status: string;
  title: string;
  description: string | null;
  created_at: string;
};

export type ComplaintCreatePayload = {
  category: ComplaintCategory;
  title: string;
  description?: string;
  order_id?: number;
};

export async function getMyComplaints(): Promise<Complaint[]> {
  const res = await apiClient.get('/complaints/my', { headers: await authHeaders() });
  return res.data as Complaint[];
}

export async function createComplaint(
  payload: ComplaintCreatePayload,
): Promise<{ message: string; complaint_id: number }> {
  const res = await apiClient.post('/complaints/', payload, { headers: await authHeaders() });
  return res.data as { message: string; complaint_id: number };
}

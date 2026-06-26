import { apiClient } from './apiClient';

export type StationeryJob = {
  id: number;
  user_id: number;
  vendor_id: number;
  service_id: number;
  quantity: number;
  file_url: string | null;
  amount: number;
  is_paid: boolean;
  status: string;
  created_at: string;
};

export async function submitStationeryJob(params: {
  serviceId: number;
  quantity: number;
  fileUri: string;
  fileName: string;
  mimeType: string;
}): Promise<StationeryJob> {
  const form = new FormData();
  form.append('service_id', String(params.serviceId));
  form.append('quantity', String(params.quantity));

  form.append('file', {
    uri: params.fileUri,
    name: params.fileName,
    type: params.mimeType,
  } as any);

  const res = await apiClient.post('/stationery/jobs', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });

  return res.data as StationeryJob;
}

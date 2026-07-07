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
  print_type: 'bw' | 'color';
  paper_size: 'A4' | 'A3';
  duplex: boolean;
  page_range: string | null;
  notes: string | null;
};

export async function submitStationeryJob(params: {
  serviceId: number;
  quantity: number;
  fileUri: string;
  fileName: string;
  mimeType: string;
  printType?: 'bw' | 'color';
  paperSize?: 'A4' | 'A3';
  duplex?: boolean;
  pageRange?: string;
  notes?: string;
}): Promise<StationeryJob> {
  const form = new FormData();
  form.append('service_id', String(params.serviceId));
  form.append('quantity', String(params.quantity));
  form.append('print_type', params.printType ?? 'bw');
  form.append('paper_size', params.paperSize ?? 'A4');
  form.append('duplex', String(params.duplex ?? false));
  if (params.pageRange) form.append('page_range', params.pageRange);
  if (params.notes) form.append('notes', params.notes);

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

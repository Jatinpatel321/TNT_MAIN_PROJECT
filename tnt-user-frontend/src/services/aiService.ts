import { apiClient } from './apiClient';

export async function getSlotRecommendations(): Promise<any> {
  const res = await apiClient.get('/ai/slot-recommendations');
  return res.data;
}

export async function getPersonalization(): Promise<any> {
  const res = await apiClient.get('/ai/personalization');
  return res.data;
}

export async function getReorderSuggestions(): Promise<any> {
  const res = await apiClient.get('/ai/reorder-suggestions');
  return res.data;
}

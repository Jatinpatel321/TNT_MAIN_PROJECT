import apiClient from './apiClient';
import { API_BASE_URL } from '../config/api';

export const retentionApi = {
  getCustomers: () => apiClient.get(`${API_BASE_URL}/v1/vendors/retention/customers`),
  getRepeatCustomers: () => apiClient.get(`${API_BASE_URL}/v1/vendors/retention/repeat-customers`),
  createOffer: (data: any) => apiClient.post(`${API_BASE_URL}/v1/vendors/retention/offers`, data),
  getOffers: () => apiClient.get(`${API_BASE_URL}/v1/vendors/retention/offers`),
  createCampaign: (data: any) => apiClient.post(`${API_BASE_URL}/v1/vendors/retention/campaigns`, data),
  getCampaigns: () => apiClient.get(`${API_BASE_URL}/v1/vendors/retention/campaigns`),
  getPromotions: () => apiClient.get(`${API_BASE_URL}/v1/vendors/retention/promotions`),
  getAiSuggestions: () => apiClient.get(`${API_BASE_URL}/v1/vendors/retention/ai-suggestions`),
  notifyCustomers: (offerId: number) => apiClient.post(`${API_BASE_URL}/v1/vendors/retention/offers/${offerId}/notify`),
};

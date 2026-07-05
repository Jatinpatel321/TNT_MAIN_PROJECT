import apiClient from './apiClient';

export const retentionApi = {
  getCustomers: () => apiClient.get(`/v1/vendors/retention/customers`),
  getRepeatCustomers: () => apiClient.get(`/v1/vendors/retention/repeat-customers`),
  createOffer: (data: any) => apiClient.post(`/v1/vendors/retention/offers`, data),
  getOffers: () => apiClient.get(`/v1/vendors/retention/offers`),
  createCampaign: (data: any) => apiClient.post(`/v1/vendors/retention/campaigns`, data),
  getCampaigns: () => apiClient.get(`/v1/vendors/retention/campaigns`),
  getPromotions: () => apiClient.get(`/v1/vendors/retention/promotions`),
  getAiSuggestions: () => apiClient.get(`/v1/vendors/retention/ai-suggestions`),
  notifyCustomers: (offerId: number) => apiClient.post(`/v1/vendors/retention/offers/${offerId}/notify`),
};

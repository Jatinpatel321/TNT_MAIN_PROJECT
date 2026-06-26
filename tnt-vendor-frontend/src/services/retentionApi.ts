import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

export const retentionApi = {
  getCustomers: () => axios.get(`${API_BASE_URL}/v1/vendors/retention/customers`),
  getRepeatCustomers: () => axios.get(`${API_BASE_URL}/v1/vendors/retention/repeat-customers`),
  createOffer: (data: any) => axios.post(`${API_BASE_URL}/v1/vendors/retention/offers`, data),
  getOffers: () => axios.get(`${API_BASE_URL}/v1/vendors/retention/offers`),
  createCampaign: (data: any) => axios.post(`${API_BASE_URL}/v1/vendors/retention/campaigns`, data),
  getCampaigns: () => axios.get(`${API_BASE_URL}/v1/vendors/retention/campaigns`),
  getPromotions: () => axios.get(`${API_BASE_URL}/v1/vendors/retention/promotions`),
  getAiSuggestions: () => axios.get(`${API_BASE_URL}/v1/vendors/retention/ai-suggestions`),
  notifyCustomers: (offerId: number) => axios.post(`${API_BASE_URL}/v1/vendors/retention/offers/${offerId}/notify`),
};
import apiClient from './apiClient';
import { API_BASE_URL } from '../config/api';

export const settlementApi = {
  getRevenue: () => apiClient.get(`${API_BASE_URL}/v1/vendors/settlement/revenue`),
  getTransactions: (days: number = 30) =>
    apiClient.get(`${API_BASE_URL}/v1/vendors/settlement/transactions?days=${days}`),
  getSettlements: () => apiClient.get(`${API_BASE_URL}/v1/vendors/settlement/settlements`),
  getRefunds: () => apiClient.get(`${API_BASE_URL}/v1/vendors/settlement/refunds`),
  getDailyRevenue: (days: number = 7) =>
    apiClient.get(`${API_BASE_URL}/v1/vendors/settlement/daily-revenue?days=${days}`),
};

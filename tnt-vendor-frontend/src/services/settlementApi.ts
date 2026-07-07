import apiClient from './apiClient';

export const settlementApi = {
  getRevenue: () => apiClient.get(`/v1/vendors/settlement/revenue`),
  getTransactions: (days: number = 30) =>
    apiClient.get(`/v1/vendors/settlement/transactions?days=${days}`),
  getSettlements: () => apiClient.get(`/v1/vendors/settlement/settlements`),
  getRefunds: () => apiClient.get(`/v1/vendors/settlement/refunds`),
  getDailyRevenue: (days: number = 7) =>
    apiClient.get(`/v1/vendors/settlement/daily-revenue?days=${days}`),
};

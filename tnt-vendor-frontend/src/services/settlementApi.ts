import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

export const settlementApi = {
  getRevenue: () => axios.get(`${API_BASE_URL}/v1/vendors/settlement/revenue`),
  getTransactions: (days: number = 30) =>
    axios.get(`${API_BASE_URL}/v1/vendors/settlement/transactions?days=${days}`),
  getSettlements: () => axios.get(`${API_BASE_URL}/v1/vendors/settlement/settlements`),
  getRefunds: () => axios.get(`${API_BASE_URL}/v1/vendors/settlement/refunds`),
  getDailyRevenue: (days: number = 7) =>
    axios.get(`${API_BASE_URL}/v1/vendors/settlement/daily-revenue?days=${days}`),
};
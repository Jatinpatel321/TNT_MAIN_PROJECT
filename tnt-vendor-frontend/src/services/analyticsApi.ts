import apiClient from './apiClient';
import { API_BASE_URL } from '../config/api';

export const analyticsApi = {
  getDashboard: () => apiClient.get(`${API_BASE_URL}/v1/vendors/analytics/dashboard`),
  getDailySales: (days: number = 30) =>
    apiClient.get(`${API_BASE_URL}/v1/vendors/analytics/daily?days=${days}`),
  getWeeklySales: (weeks: number = 12) =>
    apiClient.get(`${API_BASE_URL}/v1/vendors/analytics/weekly?weeks=${weeks}`),
  getMonthlySales: (months: number = 12) =>
    apiClient.get(`${API_BASE_URL}/v1/vendors/analytics/monthly?months=${months}`),
  getYearlySales: () => apiClient.get(`${API_BASE_URL}/v1/vendors/analytics/yearly`),
  getPeakHours: () => apiClient.get(`${API_BASE_URL}/v1/vendors/analytics/peak-hours`),
  getItemAnalysis: () => apiClient.get(`${API_BASE_URL}/v1/vendors/analytics/items`),
  getWasteAnalysis: () => apiClient.get(`${API_BASE_URL}/v1/vendors/analytics/waste`),
  getRevenueTrends: () => apiClient.get(`${API_BASE_URL}/v1/vendors/analytics/revenue-trends`),
  exportCsv: (reportType: string) =>
    apiClient.get(`${API_BASE_URL}/v1/vendors/analytics/export/csv/${reportType}`, {
      responseType: 'text',
    }),
};

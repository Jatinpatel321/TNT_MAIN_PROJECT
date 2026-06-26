import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

export const analyticsApi = {
  getDashboard: () => axios.get(`${API_BASE_URL}/v1/vendors/analytics/dashboard`),
  getDailySales: (days: number = 30) =>
    axios.get(`${API_BASE_URL}/v1/vendors/analytics/daily?days=${days}`),
  getWeeklySales: (weeks: number = 12) =>
    axios.get(`${API_BASE_URL}/v1/vendors/analytics/weekly?weeks=${weeks}`),
  getMonthlySales: (months: number = 12) =>
    axios.get(`${API_BASE_URL}/v1/vendors/analytics/monthly?months=${months}`),
  getYearlySales: () => axios.get(`${API_BASE_URL}/v1/vendors/analytics/yearly`),
  getPeakHours: () => axios.get(`${API_BASE_URL}/v1/vendors/analytics/peak-hours`),
  getItemAnalysis: () => axios.get(`${API_BASE_URL}/v1/vendors/analytics/items`),
  getWasteAnalysis: () => axios.get(`${API_BASE_URL}/v1/vendors/analytics/waste`),
  getRevenueTrends: () => axios.get(`${API_BASE_URL}/v1/vendors/analytics/revenue-trends`),
  exportCsv: (reportType: string) =>
    axios.get(`${API_BASE_URL}/v1/vendors/analytics/export/csv/${reportType}`, {
      responseType: 'text',
    }),
};
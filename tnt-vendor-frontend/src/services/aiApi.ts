import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

export const aiApi = {
  getDashboard: () => axios.get(`${API_BASE_URL}/v1/vendors/ai/dashboard`),
  getDailyForecast: (days: number = 7) =>
    axios.get(`${API_BASE_URL}/v1/vendors/ai/forecast/daily?days=${days}`),
  getWeeklyForecast: (weeks: number = 4) =>
    axios.get(`${API_BASE_URL}/v1/vendors/ai/forecast/weekly?weeks=${weeks}`),
  getMonthlyForecast: (months: number = 3) =>
    axios.get(`${API_BASE_URL}/v1/vendors/ai/forecast/monthly?months=${months}`),
  getPopularItems: (limit: number = 10) =>
    axios.get(`${API_BASE_URL}/v1/vendors/ai/popular-items?limit=${limit}`),
  getWorkload: () => axios.get(`${API_BASE_URL}/v1/vendors/ai/workload`),
  getPeakTimes: () => axios.get(`${API_BASE_URL}/v1/vendors/ai/peak-times`),
  getWasteInsights: () => axios.get(`${API_BASE_URL}/v1/vendors/ai/waste-insights`),
  getInventorySuggestions: () =>
    axios.get(`${API_BASE_URL}/v1/vendors/ai/inventory-suggestions`),
  getRecommendations: () =>
    axios.get(`${API_BASE_URL}/v1/vendors/ai/recommendations`),
};
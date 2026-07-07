import apiClient from './apiClient';

export const aiApi = {
  getDashboard: () => apiClient.get(`/v1/vendors/ai/dashboard`),
  getDailyForecast: (days: number = 7) =>
    apiClient.get(`/v1/vendors/ai/forecast/daily?days=${days}`),
  getWeeklyForecast: (weeks: number = 4) =>
    apiClient.get(`/v1/vendors/ai/forecast/weekly?weeks=${weeks}`),
  getMonthlyForecast: (months: number = 3) =>
    apiClient.get(`/v1/vendors/ai/forecast/monthly?months=${months}`),
  getPopularItems: (limit: number = 10) =>
    apiClient.get(`/v1/vendors/ai/popular-items?limit=${limit}`),
  getWorkload: () => apiClient.get(`/v1/vendors/ai/workload`),
  getPeakTimes: () => apiClient.get(`/v1/vendors/ai/peak-times`),
  getWasteInsights: () => apiClient.get(`/v1/vendors/ai/waste-insights`),
  getInventorySuggestions: () =>
    apiClient.get(`/v1/vendors/ai/inventory-suggestions`),
  getRecommendations: () =>
    apiClient.get(`/v1/vendors/ai/recommendations`),
};

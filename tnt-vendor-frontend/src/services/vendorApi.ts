import axios from 'axios';

const API_BASE_URL = 'http://localhost:8001';

export interface Order {
  id: number;
  user_id: number;
  user_name?: string;
  slot_id: number;
  status: string;
  total_amount: number;
  created_at: string;
  is_online?: boolean;
  qr_code?: string;
  fraud_flag: boolean;
  eta_minutes?: number;
  items?: OrderItem[];
}

export interface OrderItem {
  id: number;
  menu_item_id: number;
  name: string;
  quantity: number;
  price_at_time: number;
}

export interface OrderMetrics {
  orders_today: number;
  pending: number;
  preparing: number;
  ready: number;
  completed: number;
  cancelled: number;
}

export interface OrdersResponse {
  orders: Order[];
  metrics: OrderMetrics;
}

export interface CurrentSlotResponse {
  current_slot: {
    id: number;
    start_time: string;
    end_time: string;
    max_orders: number;
    current_orders: number;
    status: string;
  } | null;
  orders: Order[];
  status_counts: Record<string, number>;
  total_orders: number;
}

export interface DashboardMetrics {
  orders_today: number;
  revenue_today: number;
  pending_orders: number;
  completed_orders: number;
  avg_rating: number;
  active_slots: number;
  recent_orders: any[];
  recent_notifications: any[];
  revenue_trend: { date: string; revenue: number }[];
}

export interface RevenueChartData {
  daily_data: { date: string; day_name: string; online: number; cash: number; refunds: number; net: number; orders: number }[];
  total_online: number;
  total_cash: number;
  total_net: number;
  total_orders: number;
}

export interface CustomerInsights {
  vendor_id: number;
  total_customers: number;
  recent_customers: number;
  new_customers: number;
  repeat_customers: number;
  repeat_rate: number;
  segments: { loyal: number; repeat: number; new: number; at_risk: number; lapsed: number };
  top_customers: { user_id: number; name: string; phone: string; order_count: number; total_spent: number; last_order: string }[];
}

export interface DemandDashboard {
  vendor_id: number;
  demand_overview: any;
  stock_prediction: any;
  rush_prediction: any;
  ai_forecast: any;
  recommendations: any[];
}

export interface BusinessHours {
  business_hours: Record<string, { open: string; close: string }>;
  holidays: { date: string; reason: string }[];
  is_open: boolean;
  currently_open: boolean;
  message: string;
}

export interface InventoryItem {
  item_id: number;
  name: string;
  price: number;
  is_available: boolean;
  available_quantity: number;
  current_stock: number;
  low_stock_threshold: number;
  last_restocked_at: string | null;
  auto_disable: boolean;
  status: 'in_stock' | 'low_stock' | 'out_of_stock' | 'manually_disabled';
}

export interface InventoryDashboard {
  vendor_id: number;
  total_items: number;
  in_stock: number;
  low_stock: number;
  out_of_stock: number;
  manually_disabled: number;
  items: InventoryItem[];
  stock_summary: {
    total_stock_available: number;
    items_needing_attention: number;
  };
}

export interface Campaign {
  id: number;
  name: string;
  description: string;
  offer_type: string;
  discount_value: number;
  min_order_amount: number;
  is_combo: boolean;
  combo_items: any[];
  start_date: string;
  end_date: string;
  usage_limit: number;
  times_used: number;
  is_active: boolean;
  status: string;
}

export interface RetentionAnalytics {
  vendor_id: number;
  total_customers: number;
  segments: Record<string, number>;
  repeat_rate: number;
  total_repeat_customers: number;
  frequent_buyers: any[];
  active_promotions: number;
  ai_suggestions: any[];
}

export const vendorApi = {
  // Existing endpoints
  getOrders: () => axios.get<OrdersResponse>(`${API_BASE_URL}/v1/vendors/orders`),
  getCurrentSlotOrders: () => axios.get<CurrentSlotResponse>(`${API_BASE_URL}/v1/vendors/orders/current-slot`),
  getUpcomingOrders: () => axios.get(`${API_BASE_URL}/v1/vendors/orders/upcoming`),
  acceptOrder: (orderId: number) => axios.put(`${API_BASE_URL}/v1/vendors/orders/${orderId}/accept`),
  prepareOrder: (orderId: number) => axios.put(`${API_BASE_URL}/v1/vendors/orders/${orderId}/prepare`),
  readyOrder: (orderId: number) => axios.put(`${API_BASE_URL}/v1/vendors/orders/${orderId}/ready`),
  completeOrder: (orderId: number) => axios.put(`${API_BASE_URL}/v1/vendors/orders/${orderId}/complete`),
  confirmPickup: (qrCode: string) => axios.post(`${API_BASE_URL}/v1/orders/qr/confirm`, null, {params: {qr_code: qrCode}}),
  confirmQRPickup: (qrCode: string) => axios.post(`${API_BASE_URL}/v1/orders/qr/pickup/confirm`, { qr_code: qrCode }),
  getOrderByQr: (qrCode: string) => axios.get(`${API_BASE_URL}/v1/orders/qr/${qrCode}`),
  getOrderByQR: (qrCode: string) => axios.get(`${API_BASE_URL}/v1/orders/qr/${encodeURIComponent(qrCode)}`),

  // Dashboard
  getDashboardMetrics: () => axios.get<DashboardMetrics>(`${API_BASE_URL}/v1/vendors/dashboard/`),
  getLiveOrders: () => axios.get<CurrentSlotResponse>(`${API_BASE_URL}/v1/vendors/dashboard/live-orders`),
  getRevenueChart: (days: number = 30) => axios.get<RevenueChartData>(`${API_BASE_URL}/v1/vendors/dashboard/revenue-chart?days=${days}`),
  getCustomerInsights: () => axios.get<CustomerInsights>(`${API_BASE_URL}/v1/vendors/dashboard/customer-insights`),

  // Demand Dashboard
  getDemandDashboard: () => axios.get<DemandDashboard>(`${API_BASE_URL}/v1/vendors/demand-dashboard/`),
  getDemandOverview: () => axios.get(`${API_BASE_URL}/v1/vendors/demand-dashboard/overview`),
  getStockPrediction: () => axios.get(`${API_BASE_URL}/v1/vendors/demand-dashboard/stock-prediction`),
  getRushPrediction: () => axios.get(`${API_BASE_URL}/v1/vendors/demand-dashboard/rush-prediction`),

  // Business Hours
  getBusinessHours: () => axios.get<BusinessHours>(`${API_BASE_URL}/v1/vendors/business-hours/`),
  updateBusinessHours: (data: Partial<BusinessHours>) => axios.put(`${API_BASE_URL}/v1/vendors/business-hours/`, data),
  getBusinessHoursStatus: () => axios.get(`${API_BASE_URL}/v1/vendors/business-hours/status`),

  // ── PHASE A: Inventory Automation ──
  getInventoryDashboard: () => axios.get<InventoryDashboard>(`${API_BASE_URL}/v1/vendors/inventory/dashboard`),
  getLowStockItems: () => axios.get(`${API_BASE_URL}/v1/vendors/inventory/low-stock`),
  getOutOfStockItems: () => axios.get(`${API_BASE_URL}/v1/vendors/inventory/out-of-stock`),
  deductStock: (orderId: number) => axios.post(`${API_BASE_URL}/v1/vendors/inventory/deduct/${orderId}`),
  restockItem: (itemId: number, quantity: number) => axios.post(`${API_BASE_URL}/v1/vendors/inventory/restock/${itemId}?quantity=${quantity}`),
  autoEnableItems: () => axios.post(`${API_BASE_URL}/v1/vendors/inventory/auto-enable`),
  sendInventoryAlerts: () => axios.post(`${API_BASE_URL}/v1/vendors/inventory/send-alerts`),

  // ── PHASE B: Analytics ──
  getAnalyticsDashboard: () => axios.get(`${API_BASE_URL}/v1/vendors/analytics/dashboard`),
  getDailySales: (days: number = 30) => axios.get(`${API_BASE_URL}/v1/vendors/analytics/daily?days=${days}`),
  getWeeklySales: (weeks: number = 12) => axios.get(`${API_BASE_URL}/v1/vendors/analytics/weekly?weeks=${weeks}`),
  getMonthlySales: (months: number = 12) => axios.get(`${API_BASE_URL}/v1/vendors/analytics/monthly?months=${months}`),
  getPeakHours: () => axios.get(`${API_BASE_URL}/v1/vendors/analytics/peak-hours`),
  getItemAnalysis: () => axios.get(`${API_BASE_URL}/v1/vendors/analytics/items`),
  getWasteAnalysis: () => axios.get(`${API_BASE_URL}/v1/vendors/analytics/waste`),
  getRevenueTrends: () => axios.get(`${API_BASE_URL}/v1/vendors/analytics/revenue-trends`),
  exportCsv: (reportType: string) => axios.get(`${API_BASE_URL}/v1/vendors/analytics/export/csv/${reportType}`, { responseType: 'blob' }),

  // ── PHASE C: AI Intelligence ──
  getAiDashboard: () => axios.get(`${API_BASE_URL}/v1/vendors/ai/dashboard`),
  getDailyForecast: (days: number = 7) => axios.get(`${API_BASE_URL}/v1/vendors/ai/forecast/daily?days=${days}`),
  getWeeklyForecast: (weeks: number = 4) => axios.get(`${API_BASE_URL}/v1/vendors/ai/forecast/weekly?weeks=${weeks}`),
  getMonthlyForecast: (months: number = 3) => axios.get(`${API_BASE_URL}/v1/vendors/ai/forecast/monthly?months=${months}`),
  getPopularItems: () => axios.get(`${API_BASE_URL}/v1/vendors/ai/popular-items`),
  getPeakTimes: () => axios.get(`${API_BASE_URL}/v1/vendors/ai/peak-times`),
  getWasteInsights: () => axios.get(`${API_BASE_URL}/v1/vendors/ai/waste-insights`),
  getInventorySuggestions: () => axios.get(`${API_BASE_URL}/v1/vendors/ai/inventory-suggestions`),
  getAiRecommendations: () => axios.get(`${API_BASE_URL}/v1/vendors/ai/recommendations`),

  // ── Enhanced Forecasting ──
  getComprehensiveForecast: () => axios.get(`${API_BASE_URL}/v1/vendor/forecast/comprehensive`),
  getShortTermForecast: () => axios.get(`${API_BASE_URL}/v1/vendor/forecast/short-term`),
  getDailyForecastEnhanced: (days: number = 7) => axios.get(`${API_BASE_URL}/v1/vendor/forecast/daily?days=${days}`),
  getWeeklyForecastEnhanced: (weeks: number = 4) => axios.get(`${API_BASE_URL}/v1/vendor/forecast/weekly?weeks=${weeks}`),
  getMonthlyForecastEnhanced: (months: number = 3) => axios.get(`${API_BASE_URL}/v1/vendor/forecast/monthly?months=${months}`),
  getRevenueForecast: (days: number = 30) => axios.get(`${API_BASE_URL}/v1/vendor/forecast/revenue?days=${days}`),
  getCustomerForecast: (days: number = 7) => axios.get(`${API_BASE_URL}/v1/vendor/forecast/customers?days=${days}`),

  // ── Performance Intelligence ──
  getPerformanceMetrics: (days: number = 30) => axios.get(`${API_BASE_URL}/v1/vendor/performance/metrics?days=${days}`),
  getVendorScore: () => axios.get(`${API_BASE_URL}/v1/vendor/performance/score`),
  getPerformanceReport: (days: number = 30) => axios.get(`${API_BASE_URL}/v1/vendor/performance/report?days=${days}`),
  getPerformanceHistory: (days: number = 90) => axios.get(`${API_BASE_URL}/v1/vendor/performance/history?days=${days}`),
  getForecastInsights: () => axios.get(`${API_BASE_URL}/v1/vendor/performance/insights/forecast`),
  getRecommendationInsights: () => axios.get(`${API_BASE_URL}/v1/vendor/performance/insights/recommendations`),
  getInventoryInsights: () => axios.get(`${API_BASE_URL}/v1/vendor/performance/insights/inventory`),
  getDashboardInsights: () => axios.get(`${API_BASE_URL}/v1/vendor/performance/insights/dashboard`),

  // ── AI Inventory Planning ──
  getAIInventoryPlan: () => axios.get(`${API_BASE_URL}/v1/vendors/inventory/ai/plan`),
  getItemsFinishing: () => axios.get(`${API_BASE_URL}/v1/vendors/inventory/ai/items-finishing`),
  getItemsToRestock: () => axios.get(`${API_BASE_URL}/v1/vendors/inventory/ai/items-restock`),
  getExpectedDemand: () => axios.get(`${API_BASE_URL}/v1/vendors/inventory/ai/demand`),
  getExpectedWastage: () => axios.get(`${API_BASE_URL}/v1/vendors/inventory/ai/wastage`),
  getRestockSuggestions: () => axios.get(`${API_BASE_URL}/v1/vendors/inventory/ai/restock-suggestions`),
  getWasteSuggestions: () => axios.get(`${API_BASE_URL}/v1/vendors/inventory/ai/waste-suggestions`),
  getPurchasePlan: () => axios.get(`${API_BASE_URL}/v1/vendors/inventory/ai/purchase-plan`),

  // ── Peak Hour Prediction ──
  getPeakHourPredictions: (daysAhead: number = 1) => axios.get(`${API_BASE_URL}/v1/vendor/peak-hours/predict?days_ahead=${daysAhead}`),
  getRushHours: (daysAhead: number = 1) => axios.get(`${API_BASE_URL}/v1/vendor/peak-hours/rush?days_ahead=${daysAhead}`),
  getQuietHours: (daysAhead: number = 1) => axios.get(`${API_BASE_URL}/v1/vendor/peak-hours/quiet?days_ahead=${daysAhead}`),
  getPeakHourHeatmap: (daysAhead: number = 1) => axios.get(`${API_BASE_URL}/v1/vendor/peak-hours/heatmap?days_ahead=${daysAhead}`),
  getCapacityRecommendations: (daysAhead: number = 1) => axios.get(`${API_BASE_URL}/v1/vendor/peak-hours/capacity?days_ahead=${daysAhead}`),
  getStaffSuggestions: (daysAhead: number = 1) => axios.get(`${API_BASE_URL}/v1/vendor/peak-hours/staff?days_ahead=${daysAhead}`),
  getWaitingTimeEstimates: (daysAhead: number = 1) => axios.get(`${API_BASE_URL}/v1/vendor/peak-hours/waiting?days_ahead=${daysAhead}`),

  // ── Forecast Validation ──
  validateForecast: (predictions: any[], actuals: any[], periodType: string = 'daily') =>
    axios.post(`${API_BASE_URL}/v1/vendor/forecast/validate`, {
      predictions, actuals, period_type: periodType,
    }),
  validateWithDatabase: (predictions: any[], daysBack: number = 30) =>
    axios.post(`${API_BASE_URL}/v1/vendor/forecast/validate/with-db`, {
      predictions, days_back: daysBack,
    }),
  getValidationHistory: (periodType: string = 'daily', limit: number = 50) =>
    axios.get(`${API_BASE_URL}/v1/vendor/forecast/validate/history?period_type=${periodType}&limit=${limit}`),

  // ── PHASE D: Promotion & Retention ──
  getCampaigns: () => axios.get(`${API_BASE_URL}/v1/vendors/promotions/campaigns`),
  createCampaign: (data: any) => axios.post(`${API_BASE_URL}/v1/vendors/promotions/campaigns`, data),
  toggleCampaign: (campaignId: number) => axios.put(`${API_BASE_URL}/v1/vendors/promotions/campaigns/${campaignId}/toggle`),
  getCoupons: () => axios.get(`${API_BASE_URL}/v1/vendors/promotions/coupons`),
  createCoupon: (data: any) => axios.post(`${API_BASE_URL}/v1/vendors/promotions/coupons`, data),
  deleteCoupon: (offerId: number) => axios.delete(`${API_BASE_URL}/v1/vendors/promotions/coupons/${offerId}`),
  getActivePromotions: () => axios.get(`${API_BASE_URL}/v1/vendors/promotions/active`),
  getAiSuggestedDiscounts: () => axios.get(`${API_BASE_URL}/v1/vendors/promotions/ai-suggestions`),
  sendPushCampaign: (data: any) => axios.post(`${API_BASE_URL}/v1/vendors/promotions/push-campaign`, data),
  notifyOffer: (offerId: number) => axios.post(`${API_BASE_URL}/v1/vendors/promotions/notify-offer/${offerId}`),
  getRetentionAnalytics: () => axios.get(`${API_BASE_URL}/v1/vendors/promotions/retention-analytics`),
  getCustomerSegments: () => axios.get(`${API_BASE_URL}/v1/vendors/promotions/customer-segments`),

  // Generic
  get: (url: string) => axios.get(`${API_BASE_URL}/v1${url.startsWith('/') ? url : `/${url}`}`),
};

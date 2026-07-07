import apiClient from './apiClient';

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
  booking_type?: string;
  stationery_jobs?: StationeryJobSummary[];
  is_faculty?: boolean;
  is_group?: boolean;
  is_delayed?: boolean;
  customer_notes?: string;
  is_preorder?: boolean;
  group_id?: number;
}

export interface StationeryJobSummary {
  id: number;
  service_id: number;
  quantity: number;
  amount: number;
  status: string;
  print_type?: string;
  paper_size?: string;
  duplex?: boolean;
  page_range?: string;
  notes?: string;
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

export interface DemandDashboard {
  vendor_id: number;
  demand_overview: any;
  stock_prediction: any;
  rush_prediction: any;
  ai_forecast: any;
  recommendations: any[];
}

export interface ComprehensiveForecast {
  short_term: any;
  daily: any;
  weekly: any;
  monthly: any;
  insights: string[];
}

export const vendorApi = {
  // ── Orders ─────────────────────────────────────────────────────
  getOrders: () => apiClient.get<OrdersResponse>(`/v1/vendors/orders`),
  acceptOrder: (orderId: number) => apiClient.put(`/v1/vendors/orders/${orderId}/accept`),
  prepareOrder: (orderId: number) => apiClient.put(`/v1/vendors/orders/${orderId}/prepare`),
  readyOrder: (orderId: number) => apiClient.put(`/v1/vendors/orders/${orderId}/ready`),
  completeOrder: (orderId: number) => apiClient.put(`/v1/vendors/orders/${orderId}/complete`),
  confirmPickup: (qrCode: string) => apiClient.post(`/v1/orders/qr/confirm`, null, {params: {qr_code: qrCode}}),
  confirmQRPickup: (qrCode: string) => apiClient.post(`/v1/orders/qr/pickup/confirm`, { qr_code: qrCode }),
  getOrderByQR: (qrCode: string) => apiClient.get(`/v1/orders/qr/${encodeURIComponent(qrCode)}`),
  // Single-scan pickup for a whole group order (Phase 9).
  confirmGroupPickup: (qrCode: string) => apiClient.post(`/v1/groups/pickup/confirm`, { qr_code: qrCode }),

  // ── Dashboard ──────────────────────────────────────────────────
  getDashboardMetrics: () => apiClient.get<DashboardMetrics>(`/v1/vendors/dashboard/`),
  getComprehensiveForecast: () => apiClient.get<ComprehensiveForecast>(`/v1/vendor/forecast/comprehensive`),
  getDemandDashboard: () => apiClient.get<DemandDashboard>(`/v1/vendors/demand-dashboard/`),
  getForecastByType: () => apiClient.get(`/v1/vendor/forecast/by-type`),

  // ── AI Inventory Plan ──────────────────────────────────────────
  getAIInventoryPlan: () => apiClient.get(`/v1/vendors/inventory/ai/plan`),
  getRestockSuggestions: () => apiClient.get(`/v1/vendors/inventory/ai/restock-suggestions`),

  // ── Performance Intelligence ───────────────────────────────────
  getPerformanceMetrics: (days: number = 30) => apiClient.get(`/v1/vendor/performance/metrics?days=${days}`),
  getVendorScore: () => apiClient.get(`/v1/vendor/performance/score`),
  getPerformanceHistory: (days: number = 90) => apiClient.get(`/v1/vendor/performance/history?days=${days}`),
  getDashboardInsights: () => apiClient.get(`/v1/vendor/performance/insights/dashboard`),

  // ── Loyalty / Rewards (vendor-facing) ──────────────────────────
  getVoucherList: () =>
    apiClient.get(`/v1/rewards/vouchers`),
  getRewardRules: () =>
    apiClient.get(`/v1/rewards/redemptions`),
};

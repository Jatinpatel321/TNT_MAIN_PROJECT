// ─── Auth ─────────────────────────────────────────────────────────────────────
export interface AdminUser {
  id: number;
  phone: string;
  role: 'admin' | 'super_admin';
  name: string;
}

export interface AuthState {
  token: string | null;
  user: AdminUser | null;
  isAuthenticated: boolean;
}

// ─── Analytics ────────────────────────────────────────────────────────────────
export interface AdminAnalytics {
  total_users: number;
  active_users: number;
  total_vendors: number;
  pending_vendors: number;
  total_orders: number;
  orders_today: number;
  total_revenue_paise: number;
  revenue_today_paise: number;
  active_vendors?: number;
  food_vendors?: number;
  stationery_vendors?: number;
  completed_today?: number;
  pending_today?: number;
}

// ─── Orders ───────────────────────────────────────────────────────────────────
export type OrderStatus = 'placed' | 'confirmed' | 'preparing' | 'ready' | 'picked' | 'cancelled';

export interface OrderItem {
  id: number;
  menu_item_id: number;
  name: string;
  quantity: number;
  unit_price: number;
}

export interface Order {
  id: number;
  user_id: number;
  vendor_id: number;
  slot_id: number;
  status: OrderStatus;
  total_amount: number;
  fraud_flag: boolean;
  fraud_reason?: string;
  created_at: string;
  items: OrderItem[];
  user_name?: string;
  vendor_name?: string;
  payment_method?: string;
  razorpay_payment_id?: string;
  slot_time?: string;
}

export interface OrderTimeline {
  event: string;
  actor: string;
  timestamp: string;
}

// ─── Vendors ──────────────────────────────────────────────────────────────────
export type VendorType = 'food' | 'stationery' | 'mixed';
export type VendorStatus = 'pending' | 'approved' | 'rejected' | 'inactive';

export interface VendorMeta {
  stall?: string;
  location?: string;
  business_name?: string;
  description?: string;
  email?: string;
  operating_hours?: Record<string, { open?: string; close?: string; closed?: boolean }>;
  slot_defaults?: {
    slot_duration_minutes?: number;
    default_capacity?: number;
    opening_time?: string;
    closing_time?: string;
  };
}

export interface Vendor {
  id: number;
  name: string;
  phone: string;
  vendor_type: VendorType;
  is_approved: boolean;
  is_active: boolean;
  location?: string;
  stall?: string;
  vendor_meta?: VendorMeta;
  created_at: string;
  rating?: number;
  total_orders?: number;
  total_revenue?: number;
  menu_count?: number;
  slot_count?: number;
  image_url?: string;
}

export interface MenuItem {
  id: number;
  vendor_id: number;
  name: string;
  price: number;
  prep_time_minutes: number;
  is_available: boolean;
  category?: string;
  description?: string;
  image_url?: string;
}

export interface TimeSlot {
  id: number;
  vendor_id: number;
  start_time: string;
  end_time: string;
  capacity: number;
  booked_count: number;
  is_active: boolean;
}

// ─── Users ────────────────────────────────────────────────────────────────────
export type UserRole = 'student' | 'faculty' | 'vendor' | 'admin' | 'super_admin';

export interface User {
  id: number;
  phone: string;
  name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  department?: string;
  year?: string;
  email?: string;
  reward_points?: number;
  total_orders?: number;
  complaints_filed?: number;
}

// ─── Complaints ───────────────────────────────────────────────────────────────
export type ComplaintStatus = 'open' | 'assigned' | 'resolved' | 'escalated';

export interface Complaint {
  id: number;
  user_id: number;
  vendor_id?: number;
  category: string;
  description: string;
  status: ComplaintStatus;
  assigned_to?: number;
  created_at: string;
  user_name?: string;
  vendor_name?: string;
  assigned_to_name?: string;
}

// ─── Vouchers & Rewards ───────────────────────────────────────────────────────
export interface Voucher {
  id: number;
  code: string;
  discount_type: 'flat' | 'percent';
  discount_value: number;
  expiry_date: string;
  max_redemptions: number;
  redemption_count: number;
  is_active: boolean;
}

export interface OffPeakPolicy {
  id?: number;
  time_windows: Array<{ start: string; end: string }>;
  bonus_points_per_order: number;
  multiplier?: number;
  is_active: boolean;
}

export interface OffPeakAuditEntry {
  id: number;
  changed_by: string;
  changed_at: string;
  previous_policy: Partial<OffPeakPolicy>;
  new_policy: Partial<OffPeakPolicy>;
  reason?: string;
}

// ─── AI Signals ───────────────────────────────────────────────────────────────
export interface RushHourSignal {
  level: 'low' | 'medium' | 'high' | 'critical';
  active_orders: number;
  score?: number;
  timestamp?: string;
}

export interface VendorRanking {
  vendor_id: number;
  vendor_name?: string;
  score?: number;
  vendor_rank_score: number;
  rank: number;
  trend?: 'up' | 'down' | 'stable';
  category?: string;
  source?: 'model' | 'heuristic';
  live_load_indicator?: string;  // LOW, MEDIUM, HIGH
  express_pickup_eligible?: boolean;
  reasoning?: string;
}

export interface DemandPlan {
  vendor_id: number;
  vendor_name: string;
  predicted_orders: number;
  current_capacity: number;
  recommended_capacity: number;
  status?: 'ok' | 'warning' | 'critical';
}

export interface SlotSuggestion {
  slot_id: number;
  vendor_id: number;
  vendor_name: string;
  slot_time?: string;
  utilization_percent?: number;
}

export interface ModelVersionInfo {
  version_id?: string;
  version_num?: number;
  status?: 'active' | 'archived';
  metrics?: Record<string, any>;
  cv_score?: number;
  cv_rmse?: number;
  cv_f1?: number;
  tuned_params?: Record<string, any>;
  created_at?: string;
}

export interface ModelAccuracyDetail {
  model_type: string;
  active_version?: ModelVersionInfo;
  versions?: ModelVersionInfo[];
  latest_backtest?: {
    status?: string;
    total_orders?: number;
    within_3_min_pct?: number;
    within_5_min_pct?: number;
    mae_minutes?: number;
    top_1_hit_rate?: number;
    top_3_hit_rate?: number;
    caveat?: string;
  };
  latest_drift?: {
    has_drift: boolean;
    drifted_features: string[];
    feature_psi: Record<string, number>;
    created_at?: string;
  };
  feature_importance?: Array<{ feature: string; importance: number }>;
}

export type ModelAccuracySummary = Record<string, ModelAccuracyDetail>;

export interface ReorderPrompt {
  user_id: number;
  vendor_id: number;
  likelihood_score: number;
  last_order_date: string;
}

export interface ETAMetrics {
  vendor_id: number;
  vendor_name: string;
  avg_predicted_eta: number;
  avg_actual_time: number;
  accuracy_percent: number;
}

export interface AISignals {
  rush_hour: RushHourSignal;
  slot_suggestions: SlotSuggestion[];
  reorder_prompts: ReorderPrompt[];
}

// ─── Health ───────────────────────────────────────────────────────────────────
export interface HealthStatus {
  status: 'ok' | 'degraded';
  db: 'ok' | 'error';
  redis: 'ok' | 'error';
  shutdown_active?: boolean;
}

// ─── Policies ─────────────────────────────────────────────────────────────────
export interface FacultyPriorityPolicy {
  time_windows: Array<{ start: string; end: string; priority_weight: number }>;
  discount_percent: number;
  is_active: boolean;
}

export interface UniversityPolicy {
  max_orders_per_user_per_day: number;
  allowed_categories: string[];
  break_windows: Array<{ start: string; end: string }>;
  is_active: boolean;
}

// ─── Stationery ───────────────────────────────────────────────────────────────
export type PrintJobStatus = 'pending' | 'processing' | 'ready' | 'completed' | 'cancelled';

export interface PrintJob {
  id: number;
  user_id: number;
  user_name?: string;
  vendor_id: number;
  vendor_name?: string;
  service_name: string;
  file_url?: string;
  quantity: number;
  print_type: 'bw' | 'color';
  paper_size: 'A4' | 'A3';
  duplex: boolean;
  page_range?: string;
  notes?: string;
  status: PrintJobStatus;
  payment_status: string;
  total_amount: number;
  submitted_at: string;
}

// ─── Ledger ───────────────────────────────────────────────────────────────────
export type LedgerEntryType = 'credit' | 'debit';

export interface LedgerEntry {
  id: number;
  user_id: number;
  user_name?: string;
  type: LedgerEntryType;
  amount: number;
  description: string;
  order_id?: number;
  source?: string;
  timestamp: string;
  balance_after?: number;
}

// ─── Notifications ────────────────────────────────────────────────────────────
export interface Notification {
  id: number;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
  type?: string;
}

// ─── Feedback ─────────────────────────────────────────────────────────────────
export interface FeedbackSummary {
  vendor_id: number;
  average_rating: number;
  total_reviews: number;
  rating_distribution: Record<number, number>;
  recent_reviews?: Array<{
    id: number;
    user_name: string;
    rating: number;
    comment: string;
    created_at: string;
  }>;
}

// ─── Vendor Analytics ─────────────────────────────────────────────────────────
export interface VendorAnalytics {
  vendor_id: number;
  total_orders: number;
  total_revenue: number;
  peak_hour: string;
  orders_by_day: Array<{ date: string; count: number }>;
  revenue_by_day: Array<{ date: string; amount: number }>;
}

// ─── Pagination ───────────────────────────────────────────────────────────────
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// ─── Institutional KPIs ──────────────────────────────────────────────────────────
export interface KPIData {
  filters: {
    date_from: string;
    date_to: string;
    department: string | null;
    vendor_id: number | null;
  };
  university_kpis: {
    total_orders: number;
    food_orders: number;
    stationery_orders: number;
    daily_trend: Array<{ date: string; count: number }>;
    weekly_trend: Array<{ date: string; count: number }>;
    monthly_trend: Array<{ date: string; count: number }>;
  };
  operational_kpis: {
    avg_waiting_time_minutes: number;
    queue_reduction_pct: number;
    avg_pickup_time_minutes: number;
    slot_utilization_pct: number;
    vendor_performance: Array<{
      vendor_id: number;
      vendor_name: string;
      orders_count: number;
      completion_rate: number;
      avg_wait_minutes: number;
      rating: number;
      score?: number;
    }>;
  };
  business_kpis: {
    revenue_inr: number;
    refunds_inr: number;
    cancellation_rate_pct: number;
    user_growth_count: number;
    vendor_growth_count: number;
  };
  engagement_kpis: {
    active_users: number;
    returning_users: number;
    peak_hours: number[];
    heatmap_grid: Record<number, Record<number, number>>;
    vouchers_redeemed_count: number;
    points_redeemed: number;
  };
  department_analytics?: Array<{
    department: string;
    order_count: number;
    active_users: number;
    revenue_inr: number;
  }>;
  food_trends?: Array<{
    date: string;
    orders: number;
    revenue_inr: number;
  }>;
  stationery_trends?: Array<{
    date: string;
    orders: number;
    revenue_inr: number;
  }>;
  revenue_trends?: Array<{
    date: string;
    revenue_inr: number;
  }>;
  peak_hour_analysis?: Array<{
    hour: number;
    food_orders: number;
    stationery_orders: number;
  }>;
  slot_usage_analysis?: Array<{
    hour: number;
    booked_orders: number;
    total_capacity: number;
    utilization_pct: number;
  }>;
  cancellation_trends?: Array<{
    date: string;
    cancelled_count: number;
    total_count: number;
    cancellation_rate: number;
  }>;
  ai_insights?: Array<{
    type: 'info' | 'warning' | 'success' | 'danger';
    title: string;
    detail: string;
    recommendation: string;
  }>;
}

// ─── Fraud Detection ──────────────────────────────────────────────────────────
export interface FraudAlert {
  id: number;
  user_id?: number;
  vendor_id?: number;
  order_id?: number;
  alert_type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  score: number;
  description?: string;
  status: 'pending' | 'resolved' | 'false_positive';
  resolution_notes?: string;
  created_at: string;
  updated_at: string;
  user_phone?: string;
  user_name?: string;
  vendor_name?: string;
}

export interface FraudAlertListResponse {
  alerts: FraudAlert[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface FraudMetrics {
  summary: {
    total_alerts: number;
    pending_alerts: number;
    resolved_alerts: number;
    false_positives: number;
    critical_alerts: number;
    blacklisted_users: number;
    blacklisted_vendors: number;
  };
  severity_distribution: {
    low: number;
    medium: number;
    high: number;
    critical: number;
  };
  type_distribution: Record<string, number>;
  recent_activity: Array<{
    id: number;
    alert_type: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
    user_name: string;
    created_at: string;
    status: 'pending' | 'resolved' | 'false_positive';
  }>;
}

export interface FraudAlertDetailResponse {
  alert: FraudAlert;
  user?: {
    id: number;
    name: string;
    phone: string;
    role: string;
    is_active: boolean;
    created_at: string;
    cumulative_fraud_score: number;
  };
  vendor?: {
    id: number;
    name: string;
    phone: string;
    status: string;
    is_active: boolean;
  };
  order?: {
    id: number;
    status: string;
    total_amount: number;
    created_at: string;
    booking_type: string;
  };
}


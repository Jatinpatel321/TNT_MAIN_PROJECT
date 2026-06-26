export type UserRole =
  | 'student'
  | 'faculty'
  | 'vendor'
  | 'admin'
  | 'super_admin';

export type User = {
  id: number;
  phone: string;
  name: string | null;
  full_name: string | null;
  role: UserRole;
  vendor_type: string | null;
  university_id: string | null;
  department: string | null;
  semester: number | null;
  profile_image: string | null;
  is_active: boolean;
  is_approved: boolean;
  preferences: Record<string, any> | null;
  created_at: string | null;
};

export type VendorType = 'food' | 'stationery';

export type Vendor = {
  id: number;
  name: string | null;
  description: string;
  vendor_type: string;
  is_approved: boolean;
  phone: string;
  is_open: boolean;
  logo_url: string | null;
  cover_image?: string | null;
  rating?: number;
  category?: string | null;
  location?: string | null;
  live_load_label: string;
  express_pickup_eligible: boolean;
};

export type MenuItem = {
  id: number;
  vendor_id: number;
  name: string;
  description: string | null;
  price: number;
  image_url: string;
  is_available: boolean;
  prep_time_minutes?: number | null;
  category?: string | null;
};

export type VendorSlot = {
  id: number;
  vendor_id: number;
  start_time: string;
  end_time: string;
  is_available: boolean;
  max_orders: number;
  current_orders: number;
  load_label: string;
  express_pickup_eligible: boolean;
};

export type CartItem = {
  menu_item_id: number;
  name: string;
  price: number;
  quantity: number;
};

export type Cart = {
  vendor_id: number | null;
  items: CartItem[];
  total_items: number;
  total_amount: number;
};

export type OrderItem = {
  menu_item_id: number;
  name: string;
  quantity: number;
  price_at_time: number;
  line_total?: number;
};

export type OrderStatusKey =
  | 'placed'
  | 'pending'
  | 'confirmed'
  | 'preparing'
  | 'ready'
  | 'ready_for_pickup'
  | 'picked'
  | 'completed'
  | 'cancelled';

// Stationery job summary embedded in a combined order
export type StationeryJobSummary = {
  id: number;
  service_id: number;
  quantity: number;
  amount: number;
  status: string;
};

export type Order = {
  id: number;
  user_id?: number;
  slot_id: number;
  vendor_id: number;
  vendor_name?: string;
  status: OrderStatusKey;
  created_at: string;
  total_amount?: number | null;
  qr_code?: string | null;
  items?: OrderItem[];
  eta_minutes?: number | null;
  is_delayed?: boolean | null;
  booking_type?: string; // 'food' | 'stationery' | 'combined'
  stationery_jobs?: StationeryJobSummary[] | null;
};

export type OrderHistoryItem = {
  status: string;
  changed_at: string;
};

export type NotificationTypeKey =
  | 'order_accepted'
  | 'order_preparing'
  | 'order_ready'
  | 'pickup_reminder'
  | 'delay_alert'
  | 'order_cancelled'
  | 'order_placed'
  | 'promo'
  | 'system';

export type NotificationItem = {
  id: number;
  user_id: number;
  title: string;
  message: string;
  notification_type: NotificationTypeKey;
  reference_id: number | null;
  is_read: boolean;
  created_at: string;
};

// Search types
export type SearchItemType = 'food' | 'stationery';

export type SearchItemResult = {
  id: number;
  vendor_id: number;
  name: string;
  description: string | null;
  price: number;
  item_type: SearchItemType;
  is_available: boolean;
  image_url: string | null;
  unit: string | null;
  vendor_name: string | null;
  vendor_rating: number;
  vendor_category: string | null;
};

export type SearchVendorResult = {
  id: number;
  name: string | null;
  vendor_type: string;
  description: string | null;
  rating: number;
  category: string | null;
  location: string | null;
  logo_url: string | null;
  is_open: boolean;
  live_load_label: string;
  express_pickup_eligible: boolean;
  matched_items: SearchItemResult[];
};

export type SearchResponse = {
  vendors: SearchVendorResult[];
  items: SearchItemResult[];
  total_vendors: number;
  total_items: number;
};

export type FeedbackRecord = {
  id: number;
  order_id: number;
  vendor_id: number;
  user_id: number;
  overall_rating: number | null;
  quality_rating: number;
  time_rating: number;
  behavior_rating: number;
  comment: string | null;
  created_at: string;
};

export type VendorReview = {
  id: number;
  vendor_id: number;
  user_id: number;
  order_id: number | null;
  rating: number;
  title: string | null;
  review_text: string | null;
  is_anonymous: boolean;
  reviewer_name: string | null;
  created_at: string;
};

export type VendorFeedbackSummary = {
  vendor_id: number;
  total_reviews: number;
  avg_quality_rating: number;
  avg_time_rating: number;
  avg_behavior_rating: number;
  avg_overall_rating: number;
  rating_distribution: Record<number, number>;
};

export type RewardTypeKey =
  | 'order_completion'
  | 'referral'
  | 'first_order'
  | 'loyalty_milestone'
  | 'off_peak_bonus'
  | 'voucher_redemption';

export type RedemptionTypeKey =
  | 'discount_percentage'
  | 'discount_fixed'
  | 'free_item';

export type RewardTransaction = {
  id: number;
  reward_type: RewardTypeKey;
  points: number;
  description: string;
  order_id: number | null;
  created_at: string;
};

export type RewardRedemption = {
  id: number;
  redemption_type: RedemptionTypeKey;
  points_used: number;
  value: number;
  description: string;
  order_id: number | null;
  created_at: string;
};

export type UserPoints = {
  current_points: number;
  total_earned: number;
  total_redeemed: number;
  recent_transactions: RewardTransaction[];
  recent_redemptions: RewardRedemption[];
};

export type RedemptionRule = {
  id: number;
  redemption_type: RedemptionTypeKey;
  min_points: number;
  max_discount_percentage: number | null;
  max_discount_amount: number | null;
};

export type Voucher = {
  id: number;
  code: string;
  description: string;
  discount_type: 'percentage' | 'fixed';
  discount_value: number;
  min_order_amount_paise: number;
  max_discount_amount_paise: number | null;
  usage_limit: number | null;
  times_redeemed: number;
  expires_at: string;
  is_active: boolean;
};

export type SearchSortOption =
  | 'popular'
  | 'price_low'
  | 'price_high'
  | 'fastest'
  | 'rating';

export type SearchFilters = {
  type?: 'all' | 'food' | 'stationery';
  category?: string;
  price_min?: number;
  price_max?: number;
  min_rating?: number;
  availability?: boolean;
  prep_time_max?: number;
  sort?: SearchSortOption;
};

// AI Recommendation types
export type VendorRecommendation = {
  vendor_id: number;
  vendor_name: string;
  vendor_type: string;
  category: string | null;
  logo_url: string | null;
  rank_score: number;
  live_load: string;
  express_pickup: boolean;
  reason: string;
};

export type MenuSuggestion = {
  item_id: number;
  item_name: string;
  vendor_id: number;
  vendor_name: string;
  price_paise: number;
  image_url: string | null;
  is_available: boolean;
  reason: string;
  confidence: number;
};

export type SmartReorderItem = {
  item_id: number;
  item_name: string;
  vendor_id: number;
  vendor_name: string;
  price_paise: number;
  image_url: string | null;
  order_count: number;
  last_ordered_at: string;
  suggested_quantity: number;
  suggested_slot_id: number | null;
  suggested_slot_time: string | null;
};

export type PickupTimeSlot = {
  slot_id: number;
  vendor_id: number;
  vendor_name: string;
  start_time: string;
  end_time: string;
  eta_minutes: number;
  congestion_level: string;
  delay_risk: string;
  score: number;
};

export type PeakHourPeriod = {
  start_hour: number;
  end_hour: number;
  label: string;
  severity: string;
  avg_wait_minutes: number;
  order_volume: number;
};

export type PeakHourAlertData = {
  is_peak_now: boolean;
  current_period: PeakHourPeriod | null;
  peak_periods_today: PeakHourPeriod[];
  off_peak_windows: { hour: number; label: string; expected_wait_minutes: number }[];
  suggested_action: string;
};

export type PopularNearbyVendor = {
  vendor_id: number;
  vendor_name: string;
  vendor_type: string;
  category: string | null;
  logo_url: string | null;
  order_count: number;
  avg_rating: number;
  live_load: string;
};

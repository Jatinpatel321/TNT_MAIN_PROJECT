import type { OrderStatus, VendorStatus, ComplaintStatus, PrintJobStatus } from '../types';

// ─── Order Status ─────────────────────────────────────────────────────────────
export const ORDER_STATUS_LABELS: Record<OrderStatus, string> = {
  placed: 'Placed',
  confirmed: 'Confirmed',
  preparing: 'Preparing',
  ready: 'Ready',
  picked_up: 'Picked Up',
  cancelled: 'Cancelled',
};

export const ORDER_STATUS_COLORS: Record<OrderStatus, string> = {
  placed: 'bg-blue-50 text-blue-600 border-blue-200',
  confirmed: 'bg-amber-50 text-amber-600 border-amber-200',
  preparing: 'bg-orange-50 text-orange-600 border-orange-200',
  ready: 'bg-green-50 text-green-600 border-green-200',
  picked_up: 'bg-teal-50 text-teal-600 border-teal-200',
  cancelled: 'bg-red-50 text-red-600 border-red-200',
};

export const TERMINAL_ORDER_STATUSES: OrderStatus[] = ['picked_up', 'cancelled'];
export const ACTIVE_ORDER_STATUSES: OrderStatus[] = ['placed', 'confirmed', 'preparing', 'ready'];

// ─── Vendor Status ────────────────────────────────────────────────────────────
export const VENDOR_STATUS_COLORS: Record<VendorStatus, string> = {
  pending: 'bg-amber-50 text-amber-600 border-amber-200',
  approved: 'bg-green-50 text-green-600 border-green-200',
  rejected: 'bg-red-50 text-red-600 border-red-200',
  inactive: 'bg-gray-50 text-gray-500 border-gray-200',
};

// ─── Complaint Status ─────────────────────────────────────────────────────────
export const COMPLAINT_STATUS_COLORS: Record<ComplaintStatus, string> = {
  open: 'bg-red-50 text-red-600 border-red-200',
  assigned: 'bg-amber-50 text-amber-600 border-amber-200',
  resolved: 'bg-green-50 text-green-600 border-green-200',
  escalated: 'bg-purple-50 text-purple-600 border-purple-200',
};

export const COMPLAINT_STATUS_LABELS: Record<ComplaintStatus, string> = {
  open: 'Open',
  assigned: 'Assigned',
  resolved: 'Resolved',
  escalated: 'Escalated',
};

// ─── Print Job Status ─────────────────────────────────────────────────────────
export const PRINT_JOB_STATUS_COLORS: Record<PrintJobStatus, string> = {
  pending: 'bg-amber-50 text-amber-600 border-amber-200',
  processing: 'bg-blue-50 text-blue-600 border-blue-200',
  ready: 'bg-green-50 text-green-600 border-green-200',
  completed: 'bg-teal-50 text-teal-600 border-teal-200',
  cancelled: 'bg-red-50 text-red-600 border-red-200',
};

// ─── Rush Hour Levels ─────────────────────────────────────────────────────────
export const RUSH_HOUR_COLORS = {
  low: { bg: 'bg-green-50', text: 'text-green-600', fill: '#22C55E' },
  medium: { bg: 'bg-amber-50', text: 'text-amber-600', fill: '#F59E0B' },
  high: { bg: 'bg-orange-50', text: 'text-orange-600', fill: '#F97316' },
  critical: { bg: 'bg-red-50', text: 'text-red-600', fill: '#EF4444' },
};

// ─── Sidebar Nav Items ────────────────────────────────────────────────────────
export const NAV_ITEMS = [
  { path: '/dashboard', label: 'Dashboard', icon: 'LayoutDashboard' },
  { path: '/users', label: 'Users', icon: 'Users' },
  { path: '/vendors', label: 'Vendors', icon: 'Store', badge: 'pendingVendors' },
  { path: '/orders', label: 'Orders', icon: 'ShoppingBag' },
  { path: '/complaints', label: 'Complaints', icon: 'MessageSquareWarning', badge: 'openComplaints' },
  { path: '/wastage', label: 'Wastage', icon: 'Trash2' },
  { path: '/rewards', label: 'Rewards', icon: 'Gift' },
  { path: '/stationery', label: 'Stationery', icon: 'Printer' },
  { path: '/ai', label: 'AI Intelligence', icon: 'Brain' },
  { path: '/ledger', label: 'Ledger', icon: 'BookOpen' },
  { path: '/announcements', label: 'Announcements', icon: 'Megaphone' },
  { path: '/policies', label: 'Policies', icon: 'Shield' },
  { path: '/settings', label: 'Settings', icon: 'Settings' },
] as const;

// ─── Chart Colors ─────────────────────────────────────────────────────────────
export const CHART_COLORS = {
  primary: '#4F46E5',
  secondary: '#2563EB',
  tertiary: '#22C55E',
  quaternary: '#F59E0B',
  quinary: '#EF4444',
};

// ─── Vendor Type Labels ───────────────────────────────────────────────────────
export const VENDOR_TYPE_LABELS = {
  food: 'Food Court',
  stationery: 'Stationery',
};

export const VENDOR_TYPE_COLORS = {
  food: 'bg-orange-50 text-orange-600 border-orange-200',
  stationery: 'bg-blue-50 text-blue-600 border-blue-200',
};

// ─── Role Labels ──────────────────────────────────────────────────────────────
export const ROLE_LABELS = {
  student: 'Student',
  faculty: 'Faculty',
  vendor: 'Vendor',
  admin: 'Admin',
  super_admin: 'Super Admin',
};

export const ROLE_COLORS = {
  student: 'bg-blue-50 text-blue-600 border-blue-200',
  faculty: 'bg-purple-50 text-purple-600 border-purple-200',
  vendor: 'bg-orange-50 text-orange-600 border-orange-200',
  admin: 'bg-teal-50 text-teal-600 border-teal-200',
  super_admin: 'bg-red-50 text-red-600 border-red-200',
};

// ─── API ──────────────────────────────────────────────────────────────────────
export const WS_BASE_URL = 'ws://localhost:8000';
export const API_BASE_URL = 'http://localhost:8000';
export const POLL_INTERVAL_STATS = 30_000; // 30s
export const POLL_INTERVAL_HEALTH = 10_000; // 10s
export const POLL_INTERVAL_ORDERS = 5_000; // 5s
export const POLL_INTERVAL_AI = 60_000; // 60s
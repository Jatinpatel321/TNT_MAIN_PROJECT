import api from './axios';

export const adminApi = {
  // Analytics
  getAnalytics: () =>
    api.get('/v1/admin/analytics'),

  getWastageAnalytics: () =>
    api.get('/v1/admin/analytics/wastage'),

  // Vendor management
  getVendors: () =>
    api.get('/v1/admin/vendors'),

  getVendorById: (id: number) =>
    api.get(`/v1/admin/vendors/${id}`),

  getVendorMenu: (id: number) =>
    api.get(`/v1/admin/vendors/${id}/menu`),

  getVendorSlots: (id: number) =>
    api.get(`/v1/admin/vendors/${id}/slots`),

  getPendingVendors: async () => {
    const res = await api.get('/v1/admin/vendors');
    if (Array.isArray(res.data)) {
      res.data = res.data.filter((v: any) => !v.is_approved && v.is_active !== false);
    }
    return res;
  },

  approveVendor: (id: number) =>
    api.post(`/v1/admin/vendors/${id}/approve`),

  rejectVendor: (id: number) =>
    api.post(`/v1/admin/vendors/${id}/reject`),

  createVendor: (payload: {
    phone: string;
    name: string;
    vendor_type: 'food' | 'stationery' | 'mixed';
    is_approved?: boolean;
    stall?: string | null;
    location?: string | null;
    business_name?: string | null;
    description?: string | null;
    email?: string | null;
    operating_hours?: Record<string, unknown> | null;
    slot_defaults?: Record<string, unknown> | null;
  }) => api.post('/v1/admin/vendors', payload),

  updateVendor: (
    id: number,
    payload: Partial<{
      name: string;
      vendor_type: 'food' | 'stationery' | 'mixed';
      is_approved: boolean;
      is_active: boolean;
      stall: string | null;
      location: string | null;
      business_name: string | null;
      description: string | null;
      email: string | null;
      operating_hours: Record<string, unknown> | null;
      slot_defaults: Record<string, unknown> | null;
    }>,
  ) => api.patch(`/v1/admin/vendors/${id}`, payload),

  bulkApproveVendors: (ids: number[]) =>
    api.post('/v1/admin/vendors/bulk-approve', { vendor_ids: ids }),

  // User management
  toggleUser: (id: number) =>
    api.post(`/v1/admin/users/${id}/toggle`),

  getUsers: (params?: {
    page?: number;
    page_size?: number;
    search?: string;
    role?: string;
    is_active?: boolean;
  }) =>
    api.get('/v1/admin/users', { params }),

  updateUserStatus: (id: number, is_active: boolean) =>
    api.patch(`/v1/admin/users/${id}/status`, { is_active }),

  bulkUserAction: (user_ids: number[], action: 'block' | 'unblock') =>
    api.post('/v1/admin/users/bulk-action', { user_ids, action }),

  // Maintenance mode
  getMaintenance: () =>
    api.get('/v1/admin/maintenance'),

  setMaintenance: (enabled: boolean, message?: string) =>
    api.post('/v1/admin/maintenance', { enabled, message }),

  // Permission matrix
  getPermissionMatrix: () =>
    api.get('/v1/admin/permission-matrix'),

  // Slot management — global config + templates
  getSlotConfig: () =>
    api.get('/v1/admin/slot-config'),

  setSlotConfig: (payload: Record<string, string>) =>
    api.post('/v1/admin/slot-config', payload),

  getSlotTemplates: () =>
    api.get('/v1/admin/slot-templates'),

  createSlotTemplate: (payload: {
    name: string;
    vendor_id?: number | null;
    day_of_week?: number | null;
    start_time: string;
    end_time: string;
    slot_duration_minutes: number;
    max_orders_per_slot: number;
  }) => api.post('/v1/admin/slot-templates', payload),

  updateSlotTemplate: (id: number, payload: Record<string, unknown>) =>
    api.patch(`/v1/admin/slot-templates/${id}`, payload),

  deleteSlotTemplate: (id: number) =>
    api.delete(`/v1/admin/slot-templates/${id}`),

  generateSlotsFromTemplate: (id: number, payload: { vendor_id?: number | null; date_from: string; date_to: string }) =>
    api.post(`/v1/admin/slot-templates/${id}/generate`, payload),

  // Orders
  getAllOrders: (params?: Record<string, unknown>) =>
    api.get('/v1/admin/orders', { params }),

  flagOrderFraud: (id: number) =>
    api.post(`/v1/admin/orders/${id}/fraud`),

  // Ledger
  getLedger: (params?: Record<string, unknown>) =>
    api.get('/v1/admin/ledger', { params }),

  addLedgerAdjustment: (payload: {
    type: 'credit' | 'debit';
    amount: number;
    description?: string;
    order_id?: number | null;
  }) => api.post('/v1/admin/ledger/adjustment', payload),

  // Stationery — printer monitoring
  getPrinters: () =>
    api.get('/v1/admin/printers'),

  createPrinter: (payload: {
    name: string;
    location?: string | null;
    model?: string | null;
    vendor_id?: number | null;
    queue_depth?: number;
    ink_level_pct?: number;
    paper_count?: number;
    capacity_pages_per_hour?: number;
  }) => api.post('/v1/admin/printers', payload),

  updatePrinter: (id: number, payload: Record<string, unknown>) =>
    api.patch(`/v1/admin/printers/${id}`, payload),

  deletePrinter: (id: number) =>
    api.delete(`/v1/admin/printers/${id}`),

  // Stationery — print cost matrix
  getPrintCostMatrix: () =>
    api.get('/v1/admin/print-cost-matrix'),

  upsertPrintCost: (payload: {
    vendor_id?: number | null;
    print_type: 'bw' | 'color';
    paper_size: 'A4' | 'A3';
    duplex: boolean;
    price_per_page_paise: number;
  }) => api.put('/v1/admin/print-cost-matrix', payload),

  deletePrintCost: (id: number) =>
    api.delete(`/v1/admin/print-cost-matrix/${id}`),

  // Finance — settlements
  getSettlements: (params?: { status?: string }) =>
    api.get('/v1/admin/settlements', { params }),

  approveSettlement: (id: number) =>
    api.post(`/v1/admin/settlements/${id}/approve`),

  // Finance — refund requests
  getRefundRequests: (params?: { status?: string }) =>
    api.get('/v1/admin/refund-requests', { params }),

  approveRefundRequest: (id: number) =>
    api.post(`/v1/admin/refund-requests/${id}/approve`),

  rejectRefundRequest: (id: number, note: string) =>
    api.post(`/v1/admin/refund-requests/${id}/reject`, { note }),

  // Shutdown
  toggleShutdown: (enabled: boolean = true) =>
    api.post('/v1/admin/shutdown', null, { params: { enabled } }),

  // Announcements — legacy
  sendAnnouncement: (_title: string, message: string) =>
    api.post('/v1/admin/announce', null, { params: { message } }),

  // Broadcasts — persistent, with severity & audience
  getBroadcasts: (params?: { limit?: number; offset?: number }) =>
    api.get('/v1/admin/broadcasts', { params }),

  sendBroadcast: (payload: {
    title: string;
    message: string;
    severity: string;
    audience: string;
    vendor_id?: number | null;
  }) =>
    api.post('/v1/admin/broadcasts', payload),

  // Policies
  getFacultyPolicy: () =>
    api.get('/v1/admin/policies/faculty-priority'),

  setFacultyPolicy: (policy: any) =>
    api.post('/v1/admin/policies/faculty-priority', null, {
      params: {
        enabled: policy.is_active,
        start_hour: policy.time_windows?.[0]?.start ? parseInt(policy.time_windows[0].start.split(':')[0]) : 12,
        end_hour: policy.time_windows?.[0]?.end ? parseInt(policy.time_windows[0].end.split(':')[0]) : 14,
      },
    }),

  getUniversityPolicy: () =>
    api.get('/v1/admin/policies/university'),

  setUniversityPolicy: (policy: any) =>
    api.post('/v1/admin/policies/university', null, {
      params: {
        enabled: policy.is_active,
        break_start_hour: policy.break_windows?.[0]?.start ? parseInt(policy.break_windows[0].start.split(':')[0]) : 12,
        break_end_hour: policy.break_windows?.[0]?.end ? parseInt(policy.break_windows[0].end.split(':')[0]) : 14,
        max_orders_per_user: policy.max_orders_per_user_per_day ?? 3,
        min_slot_duration_minutes: 15,
      },
    }),

  // Health
  getHealth: () =>
    api.get('/health'),

  // Audit logs
  getAuditLogs: (params?: {
    page?: number;
    page_size?: number;
    search?: string;
    action_category?: string;
    actor_role?: string;
    date_from?: string;
    date_to?: string;
  }) =>
    api.get('/v1/admin/audit-logs', { params }),

  getAuditStats: () =>
    api.get('/v1/admin/audit-logs/stats'),

  getAuditTimeline: (actorId: number, params?: { page?: number; page_size?: number }) =>
    api.get(`/v1/admin/audit-logs/timeline/${actorId}`, { params }),

  exportAuditLogs: (params?: {
    actor_role?: string;
    action_category?: string;
    date_from?: string;
    date_to?: string;
  }) =>
    api.get('/v1/admin/audit-logs/export', { params, responseType: 'blob' }),

  // Conflict resolution
  getConflicts: () =>
    api.get('/v1/admin/conflicts'),

  // Backup & Restore — Enhanced
  getBackupList: (params?: {
    page?: number;
    page_size?: number;
    backup_type?: string;
    status?: string;
  }) =>
    api.get('/v1/admin/backups', { params }),

  getBackupDetail: (id: number) =>
    api.get(`/v1/admin/backups/${id}`),

  triggerBackup: () =>
    api.post('/v1/admin/backup/run'),

  deleteBackup: (id: number) =>
    api.delete(`/v1/admin/backups/${id}`),

  restoreBackup: (backupId: number, confirmPhrase: string) =>
    api.post('/v1/admin/backup/restore', {
      backup_id: backupId,
      confirm_phrase: confirmPhrase,
    }),

  getStorageStats: () =>
    api.get('/v1/admin/backup/storage'),

  getSchedulerStatus: () =>
    api.get('/v1/admin/backup/scheduler'),

  verifyBackup: (id: number) =>
    api.get(`/v1/admin/backup/verify/${id}`),

  // Legacy aliases
  getBackups: (params?: { page?: number; page_size?: number }) =>
    api.get('/v1/admin/backups', { params }),

  exportOrders: (params?: { date_from?: string; date_to?: string; status?: string }) =>
    api.get('/v1/admin/export/orders', { params, responseType: 'blob' }),

  exportUsers: (params?: { role?: string; is_active?: boolean }) =>
    api.get('/v1/admin/export/users', { params, responseType: 'blob' }),

  exportVendors: () =>
    api.get('/v1/admin/export/vendors', { responseType: 'blob' }),

  exportComplaints: (params?: { status?: string }) =>
    api.get('/v1/admin/export/complaints', { params, responseType: 'blob' }),

  exportRevenue: (params?: { date_from?: string; date_to?: string }) =>
    api.get('/v1/admin/export/revenue', { params, responseType: 'blob' }),

  getAnalyticsTrends: (days?: number) =>
    api.get('/v1/admin/analytics/trends', { params: { days: days ?? 30 } }),

  getKPIs: (params?: {
    date_from?: string;
    date_to?: string;
    department?: string;
    vendor_id?: number;
  }) =>
    api.get('/v1/admin/analytics/kpis', { params }),

  exportKPIs: (params: {
    format: 'excel' | 'pdf';
    date_from?: string;
    date_to?: string;
    department?: string;
    vendor_id?: number;
  }) =>
    api.get('/v1/admin/export/kpis', { params, responseType: 'blob' }),

  // Holiday & Exam Calendar
  getCalendarEvents: (params?: { year?: number; month?: number; event_type?: string }) =>
    api.get('/v1/admin/calendar-events/', { params }),

  createCalendarEvent: (payload: {
    event_date: string;
    label: string;
    event_type: string;
    affects_ordering?: boolean;
    description?: string | null;
  }) =>
    api.post('/v1/admin/calendar-events/', payload),

  deleteCalendarEvent: (id: number) =>
    api.delete(`/v1/admin/calendar-events/${id}`),

  checkCalendarDate: (event_date: string) =>
    api.get('/v1/admin/calendar-events/check-date', { params: { event_date } }),

  // Fraud Detection Endpoints
  getFraudAlerts: (params?: {
    page?: number;
    page_size?: number;
    alert_type?: string;
    severity?: string;
    status?: string;
    search?: string;
  }) =>
    api.get('/v1/admin/fraud/alerts', { params }),

  getFraudAlertDetail: (id: number) =>
    api.get(`/v1/admin/fraud/alerts/${id}`),

  resolveFraudAlert: (id: number, notes: string) =>
    api.post(`/v1/admin/fraud/alerts/${id}/resolve`, { notes }),

  markFalsePositive: (id: number, notes: string) =>
    api.post(`/v1/admin/fraud/alerts/${id}/false-positive`, { notes }),

  blacklistUser: (userId: number) =>
    api.post(`/v1/admin/fraud/users/${userId}/blacklist`),

  blacklistVendor: (vendorId: number) =>
    api.post(`/v1/admin/fraud/vendors/${vendorId}/blacklist`),

  triggerFraudScan: () =>
    api.post('/v1/admin/fraud/scan'),

  getFraudMetrics: () =>
    api.get('/v1/admin/fraud/metrics'),

  // Security Dashboard Endpoints
  getSecurityMetrics: () =>
    api.get('/v1/admin/security/metrics'),

  getSecurityEvents: (params?: { limit?: number }) =>
    api.get('/v1/admin/security/events', { params }),

  getActiveSessions: () =>
    api.get('/v1/admin/security/sessions'),

  revokeSession: (tokenKey: string) =>
    api.delete(`/v1/admin/security/sessions/${tokenKey}`),

  getBlockedTargets: () =>
    api.get('/v1/admin/security/ip-blocks'),

  blockTarget: (payload: { target: string; reason: string; duration_seconds?: number }) =>
    api.post('/v1/admin/security/ip-blocks', payload),

  unblockTarget: (target: string) =>
    api.delete(`/v1/admin/security/ip-blocks/${target}`),

  changeUserRole: (userId: number, role: string) =>
    api.patch(`/v1/admin/users/${userId}/role`, { role }),

  // System Health Endpoints
  getSystemHealthMetrics: () =>
    api.get('/v1/admin/health/metrics'),

  getSystemHealthStatus: () =>
    api.get('/v1/admin/health/status'),
};

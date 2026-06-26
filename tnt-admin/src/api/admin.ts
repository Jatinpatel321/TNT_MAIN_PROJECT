import api from './axios';

export const adminApi = {
  // Analytics
  getAnalytics: () =>
    api.get('/v1/admin/analytics'),

  // Vendor management
  getVendors: () =>
    api.get('/v1/admin/vendors'),

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

  // Orders
  getAllOrders: (params?: Record<string, unknown>) =>
    api.get('/v1/admin/orders', { params }),

  flagOrderFraud: (id: number) =>
    api.post(`/v1/admin/orders/${id}/fraud`),

  // Ledger
  getLedger: (params?: Record<string, unknown>) =>
    api.get('/v1/admin/ledger', { params }),

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
};

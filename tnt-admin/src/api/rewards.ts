import api from './axios';
import type { Voucher, OffPeakPolicy, OffPeakAuditEntry } from '../types';

export const rewardsApi = {
  getPoints: () =>
    api.get('/v1/rewards/points'),

  getRedemptions: () =>
    api.get('/v1/rewards/redemptions'),

  // Vouchers
  createVoucher: (data: Partial<Voucher>) =>
    api.post<Voucher>('/v1/rewards/vouchers', data),

  getVouchers: () =>
    api.get<Voucher[]>('/v1/rewards/vouchers'),

  updateVoucher: (id: number, data: Partial<Voucher>) =>
    api.put<Voucher>(`/v1/rewards/vouchers/${id}`, data),

  deleteVoucher: (id: number) =>
    api.delete(`/v1/rewards/vouchers/${id}`),

  // Off-peak policy
  getOffPeakPolicy: () =>
    api.get<OffPeakPolicy>('/v1/rewards/offpeak-policy'),

  setOffPeakPolicy: (policy: Partial<OffPeakPolicy>) =>
    api.post<OffPeakPolicy>('/v1/rewards/offpeak-policy', policy),

  getOffPeakAudit: () =>
    api.get<OffPeakAuditEntry[]>('/v1/rewards/offpeak-policy/audit'),
};

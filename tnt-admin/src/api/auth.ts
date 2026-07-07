import api from './axios';

export const authApi = {
  sendOtp: (phone: string) =>
    api.post('/v1/auth/send-otp', { phone }),

  verifyOtp: (phone: string, otp: string) =>
    api.post('/v1/auth/verify-otp', { phone, otp }),

  /** Verify TOTP code after OTP login when admin has 2FA enabled. */
  verifyAdmin2fa: (totpCode: string, token: string) =>
    api.post('/v1/auth/admin/2fa/verify', null, {
      params: { totp_code: totpCode },
      headers: { Authorization: `Bearer ${token}` },
    }),
};

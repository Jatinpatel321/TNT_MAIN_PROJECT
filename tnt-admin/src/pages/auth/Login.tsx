import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, RefreshCw, Shield, CheckCircle, KeyRound } from 'lucide-react';
import logo from '../../assets/TAP N TAKE_page-0001 (1).jpg';
import { jwtDecode } from 'jwt-decode';
import { AxiosError } from 'axios';
import toast from 'react-hot-toast';
import { authApi } from '../../api/auth';
import { useAuthStore } from '../../store/authStore';
import type { AdminUser } from '../../types';

interface JWTPayload {
  sub: string;
  role: string;
  name?: string;
  id?: number;
  exp?: number;
}

/** Shape returned by /v1/auth/verify-otp on success. */
interface VerifyOtpResponse {
  success: boolean;
  data: {
    access_token: string;
    refresh_token?: string;
    token_type?: string;
    requires_2fa?: boolean;
    user: {
      id: number;
      phone: string;
      name: string;
      role: string;
      [key: string]: unknown;
    };
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

export default function Login() {
  const navigate = useNavigate();
  const { setAuth, isAuthenticated, token, user } = useAuthStore();

  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [totpCode, setTotpCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const otpRefs = useRef<(HTMLInputElement | null)[]>([]);
  const totpRef = useRef<HTMLInputElement | null>(null);

  /** Store the pending auth values until 2FA is verified. */
  const [pendingAuth, setPendingAuth] = useState<{
    token: string;
    user: AdminUser;
  } | null>(null);

  useEffect(() => {
    if (isAuthenticated && token && user) navigate('/dashboard');
  }, [isAuthenticated, token, user, navigate]);

  useEffect(() => {
    if (countdown <= 0) return;
    const timer = setTimeout(() => setCountdown((c) => c - 1), 1000);
    return () => clearTimeout(timer);
  }, [countdown]);

  const validatePhone = (ph: string) => /^[6-9]\d{9}$/.test(ph);

  const handleSendOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validatePhone(phone)) {
      toast.error('Enter a valid 10-digit Indian mobile number');
      return;
    }

    setLoading(true);
    try {
      await authApi.sendOtp(`+91${phone}`);
      setStep(2);
      setCountdown(30);
      toast.success('OTP sent to your mobile number');
      setTimeout(() => otpRefs.current[0]?.focus(), 100);
    } catch {
      toast.error('Failed to send OTP');
    } finally {
      setLoading(false);
    }
  };

  const handleOTPChange = (index: number, value: string) => {
    if (!/^\d*$/.test(value)) return;

    const newOtp = [...otp];
    newOtp[index] = value.slice(-1);
    setOtp(newOtp);

    if (value && index < 5) {
      otpRefs.current[index + 1]?.focus();
    }

    if (index === 5 && value && newOtp.every((d) => d)) {
      handleVerifyOTP(newOtp.join(''));
    }
  };

  const handleOTPKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      otpRefs.current[index - 1]?.focus();
    }
    if (e.key === 'ArrowLeft' && index > 0) {
      otpRefs.current[index - 1]?.focus();
    }
    if (e.key === 'ArrowRight' && index < 5) {
      otpRefs.current[index + 1]?.focus();
    }
  };

  const handleOTPPaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (pasted.length === 6) {
      const newOtp = pasted.split('');
      setOtp(newOtp);
      otpRefs.current[5]?.focus();
      handleVerifyOTP(pasted);
    }
  };

  const handleVerifyOTP = async (otpString?: string) => {
    const code = otpString || otp.join('');
    if (code.length !== 6) {
      toast.error('Please enter the complete 6-digit OTP');
      return;
    }

    setLoading(true);
    try {
      const res = await authApi.verifyOtp(`+91${phone}`, code);
      const data = res.data as VerifyOtpResponse;
      const { access_token, token: legacyToken, user, requires_2fa } = data.data;
      const authToken = (access_token || legacyToken) as string;

      if (!authToken) {
        throw new Error('Login response did not include an access token');
      }

      const decoded = jwtDecode<JWTPayload>(authToken);

      if (!['ADMIN', 'SUPER_ADMIN', 'admin', 'super_admin'].includes(decoded.role)) {
        toast.error('Access denied — Admin only portal');
        setLoading(false);
        return;
      }

      const adminUser: AdminUser = {
        id: decoded.id || user?.id || 0,
        phone: `+91${phone}`,
        role: decoded.role as 'admin' | 'super_admin',
        name: decoded.name || user?.name || 'Admin',
      };

      // If the backend says this admin has 2FA enabled, show the TOTP step
      if (requires_2fa === true) {
        setPendingAuth({ token: authToken, user: adminUser });
        setStep(3);
        setTimeout(() => totpRef.current?.focus(), 100);
        return;
      }

      // No 2FA — complete login immediately
      setAuth(authToken, adminUser);
      toast.success(`Welcome back, ${adminUser.name}!`);
      navigate('/dashboard');
    } catch (err) {
      const status = err instanceof AxiosError ? err.response?.status : undefined;
      const message = err instanceof Error ? err.message : '';
      const isOtpFailure = status === 400 || /otp/i.test(message);

      toast.error(isOtpFailure ? 'Invalid OTP. Please try again.' : 'Login failed. Please try again.');
      setOtp(['', '', '', '', '', '']);
      otpRefs.current[0]?.focus();
    } finally {
      setLoading(false);
    }
  };

  /** Verify the TOTP code from the authenticator app (step 3). */
  const handleVerifyTOTP = async () => {
    const code = totpCode.trim();
    if (code.length !== 6 || !/^\d{6}$/.test(code)) {
      toast.error('Enter a valid 6-digit authenticator code');
      return;
    }

    if (!pendingAuth) {
      toast.error('Session expired — please log in again');
      setStep(1);
      return;
    }

    setLoading(true);
    try {
      await authApi.verifyAdmin2fa(code, pendingAuth.token);

      // 2FA passed — complete authentication and route to dashboard
      setAuth(pendingAuth.token, pendingAuth.user);
      setPendingAuth(null);
      toast.success(`Welcome back, ${pendingAuth.user.name}!`);
      navigate('/dashboard');
    } catch (err) {
      const status = err instanceof AxiosError ? err.response?.status : undefined;
      if (status === 401) {
        toast.error('Invalid authenticator code — try again');
      } else {
        toast.error('2FA verification failed');
      }
      setTotpCode('');
      totpRef.current?.focus();
    } finally {
      setLoading(false);
    }
  };

  const handleResendOTP = async () => {
    if (countdown > 0) return;
    setLoading(true);
    try {
      await authApi.sendOtp(`+91${phone}`);
      setCountdown(30);
      setOtp(['', '', '', '', '', '']);
      toast.success('OTP resent');
      setTimeout(() => otpRefs.current[0]?.focus(), 100);
    } catch {
      toast.error('Failed to resend OTP');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F7F8FC] flex items-center justify-center relative overflow-hidden">
      {/* Background effects */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-indigo-100 rounded-full blur-3xl opacity-60" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-orange-100 rounded-full blur-3xl opacity-60" />
        <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-50 rounded-full blur-2xl" />
      </div>

      <div className="relative z-10 w-full max-w-md px-6">
        {/* Logo */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-white border-2 border-[#E5E7EB] shadow-lg mb-5 overflow-hidden">
            <img src={logo} alt="TAP N TAKE Logo" className="w-full h-full object-cover" />
          </div>
          <h1 className="text-3xl font-bold text-[#111827] mb-1">
            TNT Admin
          </h1>
          <p className="text-[#4B5563] text-sm">Tap N Take — Parul University</p>
        </div>

        {/* Step indicators — show dynamic labels for 3-step flow */}
        <div className="flex items-center justify-center gap-3 mb-8">
          {[1, 2, 3].map((s) => (
            <React.Fragment key={s}>
              <div className={`flex items-center gap-2 ${s <= step ? 'text-[#E85D24]' : 'text-[#9CA3AF]'}`}>
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-all duration-300
                    ${s < step ? 'bg-[#E85D24] border-[#E85D24] text-white' :
                      s === step ? 'border-[#E85D24] text-[#E85D24]' :
                        'border-[#E5E7EB] text-[#9CA3AF]'}`}
                >
                  {s < step ? <CheckCircle className="w-3.5 h-3.5" /> : s}
                </div>
                <span className="text-xs font-medium hidden sm:inline">
                  {s === 1 ? 'Phone' : s === 2 ? 'OTP' : '2FA'}
                </span>
              </div>
              {s < 3 && (
                <div
                  className={`flex-1 h-0.5 max-w-[40px] transition-all duration-500 ${
                    step > s ? 'bg-[#E85D24]' : 'bg-[#E5E7EB]'
                  }`}
                />
              )}
            </React.Fragment>
          ))}
        </div>

        {/* Card */}
        <div className="bg-white border border-[#E5E7EB] rounded-2xl p-8 shadow-[0_1px_2px_rgba(0,0,0,0.03),0_8px_24px_rgba(0,0,0,0.04)]">
          {/* STEP 1 — Phone Number */}
          {step === 1 && (
            <>
              <h2 className="text-xl font-semibold text-[#111827] mb-1">Sign In</h2>
              <p className="text-sm text-[#4B5563] mb-6">Enter your admin mobile number</p>

              <form onSubmit={handleSendOTP} className="space-y-5">
                <div>
                  <label className="tnt-label">Mobile Number</label>
                  <div className="flex gap-2">
                    <div className="flex items-center gap-2 bg-[#F3F5F9] border border-[#E5E7EB] rounded-xl px-3 py-2.5 text-[#4B5563] text-sm font-medium shrink-0">
                      <span className="text-base">🇮🇳</span>
                      <span>+91</span>
                    </div>
                    <input
                      type="tel"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value.replace(/\D/g, '').slice(0, 10))}
                      placeholder="9876543210"
                      className="tnt-input flex-1"
                      autoFocus
                      required
                      inputMode="numeric"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading || phone.length !== 10}
                  className="btn-primary w-full justify-center py-3 text-base font-semibold"
                >
                  {loading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Sending OTP...
                    </>
                  ) : (
                    <>
                      Send OTP
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </form>
            </>
          )}

          {/* STEP 2 — OTP Verification */}
          {step === 2 && (
            <>
              <div className="flex items-center gap-2 mb-1">
                <button
                  onClick={() => {
                    setStep(1);
                    setOtp(['', '', '', '', '', '']);
                  }}
                  className="text-[#9CA3AF] hover:text-[#111827] transition-colors"
                >
                  ←
                </button>
                <h2 className="text-xl font-semibold text-[#111827]">Verify OTP</h2>
              </div>
              <p className="text-sm text-[#4B5563] mb-6 ml-6">
                Sent to{' '}
                <span className="text-[#111827] font-medium">
                  +91 {phone.slice(0, 5)} {phone.slice(5)}
                </span>
              </p>

              <div className="space-y-5">
                {/* OTP Input Boxes */}
                <div>
                  <label className="tnt-label">6-Digit OTP</label>
                  <div className="flex gap-2 justify-between" onPaste={handleOTPPaste}>
                    {otp.map((digit, index) => (
                      <input
                        key={index}
                        ref={(el) => {
                          otpRefs.current[index] = el;
                        }}
                        type="text"
                        inputMode="numeric"
                        maxLength={1}
                        value={digit}
                        onChange={(e) => handleOTPChange(index, e.target.value)}
                        onKeyDown={(e) => handleOTPKeyDown(index, e)}
                        title={`OTP digit ${index + 1}`}
                        className="w-12 h-14 text-center text-xl font-bold
                                   bg-[#F3F5F9] border-2 border-[#E5E7EB] rounded-xl
                                   text-[#111827] focus:outline-none focus:border-[#4F46E5]
                                   transition-all duration-150"
                      />
                    ))}
                  </div>
                </div>

                <button
                  onClick={() => handleVerifyOTP()}
                  disabled={loading || otp.some((d) => !d)}
                  className="btn-primary w-full justify-center py-3 text-base font-semibold"
                >
                  {loading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Verifying...
                    </>
                  ) : (
                    <>
                      <Shield className="w-4 h-4" />
                      Verify & Sign In
                    </>
                  )}
                </button>

                {/* Resend */}
                <div className="text-center">
                  {countdown > 0 ? (
                    <p className="text-sm text-[#4B5563]">
                      Resend OTP in{' '}
                      <span className="text-[#E85D24] font-medium font-mono">{countdown}s</span>
                    </p>
                  ) : (
                    <button
                      onClick={handleResendOTP}
                      disabled={loading}
                      className="text-sm text-[#E85D24] hover:text-[#F97316] font-medium
                                 inline-flex items-center gap-1.5 transition-colors"
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                      Resend OTP
                    </button>
                  )}
                </div>
              </div>
            </>
          )}

          {/* STEP 3 — TOTP 2FA Verification */}
          {step === 3 && (
            <>
              <div className="flex items-center gap-2 mb-1">
                <button
                  onClick={() => {
                    setStep(2);
                    setPendingAuth(null);
                    setTotpCode('');
                  }}
                  className="text-[#9CA3AF] hover:text-[#111827] transition-colors"
                >
                  ←
                </button>
                <h2 className="text-xl font-semibold text-[#111827]">Two-Factor Auth</h2>
              </div>
              <p className="text-sm text-[#4B5563] mb-2 ml-6">
                Enter the 6-digit code from your authenticator app
              </p>
              <p className="text-xs text-[#9CA3AF] mb-6 ml-6">
                This account requires 2FA verification to proceed.
              </p>

              <div className="space-y-5">
                <div>
                  <label className="tnt-label">Authenticator Code</label>
                  <input
                    ref={totpRef}
                    type="text"
                    inputMode="numeric"
                    maxLength={6}
                    value={totpCode}
                    onChange={(e) => {
                      const val = e.target.value.replace(/\D/g, '').slice(0, 6);
                      setTotpCode(val);
                      if (val.length === 6) {
                        // Auto-submit when 6 digits are entered
                        setTimeout(() => setTotpCode(val), 0);
                      }
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && totpCode.length === 6) {
                        handleVerifyTOTP();
                      }
                    }}
                    placeholder="000000"
                    className="w-full text-center text-2xl font-bold tracking-[0.5em] py-4
                               bg-[#F3F5F9] border-2 border-[#E5E7EB] rounded-xl
                               text-[#111827] focus:outline-none focus:border-[#4F46E5]
                               transition-all duration-150"
                    autoComplete="one-time-code"
                  />
                </div>

                <button
                  onClick={handleVerifyTOTP}
                  disabled={loading || totpCode.length !== 6}
                  className="btn-primary w-full justify-center py-3 text-base font-semibold"
                >
                  {loading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Verifying...
                    </>
                  ) : (
                    <>
                      <KeyRound className="w-4 h-4" />
                      Verify & Access Dashboard
                    </>
                  )}
                </button>

                <div className="text-center">
                  <button
                    onClick={() => {
                      setStep(1);
                      setPendingAuth(null);
                      setTotpCode('');
                      setOtp(['', '', '', '', '', '']);
                    }}
                    className="text-sm text-[#9CA3AF] hover:text-[#E85D24] transition-colors"
                  >
                    Sign out & start over
                  </button>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-[#9CA3AF] mt-6">
          🔒 Admin access only — Unauthorized access is prohibited
        </p>
      </div>
    </div>
  );
}

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
import { motion, AnimatePresence, useMotionValue, useTransform, useSpring } from 'framer-motion';

// Outline SVG Illustration Components
const BurgerIcon = () => (
  <svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 11c0-4.4 3.6-8 8-8s8 3.6 8 8" />
    <path d="M2 11h20M3 14h18" />
    <rect x="3" y="14" width="18" height="3" rx="1.5" />
    <path d="M4 17h16c0 2.2-1.8 4-4 4H8c-2.2 0-4-1.8-4-4z" />
  </svg>
);

const PizzaIcon = () => (
  <svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 4c0 0-7.5 1.5-11 5.5s-4.5 9-4.5 9S8 17.5 12 14.5s8-2 8-2z" />
    <path d="M4.5 18.5A2.5 2.5 0 0 1 2 16" />
    <circle cx="12" cy="7" r="1" />
    <circle cx="9" cy="12" r="1" />
    <circle cx="15" cy="10" r="1" />
  </svg>
);

const FriesIcon = () => (
  <svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
    <path d="M5 14h14M5 14l1.5 8h11l1.5-8" />
    <path d="M4 14l.5-4h2.5l.5 4" />
    <path d="M8 14l.5-6h2l.5 6" />
    <path d="M12 14l.5-7h2l.5 7" />
    <path d="M16 14l.5-5h2.5l.5 5" />
    <path d="M10 8l1-5h1.5l.5 5" />
  </svg>
);

const SoftDrinkIcon = () => (
  <svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
    <path d="M6 8l1.5 13h9L18 8" />
    <path d="M5 8h14v-2H5z" />
    <path d="M12 6V2l4 1" />
  </svg>
);

const CoffeeIcon = () => (
  <svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
    <path d="M18 8h1a3 3 0 0 1 0 6h-1" />
    <path d="M4 8h14v9a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4V8z" />
    <path d="M6 2v2M10 2v2M14 2v2" />
  </svg>
);

const DonutIcon = () => (
  <svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" />
    <circle cx="12" cy="12" r="3" />
    <path d="M12 2c1 2 2.5 3 4.5 3s4.5 1.5 5.5 3" />
    <path d="M2 12c2 1 3 2.5 3 4.5s1.5 4.5 3 5.5" />
  </svg>
);

const NotebookIcon = () => (
  <svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
    <rect x="5" y="3" width="15" height="18" rx="2" />
    <path d="M5 6h15M5 10h15M5 14h15M5 18h15M2 5h3M2 9h3M2 13h3M2 17h3" />
  </svg>
);

const SpiralNotebookIcon = () => (
  <svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
    <rect x="6" y="3" width="14" height="18" rx="2" />
    <path d="M3 6h4M3 9h4M3 12h4M3 15h4M3 18h4" />
    <path d="M3 6c0-1 1-1 2 0M3 9c0-1 1-1 2 0M3 12c0-1 1-1 2 0M3 15c0-1 1-1 2 0M3 18c0-1 1-1 2 0" />
  </svg>
);

const PencilIcon = () => (
  <svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
    <path d="M18 2L22 6L9 19H5v-4L18 2zM15 5l4 4" />
    <path d="M5 19l2.5-2.5" />
  </svg>
);

const ClipboardIcon = () => (
  <svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
    <rect x="5" y="4" width="14" height="17" rx="2" />
    <path d="M9 4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2" />
    <path d="M9 9h6M9 13h6M9 17h6" />
  </svg>
);

const PaperClipIcon = () => (
  <svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
    <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
  </svg>
);

const CalculatorIcon = () => (
  <svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
    <rect x="4" y="3" width="16" height="18" rx="2" />
    <rect x="7" y="6" width="10" height="4" />
    <path d="M7 13h2M11 13h2M15 13h2M7 17h2M11 17h2M15 17h2" />
  </svg>
);

const FolderIcon = () => (
  <svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
  </svg>
);

const CutleryIcon = () => (
  <svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 2v7c0 1.1.9 2 2 2h1v9h2v-9h1a2 2 0 0 0 2-2V2" />
    <path d="M6 2v4M9 2v4" />
    <path d="M17 2A3 3 0 0 0 14 5v5a3 3 0 0 0 3 3h1a3 3 0 0 0 3-3V5a3 3 0 0 0-3-3h-1z" />
    <path d="M17.5 13V21h2v-8" />
  </svg>
);

const PencilCupIcon = () => (
  <svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
    <path d="M6 10l1 11h10l1-11" />
    <path d="M5 10h14" />
    <path d="M14 10l3-7 2.5 1-3 7" />
    <path d="M15 8.5l.8-.4M15.8 6.5l.8-.4" />
    <path d="M9 10V4l1.5-2L12 4v6" />
    <path d="M8 10L6 5.5l1.5-1.5L9 8" />
  </svg>
);

const StaplerIcon = () => (
  <svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 17h18a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1H7M3 13V6a2 2 0 0 1 2-2h12v4" />
    <rect x="3" y="17" width="19" height="3" rx="1" />
  </svg>
);

const DocumentIcon = () => (
  <svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" />
  </svg>
);

// Decorative Contour Waves for Bottom Corners
const BottomWaves = () => (
  <div className="absolute inset-0 pointer-events-none overflow-hidden">
    {/* Bottom Left Waves (Orange) */}
    <svg className="absolute bottom-0 left-0 w-[35rem] h-[18rem] text-[#E85D24] opacity-[0.035]" viewBox="0 0 600 300" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M-100 350 C 150 320, 250 200, -20 100" />
      <path d="M-100 390 C 220 360, 320 220, -10 60" />
      <path d="M-100 430 C 290 400, 390 240, 0 20" />
    </svg>
    {/* Bottom Right Waves (Blue) */}
    <svg className="absolute bottom-0 right-0 w-[35rem] h-[18rem] text-[#4F46E5] opacity-[0.035]" viewBox="0 0 600 300" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M700 350 C 450 320, 350 200, 620 100" />
      <path d="M700 390 C 380 360, 280 220, 610 60" />
      <path d="M700 430 C 310 400, 210 240, 600 20" />
    </svg>
  </div>
);

interface JWTPayload {
  sub: string;
  role: string;
  name?: string;
  id?: number;
  exp?: number;
}

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

  // Premium Animation States
  const [isError, setIsError] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  // Mouse Parallax & Card 3D Tilt Setup
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  const springConfig = { damping: 25, stiffness: 120 };
  const rotateX = useSpring(useTransform(mouseY, [-0.5, 0.5], [3, -3]), springConfig);
  const rotateY = useSpring(useTransform(mouseX, [-0.5, 0.5], [-3, 3]), springConfig);

  const bgX = useSpring(useTransform(mouseX, [-0.5, 0.5], [15, -15]), springConfig);
  const bgY = useSpring(useTransform(mouseY, [-0.5, 0.5], [15, -15]), springConfig);

  const handleMouseMove = (e: React.MouseEvent) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;
    const xOffset = e.clientX - rect.left - width / 2;
    const yOffset = e.clientY - rect.top - height / 2;
    mouseX.set(xOffset / width);
    mouseY.set(yOffset / height);
  };

  const handleMouseLeave = () => {
    mouseX.set(0);
    mouseY.set(0);
  };

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

  const triggerErrorAnimation = () => {
    setIsError(true);
    setTimeout(() => setIsError(false), 500);
  };

  const handleSendOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validatePhone(phone)) {
      toast.error('Enter a valid 10-digit Indian mobile number');
      triggerErrorAnimation();
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
      triggerErrorAnimation();
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
      triggerErrorAnimation();
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
        triggerErrorAnimation();
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
      setIsSuccess(true);
      setAuth(authToken, adminUser);
      toast.success(`Welcome back, ${adminUser.name}!`);
      setTimeout(() => {
        navigate('/dashboard');
      }, 1000);
    } catch (err) {
      const status = err instanceof AxiosError ? err.response?.status : undefined;
      const message = err instanceof Error ? err.message : '';
      const isOtpFailure = status === 400 || /otp/i.test(message);

      toast.error(isOtpFailure ? 'Invalid OTP. Please try again.' : 'Login failed. Please try again.');
      setOtp(['', '', '', '', '', '']);
      otpRefs.current[0]?.focus();
      triggerErrorAnimation();
    } finally {
      setLoading(false);
    }
  };

  /** Verify the TOTP code from the authenticator app (step 3). */
  const handleVerifyTOTP = async () => {
    const code = totpCode.trim();
    if (code.length !== 6 || !/^\d{6}$/.test(code)) {
      toast.error('Enter a valid 6-digit authenticator code');
      triggerErrorAnimation();
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
      setIsSuccess(true);
      setAuth(pendingAuth.token, pendingAuth.user);
      setPendingAuth(null);
      toast.success(`Welcome back, ${pendingAuth.user.name}!`);
      setTimeout(() => {
        navigate('/dashboard');
      }, 1000);
    } catch (err) {
      const status = err instanceof AxiosError ? err.response?.status : undefined;
      if (status === 401) {
        toast.error('Invalid authenticator code — try again');
      } else {
        toast.error('2FA verification failed');
      }
      setTotpCode('');
      totpRef.current?.focus();
      triggerErrorAnimation();
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
      triggerErrorAnimation();
    } finally {
      setLoading(false);
    }
  };

  // Motion Variants
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.1,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 15 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        type: 'spring',
        stiffness: 100,
        damping: 15,
      },
    },
  };

  const cardVariants = {
    hidden: { opacity: 0, y: 25, scale: 0.97 },
    visible: {
      opacity: 1,
      y: 0,
      scale: 1,
      transition: {
        type: 'spring',
        stiffness: 90,
        damping: 18,
      },
    },
    shake: {
      x: [0, -10, 10, -10, 10, -5, 5, 0],
      transition: { duration: 0.4 },
    },
  };

  // Reference-Matching Outline Illustrations Configuration
  // LEFT: Food items, colored brand orange (text-[#E85D24])
  // RIGHT: Stationery items, colored brand blue (text-[#4F46E5])
  const illustrations = [
    // Left Side (Food)
    { icon: SoftDrinkIcon, colorClass: 'text-[#E85D24]', scale: 120, rotation: -15, left: '3vw', top: '6vh', responsiveClass: 'block' },
    { icon: BurgerIcon, colorClass: 'text-[#E85D24]', scale: 115, rotation: -10, left: '11vw', top: '18vh', responsiveClass: 'hidden md:block' },
    { icon: CoffeeIcon, colorClass: 'text-[#E85D24]', scale: 95, rotation: 12, left: '22vw', top: '28vh', responsiveClass: 'hidden lg:block' },
    { icon: FriesIcon, colorClass: 'text-[#E85D24]', scale: 110, rotation: -15, left: '5vw', top: '44vh', responsiveClass: 'hidden md:block' },
    { icon: PizzaIcon, colorClass: 'text-[#E85D24]', scale: 115, rotation: 20, left: '13vw', top: '60vh', responsiveClass: 'hidden md:block' },
    { icon: CutleryIcon, colorClass: 'text-[#E85D24]', scale: 115, rotation: 15, left: '1vw', top: '76vh', responsiveClass: 'block' },

    // Right Side (Stationery)
    { icon: SpiralNotebookIcon, colorClass: 'text-[#4F46E5]', scale: 135, rotation: 15, right: '4vw', top: '8vh', responsiveClass: 'block' },
    { icon: PencilIcon, colorClass: 'text-[#4F46E5]', scale: 105, rotation: -15, right: '12vw', top: '20vh', responsiveClass: 'hidden lg:block' },
    { icon: StaplerIcon, colorClass: 'text-[#4F46E5]', scale: 95, rotation: -20, right: '2vw', top: '34vh', responsiveClass: 'hidden md:block' },
    { icon: PencilCupIcon, colorClass: 'text-[#4F46E5]', scale: 105, rotation: 5, right: '15vw', top: '47vh', responsiveClass: 'hidden md:block' },
    { icon: DocumentIcon, colorClass: 'text-[#4F46E5]', scale: 120, rotation: 12, right: '6vw', top: '63vh', responsiveClass: 'hidden md:block' },
    { icon: PencilIcon, colorClass: 'text-[#4F46E5]', scale: 95, rotation: -25, right: '17vw', top: '76vh', responsiveClass: 'hidden lg:block' },
    { icon: NotebookIcon, colorClass: 'text-[#4F46E5]', scale: 125, rotation: 15, right: '9vw', top: '84vh', responsiveClass: 'block' },
  ];

  // Micro Background details Configuration (Plus, Circles, Sparkles)
  const backgroundDetails = [
    { type: 'plus', left: '15%', top: '20%', size: 14 },
    { type: 'plus', right: '20%', top: '15%', size: 16 },
    { type: 'plus', left: '25%', bottom: '25%', size: 15 },
    { type: 'plus', right: '15%', bottom: '30%', size: 14 },
    { type: 'circle', left: '40%', top: '10%', size: 8 },
    { type: 'circle', right: '35%', top: '22%', size: 10 },
    { type: 'circle', left: '30%', bottom: '15%', size: 9 },
    { type: 'circle', right: '45%', bottom: '8%', size: 10 },
    { type: 'sparkle', left: '10%', top: '45%', size: 12 },
    { type: 'sparkle', right: '8%', top: '50%', size: 14 },
    { type: 'sparkle', left: '20%', bottom: '45%', size: 13 },
    { type: 'sparkle', right: '18%', bottom: '55%', size: 12 },
  ];

  return (
    <div
      className="min-h-screen bg-[#F7F8FC] flex items-center justify-center relative overflow-hidden select-none"
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      {/* Tiny Animated Dots Background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none bg-grid-dots opacity-30" />

      {/* Floating blurred background circles */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_120%,rgba(79,70,229,0.05),transparent_60%)] animate-pulse" style={{ animationDuration: '10s' }} />

        {/* Circle 1 - Indigo */}
        <motion.div
          style={{ x: bgX, y: bgY }}
          className="absolute top-1/4 left-1/4 w-[32rem] h-[32rem] bg-indigo-100 rounded-full blur-3xl opacity-50 animate-float-slow"
        />

        {/* Circle 2 - Orange */}
        <motion.div
          style={{ x: useTransform(bgX, (v) => -v), y: useTransform(bgY, (v) => -v) }}
          className="absolute bottom-1/4 right-1/4 w-[32rem] h-[32rem] bg-orange-100 rounded-full blur-3xl opacity-45 animate-float-reverse"
        />

        {/* Circle 3 - Top Right Indigo */}
        <motion.div
          style={{ x: bgY, y: bgX }}
          className="absolute top-0 right-0 w-80 h-80 bg-indigo-50 rounded-full blur-2xl opacity-60 animate-float-slow"
        />
      </div>

      {/* Ambient background particles */}
      {[...Array(6)].map((_, i) => (
        <motion.div
          key={i}
          className="absolute w-2.5 h-2.5 rounded-full bg-indigo-400/30 blur-[1px] pointer-events-none"
          initial={{
            x: `${15 + Math.random() * 70}%`,
            y: `${15 + Math.random() * 70}%`,
            scale: 0.5 + Math.random() * 0.5,
            opacity: 0.15 + Math.random() * 0.2,
          }}
          animate={{
            y: ['0%', '-12%', '0%'],
            opacity: [0.15, 0.45, 0.15],
          }}
          transition={{
            duration: 6 + i * 2,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      ))}

      {/* Corner Waves Accents */}
      <BottomWaves />

      {/* Scattered Outline Illustrations */}
      {illustrations.map((item, idx) => {
        // Individual parallax translation values based on index
        const weightX = ((idx % 3) - 1) * 8; // -8px to 8px max offset
        const weightY = (idx % 2 === 0 ? 1 : -1) * 6;
        const weightRot = ((idx % 4) - 1.5) * 1.2; // -1.8deg to 1.8deg max rotation

        const parallaxX = useTransform(mouseX, [-0.5, 0.5], [-weightX, weightX]);
        const parallaxY = useTransform(mouseY, [-0.5, 0.5], [-weightY, weightY]);
        const parallaxRot = useTransform(mouseX, [-0.5, 0.5], [-weightRot, weightRot]);

        return (
          <motion.div
            key={`illus-${idx}`}
            className={`${item.responsiveClass} absolute pointer-events-none`}
            style={{
              left: item.left,
              top: item.top,
              right: item.right,
              bottom: item.bottom,
              width: item.scale,
              height: item.scale,
              x: parallaxX,
              y: parallaxY,
              rotate: parallaxRot,
            }}
          >
            <motion.div
              className={item.colorClass}
              style={{ width: '100%', height: '100%' }}
              animate={{
                y: [0, idx % 2 === 0 ? 5 : -5, 0],
                rotate: [item.rotation, item.rotation + (idx % 3 === 0 ? 1.5 : -1.5), item.rotation],
                opacity: [0.07, 0.11, 0.07],
              }}
              transition={{
                duration: 11 + ((idx * 2) % 8), // 11-19s
                repeat: Infinity,
                ease: 'easeInOut',
                delay: (idx * 0.5) % 5,
              }}
            >
              <item.icon />
            </motion.div>
          </motion.div>
        );
      })}

      {/* Tiny geometric details (plus, circles, sparkles) scattered */}
      {backgroundDetails.map((item, idx) => {
        const weightX = (idx % 2 === 0 ? 4 : -4);
        const weightY = (idx % 3 === 0 ? 3 : -3);

        const parallaxX = useTransform(mouseX, [-0.5, 0.5], [-weightX, weightX]);
        const parallaxY = useTransform(mouseY, [-0.5, 0.5], [-weightY, weightY]);

        return (
          <motion.div
            key={`detail-${idx}`}
            className="absolute pointer-events-none"
            style={{
              left: item.left,
              top: item.top,
              right: item.right,
              bottom: item.bottom,
              width: item.size,
              height: item.size,
              x: parallaxX,
              y: parallaxY,
            }}
          >
            <motion.div
              className={idx % 2 === 0 ? 'text-[#4F46E5]' : 'text-[#E85D24]'}
              style={{ width: '100%', height: '100%' }}
              animate={{
                opacity: [0.04, 0.08, 0.04],
                scale: [0.96, 1.04, 0.96],
              }}
              transition={{
                duration: 9 + ((idx * 1.5) % 6), // 9-15s
                repeat: Infinity,
                ease: 'easeInOut',
                delay: (idx * 0.4) % 3,
              }}
            >
              {item.type === 'plus' && (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                  <path d="M12 5v14M5 12h14" strokeLinecap="round" />
                </svg>
              )}
              {item.type === 'circle' && (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                  <circle cx="12" cy="12" r="8" />
                </svg>
              )}
              {item.type === 'sparkle' && (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                  <path d="M12 3c0 4.5 1.5 6 6 6-4.5 0-6 1.5-6 6 0-4.5-1.5-6-6-6 4.5 0 6-1.5 6-6z" strokeLinejoin="round" />
                </svg>
              )}
            </motion.div>
          </motion.div>
        );
      })}

      <motion.div
        initial="hidden"
        animate="visible"
        variants={containerVariants}
        className="relative z-10 w-full max-w-md px-6"
      >
        {/* Logo and Titles */}
        <motion.div variants={itemVariants} className="text-center mb-10">
          <motion.div
            animate={{
              y: [0, -6, 0],
              boxShadow: [
                '0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.05)',
                '0 20px 25px -5px rgba(232, 93, 36, 0.12), 0 8px 10px -6px rgba(232, 93, 36, 0.12)',
                '0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.05)',
              ],
            }}
            transition={{
              y: { repeat: Infinity, duration: 6, ease: 'easeInOut' },
              boxShadow: { repeat: Infinity, duration: 6, ease: 'easeInOut' },
            }}
            whileHover={{ scale: 1.04 }}
            className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-white border-2 border-[#E5E7EB] shadow-lg mb-5 overflow-hidden group cursor-pointer hover:border-[#E85D24] transition-colors duration-300"
          >
            <img src={logo} alt="TAP N TAKE Logo" className="w-full h-full object-cover" />
          </motion.div>
          <h1 className="text-3xl font-bold text-[#111827] mb-1">
            TNT Admin
          </h1>
          <p className="text-[#4B5563] text-sm">Tap N Take — Parul University</p>
        </motion.div>

        {/* Step indicators */}
        <motion.div variants={itemVariants} className="flex items-center justify-center gap-3 mb-8">
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
        </motion.div>

        {/* Card */}
        <motion.div
          variants={cardVariants}
          animate={isError ? 'shake' : 'visible'}
          style={{ rotateX, rotateY, transformStyle: 'preserve-3d' }}
          whileHover={{
            y: -3,
            boxShadow: '0 12px 20px -3px rgba(79, 70, 229, 0.06), 0 28px 36px -4px rgba(0, 0, 0, 0.05)',
          }}
          className={`bg-white border ${
            isError
              ? 'border-red-500 shadow-[0_0_20px_rgba(239,68,68,0.15)]'
              : isSuccess
              ? 'border-green-500 shadow-[0_0_20px_rgba(34,197,94,0.15)]'
              : 'border-[#E5E7EB]'
          } rounded-2xl p-8 shadow-[0_1px_2px_rgba(0,0,0,0.03),0_8px_24px_rgba(0,0,0,0.04)] glass-shine transition-all duration-300`}
        >
          <AnimatePresence mode="wait">
            {/* STEP 1 — Phone Number */}
            {step === 1 && (
              <motion.div
                key="step-1"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 10 }}
                transition={{ duration: 0.2 }}
              >
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
                      <motion.input
                        whileFocus={{ scale: 1.01, boxShadow: '0 0 0 3px rgba(79, 70, 229, 0.12)' }}
                        transition={{ duration: 0.15 }}
                        type="tel"
                        value={phone}
                        onChange={(e) => setPhone(e.target.value.replace(/\D/g, '').slice(0, 10))}
                        placeholder="9999999999"
                        className="tnt-input flex-1 focus:border-[#4F46E5]"
                        autoFocus
                        required
                        inputMode="numeric"
                      />
                    </div>
                    
                    {/* Demo Admin Helper Badges */}
                    <div className="mt-3 flex flex-wrap gap-2 text-xs">
                      <span className="text-[#6B7280]">Demo Accounts:</span>
                      <button
                        type="button"
                        onClick={() => setPhone('9999999999')}
                        className="text-[#E85D24] hover:underline font-medium"
                      >
                        Admin (9999999999)
                      </button>
                      <span className="text-[#D1D5DB]">•</span>
                      <button
                        type="button"
                        onClick={() => setPhone('9999999900')}
                        className="text-[#4F46E5] hover:underline font-medium"
                      >
                        Super Admin (9999999900)
                      </button>
                    </div>
                  </div>

                  <motion.button
                    whileHover={{
                      scale: 1.02,
                      y: -1.5,
                      boxShadow: '0 10px 15px -3px rgba(79, 70, 229, 0.25), 0 4px 6px -2px rgba(79, 70, 229, 0.2)',
                    }}
                    whileTap={{ scale: 0.985, y: 0 }}
                    type="submit"
                    disabled={loading || phone.length !== 10}
                    className="btn-primary w-full justify-center py-3 text-base font-semibold bg-gradient-to-r from-[#4F46E5] to-[#4338CA] bg-[length:200%_auto] hover:bg-right transition-all duration-500 shadow-md relative overflow-hidden"
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
                  </motion.button>
                </form>
              </motion.div>
            )}

            {/* STEP 2 — OTP Verification */}
            {step === 2 && (
              <motion.div
                key="step-2"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 10 }}
                transition={{ duration: 0.2 }}
              >
                <div className="flex items-center gap-2 mb-1">
                  <motion.button
                    whileHover={{ x: -2, scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => {
                      setStep(1);
                      setOtp(['', '', '', '', '', '']);
                    }}
                    className="text-[#9CA3AF] hover:text-[#111827] transition-colors p-1"
                  >
                    ←
                  </motion.button>
                  <h2 className="text-xl font-semibold text-[#111827]">Verify OTP</h2>
                </div>
                <p className="text-sm text-[#4B5563] mb-6 ml-8">
                  Sent to{' '}
                  <span className="text-[#111827] font-medium">
                    +91 {phone.slice(0, 5)} {phone.slice(5)}
                  </span>
                </p>

                <div className="space-y-5">
                  <div>
                    <label className="tnt-label">6-Digit OTP</label>
                    <div className="flex gap-2 justify-between" onPaste={handleOTPPaste}>
                      {otp.map((digit, index) => (
                        <motion.input
                          whileFocus={{ scale: 1.05, borderColor: '#4F46E5', boxShadow: '0 0 0 3px rgba(79, 70, 229, 0.12)' }}
                          transition={{ duration: 0.12 }}
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

                  <motion.button
                    whileHover={{
                      scale: 1.02,
                      y: -1.5,
                      boxShadow: '0 10px 15px -3px rgba(79, 70, 229, 0.25), 0 4px 6px -2px rgba(79, 70, 229, 0.2)',
                    }}
                    whileTap={{ scale: 0.985, y: 0 }}
                    onClick={() => handleVerifyOTP()}
                    disabled={loading || otp.some((d) => !d)}
                    className="btn-primary w-full justify-center py-3 text-base font-semibold bg-gradient-to-r from-[#4F46E5] to-[#4338CA] bg-[length:200%_auto] hover:bg-right transition-all duration-500 shadow-md"
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
                  </motion.button>

                  {/* Resend */}
                  <div className="text-center">
                    {countdown > 0 ? (
                      <p className="text-sm text-[#4B5563]">
                        Resend OTP in{' '}
                        <span className="text-[#E85D24] font-medium font-mono">{countdown}s</span>
                      </p>
                    ) : (
                      <motion.button
                        whileHover={{ scale: 1.03, y: -0.5 }}
                        whileTap={{ scale: 0.97 }}
                        onClick={handleResendOTP}
                        disabled={loading}
                        className="text-sm text-[#E85D24] hover:text-[#F97316] font-medium
                                   inline-flex items-center gap-1.5 transition-colors"
                      >
                        <motion.span whileHover={{ rotate: 180 }} transition={{ duration: 0.4 }} className="inline-block">
                          <RefreshCw className="w-3.5 h-3.5" />
                        </motion.span>
                        Resend OTP
                      </motion.button>
                    )}
                  </div>
                </div>
              </motion.div>
            )}

            {/* STEP 3 — TOTP 2FA Verification */}
            {step === 3 && (
              <motion.div
                key="step-3"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 10 }}
                transition={{ duration: 0.2 }}
              >
                <div className="flex items-center gap-2 mb-1">
                  <motion.button
                    whileHover={{ x: -2, scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => {
                      setStep(2);
                      setPendingAuth(null);
                      setTotpCode('');
                    }}
                    className="text-[#9CA3AF] hover:text-[#111827] transition-colors p-1"
                  >
                    ←
                  </motion.button>
                  <h2 className="text-xl font-semibold text-[#111827]">Two-Factor Auth</h2>
                </div>
                <p className="text-sm text-[#4B5563] mb-2 ml-8">
                  Enter the 6-digit code from your authenticator app
                </p>
                <p className="text-xs text-[#9CA3AF] mb-6 ml-8">
                  This account requires 2FA verification to proceed.
                </p>

                <div className="space-y-5">
                  <div>
                    <label className="tnt-label">Authenticator Code</label>
                    <motion.input
                      whileFocus={{ scale: 1.02, borderColor: '#4F46E5', boxShadow: '0 0 0 3px rgba(79, 70, 229, 0.12)' }}
                      transition={{ duration: 0.15 }}
                      ref={totpRef}
                      type="text"
                      inputMode="numeric"
                      maxLength={6}
                      value={totpCode}
                      onChange={(e) => {
                        const val = e.target.value.replace(/\D/g, '').slice(0, 6);
                        setTotpCode(val);
                        if (val.length === 6) {
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

                  <motion.button
                    whileHover={{
                      scale: 1.02,
                      y: -1.5,
                      boxShadow: '0 10px 15px -3px rgba(79, 70, 229, 0.25), 0 4px 6px -2px rgba(79, 70, 229, 0.2)',
                    }}
                    whileTap={{ scale: 0.985, y: 0 }}
                    onClick={handleVerifyTOTP}
                    disabled={loading || totpCode.length !== 6}
                    className="btn-primary w-full justify-center py-3 text-base font-semibold bg-gradient-to-r from-[#4F46E5] to-[#4338CA] bg-[length:200%_auto] hover:bg-right transition-all duration-500 shadow-md"
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
                  </motion.button>

                  <div className="text-center">
                    <motion.button
                      whileHover={{ scale: 1.03, color: '#E85D24' }}
                      whileTap={{ scale: 0.97 }}
                      onClick={() => {
                        setStep(1);
                        setPendingAuth(null);
                        setTotpCode('');
                        setOtp(['', '', '', '', '', '']);
                      }}
                      className="text-sm text-[#9CA3AF] hover:text-[#E85D24] transition-colors"
                    >
                      Sign out & start over
                    </motion.button>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Footer */}
        <motion.p variants={itemVariants} className="text-center text-xs text-[#9CA3AF] mt-6">
          🔒 Admin access only — Unauthorized access is prohibited
        </motion.p>
      </motion.div>
    </div>
  );
}

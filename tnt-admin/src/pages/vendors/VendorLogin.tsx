import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Store, ArrowRight, Shield, RefreshCw, CheckCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import { vendorAuthApi } from '../../api/vendorAuth';
import { AxiosError } from 'axios';

export default function VendorLogin() {
  const navigate = useNavigate();

  const [step, setStep] = useState<1 | 2>(1);
  const [vendorId, setVendorId] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [vendorName, setVendorName] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!vendorId || !password) {
      toast.error('Enter vendor ID and password');
      return;
    }

    setLoading(true);
    try {
      const res = await vendorAuthApi.login(Number(vendorId), password);
      const { access_token, refresh_token, vendor } = res.data;

      // Store in localStorage for vendor portal
      localStorage.setItem('tnt-vendor-token', access_token);
      localStorage.setItem('tnt-vendor-refresh', refresh_token);
      localStorage.setItem('tnt-vendor-profile', JSON.stringify(vendor));

      setVendorName(vendor.vendor_name);
      setStep(2);
      toast.success('Login successful!');
    } catch (err) {
      const status = err instanceof AxiosError ? err.response?.status : undefined;
      const msg = status === 401 ? 'Invalid vendor ID or password' : 'Login failed';
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleGoToDashboard = () => {
    window.location.href = '/vendor/dashboard';
  };

  return (
    <div className="min-h-screen bg-[#F7F8FC] flex items-center justify-center relative overflow-hidden">
      {/* Background effects */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-emerald-100 rounded-full blur-3xl opacity-60" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-orange-100 rounded-full blur-3xl opacity-60" />
      </div>

      <div className="relative z-10 w-full max-w-md px-6">
        {/* Logo */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-white border-2 border-[#E5E7EB] shadow-lg mb-4">
            <Store className="w-10 h-10 text-emerald-600" />
          </div>
          <h1 className="text-2xl font-bold text-[#111827] mb-1">Vendor Portal</h1>
          <p className="text-[#4B5563] text-sm">TNT — Tap N Take Vendor Login</p>
        </div>

        {/* Step indicators */}
        <div className="flex items-center justify-center gap-3 mb-8">
          {[1, 2].map((s) => (
            <React.Fragment key={s}>
              <div className={`flex items-center gap-2 ${s <= step ? 'text-emerald-600' : 'text-[#9CA3AF]'}`}>
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-all duration-300
                  ${s < step ? 'bg-emerald-600 border-emerald-600 text-white' :
                    s === step ? 'border-emerald-600 text-emerald-600' :
                      'border-[#E5E7EB] text-[#9CA3AF]'}`}
                >
                  {s < step ? <CheckCircle className="w-3.5 h-3.5" /> : s}
                </div>
                <span className="text-xs font-medium hidden sm:inline">
                  {s === 1 ? 'Sign In' : 'Dashboard'}
                </span>
              </div>
              {s < 2 && (
                <div className={`flex-1 h-0.5 max-w-[60px] transition-all duration-500 ${step > 1 ? 'bg-emerald-600' : 'bg-[#E5E7EB]'}`} />
              )}
            </React.Fragment>
          ))}
        </div>

        {/* Card */}
        <div className="bg-white border border-[#E5E7EB] rounded-2xl p-8 shadow-[0_1px_2px_rgba(0,0,0,0.03),0_8px_24px_rgba(0,0,0,0.04)]">
          {step === 1 ? (
            <>
              <h2 className="text-xl font-semibold text-[#111827] mb-1">Vendor Sign In</h2>
              <p className="text-sm text-[#4B5563] mb-6">Enter your vendor credentials</p>

              <form onSubmit={handleLogin} className="space-y-5">
                <div>
                  <label className="block text-sm font-medium text-[#374151] mb-1.5">
                    Vendor ID
                  </label>
                  <input
                    type="number"
                    value={vendorId}
                    onChange={(e) => setVendorId(e.target.value.replace(/\D/g, '').slice(0, 10))}
                    placeholder="e.g. 1"
                    className="w-full bg-[#F3F5F9] border border-[#E5E7EB] rounded-xl px-4 py-2.5 text-[#111827] text-sm focus:outline-none focus:border-emerald-500 transition-colors"
                    autoFocus
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-[#374151] mb-1.5">
                    Password
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    className="w-full bg-[#F3F5F9] border border-[#E5E7EB] rounded-xl px-4 py-2.5 text-[#111827] text-sm focus:outline-none focus:border-emerald-500 transition-colors"
                    required
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-3 px-4 rounded-xl inline-flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
                >
                  {loading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Signing in...
                    </>
                  ) : (
                    <>
                      Sign In
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </form>
            </>
          ) : (
            <>
              <div className="text-center">
                <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <CheckCircle className="w-8 h-8 text-emerald-600" />
                </div>
                <h2 className="text-xl font-semibold text-[#111827] mb-1">Welcome!</h2>
                <p className="text-sm text-[#4B5563] mb-2">
                  Signed in as <span className="font-semibold text-emerald-700">{vendorName}</span>
                </p>
                <p className="text-xs text-[#9CA3AF] mb-6">
                  You can now manage your menu, view orders, and track analytics.
                </p>
                <button
                  onClick={handleGoToDashboard}
                  className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-3 px-4 rounded-xl transition-colors"
                >
                  Go to Dashboard
                </button>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-[#9CA3AF] mt-6">
          🔒 Vendor access only — Unauthorized access is prohibited
        </p>
      </div>
    </div>
  );
}
</path>
</write_to_file>

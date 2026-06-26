import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, AlertTriangle, ShieldCheck, ShieldAlert, 
  User as UserIcon, Store, ShoppingBag, Ban, CheckCircle, 
  HelpCircle, AlertOctagon, Terminal, RefreshCw, Send 
} from 'lucide-react';
import toast from 'react-hot-toast';
import { adminApi } from '../../api/admin';
import { formatDate } from '../../utils/format';
import type { FraudAlertDetailResponse } from '../../types';

const SEVERITY_TEXT_COLORS = {
  low: 'text-emerald-700 bg-emerald-50 border-emerald-200',
  medium: 'text-amber-700 bg-amber-50 border-amber-200',
  high: 'text-red-700 bg-red-50 border-red-200',
  critical: 'text-rose-900 bg-rose-50 border-rose-200',
};

export default function FraudDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<FraudAlertDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionNotes, setActionNotes] = useState('');
  const [processing, setProcessing] = useState(false);
  const [confirmModal, setConfirmModal] = useState<null | 'resolve' | 'false_positive' | 'blacklist_user' | 'blacklist_vendor'>(null);

  const fetchDetail = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const res = await adminApi.getFraudAlertDetail(Number(id));
      setDetail(res.data);
    } catch {
      toast.error('Failed to load alert details');
      navigate('/fraud');
    } finally {
      setLoading(false);
    }
  }, [id, navigate]);

  useEffect(() => {
    fetchDetail();
  }, [fetchDetail]);

  const handleResolveAlert = async () => {
    if (!id || !actionNotes.trim()) {
      toast.error('Please enter resolution notes');
      return;
    }
    setProcessing(true);
    try {
      await adminApi.resolveFraudAlert(Number(id), actionNotes);
      toast.success('Alert marked as resolved');
      setActionNotes('');
      setConfirmModal(null);
      fetchDetail();
    } catch {
      toast.error('Failed to resolve alert');
    } finally {
      setProcessing(false);
    }
  };

  const handleMarkFalsePositive = async () => {
    if (!id || !actionNotes.trim()) {
      toast.error('Please enter resolution notes');
      return;
    }
    setProcessing(true);
    try {
      await adminApi.markFalsePositive(Number(id), actionNotes);
      toast.success('Alert marked as false positive');
      setActionNotes('');
      setConfirmModal(null);
      fetchDetail();
    } catch {
      toast.error('Failed to update alert');
    } finally {
      setProcessing(false);
    }
  };

  const handleBlacklistUser = async () => {
    if (!detail?.user?.id) return;
    setProcessing(true);
    try {
      await adminApi.blacklistUser(detail.user.id);
      toast.success('User blacklisted successfully');
      setConfirmModal(null);
      fetchDetail();
    } catch {
      toast.error('Failed to blacklist user');
    } finally {
      setProcessing(false);
    }
  };

  const handleBlacklistVendor = async () => {
    if (!detail?.vendor?.id) return;
    setProcessing(true);
    try {
      await adminApi.blacklistVendor(detail.vendor.id);
      toast.success('Vendor blacklisted and suspended successfully');
      setConfirmModal(null);
      fetchDetail();
    } catch {
      toast.error('Failed to blacklist vendor');
    } finally {
      setProcessing(false);
    }
  };

  if (loading) {
    return (
      <div className="py-24 text-center">
        <RefreshCw className="w-10 h-10 animate-spin mx-auto text-[#4F46E5] mb-2" />
        <p className="text-sm text-[#6B7280]">Loading investigator session...</p>
      </div>
    );
  }

  if (!detail) return null;
  const { alert, user, vendor, order } = detail;

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/fraud')}
          className="p-2 border border-[#E5E7EB] bg-white rounded-xl text-[#4B5563] hover:bg-[#F3F5F9] transition-all"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <span className="text-xs font-semibold text-[#6B7280]">ALERT INVESTIGATION</span>
          <h1 className="text-xl font-bold text-[#111827]">Case ID #{alert.id}</h1>
        </div>
      </div>

      {/* Overview Metrics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Risk Score Gauge */}
        <div className="tnt-card flex flex-col justify-between items-center text-center p-6">
          <div className="w-full text-left">
            <h3 className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider">Threat Index</h3>
          </div>
          <div className="relative my-4 flex items-center justify-center">
            {/* Simple Visual Score ring */}
            <div className="w-28 h-28 rounded-full border-[8px] border-[#F3F5F9] flex flex-col items-center justify-center">
              <span className="text-3xl font-extrabold text-[#111827]">{alert.score.toFixed(0)}</span>
              <span className="text-[10px] text-[#6B7280] font-semibold">OF 100</span>
            </div>
            <div 
              className="absolute inset-0 rounded-full border-[8px] pointer-events-none"
              style={{
                borderColor: alert.score >= 85 ? '#EF4444' : alert.score >= 60 ? '#F59E0B' : '#10B981',
                clipPath: `polygon(50% 50%, -50% -50%, ${alert.score * 3.6}deg)`
              }}
            />
          </div>
          <div>
            <span className={`inline-flex px-3 py-1 border rounded-full text-xs font-bold ${
              SEVERITY_TEXT_COLORS[alert.severity as keyof typeof SEVERITY_TEXT_COLORS]
            }`}>
              {alert.severity.toUpperCase()} SEVERITY
            </span>
          </div>
        </div>

        {/* Diagnostic Metadata */}
        <div className="tnt-card lg:col-span-2 space-y-4">
          <h3 className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider">Anomaly Explanation</h3>
          <div className="p-4 bg-[#F8FAFC] border border-[#E5E7EB] rounded-2xl">
            <p className="font-mono text-sm text-[#111827] font-semibold">{alert.alert_type}</p>
            <p className="text-xs text-[#4B5563] mt-2 leading-relaxed">{alert.description}</p>
          </div>
          <div className="grid grid-cols-2 gap-4 text-xs">
            <div>
              <p className="text-[#6B7280]">Logged Date</p>
              <p className="font-medium text-[#111827] mt-0.5">{formatDate(alert.created_at)}</p>
            </div>
            <div>
              <p className="text-[#6B7280]">Resolution Status</p>
              <p className={`font-semibold capitalize mt-0.5 ${
                alert.status === 'pending' ? 'text-orange-600' :
                alert.status === 'resolved' ? 'text-green-600' : 'text-slate-600'
              }`}>
                {alert.status.replace('_', ' ')}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Entity Context Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* User Card */}
        {user ? (
          <div className="tnt-card flex flex-col justify-between">
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-blue-50 text-blue-600 rounded-lg flex items-center justify-center">
                  <UserIcon className="w-4.5 h-4.5" />
                </div>
                <h4 className="font-semibold text-sm text-[#111827]">Associated Student</h4>
              </div>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-[#6B7280]">Full Name:</span>
                  <span className="font-semibold text-[#111827]">{user.name || 'Anonymous'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#6B7280]">Phone ID:</span>
                  <span className="font-mono text-[#111827]">{user.phone}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#6B7280]">Created:</span>
                  <span className="text-[#4B5563]">{formatDate(user.created_at)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#6B7280]">Cumulative Index:</span>
                  <span className={`font-bold ${
                    user.cumulative_fraud_score >= 85 ? 'text-red-600' :
                    user.cumulative_fraud_score >= 60 ? 'text-orange-500' : 'text-green-600'
                  }`}>
                    {user.cumulative_fraud_score.toFixed(0)} / 100
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#6B7280]">Account Active:</span>
                  <span className={`font-bold ${user.is_active ? 'text-green-600' : 'text-red-500'}`}>
                    {user.is_active ? 'Active' : 'Blocked/Inactive'}
                  </span>
                </div>
              </div>
            </div>

            {user.is_active && (
              <button
                onClick={() => setConfirmModal('blacklist_user')}
                className="mt-6 w-full inline-flex items-center justify-center gap-2 text-xs font-semibold px-4 py-2 border border-red-200 text-red-700 bg-red-50 hover:bg-red-100 rounded-xl transition-all"
              >
                <Ban className="w-4 h-4" />
                Blacklist Account
              </button>
            )}
          </div>
        ) : (
          <div className="tnt-card border-dashed border-[#E5E7EB] flex flex-col justify-center items-center text-center text-xs text-[#9CA3AF]">
            <UserIcon className="w-8 h-8 mb-2" />
            No associated student account
          </div>
        )}

        {/* Vendor Card */}
        {vendor ? (
          <div className="tnt-card flex flex-col justify-between">
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-amber-50 text-amber-600 rounded-lg flex items-center justify-center">
                  <Store className="w-4.5 h-4.5" />
                </div>
                <h4 className="font-semibold text-sm text-[#111827]">Vendor Business</h4>
              </div>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-[#6B7280]">Business Name:</span>
                  <span className="font-semibold text-[#111827]">{vendor.name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#6B7280]">Owner Phone:</span>
                  <span className="font-mono text-[#111827]">{vendor.phone}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#6B7280]">Status Flag:</span>
                  <span className="font-semibold text-[#111827] capitalize">{vendor.status}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#6B7280]">Account Active:</span>
                  <span className={`font-bold ${vendor.is_active ? 'text-green-600' : 'text-red-500'}`}>
                    {vendor.is_active ? 'Active' : 'Suspended/Blocked'}
                  </span>
                </div>
              </div>
            </div>

            {vendor.is_active && (
              <button
                onClick={() => setConfirmModal('blacklist_vendor')}
                className="mt-6 w-full inline-flex items-center justify-center gap-2 text-xs font-semibold px-4 py-2 border border-red-200 text-red-700 bg-red-50 hover:bg-red-100 rounded-xl transition-all"
              >
                <Ban className="w-4 h-4" />
                Suspend Vendor
              </button>
            )}
          </div>
        ) : (
          <div className="tnt-card border-dashed border-[#E5E7EB] flex flex-col justify-center items-center text-center text-xs text-[#9CA3AF]">
            <Store className="w-8 h-8 mb-2" />
            No vendor business linked
          </div>
        )}

        {/* Order Details Card */}
        {order ? (
          <div className="tnt-card flex flex-col justify-between">
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-purple-50 text-purple-600 rounded-lg flex items-center justify-center">
                  <ShoppingBag className="w-4.5 h-4.5" />
                </div>
                <h4 className="font-semibold text-sm text-[#111827]">Order Details</h4>
              </div>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-[#6B7280]">Order ID:</span>
                  <span className="font-mono text-[#111827]">#{order.id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#6B7280]">Total Value:</span>
                  <span className="font-semibold text-[#111827]">₹{(order.total_amount / 100).toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#6B7280]">Order Status:</span>
                  <span className="font-semibold capitalize text-[#111827]">{order.status}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#6B7280]">Booking Segment:</span>
                  <span className="font-semibold capitalize text-[#111827]">{order.booking_type}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#6B7280]">Created Time:</span>
                  <span className="text-[#4B5563]">{formatDate(order.created_at)}</span>
                </div>
              </div>
            </div>
            <button
              onClick={() => navigate(`/orders/${order.id}`)}
              className="mt-6 w-full inline-flex items-center justify-center gap-2 text-xs font-semibold px-4 py-2 border border-[#D1D5DB] bg-white text-[#4B5563] hover:bg-[#F3F5F9] rounded-xl transition-all"
            >
              <ShoppingBag className="w-4 h-4" />
              View Full Order
            </button>
          </div>
        ) : (
          <div className="tnt-card border-dashed border-[#E5E7EB] flex flex-col justify-center items-center text-center text-xs text-[#9CA3AF]">
            <ShoppingBag className="w-8 h-8 mb-2" />
            No transaction linked
          </div>
        )}
      </div>

      {/* Admin Action Console */}
      <div className="tnt-card space-y-4">
        <h3 className="font-semibold text-base text-[#111827] flex items-center gap-2">
          <Terminal className="w-5 h-5 text-[#6B7280]" />
          Resolution Console
        </h3>

        {alert.status === 'pending' ? (
          <div className="space-y-4">
            <textarea
              value={actionNotes}
              onChange={(e) => setActionNotes(e.target.value)}
              placeholder="Provide investigation details, verification logs, or reason notes..."
              className="w-full text-xs border border-[#E5E7EB] bg-white rounded-xl p-4 focus:ring-1 focus:ring-[#4F46E5] focus:border-[#4F46E5] outline-none text-[#111827] h-28"
            />
            <div className="flex gap-2">
              <button
                onClick={() => setConfirmModal('resolve')}
                className="btn-primary inline-flex items-center gap-2"
              >
                <CheckCircle className="w-4 h-4" />
                Resolve Alert
              </button>
              <button
                onClick={() => setConfirmModal('false_positive')}
                className="inline-flex items-center gap-2 text-sm font-medium px-4 py-2 rounded-xl border border-[#D1D5DB] bg-white text-[#4B5563] hover:bg-[#F3F5F9] transition-all"
              >
                <HelpCircle className="w-4 h-4" />
                Mark False Positive
              </button>
            </div>
          </div>
        ) : (
          <div className="p-4 bg-slate-50 border border-slate-200 rounded-2xl text-xs space-y-2">
            <div className="flex items-center gap-2">
              {alert.status === 'resolved' ? (
                <ShieldCheck className="w-5 h-5 text-[#22C55E]" />
              ) : (
                <HelpCircle className="w-5 h-5 text-slate-500" />
              )}
              <span className="font-semibold capitalize text-[#111827]">Case status: {alert.status.replace('_', ' ')}</span>
            </div>
            <p className="text-[#6B7280] font-semibold mt-1">Resolution Summary:</p>
            <p className="text-[#4B5563] italic leading-relaxed">
              {alert.resolution_notes || 'No notes saved.'}
            </p>
          </div>
        )}
      </div>

      {/* Confirmation Modals */}
      {confirmModal && (
        <div className="fixed inset-0 bg-[#0F0F1A]/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="tnt-card max-w-md w-full bg-white space-y-4">
            <h3 className="font-bold text-lg text-[#111827] flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-red-600" />
              Confirm Action
            </h3>
            <p className="text-xs text-[#4B5563] leading-relaxed">
              {confirmModal === 'resolve' && 'Are you sure you want to resolve this alert? The incident will be marked cleared.'}
              {confirmModal === 'false_positive' && 'Are you sure this is a false positive? Alert indicators will be dismissed.'}
              {confirmModal === 'blacklist_user' && 'CRITICAL: Blacklisting this student account will deactivate it immediately and terminate all sessions. The student will not be able to log in.'}
              {confirmModal === 'blacklist_vendor' && 'CRITICAL: Suspending this vendor will deactivate the business owner, block staff credentials, and remove their inventory from the user app.'}
            </p>
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setConfirmModal(null)}
                className="px-4 py-2 text-xs font-semibold border border-[#D1D5DB] rounded-xl hover:bg-[#F3F5F9] text-[#4B5563] transition-all"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  if (confirmModal === 'resolve') handleResolveAlert();
                  if (confirmModal === 'false_positive') handleMarkFalsePositive();
                  if (confirmModal === 'blacklist_user') handleBlacklistUser();
                  if (confirmModal === 'blacklist_vendor') handleBlacklistVendor();
                }}
                disabled={processing}
                className="px-4 py-2 text-xs font-semibold bg-red-600 hover:bg-red-700 text-white rounded-xl transition-all disabled:opacity-50"
              >
                {processing ? 'Processing...' : 'Confirm'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

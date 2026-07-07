import React, { useCallback, useEffect, useState } from 'react';
import { ShieldCheck, Wrench, Check, X, Loader2, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';
import { adminApi } from '../../api/admin';

interface MatrixRow { capability: string; roles: Record<string, boolean>; }

export default function AccessControl() {
  const [maintEnabled, setMaintEnabled] = useState(false);
  const [maintMessage, setMaintMessage] = useState('');
  const [savingMaint, setSavingMaint] = useState(false);
  const [roles, setRoles] = useState<string[]>([]);
  const [matrix, setMatrix] = useState<MatrixRow[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [m, pm] = await Promise.allSettled([adminApi.getMaintenance(), adminApi.getPermissionMatrix()]);
      if (m.status === 'fulfilled') {
        setMaintEnabled(!!m.value.data.enabled);
        setMaintMessage(m.value.data.message || '');
      }
      if (pm.status === 'fulfilled') {
        setRoles(pm.value.data.roles || []);
        setMatrix(pm.value.data.matrix || []);
      }
    } catch { toast.error('Failed to load access control'); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const saveMaintenance = async (enabled: boolean) => {
    setSavingMaint(true);
    try {
      const res = await adminApi.setMaintenance(enabled, maintMessage);
      setMaintEnabled(!!res.data.enabled);
      setMaintMessage(res.data.message || '');
      toast.success(enabled ? 'Maintenance mode enabled' : 'Maintenance mode disabled');
    } catch { toast.error('Failed to update maintenance mode'); }
    finally { setSavingMaint(false); }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-[#111827]">Access Control</h2>
          <p className="text-sm text-[#6B7280] mt-1">Campus maintenance mode & role permission matrix</p>
        </div>
        <button onClick={load} className="btn-ghost" aria-label="Refresh"><RefreshCw className="w-4 h-4" /></button>
      </div>

      {/* Maintenance mode */}
      <div className={`tnt-card border-2 ${maintEnabled ? 'border-amber-300 bg-amber-50/40' : 'border-[#E5E7EB]'}`}>
        <div className="flex items-start gap-3">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${maintEnabled ? 'bg-amber-100' : 'bg-[#F3F4F6]'}`}>
            <Wrench className={`w-5 h-5 ${maintEnabled ? 'text-amber-600' : 'text-[#6B7280]'}`} />
          </div>
          <div className="flex-1">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div>
                <h3 className="font-semibold text-[#111827]">Campus Maintenance Mode</h3>
                <p className="text-xs text-[#6B7280]">
                  When enabled, students & vendors are blocked from ordering with your message. Admin access stays open.
                </p>
              </div>
              <span className={`px-3 py-1 rounded-full text-xs font-medium border ${maintEnabled ? 'bg-amber-100 text-amber-700 border-amber-200' : 'bg-green-50 text-green-700 border-green-200'}`}>
                {maintEnabled ? 'ENABLED' : 'Disabled'}
              </span>
            </div>
            <textarea
              className="tnt-input mt-3"
              rows={2}
              value={maintMessage}
              onChange={(e) => setMaintMessage(e.target.value)}
              placeholder="Message shown to users during maintenance"
            />
            <div className="flex gap-2 mt-3">
              {!maintEnabled ? (
                <button onClick={() => saveMaintenance(true)} disabled={savingMaint} className="btn-danger">
                  {savingMaint ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wrench className="w-4 h-4" />} Enable Maintenance
                </button>
              ) : (
                <>
                  <button onClick={() => saveMaintenance(true)} disabled={savingMaint} className="btn-ghost">Update Message</button>
                  <button onClick={() => saveMaintenance(false)} disabled={savingMaint} className="btn-success">
                    {savingMaint ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />} Disable
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Permission matrix */}
      <div className="tnt-card">
        <div className="flex items-center gap-2 mb-4">
          <ShieldCheck className="w-5 h-5 text-[#4F46E5]" />
          <h3 className="font-semibold text-[#111827]">Role Permission Matrix</h3>
        </div>
        {loading ? (
          <div className="skeleton h-64 rounded-xl" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-[#6B7280] border-b border-[#E5E7EB]">
                  <th className="py-2 px-3 min-w-[220px]">Capability</th>
                  {roles.map(r => (
                    <th key={r} className="py-2 px-3 text-center capitalize">{r.replace('_', ' ')}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {matrix.map((row) => (
                  <tr key={row.capability} className="border-b border-[#F3F4F6]">
                    <td className="py-2 px-3 text-[#111827]">{row.capability}</td>
                    {roles.map(r => (
                      <td key={r} className="py-2 px-3 text-center">
                        {row.roles[r]
                          ? <Check className="w-4 h-4 text-green-600 mx-auto" />
                          : <X className="w-4 h-4 text-[#D1D5DB] mx-auto" />}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

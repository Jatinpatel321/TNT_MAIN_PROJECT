import React, { useEffect, useState } from 'react';
import { Download, HardDrive, Play, RefreshCw, Database, Clock, FileText, AlertTriangle } from 'lucide-react';
import toast from 'react-hot-toast';
import { adminApi } from '../../api/admin';
import { formatTimeAgo, formatFileSize } from '../../utils/format';

interface BackupFile {
  filename: string;
  size_bytes: number;
  size_kb: number;
  size_mb: number;
  created_at: string;
}

export default function BackupRecovery() {
  const [backups, setBackups] = useState<BackupFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [backingUp, setBackingUp] = useState(false);

  const fetchBackups = async () => {
    try {
      setLoading(true);
      const res = await adminApi.getBackups();
      setBackups(res.data.backups ?? []);
    } catch {
      toast.error('Failed to load backup list');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBackups();
  }, []);

  const handleBackup = async () => {
    setBackingUp(true);
    try {
      const res = await adminApi.triggerBackup();
      const b = res.data.backup;
      toast.success(`Backup created: ${b.filename} (${b.size_mb} MB)`);
      // Refresh list
      await fetchBackups();
    } catch (err: any) {
      const detail = err?.response?.data?.detail || 'Backup failed';
      toast.error(detail);
    } finally {
      setBackingUp(false);
    }
  };

  return (
    <div className="max-w-3xl space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-lg font-bold text-[#111827]">Backup & Recovery</h2>
        <p className="text-sm text-[#6B7280] mt-1">
          Create and manage PostgreSQL database backups. Restore via CLI.
        </p>
      </div>

      {/* Run Backup */}
      <div className="tnt-card">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-lg bg-[#E85D24]/20 flex items-center justify-center">
            <Database className="w-5 h-5 text-[#E85D24]" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-[#111827]">Create a Backup</h3>
            <p className="text-xs text-[#6B7280]">
              Runs pg_dump in custom format. Saved to <code className="bg-[#F3F5F9] px-1 rounded">backups/</code> directory.
            </p>
          </div>
        </div>

        <button
          onClick={handleBackup}
          disabled={backingUp}
          className="btn-primary"
        >
          {backingUp ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" />
              Creating backup...
            </>
          ) : (
            <>
              <Play className="w-4 h-4" />
              Run Backup Now
            </>
          )}
        </button>

        {backups.length > 0 && (
          <p className="text-xs text-[#6B7280] mt-3">
            Last backup: {formatTimeAgo(backups[0].created_at)}
          </p>
        )}
      </div>

      {/* Info card */}
      <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-4 flex gap-3 text-sm">
        <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="text-amber-700 text-xs space-y-1">
          <p><strong>Restore via CLI only</strong> — Destructive operations are not exposed in the UI.</p>
          <p>To restore, run in the backend directory:</p>
          <code className="block bg-amber-700/10 px-2 py-1 rounded mt-1 font-mono">
            python scripts/restore_db.py backups/{"<filename>"}
          </code>
          <p className="mt-1">This will <strong>drop</strong> the current database and recreate it from the backup file.</p>
        </div>
      </div>

      {/* Backup List */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <HardDrive className="w-4 h-4 text-[#6B7280]" />
          <h3 className="text-sm font-semibold text-[#111827]">Backup Files</h3>
          <span className="badge bg-[#F3F5F9] text-[#6B7280] border-[#E5E7EB]">
            {backups.length}
          </span>
          <button
            onClick={fetchBackups}
            disabled={loading}
            className="ml-auto text-xs text-[#6B7280] hover:text-[#111827] flex items-center gap-1"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        <div className="space-y-2">
          {loading ? (
            <div className="tnt-card text-center py-8 text-[#6B7280] text-sm">
              Loading...
            </div>
          ) : backups.length === 0 ? (
            <div className="tnt-card text-center py-8 text-[#6B7280] text-sm">
              No backups yet. Click "Run Backup Now" to create one.
            </div>
          ) : (
            backups.map((bf) => (
              <div key={bf.filename} className="tnt-card flex items-center gap-3 py-3 px-4">
                <div className="w-8 h-8 rounded-lg bg-[#F3F5F9] flex items-center justify-center shrink-0">
                  <FileText className="w-4 h-4 text-[#6B7280]" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-[#111827] truncate">{bf.filename}</p>
                  <div className="flex items-center gap-3 text-xs text-[#6B7280] mt-0.5">
                    <span className="flex items-center gap-1">
                      <HardDrive className="w-3 h-3" />
                      {bf.size_mb >= 1 ? `${bf.size_mb} MB` : `${bf.size_kb} KB`}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {formatTimeAgo(bf.created_at)}
                    </span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

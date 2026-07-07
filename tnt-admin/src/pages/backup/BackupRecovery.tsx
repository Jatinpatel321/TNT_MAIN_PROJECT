import React, { useEffect, useState, useCallback } from 'react';
import {
  Database, Download, RefreshCw, ShieldCheck, Trash2, RotateCcw,
  HardDrive, Clock, CheckCircle, XCircle, AlertTriangle, Play,
  Calendar, BarChart3, FileText, Activity, Server, Lock,
  ChevronRight, Info, Loader2, Filter
} from 'lucide-react';
import toast from 'react-hot-toast';
import { adminApi } from '../../api/admin';

// ── Types ─────────────────────────────────────────────────────────────────

interface BackupRecord {
  id: number;
  filename: string;
  backup_type: 'manual' | 'daily' | 'weekly';
  status: 'success' | 'failed' | 'in_progress' | 'deleted';
  size_bytes: number | null;
  size_kb: number | null;
  size_mb: number | null;
  checksum_sha256: string | null;
  database_name: string | null;
  tables_count: number | null;
  rows_exported: number | null;
  duration_seconds: number | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

interface StorageStats {
  total_backups: number;
  total_size_bytes: number;
  total_size_mb: number;
  by_type: Record<string, number>;
  by_status: Record<string, number>;
  disk_free_mb: number | null;
  disk_total_bytes: number | null;
  backup_dir: string;
  oldest_backup: string | null;
  newest_backup: string | null;
}

interface SchedulerJob {
  job_id: string;
  name: string;
  next_run_time: string | null;
  trigger: string;
}

interface SchedulerStatus {
  running: boolean;
  jobs: SchedulerJob[];
}

interface VerifyResult {
  backup_id: number;
  filename: string;
  stored_checksum: string | null;
  computed_checksum: string | null;
  integrity_ok: boolean;
  file_exists: boolean;
  message: string;
}

// ── Helpers ──────────────────────────────────────────────────────────────

function formatAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function formatSize(mb: number | null, kb: number | null): string {
  if (!mb && !kb) return '—';
  if (mb !== null && mb >= 1) return `${mb.toFixed(2)} MB`;
  if (kb !== null) return `${kb.toFixed(1)} KB`;
  return '—';
}

const TYPE_COLORS: Record<string, string> = {
  manual: 'bg-violet-500/20 text-violet-300 border-violet-500/30',
  daily: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
  weekly: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
};

const STATUS_COLORS: Record<string, string> = {
  success: 'text-emerald-400',
  failed: 'text-red-400',
  in_progress: 'text-amber-400',
  deleted: 'text-slate-500',
};

const STATUS_ICONS: Record<string, React.ReactNode> = {
  success: <CheckCircle className="w-3.5 h-3.5" />,
  failed: <XCircle className="w-3.5 h-3.5" />,
  in_progress: <Loader2 className="w-3.5 h-3.5 animate-spin" />,
  deleted: <Trash2 className="w-3.5 h-3.5" />,
};

// ── Tab Components ────────────────────────────────────────────────────────

type Tab = 'dashboard' | 'recovery' | 'logs';

// ── Restore Confirmation Modal ────────────────────────────────────────────

function RestoreModal({
  backup,
  onClose,
  onConfirm,
}: {
  backup: BackupRecord;
  onClose: () => void;
  onConfirm: (phrase: string) => void;
}) {
  const [phrase, setPhrase] = useState('');
  const [loading, setLoading] = useState(false);
  const REQUIRED = 'CONFIRM RESTORE';

  const handleSubmit = async () => {
    if (phrase !== REQUIRED) {
      toast.error('Phrase does not match. Type exactly: CONFIRM RESTORE');
      return;
    }
    setLoading(true);
    try {
      await onConfirm(phrase);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-[#12121E] border border-red-500/30 rounded-2xl w-full max-w-lg shadow-2xl shadow-red-900/20">
        {/* Header */}
        <div className="p-6 border-b border-red-500/20">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-red-500/20 flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-red-400" />
            </div>
            <div>
              <h3 className="text-base font-bold text-[#F1F0FF]">Destructive Restore</h3>
              <p className="text-xs text-red-400">All current data will be replaced</p>
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4">
          <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-sm text-red-300 space-y-2">
            <p className="font-semibold">⚠️ This operation will:</p>
            <ul className="list-disc list-inside space-y-1 text-xs text-red-400">
              <li>Truncate <strong>ALL</strong> database tables</li>
              <li>Reload data from: <code className="bg-red-900/30 px-1 rounded">{backup.filename}</code></li>
              <li>This action cannot be undone</li>
            </ul>
          </div>

          <div className="space-y-2">
            <p className="text-xs text-[#9B9BC4]">
              Backup: <span className="text-[#F1F0FF] font-mono">{backup.filename}</span>
            </p>
            <p className="text-xs text-[#9B9BC4]">
              Size: <span className="text-[#F1F0FF]">{formatSize(backup.size_mb, backup.size_kb)}</span>
              {backup.tables_count && (
                <> · <span className="text-[#F1F0FF]">{backup.tables_count} tables</span></>
              )}
            </p>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold text-[#9B9BC4]">
              Type <span className="text-red-400 font-mono">CONFIRM RESTORE</span> to proceed:
            </label>
            <input
              type="text"
              value={phrase}
              onChange={(e) => setPhrase(e.target.value)}
              placeholder="CONFIRM RESTORE"
              className="w-full bg-[#1A1A2E] border border-[#2D2D4E] rounded-xl px-4 py-3 text-sm text-[#F1F0FF] font-mono placeholder:text-[#4B4B6E] focus:outline-none focus:border-red-500/50 transition"
            />
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-[#2D2D4E] flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2.5 rounded-xl border border-[#2D2D4E] text-[#9B9BC4] text-sm font-medium hover:bg-[#1A1A2E] transition"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={phrase !== REQUIRED || loading}
            className="flex-1 px-4 py-2.5 rounded-xl bg-red-500 text-white text-sm font-semibold
              disabled:opacity-40 disabled:cursor-not-allowed hover:bg-red-600 transition flex items-center justify-center gap-2"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-4 h-4" />}
            Restore Now
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Dashboard Tab ─────────────────────────────────────────────────────────

function DashboardTab({
  storage,
  scheduler,
  recentBackups,
  onRunBackup,
  runningBackup,
  onRefresh,
}: {
  storage: StorageStats | null;
  scheduler: SchedulerStatus | null;
  recentBackups: BackupRecord[];
  onRunBackup: () => void;
  runningBackup: boolean;
  onRefresh: () => void;
}) {
  const lastBackup = recentBackups[0];

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            label: 'Total Backups',
            value: storage?.total_backups ?? '—',
            icon: <Database className="w-5 h-5 text-violet-400" />,
            color: 'from-violet-500/10 to-violet-600/5',
            border: 'border-violet-500/20',
          },
          {
            label: 'Storage Used',
            value: storage ? `${storage.total_size_mb.toFixed(1)} MB` : '—',
            icon: <HardDrive className="w-5 h-5 text-blue-400" />,
            color: 'from-blue-500/10 to-blue-600/5',
            border: 'border-blue-500/20',
          },
          {
            label: 'Last Backup',
            value: lastBackup ? formatAgo(lastBackup.created_at) : 'Never',
            icon: <Clock className="w-5 h-5 text-emerald-400" />,
            color: 'from-emerald-500/10 to-emerald-600/5',
            border: 'border-emerald-500/20',
          },
          {
            label: 'Disk Free',
            value: storage?.disk_free_mb != null ? `${(storage.disk_free_mb / 1024).toFixed(1)} GB` : '—',
            icon: <Server className="w-5 h-5 text-amber-400" />,
            color: 'from-amber-500/10 to-amber-600/5',
            border: 'border-amber-500/20',
          },
        ].map((card) => (
          <div
            key={card.label}
            className={`bg-gradient-to-br ${card.color} border ${card.border} rounded-2xl p-5`}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="w-9 h-9 rounded-xl bg-black/20 flex items-center justify-center">
                {card.icon}
              </div>
            </div>
            <p className="text-2xl font-bold text-[#F1F0FF]">{card.value}</p>
            <p className="text-xs text-[#9B9BC4] mt-1">{card.label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Manual Backup Action */}
        <div className="lg:col-span-2 bg-[#12121E] border border-[#2D2D4E] rounded-2xl p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-violet-500/20 flex items-center justify-center">
              <Database className="w-5 h-5 text-violet-400" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-[#F1F0FF]">Manual Backup</h3>
              <p className="text-xs text-[#9B9BC4]">Full database snapshot with SHA-256 integrity</p>
            </div>
            <button
              onClick={onRefresh}
              className="ml-auto text-[#6B7280] hover:text-[#F1F0FF] transition"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>

          <button
            onClick={onRunBackup}
            disabled={runningBackup}
            className="w-full flex items-center justify-center gap-2 px-5 py-3 rounded-xl
              bg-gradient-to-r from-violet-600 to-violet-700 hover:from-violet-500 hover:to-violet-600
              text-white font-semibold text-sm transition-all duration-200
              disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-violet-900/30"
          >
            {runningBackup ? (
              <><Loader2 className="w-4 h-4 animate-spin" /> Creating backup...</>
            ) : (
              <><Play className="w-4 h-4" /> Run Backup Now</>
            )}
          </button>

          {lastBackup && (
            <p className="text-xs text-[#9B9BC4] mt-3 text-center">
              Last: <span className="text-[#F1F0FF]">{lastBackup.filename}</span> ·{' '}
              {formatAgo(lastBackup.created_at)}
            </p>
          )}

          {/* Backup Type Breakdown */}
          {storage && Object.keys(storage.by_type).length > 0 && (
            <div className="mt-5 grid grid-cols-3 gap-3">
              {(['manual', 'daily', 'weekly'] as const).map((type) => (
                <div key={type} className="text-center bg-[#1A1A2E] rounded-xl p-3">
                  <p className="text-lg font-bold text-[#F1F0FF]">{storage.by_type[type] ?? 0}</p>
                  <p className="text-xs text-[#9B9BC4] capitalize">{type}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Scheduler Status */}
        <div className="bg-[#12121E] border border-[#2D2D4E] rounded-2xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Calendar className="w-4 h-4 text-[#9B9BC4]" />
            <h3 className="text-sm font-bold text-[#F1F0FF]">Scheduler</h3>
            <span className={`ml-auto text-xs px-2 py-0.5 rounded-full font-medium
              ${scheduler?.running
                ? 'bg-emerald-500/20 text-emerald-400'
                : 'bg-red-500/20 text-red-400'}`}>
              {scheduler?.running ? 'Active' : 'Stopped'}
            </span>
          </div>

          <div className="space-y-3">
            {scheduler?.jobs.map((job) => (
              <div key={job.job_id} className="bg-[#1A1A2E] rounded-xl p-3">
                <p className="text-xs font-semibold text-[#F1F0FF]">{job.name}</p>
                <div className="flex items-center gap-1 mt-1">
                  <Clock className="w-3 h-3 text-[#9B9BC4]" />
                  <p className="text-xs text-[#9B9BC4]">
                    {job.next_run_time
                      ? `Next: ${formatDate(job.next_run_time)}`
                      : 'Not scheduled'}
                  </p>
                </div>
                <p className="text-xs text-[#6B7280] mt-1 font-mono truncate">{job.trigger}</p>
              </div>
            )) ?? (
              <div className="text-xs text-[#9B9BC4] text-center py-4">
                Loading scheduler info...
              </div>
            )}
          </div>

          <div className="mt-4 bg-amber-500/10 border border-amber-500/20 rounded-xl p-3">
            <p className="text-xs text-amber-300">
              <strong>Daily</strong> at 02:00 UTC · <strong>Weekly</strong> Sunday 03:00 UTC
            </p>
          </div>
        </div>
      </div>

      {/* Recent Backups Quick List */}
      {recentBackups.length > 0 && (
        <div className="bg-[#12121E] border border-[#2D2D4E] rounded-2xl p-6">
          <h3 className="text-sm font-bold text-[#F1F0FF] mb-4">Recent Backups</h3>
          <div className="space-y-2">
            {recentBackups.slice(0, 5).map((b) => (
              <div key={b.id} className="flex items-center gap-3 p-3 bg-[#1A1A2E] rounded-xl">
                <span className={`flex items-center gap-1 text-xs ${STATUS_COLORS[b.status]}`}>
                  {STATUS_ICONS[b.status]}
                </span>
                <span className={`text-xs px-2 py-0.5 rounded-md border capitalize font-medium ${TYPE_COLORS[b.backup_type]}`}>
                  {b.backup_type}
                </span>
                <span className="flex-1 text-xs text-[#F1F0FF] font-mono truncate">{b.filename}</span>
                <span className="text-xs text-[#9B9BC4]">{formatSize(b.size_mb, b.size_kb)}</span>
                <span className="text-xs text-[#6B7280]">{formatAgo(b.created_at)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Recovery Tab ──────────────────────────────────────────────────────────

function RecoveryTab({
  backups,
  loading,
  onRestore,
  onVerify,
  verifyResults,
  verifyingId,
}: {
  backups: BackupRecord[];
  loading: boolean;
  onRestore: (backup: BackupRecord) => void;
  onVerify: (id: number) => void;
  verifyResults: Record<number, VerifyResult>;
  verifyingId: number | null;
}) {
  const successBackups = backups.filter((b) => b.status === 'success');

  return (
    <div className="space-y-6">
      {/* Warning Banner */}
      <div className="bg-red-500/10 border border-red-500/25 rounded-2xl p-5 flex gap-4">
        <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="text-sm font-semibold text-red-300">Restore is a Destructive Operation</p>
          <p className="text-xs text-red-400">
            Restoring a backup will truncate all current database tables and replace them with
            backup data. This cannot be undone. Always create a fresh backup before restoring.
          </p>
        </div>
      </div>

      {/* Backup Selection Table */}
      <div className="bg-[#12121E] border border-[#2D2D4E] rounded-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-[#2D2D4E] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <RotateCcw className="w-4 h-4 text-[#9B9BC4]" />
            <h3 className="text-sm font-bold text-[#F1F0FF]">Available for Restore</h3>
            <span className="text-xs px-2 py-0.5 rounded-full bg-[#2D2D4E] text-[#9B9BC4]">
              {successBackups.length}
            </span>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-6 h-6 animate-spin text-violet-400" />
          </div>
        ) : successBackups.length === 0 ? (
          <div className="py-16 text-center">
            <Database className="w-10 h-10 text-[#4B4B6E] mx-auto mb-3" />
            <p className="text-sm text-[#9B9BC4]">No successful backups available</p>
            <p className="text-xs text-[#6B7280] mt-1">Create a backup first from the Dashboard tab</p>
          </div>
        ) : (
          <div className="divide-y divide-[#1E1E32]">
            {successBackups.map((b) => {
              const verResult = verifyResults[b.id];
              const isVerifying = verifyingId === b.id;

              return (
                <div key={b.id} className="px-6 py-4 hover:bg-[#1A1A2E] transition-colors">
                  <div className="flex items-start gap-4">
                    {/* File Icon */}
                    <div className="w-9 h-9 rounded-xl bg-[#2D2D4E] flex items-center justify-center shrink-0 mt-0.5">
                      <FileText className="w-4 h-4 text-[#9B9BC4]" />
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="text-sm font-medium text-[#F1F0FF] font-mono truncate">{b.filename}</p>
                        <span className={`text-xs px-2 py-0.5 rounded-md border capitalize font-medium ${TYPE_COLORS[b.backup_type]}`}>
                          {b.backup_type}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 mt-1.5 flex-wrap">
                        <span className="text-xs text-[#9B9BC4] flex items-center gap-1">
                          <HardDrive className="w-3 h-3" /> {formatSize(b.size_mb, b.size_kb)}
                        </span>
                        {b.tables_count && (
                          <span className="text-xs text-[#9B9BC4] flex items-center gap-1">
                            <Database className="w-3 h-3" /> {b.tables_count} tables
                          </span>
                        )}
                        {b.rows_exported && (
                          <span className="text-xs text-[#9B9BC4]">
                            {b.rows_exported.toLocaleString()} rows
                          </span>
                        )}
                        <span className="text-xs text-[#9B9BC4] flex items-center gap-1">
                          <Clock className="w-3 h-3" /> {formatDate(b.created_at)}
                        </span>
                      </div>

                      {/* Integrity Status */}
                      {verResult && (
                        <div className={`mt-2 flex items-center gap-2 text-xs rounded-lg px-3 py-1.5
                          ${verResult.integrity_ok
                            ? 'bg-emerald-500/10 text-emerald-400'
                            : 'bg-red-500/10 text-red-400'}`}>
                          {verResult.integrity_ok
                            ? <><CheckCircle className="w-3 h-3" /> Integrity verified — {verResult.message}</>
                            : <><XCircle className="w-3 h-3" /> {verResult.message}</>}
                        </div>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        onClick={() => onVerify(b.id)}
                        disabled={isVerifying}
                        title="Verify integrity"
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
                          bg-[#2D2D4E] text-[#9B9BC4] hover:bg-[#3D3D5E] hover:text-[#F1F0FF]
                          disabled:opacity-50 transition"
                      >
                        {isVerifying
                          ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          : <ShieldCheck className="w-3.5 h-3.5" />}
                        Verify
                      </button>
                      <button
                        onClick={() => onRestore(b)}
                        title="Restore this backup"
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold
                          bg-red-500/20 text-red-400 hover:bg-red-500/30 border border-red-500/30 transition"
                      >
                        <RotateCcw className="w-3.5 h-3.5" />
                        Restore
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Logs Tab ──────────────────────────────────────────────────────────────

function LogsTab({
  backups,
  loading,
  page,
  totalPages,
  onPageChange,
  filterType,
  setFilterType,
  filterStatus,
  setFilterStatus,
  onRefresh,
  onDelete,
  deletingId,
}: {
  backups: BackupRecord[];
  loading: boolean;
  page: number;
  totalPages: number;
  onPageChange: (p: number) => void;
  filterType: string;
  setFilterType: (t: string) => void;
  filterStatus: string;
  setFilterStatus: (s: string) => void;
  onRefresh: () => void;
  onDelete: (id: number, filename: string) => void;
  deletingId: number | null;
}) {
  return (
    <div className="space-y-5">
      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-[#9B9BC4]" />
          <span className="text-xs text-[#9B9BC4]">Filter:</span>
        </div>
        <select
          value={filterType}
          onChange={(e) => { setFilterType(e.target.value); onPageChange(1); }}
          className="bg-[#1A1A2E] border border-[#2D2D4E] text-[#F1F0FF] text-xs rounded-lg px-3 py-2 focus:outline-none focus:border-violet-500/50"
        >
          <option value="">All Types</option>
          <option value="manual">Manual</option>
          <option value="daily">Daily</option>
          <option value="weekly">Weekly</option>
        </select>
        <select
          value={filterStatus}
          onChange={(e) => { setFilterStatus(e.target.value); onPageChange(1); }}
          className="bg-[#1A1A2E] border border-[#2D2D4E] text-[#F1F0FF] text-xs rounded-lg px-3 py-2 focus:outline-none focus:border-violet-500/50"
        >
          <option value="">All Statuses</option>
          <option value="success">Success</option>
          <option value="failed">Failed</option>
          <option value="in_progress">In Progress</option>
        </select>
        <button
          onClick={onRefresh}
          disabled={loading}
          className="ml-auto flex items-center gap-1.5 text-xs text-[#9B9BC4] hover:text-[#F1F0FF] transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Table */}
      <div className="bg-[#12121E] border border-[#2D2D4E] rounded-2xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[#2D2D4E] bg-[#0F0F1A]">
              <th className="px-5 py-3.5 text-left text-xs font-semibold text-[#6B7280] uppercase tracking-wide">Filename</th>
              <th className="px-4 py-3.5 text-left text-xs font-semibold text-[#6B7280] uppercase tracking-wide">Type</th>
              <th className="px-4 py-3.5 text-left text-xs font-semibold text-[#6B7280] uppercase tracking-wide">Status</th>
              <th className="px-4 py-3.5 text-left text-xs font-semibold text-[#6B7280] uppercase tracking-wide">Size</th>
              <th className="px-4 py-3.5 text-left text-xs font-semibold text-[#6B7280] uppercase tracking-wide">Tables</th>
              <th className="px-4 py-3.5 text-left text-xs font-semibold text-[#6B7280] uppercase tracking-wide">Duration</th>
              <th className="px-4 py-3.5 text-left text-xs font-semibold text-[#6B7280] uppercase tracking-wide">Created</th>
              <th className="px-4 py-3.5 text-left text-xs font-semibold text-[#6B7280] uppercase tracking-wide">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={8} className="text-center py-16">
                  <Loader2 className="w-6 h-6 animate-spin text-violet-400 mx-auto" />
                </td>
              </tr>
            ) : backups.length === 0 ? (
              <tr>
                <td colSpan={8} className="text-center py-16">
                  <Activity className="w-8 h-8 text-[#4B4B6E] mx-auto mb-2" />
                  <p className="text-sm text-[#9B9BC4]">No backup records found</p>
                </td>
              </tr>
            ) : (
              backups.map((b) => (
                <tr key={b.id} className="border-b border-[#1E1E32] hover:bg-[#1A1A2E] transition-colors">
                  <td className="px-5 py-3.5">
                    <span className="text-xs font-mono text-[#F1F0FF] truncate block max-w-[220px]" title={b.filename}>
                      {b.filename}
                    </span>
                    {b.error_message && (
                      <span className="text-xs text-red-400 mt-0.5 block truncate max-w-[220px]" title={b.error_message}>
                        {b.error_message}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3.5">
                    <span className={`text-xs px-2 py-0.5 rounded-md border capitalize font-medium ${TYPE_COLORS[b.backup_type]}`}>
                      {b.backup_type}
                    </span>
                  </td>
                  <td className="px-4 py-3.5">
                    <span className={`flex items-center gap-1.5 text-xs font-medium ${STATUS_COLORS[b.status]}`}>
                      {STATUS_ICONS[b.status]} {b.status}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 text-xs text-[#9B9BC4]">{formatSize(b.size_mb, b.size_kb)}</td>
                  <td className="px-4 py-3.5 text-xs text-[#9B9BC4]">{b.tables_count ?? '—'}</td>
                  <td className="px-4 py-3.5 text-xs text-[#9B9BC4]">{b.duration_seconds != null ? `${b.duration_seconds}s` : '—'}</td>
                  <td className="px-4 py-3.5 text-xs text-[#9B9BC4] whitespace-nowrap">{formatDate(b.created_at)}</td>
                  <td className="px-4 py-3.5">
                    {b.status === 'success' && (
                      <button
                        onClick={() => onDelete(b.id, b.filename)}
                        disabled={deletingId === b.id}
                        title="Delete backup"
                        className="text-red-400 hover:text-red-300 disabled:opacity-40 transition"
                      >
                        {deletingId === b.id
                          ? <Loader2 className="w-4 h-4 animate-spin" />
                          : <Trash2 className="w-4 h-4" />}
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            className="px-3 py-1.5 rounded-lg text-xs text-[#9B9BC4] bg-[#1A1A2E] hover:bg-[#2D2D4E] disabled:opacity-40 transition"
          >
            Previous
          </button>
          <span className="text-xs text-[#9B9BC4]">Page {page} of {totalPages}</span>
          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
            className="px-3 py-1.5 rounded-lg text-xs text-[#9B9BC4] bg-[#1A1A2E] hover:bg-[#2D2D4E] disabled:opacity-40 transition"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────

export default function BackupRecovery() {
  const [activeTab, setActiveTab] = useState<Tab>('dashboard');
  const [backups, setBackups] = useState<BackupRecord[]>([]);
  const [storage, setStorage] = useState<StorageStats | null>(null);
  const [scheduler, setScheduler] = useState<SchedulerStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [runningBackup, setRunningBackup] = useState(false);
  const [restoreTarget, setRestoreTarget] = useState<BackupRecord | null>(null);
  const [verifyResults, setVerifyResults] = useState<Record<number, VerifyResult>>({});
  const [verifyingId, setVerifyingId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [filterType, setFilterType] = useState('');
  const [filterStatus, setFilterStatus] = useState('');

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [backupRes, storageRes, schedRes] = await Promise.allSettled([
        adminApi.getBackupList({ page, page_size: 20, backup_type: filterType || undefined, status: filterStatus || undefined }),
        adminApi.getStorageStats(),
        adminApi.getSchedulerStatus(),
      ]);

      if (backupRes.status === 'fulfilled') {
        const data = backupRes.value.data;
        setBackups(data.backups ?? []);
        setTotalPages(data.total_pages ?? 1);
      }
      if (storageRes.status === 'fulfilled') {
        setStorage(storageRes.value.data);
      }
      if (schedRes.status === 'fulfilled') {
        setScheduler(schedRes.value.data);
      }
    } catch {
      toast.error('Failed to load backup data');
    } finally {
      setLoading(false);
    }
  }, [page, filterType, filterStatus]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const handleRunBackup = async () => {
    setRunningBackup(true);
    try {
      const res = await adminApi.triggerBackup();
      const b = res.data.backup;
      toast.success(`✅ Backup created: ${b.filename} (${b.size_mb ?? '—'} MB)`);
      await fetchAll();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Backup failed');
    } finally {
      setRunningBackup(false);
    }
  };

  const handleVerify = async (id: number) => {
    setVerifyingId(id);
    try {
      const res = await adminApi.verifyBackup(id);
      const result: VerifyResult = res.data;
      setVerifyResults((prev) => ({ ...prev, [id]: result }));
      if (result.integrity_ok) {
        toast.success('✅ Backup integrity verified!');
      } else {
        toast.error(`⚠️ Integrity check failed: ${result.message}`);
      }
    } catch {
      toast.error('Verification failed');
    } finally {
      setVerifyingId(null);
    }
  };

  const handleRestore = async (phrase: string) => {
    if (!restoreTarget) return;
    try {
      const res = await adminApi.restoreBackup(restoreTarget.id, phrase);
      toast.success(`✅ Restore complete — ${res.data.tables_restored} tables restored in ${res.data.duration_seconds}s`);
      setRestoreTarget(null);
      await fetchAll();
    } catch (err: any) {
      const detail = err?.response?.data?.detail || 'Restore failed';
      toast.error(`Restore failed: ${detail}`);
      throw err;
    }
  };

  const handleDelete = async (id: number, filename: string) => {
    if (!window.confirm(`Delete backup "${filename}"? This removes the file from disk.`)) return;
    setDeletingId(id);
    try {
      await adminApi.deleteBackup(id);
      toast.success('Backup deleted');
      await fetchAll();
    } catch {
      toast.error('Delete failed');
    } finally {
      setDeletingId(null);
    }
  };

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: 'dashboard', label: 'Dashboard', icon: <BarChart3 className="w-4 h-4" /> },
    { id: 'recovery', label: 'Recovery', icon: <RotateCcw className="w-4 h-4" /> },
    { id: 'logs', label: 'Backup Logs', icon: <Activity className="w-4 h-4" /> },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center gap-4">
        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-violet-500/30 to-violet-600/10 border border-violet-500/30 flex items-center justify-center">
          <Database className="w-6 h-6 text-violet-400" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-[#F1F0FF]">Backup & Recovery</h1>
          <p className="text-xs text-[#9B9BC4] mt-0.5">
            PostgreSQL database backup, restore, and integrity monitoring
          </p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <div className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg bg-[#12121E] border border-[#2D2D4E] text-[#9B9BC4]">
            <Lock className="w-3 h-3 text-violet-400" />
            Admin Only
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-1 bg-[#0F0F1A] border border-[#2D2D4E] rounded-xl p-1">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 flex-1 justify-center
              ${activeTab === tab.id
                ? 'bg-violet-600 text-white shadow-lg shadow-violet-900/30'
                : 'text-[#9B9BC4] hover:text-[#F1F0FF] hover:bg-[#1A1A2E]'
              }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'dashboard' && (
        <DashboardTab
          storage={storage}
          scheduler={scheduler}
          recentBackups={backups}
          onRunBackup={handleRunBackup}
          runningBackup={runningBackup}
          onRefresh={fetchAll}
        />
      )}
      {activeTab === 'recovery' && (
        <RecoveryTab
          backups={backups}
          loading={loading}
          onRestore={setRestoreTarget}
          onVerify={handleVerify}
          verifyResults={verifyResults}
          verifyingId={verifyingId}
        />
      )}
      {activeTab === 'logs' && (
        <LogsTab
          backups={backups}
          loading={loading}
          page={page}
          totalPages={totalPages}
          onPageChange={setPage}
          filterType={filterType}
          setFilterType={setFilterType}
          filterStatus={filterStatus}
          setFilterStatus={setFilterStatus}
          onRefresh={fetchAll}
          onDelete={handleDelete}
          deletingId={deletingId}
        />
      )}

      {/* Restore Confirmation Modal */}
      {restoreTarget && (
        <RestoreModal
          backup={restoreTarget}
          onClose={() => setRestoreTarget(null)}
          onConfirm={handleRestore}
        />
      )}
    </div>
  );
}

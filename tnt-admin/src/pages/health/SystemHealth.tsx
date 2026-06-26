import React, { useEffect, useState } from 'react';
import { adminApi } from '../../api/admin';
import {
  Activity, Database, Server, RefreshCw, AlertTriangle, CheckCircle2,
  XCircle, Clock, Cpu, HardDrive, Bell, Brain, Zap, TrendingUp
} from 'lucide-react';
import toast from 'react-hot-toast';

interface SubsystemInfo {
  status: 'healthy' | 'degraded' | 'unhealthy';
  [key: string]: any;
}

interface HealthMetrics {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  subsystems: {
    backend: SubsystemInfo & { cpu_usage_pct: number; memory_usage_pct: number; uptime_seconds: number };
    database: SubsystemInfo & { latency_ms: number; message: string };
    redis: SubsystemInfo & { latency_ms: number; message: string };
    notifications: SubsystemInfo & { fcm_active: boolean; sms_active: boolean; message: string };
    ai_engine: SubsystemInfo & { total_models: number; active_models: number; message: string };
    storage: SubsystemInfo & { free_gb: number; total_gb: number; usage_pct: number; uploads_dir_size_mb: number; models_dir_size_mb: number };
    api_health: SubsystemInfo & { total_requests: number; server_errors: number; error_rate_pct: number; avg_response_time_ms: number };
    queue_health: SubsystemInfo & { notifications_queue_depth: number; scheduler_running: boolean; cron_jobs_scheduled: number };
  };
  history: Array<{
    timestamp: string;
    db_latency: number;
    redis_latency: number;
    cpu_usage: number;
    memory_usage: number;
    queue_depth: number;
    error_rate: number;
  }>;
}

export default function SystemHealth() {
  const [data, setData] = useState<HealthMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [pollingRate, setPollingRate] = useState<number>(10000); // 10s default
  const [chartTab, setChartTab] = useState<'latency' | 'resources' | 'queue'>('latency');

  const fetchHealthData = async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const res = await adminApi.getSystemHealthMetrics();
      setData(res.data);
    } catch (err) {
      console.error('Error fetching health checks', err);
      toast.error('Failed to retrieve system health metrics');
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealthData();
  }, []);

  // Polling setup
  useEffect(() => {
    if (pollingRate === 0) return;
    const interval = setInterval(() => {
      fetchHealthData(true);
    }, pollingRate);
    return () => clearInterval(interval);
  }, [pollingRate]);

  const handleManualRefresh = () => {
    fetchHealthData();
    toast.success('System health diagnostics complete');
  };

  // Status visual helpers
  const getStatusColor = (status: 'healthy' | 'degraded' | 'unhealthy') => {
    if (status === 'healthy') return 'text-emerald-500 border-emerald-200 bg-emerald-50';
    if (status === 'degraded') return 'text-amber-500 border-amber-200 bg-amber-50';
    return 'text-rose-500 border-rose-200 bg-rose-50';
  };

  const getStatusIcon = (status: 'healthy' | 'degraded' | 'unhealthy') => {
    if (status === 'healthy') return <CheckCircle2 className="w-5 h-5 text-emerald-500" />;
    if (status === 'degraded') return <AlertTriangle className="w-5 h-5 text-amber-500" />;
    return <XCircle className="w-5 h-5 text-rose-500" />;
  };

  const formatUptime = (seconds: number) => {
    const d = Math.floor(seconds / (3600 * 24));
    const h = Math.floor((seconds % (3600 * 24)) / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return `${d}d ${h}h ${m}m`;
  };

  // Custom SVG Line Graph Renderer
  const renderSVGChart = (
    key1: 'db_latency' | 'cpu_usage' | 'queue_depth',
    key2: 'redis_latency' | 'memory_usage' | 'error_rate',
    title1: string,
    title2: string,
    color1 = '#3B82F6',
    color2 = '#8B5CF6',
    unit = 'ms'
  ) => {
    if (!data || !data.history || data.history.length === 0) return null;
    
    const history = data.history;
    const width = 600;
    const height = 180;
    const padding = 30;

    const maxVal1 = Math.max(...history.map(d => d[key1] as number), 1.0);
    const maxVal2 = Math.max(...history.map(d => d[key2] as number), 1.0);
    const overallMax = Math.max(maxVal1, maxVal2) * 1.15; // 15% headroom

    const points1 = history.map((d, index) => {
      const x = padding + (index / (history.length - 1)) * (width - padding * 2);
      const y = height - padding - ((d[key1] as number) / overallMax) * (height - padding * 2);
      return `${x},${y}`;
    }).join(' ');

    const points2 = history.map((d, index) => {
      const x = padding + (index / (history.length - 1)) * (width - padding * 2);
      const y = height - padding - ((d[key2] as number) / overallMax) * (height - padding * 2);
      return `${x},${y}`;
    }).join(' ');

    // Fill paths (area under the line)
    const fillPath1 = history.map((d, index) => {
      const x = padding + (index / (history.length - 1)) * (width - padding * 2);
      const y = height - padding - ((d[key1] as number) / overallMax) * (height - padding * 2);
      return {x, y};
    });
    const fillStr1 = fillPath1.length > 0 
      ? `M ${padding},${height - padding} L ${fillPath1.map(p => `${p.x},${p.y}`).join(' L ')} L ${width - padding},${height - padding} Z`
      : '';

    const fillPath2 = history.map((d, index) => {
      const x = padding + (index / (history.length - 1)) * (width - padding * 2);
      const y = height - padding - ((d[key2] as number) / overallMax) * (height - padding * 2);
      return {x, y};
    });
    const fillStr2 = fillPath2.length > 0 
      ? `M ${padding},${height - padding} L ${fillPath2.map(p => `${p.x},${p.y}`).join(' L ')} L ${width - padding},${height - padding} Z`
      : '';

    return (
      <div className="relative w-full h-[220px]">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full">
          <defs>
            <linearGradient id={`grad1`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color1} stopOpacity="0.25"/>
              <stop offset="100%" stopColor={color1} stopOpacity="0.0"/>
            </linearGradient>
            <linearGradient id={`grad2`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color2} stopOpacity="0.25"/>
              <stop offset="100%" stopColor={color2} stopOpacity="0.0"/>
            </linearGradient>
          </defs>

          {/* Gridlines */}
          <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#F3F4F6" strokeWidth="2" />
          <line x1={padding} y1={height - padding - (height - padding * 2) * 0.5} x2={width - padding} y2={height - padding - (height - padding * 2) * 0.5} stroke="#F9FAFB" strokeWidth="1" strokeDasharray="4" />
          <line x1={padding} y1={padding} x2={width - padding} y2={padding} stroke="#F9FAFB" strokeWidth="1" />

          {/* Fill Areas */}
          {fillStr1 && <path d={fillStr1} fill={`url(#grad1)`} />}
          {fillStr2 && <path d={fillStr2} fill={`url(#grad2)`} />}

          {/* Line 1 */}
          <polyline fill="none" stroke={color1} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" points={points1} />
          {/* Line 2 */}
          <polyline fill="none" stroke={color2} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" points={points2} />

          {/* Interactive dots for the final point */}
          {history.length > 0 && (() => {
            const lastIdx = history.length - 1;
            const x = padding + (width - padding * 2);
            const y1 = height - padding - ((history[lastIdx][key1] as number) / overallMax) * (height - padding * 2);
            const y2 = height - padding - ((history[lastIdx][key2] as number) / overallMax) * (height - padding * 2);
            return (
              <>
                <circle cx={x} cy={y1} r="4" fill={color1} stroke="#ffffff" strokeWidth="1.5" />
                <circle cx={x} cy={y2} r="4" fill={color2} stroke="#ffffff" strokeWidth="1.5" />
              </>
            );
          })()}

          {/* Y Axis Labels */}
          <text x={padding - 5} y={padding + 4} textAnchor="end" fontSize="9" fill="#9CA3AF" fontFamily="monospace">
            {Math.round(overallMax)}{unit}
          </text>
          <text x={padding - 5} y={height - padding} textAnchor="end" fontSize="9" fill="#9CA3AF" fontFamily="monospace">
            0{unit}
          </text>
        </svg>

        {/* Legend */}
        <div className="absolute top-2 right-4 flex items-center gap-4 text-xs font-semibold text-[#4B5563]">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-1 rounded" style={{ backgroundColor: color1 }} />
            <span>{title1}: {history[history.length - 1][key1] as number}{unit}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-1 rounded" style={{ backgroundColor: color2 }} />
            <span>{title2}: {history[history.length - 1][key2] as number}{unit}</span>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Title */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[#111827] flex items-center gap-2.5">
            <Activity className="w-7 h-7 text-indigo-600 animate-pulse" />
            System Health Monitoring
          </h1>
          <p className="text-sm text-[#4B5563]">Operational metrics, latencies, resource indicators, and backup daemon status.</p>
        </div>
        
        <div className="flex items-center gap-3">
          {/* Polling Selector */}
          <div className="flex items-center gap-2 bg-white border border-[#E5E7EB] rounded-xl px-3 py-1.5 text-xs font-medium text-[#4B5563]">
            <span className="text-[#9CA3AF]">Refresh rate:</span>
            <select
              value={pollingRate}
              onChange={(e) => setPollingRate(parseInt(e.target.value))}
              className="bg-transparent font-semibold border-none outline-none text-[#111827] cursor-pointer"
            >
              <option value={5000}>5 seconds</option>
              <option value={10000}>10 seconds</option>
              <option value={30000}>30 seconds</option>
              <option value={0}>Manual only</option>
            </select>
          </div>

          <button
            onClick={handleManualRefresh}
            disabled={loading}
            className="btn-primary bg-indigo-600 hover:bg-indigo-700 text-white font-semibold flex items-center gap-2 text-xs py-2 px-3"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Run Diagnostics
          </button>
        </div>
      </div>

      {/* Main Subsystem Indicators */}
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
          {Object.entries(data.subsystems).map(([key, sub]: [string, any]) => (
            <div
              key={key}
              className={`tnt-card p-4 border rounded-2xl flex flex-col justify-between hover:shadow-md transition-all ${
                getStatusColor(sub.status)
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-gray-500">{key.replace('_', ' ')}</span>
                {getStatusIcon(sub.status)}
              </div>
              <div className="mt-4">
                <h4 className="text-2xl font-bold text-[#111827] capitalize">{sub.status}</h4>
                <p className="text-[10px] text-gray-500 mt-1 truncate">
                  {key === 'database' || key === 'redis' ? `${sub.latency_ms}ms response` : ''}
                  {key === 'backend' ? `${sub.cpu_usage_pct}% CPU` : ''}
                  {key === 'storage' ? `${sub.usage_pct}% disk` : ''}
                  {key === 'queue_health' ? `${sub.notifications_queue_depth} queued` : ''}
                  {key === 'api_health' ? `${sub.error_rate_pct}% errors` : ''}
                  {key === 'ai_engine' ? `${sub.active_models} active models` : ''}
                  {key === 'notifications' ? (sub.fcm_active && sub.sms_active ? 'Dual Active' : 'Degraded config') : ''}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Grid: Charts + Subsystem Details */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Performance Charts */}
        <div className="lg:col-span-2 tnt-card bg-white border border-[#E5E7EB] rounded-3xl p-6 flex flex-col justify-between">
          <div className="flex justify-between items-center border-b border-[#F3F4F6] pb-4 mb-4">
            <div>
              <h3 className="text-lg font-bold text-[#111827] flex items-center gap-1.5">
                <TrendingUp className="w-5 h-5 text-indigo-600" />
                Performance Telemetry
              </h3>
              <p className="text-xs text-[#6B7280]">Historical system metrics tracked over the last 50 runs</p>
            </div>
            
            {/* Chart toggle buttons */}
            <div className="flex bg-[#F3F4F6] p-1 rounded-xl gap-1">
              <button
                onClick={() => setChartTab('latency')}
                className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                  chartTab === 'latency' ? 'bg-white text-indigo-600 shadow' : 'text-[#6B7280] hover:text-[#374151]'
                }`}
              >
                Query Speed
              </button>
              <button
                onClick={() => setChartTab('resources')}
                className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                  chartTab === 'resources' ? 'bg-white text-indigo-600 shadow' : 'text-[#6B7280] hover:text-[#374151]'
                }`}
              >
                CPU/RAM load
              </button>
              <button
                onClick={() => setChartTab('queue')}
                className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                  chartTab === 'queue' ? 'bg-white text-indigo-600 shadow' : 'text-[#6B7280] hover:text-[#374151]'
                }`}
              >
                Queue & Errors
              </button>
            </div>
          </div>

          {/* SVG Line Graph */}
          {data && (
            <div className="flex-1 flex items-center justify-center">
              {chartTab === 'latency' && renderSVGChart('db_latency', 'redis_latency', 'DB Query Latency', 'Redis Response Latency', '#3B82F6', '#10B981', 'ms')}
              {chartTab === 'resources' && renderSVGChart('cpu_usage', 'memory_usage', 'CPU Utilization', 'RAM Utilization', '#F59E0B', '#8B5CF6', '%')}
              {chartTab === 'queue' && renderSVGChart('queue_depth', 'error_rate', 'Notifications Queue', 'API Error Rate', '#EF4444', '#EC4899', '')}
            </div>
          )}
        </div>

        {/* Summary side checklist */}
        <div className="lg:col-span-1 tnt-card bg-white border border-[#E5E7EB] rounded-3xl p-6 space-y-6">
          <h3 className="text-lg font-bold text-[#111827] border-b border-[#F3F4F6] pb-3">Subsystem Details</h3>
          
          {data && (
            <div className="space-y-4 text-sm">
              {/* Backend details */}
              <div className="flex items-start gap-3">
                <Server className="w-5 h-5 text-indigo-600 shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-semibold text-[#111827]">Application Server</h4>
                  <div className="grid grid-cols-2 gap-x-4 mt-1 text-xs text-[#6B7280] font-medium font-mono">
                    <p>Uptime: {formatUptime(data.subsystems.backend.uptime_seconds)}</p>
                    <p>CPU load: {data.subsystems.backend.cpu_usage_pct}%</p>
                    <p>RAM usage: {data.subsystems.backend.memory_usage_pct}%</p>
                    <p>Version: {data.subsystems.backend.version}</p>
                  </div>
                </div>
              </div>

              {/* Database details */}
              <div className="flex items-start gap-3">
                <Database className="w-5 h-5 text-indigo-600 shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-semibold text-[#111827]">PostgreSQL DB</h4>
                  <p className="text-xs text-[#6B7280] mt-0.5 leading-snug">{data.subsystems.database.message}</p>
                  <p className="text-[10px] text-[#9CA3AF] font-mono mt-0.5">Average query time: {data.subsystems.database.latency_ms}ms</p>
                </div>
              </div>

              {/* Storage check */}
              <div className="flex items-start gap-3">
                <HardDrive className="w-5 h-5 text-indigo-600 shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-semibold text-[#111827]">Storage & Volume</h4>
                  <div className="grid grid-cols-2 gap-x-4 mt-1 text-xs text-[#6B7280] font-medium font-mono">
                    <p>Free Space: {data.subsystems.storage.free_gb}GB</p>
                    <p>Total Size: {data.subsystems.storage.total_gb}GB</p>
                    <p>Uploads dir: {data.subsystems.storage.uploads_dir_size_mb}MB</p>
                    <p>AI Models: {data.subsystems.storage.models_dir_size_mb}MB</p>
                  </div>
                  {/* Progress bar */}
                  <div className="w-full bg-[#F3F4F6] rounded-full h-2 mt-2">
                    <div
                      className="bg-indigo-600 h-2 rounded-full transition-all"
                      style={{ width: `${data.subsystems.storage.usage_pct}%` }}
                    />
                  </div>
                  <p className="text-[10px] text-[#9CA3AF] mt-1">Disk utilization: {data.subsystems.storage.usage_pct}%</p>
                </div>
              </div>

              {/* Notifications */}
              <div className="flex items-start gap-3">
                <Bell className="w-5 h-5 text-indigo-600 shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-semibold text-[#111827]">Notification Service</h4>
                  <p className="text-xs text-[#6B7280] mt-0.5">{data.subsystems.notifications.message}</p>
                  <div className="flex gap-4 mt-1.5 text-xs font-semibold">
                    <span className={data.subsystems.notifications.fcm_active ? 'text-emerald-600' : 'text-rose-600'}>
                      Push: {data.subsystems.notifications.fcm_active ? 'Active' : 'Inactive'}
                    </span>
                    <span className={data.subsystems.notifications.sms_active ? 'text-emerald-600' : 'text-rose-600'}>
                      Twilio: {data.subsystems.notifications.sms_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                </div>
              </div>

              {/* AI engine */}
              <div className="flex items-start gap-3">
                <Brain className="w-5 h-5 text-indigo-600 shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-semibold text-[#111827]">AI Intelligence Engine</h4>
                  <p className="text-xs text-[#6B7280] mt-0.5">{data.subsystems.ai_engine.message}</p>
                  <p className="text-[10px] text-[#9CA3AF] font-mono mt-0.5">Trained ML models: {data.subsystems.ai_engine.total_models}</p>
                </div>
              </div>

              {/* Queue details */}
              <div className="flex items-start gap-3">
                <Zap className="w-5 h-5 text-indigo-600 shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-semibold text-[#111827]">Queue Depth & Cron</h4>
                  <div className="grid grid-cols-2 gap-x-4 mt-1 text-xs text-[#6B7280] font-medium font-mono">
                    <p>Notification Q: {data.subsystems.queue_health.notifications_queue_depth}</p>
                    <p>Cron Jobs: {data.subsystems.queue_health.cron_jobs_scheduled}</p>
                  </div>
                  <p className="text-[10px] text-[#9CA3AF] mt-1">
                    Scheduler Status: {data.subsystems.queue_health.scheduler_running ? 'Active daemon' : 'Stopped'}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

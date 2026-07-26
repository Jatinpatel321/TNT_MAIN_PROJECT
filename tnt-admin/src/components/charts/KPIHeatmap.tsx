import React from 'react';
import { cn } from '../../utils/cn';

interface KPIHeatmapProps {
  data: Record<number, Record<number, number>>;
  title?: string;
}

const DAYS_OF_WEEK = [
  { value: 1, label: 'Mon' },
  { value: 2, label: 'Tue' },
  { value: 3, label: 'Wed' },
  { value: 4, label: 'Thu' },
  { value: 5, label: 'Fri' },
  { value: 6, label: 'Sat' },
  { value: 0, label: 'Sun' },
];

const HOURS = Array.from({ length: 13 }, (_, i) => i + 8); // 8 AM to 8 PM

export function KPIHeatmap({ data, title = 'Weekly Hourly Peak Distribution' }: KPIHeatmapProps) {
  // Helper to color cells based on volume
  const getCellColorClass = (count: number) => {
    if (!count || count === 0) return 'bg-[#F9FAFB] hover:bg-[#F3F4F6] border-[#F3F4F6] text-[#9CA3AF]';
    if (count <= 2) return 'bg-[#FFF7ED] text-[#E85D24] hover:bg-[#FFEDD5] border-[#FFEDD5]';
    if (count <= 5) return 'bg-[#FFEDD5] text-[#C2410C] hover:bg-[#FDBA74] border-[#FDBA74]';
    if (count <= 10) return 'bg-[#F97316] text-white hover:bg-[#EA580C] border-[#EA580C]';
    return 'bg-[#E85D24] text-white hover:bg-[#D84D14] border-[#D84D14] shadow-xs animate-pulse';
  };

  return (
    <div className="tnt-card">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h3 className="text-base font-bold tracking-tight text-[#111827]">{title}</h3>
          <p className="text-xs text-[#6B7280] mt-0.5">Visual representation of peak orders throughout the week</p>
        </div>
        <div className="flex items-center gap-3 text-xs text-[#4B5563] bg-[#F9FAFB] px-3 py-1.5 rounded-lg border border-[#E5E7EB]">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded bg-[#F9FAFB] border border-[#E5E7EB]" />
            <span>Idle (0)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded bg-[#FFF7ED] border border-[#FFEDD5]" />
            <span>Low (1-2)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded bg-[#F97316]" />
            <span>Medium (3-10)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded bg-[#E85D24]" />
            <span>Peak (&gt;10)</span>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto pb-2">
        <div className="min-w-[700px] space-y-2">
          {/* Header Row: Hours */}
          <div className="flex items-center gap-2">
            <div className="w-12 shrink-0 text-xs font-semibold text-[#9CA3AF]" />
            <div
              className="flex-1 grid gap-1.5"
              style={{ gridTemplateColumns: 'repeat(13, minmax(0, 1fr))' }}
            >
              {HOURS.map(h => (
                <div key={h} className="text-center text-xs font-semibold text-[#6B7280] truncate">
                  {h > 12 ? `${h - 12} PM` : h === 12 ? '12 PM' : `${h} AM`}
                </div>
              ))}
            </div>
          </div>

          {/* Grid Rows: Days */}
          {DAYS_OF_WEEK.map(day => (
            <div key={day.value} className="flex items-center gap-2">
              <div className="w-12 shrink-0 text-xs font-bold text-[#374151]">
                {day.label}
              </div>
              <div
                className="flex-1 grid gap-1.5"
                style={{ gridTemplateColumns: 'repeat(13, minmax(0, 1fr))' }}
              >
                {HOURS.map(hour => {
                  const dayData = data[day.value] || {};
                  const count = dayData[hour] || 0;
                  return (
                    <div
                      key={hour}
                      className={cn(
                        "h-10 rounded-lg border flex items-center justify-center font-mono text-xs font-bold transition-all cursor-default select-none shadow-xs hover:scale-105",
                        getCellColorClass(count)
                      )}
                      title={`${day.label} at ${hour > 12 ? hour - 12 + ' PM' : hour === 12 ? '12 PM' : hour + ' AM'}: ${count} order(s)`}
                    >
                      {count > 0 ? count : ''}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

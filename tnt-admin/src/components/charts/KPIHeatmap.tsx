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
    if (!count || count === 0) return 'bg-[#F9FAFB] hover:bg-[#F3F4F6] border-[#F3F4F6]';
    if (count <= 2) return 'bg-[#EEF2FF] text-[#4F46E5] hover:bg-[#E0E7FF] border-[#E0E7FF]';
    if (count <= 5) return 'bg-[#C7D2FE] text-[#3730A3] hover:bg-[#B5C2FD] border-[#B5C2FD]';
    if (count <= 10) return 'bg-[#818CF8] text-white hover:bg-[#6366F1] border-[#6366F1]';
    return 'bg-[#4F46E5] text-white hover:bg-[#4338CA] border-[#4338CA] animate-pulse';
  };

  return (
    <div className="tnt-card">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-base font-bold tracking-tight text-[#111827]">{title}</h3>
          <p className="text-xs text-[#9CA3AF] mt-0.5">Visual representation of peak orders throughout the week</p>
        </div>
        <div className="flex items-center gap-3 text-xs text-[#4B5563]">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded bg-[#F9FAFB] border border-[#E5E7EB]" />
            <span>Idle</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded bg-[#EEF2FF] border border-[#C7D2FE]" />
            <span>Low</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded bg-[#818CF8]" />
            <span>Medium</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded bg-[#4F46E5]" />
            <span>Peak</span>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto pb-2">
        <div className="min-w-[640px] space-y-1">
          {/* Header Row: Hours */}
          <div className="flex items-center">
            <div className="w-12 text-xs font-semibold text-[#9CA3AF]" />
            <div className="flex-1 grid grid-cols-13 gap-1">
              {HOURS.map(h => (
                <div key={h} className="text-center text-xs font-medium text-[#9CA3AF]">
                  {h > 12 ? `${h - 12} PM` : h === 12 ? '12 PM' : `${h} AM`}
                </div>
              ))}
            </div>
          </div>

          {/* Grid Rows: Days */}
          {DAYS_OF_WEEK.map(day => (
            <div key={day.value} className="flex items-center">
              <div className="w-12 text-xs font-bold text-[#4B5563]">
                {day.label}
              </div>
              <div className="flex-1 grid grid-cols-13 gap-1">
                {HOURS.map(hour => {
                  const dayData = data[day.value] || {};
                  const count = dayData[hour] || 0;
                  return (
                    <div
                      key={hour}
                      className={cn(
                        "h-10 rounded-lg border flex flex-col items-center justify-center font-mono text-[10px] font-bold transition-all cursor-default select-none",
                        getCellColorClass(count)
                      )}
                      title={`${day.label} at ${hour}:00: ${count} orders`}
                    >
                      {count > 0 && <span>{count}</span>}
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

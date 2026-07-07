import React from 'react';
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts';
import { formatShortDate } from '../../utils/format';
import { chartTokens } from './shared/chartTheme';
import './shared/tntTooltip.css';
import { TNTTooltip } from './shared/tntTooltip';

interface DataPoint {
  date: string;
  count: number;
  label?: string;
}

interface OrdersLineChartProps {
  data: DataPoint[];
  title?: string;
}

export function OrdersLineChart({ data, title = 'Orders — Last 7 Days' }: OrdersLineChartProps) {
  const formattedData = data.map(d => ({
    ...d,
    label: formatShortDate(d.date),
  }));

  return (
    <div className="tnt-card h-full">
      <h3 className="text-base font-bold mb-4 tracking-tight text-[#111827]">{title}</h3>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={formattedData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="indigoGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={chartTokens.brand.indigo} stopOpacity={0.3} />
              <stop offset="95%" stopColor={chartTokens.brand.indigo} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray={chartTokens.grid.dasharray} stroke={chartTokens.grid.stroke} strokeOpacity={chartTokens.grid.strokeOpacity} />
          <XAxis dataKey="label" tick={{ fill: chartTokens.text.axis, fontSize: 12, fontWeight: 500 }} axisLine={{ stroke: chartTokens.grid.stroke, strokeOpacity: 0.3 }} tickLine={false} />
          <YAxis tick={{ fill: chartTokens.text.axis, fontSize: 12, fontWeight: 500 }} axisLine={{ stroke: chartTokens.grid.stroke, strokeOpacity: 0.3 }} tickLine={false} />
          <Tooltip content={<TNTTooltip />} />
          <Area
            type="monotone"
            dataKey="count"
            stroke={chartTokens.brand.indigo}
            strokeWidth={2.5}
            fill="url(#indigoGradient)"
            dot={{ fill: '#4F46E5', strokeWidth: 0, r: 3 }}
            activeDot={{ r: 5, fill: chartTokens.brand.indigo, stroke: '#6366F1', strokeWidth: 2 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
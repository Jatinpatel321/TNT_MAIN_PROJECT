import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

import { chartTokens } from './shared/chartTheme';
import './shared/tntTooltip.css';
import { TNTTooltip } from './shared/tntTooltip';

interface RevenueDataPoint {
  label: string;
  food: number;
  stationery: number;
}

interface RevenueBarChartProps {
  data: RevenueDataPoint[];
  title?: string;
}

export function RevenueBarChart({ data, title = 'Revenue by Category' }: RevenueBarChartProps) {
  return (
    <div className="tnt-card h-full">
      <h3 className="text-base font-bold text-[#111827] mb-4 tracking-tight">{title}</h3>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 0 }} barGap={4}>
          <CartesianGrid
            strokeDasharray={chartTokens.grid.dasharray}
            stroke={chartTokens.grid.stroke}
            strokeOpacity={chartTokens.grid.strokeOpacity}
          />
          <XAxis dataKey="label" tick={{ fill: chartTokens.text.axis, fontSize: 12, fontWeight: 500 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: chartTokens.text.axis, fontSize: 12, fontWeight: 500 }} axisLine={false} tickLine={false} />

          <Tooltip content={<TNTTooltip />} />

          <Legend wrapperStyle={{ fontSize: '12px', fontWeight: 500, color: '#4B5563', paddingTop: '8px' }} />

          <Bar dataKey="food" name="Food" fill={chartTokens.brand.indigo} radius={[6, 6, 0, 0]} maxBarSize={32} />
          <Bar
            dataKey="stationery"
            name="Stationery"
            fill={chartTokens.brand.teal}
            radius={[6, 6, 0, 0]}
            maxBarSize={32}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
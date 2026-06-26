import React from 'react';
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';

import { chartTokens } from './shared/chartTheme';
import './shared/tntTooltip.css';
import { TNTTooltip } from './shared/tntTooltip';


interface PieDataPoint {
  name: string;
  value: number;
  color?: string;
}

interface VendorPieChartProps {
  data: PieDataPoint[];
  title?: string;
}

const COLORS = ['#E85D24', '#8B5CF6', '#14B8A6', '#3B82F6', '#EC4899'];



export function VendorPieChart({ data, title = 'Vendor Distribution' }: VendorPieChartProps) {
  return (
    <div className="tnt-card h-full">
      <h3 className="text-sm font-semibold text-[#F1F0FF] mb-4">{title}</h3>
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={55}
            outerRadius={80}
            paddingAngle={4}
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.color || COLORS[index % COLORS.length]}
                stroke="transparent"
              />
            ))}
          </Pie>
          <Tooltip content={<TNTTooltip />} />

          <Legend
            wrapperStyle={{ fontSize: '11px', color: '#9B9BC4' }}
            iconType="circle"
            iconSize={8}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

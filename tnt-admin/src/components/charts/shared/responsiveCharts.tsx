import React from 'react';

/**
 * Shared responsive sizing wrapper for Recharts.
 * Keeps charts consistent across pages.
 */
export function ChartContainer({
  children,
  height = 200,
}: {
  children: React.ReactNode;
  height?: number;
}) {
  return (
    <div className="w-full h-full">
      {/** Consumers should place their <ResponsiveContainer/> inside */}
      <div style={{ width: '100%', height }}>{children}</div>
    </div>
  );
}


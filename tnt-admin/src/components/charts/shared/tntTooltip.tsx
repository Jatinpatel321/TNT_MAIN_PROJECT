import React from 'react';
import type { TooltipProps } from 'recharts';
import { chartTokens } from './chartTheme';

type AnyPayload = Array<any>;

export function TNTTooltip({ active, payload, label }: TooltipProps<number, string> & { payload?: AnyPayload; label?: string }) {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div className="tnt-chart-tooltip">
      {label ? <p className="tnt-chart-tooltip__title">{label}</p> : null}
      {payload.map((entry: any, idx: number) => {
        const name = entry?.name ?? entry?.dataKey ?? `Series ${idx + 1}`;
        const value = entry?.value;
        const color = entry?.stroke ?? entry?.color ?? entry?.fill;

        return (
          <div key={`${name}-${idx}`} className="tnt-chart-tooltip__row">
            <span className="tnt-chart-tooltip__dot" style={{ backgroundColor: color || chartTokens.brand.orange }} />
            <span className="tnt-chart-tooltip__name">{name}:</span>
            <span className="tnt-chart-tooltip__value">
              {typeof value === 'number' ? value.toLocaleString('en-IN') : String(value)}
            </span>
          </div>
        );
      })}
    </div>
  );
}


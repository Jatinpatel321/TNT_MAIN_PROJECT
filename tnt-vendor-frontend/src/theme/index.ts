// ─── TNT Vendor Design System (Legacy Compatibility Layer) ──────────
// Re-exports from the new premium design system for backward compatibility
// All new code should import directly from '../design-system'

import colors from '../design-system/tokens/colors';
import typography from '../design-system/tokens/typography';
import spacing, { borderRadius } from '../design-system/tokens/spacing';
import shadows from '../design-system/tokens/shadows';

export { colors as Colors };
export { typography as Typography };
export { spacing as Spacing, borderRadius as BorderRadius };
export { shadows as Shadows };

// Status color/label helpers
export const getStatusColor = (status: string): string => {
  const map: Record<string, string> = {
    placed: colors.statusPlaced,
    pending: colors.statusPlaced,
    confirmed: colors.statusConfirmed,
    preparing: colors.statusPreparing,
    ready: colors.statusReady,
    ready_for_pickup: colors.statusReady,
    completed: colors.statusCompleted,
    picked: colors.statusPicked,
    cancelled: colors.statusCancelled,
  };
  return map[status.toLowerCase()] || colors.textMuted;
};

export const getStatusLabel = (status: string): string => {
  const map: Record<string, string> = {
    placed: 'Placed',
    pending: 'Pending',
    confirmed: 'Confirmed',
    preparing: 'Preparing',
    ready: 'Ready',
    ready_for_pickup: 'Ready',
    completed: 'Completed',
    picked: 'Picked Up',
    cancelled: 'Cancelled',
  };
  return map[status.toLowerCase()] || status;
};

export const getStatusIcon = (status: string): string => {
  const map: Record<string, string> = {
    placed: '📋',
    pending: '⏳',
    confirmed: '✅',
    preparing: '👨‍🍳',
    ready: '🍽️',
    ready_for_pickup: '🍽️',
    completed: '✅',
    picked: '📦',
    cancelled: '❌',
  };
  return map[status.toLowerCase()] || '📌';
};

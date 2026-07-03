// ─── TNT Premium Design System — Spacing & Layout ───────────────────

const spacing = {
  micro: 2,
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  xxxl: 32,
  huge: 40,
  massive: 48,
  giant: 56,
  section: 64,
} as const;

export const borderRadius = {
  sm: 6,
  md: 10,
  lg: 14,
  xl: 20,
  xxl: 24,
  xxxl: 28,
  full: 9999,
} as const;

export const iconSize = {
  sm: 16,
  md: 20,
  lg: 24,
  xl: 32,
  xxl: 40,
  xxxl: 48,
} as const;

export const hitSlop = {
  top: 10,
  bottom: 10,
  left: 10,
  right: 10,
} as const;

export type SpacingKey = keyof typeof spacing;
export type RadiusKey = keyof typeof borderRadius;

export default spacing;


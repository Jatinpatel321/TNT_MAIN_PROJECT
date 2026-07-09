/**
 * Central colour system for the app.
 *
 * The light palette mirrors the design tokens already used across screens
 * (indigo #6C63FF primary on a cool-grey canvas) so light mode is visually
 * unchanged; the dark palette re-maps the same roles onto deep surfaces.
 */
export type ThemeMode = 'light' | 'dark';

export type AppPalette = {
  background: string;
  surface: string;
  surfaceAlt: string;
  text: string;
  subtext: string;
  muted: string;
  border: string;
  primary: string;
  primarySoft: string;
  onPrimary: string;
  accent: string;
  success: string;
  successSoft: string;
  warning: string;
  warningSoft: string;
  danger: string;
  dangerSoft: string;
  skeleton: string;
  overlay: string;
};

export const lightPalette: AppPalette = {
  background: '#F6F7FB',
  surface: '#FFFFFF',
  surfaceAlt: '#F9FAFB',
  text: '#111827',
  subtext: '#4B5563',
  muted: '#6B7280',
  border: '#E5E7EB',
  primary: '#6C63FF',
  primarySoft: '#F3F2FF',
  onPrimary: '#FFFFFF',
  accent: '#3B82F6',
  success: '#10B981',
  successSoft: '#ECFDF5',
  warning: '#F59E0B',
  warningSoft: '#FFFBEB',
  danger: '#EF4444',
  dangerSoft: '#FEF2F2',
  skeleton: '#E5E7EB',
  overlay: 'rgba(17, 24, 39, 0.45)',
};

export const darkPalette: AppPalette = {
  background: '#0F1117',
  surface: '#1A1D27',
  surfaceAlt: '#232734',
  text: '#F3F4F6',
  subtext: '#C3C7D1',
  muted: '#9CA3AF',
  border: '#2D3140',
  primary: '#8B85FF',
  primarySoft: 'rgba(108, 99, 255, 0.18)',
  onPrimary: '#FFFFFF',
  accent: '#60A5FA',
  success: '#34D399',
  successSoft: 'rgba(16, 185, 129, 0.15)',
  warning: '#FBBF24',
  warningSoft: 'rgba(245, 158, 11, 0.15)',
  danger: '#F87171',
  dangerSoft: 'rgba(239, 68, 68, 0.15)',
  skeleton: '#2D3140',
  overlay: 'rgba(0, 0, 0, 0.6)',
};

export function paletteFor(mode: ThemeMode): AppPalette {
  return mode === 'dark' ? darkPalette : lightPalette;
}

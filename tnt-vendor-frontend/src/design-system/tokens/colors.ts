// ─── TNT Premium Design System — Colors ─────────────────────────────
// Light theme only — luxury minimal palette

const colors = {
  // Primary Brand
  primary: '#635BFF',
  primaryDark: '#4F46E5',
  primaryLight: '#818CF8',
  primaryPale: '#EEF0FF',
  primaryFaded: '#E0E0FF',

  // Secondary
  secondary: '#8B5CF6',
  secondaryDark: '#7C3AED',
  secondaryLight: '#A78BFA',
  secondaryPale: '#F5F3FF',

  // Accent Gradients (used behind content)
  gradientPurple: '#8B5CF6',
  gradientBlue: '#6366F1',
  gradientIndigo: '#4F46E5',

  // Semantic Colors
  success: '#10B981',
  successPale: '#D1FAE5',
  successDark: '#059669',
  warning: '#F59E0B',
  warningPale: '#FEF3C7',
  warningDark: '#D97706',
  error: '#EF4444',
  errorPale: '#FEE2E2',
  errorDark: '#DC2626',
  info: '#3B82F6',
  infoPale: '#DBEAFE',

  // Backgrounds
  bg: '#F7F8FC',
  bgCard: '#FFFFFF',
  bgSecondary: '#F1F5F9',
  bgTertiary: '#E8ECF4',
  bgOverlay: 'rgba(0, 0, 0, 0.3)',

  // Glass Effects
  glassWhite: 'rgba(255, 255, 255, 0.7)',
  glassBorder: 'rgba(255, 255, 255, 0.2)',
  glassShadow: 'rgba(99, 91, 255, 0.08)',

  // Borders
  border: '#E8ECF0',
  borderLight: '#F1F3F5',
  borderDark: '#D0D5DD',

  // Text
  textPrimary: '#0A0A1A',
  textSecondary: '#4A4A6A',
  textMuted: '#9A9AB0',
  textInverse: '#FFFFFF',
  textLink: '#635BFF',

  // Shadows
  shadowSm: 'rgba(99, 91, 255, 0.06)',
  shadowMd: 'rgba(99, 91, 255, 0.08)',
  shadowLg: 'rgba(99, 91, 255, 0.12)',
  shadowXl: 'rgba(99, 91, 255, 0.16)',

  // Status Colors (Orders)
  statusPlaced: '#8B5CF6',
  statusConfirmed: '#3B82F6',
  statusPreparing: '#F59E0B',
  statusReady: '#10B981',
  statusCompleted: '#059669',
  statusCancelled: '#EF4444',
  statusPicked: '#6B7280',
  statusDelay: '#EF4444',

  // Order Type Badges
  badgeFaculty: '#8B5CF6',
  badgeGroup: '#F59E0B',
  badgeStationery: '#3B82F6',
  badgePriority: '#EF4444',

  // AI Features
  aiPrimary: '#635BFF',
  aiSecondary: '#8B5CF6',
  aiSuccess: '#10B981',
  aiWarning: '#F59E0B',
  aiDanger: '#EF4444',
  aiInfo: '#3B82F6',
} as const;

export type ColorKey = keyof typeof colors;
export default colors;


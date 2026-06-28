// ─── TNT Vendor Design System ──────────────────────────────────────────
// A bold, premium design language for the TNT Vendor Portal

export const Colors = {
  // Primary palette
  primary: '#059669',       // Emerald-600
  primaryDark: '#047857',   // Emerald-700
  primaryLight: '#10B981',  // Emerald-500
  primaryPale: '#D1FAE5',   // Emerald-100
  primaryFaded: '#A7F3D0',  // Emerald-200

  // Secondary palette
  secondary: '#6366F1',     // Indigo-500
  secondaryDark: '#4F46E5', // Indigo-600
  secondaryLight: '#818CF8', // Indigo-400
  secondaryPale: '#E0E7FF',  // Indigo-100

  // Accent
  accent: '#F59E0B',        // Amber-500
  accentDark: '#D97706',    // Amber-600
  accentPale: '#FEF3C7',    // Amber-100

  // Semantic
  success: '#10B981',
  successPale: '#D1FAE5',
  warning: '#F59E0B',
  warningPale: '#FEF3C7',
  error: '#EF4444',
  errorPale: '#FEE2E2',
  info: '#3B82F6',
  infoPale: '#DBEAFE',

  // Neutrals
  white: '#FFFFFF',
  bg: '#F0FDF4',           // Very light green tinted bg
  bgCard: '#FFFFFF',
  bgSecondary: '#F9FAFB',
  bgTertiary: '#F3F5F9',

  border: '#E5E7EB',
  borderLight: '#F3F4F6',
  borderDark: '#D1D5DB',

  // Text
  textPrimary: '#111827',
  textSecondary: '#4B5563',
  textMuted: '#9CA3AF',
  textInverse: '#FFFFFF',
  textLink: '#059669',

  // Shadows
  shadow: '#000000',
  shadowLight: 'rgba(0,0,0,0.05)',
  shadowMedium: 'rgba(0,0,0,0.08)',
  shadowHeavy: 'rgba(0,0,0,0.12)',

  // Status colors for orders
  statusPlaced: '#8B5CF6',
  statusConfirmed: '#3B82F6',
  statusPreparing: '#F59E0B',
  statusReady: '#10B981',
  statusCompleted: '#059669',
  statusCancelled: '#EF4444',
  statusPicked: '#6B7280',
} as const;

export const Typography = {
  // Font sizes
  h1: 28,
  h2: 24,
  h3: 20,
  h4: 18,
  body: 16,
  bodySmall: 14,
  caption: 12,
  tiny: 10,

  // Font weights
  bold: '700' as const,
  semibold: '600' as const,
  medium: '500' as const,
  regular: '400' as const,
  light: '300' as const,

  // Line heights
  leadingTight: 1.2,
  leadingNormal: 1.5,
  leadingRelaxed: 1.75,
} as const;

export const Spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  xxxl: 32,
  huge: 48,
} as const;

export const BorderRadius = {
  sm: 6,
  md: 10,
  lg: 14,
  xl: 20,
  full: 9999,
} as const;

export const Shadows = {
  card: {
    shadowColor: Colors.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 3,
  },
  cardHover: {
    shadowColor: Colors.shadow,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.12,
    shadowRadius: 12,
    elevation: 5,
  },
  button: {
    shadowColor: Colors.shadow,
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.15,
    shadowRadius: 6,
    elevation: 4,
  },
  header: {
    shadowColor: Colors.shadow,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 12,
    elevation: 8,
  },
  modal: {
    shadowColor: Colors.shadow,
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.2,
    shadowRadius: 24,
    elevation: 12,
  },
} as const;

// Status color mapping
export const getStatusColor = (status: string): string => {
  const map: Record<string, string> = {
    placed: Colors.statusPlaced,
    pending: Colors.statusPlaced,
    confirmed: Colors.statusConfirmed,
    preparing: Colors.statusPreparing,
    ready: Colors.statusReady,
    ready_for_pickup: Colors.statusReady,
    completed: Colors.statusCompleted,
    picked: Colors.statusPicked,
    cancelled: Colors.statusCancelled,
  };
  return map[status.toLowerCase()] || Colors.textMuted;
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

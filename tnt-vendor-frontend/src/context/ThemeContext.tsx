// ─── Theme Context ────────────────────────────────────────────────
// Light / Dark / System theme switching, persisted to SecureStore.
// All screens access colors through useTheme().colors — never import
// the static colors.ts object directly in themed components.

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useMemo,
} from 'react';
import { useColorScheme } from 'react-native';
import * as SecureStore from 'expo-secure-store';

// ── Type extracted loosely so dark palette can use different strings ──
export type ColorPalette = {
  primary: string;
  primaryDark: string;
  primaryLight: string;
  primaryPale: string;
  primaryFaded: string;
  secondary: string;
  secondaryDark: string;
  secondaryLight: string;
  secondaryPale: string;
  gradientPurple: string;
  gradientBlue: string;
  gradientIndigo: string;
  success: string;
  successPale: string;
  successDark: string;
  warning: string;
  warningPale: string;
  warningDark: string;
  error: string;
  errorPale: string;
  errorDark: string;
  info: string;
  infoPale: string;
  bg: string;
  bgCard: string;
  bgSecondary: string;
  bgTertiary: string;
  bgOverlay: string;
  glassWhite: string;
  glassBorder: string;
  glassShadow: string;
  border: string;
  borderLight: string;
  borderDark: string;
  textPrimary: string;
  textSecondary: string;
  textMuted: string;
  textInverse: string;
  textLink: string;
  shadowSm: string;
  shadowMd: string;
  shadowLg: string;
  shadowXl: string;
  statusPlaced: string;
  statusConfirmed: string;
  statusPreparing: string;
  statusReady: string;
  statusCompleted: string;
  statusCancelled: string;
  statusPicked: string;
  statusDelay: string;
  badgeFaculty: string;
  badgeGroup: string;
  badgeStationery: string;
  badgePriority: string;
  aiPrimary: string;
  aiSecondary: string;
  aiSuccess: string;
  aiWarning: string;
  aiDanger: string;
  aiInfo: string;
};

const lightPalette: ColorPalette = {
  primary: '#635BFF',
  primaryDark: '#4F46E5',
  primaryLight: '#818CF8',
  primaryPale: '#EEF0FF',
  primaryFaded: '#E0E0FF',
  secondary: '#8B5CF6',
  secondaryDark: '#7C3AED',
  secondaryLight: '#A78BFA',
  secondaryPale: '#F5F3FF',
  gradientPurple: '#8B5CF6',
  gradientBlue: '#6366F1',
  gradientIndigo: '#4F46E5',
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
  bg: '#F7F8FC',
  bgCard: '#FFFFFF',
  bgSecondary: '#F1F5F9',
  bgTertiary: '#E8ECF4',
  bgOverlay: 'rgba(0, 0, 0, 0.3)',
  glassWhite: 'rgba(255, 255, 255, 0.7)',
  glassBorder: 'rgba(255, 255, 255, 0.2)',
  glassShadow: 'rgba(99, 91, 255, 0.08)',
  border: '#E8ECF0',
  borderLight: '#F1F3F5',
  borderDark: '#D0D5DD',
  textPrimary: '#0A0A1A',
  textSecondary: '#4A4A6A',
  textMuted: '#9A9AB0',
  textInverse: '#FFFFFF',
  textLink: '#635BFF',
  shadowSm: 'rgba(99, 91, 255, 0.06)',
  shadowMd: 'rgba(99, 91, 255, 0.08)',
  shadowLg: 'rgba(99, 91, 255, 0.12)',
  shadowXl: 'rgba(99, 91, 255, 0.16)',
  statusPlaced: '#8B5CF6',
  statusConfirmed: '#3B82F6',
  statusPreparing: '#F59E0B',
  statusReady: '#10B981',
  statusCompleted: '#059669',
  statusCancelled: '#EF4444',
  statusPicked: '#6B7280',
  statusDelay: '#EF4444',
  badgeFaculty: '#8B5CF6',
  badgeGroup: '#F59E0B',
  badgeStationery: '#3B82F6',
  badgePriority: '#EF4444',
  aiPrimary: '#635BFF',
  aiSecondary: '#8B5CF6',
  aiSuccess: '#10B981',
  aiWarning: '#F59E0B',
  aiDanger: '#EF4444',
  aiInfo: '#3B82F6',
} ;

const darkPalette: ColorPalette = {
  primary: '#818CF8',
  primaryDark: '#6366F1',
  primaryLight: '#A5B4FC',
  primaryPale: '#1E1B4B',
  primaryFaded: '#1E1B4B',
  secondary: '#A78BFA',
  secondaryDark: '#8B5CF6',
  secondaryLight: '#C4B5FD',
  secondaryPale: '#1D1340',
  gradientPurple: '#A78BFA',
  gradientBlue: '#818CF8',
  gradientIndigo: '#6366F1',
  success: '#34D399',
  successPale: '#064E3B',
  successDark: '#10B981',
  warning: '#FCD34D',
  warningPale: '#451A03',
  warningDark: '#F59E0B',
  error: '#FC8181',
  errorPale: '#450A0A',
  errorDark: '#EF4444',
  info: '#60A5FA',
  infoPale: '#1E3A5F',
  bg: '#0F0F1A',
  bgCard: '#1A1A2E',
  bgSecondary: '#16213E',
  bgTertiary: '#1A1A2E',
  bgOverlay: 'rgba(0, 0, 0, 0.6)',
  glassWhite: 'rgba(255, 255, 255, 0.06)',
  glassBorder: 'rgba(255, 255, 255, 0.08)',
  glassShadow: 'rgba(0, 0, 0, 0.3)',
  border: '#2D2D4E',
  borderLight: '#1E1E38',
  borderDark: '#3D3D6E',
  textPrimary: '#E8E8F0',
  textSecondary: '#A0A0C0',
  textMuted: '#606080',
  textInverse: '#0A0A1A',
  textLink: '#818CF8',
  shadowSm: 'rgba(0, 0, 0, 0.2)',
  shadowMd: 'rgba(0, 0, 0, 0.3)',
  shadowLg: 'rgba(0, 0, 0, 0.4)',
  shadowXl: 'rgba(0, 0, 0, 0.5)',
  statusPlaced: '#A78BFA',
  statusConfirmed: '#60A5FA',
  statusPreparing: '#FCD34D',
  statusReady: '#34D399',
  statusCompleted: '#10B981',
  statusCancelled: '#FC8181',
  statusPicked: '#9CA3AF',
  statusDelay: '#FC8181',
  badgeFaculty: '#A78BFA',
  badgeGroup: '#FCD34D',
  badgeStationery: '#60A5FA',
  badgePriority: '#FC8181',
  aiPrimary: '#818CF8',
  aiSecondary: '#A78BFA',
  aiSuccess: '#34D399',
  aiWarning: '#FCD34D',
  aiDanger: '#FC8181',
  aiInfo: '#60A5FA',
};

export type ThemeMode = 'light' | 'dark' | 'system';
// ColorPalette is defined at the top of this file


// ── Context Definition ───────────────────────────────────────────

interface ThemeContextType {
  mode: ThemeMode;
  isDark: boolean;
  colors: ColorPalette;
  setMode: (mode: ThemeMode) => void;
}

const ThemeContext = createContext<ThemeContextType>({
  mode: 'system',
  isDark: false,
  colors: lightPalette,
  setMode: () => {},
});

const STORAGE_KEY = 'tnt_theme_mode';

// ── Provider ────────────────────────────────────────────────────

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const systemScheme = useColorScheme(); // 'light' | 'dark' | null
  const [mode, setModeState] = useState<ThemeMode>('system');

  // Load persisted preference on mount
  useEffect(() => {
    SecureStore.getItemAsync(STORAGE_KEY).then(stored => {
      if (stored === 'light' || stored === 'dark' || stored === 'system') {
        setModeState(stored);
      }
    }).catch(() => {/* ignore */});
  }, []);

  const setMode = useCallback((newMode: ThemeMode) => {
    setModeState(newMode);
    SecureStore.setItemAsync(STORAGE_KEY, newMode).catch(() => {/* ignore */});
  }, []);

  const isDark = useMemo(() => {
    if (mode === 'dark') return true;
    if (mode === 'light') return false;
    return systemScheme === 'dark';
  }, [mode, systemScheme]);

  const colors = isDark ? darkPalette : lightPalette;

  return (
    <ThemeContext.Provider value={{ mode, isDark, colors, setMode }}>
      {children}
    </ThemeContext.Provider>
  );
};

// ── Hook ────────────────────────────────────────────────────────

export const useTheme = () => useContext(ThemeContext);

// Re-export palettes for direct access where needed
export { lightPalette, darkPalette };

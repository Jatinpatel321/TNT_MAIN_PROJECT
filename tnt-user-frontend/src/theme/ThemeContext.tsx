import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import { getItem, setItem } from '../utils/storage';
import { AppPalette, ThemeMode, paletteFor } from './theme';

const THEME_STORAGE_KEY = 'tnt.theme_mode';

type ThemeState = {
  mode: ThemeMode;
  isDark: boolean;
  colors: AppPalette;
  setMode: (mode: ThemeMode) => void;
  toggle: () => void;
};

const ThemeContext = createContext<ThemeState | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>('light');

  useEffect(() => {
    (async () => {
      const stored = await getItem(THEME_STORAGE_KEY);
      if (stored === 'dark' || stored === 'light') {
        setModeState(stored);
      }
    })();
  }, []);

  const setMode = useCallback((next: ThemeMode) => {
    setModeState(next);
    // Fire-and-forget persistence; the UI must not wait on disk.
    setItem(THEME_STORAGE_KEY, next).catch(() => {});
  }, []);

  const toggle = useCallback(() => {
    setModeState((prev) => {
      const next = prev === 'dark' ? 'light' : 'dark';
      setItem(THEME_STORAGE_KEY, next).catch(() => {});
      return next;
    });
  }, []);

  const value = useMemo<ThemeState>(
    () => ({
      mode,
      isDark: mode === 'dark',
      colors: paletteFor(mode),
      setMode,
      toggle,
    }),
    [mode, setMode, toggle],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useAppTheme(): ThemeState {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error('useAppTheme must be used within a ThemeProvider');
  }
  return ctx;
}

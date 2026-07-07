import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import { STORAGE_KEYS } from '../utils/constants';
import { getItem, removeItem, setItem } from '../utils/storage';
import { registerFCMToken } from '../services/pushNotificationService';
import type { User } from '../types/models';

type AuthState = {
  isBootstrapping: boolean;
  accessToken: string | null;
  user: User | null;
  setSession: (token: string, user: User) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const token = await getItem(STORAGE_KEYS.accessToken);
        const userJson = await getItem(STORAGE_KEYS.user);
        setAccessToken(token);
        setUser(userJson ? (JSON.parse(userJson) as User) : null);
      } finally {
        setIsBootstrapping(false);
      }
    })();
  }, []);

  const setSession = useCallback(async (token: string, u: User) => {
    await setItem(STORAGE_KEYS.accessToken, token);
    await setItem(STORAGE_KEYS.user, JSON.stringify(u));
    setAccessToken(token);
    setUser(u);
    // Register FCM token after successful login
    registerFCMToken();
  }, []);

  const logout = useCallback(async () => {
    await removeItem(STORAGE_KEYS.accessToken);
    await removeItem(STORAGE_KEYS.user);
    setAccessToken(null);
    setUser(null);
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      isBootstrapping,
      accessToken,
      user,
      setSession,
      logout,
    }),
    [isBootstrapping, accessToken, user, setSession, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

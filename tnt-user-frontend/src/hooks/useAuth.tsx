import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';

import { STORAGE_KEYS } from '../utils/constants';
import { getItem, removeItem, setItem } from '../utils/storage';
import { registerFCMToken } from '../services/pushNotificationService';
import { resetUnauthorizedState, setUnauthorizedHandler } from '../services/apiClient';
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
    // A fresh sign-in re-arms the 401 auto-logout for the next expiry.
    resetUnauthorizedState();
    // Register FCM token after successful login
    registerFCMToken();
  }, []);

  const logout = useCallback(async () => {
    await removeItem(STORAGE_KEYS.accessToken);
    await removeItem(STORAGE_KEYS.user);
    setAccessToken(null);
    setUser(null);
  }, []);

  // Sign out automatically when the backend rejects our token (expired session
  // or rotated signing key). This clears the dead token and flips RootNavigator
  // to the login stack instead of looping failed requests forever.
  const loggedOutRef = useRef(false);
  useEffect(() => {
    setUnauthorizedHandler(() => {
      if (loggedOutRef.current) return;
      loggedOutRef.current = true;
      logout().finally(() => {
        loggedOutRef.current = false;
      });
    });
    return () => setUnauthorizedHandler(null);
  }, [logout]);

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

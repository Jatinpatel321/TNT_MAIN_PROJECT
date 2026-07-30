// ─── Secure Auth Context ───────────────────────────────────────────
// JWT stored in expo-secure-store (encrypted), with token expiry
// validation and automatic logout on 401 via event bus.

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import * as SecureStore from 'expo-secure-store';
import { STORAGE_KEYS } from '../config/api';
import apiClient from '../services/apiClient';
import { onAuthEvent, AUTH_EVENTS } from '../services/apiClient';
import { registerFCMToken } from '../services/pushRegistrationService';

// Matches backend VendorProfileResponse + derived fields from JWT
interface User {
  vendor_id: number;
  vendor_name: string;
  category: string | null;
  owner_id: number;
  owner_name: string | null;
  /** Normalized from backend's owner_phone field */
  phone: string | null;
  status: string;
  /** Derived from JWT: 'vendor_owner' | 'vendor_staff' */
  role: string;
  /** Staff-only: staff record id from JWT staff_id claim */
  staff_id: number | null;
  /** Staff permissions dict — loaded from login response or secure store */
  staff_permissions?: Record<string, boolean> | null;
}

// Payload embedded in the JWT
interface JwtPayload {
  sub?: string;
  exp?: number;
  iat?: number;
  role?: string;
  staff_id?: number | null;
  [key: string]: unknown;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (
    identifier: string,
    password: string,
    accountType?: 'owner' | 'staff',
  ) => Promise<void>;
  logout: () => Promise<void>;
  isLoading: boolean;
  isTokenExpired: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// ── JWT helpers ────────────────────────────────────────────────────

/** Safe base64 decode for React Native (no native atob in Hermes). */
function base64Decode(input: string): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=';
  let output = '';
  let buffer = 0;
  let bits = 0;

  for (let i = 0; i < input.length; i++) {
    const char = input[i];
    if (char === '=') break;
    const idx = chars.indexOf(char);
    if (idx === -1) continue;
    buffer = (buffer << 6) | idx;
    bits += 6;
    if (bits >= 8) {
      bits -= 8;
      output += String.fromCharCode((buffer >> bits) & 0xff);
    }
  }
  return output;
}

/** Decode a JWT without verifying the signature (client-side only). */
function decodeJwt(token: string): JwtPayload | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const payload = parts[1];
    // Base64url → standard base64 → decode
    const decoded = base64Decode(payload.replace(/-/g, '+').replace(/_/g, '/'));
    return JSON.parse(decoded) as JwtPayload;
  } catch {
    return null;
  }
}

/** Check if a JWT is expired (based on its `exp` claim). */
function isJwtExpired(token: string): boolean {
  const payload = decodeJwt(token);
  if (!payload || !payload.exp) return false; // Can't verify — assume valid
  const expMs = payload.exp * 1000; // JWT exp is in seconds
  return Date.now() >= expMs;
}

// ── Provider ───────────────────────────────────────────────────────

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isTokenExpired, setIsTokenExpired] = useState(false);

  // Load stored auth on mount
  useEffect(() => {
    loadStoredAuth();
  }, []);

  // Listen for forced logout from 401 interceptor
  useEffect(() => {
    const unsubscribe = onAuthEvent(AUTH_EVENTS.LOGOUT, () => {
      performLogout();
    });
    return unsubscribe;
  }, []);

  const loadStoredAuth = async () => {
    try {
      const storedToken = await SecureStore.getItemAsync(STORAGE_KEYS.AUTH_TOKEN);
      const storedUser = await SecureStore.getItemAsync(STORAGE_KEYS.USER_DATA);

      if (!storedToken || !storedUser) {
        setIsLoading(false);
        return;
      }

      // Check token expiry before accepting
      if (isJwtExpired(storedToken)) {
        console.warn('[Auth] Stored token is expired — clearing session');
        await SecureStore.deleteItemAsync(STORAGE_KEYS.AUTH_TOKEN);
        await SecureStore.deleteItemAsync(STORAGE_KEYS.USER_DATA);
        setIsTokenExpired(true);
        setIsLoading(false);
        return;
      }

      setToken(storedToken);
      setUser(JSON.parse(storedUser));
    } catch (error) {
      console.error('[Auth] Failed to load stored auth:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (
    identifier: string,
    password: string,
    accountType: 'owner' | 'staff' = 'owner',
  ) => {
    const ownerPayload = { vendor_id: Number(identifier), password };
    const staffPayload = { staff_phone: identifier, password };
    const loginPayload = accountType === 'staff' ? staffPayload : ownerPayload;

    if (accountType === 'owner' && !Number.isFinite(ownerPayload.vendor_id)) {
      throw new Error('Vendor ID must be a number');
    }

    let response;
    try {
      response = await apiClient.post('/v1/vendors/auth/login', loginPayload);
    } catch (error: any) {
      const backendMessage = error?.response?.data?.detail;
      throw new Error(backendMessage || error?.message || 'Login failed');
    }
    const { access_token, vendor } = response.data;

    if (!access_token || !vendor) {
      throw new Error('Invalid server response — missing token or vendor data');
    }

    // Check token expiry at login time
    const payload = decodeJwt(access_token);
    if (isJwtExpired(access_token)) {
      throw new Error('Server returned an expired token');
    }

    // Build normalized user — role comes from JWT, phone from owner_phone
    const userData: User = {
      vendor_id: vendor.vendor_id,
      vendor_name: vendor.vendor_name,
      category: vendor.category ?? null,
      owner_id: vendor.owner_id,
      owner_name: vendor.owner_name ?? null,
      phone: vendor.owner_phone ?? null,
      status: vendor.status ?? 'active',
      role: payload?.role ?? 'vendor_owner',
      staff_id: payload?.staff_id ?? null,
      // Include staff permissions if the vendor object has them (staff login response includes permissions dict)
      staff_permissions: vendor.staff_permissions ?? null,
    };

    // Store securely
    await SecureStore.setItemAsync(STORAGE_KEYS.AUTH_TOKEN, access_token);
    await SecureStore.setItemAsync(STORAGE_KEYS.USER_DATA, JSON.stringify(userData));

    setToken(access_token);
    setUser(userData);
    setIsTokenExpired(false);

    // Register push notifications in background
    registerFCMToken();
  };

  const performLogout = useCallback(async () => {
    try {
      // Notify backend to invalidate refresh token
      const currentToken = token;
      if (currentToken) {
        await apiClient.post(`/v1/vendors/auth/logout`, null, {
          headers: { Authorization: `Bearer ${currentToken}` },
        }).catch(() => {
          // Ignore network errors — still clear local state
        });
      }
    } catch {
      // Ignore
    }

    setUser(null);
    setToken(null);
    setIsTokenExpired(false);
    try {
      await SecureStore.deleteItemAsync(STORAGE_KEYS.AUTH_TOKEN);
      await SecureStore.deleteItemAsync(STORAGE_KEYS.USER_DATA);
    } catch {
      // Ignore cleanup errors
    }
  }, [token]);

  const logout = useCallback(async () => {
    await performLogout();
  }, [performLogout]);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        login,
        logout,
        isLoading,
        isTokenExpired,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

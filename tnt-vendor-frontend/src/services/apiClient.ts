// ─── Secure Axios Client ───────────────────────────────────────────
// Centralized HTTP client with automatic JWT injection, 401 handling,
// and request timeout. All API services should import this instead of
// raw axios.

import axios, {
  AxiosError,
  AxiosInstance,
  InternalAxiosRequestConfig,
} from 'axios';
import * as SecureStore from 'expo-secure-store';
import { API_BASE_URL, REQUEST_TIMEOUT, STORAGE_KEYS } from '../config/api';

// ── Auth event bus for cross-module communication ──────────────────
// Simple subscriber-based pattern (no Node events dependency needed)

type AuthEventHandler = () => void;
const authListeners: { event: string; handler: AuthEventHandler }[] = [];

export function onAuthEvent(event: string, handler: AuthEventHandler) {
  authListeners.push({ event, handler });
  return () => {
    const idx = authListeners.findIndex((l) => l.event === event && l.handler === handler);
    if (idx >= 0) authListeners.splice(idx, 1);
  };
}

function emitAuthEvent(event: string) {
  authListeners
    .filter((l) => l.event === event)
    .forEach((l) => l.handler());
}

export const AUTH_EVENTS = {
  LOGOUT: 'auth:logout',
  TOKEN_EXPIRED: 'auth:token_expired',
} as const;

// ── Singleton axios instance ───────────────────────────────────────

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: REQUEST_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

// ── Request interceptor: attach JWT ────────────────────────────────

apiClient.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    try {
      const token = await SecureStore.getItemAsync(STORAGE_KEYS.AUTH_TOKEN);
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch {
      // SecureStore read failed — proceed without token
    }
    return config;
  },
  (error: AxiosError) => Promise.reject(error),
);

// ── Response interceptor: handle 401 globally ──────────────────────

let isLoggingOut = false;

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    if (error.response?.status === 401 && !isLoggingOut) {
      isLoggingOut = true;

      // Token expired or invalid — clear stored auth
      try {
        await SecureStore.deleteItemAsync(STORAGE_KEYS.AUTH_TOKEN);
        await SecureStore.deleteItemAsync(STORAGE_KEYS.USER_DATA);
      } catch {
        // Ignore cleanup errors
      }

      // Notify AuthContext to force logout
      emitAuthEvent(AUTH_EVENTS.LOGOUT);

      isLoggingOut = false;
    }
    return Promise.reject(error);
  },
);

export { apiClient };
export default apiClient;

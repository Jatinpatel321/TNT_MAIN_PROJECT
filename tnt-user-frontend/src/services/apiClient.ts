import axios, { AxiosError } from 'axios';

import { API_BASE_URL, API_PREFIX, STORAGE_KEYS } from '../utils/constants';
import { getItem } from '../utils/storage';

declare const __DEV__: boolean;

export type ApiError = {
  status: number;
  message: string;
  detail?: unknown;
};

export const apiClient = axios.create({
  baseURL: `${API_BASE_URL}${API_PREFIX}`,
  timeout: 20000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Helper to append Authorization when a token exists.
export async function authHeaders(): Promise<Record<string, string>> {
  const token = await getItem(STORAGE_KEYS.accessToken);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ── Session-expiry bridge ────────────────────────────────────────────────────
// The AuthProvider registers a handler here so the client can sign the user out
// the moment the backend rejects their token (expired / rotated secret). Without
// this, an expired session just fails every request forever, spamming the
// console with 401s and leaving the UI stuck on stale/blank data.
let onUnauthorized: (() => void) | null = null;
let unauthorizedHandled = false;

export function setUnauthorizedHandler(fn: (() => void) | null): void {
  onUnauthorized = fn;
}

/** Re-arm the 401 handler after a fresh, successful sign-in. */
export function resetUnauthorizedState(): void {
  unauthorizedHandled = false;
}

apiClient.interceptors.request.use(async (config) => {
  const token = await getItem(STORAGE_KEYS.accessToken);
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error)) {
      const status = error.response?.status ?? 0;
      const hadAuth = Boolean(
        (error.config?.headers as Record<string, unknown> | undefined)?.Authorization,
      );

      // 401 is an expected auth state, not an error to log on repeat. The first
      // one that carried a token clears the session (→ login); every other 401
      // (already handling, or fired with no token during/after logout) is
      // swallowed silently so the console never fills with 401 spam.
      if (status === 401) {
        if (hadAuth && !unauthorizedHandled) {
          unauthorizedHandled = true;
          if (__DEV__) {
            console.warn('[apiClient] session expired — signing out');
          }
          onUnauthorized?.();
        }
        return Promise.reject(error);
      }

      // Genuine errors (5xx, network, 4xx other than auth): one concise dev line.
      if (__DEV__) {
        const method = error.config?.method?.toUpperCase() ?? '';
        const url = `${error.config?.baseURL ?? ''}${error.config?.url ?? ''}`;
        if (status === 0 || error.message === 'Network Error') {
          console.warn(
            `[apiClient] network error → ${method} ${url} (backend reachable? adb reverse tcp:8000 tcp:8000)`,
          );
        } else {
          console.warn(`[apiClient] ${method} ${url} → ${status}`);
        }
      }
    } else if (__DEV__) {
      console.warn('[apiClient] request failed', error);
    }
    return Promise.reject(error);
  }
);

export function toApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const axErr = error as AxiosError<any>;
    const status = axErr.response?.status ?? 0;
    const data = axErr.response?.data;
    const message =
      (typeof data?.detail === 'string' && data.detail) ||
      (typeof data?.message === 'string' && data.message) ||
      axErr.message ||
      'Request failed';

    return { status, message, detail: data };
  }

  if (error instanceof Error) {
    return { status: 0, message: error.message };
  }

  return { status: 0, message: 'Unknown error' };
}

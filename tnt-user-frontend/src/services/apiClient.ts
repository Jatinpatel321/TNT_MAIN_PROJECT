import axios, { AxiosError } from 'axios';

import { API_BASE_URL, API_PREFIX, STORAGE_KEYS } from '../utils/constants';
import { getItem } from '../utils/storage';

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
      const method = error.config?.method?.toUpperCase() ?? "";
      const baseURL = error.config?.baseURL ?? "";
      const url = error.config?.url ?? "";
      const detail = error.response?.data ?? error.message;
      console.error("[apiClient] request failed", {
        status,
        method,
        url: `${baseURL}${url}`,
        detail,
      });
    } else {
      console.error("[apiClient] request failed", error);
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

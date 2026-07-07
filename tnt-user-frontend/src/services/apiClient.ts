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

  // Log every outgoing request for debugging
  console.log(
    `[apiClient] ${config.method?.toUpperCase() ?? "?"} ${config.baseURL ?? ""}${config.url ?? ""}`,
    config.data ? { body: config.data } : ""
  );

  return config;
});

apiClient.interceptors.response.use(
  (response) => {
    console.log(
      `[apiClient] ${response.config.method?.toUpperCase() ?? "?"} ${response.config.baseURL ?? ""}${response.config.url ?? ""} → ${response.status}`
    );
    return response;
  },
  (error) => {
    if (axios.isAxiosError(error)) {
      const status = error.response?.status ?? 0;
      const method = error.config?.method?.toUpperCase() ?? "";
      const baseURL = error.config?.baseURL ?? "";
      const url = error.config?.url ?? "";
      const requestBody = error.config?.data ?? "(none)";
      const detail = error.response?.data ?? error.message;

      // Enhanced error logging — includes full request URL, method, body, and response
      console.error(
        `[apiClient] REQUEST FAILED ${method} ${baseURL}${url}\n` +
        `  status : ${status}\n` +
        `  body   : ${typeof requestBody === "string" ? requestBody : JSON.stringify(requestBody)}\n` +
        `  detail : ${typeof detail === "string" ? detail : JSON.stringify(detail)}\n` +
        `  message: ${error.message}`
      );

      // Check for common network issues
      if (status === 0 || error.message === "Network Error") {
        console.error(
          `[apiClient] NETWORK ERROR — device cannot reach ${baseURL}${url}.\n` +
          `  • Physical device via USB: run "adb reverse tcp:8000 tcp:8000"\n` +
          `  • Change baseURL to http://localhost:8000\n` +
          `  • Or use Wi-Fi IP (same subnet): http://YOUR_LAN_IP:8000`
        );
      }
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

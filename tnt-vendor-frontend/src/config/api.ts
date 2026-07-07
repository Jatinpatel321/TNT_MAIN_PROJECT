// Centralized API configuration.
// Use localhost in development so adb reverse can tunnel requests from a physical device.
const DEV_HOST = 'localhost';
const DEV_PORT = '8000';

export const API_BASE_URL = __DEV__
  ? `http://${DEV_HOST}:${DEV_PORT}`
  : 'https://api.tnt-campus.com';

export const WS_BASE_URL = __DEV__
  ? `ws://${DEV_HOST}:${DEV_PORT}`
  : 'wss://api.tnt-campus.com';

// API version prefix
export const API_PREFIX = '/v1';

// Request timeout in milliseconds
export const REQUEST_TIMEOUT = 15000;

// Token storage keys
export const STORAGE_KEYS = {
  AUTH_TOKEN: 'vendor_auth_token',
  USER_DATA: 'vendor_user_data',
  FCM_TOKEN: 'fcm_token',
} as const;

export default {
  API_BASE_URL,
  WS_BASE_URL,
  API_PREFIX,
  REQUEST_TIMEOUT,
  STORAGE_KEYS,
};

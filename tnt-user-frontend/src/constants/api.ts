// ─── TNT API Configuration ────────────────────────────────────────────────────
//
// HOW TO CHOOSE YOUR URL:
//
//  ① PHYSICAL USB DEVICE (adb reverse — recommended):
//       Run: adb reverse tcp:8000 tcp:8000
//       Use: API_BASE_URL = 'http://localhost:8000'    ← DEFAULT (already set)
//
//  ② ANDROID EMULATOR (AVD):
//       Use: API_BASE_URL = 'http://10.0.2.2:8000'
//       (10.0.2.2 is the AVD loopback alias for the host machine)
//
//  ③ WIFI / LAN (no USB, same network):
//       Run: ipconfig  →  find your IPv4 address (e.g. 192.168.1.100)
//       Use: API_BASE_URL = 'http://192.168.1.100:8000'
//
declare const __DEV__: boolean;

// ─── TNT API Configuration ────────────────────────────────────────────────────
//
// In release / production builds, NEVER connect to device localhost.
// Use process.env.API_BASE_URL or production HTTPS endpoint.
// In local development (__DEV__ === true), use local developer gateway.
// ─────────────────────────────────────────────────────────────────────────────

const PROD_API_BASE_URL = 'https://api.tnt.edu';
const DEV_API_BASE_URL = 'http://localhost:8000';

const isDev = typeof __DEV__ !== 'undefined' ? __DEV__ : process.env.NODE_ENV !== 'production';

export const API_BASE_URL =
  process.env.API_BASE_URL ||
  (isDev ? DEV_API_BASE_URL : PROD_API_BASE_URL);

export const API_PREFIX = '/v1';

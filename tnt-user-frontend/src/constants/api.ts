// Central API configuration.
// ─────────────────────────────────────────────────────────────────────────
// USB DEBUGGING (physical device, adb reverse):
//   adb reverse tcp:8000 tcp:8000
//   export const API_BASE_URL = 'http://localhost:8000';
//
// WIFI (device and PC on same LAN):
//   Find your PC LAN IP via `ipconfig` (e.g. 192.168.x.x).
//   export const API_BASE_URL = 'http://192.168.x.x:8000';
//
// EMULATOR:
//   export const API_BASE_URL = 'http://10.0.2.2:8000';
// ─────────────────────────────────────────────────────────────────────────
export const API_BASE_URL = 'http://localhost:8000';
export const API_PREFIX = '/v1';

// Central API configuration
// Dev over USB: use localhost so adb reverse routes traffic to the host machine (port 8000 reversed above).
// For real Wi-Fi testing, swap this to your LAN IP (e.g., http://10.209.21.52:8000) and ensure phone + PC share the network.
// Use LAN IP so the Android device can reach the backend over Wi-Fi/USB.
export const API_BASE_URL = 'http://localhost:8000';
export const API_PREFIX = '/v1';

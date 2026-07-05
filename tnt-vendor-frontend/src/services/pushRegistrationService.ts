import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import apiClient from './apiClient';
import { STORAGE_KEYS } from '../config/api';

export async function registerFCMToken(): Promise<void> {
  try {
    // Dynamic import to avoid hard crash if package not installed
    let messaging: any;
    try {
      const messagingModule = require('@react-native-firebase/messaging');
      messaging = messagingModule.default;
    } catch {
      console.warn('[FCM] @react-native-firebase/messaging not installed — skipping registration');
      return;
    }

    // Request permission (required on iOS, optional on Android)
    const authStatus = await messaging.requestPermission();
    const enabled =
      authStatus === messaging.AuthorizationStatus.AUTHORIZED ||
      authStatus === messaging.AuthorizationStatus.PROVISIONAL;

    if (!enabled) {
      console.log('[FCM] Permission not granted');
      return;
    }

    // Get FCM token
    const fcmToken = await messaging.getToken();
    if (!fcmToken) {
      console.warn('[FCM] No token returned');
      return;
    }

    // Store token locally
    await SecureStore.setItemAsync(STORAGE_KEYS.FCM_TOKEN, fcmToken);

    // Register token with backend
    await apiClient.post(`/v1/vendors/notifications/register-device`, {
      device_token: fcmToken,
      platform: Platform.OS,
    });

    // Listen for token refresh
    messaging.onTokenRefresh(async (newToken: string) => {
      try {
        await SecureStore.setItemAsync(STORAGE_KEYS.FCM_TOKEN, newToken);
        await apiClient.post(`/v1/vendors/notifications/register-device`, {
          device_token: newToken,
          platform: Platform.OS,
        });
      } catch {
        console.warn('[FCM] Token refresh handler failed');
      }
    });

    // Handle foreground messages (optional — can show in-app notification)
    messaging.onMessage(async (remoteMessage: any) => {
      console.log('[FCM] Foreground message:', remoteMessage);
    });

    console.log('[FCM] Registration complete');
  } catch (error) {
    console.warn('[FCM] Registration failed:', error);
  }
}

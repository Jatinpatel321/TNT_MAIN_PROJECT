/**
 * Push notification registration hook.
 * 
 * Registers the device token with the backend on login and app foreground.
 * Uses the existing `POST /v1/profile/device-token` endpoint and FCM infrastructure.
 */
import {useEffect, useRef, useCallback} from 'react';
import {Platform, AppState, AppStateStatus} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import {apiClient, authHeaders} from '../services/apiClient';

const STORAGE_KEY_TOKEN_REGISTERED = '@tnt/push_registered';

/**
 * Request push notification permissions and get device token.
 * 
 * On Android, uses Firebase Cloud Messaging (FCM) via react-native-firebase.
 * On iOS, requests APNs permission and gets FCM token.
 * Falls back gracefully if Firebase SDK is not configured.
 */
async function getDeviceToken(): Promise<string | null> {
  try {
    // Try Firebase Cloud Messaging
    const messaging = require('@react-native-firebase/messaging').default;
    const authStatus = await messaging().requestPermission();
    const enabled =
      authStatus === messaging.AuthorizationStatus.AUTHORIZED ||
      authStatus === messaging.AuthorizationStatus.PROVISIONAL;

    if (enabled) {
      const token = await messaging().getToken();
      return token || null;
    }
    return null;
  } catch (e) {
    // Firebase SDK not available — return null (push won't work but app won't crash)
    console.log('Push registration unavailable:', (e as Error).message);
    return null;
  }
}

/**
 * Register the device token with the backend.
 */
async function registerToken(token: string): Promise<boolean> {
  try {
    await apiClient.post(
      '/v1/profile/device-token',
      {
        device_token: token,
        platform: Platform.OS,
      },
      {headers: await authHeaders()},
    );
    await AsyncStorage.setItem(STORAGE_KEY_TOKEN_REGISTERED, 'true');
    return true;
  } catch (e) {
    console.warn('Failed to register device token:', (e as Error).message);
    return false;
  }
}

export function usePushRegistration() {
  const isRegisteredRef = useRef(false);

  const register = useCallback(async () => {
    if (isRegisteredRef.current) return;

    const already = await AsyncStorage.getItem(STORAGE_KEY_TOKEN_REGISTERED);
    if (already === 'true') {
      // Already registered in a previous session — re-register to refresh token
      // but don't block on it
    }

    const token = await getDeviceToken();
    if (token) {
      const success = await registerToken(token);
      if (success) {
        isRegisteredRef.current = true;
      }
    }
  }, []);

  useEffect(() => {
    // Register on mount (app start / login)
    register();

    // Handle app state changes — re-register on foreground
    const subscription = AppState.addEventListener(
      'change',
      (state: AppStateStatus) => {
        if (state === 'active') {
          register();
        }
      },
    );

    return () => {
      subscription.remove();
    };
  }, [register]);

  return {register};
}
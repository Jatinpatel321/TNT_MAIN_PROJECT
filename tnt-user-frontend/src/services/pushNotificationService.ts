import { Platform, PermissionsAndroid } from 'react-native';
import { apiClient } from './apiClient';

export async function registerFCMToken(): Promise<void> {
  try {
    // Dynamic import so the app doesn't crash if Firebase isn't set up yet
    const messaging = (await import('@react-native-firebase/messaging')).default;

    // Request permission on iOS
    const authStatus = await messaging().requestPermission();
    const enabled =
      authStatus === messaging.AuthorizationStatus.AUTHORIZED ||
      authStatus === messaging.AuthorizationStatus.PROVISIONAL;

    if (!enabled) {
      console.log('Push notification permission denied');
      return;
    }

    // Request permission on Android 13+
    if (Platform.OS === 'android') {
      await PermissionsAndroid.request(
        PermissionsAndroid.PERMISSIONS.POST_NOTIFICATIONS,
      );
    }

    const token = await messaging().getToken();
    if (!token) return;

    await apiClient.post('/v1/profile/device-token', {
      device_token: token,
      push_enabled: true,
    });
    console.log('FCM token registered successfully');
  } catch (err) {
    // Non-fatal — push notifications are a nice-to-have, not a blocker
    console.warn('FCM token registration failed:', err);
  }
}

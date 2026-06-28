import { Platform, PermissionsAndroid } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8001';

export async function registerFCMToken(): Promise<void> {
  // Skip Firebase registration in dev — dummy credentials won't work
  try {
    const { default: firebase } = await import('@react-native-firebase/app');
    // Check if Firebase has a real appId (not dummy)
    const app = firebase.app();
    if (!app.options.appId || app.options.appId === 'dummy-app-id') {
      console.log('FCM: Skipping registration — no real Firebase project configured');
      return;
    }
  } catch {
    console.log('FCM: Firebase not configured — skipping');
    return;
  }

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

    const authToken = await AsyncStorage.getItem('vendor_token');
    if (!authToken) {
      console.warn('No auth token — skipping FCM registration');
      return;
    }

    await axios.post(
      `${API_BASE_URL}/v1/profile/device-token`,
      { device_token: token, push_enabled: true },
      { headers: { Authorization: `Bearer ${authToken}` } },
    );
    console.log('FCM token registered successfully');
  } catch (err) {
    // Non-fatal — push notifications are a nice-to-have, not a blocker
    console.warn('FCM token registration failed:', err);
  }
}

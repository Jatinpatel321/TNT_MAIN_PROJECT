// ─── TNT Vendor App Entry ──────────────────────────────────────────
// Firebase configuration is loaded from environment variables.
// In production, use react-native-config or expo-constants to inject.

import 'react-native-gesture-handler';
import { AppRegistry, Platform } from 'react-native';
import App from './App';
import { API_BASE_URL } from './src/config/api';

// Lazy Firebase initialization — only if real config is available.
// During development with Expo, Firebase is configured via app.json
// or expo-constants.
const initFirebase = async () => {
  try {
    // Using dynamic import to avoid crash if Firebase is not configured
    const firebase = require('@react-native-firebase/app').default;

    // In development, Firebase might already be configured via Expo.
    // Only initialize if no apps exist and we have real config values.
    if (!firebase.apps.length) {
      // Attempt to load from environment (react-native-config / expo-constants)
      let config = {};

      try {
        // Try expo-constants first
        const Constants = require('expo-constants').default;
        const manifestConfig = Constants.expoConfig?.extra?.firebase;
        if (manifestConfig?.apiKey && manifestConfig?.projectId) {
          config = manifestConfig;
        }
      } catch {
        // expo-constants not available — try react-native-config
      }

      if (!config.apiKey) {
        try {
          const RNConfig = require('react-native-config').default;
          if (RNConfig.FIREBASE_API_KEY) {
            config = {
              apiKey: RNConfig.FIREBASE_API_KEY,
              appId: RNConfig.FIREBASE_APP_ID,
              projectId: RNConfig.FIREBASE_PROJECT_ID,
              databaseURL: RNConfig.FIREBASE_DATABASE_URL,
              messagingSenderId: RNConfig.FIREBASE_SENDER_ID,
              storageBucket: RNConfig.FIREBASE_STORAGE_BUCKET,
            };
          }
        } catch {
          // react-native-config not available
        }
      }

      // Only initialize Firebase if we have real config values
      if (config.apiKey && config.apiKey !== 'dummy-api-key') {
        firebase.initializeApp(config);
        console.log('[Firebase] Initialized with environment config');
      } else {
        console.log('[Firebase] Skipping initialization — no real config available');
      }
    }
  } catch {
    // Firebase module not installed — skip initialization
    console.log('[Firebase] Module not available');
  }
};

// Initialize Firebase asynchronously
initFirebase();

AppRegistry.registerComponent('TNTVendorApp', () => App);

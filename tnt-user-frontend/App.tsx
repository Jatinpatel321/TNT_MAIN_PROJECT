import React, { useEffect } from 'react';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { MD3LightTheme, PaperProvider } from 'react-native-paper';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { AuthProvider } from './src/hooks/useAuth';
import RootNavigator from './src/navigation/RootNavigator';
import { CartProvider } from './src/context/CartContext';
import { registerFCMToken } from './src/services/pushNotificationService';

const theme = {
  ...MD3LightTheme,
  roundness: 16,
};

export default function App() {
  useEffect(() => {
    // Firebase FCM is optional — silently skip if native module is missing
    let unsubscribe: (() => void) | undefined;
    (async () => {
      try {
        const messaging = (await import('@react-native-firebase/messaging')).default;
        const unsub = messaging().onTokenRefresh(() => {
          registerFCMToken();
        });
        unsubscribe = unsub;
      } catch {
        console.warn('Firebase not available natively — push notifications disabled');
      }
    })();
    return () => {
      if (unsubscribe) unsubscribe();
    };
  }, []);

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <PaperProvider theme={theme}>
          <AuthProvider>
            <CartProvider>
              <RootNavigator />
            </CartProvider>
          </AuthProvider>
        </PaperProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}

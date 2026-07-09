import React, { useEffect } from 'react';
import { StatusBar } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { MD3DarkTheme, MD3LightTheme, PaperProvider } from 'react-native-paper';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { AuthProvider } from './src/hooks/useAuth';
import RootNavigator from './src/navigation/RootNavigator';
import { CartProvider } from './src/context/CartContext';
import { registerFCMToken } from './src/services/pushNotificationService';
import { ThemeProvider, useAppTheme } from './src/theme/ThemeContext';

function ThemedApp() {
  const { isDark, colors } = useAppTheme();

  const paperTheme = React.useMemo(() => {
    const base = isDark ? MD3DarkTheme : MD3LightTheme;
    return {
      ...base,
      roundness: 16,
      colors: {
        ...base.colors,
        primary: colors.primary,
        background: colors.background,
        surface: colors.surface,
        onSurface: colors.text,
      },
    };
  }, [isDark, colors]);

  return (
    <PaperProvider theme={paperTheme}>
      <StatusBar
        barStyle={isDark ? 'light-content' : 'dark-content'}
        backgroundColor={colors.background}
      />
      <AuthProvider>
        <CartProvider>
          <RootNavigator />
        </CartProvider>
      </AuthProvider>
    </PaperProvider>
  );
}

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
        <ThemeProvider>
          <ThemedApp />
        </ThemeProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}

import React, { useEffect } from 'react';
import { ActivityIndicator, Image, StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';
import { NativeStackScreenProps } from '@react-navigation/native-stack';

import type { AuthStackParamList } from '../../types/navigation';
import { useAuth } from '../../hooks/useAuth';
import { LOGO } from '../../assets';

type Props = NativeStackScreenProps<AuthStackParamList, 'Splash'>;

export function SplashScreen({ navigation }: Props) {
  const { isBootstrapping, accessToken } = useAuth();

  useEffect(() => {
    if (isBootstrapping) return;
    const timer = setTimeout(() => {
      if (accessToken) return; // Root navigator will transition to AppTabs when token exists.
      navigation.replace('Login');
    }, 2000);
    return () => clearTimeout(timer);
  }, [isBootstrapping, accessToken, navigation]);

  return (
    <View style={styles.container}>
      <Image source={LOGO} style={styles.logo} resizeMode="contain" />
      <Text variant="headlineMedium" style={styles.title}>Tap N Take</Text>
      <Text style={styles.sub}>Smart Campus Scheduling</Text>
      <ActivityIndicator size="large" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
    backgroundColor: '#FFFFFF',
  },
  logo: {
    width: 160,
    height: 80,
    marginBottom: 12,
  },
  title: {
    fontWeight: '800',
    marginBottom: 6,
  },
  sub: {
    marginBottom: 16,
    opacity: 0.7,
  },
});

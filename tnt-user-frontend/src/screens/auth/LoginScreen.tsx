import React, { useMemo, useState } from 'react';
import { Alert, Image, StyleSheet, View } from 'react-native';
import { Text, TextInput } from 'react-native-paper';
import { NativeStackScreenProps } from '@react-navigation/native-stack';

import type { AuthStackParamList } from '../../types/navigation';
import { Screen } from '../../components/Screen';
import { GradientButton } from '../../components/GradientButton';
import { login, sendOtp } from '../../services/authService';
import { toApiError } from '../../services/apiClient';
import { useAuth } from '../../hooks/useAuth';
import { LOGO } from '../../assets';

type Props = NativeStackScreenProps<AuthStackParamList, 'Login'>;

export function LoginScreen({ navigation }: Props) {
  const { setSession } = useAuth();

  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState('');
  const [step, setStep] = useState<'phone' | 'otp'>('phone');
  const [loading, setLoading] = useState(false);

  const phoneClean = useMemo(() => phone.trim(), [phone]);

  const onSendOtp = async () => {
    try {
      setLoading(true);
      const res = await sendOtp(phoneClean);
      setStep('otp');
      if (res.otp) {
        Alert.alert('OTP sent (dev)', `Use code ${res.otp}.`);
      } else {
        Alert.alert('OTP sent', 'Check your SMS for the code.');
      }
    } catch (e) {
      Alert.alert('OTP failed', toApiError(e).message);
    } finally {
      setLoading(false);
    }
  };

  const onVerify = async () => {
    try {
      setLoading(true);
      const res = await login(phoneClean, otp.trim());
      await setSession(res.data.access_token, res.data.user);
      // Root navigator will switch to the authenticated stack automatically.
    } catch (e) {
      Alert.alert('Login failed', toApiError(e).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Screen>
      <View style={styles.logoWrap}>
        <Image source={LOGO} style={styles.logo} resizeMode="contain" />
        <Text style={styles.logoText}>Welcome Back</Text>
      </View>

      <View style={styles.header}>
        <Text variant="headlineMedium" style={styles.title}>Login</Text>
        <Text style={styles.sub}>OTP login using your registered phone.</Text>
      </View>

      <View style={styles.card}>
        <TextInput
          label="Phone"
          value={phone}
          onChangeText={setPhone}
          keyboardType="phone-pad"
          autoCapitalize="none"
          mode="outlined"
          style={styles.input}
          disabled={loading || step === 'otp'}
        />

        {step === 'otp' && (
          <TextInput
            label="OTP"
            value={otp}
            onChangeText={setOtp}
            keyboardType="number-pad"
            autoCapitalize="none"
            mode="outlined"
            style={styles.input}
            disabled={loading}
          />
        )}

        {step === 'phone' ? (
          <GradientButton label={loading ? 'Sending…' : 'Send OTP'} onPress={onSendOtp} disabled={loading || !phoneClean} />
        ) : (
          <GradientButton label={loading ? 'Verifying…' : 'Verify & Continue'} onPress={onVerify} disabled={loading || !otp.trim()} />
        )}

        <Text style={styles.hint}>
          New here? <Text style={styles.link} onPress={() => navigation.navigate('Signup')}>Create an account</Text>
        </Text>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    paddingTop: 18,
    paddingBottom: 10,
  },
  logoWrap: {
    alignItems: 'center',
    marginTop: 40,
    marginBottom: 12,
  },
  logo: {
    width: 120,
    height: 60,
  },
  logoText: {
    marginTop: 6,
    fontSize: 16,
    fontWeight: '800',
  },
  title: {
    fontWeight: '900',
  },
  sub: {
    opacity: 0.7,
    marginTop: 4,
  },
  card: {
    borderRadius: 18,
    padding: 14,
    backgroundColor: '#fff',
    shadowColor: '#000',
    shadowOpacity: 0.08,
    shadowOffset: { width: 0, height: 4 },
    shadowRadius: 12,
    elevation: 4,
    gap: 12,
  },
  input: {
    backgroundColor: 'transparent',
  },
  hint: {
    opacity: 0.75,
    marginTop: 4,
  },
  link: {
    fontWeight: '800',
  },
});

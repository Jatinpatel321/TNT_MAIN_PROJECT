import React, { useMemo, useState } from 'react';
import { Alert, StyleSheet, View } from 'react-native';
import { Text, TextInput } from 'react-native-paper';

import { Screen } from '../components/Screen';
import { GradientButton } from '../components/GradientButton';
import { sendOtp, verifyOtp } from '../services/authService';
import { toApiError } from '../services/apiClient';
import { useAuth } from '../hooks/useAuth';

export function LoginScreen() {
  const { setSession } = useAuth();

  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState('');
  const [step, setStep] = useState<'phone' | 'otp'>('phone');
  const [loading, setLoading] = useState(false);

  const phoneClean = useMemo(() => phone.trim(), [phone]);

  const onSendOtp = async () => {
    try {
      setLoading(true);
      await sendOtp(phoneClean);
      setStep('otp');
    } catch (e) {
      const err = toApiError(e);
      Alert.alert('OTP failed', err.message);
    } finally {
      setLoading(false);
    }
  };

  const onVerify = async () => {
    try {
      setLoading(true);
      const res = await verifyOtp(phoneClean, otp.trim());
      await setSession(res.data.access_token, res.data.user);
    } catch (e) {
      const err = toApiError(e);
      Alert.alert('Login failed', err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Screen>
      <View style={styles.header}>
        <Text variant="headlineMedium" style={styles.title}>Sign in</Text>
        <Text style={styles.sub}>OTP login (JWT powered)</Text>
      </View>

      <View style={styles.form}>
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

        {step === 'otp' && (
          <Text style={styles.hint}>
            OTP sent to {phoneClean}. If you didn’t receive it, go back and resend.
          </Text>
        )}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    paddingTop: 24,
    paddingBottom: 8,
  },
  title: {
    fontWeight: '900',
  },
  sub: {
    opacity: 0.7,
    marginTop: 4,
  },
  form: {
    gap: 12,
  },
  input: {
    backgroundColor: 'transparent',
  },
  hint: {
    opacity: 0.7,
    marginTop: 8,
    lineHeight: 18,
  },
});

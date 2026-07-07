import React, { useState } from 'react';
import { Alert, StyleSheet, View } from 'react-native';
import { RadioButton, Text, TextInput } from 'react-native-paper';
import { NativeStackScreenProps } from '@react-navigation/native-stack';

import type { AuthStackParamList } from '../../types/navigation';
import { Screen } from '../../components/Screen';
import { GradientButton } from '../../components/GradientButton';
import { signup } from '../../services/authService';
import { toApiError } from '../../services/apiClient';

type Props = NativeStackScreenProps<AuthStackParamList, 'Signup'>;

export function SignupScreen({ navigation }: Props) {
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [universityId, setUniversityId] = useState('');
  const [role, setRole] = useState<'student' | 'faculty'>('student');
  const [loading, setLoading] = useState(false);

  const onSubmit = async () => {
    try {
      setLoading(true);
      await signup({
        phone: phone.trim(),
        name: name.trim(),
        role,
        university_id: universityId.trim() || null,
      });
      Alert.alert('Account created', 'OTP login is used to sign in.');
      navigation.navigate('Login');
    } catch (e) {
      Alert.alert('Signup failed', toApiError(e).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Screen>
      <View style={styles.header}>
        <Text variant="headlineMedium" style={styles.title}>Create account</Text>
        <Text style={styles.sub}>Students and faculty sign up with phone + role.</Text>
      </View>

      <View style={styles.card}>
        <TextInput label="Full name" value={name} onChangeText={setName} mode="outlined" style={styles.input} />
        <TextInput label="Phone" value={phone} onChangeText={setPhone} keyboardType="phone-pad" mode="outlined" style={styles.input} />
        <TextInput
          label="University ID (optional)"
          value={universityId}
          onChangeText={setUniversityId}
          mode="outlined"
          style={styles.input}
        />

        <View style={styles.radioRow}>
          <Text style={styles.radioLabel}>Role</Text>
          <RadioButton.Group onValueChange={(v) => setRole(v as 'student' | 'faculty')} value={role}>
            <View style={styles.radioOption}>
              <RadioButton value="student" />
              <Text>Student</Text>
            </View>
            <View style={styles.radioOption}>
              <RadioButton value="faculty" />
              <Text>Faculty</Text>
            </View>
          </RadioButton.Group>
        </View>

        <GradientButton label={loading ? 'Creating…' : 'Create Account'} onPress={onSubmit} disabled={loading || !name.trim() || !phone.trim()} />

        <Text style={styles.hint}>
          Already have an account? <Text style={styles.link} onPress={() => navigation.navigate('Login')}>Login</Text>
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
  radioRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  radioLabel: {
    fontWeight: '700',
  },
  radioOption: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 14,
  },
  hint: {
    opacity: 0.75,
    marginTop: 4,
  },
  link: {
    fontWeight: '800',
  },
});

import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  KeyboardAvoidingView,
  Platform,
  Animated,
  Dimensions,
  StatusBar,
} from 'react-native';
import { useAuth } from '../../context/AuthContext';
import { Colors, Typography, BorderRadius, Shadows } from '../../theme';

const { width } = Dimensions.get('window');
const LOGO_SIZE = width * 0.28;

export default function LoginScreen({ navigation }: any) {
  const [vendorId, setVendorId] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();

  // Animations
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(30)).current;
  const scaleAnim = useRef(new Animated.Value(0.8)).current;
  const formSlide = useRef(new Animated.Value(50)).current;
  const formFade = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 800,
        useNativeDriver: true,
      }),
      Animated.timing(slideAnim, {
        toValue: 0,
        duration: 600,
        useNativeDriver: true,
      }),
      Animated.spring(scaleAnim, {
        toValue: 1,
        friction: 6,
        tension: 40,
        useNativeDriver: true,
      }),
      Animated.sequence([
        Animated.delay(400),
        Animated.parallel([
          Animated.timing(formSlide, {
            toValue: 0,
            duration: 500,
            useNativeDriver: true,
          }),
          Animated.timing(formFade, {
            toValue: 1,
            duration: 500,
            useNativeDriver: true,
          }),
        ]),
      ]),
    ]).start();
  }, []);

  const handleLogin = async () => {
    if (!vendorId || !password) {
      Alert.alert('Error', 'Please enter vendor ID and password');
      return;
    }

    setLoading(true);
    try {
      await login(parseInt(vendorId), password);
      navigation.replace('Main');
    } catch (error) {
      Alert.alert('Login Failed', 'Invalid credentials');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={Colors.primaryDark} />

      {/* Decorative Background Elements */}
      <View style={styles.bgCircle1} />
      <View style={styles.bgCircle2} />
      <View style={styles.bgCircle3} />

      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.keyboardView}
      >
        {/* Header / Branding Section */}
        <Animated.View
          style={[
            styles.headerSection,
            {
              opacity: fadeAnim,
              transform: [{ translateY: slideAnim }],
            },
          ]}
        >
          {/* Logo */}
          <Animated.View
            style={[
              styles.logoContainer,
              { transform: [{ scale: scaleAnim }] },
            ]}
          >
            <View style={styles.logoInner}>
              <Text style={styles.logoEmoji}>🍽️</Text>
            </View>
          </Animated.View>

          <Text style={styles.brandName}>Tap N Take</Text>
          <Text style={styles.tagline}>Vendor Portal</Text>
          <Text style={styles.subtitle}>
            Manage your orders, menu, and analytics on the go
          </Text>
        </Animated.View>

        {/* Login Form */}
        <Animated.View
          style={[
            styles.formContainer,
            {
              opacity: formFade,
              transform: [{ translateY: formSlide }],
            },
          ]}
        >
          <Text style={styles.formTitle}>Welcome Back</Text>
          <Text style={styles.formSubtitle}>Sign in to your vendor account</Text>

          {/* Vendor ID Field */}
          <View style={styles.fieldGroup}>
            <Text style={styles.label}>Vendor ID</Text>
            <View style={styles.inputWrapper}>
              <Text style={styles.inputIcon}>🏪</Text>
              <TextInput
                style={styles.input}
                value={vendorId}
                onChangeText={setVendorId}
                placeholder="Enter your vendor ID"
                placeholderTextColor={Colors.textMuted}
                keyboardType="numeric"
                autoCapitalize="none"
              />
            </View>
          </View>

          {/* Password Field */}
          <View style={styles.fieldGroup}>
            <Text style={styles.label}>Password</Text>
            <View style={styles.inputWrapper}>
              <Text style={styles.inputIcon}>🔒</Text>
              <TextInput
                style={styles.input}
                value={password}
                onChangeText={setPassword}
                placeholder="Enter your password"
                placeholderTextColor={Colors.textMuted}
                secureTextEntry
                autoCapitalize="none"
              />
            </View>
          </View>

          {/* Login Button */}
          <TouchableOpacity
            style={[styles.loginButton, loading && styles.loginButtonDisabled]}
            onPress={handleLogin}
            disabled={loading}
            activeOpacity={0.85}
          >
            {loading ? (
              <View style={styles.loadingRow}>
                <View style={styles.loadingDot} />
                <Text style={styles.loginButtonText}>Signing in...</Text>
              </View>
            ) : (
              <Text style={styles.loginButtonText}>Sign In →</Text>
            )}
          </TouchableOpacity>

          {/* Footer */}
          <Text style={styles.footerText}>
            Powered by TNT Campus Solutions
          </Text>
        </Animated.View>
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.primaryDark,
  },
  keyboardView: {
    flex: 1,
    justifyContent: 'center',
  },
  // Decorative circles
  bgCircle1: {
    position: 'absolute',
    top: -100,
    right: -80,
    width: 300,
    height: 300,
    borderRadius: 150,
    backgroundColor: Colors.primary + '25',
  },
  bgCircle2: {
    position: 'absolute',
    top: 60,
    left: -60,
    width: 200,
    height: 200,
    borderRadius: 100,
    backgroundColor: Colors.primaryLight + '15',
  },
  bgCircle3: {
    position: 'absolute',
    bottom: 100,
    right: -40,
    width: 180,
    height: 180,
    borderRadius: 90,
    backgroundColor: Colors.primaryLight + '10',
  },

  // Header
  headerSection: {
    alignItems: 'center',
    paddingHorizontal: 40,
    marginBottom: 30,
  },
  logoContainer: {
    marginBottom: 16,
  },
  logoInner: {
    width: LOGO_SIZE,
    height: LOGO_SIZE,
    borderRadius: LOGO_SIZE / 2,
    backgroundColor: Colors.white + '20',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 3,
    borderColor: Colors.white + '40',
  },
  logoEmoji: {
    fontSize: LOGO_SIZE * 0.45,
  },
  brandName: {
    fontSize: 36,
    fontWeight: Typography.bold,
    color: Colors.textInverse,
    letterSpacing: 1,
  },
  tagline: {
    fontSize: Typography.h4,
    fontWeight: Typography.semibold,
    color: Colors.textInverse + 'E0',
    marginTop: 4,
    letterSpacing: 4,
    textTransform: 'uppercase',
  },
  subtitle: {
    fontSize: Typography.bodySmall,
    color: Colors.textInverse + '99',
    textAlign: 'center',
    marginTop: 8,
    lineHeight: 20,
    paddingHorizontal: 20,
  },

  // Form
  formContainer: {
    marginHorizontal: 24,
    backgroundColor: Colors.bgCard,
    borderRadius: BorderRadius.xl,
    padding: 28,
    ...Shadows.modal,
  },
  formTitle: {
    fontSize: Typography.h3,
    fontWeight: Typography.bold,
    color: Colors.textPrimary,
    marginBottom: 4,
  },
  formSubtitle: {
    fontSize: Typography.bodySmall,
    color: Colors.textMuted,
    marginBottom: 24,
  },

  // Fields
  fieldGroup: {
    marginBottom: 16,
  },
  label: {
    fontSize: Typography.bodySmall,
    fontWeight: Typography.semibold,
    color: Colors.textSecondary,
    marginBottom: 8,
  },
  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1.5,
    borderColor: Colors.border,
    borderRadius: BorderRadius.md,
    backgroundColor: Colors.bgSecondary,
    paddingHorizontal: 14,
  },
  inputIcon: {
    fontSize: 18,
    marginRight: 10,
  },
  input: {
    flex: 1,
    paddingVertical: 14,
    fontSize: Typography.body,
    color: Colors.textPrimary,
  },

  // Button
  loginButton: {
    backgroundColor: Colors.primary,
    borderRadius: BorderRadius.md,
    paddingVertical: 16,
    alignItems: 'center',
    marginTop: 8,
    ...Shadows.button,
  },
  loginButtonDisabled: {
    opacity: 0.7,
  },
  loginButtonText: {
    color: Colors.textInverse,
    fontSize: Typography.h4,
    fontWeight: Typography.bold,
  },
  loadingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  loadingDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: Colors.textInverse,
  },

  // Footer
  footerText: {
    fontSize: Typography.caption,
    color: Colors.textMuted,
    textAlign: 'center',
    marginTop: 20,
  },
});

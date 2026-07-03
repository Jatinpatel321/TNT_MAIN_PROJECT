// ─── Premium QR Scanner Screen ──────────────────────────────────
// Vendor-side pickup confirmation with premium design system

import React, {useCallback, useRef, useState} from 'react';
import {
  Alert,
  Animated,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
  Vibration,
} from 'react-native';
import {NativeStackScreenProps} from '@react-navigation/native-stack';
import {vendorApi} from '../../services/vendorApi';
import {colors, spacing} from '../../design-system';
import GlassCard from '../../design-system/components/GlassCard';
import Button from '../../design-system/components/Button';

type Props = NativeStackScreenProps<any, 'QRScanner'>;

export function QRScannerScreen({navigation}: Props) {
  const [scanning, setScanning] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [manualQrCode, setManualQrCode] = useState('');
  const [lastScanned, setLastScanned] = useState<string | null>(null);
  const scanLockRef = useRef(false);
  const fadeAnim = useRef(new Animated.Value(0)).current;

  React.useEffect(() => {
    Animated.timing(fadeAnim, {toValue: 1, duration: 400, useNativeDriver: true}).start();
  }, []);

  const handleConfirmPickup = useCallback(async (qrCode: string) => {
    if (!qrCode.trim()) { Alert.alert('Error', 'Enter or scan a QR code'); return; }
    if (scanLockRef.current) return;
    scanLockRef.current = true;
    try {
      setConfirming(true);
      await vendorApi.confirmPickup(qrCode.trim());
      Vibration.vibrate(200);
      Alert.alert('✅ Pickup Confirmed', 'Order has been marked as picked up.', [
        {text: 'OK', onPress: () => { scanLockRef.current = false; navigation.goBack(); }},
      ]);
    } catch (error: any) {
      Alert.alert('❌ Failed', error?.response?.data?.detail || error?.message || 'Pickup confirmation failed');
      scanLockRef.current = false;
    } finally {
      setConfirming(false);
    }
  }, [navigation]);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View style={styles.headerDeco1} /><View style={styles.headerDeco2} />
        <Text style={styles.headerTitle}>Scan QR Code</Text>
        <Text style={styles.headerSubtitle}>Scan student's QR code to confirm pickup</Text>
      </View>

      <Animated.View style={{flex: 1, opacity: fadeAnim}}>
        {/* Camera placeholder */}
        <GlassCard padding={0} borderRadius={20} style={{marginHorizontal: spacing.lg, marginTop: spacing.md, overflow: 'hidden'}}>
          <View style={styles.cameraPlaceholder}>
            <Text style={styles.cameraIcon}>📷</Text>
            <Text style={styles.placeholderTitle}>Camera Scanner</Text>
            <Text style={styles.placeholderHint}>Point camera at the student's QR code</Text>
            {scanning && (
              <View style={styles.scanningIndicator}>
                <View style={styles.scanningDot} />
                <Text style={styles.scanningText}>Scanning...</Text>
              </View>
            )}
          </View>
        </GlassCard>

        {/* Manual QR input */}
        <View style={styles.manualSection}>
          <Text style={styles.manualLabel}>Or enter QR code manually:</Text>
          <TextInput
            style={styles.manualInput}
            placeholder="Paste QR code here..."
            value={manualQrCode}
            onChangeText={setManualQrCode}
            autoCapitalize="none"
            autoCorrect={false}
          />
          <Button title={confirming ? 'Confirming...' : 'Confirm Pickup'} onPress={() => handleConfirmPickup(manualQrCode)} loading={confirming} variant="success" size="lg" fullWidth />
          <TouchableOpacity style={[styles.scanToggle, scanning && styles.scanToggleActive]} onPress={() => setScanning(prev => !prev)}>
            <Text style={[styles.scanToggleText, scanning && styles.scanToggleTextActive]}>
              {scanning ? '⏸ Pause Scanning' : '▶ Start Scanning'}
            </Text>
          </TouchableOpacity>
        </View>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: colors.bg},
  header: {
    backgroundColor: colors.primary, paddingTop: spacing.huge + 20, paddingBottom: spacing.xxl, paddingHorizontal: spacing.xl,
    borderBottomLeftRadius: 28, borderBottomRightRadius: 28, overflow: 'hidden',
  },
  headerDeco1: {position: 'absolute', top: -40, right: -30, width: 180, height: 180, borderRadius: 90, backgroundColor: 'rgba(255,255,255,0.08)'},
  headerDeco2: {position: 'absolute', bottom: -30, left: -60, width: 140, height: 140, borderRadius: 70, backgroundColor: 'rgba(255,255,255,0.05)'},
  headerTitle: {fontSize: 28, fontWeight: '700', color: colors.textInverse, letterSpacing: -0.3},
  headerSubtitle: {fontSize: 14, color: 'rgba(255,255,255,0.7)', marginTop: 4, fontWeight: '500'},
  cameraPlaceholder: {height: 220, backgroundColor: colors.textPrimary, justifyContent: 'center', alignItems: 'center', borderWidth: 2, borderColor: colors.borderDark, borderStyle: 'dashed', borderRadius: 20},
  cameraIcon: {fontSize: 48, marginBottom: 8},
  placeholderTitle: {fontSize: 16, fontWeight: '600', color: colors.textInverse},
  placeholderHint: {fontSize: 12, color: colors.textMuted, marginTop: 4},
  scanningIndicator: {flexDirection: 'row', alignItems: 'center', marginTop: 12},
  scanningDot: {width: 8, height: 8, borderRadius: 4, backgroundColor: colors.success, marginRight: 6},
  scanningText: {fontSize: 12, color: colors.success, fontWeight: '600'},
  manualSection: {padding: spacing.lg, gap: spacing.sm},
  manualLabel: {fontSize: 14, fontWeight: '600', color: colors.textSecondary},
  manualInput: {borderWidth: 1, borderColor: colors.border, borderRadius: 12, padding: 14, fontSize: 16, backgroundColor: colors.bgCard, color: colors.textPrimary},
  scanToggle: {backgroundColor: colors.bgSecondary, borderRadius: 12, paddingVertical: 14, alignItems: 'center', borderWidth: 1, borderColor: colors.border},
  scanToggleActive: {backgroundColor: colors.errorPale, borderColor: colors.error + '40'},
  scanToggleText: {fontSize: 14, fontWeight: '600', color: colors.textSecondary},
  scanToggleTextActive: {color: colors.error},
});

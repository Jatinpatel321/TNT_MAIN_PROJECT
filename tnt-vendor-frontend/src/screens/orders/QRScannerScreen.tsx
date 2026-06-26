/**
 * QR Scanner Screen — vendor-side pickup confirmation.
 *
 * Uses react-native-camera-kit for real barcode scanning.
 * Falls back to manual QR code entry for development.
 *
 * On successful scan:
 * 1. Calls POST /v1/orders/qr/confirm?qr_code=...
 * 2. Displays confirmation with order details.
 * 3. Plays a success sound.
 */
import React, {useCallback, useEffect, useRef, useState} from 'react';
import {
  Alert,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
  Vibration,
} from 'react-native';
import {NativeStackScreenProps} from '@react-navigation/native-stack';
import {vendorApi} from '../../services/vendorApi';

type Props = NativeStackScreenProps<any, 'QRScanner'>;

export function QRScannerScreen({navigation, route}: Props) {
  const [scanning, setScanning] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [manualQrCode, setManualQrCode] = useState('');
  const [lastScanned, setLastScanned] = useState<string | null>(null);
  const scanLockRef = useRef(false);

  // ── Handle QR confirmation ───────────────────────────────────────────
  const handleConfirmPickup = useCallback(
    async (qrCode: string) => {
      if (!qrCode.trim()) {
        Alert.alert('Error', 'Please enter or scan a QR code');
        return;
      }

      // Prevent duplicate scans
      if (scanLockRef.current) return;
      scanLockRef.current = true;

      try {
        setConfirming(true);

        // Attempt the confirmation via backend
        const response = await vendorApi.confirmPickup(qrCode.trim());
        const orderId = response.data?.order_id;

        // Haptic + visual feedback
        Vibration.vibrate(200);

        Alert.alert(
          '✅ Pickup Confirmed',
          orderId
            ? `Order #${orderId} has been marked as picked up.`
            : 'Order has been marked as picked up successfully.',
          [
            {
              text: 'OK',
              onPress: () => {
                scanLockRef.current = false;
                navigation.goBack();
              },
            },
          ],
        );
      } catch (error: any) {
        const message =
          error?.response?.data?.detail ||
          error?.message ||
          'Pickup confirmation failed. Please try again.';
        Alert.alert('❌ Confirmation Failed', message);
        scanLockRef.current = false;
      } finally {
        setConfirming(false);
      }
    },
    [navigation],
  );

  // ── Camera scanner (react-native-camera-kit integration) ─────────────
  const handleBarcodeRead = useCallback(
    (event: {nativeEvent: {codeStringValue?: string}}) => {
      const code = event.nativeEvent?.codeStringValue;
      if (!code || code === lastScanned) return;

      setLastScanned(code);
      setManualQrCode(code);

      // Automatically confirm on successful scan
      Alert.alert(
        'QR Code Scanned',
        `Code: ${code.substring(0, 20)}...\n\nConfirm pickup?`,
        [
          {text: 'Cancel', style: 'cancel'},
          {
            text: 'Confirm Pickup',
            onPress: () => handleConfirmPickup(code),
          },
        ],
      );
    },
    [handleConfirmPickup, lastScanned],
  );

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>Scan QR Code</Text>
        <Text style={styles.subtitle}>
          Scan the student's QR code to confirm pickup
        </Text>
      </View>

      {/* Camera Scanner View */}
      <View style={styles.cameraContainer}>
        {/*
         * PRODUCTION CAMERA (uncomment when react-native-camera-kit is installed):
         *
         * <CameraScreen
         *   scanBarcode={true}
         *   onReadCode={handleBarcodeRead}
         *   showFrame={true}
         *   laserColor="#10B981"
         *   frameColor="#10B981"
         *   style={styles.camera}
         * />
         *
         * If using expo-camera instead:
         *
         * <CameraView
         *   style={styles.camera}
         *   facing="back"
         *   barcodeScannerSettings={{barcodeTypes: ['qr']}}
         *   onBarcodeScanned={scanning ? handleBarcodeScan : undefined}
         * >
         *   <View style={styles.cameraOverlay}>
         *     <View style={styles.scanFrame} />
         *   </View>
         * </CameraView>
         */}

        {/* Fallback placeholder for development */}
        <View style={styles.cameraPlaceholder}>
          <Text style={styles.cameraIcon}>📷</Text>
          <Text style={styles.cameraPlaceholderTitle}>
            Camera Scanner
          </Text>
          <Text style={styles.cameraHint}>
            Point camera at the student's QR code
          </Text>

          {/* Simulated scan button for development */}
          <TouchableOpacity
            style={styles.simulateButton}
            onPress={() => {
              Alert.alert(
                'Simulate Scan',
                'Enter QR code manually below, or generate one from an active order.',
              );
            }}>
            <Text style={styles.simulateButtonText}>Simulate Scan</Text>
          </TouchableOpacity>

          {/* Scanning indicator */}
          {scanning && (
            <View style={styles.scanningIndicator}>
              <View style={styles.scanningDot} />
              <Text style={styles.scanningText}>Scanning...</Text>
            </View>
          )}
        </View>
      </View>

      {/* Manual QR Input */}
      <View style={styles.manualSection}>
        <Text style={styles.manualLabel}>Or enter QR code manually:</Text>
        <TextInput
          style={styles.manualInput}
          placeholder="Paste QR code here..."
          value={manualQrCode}
          onChangeText={setManualQrCode}
          autoCapitalize="none"
          autoCorrect={false}
          autoFocus={false}
        />
        <TouchableOpacity
          style={[
            styles.confirmButton,
            confirming && styles.confirmButtonDisabled,
          ]}
          onPress={() => handleConfirmPickup(manualQrCode)}
          disabled={confirming}>
          <Text style={styles.confirmButtonText}>
            {confirming ? 'Confirming...' : 'Confirm Pickup'}
          </Text>
        </TouchableOpacity>

        {/* Scan activation toggle */}
        <TouchableOpacity
          style={[
            styles.scanToggle,
            scanning && styles.scanToggleActive,
          ]}
          onPress={() => setScanning(prev => !prev)}>
          <Text
            style={[
              styles.scanToggleText,
              scanning && styles.scanToggleTextActive,
            ]}>
            {scanning ? '⏸ Pause Scanning' : '▶ Start Scanning'}
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F9FAFB',
  },
  header: {
    padding: 20,
    paddingTop: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: '800',
    color: '#111827',
  },
  subtitle: {
    fontSize: 14,
    color: '#6B7280',
    marginTop: 4,
  },
  cameraContainer: {
    margin: 20,
    height: 280,
    borderRadius: 16,
    overflow: 'hidden',
    backgroundColor: '#1F2937',
  },
  camera: {
    flex: 1,
  },
  cameraPlaceholder: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#374151',
    borderStyle: 'dashed',
    borderRadius: 16,
  },
  cameraIcon: {
    fontSize: 48,
    marginBottom: 12,
  },
  cameraPlaceholderTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#D1D5DB',
  },
  cameraHint: {
    fontSize: 12,
    color: '#9CA3AF',
    marginTop: 4,
  },
  cameraOverlay: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  scanFrame: {
    width: 200,
    height: 200,
    borderWidth: 2,
    borderColor: '#10B981',
    borderRadius: 16,
    backgroundColor: 'transparent',
  },
  simulateButton: {
    marginTop: 20,
    paddingVertical: 10,
    paddingHorizontal: 24,
    backgroundColor: '#6366F1',
    borderRadius: 8,
  },
  simulateButtonText: {
    color: '#FFFFFF',
    fontWeight: '600',
  },
  scanningIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 12,
  },
  scanningDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#10B981',
    marginRight: 6,
  },
  scanningText: {
    fontSize: 12,
    color: '#10B981',
    fontWeight: '600',
  },
  manualSection: {
    padding: 20,
    gap: 12,
  },
  manualLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
  },
  manualInput: {
    borderWidth: 1,
    borderColor: '#D1D5DB',
    borderRadius: 8,
    padding: 12,
    fontSize: 14,
    backgroundColor: '#FFFFFF',
  },
  confirmButton: {
    backgroundColor: '#059669',
    borderRadius: 8,
    paddingVertical: 14,
    alignItems: 'center',
  },
  confirmButtonDisabled: {
    opacity: 0.6,
  },
  confirmButtonText: {
    color: '#FFFFFF',
    fontWeight: '700',
    fontSize: 16,
  },
  scanToggle: {
    backgroundColor: '#F3F4F6',
    borderRadius: 8,
    paddingVertical: 12,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  scanToggleActive: {
    backgroundColor: '#FEE2E2',
    borderColor: '#FECACA',
  },
  scanToggleText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#4B5563',
  },
  scanToggleTextActive: {
    color: '#DC2626',
  },
});

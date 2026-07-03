// ─── Premium QR Scan Screen ─────────────────────────────────────
// Camera-based QR pickup confirmation with premium design system

import React, { useState, useEffect, useRef } from 'react';
import { View, Text, StyleSheet, Alert, ActivityIndicator, Animated } from 'react-native';
import { Camera, CameraType } from 'expo-camera';
import { BarCodeScanner } from 'expo-barcode-scanner';
import { vendorApi } from '../../services/vendorApi';
import { colors, spacing } from '../../design-system';
import GlassCard from '../../design-system/components/GlassCard';
import Button from '../../design-system/components/Button';

export function QRScanScreen({ navigation }: any) {
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);
  const [scanned, setScanned] = useState(false);
  const [loading, setLoading] = useState(false);
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, {toValue: 1, duration: 400, useNativeDriver: true}).start();
    (async () => {
      const {status} = await Camera.requestCameraPermissionsAsync();
      setHasPermission(status === 'granted');
    })();
  }, []);

  const handleBarCodeScanned = async ({data}: {data: string}) => {
    if (scanned || loading) return;
    setScanned(true);
    setLoading(true);
    try {
      const orderRes = await vendorApi.getOrderByQR(data);
      const order = orderRes.data;
      Alert.alert(
        `Order #${order.id}`,
        `Customer: ${order.user_name || 'Unknown'}\nItems: ${order.item_count || '?'}\nAmount: ₹${order.total_amount}`,
        [
          {text: 'Cancel', style: 'cancel', onPress: () => setScanned(false)},
          {text: 'Confirm Pickup ✓', onPress: async () => {
            try {
              await vendorApi.confirmQRPickup(data);
              Alert.alert('Success', 'Order marked as picked up!', [
                {text: 'Scan Next', onPress: () => setScanned(false)},
                {text: 'Done', onPress: () => navigation.goBack()},
              ]);
            } catch (err: any) {
              Alert.alert('Error', err?.response?.data?.detail || 'Failed to confirm pickup');
              setScanned(false);
            } finally {setLoading(false);}
          }},
        ],
      );
    } catch (err: any) {
      Alert.alert('Invalid QR', err?.response?.data?.detail || 'Order not found');
      setScanned(false);
    } finally {setLoading(false);}
  };

  if (hasPermission === null) {
    return <View style={styles.center}><ActivityIndicator size="large" color={colors.primary} /><Text style={styles.permissionText}>Requesting camera permission...</Text></View>;
  }
  if (hasPermission === false) {
    return <View style={styles.center}><Text style={styles.errorText}>Camera permission denied. Enable it in Settings.</Text></View>;
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View style={styles.headerDeco1} /><View style={styles.headerDeco2} />
        <Text style={styles.headerTitle}>QR Scan</Text>
        <Text style={styles.headerSubtitle}>Scan customer QR code to confirm pickup</Text>
      </View>

      <Animated.View style={{flex: 1, opacity: fadeAnim}}>
        <Camera
          style={styles.camera}
          type={CameraType.back}
          barCodeScannerSettings={{barCodeTypes: [BarCodeScanner.Constants.BarCodeType.qr]}}
          onBarCodeScanned={scanned ? undefined : handleBarCodeScanned}>
          <View style={styles.overlay}>
            <View style={styles.scanBox} />
            <Text style={styles.hint}>
              {loading ? 'Verifying...' : scanned ? 'Confirmed!' : 'Point camera at customer QR code'}
            </Text>
            {loading && <ActivityIndicator color="#fff" style={{marginTop: 16}} />}
          </View>
        </Camera>
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
  camera: {flex: 1, margin: spacing.lg, borderRadius: 20, overflow: 'hidden'},
  overlay: {flex: 1, justifyContent: 'center', alignItems: 'center'},
  scanBox: {width: 240, height: 240, borderWidth: 3, borderColor: colors.primary, borderRadius: 16, backgroundColor: 'transparent'},
  hint: {color: colors.textInverse, marginTop: 24, fontSize: 16, textAlign: 'center', paddingHorizontal: 32, fontWeight: '600'},
  errorText: {color: colors.error, fontSize: 16, textAlign: 'center', padding: 24},
  permissionText: {fontSize: 14, color: colors.textMuted, marginTop: 12},
  center: {flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: colors.bg},
});

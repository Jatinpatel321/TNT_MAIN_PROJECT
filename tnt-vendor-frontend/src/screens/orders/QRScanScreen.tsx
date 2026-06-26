import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, Alert, ActivityIndicator } from 'react-native';
import { Camera, CameraType } from 'expo-camera';
import { BarCodeScanner } from 'expo-barcode-scanner';
import { vendorApi } from '../../services/vendorApi';

export function QRScanScreen({ navigation }: any) {
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);
  const [scanned, setScanned] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    (async () => {
      const { status } = await Camera.requestCameraPermissionsAsync();
      setHasPermission(status === 'granted');
    })();
  }, []);

  const handleBarCodeScanned = async ({ data }: { data: string }) => {
    if (scanned || loading) return;
    setScanned(true);
    setLoading(true);

    try {
      // Step 1: Look up order by QR code
      const orderRes = await vendorApi.getOrderByQR(data);
      const order = orderRes.data;

      Alert.alert(
        `Order #${order.id}`,
        `Customer: ${order.user_name || 'Unknown'}\nItems: ${order.item_count || '?'}\nAmount: ₹${order.total_amount}`,
        [
          {
            text: 'Cancel',
            style: 'cancel',
            onPress: () => setScanned(false),
          },
          {
            text: 'Confirm Pickup ✓',
            onPress: async () => {
              try {
                await vendorApi.confirmQRPickup(data);
                Alert.alert('Success', 'Order marked as picked up!', [
                  { text: 'Scan Next', onPress: () => setScanned(false) },
                  { text: 'Done', onPress: () => navigation.goBack() },
                ]);
              } catch (err: any) {
                Alert.alert('Error', err?.response?.data?.detail || 'Failed to confirm pickup');
                setScanned(false);
              } finally {
                setLoading(false);
              }
            },
          },
        ],
      );
    } catch (err: any) {
      Alert.alert('Invalid QR', err?.response?.data?.detail || 'Order not found or QR is invalid');
      setScanned(false);
    } finally {
      setLoading(false);
    }
  };

  if (hasPermission === null) {
    return <View style={styles.center}><Text>Requesting camera permission...</Text></View>;
  }
  if (hasPermission === false) {
    return <View style={styles.center}><Text style={styles.error}>Camera permission denied. Please enable it in Settings.</Text></View>;
  }

  return (
    <View style={styles.container}>
      <Camera
        style={styles.camera}
        type={CameraType.back}
        barCodeScannerSettings={{ barCodeTypes: [BarCodeScanner.Constants.BarCodeType.qr] }}
        onBarCodeScanned={scanned ? undefined : handleBarCodeScanned}
      >
        <View style={styles.overlay}>
          <View style={styles.scanBox} />
          <Text style={styles.hint}>
            {loading ? 'Verifying...' : scanned ? 'Confirmed!' : 'Point camera at customer QR code'}
          </Text>
          {loading && <ActivityIndicator color="#fff" style={{ marginTop: 16 }} />}
        </View>
      </Camera>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000' },
  camera: { flex: 1 },
  overlay: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  scanBox: {
    width: 240, height: 240,
    borderWidth: 3, borderColor: '#4CAF50', borderRadius: 12,
    backgroundColor: 'transparent',
  },
  hint: { color: '#fff', marginTop: 24, fontSize: 16, textAlign: 'center', paddingHorizontal: 32 },
  error: { color: 'red', padding: 24, textAlign: 'center' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
});

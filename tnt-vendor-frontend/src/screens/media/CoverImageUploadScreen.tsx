// ─── Premium Cover Image Upload ─────────────────────────────────
// Upload cover image with premium design system

import React, { useState, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  Animated,
} from 'react-native';
import ImagePicker from '../../components/ImagePicker';
import ImagePreview from '../../components/ImagePreview';
import UploadProgress from '../../components/UploadProgress';
import { imageUploadApi } from '../../services/imageUploadApi';
import { validateImage } from '../../utils/imageCompressor';
import { colors, spacing } from '../../design-system';
import GlassCard from '../../design-system/components/GlassCard';
import Button from '../../design-system/components/Button';

export default function CoverImageUploadScreen({ navigation }: any) {
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [showProgress, setShowProgress] = useState(false);
  const fadeAnim = useRef(new Animated.Value(0)).current;

  React.useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }).start();
  }, []);

  const handleImageSelected = (uri: string) => {
    const validation = validateImage({ uri });
    if (!validation.valid) { Alert.alert('Error', validation.error); return; }
    setSelectedImage(uri);
  };

  const handleUpload = async () => {
    if (!selectedImage) { Alert.alert('Error', 'Select an image first'); return; }
    try {
      setUploading(true); setShowProgress(true); setUploadProgress(0);
      await imageUploadApi.uploadCoverImage(selectedImage, (p) => setUploadProgress(p));
      Alert.alert('Success', 'Cover image uploaded', [{ text: 'OK', onPress: () => navigation.goBack() }]);
    } catch (err: any) { Alert.alert('Error', err.message); }
    finally { setUploading(false); setShowProgress(false); setUploadProgress(0); }
  };

  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      <View style={styles.header}>
        <View style={styles.headerDeco1} /><View style={styles.headerDeco2} />
        <Text style={styles.headerTitle}>Cover Image</Text>
        <Text style={styles.headerSubtitle}>Showcase your business with a beautiful cover</Text>
      </View>

      <Animated.View style={{ opacity: fadeAnim }}>
        <View style={styles.contentSection}>
          {selectedImage ? (
            <GlassCard padding={0} borderRadius={20} style={{ overflow: 'hidden' }}>
              <ImagePreview uri={selectedImage} onRemove={() => setSelectedImage(null)} onEdit={() => {}} />
            </GlassCard>
          ) : (
            <GlassCard padding={20} borderRadius={20}>
              <ImagePicker onImageSelected={handleImageSelected} title="Select Cover Image" />
            </GlassCard>
          )}

          {selectedImage && (
            <Button title="Upload Cover Image" onPress={handleUpload} loading={uploading} variant="primary" size="lg" fullWidth style={{ marginTop: spacing.md }} />
          )}

          <GlassCard padding={16} borderRadius={18} style={{ marginTop: spacing.md }}>
            <Text style={styles.guideTitle}>📋 Guidelines</Text>
            {['1200x630 pixels recommended', 'JPEG, PNG, or WebP', 'Max 5MB', 'Landscape orientation', 'High resolution'].map((g, i) => (
              <Text key={i} style={styles.guideText}>• {g}</Text>
            ))}
          </GlassCard>

          <GlassCard padding={16} borderRadius={18} style={{ marginTop: spacing.sm, backgroundColor: colors.infoPale }}>
            <Text style={styles.helpText}>💡 Your cover image is displayed at the top of your store page. Use an attractive image that represents your business.</Text>
          </GlassCard>
        </View>
        <View style={{ height: spacing.huge }} />
      </Animated.View>

      <UploadProgress progress={uploadProgress} visible={showProgress} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  header: {
    backgroundColor: colors.primary, paddingTop: spacing.huge + 20, paddingBottom: spacing.xxl, paddingHorizontal: spacing.xl,
    borderBottomLeftRadius: 28, borderBottomRightRadius: 28, overflow: 'hidden',
  },
  headerDeco1: { position: 'absolute', top: -40, right: -30, width: 180, height: 180, borderRadius: 90, backgroundColor: 'rgba(255,255,255,0.08)' },
  headerDeco2: { position: 'absolute', bottom: -30, left: -60, width: 140, height: 140, borderRadius: 70, backgroundColor: 'rgba(255,255,255,0.05)' },
  headerTitle: { fontSize: 28, fontWeight: '700', color: colors.textInverse, letterSpacing: -0.3 },
  headerSubtitle: { fontSize: 14, color: 'rgba(255,255,255,0.7)', marginTop: 4, fontWeight: '500' },
  contentSection: { padding: spacing.lg },
  guideTitle: { fontSize: 15, fontWeight: '700', color: colors.textPrimary, marginBottom: 8 },
  guideText: { fontSize: 13, color: colors.textSecondary, marginBottom: 4, lineHeight: 18 },
  helpText: { fontSize: 13, color: colors.info, lineHeight: 18 },
});

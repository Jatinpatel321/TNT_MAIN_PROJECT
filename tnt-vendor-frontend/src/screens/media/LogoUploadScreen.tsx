import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
} from 'react-native';
import ImagePicker from '../../components/ImagePicker';
import ImagePreview from '../../components/ImagePreview';
import UploadProgress from '../../components/UploadProgress';
import { imageUploadApi } from '../../services/imageUploadApi';
import { validateImage } from '../../utils/imageCompressor';

export default function LogoUploadScreen({ navigation }: any) {
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [showProgress, setShowProgress] = useState(false);

  const handleImageSelected = (uri: string) => {
    // Validate image
    const validation = validateImage({ uri });
    if (!validation.valid) {
      Alert.alert('Error', validation.error);
      return;
    }

    setSelectedImage(uri);
  };

  const handleRemoveImage = () => {
    setSelectedImage(null);
  };

  const handleUpload = async () => {
    if (!selectedImage) {
      Alert.alert('Error', 'Please select an image first');
      return;
    }

    try {
      setUploading(true);
      setShowProgress(true);
      setUploadProgress(0);

      const response = await imageUploadApi.uploadLogo(selectedImage, (progress) => {
        setUploadProgress(progress);
      });

      Alert.alert('Success', 'Logo uploaded successfully', [
        { text: 'OK', onPress: () => navigation.goBack() }
      ]);
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Failed to upload logo');
    } finally {
      setUploading(false);
      setShowProgress(false);
      setUploadProgress(0);
    }
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Upload Logo</Text>
        <Text style={styles.headerSubtitle}>
          Add your business logo to personalize your store
        </Text>
      </View>

      <View style={styles.content}>
        {/* Image Preview or Picker */}
        {selectedImage ? (
          <ImagePreview
            uri={selectedImage}
            onRemove={handleRemoveImage}
            onEdit={() => {}}
          />
        ) : (
          <ImagePicker
            onImageSelected={handleImageSelected}
            title="Select Logo"
          />
        )}

        {/* Upload Button */}
        {selectedImage && (
          <TouchableOpacity
            style={[styles.uploadButton, uploading && styles.uploadButtonDisabled]}
            onPress={handleUpload}
            disabled={uploading}
          >
            {uploading ? (
              <ActivityIndicator color="white" />
            ) : (
              <Text style={styles.uploadButtonText}>Upload Logo</Text>
            )}
          </TouchableOpacity>
        )}

        {/* Guidelines */}
        <View style={styles.guidelinesContainer}>
          <Text style={styles.guidelinesTitle}>📋 Guidelines:</Text>
          <Text style={styles.guidelineText}>• Recommended size: 512x512 pixels</Text>
          <Text style={styles.guidelineText}>• Format: JPEG, PNG, or WebP</Text>
          <Text style={styles.guidelineText}>• Max file size: 5MB</Text>
          <Text style={styles.guidelineText}>• Use a square image for best results</Text>
          <Text style={styles.guidelineText}>• High resolution recommended</Text>
        </View>

        {/* Help Text */}
        <View style={styles.helpContainer}>
          <Text style={styles.helpIcon}>💡</Text>
          <Text style={styles.helpText}>
            Your logo will be displayed on your store page and in customer communications.
            Make sure it's clear and professional.
          </Text>
        </View>
      </View>

      {/* Upload Progress Overlay */}
      <UploadProgress progress={uploadProgress} visible={showProgress} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F9FAFB',
  },
  header: {
    padding: 20,
    paddingTop: 60,
    backgroundColor: '#10B981',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: 'white',
    marginBottom: 4,
  },
  headerSubtitle: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.8)',
  },
  content: {
    padding: 16,
  },
  uploadButton: {
    backgroundColor: '#10B981',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    marginTop: 16,
    marginBottom: 16,
  },
  uploadButtonDisabled: {
    backgroundColor: '#9CA3AF',
  },
  uploadButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  guidelinesContainer: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  guidelinesTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
    marginBottom: 12,
  },
  guidelineText: {
    fontSize: 14,
    color: '#374151',
    marginBottom: 6,
    lineHeight: 20,
  },
  helpContainer: {
    backgroundColor: '#DBEAFE',
    borderRadius: 12,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 40,
  },
  helpIcon: {
    fontSize: 20,
    marginRight: 12,
  },
  helpText: {
    flex: 1,
    fontSize: 14,
    color: '#1E40AF',
    lineHeight: 20,
  },
});
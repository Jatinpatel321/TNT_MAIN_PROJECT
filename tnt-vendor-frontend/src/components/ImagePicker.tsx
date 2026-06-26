import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Alert, Platform } from 'react-native';
import { launchCamera, launchImageLibrary, ImagePickerResponse } from 'react-native-image-picker';

interface ImagePickerProps {
  onImageSelected: (uri: string) => void;
  title?: string;
}

export default function ImagePicker({ onImageSelected, title = 'Select Image' }: ImagePickerProps) {
  const handleCamera = () => {
    const options = {
      mediaType: 'photo' as const,
      quality: 0.8,
      maxWidth: 1024,
      maxHeight: 1024,
      includeBase64: false,
    };

    launchCamera(options, (response: ImagePickerResponse) => {
      if (response.assets && response.assets[0]) {
        onImageSelected(response.assets[0].uri || '');
      }
    });
  };

  const handleGallery = () => {
    const options = {
      mediaType: 'photo' as const,
      quality: 0.8,
      maxWidth: 1024,
      maxHeight: 1024,
      includeBase64: false,
    };

    launchImageLibrary(options, (response: ImagePickerResponse) => {
      if (response.assets && response.assets[0]) {
        onImageSelected(response.assets[0].uri || '');
      }
    });
  };

  const showOptions = () => {
    Alert.alert(
      title,
      'Choose an option',
      [
        { text: 'Camera', onPress: handleCamera },
        { text: 'Gallery', onPress: handleGallery },
        { text: 'Cancel', style: 'cancel' },
      ],
      { cancelable: true }
    );
  };

  return (
    <TouchableOpacity style={styles.container} onPress={showOptions}>
      <View style={styles.iconContainer}>
        <Text style={styles.icon}>📷</Text>
      </View>
      <Text style={styles.text}>Tap to select image</Text>
      <Text style={styles.subtext}>Camera or Gallery</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 24,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: '#D1D5DB',
    borderStyle: 'dashed',
    minHeight: 200,
  },
  iconContainer: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#F3F4F6',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  icon: {
    fontSize: 40,
  },
  text: {
    fontSize: 16,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 4,
  },
  subtext: {
    fontSize: 14,
    color: '#6B7280',
  },
});
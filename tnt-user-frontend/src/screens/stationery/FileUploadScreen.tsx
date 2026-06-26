import React, { useState } from 'react';
import { Alert, StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';
import DocumentPicker, { isCancel, types as DocumentPickerTypes } from 'react-native-document-picker';
import { NativeStackScreenProps } from '@react-navigation/native-stack';

import type { RootStackParamList } from '../../types/navigation';
import { Screen } from '../../components/Screen';
import { GradientButton } from '../../components/GradientButton';
import { FileCard, PickedFile } from '../../components/FileCard';
import { toApiError } from '../../services/apiClient';

 type Props = NativeStackScreenProps<RootStackParamList, 'FileUpload'>;

const allowedTypes = ['application/pdf', 'image/jpeg', 'image/png'];

export function FileUploadScreen({ navigation, route }: Props) {
  const { vendorId, vendorName } = route.params;
  const [file, setFile] = useState<PickedFile | null>(null);

  const pick = async () => {
    try {
      const picked = await DocumentPicker.pickSingle({
        type: [DocumentPickerTypes.pdf, DocumentPickerTypes.images],
        copyTo: 'cachesDirectory',
        presentationStyle: 'fullScreen',
      });

      const mimeType = picked.type ?? 'application/octet-stream';
      const finalUri = picked.fileCopyUri ?? picked.uri;
      if (mimeType && !allowedTypes.includes(mimeType) && !mimeType.startsWith('image/')) {
        Alert.alert('Unsupported file', 'Use PDF, JPG, or PNG.');
        return;
      }

      setFile({
        uri: finalUri,
        name: picked.name ?? 'file',
        size: picked.size ?? undefined,
        mimeType,
      });
    } catch (e) {
      if (isCancel(e)) return;
      Alert.alert('File error', toApiError(e).message);
    }
  };

  return (
    <Screen>
      <View style={styles.header}>
        <Text style={styles.title}>Upload Document</Text>
        <Text style={styles.sub}>{vendorName ?? `Vendor #${vendorId}`}</Text>
      </View>

      <View style={styles.uploadBox}>
        <Text style={styles.uploadTitle}>Select PDF or Image</Text>
        <Text style={styles.uploadSub}>Allowed: PDF, JPG, PNG</Text>
        <GradientButton label="Upload Document" onPress={pick} style={styles.uploadBtn} />
      </View>

      {file && (
        <View style={styles.cardWrap}>
          <FileCard file={file} onRemove={() => setFile(null)} />
        </View>
      )}

      <View style={styles.actions}>
        <GradientButton
          label="Continue"
          disabled={!file}
          onPress={() => {
            if (!file) return;
            navigation.navigate('PrintOptions', { vendorId, vendorName, file });
          }}
        />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    paddingVertical: 10,
  },
  title: {
    fontSize: 18,
    fontWeight: '800',
  },
  sub: {
    fontSize: 14,
    color: '#6B7280',
    marginTop: 4,
  },
  uploadBox: {
    backgroundColor: '#FFFFFF',
    borderRadius: 18,
    padding: 16,
    shadowColor: 'rgba(0,0,0,0.1)',
    shadowOpacity: 0.1,
    shadowOffset: { width: 0, height: 4 },
    shadowRadius: 8,
    elevation: 4,
    marginTop: 10,
    gap: 8,
  },
  uploadTitle: {
    fontSize: 16,
    fontWeight: '700',
  },
  uploadSub: {
    fontSize: 14,
    color: '#6B7280',
  },
  uploadBtn: {
    marginTop: 6,
  },
  cardWrap: {
    marginTop: 12,
  },
  actions: {
    marginTop: 16,
  },
});

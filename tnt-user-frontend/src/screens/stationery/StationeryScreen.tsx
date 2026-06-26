import React, { useMemo, useState } from 'react';
import { Alert, StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';
import { NativeStackScreenProps } from '@react-navigation/native-stack';

import type { RootStackParamList } from '../../types/navigation';
import { Screen } from '../../components/Screen';
import { GradientButton } from '../../components/GradientButton';
import { RoundedCard } from '../../components/RoundedCard';
import { FileCard } from '../../components/FileCard';
import { submitStationeryJob } from '../../services/stationeryService';
import { toApiError } from '../../services/apiClient';

type Props = NativeStackScreenProps<RootStackParamList, 'Stationery'>;

export function StationeryScreen({ navigation, route }: Props) {
  const { vendorId, vendorName, file, options } = route.params;
  const [submitting, setSubmitting] = useState(false);

  const summary = useMemo(
    () => [
      { label: 'Print type', value: options.printType === 'color' ? 'Color' : 'Black & White' },
      { label: 'Paper size', value: options.paperSize },
      { label: 'Sides', value: options.duplex ? 'Double sided' : 'Single sided' },
      { label: 'Copies', value: String(options.copies) },
      { label: 'Pages', value: options.pageMode === 'custom' ? options.pageRange ?? 'Custom' : 'All pages' },
      ...(options.notes ? [{ label: 'Notes', value: options.notes }] : []),
    ],
    [options],
  );

  const onSubmit = async () => {
    try {
      setSubmitting(true);
      // Submit the stationery job first (creates a job record)
      const job = await submitStationeryJob({
        serviceId: vendorId,
        quantity: options.copies,
        fileUri: file.uri,
        fileName: file.name,
        mimeType: file.mimeType ?? 'application/octet-stream',
      });

      // Navigate to SlotSelection with stationery items so the user can
      // optionally combine with food items for a single pickup.
      Alert.alert('Job submitted', 'Next, pick a slot for pickup.', [
        {
          text: 'Choose Slot',
          onPress: () =>
            navigation.navigate('SlotSelection', {
              vendorId,
              stationeryItems: [
                {
                  service_id: vendorId,
                  quantity: options.copies,
                  file_url: job.file_url,
                },
              ],
            }),
        },
      ]);
    } catch (e) {
      Alert.alert('Submit failed', toApiError(e).message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Screen scroll>
      <View style={styles.header}>
        <Text style={styles.title}>Review & submit</Text>
        <Text style={styles.sub}>{vendorName ?? `Vendor #${vendorId}`}</Text>
      </View>

      <FileCard file={file} onRemove={() => navigation.navigate('FileUpload', { vendorId, vendorName })} />

      <RoundedCard style={styles.card}>
        <Text style={styles.sectionTitle}>Summary</Text>
        {summary.map((row) => (
          <View key={row.label} style={styles.row}>
            <Text style={styles.label}>{row.label}</Text>
            <Text style={styles.value}>{row.value}</Text>
          </View>
        ))}
      </RoundedCard>

      <View style={styles.actions}>
        <GradientButton
          label={submitting ? 'Submitting…' : 'Submit & Pick Slot'}
          onPress={onSubmit}
          disabled={submitting}
        />
        <Text style={styles.editLink} onPress={() => navigation.goBack()}>
          Edit options
        </Text>
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
  card: {
    marginTop: 12,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '800',
    marginBottom: 8,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  label: {
    fontSize: 14,
    color: '#6B7280',
  },
  value: {
    fontSize: 14,
    fontWeight: '700',
    color: '#111827',
    maxWidth: '60%',
    textAlign: 'right',
  },
  actions: {
    marginTop: 18,
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
  },
  editLink: {
    color: '#6C63FF',
    fontWeight: '700',
  },
});

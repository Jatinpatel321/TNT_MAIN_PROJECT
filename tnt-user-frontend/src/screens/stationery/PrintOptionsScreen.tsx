import React, { useState } from 'react';
import { Alert, Pressable, StyleSheet, TextInput, View } from 'react-native';
import { Text } from 'react-native-paper';
import { NativeStackScreenProps } from '@react-navigation/native-stack';

import type { RootStackParamList } from '../../types/navigation';
import { Screen } from '../../components/Screen';
import { GradientButton } from '../../components/GradientButton';
import { FileCard } from '../../components/FileCard';
import { PrintOptionSelector } from '../../components/PrintOptionSelector';

type Props = NativeStackScreenProps<RootStackParamList, 'PrintOptions'>;

type PrintType = 'bw' | 'color';
type PaperSize = 'A4' | 'A3';
type PageMode = 'all' | 'custom';

export function PrintOptionsScreen({ navigation, route }: Props) {
  const { vendorId, vendorName, file } = route.params;

  const [printType, setPrintType] = useState<PrintType>('bw');
  const [paperSize, setPaperSize] = useState<PaperSize>('A4');
  const [duplex, setDuplex] = useState(false);
  const [copies, setCopies] = useState(1);
  const [pageMode, setPageMode] = useState<PageMode>('all');
  const [pageRange, setPageRange] = useState('');
  const [notes, setNotes] = useState('');

  const onContinue = () => {
    if (pageMode === 'custom' && !pageRange.trim()) {
      Alert.alert('Add page range', 'Specify page numbers or switch back to all pages.');
      return;
    }

    const cleanNotes = notes.trim();
    navigation.navigate('Stationery', {
      vendorId,
      vendorName,
      file,
      options: {
        printType,
        paperSize,
        duplex,
        copies,
        pageMode,
        pageRange: pageMode === 'custom' ? pageRange.trim() : undefined,
        notes: cleanNotes ? cleanNotes : undefined,
      },
    });
  };

  const adjustCopies = (delta: number) => {
    setCopies((prev) => Math.max(1, prev + delta));
  };

  return (
    <Screen scroll>
      <View style={styles.header}>
        <Text style={styles.title}>Print options</Text>
        <Text style={styles.sub}>{vendorName ?? `Vendor #${vendorId}`}</Text>
      </View>

      <FileCard file={file} onRemove={() => navigation.navigate('FileUpload', { vendorId, vendorName })} />

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Print type</Text>
        <View style={styles.rowGap}>
          <PrintOptionSelector label="Black & White" value="bw" current={printType} onSelect={(v) => setPrintType(v as PrintType)} />
          <PrintOptionSelector label="Color" value="color" current={printType} onSelect={(v) => setPrintType(v as PrintType)} />
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Paper size</Text>
        <View style={styles.rowGap}>
          <PrintOptionSelector label="A4" value="A4" current={paperSize} onSelect={(v) => setPaperSize(v as PaperSize)} />
          <PrintOptionSelector label="A3" value="A3" current={paperSize} onSelect={(v) => setPaperSize(v as PaperSize)} />
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Sides</Text>
        <View style={styles.rowGap}>
          <PrintOptionSelector label="Single" value="single" current={duplex ? 'double' : 'single'} onSelect={() => setDuplex(false)} />
          <PrintOptionSelector label="Double" value="double" current={duplex ? 'double' : 'single'} onSelect={() => setDuplex(true)} />
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Copies</Text>
        <View style={styles.stepperRow}>
          <Pressable onPress={() => adjustCopies(-1)} style={[styles.stepperBtn, copies === 1 && styles.stepperDisabled]}>
            <Text style={styles.stepperText}>-</Text>
          </Pressable>
          <Text style={styles.copyCount}>{copies}</Text>
          <Pressable onPress={() => adjustCopies(1)} style={styles.stepperBtn}>
            <Text style={styles.stepperText}>+</Text>
          </Pressable>
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Pages</Text>
        <View style={styles.rowGap}>
          <PrintOptionSelector label="All pages" value="all" current={pageMode} onSelect={(v) => setPageMode(v as PageMode)} />
          <PrintOptionSelector label="Custom" value="custom" current={pageMode} onSelect={(v) => setPageMode(v as PageMode)} />
        </View>
        {pageMode === 'custom' && (
          <TextInput
            placeholder="e.g. 1-3,5,7"
            placeholderTextColor="#9CA3AF"
            value={pageRange}
            onChangeText={setPageRange}
            style={styles.input}
          />
        )}
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Notes</Text>
        <TextInput
          placeholder="Binding, stapling, or any special instructions"
          placeholderTextColor="#9CA3AF"
          value={notes}
          onChangeText={setNotes}
          style={[styles.input, styles.multiline]}
          multiline
          numberOfLines={3}
        />
      </View>

      <View style={styles.actions}>
        <GradientButton label="Review & Continue" onPress={onContinue} />
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
  section: {
    backgroundColor: '#FFFFFF',
    borderRadius: 18,
    padding: 14,
    shadowColor: 'rgba(0,0,0,0.08)',
    shadowOpacity: 0.08,
    shadowOffset: { width: 0, height: 3 },
    shadowRadius: 8,
    elevation: 4,
    marginTop: 12,
    gap: 10,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
  },
  rowGap: {
    flexDirection: 'row',
    gap: 10,
  },
  stepperRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
  },
  stepperBtn: {
    width: 44,
    height: 44,
    borderRadius: 14,
    backgroundColor: '#6C63FF',
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepperDisabled: {
    backgroundColor: '#C7CCD1',
  },
  stepperText: {
    fontSize: 20,
    fontWeight: '800',
    color: '#FFFFFF',
  },
  copyCount: {
    fontSize: 18,
    fontWeight: '800',
  },
  input: {
    marginTop: 6,
    backgroundColor: '#F5F7FB',
    borderRadius: 12,
    padding: 12,
    fontSize: 14,
    color: '#111827',
  },
  multiline: {
    textAlignVertical: 'top',
    minHeight: 90,
  },
  actions: {
    marginTop: 16,
    marginBottom: 12,
  },
});

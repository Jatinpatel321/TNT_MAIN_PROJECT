// ─── Menu Bulk Import / Export ─────────────────────────────────────
// CSV export of the current menu + CSV import with inline preview
// and per-row validation before submitting to the backend.

import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  TextInput,
} from 'react-native';
import { useAuth } from '../../context/AuthContext';
import apiClient from '../../services/apiClient';
import { API_BASE_URL } from '../../config/api';
import { colors, spacing, shadows } from '../../design-system';
import GlassCard from '../../design-system/components/GlassCard';
import Button from '../../design-system/components/Button';
import StatusPill from '../../design-system/components/StatusPill';
import PremiumEmptyState from '../../design-system/components/PremiumEmptyState';

interface ParsedRow {
  line: number;
  name: string;
  price: string;
  category: string;
  description: string;
  prep_time: string;
  available_quantity: string;
  errors: string[];
}

const REQUIRED_HEADERS = ['name', 'price', 'category'];
const CSV_TEMPLATE =
  'name,price,category,description,prep_time,available_quantity\n' +
  'Veg Burger,80,Lunch,Fresh veggie burger,10,50\n' +
  'Masala Tea,20,Beverages,Chai with spices,5,100';

function parseCsv(text: string): { rows: ParsedRow[]; headerError: string | null } {
  const lines = text.trim().split('\n').map(l => l.trim()).filter(Boolean);
  if (lines.length < 2) {
    return { rows: [], headerError: 'CSV must have a header row and at least one data row.' };
  }

  const headers = lines[0].split(',').map(h => h.trim().toLowerCase());
  for (const req of REQUIRED_HEADERS) {
    if (!headers.includes(req)) {
      return { rows: [], headerError: `Missing required column: "${req}"` };
    }
  }

  const idx = (col: string) => headers.indexOf(col);

  const rows: ParsedRow[] = lines.slice(1).map((line, i) => {
    const cols = line.split(',').map(c => c.trim());
    const get = (col: string) => (idx(col) >= 0 ? cols[idx(col)] ?? '' : '');
    const errors: string[] = [];

    const name = get('name');
    const price = get('price');
    const category = get('category');
    const description = get('description');
    const prep_time = get('prep_time');
    const available_quantity = get('available_quantity');

    if (!name) errors.push('Name is required');
    if (!price || isNaN(Number(price)) || Number(price) < 0) errors.push('Valid price required');
    if (!category) errors.push('Category is required');
    if (prep_time && isNaN(Number(prep_time))) errors.push('prep_time must be a number');
    if (available_quantity && isNaN(Number(available_quantity))) errors.push('available_quantity must be a number');

    return { line: i + 2, name, price, category, description, prep_time, available_quantity, errors };
  });

  return { rows, headerError: null };
}

export default function MenuBulkImportScreen({ navigation }: any) {
  const { user } = useAuth();
  const [csvText, setCsvText] = useState('');
  const [parsed, setParsed] = useState<ParsedRow[] | null>(null);
  const [parseError, setParseError] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);
  const [importResults, setImportResults] = useState<{ ok: number; failed: number } | null>(null);
  const [exporting, setExporting] = useState(false);

  const handleParse = () => {
    if (!csvText.trim()) {
      Alert.alert('Empty', 'Please paste CSV content first.');
      return;
    }
    const { rows, headerError } = parseCsv(csvText);
    if (headerError) {
      setParseError(headerError);
      setParsed(null);
    } else {
      setParseError(null);
      setParsed(rows);
    }
  };

  const validRows = parsed?.filter(r => r.errors.length === 0) ?? [];
  const invalidRows = parsed?.filter(r => r.errors.length > 0) ?? [];

  const handleImport = async () => {
    if (validRows.length === 0) {
      Alert.alert('Nothing to import', 'Fix validation errors first.');
      return;
    }
    setImporting(true);
    let ok = 0;
    let failed = 0;
    for (const row of validRows) {
      try {
        await apiClient.post(`${API_BASE_URL}/v1/menu/items`, {
          name: row.name,
          price: Number(row.price),
          category: row.category,
          description: row.description || undefined,
          prep_time_minutes: row.prep_time ? Number(row.prep_time) : undefined,
          available_quantity: row.available_quantity ? Number(row.available_quantity) : undefined,
          is_available: true,
        });
        ok++;
      } catch {
        failed++;
      }
    }
    setImporting(false);
    setImportResults({ ok, failed });
    Alert.alert(
      'Import Complete',
      `✅ ${ok} items added successfully.\n${failed > 0 ? `❌ ${failed} items failed.` : ''}`,
    );
  };

  const handleExport = async () => {
    const vendorId = user?.id;
    if (!vendorId) return;
    setExporting(true);
    try {
      const res = await apiClient.get(`${API_BASE_URL}/v1/menu/items?vendor_id=${vendorId}`);
      const items: any[] = res.data.items || [];
      if (items.length === 0) {
        Alert.alert('No Items', 'Your menu has no items to export.');
        setExporting(false);
        return;
      }
      const header = 'name,price,category,description,prep_time,available_quantity';
      const rows = items.map(i =>
        [
          `"${(i.name || '').replace(/"/g, '""')}"`,
          i.price ?? 0,
          `"${(i.category || '').replace(/"/g, '""')}"`,
          `"${(i.description || '').replace(/"/g, '""')}"`,
          i.prep_time_minutes ?? '',
          i.available_quantity ?? '',
        ].join(','),
      );
      const csv = [header, ...rows].join('\n');
      // Populate the text area so the user can copy
      setCsvText(csv);
      Alert.alert(
        'Exported ✓',
        'Your current menu has been loaded into the CSV editor below. You can copy and save it.',
      );
    } catch (err: any) {
      Alert.alert('Error', err?.message || 'Failed to export menu');
    } finally {
      setExporting(false);
    }
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.deco1} />
        <View style={styles.deco2} />
        <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
          <Text style={styles.backText}>← Back</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Bulk Menu</Text>
        <Text style={styles.headerSubtitle}>Import or export menu items via CSV</Text>
      </View>

      <ScrollView showsVerticalScrollIndicator={false} style={styles.scroll}>
        {/* Template download */}
        <GlassCard padding={16} borderRadius={20} style={{ marginBottom: spacing.md }}>
          <Text style={styles.sectionTitle}>📋 CSV Format</Text>
          <Text style={styles.hint}>
            Required columns: <Text style={styles.bold}>name, price, category</Text>{'\n'}
            Optional: description, prep_time (minutes), available_quantity
          </Text>
          <TouchableOpacity
            style={styles.templateBtn}
            onPress={() => {
              setCsvText(CSV_TEMPLATE);
              setParsed(null);
            }}
          >
            <Text style={styles.templateBtnText}>Load Template</Text>
          </TouchableOpacity>
        </GlassCard>

        {/* Export section */}
        <GlassCard padding={16} borderRadius={20} style={{ marginBottom: spacing.md }}>
          <Text style={styles.sectionTitle}>⬇ Export Current Menu</Text>
          <Text style={styles.hint}>Loads your existing menu items into the editor below.</Text>
          <Button
            title={exporting ? 'Exporting…' : 'Export to CSV Editor'}
            onPress={handleExport}
            loading={exporting}
            variant="secondary"
            size="md"
            fullWidth
            style={{ marginTop: spacing.sm }}
          />
        </GlassCard>

        {/* CSV Input */}
        <GlassCard padding={16} borderRadius={20} style={{ marginBottom: spacing.md }}>
          <Text style={styles.sectionTitle}>⬆ Paste / Edit CSV</Text>
          <TextInput
            style={styles.csvInput}
            value={csvText}
            onChangeText={t => { setCsvText(t); setParsed(null); setParseError(null); }}
            placeholder={CSV_TEMPLATE}
            placeholderTextColor={colors.textMuted}
            multiline
            textAlignVertical="top"
            autoCorrect={false}
            autoCapitalize="none"
          />
          <Button
            title="Preview & Validate"
            onPress={handleParse}
            variant="primary"
            size="md"
            fullWidth
            style={{ marginTop: spacing.sm }}
          />
        </GlassCard>

        {/* Parse error */}
        {parseError && (
          <GlassCard padding={14} borderRadius={16} style={{ marginBottom: spacing.md, borderWidth: 1.5, borderColor: colors.error }}>
            <Text style={{ color: colors.error, fontWeight: '700', fontSize: 14 }}>⚠ Header Error</Text>
            <Text style={{ color: colors.error, fontSize: 13, marginTop: 4 }}>{parseError}</Text>
          </GlassCard>
        )}

        {/* Preview */}
        {parsed !== null && (
          <>
            <View style={styles.summaryRow}>
              <StatusPill label={`${validRows.length} Valid`} variant="success" size="sm" />
              {invalidRows.length > 0 && (
                <StatusPill label={`${invalidRows.length} Errors`} variant="error" size="sm" />
              )}
            </View>

            {/* Valid rows */}
            {validRows.length > 0 && (
              <GlassCard padding={16} borderRadius={20} style={{ marginBottom: spacing.md }}>
                <Text style={styles.sectionTitle}>✅ Valid Rows</Text>
                {validRows.map((row, i) => (
                  <View key={i} style={styles.previewRow}>
                    <View style={styles.previewLeft}>
                      <Text style={styles.previewName}>{row.name}</Text>
                      <Text style={styles.previewMeta}>₹{row.price} · {row.category}</Text>
                    </View>
                    <Text style={styles.previewLine}>L{row.line}</Text>
                  </View>
                ))}
              </GlassCard>
            )}

            {/* Invalid rows */}
            {invalidRows.length > 0 && (
              <GlassCard padding={16} borderRadius={20} style={{ marginBottom: spacing.md, borderWidth: 1.5, borderColor: colors.errorPale }}>
                <Text style={[styles.sectionTitle, { color: colors.error }]}>❌ Rows with Errors</Text>
                {invalidRows.map((row, i) => (
                  <View key={i} style={[styles.previewRow, { borderBottomColor: colors.errorPale }]}>
                    <View style={styles.previewLeft}>
                      <Text style={[styles.previewName, { color: colors.error }]}>
                        Line {row.line}: {row.name || '(unnamed)'}
                      </Text>
                      {row.errors.map((e, j) => (
                        <Text key={j} style={styles.errorText}>• {e}</Text>
                      ))}
                    </View>
                  </View>
                ))}
              </GlassCard>
            )}

            {/* Import button */}
            {validRows.length > 0 && (
              <Button
                title={importing ? `Importing ${validRows.length} items…` : `Import ${validRows.length} Items`}
                onPress={handleImport}
                loading={importing}
                variant="primary"
                size="lg"
                fullWidth
                style={{ marginBottom: spacing.md }}
              />
            )}
          </>
        )}

        {importResults && (
          <GlassCard padding={16} borderRadius={20} style={{ marginBottom: spacing.md }}>
            <Text style={styles.sectionTitle}>Import Results</Text>
            <Text style={{ color: colors.success, fontSize: 14, fontWeight: '600' }}>✅ {importResults.ok} added</Text>
            {importResults.failed > 0 && (
              <Text style={{ color: colors.error, fontSize: 14, fontWeight: '600', marginTop: 4 }}>❌ {importResults.failed} failed</Text>
            )}
          </GlassCard>
        )}

        {parsed === null && !parseError && (
          <PremiumEmptyState
            icon="📥"
            title="No Preview Yet"
            description="Paste your CSV above and tap 'Preview & Validate' to check rows before importing."
          />
        )}

        <View style={{ height: spacing.huge }} />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  scroll: { flex: 1, padding: spacing.lg },
  header: {
    backgroundColor: colors.primary,
    paddingTop: spacing.huge + 20,
    paddingBottom: spacing.xxl,
    paddingHorizontal: spacing.xl,
    borderBottomLeftRadius: 28,
    borderBottomRightRadius: 28,
    overflow: 'hidden',
  },
  deco1: { position: 'absolute', top: -40, right: -30, width: 180, height: 180, borderRadius: 90, backgroundColor: 'rgba(255,255,255,0.08)' },
  deco2: { position: 'absolute', bottom: -30, left: -60, width: 140, height: 140, borderRadius: 70, backgroundColor: 'rgba(255,255,255,0.05)' },
  backBtn: { marginBottom: spacing.sm },
  backText: { color: 'rgba(255,255,255,0.8)', fontSize: 14, fontWeight: '600' },
  headerTitle: { fontSize: 28, fontWeight: '700', color: colors.textInverse, letterSpacing: -0.3 },
  headerSubtitle: { fontSize: 14, color: 'rgba(255,255,255,0.7)', marginTop: 4, fontWeight: '500' },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: colors.textPrimary, marginBottom: 6 },
  hint: { fontSize: 13, color: colors.textSecondary, lineHeight: 20 },
  bold: { fontWeight: '700', color: colors.textPrimary },
  templateBtn: {
    marginTop: spacing.sm,
    backgroundColor: colors.primaryPale,
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 12,
    alignSelf: 'flex-start',
  },
  templateBtnText: { color: colors.primary, fontWeight: '700', fontSize: 13 },
  csvInput: {
    backgroundColor: colors.bgSecondary,
    borderRadius: 12,
    padding: 14,
    fontSize: 12,
    color: colors.textPrimary,
    borderWidth: 1,
    borderColor: colors.border,
    height: 180,
    fontFamily: 'monospace',
  },
  summaryRow: { flexDirection: 'row', gap: spacing.sm, marginBottom: spacing.md },
  previewRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderLight,
  },
  previewLeft: { flex: 1 },
  previewName: { fontSize: 14, fontWeight: '600', color: colors.textPrimary },
  previewMeta: { fontSize: 12, color: colors.textMuted, marginTop: 2 },
  previewLine: { fontSize: 11, color: colors.textMuted, fontWeight: '600' },
  errorText: { fontSize: 12, color: colors.error, marginTop: 2 },
});

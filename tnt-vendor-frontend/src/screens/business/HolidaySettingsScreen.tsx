// ─── Premium Holiday Settings ─────────────────────────────────
// Manage business holidays with premium design system

import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  Animated,
  Modal,
  TextInput,
} from 'react-native';
import { businessSettingsApi } from '../../services/businessSettingsApi';
import { colors, shadows, spacing } from '../../design-system';
import GlassCard from '../../design-system/components/GlassCard';
import PremiumEmptyState from '../../design-system/components/PremiumEmptyState';
import Button from '../../design-system/components/Button';

interface Holiday {
  date: string;
  reason: string;
  id?: number;
}

export default function HolidaySettingsScreen({ navigation }: any) {
  const [holidays, setHolidays] = useState<Holiday[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newHoliday, setNewHoliday] = useState({ date: '', reason: '' });
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }).start();
    loadHolidays();
  }, []);

  const loadHolidays = async () => {
    try {
      setLoading(true);
      const response = await businessSettingsApi.getSettings();
      setHolidays(response.data.holidays || []);
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Failed to load holidays');
    } finally {
      setLoading(false);
    }
  };

  const handleAddHoliday = () => {
    if (!newHoliday.date || !newHoliday.reason) {
      Alert.alert('Error', 'Please fill all fields');
      return;
    }
    setHolidays(prev => [...prev, { ...newHoliday, id: Date.now() }]);
    setNewHoliday({ date: '', reason: '' });
    setShowAddModal(false);
  };

  const handleRemoveHoliday = (holidayId: number) => {
    Alert.alert('Remove Holiday', 'Are you sure?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Remove', style: 'destructive', onPress: () => setHolidays(prev => prev.filter(h => h.id !== holidayId)) },
    ]);
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await businessSettingsApi.updateHolidays(holidays);
      Alert.alert('Success', 'Holidays updated successfully');
      navigation.goBack();
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Failed to save holidays');
    } finally {
      setSaving(false);
    }
  };

  const formatDate = (dateString: string) => {
    try {
      const d = new Date(dateString);
      return d.toLocaleDateString('en-US', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' });
    } catch { return dateString; }
  };

  if (loading) {
    return (
      <View style={[styles.container, styles.centered]}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading holidays...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View style={styles.headerDeco1} />
        <View style={styles.headerDeco2} />
        <Text style={styles.headerTitle}>Holiday Settings</Text>
        <Text style={styles.headerSubtitle}>Manage your business holidays</Text>
      </View>

      <Animated.View style={{ flex: 1, opacity: fadeAnim }}>
        <ScrollView showsVerticalScrollIndicator={false}>
          {holidays.length === 0 ? (
            <PremiumEmptyState
              icon="📅"
              title="No holidays configured"
              description="Add holidays to inform customers about your closure"
              onAction={() => setShowAddModal(true)}
              actionLabel="Add Holiday"
            />
          ) : (
            <View style={styles.listContent}>
              {holidays
                .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
                .map(holiday => (
                  <GlassCard key={holiday.id} padding={14} borderRadius={16} style={{ marginBottom: spacing.sm }}>
                    <View style={styles.holidayRow}>
                      <View style={styles.holidayInfo}>
                        <View style={styles.holidayDateRow}>
                          <Text style={styles.holidayIcon}>📅</Text>
                          <Text style={styles.holidayDate}>{formatDate(holiday.date)}</Text>
                        </View>
                        <Text style={styles.holidayReasonLabel}>Reason</Text>
                        <Text style={styles.holidayReason}>{holiday.reason}</Text>
                      </View>
                      <TouchableOpacity
                        style={styles.removeBtn}
                        onPress={() => holiday.id && handleRemoveHoliday(holiday.id)}
                      >
                        <Text style={styles.removeBtnText}>🗑️</Text>
                      </TouchableOpacity>
                    </View>
                  </GlassCard>
                ))}
            </View>
          )}

          <View style={styles.actionsSection}>
            <Button title="+ Add Holiday" onPress={() => setShowAddModal(true)} variant="secondary" size="md" fullWidth style={{ marginBottom: spacing.sm }} />
            {holidays.length > 0 && (
              <Button title="Save Holidays" onPress={handleSave} loading={saving} variant="primary" size="lg" fullWidth />
            )}
          </View>
          <View style={{ height: spacing.huge }} />
        </ScrollView>
      </Animated.View>

      {/* Add Holiday Modal */}
      <Modal visible={showAddModal} animationType="slide" transparent onRequestClose={() => setShowAddModal(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Add Holiday</Text>
              <TouchableOpacity onPress={() => setShowAddModal(false)}>
                <Text style={styles.modalClose}>✕</Text>
              </TouchableOpacity>
            </View>
            <View style={styles.modalBody}>
              <Text style={styles.modalLabel}>Date *</Text>
              <TextInput
                style={styles.modalInput}
                value={newHoliday.date}
                onChangeText={t => setNewHoliday(prev => ({ ...prev, date: t }))}
                placeholder="YYYY-MM-DD"
                placeholderTextColor={colors.textMuted}
              />
              <Text style={[styles.modalLabel, { marginTop: 16 }]}>Reason *</Text>
              <TextInput
                style={[styles.modalInput, styles.modalTextArea]}
                value={newHoliday.reason}
                onChangeText={t => setNewHoliday(prev => ({ ...prev, reason: t }))}
                placeholder="e.g., Diwali, New Year"
                placeholderTextColor={colors.textMuted}
                multiline
                numberOfLines={3}
              />
            </View>
            <View style={styles.modalFooter}>
              <Button title="Cancel" onPress={() => setShowAddModal(false)} variant="outline" size="md" style={{ flex: 1 }} />
              <Button title="Add Holiday" onPress={handleAddHoliday} variant="primary" size="md" style={{ flex: 1 }} />
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  loadingText: { marginTop: 12, fontSize: 14, color: colors.textMuted, fontWeight: '600' },
  header: {
    backgroundColor: colors.primary,
    paddingTop: spacing.huge + 20,
    paddingBottom: spacing.xxl,
    paddingHorizontal: spacing.xl,
    borderBottomLeftRadius: 28,
    borderBottomRightRadius: 28,
    overflow: 'hidden',
  },
  headerDeco1: { position: 'absolute', top: -40, right: -30, width: 180, height: 180, borderRadius: 90, backgroundColor: 'rgba(255,255,255,0.08)' },
  headerDeco2: { position: 'absolute', bottom: -30, left: -60, width: 140, height: 140, borderRadius: 70, backgroundColor: 'rgba(255,255,255,0.05)' },
  headerTitle: { fontSize: 28, fontWeight: '700', color: colors.textInverse, letterSpacing: -0.3 },
  headerSubtitle: { fontSize: 14, color: 'rgba(255,255,255,0.7)', marginTop: 4, fontWeight: '500' },
  listContent: { padding: spacing.lg, paddingBottom: 0 },
  holidayRow: { flexDirection: 'row', alignItems: 'flex-start' },
  holidayInfo: { flex: 1 },
  holidayDateRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 6 },
  holidayIcon: { fontSize: 16 },
  holidayDate: { fontSize: 15, fontWeight: '600', color: colors.textPrimary },
  holidayReasonLabel: { fontSize: 11, color: colors.textMuted, fontWeight: '500', marginBottom: 2 },
  holidayReason: { fontSize: 14, color: colors.textSecondary },
  removeBtn: { width: 36, height: 36, borderRadius: 12, backgroundColor: colors.errorPale, justifyContent: 'center', alignItems: 'center' },
  removeBtnText: { fontSize: 16 },
  actionsSection: { padding: spacing.lg },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', alignItems: 'center' },
  modalContent: { backgroundColor: colors.bgCard, borderRadius: 24, width: '90%', maxHeight: '80%', ...shadows.modal },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 20, borderBottomWidth: 1, borderBottomColor: colors.border },
  modalTitle: { fontSize: 20, fontWeight: '700', color: colors.textPrimary },
  modalClose: { fontSize: 24, color: colors.textMuted },
  modalBody: { padding: 20 },
  modalLabel: { fontSize: 14, fontWeight: '600', color: colors.textSecondary, marginBottom: 8 },
  modalInput: { backgroundColor: colors.bgSecondary, borderRadius: 12, padding: 14, fontSize: 16, color: colors.textPrimary, borderWidth: 1, borderColor: colors.border },
  modalTextArea: { height: 80, textAlignVertical: 'top' },
  modalFooter: { flexDirection: 'row', padding: 20, gap: 12, borderTopWidth: 1, borderTopColor: colors.border },
});

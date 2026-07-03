// ─── Holiday Settings — Month Grid Calendar ─────────────────────────
// Calendar view to add/remove holidays with reason.
// No external calendar dependency — pure RN implementation.

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
import Button from '../../design-system/components/Button';

interface Holiday {
  date: string;   // YYYY-MM-DD
  reason: string;
  id?: number;
}

const DAYS_SHORT = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];
const MONTHS = [
  'January','February','March','April','May','June',
  'July','August','September','October','November','December',
];

function getDaysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate();
}
function getFirstDayOfWeek(year: number, month: number): number {
  return new Date(year, month, 1).getDay();
}
function toDateStr(year: number, month: number, day: number): string {
  return `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}
function formatDisplay(dateStr: string): string {
  try {
    return new Date(dateStr + 'T00:00:00').toLocaleDateString('en-IN', {
      weekday: 'short', year: 'numeric', month: 'short', day: 'numeric',
    });
  } catch { return dateStr; }
}

export default function HolidaySettingsScreen({ navigation }: any) {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth());
  const [holidays, setHolidays] = useState<Holiday[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Modal state
  const [showModal, setShowModal] = useState(false);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [reason, setReason] = useState('');
  const [editingId, setEditingId] = useState<number | null>(null);

  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }).start();
    loadHolidays();
  }, []);

  const loadHolidays = async () => {
    try {
      setLoading(true);
      const response = await businessSettingsApi.getSettings();
      setHolidays((response.data.holidays || []).map((h: any, i: number) => ({ ...h, id: h.id ?? i + 1 })));
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Failed to load holidays');
    } finally {
      setLoading(false);
    }
  };

  const holidayMap = new Set(holidays.map(h => h.date));

  const prevMonth = () => {
    if (month === 0) { setYear(y => y - 1); setMonth(11); }
    else setMonth(m => m - 1);
  };
  const nextMonth = () => {
    if (month === 11) { setYear(y => y + 1); setMonth(0); }
    else setMonth(m => m + 1);
  };

  const handleDayPress = (day: number) => {
    const dateStr = toDateStr(year, month, day);
    const existing = holidays.find(h => h.date === dateStr);
    if (existing) {
      // Open edit modal
      setSelectedDate(dateStr);
      setReason(existing.reason);
      setEditingId(existing.id ?? null);
      setShowModal(true);
    } else {
      // Open add modal
      setSelectedDate(dateStr);
      setReason('');
      setEditingId(null);
      setShowModal(true);
    }
  };

  const handleModalSave = () => {
    if (!selectedDate) return;
    if (!reason.trim()) {
      Alert.alert('Required', 'Please enter a reason for this holiday.');
      return;
    }
    setHolidays(prev => {
      const without = prev.filter(h => h.date !== selectedDate);
      return [...without, { date: selectedDate, reason: reason.trim(), id: editingId ?? Date.now() }];
    });
    setShowModal(false);
  };

  const handleModalRemove = () => {
    if (!selectedDate) return;
    Alert.alert('Remove Holiday', 'Remove this holiday?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Remove',
        style: 'destructive',
        onPress: () => {
          setHolidays(prev => prev.filter(h => h.date !== selectedDate));
          setShowModal(false);
        },
      },
    ]);
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await businessSettingsApi.updateHolidays(holidays);
      Alert.alert('Saved', 'Holidays updated successfully');
      navigation.goBack();
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Failed to save holidays');
    } finally {
      setSaving(false);
    }
  };

  const daysInMonth = getDaysInMonth(year, month);
  const firstDay = getFirstDayOfWeek(year, month);
  const todayStr = toDateStr(today.getFullYear(), today.getMonth(), today.getDate());

  if (loading) {
    return (
      <View style={[styles.container, styles.centered]}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading holidays…</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.deco1} />
        <View style={styles.deco2} />
        <Text style={styles.headerTitle}>Holiday Settings</Text>
        <Text style={styles.headerSubtitle}>Tap a date to mark / edit a holiday</Text>
      </View>

      <Animated.View style={{ flex: 1, opacity: fadeAnim }}>
        <ScrollView showsVerticalScrollIndicator={false}>
          {/* Calendar Card */}
          <GlassCard padding={16} borderRadius={20} style={{ margin: spacing.lg }}>
            {/* Month navigation */}
            <View style={styles.monthNav}>
              <TouchableOpacity onPress={prevMonth} style={styles.navBtn}>
                <Text style={styles.navArrow}>‹</Text>
              </TouchableOpacity>
              <Text style={styles.monthLabel}>{MONTHS[month]} {year}</Text>
              <TouchableOpacity onPress={nextMonth} style={styles.navBtn}>
                <Text style={styles.navArrow}>›</Text>
              </TouchableOpacity>
            </View>

            {/* Day-of-week headers */}
            <View style={styles.weekRow}>
              {DAYS_SHORT.map(d => (
                <Text key={d} style={styles.weekDay}>{d}</Text>
              ))}
            </View>

            {/* Day cells */}
            <View style={styles.grid}>
              {/* Leading blank cells */}
              {Array.from({ length: firstDay }).map((_, i) => (
                <View key={`blank-${i}`} style={styles.dayCell} />
              ))}
              {/* Day cells */}
              {Array.from({ length: daysInMonth }).map((_, i) => {
                const day = i + 1;
                const dateStr = toDateStr(year, month, day);
                const isHoliday = holidayMap.has(dateStr);
                const isToday = dateStr === todayStr;
                return (
                  <TouchableOpacity
                    key={day}
                    style={[
                      styles.dayCell,
                      isHoliday && styles.dayCellHoliday,
                      isToday && !isHoliday && styles.dayCellToday,
                    ]}
                    onPress={() => handleDayPress(day)}
                    activeOpacity={0.75}
                  >
                    <Text style={[
                      styles.dayText,
                      isHoliday && styles.dayTextHoliday,
                      isToday && !isHoliday && styles.dayTextToday,
                    ]}>
                      {day}
                    </Text>
                    {isHoliday && <View style={styles.holidayDot} />}
                  </TouchableOpacity>
                );
              })}
            </View>

            {/* Legend */}
            <View style={styles.legend}>
              <View style={styles.legendItem}>
                <View style={[styles.legendDot, { backgroundColor: colors.primary }]} />
                <Text style={styles.legendText}>Holiday</Text>
              </View>
              <View style={styles.legendItem}>
                <View style={[styles.legendDot, { backgroundColor: colors.warning }]} />
                <Text style={styles.legendText}>Today</Text>
              </View>
            </View>
          </GlassCard>

          {/* Holiday list */}
          {holidays.length > 0 && (
            <View style={{ paddingHorizontal: spacing.lg }}>
              <Text style={styles.listTitle}>📅 Configured Holidays ({holidays.length})</Text>
              {holidays
                .sort((a, b) => a.date.localeCompare(b.date))
                .map(h => (
                  <GlassCard key={h.id} padding={14} borderRadius={16} style={{ marginBottom: spacing.sm }}>
                    <View style={styles.holidayRow}>
                      <View style={styles.holidayInfo}>
                        <Text style={styles.holidayDate}>{formatDisplay(h.date)}</Text>
                        <Text style={styles.holidayReason}>{h.reason}</Text>
                      </View>
                      <TouchableOpacity
                        style={styles.removeBtn}
                        onPress={() => setHolidays(prev => prev.filter(x => x.id !== h.id))}
                      >
                        <Text style={styles.removeBtnText}>🗑️</Text>
                      </TouchableOpacity>
                    </View>
                  </GlassCard>
                ))}
            </View>
          )}

          <View style={{ paddingHorizontal: spacing.lg, marginTop: spacing.md }}>
            <Button
              title="Save Holidays"
              onPress={handleSave}
              loading={saving}
              variant="primary"
              size="lg"
              fullWidth
            />
          </View>
          <View style={{ height: spacing.huge }} />
        </ScrollView>
      </Animated.View>

      {/* Add / Edit Modal */}
      <Modal visible={showModal} animationType="slide" transparent onRequestClose={() => setShowModal(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>
                {editingId ? 'Edit Holiday' : 'Add Holiday'}
              </Text>
              <TouchableOpacity onPress={() => setShowModal(false)}>
                <Text style={styles.modalClose}>✕</Text>
              </TouchableOpacity>
            </View>
            <View style={styles.modalBody}>
              {selectedDate && (
                <Text style={styles.selectedDateText}>{formatDisplay(selectedDate)}</Text>
              )}
              <Text style={styles.modalLabel}>Reason *</Text>
              <TextInput
                style={[styles.modalInput, styles.modalTextArea]}
                value={reason}
                onChangeText={setReason}
                placeholder="e.g. Diwali, National Holiday, Maintenance"
                placeholderTextColor={colors.textMuted}
                multiline
                numberOfLines={3}
              />
            </View>
            <View style={styles.modalFooter}>
              {editingId && (
                <TouchableOpacity style={styles.removeModalBtn} onPress={handleModalRemove}>
                  <Text style={styles.removeModalBtnText}>Remove</Text>
                </TouchableOpacity>
              )}
              <Button title="Cancel" onPress={() => setShowModal(false)} variant="outline" size="md" style={{ flex: 1 }} />
              <Button title={editingId ? 'Update' : 'Add'} onPress={handleModalSave} variant="primary" size="md" style={{ flex: 1 }} />
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  centered: { justifyContent: 'center', alignItems: 'center' },
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
  deco1: { position: 'absolute', top: -40, right: -30, width: 180, height: 180, borderRadius: 90, backgroundColor: 'rgba(255,255,255,0.08)' },
  deco2: { position: 'absolute', bottom: -30, left: -60, width: 140, height: 140, borderRadius: 70, backgroundColor: 'rgba(255,255,255,0.05)' },
  headerTitle: { fontSize: 28, fontWeight: '700', color: colors.textInverse, letterSpacing: -0.3 },
  headerSubtitle: { fontSize: 14, color: 'rgba(255,255,255,0.7)', marginTop: 4, fontWeight: '500' },
  // Calendar
  monthNav: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: spacing.md },
  navBtn: { width: 36, height: 36, borderRadius: 12, backgroundColor: colors.primaryPale, justifyContent: 'center', alignItems: 'center' },
  navArrow: { fontSize: 22, color: colors.primary, fontWeight: '700' },
  monthLabel: { fontSize: 18, fontWeight: '700', color: colors.textPrimary },
  weekRow: { flexDirection: 'row', marginBottom: 8 },
  weekDay: { flex: 1, textAlign: 'center', fontSize: 12, fontWeight: '700', color: colors.textMuted },
  grid: { flexDirection: 'row', flexWrap: 'wrap' },
  dayCell: {
    width: '14.28%',
    aspectRatio: 1,
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 8,
    marginVertical: 2,
  },
  dayCellHoliday: { backgroundColor: colors.primary },
  dayCellToday: { backgroundColor: colors.warningPale },
  dayText: { fontSize: 14, fontWeight: '500', color: colors.textPrimary },
  dayTextHoliday: { color: colors.textInverse, fontWeight: '700' },
  dayTextToday: { color: colors.warningDark, fontWeight: '700' },
  holidayDot: { width: 4, height: 4, borderRadius: 2, backgroundColor: colors.textInverse, marginTop: 2 },
  legend: { flexDirection: 'row', gap: 16, marginTop: spacing.md },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  legendDot: { width: 10, height: 10, borderRadius: 5 },
  legendText: { fontSize: 12, color: colors.textMuted },
  // List
  listTitle: { fontSize: 16, fontWeight: '700', color: colors.textPrimary, marginBottom: spacing.sm },
  holidayRow: { flexDirection: 'row', alignItems: 'flex-start' },
  holidayInfo: { flex: 1 },
  holidayDate: { fontSize: 14, fontWeight: '600', color: colors.textPrimary },
  holidayReason: { fontSize: 13, color: colors.textSecondary, marginTop: 2 },
  removeBtn: { width: 36, height: 36, borderRadius: 12, backgroundColor: colors.errorPale, justifyContent: 'center', alignItems: 'center' },
  removeBtnText: { fontSize: 16 },
  // Modal
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  modalContent: { backgroundColor: colors.bgCard, borderTopLeftRadius: 24, borderTopRightRadius: 24, ...shadows.modal },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 20, borderBottomWidth: 1, borderBottomColor: colors.border },
  modalTitle: { fontSize: 20, fontWeight: '700', color: colors.textPrimary },
  modalClose: { fontSize: 24, color: colors.textMuted },
  modalBody: { padding: 20 },
  selectedDateText: { fontSize: 16, fontWeight: '700', color: colors.primary, marginBottom: spacing.md },
  modalLabel: { fontSize: 14, fontWeight: '600', color: colors.textSecondary, marginBottom: 8 },
  modalInput: { backgroundColor: colors.bgSecondary, borderRadius: 12, padding: 14, fontSize: 16, color: colors.textPrimary, borderWidth: 1, borderColor: colors.border },
  modalTextArea: { height: 80, textAlignVertical: 'top' },
  modalFooter: { flexDirection: 'row', padding: 20, gap: 12, borderTopWidth: 1, borderTopColor: colors.border },
  removeModalBtn: { paddingHorizontal: 16, paddingVertical: 10, borderRadius: 12, backgroundColor: colors.errorPale, justifyContent: 'center' },
  removeModalBtnText: { color: colors.error, fontWeight: '700', fontSize: 13 },
});

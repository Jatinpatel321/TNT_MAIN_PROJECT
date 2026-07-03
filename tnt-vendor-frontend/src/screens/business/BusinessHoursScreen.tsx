// ─── Premium Business Hours Screen ─────────────────────────────
// Set operating hours with premium design system

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
} from 'react-native';
import { businessSettingsApi } from '../../services/businessSettingsApi';
import { colors, shadows, spacing } from '../../design-system';
import GlassCard from '../../design-system/components/GlassCard';
import StatusPill from '../../design-system/components/StatusPill';
import Button from '../../design-system/components/Button';

const DAYS = [
  { key: 'monday', label: 'Monday', short: 'Mon' },
  { key: 'tuesday', label: 'Tuesday', short: 'Tue' },
  { key: 'wednesday', label: 'Wednesday', short: 'Wed' },
  { key: 'thursday', label: 'Thursday', short: 'Thu' },
  { key: 'friday', label: 'Friday', short: 'Fri' },
  { key: 'saturday', label: 'Saturday', short: 'Sat' },
  { key: 'sunday', label: 'Sunday', short: 'Sun' },
];

interface DayHours {
  open: string;
  close: string;
  is_closed: boolean;
}

export default function BusinessHoursScreen({ navigation }: any) {
  const [hours, setHours] = useState<{ [key: string]: DayHours }>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }).start();
    loadBusinessHours();
  }, []);

  const loadBusinessHours = async () => {
    try {
      setLoading(true);
      const response = await businessSettingsApi.getSettings();
      const businessHours = response.data.business_hours || {};
      const defaultHours: { [key: string]: DayHours } = {};
      DAYS.forEach(day => {
        defaultHours[day.key] = businessHours[day.key] || { open: '09:00', close: '18:00', is_closed: false };
      });
      setHours(defaultHours);
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Failed to load business hours');
    } finally {
      setLoading(false);
    }
  };

  const toggleDayClosed = (dayKey: string) => {
    setHours(prev => ({
      ...prev,
      [dayKey]: { ...prev[dayKey], is_closed: !prev[dayKey].is_closed },
    }));
  };

  const copyToAllDays = (sourceDay: string) => {
    const sourceHours = hours[sourceDay];
    const newHours: { [key: string]: DayHours } = {};
    DAYS.forEach(day => { newHours[day.key] = { ...sourceHours }; });
    setHours(newHours);
    Alert.alert('Copied', 'Hours copied to all days');
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await businessSettingsApi.updateBusinessHours(hours);
      Alert.alert('Success', 'Business hours updated successfully');
      navigation.goBack();
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Failed to save business hours');
    } finally {
      setSaving(false);
    }
  };

  const cycleTime = (key: string, field: 'open' | 'close', increment: boolean) => {
    setHours(prev => {
      const current = prev[key][field];
      const [h, m] = current.split(':').map(Number);
      let newH = (h + (increment ? 1 : -1) + 24) % 24;
      const newTime = `${String(newH).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
      return { ...prev, [key]: { ...prev[key], [field]: newTime } };
    });
  };

  if (loading) {
    return (
      <View style={[styles.container, styles.centered]}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading business hours...</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      <View style={styles.header}>
        <View style={styles.headerDeco1} />
        <View style={styles.headerDeco2} />
        <Text style={styles.headerTitle}>Business Hours</Text>
        <Text style={styles.headerSubtitle}>Set your operating hours for each day</Text>
      </View>

      <Animated.View style={{ opacity: fadeAnim }}>
        {DAYS.map((day, index) => {
          const dayHours = hours[day.key] || { open: '09:00', close: '18:00', is_closed: false };
          return (
            <View key={day.key} style={styles.daySection}>
              <GlassCard padding={16} borderRadius={18} intensity={dayHours.is_closed ? 'light' : 'medium'}>
                <View style={styles.dayHeader}>
                  <View style={styles.dayInfo}>
                    <Text style={styles.dayLabel}>{day.label}</Text>
                    <TouchableOpacity onPress={() => toggleDayClosed(day.key)}>
                      <StatusPill
                        label={dayHours.is_closed ? 'CLOSED' : 'OPEN'}
                        variant={dayHours.is_closed ? 'error' : 'success'}
                        size="sm"
                      />
                    </TouchableOpacity>
                  </View>
                  {index === 0 && (
                    <TouchableOpacity style={styles.copyBtn} onPress={() => copyToAllDays(day.key)}>
                      <Text style={styles.copyBtnText}>Copy to All</Text>
                    </TouchableOpacity>
                  )}
                </View>

                {!dayHours.is_closed && (
                  <View style={styles.timeRow}>
                    <View style={styles.timeBlock}>
                      <Text style={styles.timeLabel}>Opens</Text>
                      <View style={styles.timeDisplay}>
                        <TouchableOpacity onPress={() => cycleTime(day.key, 'open', false)} style={styles.timeArrow}>
                          <Text style={styles.arrowText}>▲</Text>
                        </TouchableOpacity>
                        <Text style={styles.timeValue}>{dayHours.open}</Text>
                        <TouchableOpacity onPress={() => cycleTime(day.key, 'open', true)} style={styles.timeArrow}>
                          <Text style={styles.arrowText}>▼</Text>
                        </TouchableOpacity>
                      </View>
                    </View>
                    <Text style={styles.timeSeparator}>→</Text>
                    <View style={styles.timeBlock}>
                      <Text style={styles.timeLabel}>Closes</Text>
                      <View style={styles.timeDisplay}>
                        <TouchableOpacity onPress={() => cycleTime(day.key, 'close', false)} style={styles.timeArrow}>
                          <Text style={styles.arrowText}>▲</Text>
                        </TouchableOpacity>
                        <Text style={styles.timeValue}>{dayHours.close}</Text>
                        <TouchableOpacity onPress={() => cycleTime(day.key, 'close', true)} style={styles.timeArrow}>
                          <Text style={styles.arrowText}>▼</Text>
                        </TouchableOpacity>
                      </View>
                    </View>
                  </View>
                )}
              </GlassCard>
            </View>
          );
        })}

        <View style={styles.saveSection}>
          <Button
            title="Save Business Hours"
            onPress={handleSave}
            loading={saving}
            variant="primary"
            size="lg"
            fullWidth
          />
        </View>
        <View style={{ height: spacing.huge }} />
      </Animated.View>
    </ScrollView>
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
  daySection: { paddingHorizontal: spacing.lg, marginTop: spacing.sm },
  dayHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  dayInfo: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  dayLabel: { fontSize: 16, fontWeight: '600', color: colors.textPrimary },
  copyBtn: { backgroundColor: colors.primaryPale, paddingHorizontal: 12, paddingVertical: 6, borderRadius: 10 },
  copyBtnText: { fontSize: 12, fontWeight: '600', color: colors.primary },
  timeRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 16, marginTop: 4 },
  timeBlock: { flex: 1, alignItems: 'center' },
  timeLabel: { fontSize: 12, color: colors.textMuted, fontWeight: '500', marginBottom: 6 },
  timeDisplay: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  timeArrow: { width: 28, height: 28, borderRadius: 8, backgroundColor: colors.bgSecondary, justifyContent: 'center', alignItems: 'center' },
  arrowText: { fontSize: 10, color: colors.textSecondary },
  timeValue: { fontSize: 20, fontWeight: '700', color: colors.textPrimary, minWidth: 50, textAlign: 'center', fontVariant: ['tabular-nums'] },
  timeSeparator: { fontSize: 20, color: colors.textMuted, marginTop: 20 },
  saveSection: { paddingHorizontal: spacing.lg, marginTop: spacing.xxl },
});

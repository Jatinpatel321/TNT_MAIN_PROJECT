// ─── Premium Faculty Priority Settings ──────────────────────────
// Configure faculty priority hours with premium design system

import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  Alert,
  ActivityIndicator,
  Animated,
} from 'react-native';
import { slotApi } from '../../services/slotApi';
import { colors, spacing } from '../../design-system';
import GlassCard from '../../design-system/components/GlassCard';
import StatusPill from '../../design-system/components/StatusPill';
import Button from '../../design-system/components/Button';

export default function FacultyPrioritySettingsScreen({ navigation }: any) {
  const [rules, setRules] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ start_hour: '9', end_hour: '17', priority: '5' });
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }).start();
    fetchRules();
  }, []);

  const fetchRules = async () => {
    try { setLoading(true); const res = await slotApi.getRules(); setRules((res.data || []).filter((r: any) => r.rule_type === 'faculty_priority')); }
    catch (err: any) { Alert.alert('Error', err.message); }
    finally { setLoading(false); }
  };

  const handleCreate = async () => {
    try {
      setSaving(true);
      await slotApi.createRule({
        rule_type: 'faculty_priority',
        rule_config: { faculty_priority_hours: { start: parseInt(form.start_hour), end: parseInt(form.end_hour) } },
        is_enabled: true, priority: parseInt(form.priority),
      });
      setShowForm(false); fetchRules(); Alert.alert('Success', 'Faculty priority rule created');
    } catch (err: any) { Alert.alert('Error', err.message); }
    finally { setSaving(false); }
  };

  const handleDelete = (id: number) => {
    Alert.alert('Delete Rule', 'Sure?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: async () => { try { await slotApi.deleteRule(id); fetchRules(); } catch (err: any) { Alert.alert('Error', err.message); } } },
    ]);
  };

  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      <View style={styles.header}>
        <View style={styles.headerDeco1} /><View style={styles.headerDeco2} />
        <Text style={styles.headerTitle}>Faculty Priority</Text>
        <Text style={styles.headerSubtitle}>{rules.length} active rules</Text>
      </View>

      <Animated.View style={{ opacity: fadeAnim }}>
        <View style={styles.infoCard}>
          <Text style={styles.infoIcon}>ℹ️</Text>
          <Text style={styles.infoText}>Faculty priority slots reserve capacity for faculty members during specified hours. Only faculty and admin users can book these slots.</Text>
        </View>

        <View style={styles.actionsWrap}>
          <Button title={showForm ? '✕ Cancel' : '+ Add Rule'} onPress={() => setShowForm(!showForm)} variant={showForm ? 'outline' : 'primary'} size="md" fullWidth />
        </View>

        {showForm && (
          <GlassCard padding={18} borderRadius={20} style={{ marginHorizontal: spacing.lg, marginBottom: spacing.md }}>
            <FormField label="Start Hour (0-23)" value={form.start_hour} onChange={t => setForm(p => ({ ...p, start_hour: t }))} placeholder="9" keyboard="numeric" />
            <FormField label="End Hour (0-23)" value={form.end_hour} onChange={t => setForm(p => ({ ...p, end_hour: t }))} placeholder="17" keyboard="numeric" />
            <FormField label="Priority (1-10)" value={form.priority} onChange={t => setForm(p => ({ ...p, priority: t }))} placeholder="5" keyboard="numeric" />
            <Button title="Create Rule" onPress={handleCreate} loading={saving} variant="primary" size="md" fullWidth style={{ marginTop: 12 }} />
          </GlassCard>
        )}

        {loading ? (
          <View style={styles.loadingWrap}><ActivityIndicator size="large" color={colors.primary} /></View>
        ) : (
          rules.map(rule => (
            <GlassCard key={rule.id} padding={16} borderRadius={18} style={{ marginHorizontal: spacing.lg, marginBottom: spacing.sm }}>
              <View style={styles.ruleHeader}>
                <View style={styles.titleRow}><Text style={styles.facultyIcon}>👨‍🏫</Text><Text style={styles.ruleType}>Faculty Priority</Text></View>
                <StatusPill label={rule.is_enabled ? 'Enabled' : 'Disabled'} variant={rule.is_enabled ? 'success' : 'neutral'} size="sm" />
              </View>
              {rule.rule_config?.faculty_priority_hours && (
                <RuleDetail label="Hours" value={`${rule.rule_config.faculty_priority_hours.start}:00 - ${rule.rule_config.faculty_priority_hours.end}:00`} />
              )}
              <RuleDetail label="Priority" value={rule.priority} />
              <View style={styles.noteBox}><Text style={styles.noteText}>Faculty-only booking during these hours</Text></View>
              <Button title="Delete" onPress={() => handleDelete(rule.id)} variant="danger" size="sm" fullWidth />
            </GlassCard>
          ))
        )}
        <View style={{ height: spacing.huge }} />
      </Animated.View>
    </ScrollView>
  );
}

function RuleDetail({ label, value }: { label: string; value: string | number }) {
  return <View style={detailStyles.row}><Text style={detailStyles.label}>{label}</Text><Text style={detailStyles.value}>{value}</Text></View>;
}
const detailStyles = StyleSheet.create({
  row: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 4 },
  label: { fontSize: 13, color: colors.textMuted },
  value: { fontSize: 14, fontWeight: '600', color: colors.textPrimary },
});

function FormField({ label, value, onChange, placeholder, keyboard }: { label: string; value: string; onChange: (t: string) => void; placeholder: string; keyboard?: any }) {
  return (
    <View style={fieldStyles.group}>
      <Text style={fieldStyles.label}>{label}</Text>
      <TextInput style={fieldStyles.input} value={value} onChangeText={onChange} placeholder={placeholder} placeholderTextColor={colors.textMuted} keyboardType={keyboard} />
    </View>
  );
}
const fieldStyles = StyleSheet.create({
  group: { marginBottom: 12 },
  label: { fontSize: 13, fontWeight: '600', color: colors.textSecondary, marginBottom: 6 },
  input: { backgroundColor: colors.bgSecondary, borderRadius: 12, padding: 12, fontSize: 16, color: colors.textPrimary, borderWidth: 1, borderColor: colors.border },
});

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
  infoCard: { flexDirection: 'row', backgroundColor: colors.infoPale, margin: spacing.lg, borderRadius: 16, padding: 16, gap: 12 },
  infoIcon: { fontSize: 20 },
  infoText: { flex: 1, fontSize: 13, color: colors.info, lineHeight: 18 },
  actionsWrap: { paddingHorizontal: spacing.lg, marginBottom: spacing.sm },
  loadingWrap: { padding: 40, alignItems: 'center' },
  ruleHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  facultyIcon: { fontSize: 20 },
  ruleType: { fontSize: 16, fontWeight: '700', color: colors.textPrimary },
  noteBox: { backgroundColor: colors.warningPale, borderRadius: 10, padding: 10, marginVertical: 10 },
  noteText: { fontSize: 12, color: colors.warningDark, fontWeight: '500' },
});

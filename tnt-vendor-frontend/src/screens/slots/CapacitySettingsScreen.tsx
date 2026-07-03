// ─── Premium Capacity Settings ──────────────────────────────────
// Manage capacity rules with premium design system

import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  Animated,
} from 'react-native';
import { slotApi } from '../../services/slotApi';
import { colors, spacing } from '../../design-system';
import GlassCard from '../../design-system/components/GlassCard';
import StatusPill from '../../design-system/components/StatusPill';
import Button from '../../design-system/components/Button';

export default function CapacitySettingsScreen({ navigation }: any) {
  const [rules, setRules] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ rule_type: 'time_based', day_of_week: '0', hour_of_day: '9', max_capacity: '20', duration_minutes: '60', priority: '1' });
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }).start();
    fetchRules();
  }, []);

  const fetchRules = async () => {
    try { setLoading(true); const res = await slotApi.getCapacityRules(); setRules(res.data || []); }
    catch (err: any) { Alert.alert('Error', err.message); }
    finally { setLoading(false); }
  };

  const handleCreate = async () => {
    try {
      setSaving(true);
      await slotApi.createCapacityRule({
        rule_type: form.rule_type,
        rule_config: {
          day_of_week: parseInt(form.day_of_week),
          hour_of_day: parseInt(form.hour_of_day),
          max_capacity: parseInt(form.max_capacity),
          duration_minutes: parseInt(form.duration_minutes),
        },
        is_enabled: true,
        priority: parseInt(form.priority),
      });
      setShowForm(false); fetchRules();
      Alert.alert('Success', 'Capacity rule created');
    } catch (err: any) { Alert.alert('Error', err.message); }
    finally { setSaving(false); }
  };

  const handleDelete = (id: number) => {
    Alert.alert('Delete Rule', 'Are you sure?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: async () => { try { await slotApi.deleteCapacityRule(id); fetchRules(); } catch (err: any) { Alert.alert('Error', err.message); } } },
    ]);
  };

  const getDayName = (d: number) => ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'][d] || 'Every day';

  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      <View style={styles.header}>
        <View style={styles.headerDeco1} /><View style={styles.headerDeco2} />
        <Text style={styles.headerTitle}>Capacity Settings</Text>
        <Text style={styles.headerSubtitle}>{rules.length} active rules</Text>
      </View>

      <Animated.View style={{ opacity: fadeAnim }}>
        <View style={styles.actionsWrap}>
          <Button title={showForm ? '✕ Cancel' : '+ Add Rule'} onPress={() => setShowForm(!showForm)} variant={showForm ? 'outline' : 'primary'} size="md" fullWidth />
        </View>

        {showForm && (
          <GlassCard padding={18} borderRadius={20} style={{ marginHorizontal: spacing.lg, marginBottom: spacing.md }}>
            <FormField label="Rule Type" value={form.rule_type} onChange={t => setForm(p => ({ ...p, rule_type: t }))} placeholder="time_based" />
            <FormField label="Day of Week (0-6, 0=Sun)" value={form.day_of_week} onChange={t => setForm(p => ({ ...p, day_of_week: t }))} placeholder="0" keyboard="numeric" />
            <FormField label="Hour (0-23)" value={form.hour_of_day} onChange={t => setForm(p => ({ ...p, hour_of_day: t }))} placeholder="9" keyboard="numeric" />
            <FormField label="Max Capacity" value={form.max_capacity} onChange={t => setForm(p => ({ ...p, max_capacity: t }))} placeholder="20" keyboard="numeric" />
            <FormField label="Duration (min)" value={form.duration_minutes} onChange={t => setForm(p => ({ ...p, duration_minutes: t }))} placeholder="60" keyboard="numeric" />
            <FormField label="Priority (1-10)" value={form.priority} onChange={t => setForm(p => ({ ...p, priority: t }))} placeholder="1" keyboard="numeric" />
            <Button title="Create Rule" onPress={handleCreate} loading={saving} variant="primary" size="md" fullWidth style={{ marginTop: 12 }} />
          </GlassCard>
        )}

        {loading ? (
          <View style={styles.loadingWrap}><ActivityIndicator size="large" color={colors.primary} /></View>
        ) : (
          rules.map(rule => (
            <GlassCard key={rule.id} padding={16} borderRadius={18} style={{ marginHorizontal: spacing.lg, marginBottom: spacing.sm }}>
              <View style={styles.ruleHeader}>
                <Text style={styles.ruleType}>{rule.rule_type}</Text>
                <StatusPill label={rule.is_enabled ? 'Enabled' : 'Disabled'} variant={rule.is_enabled ? 'success' : 'neutral'} size="sm" />
              </View>
              <View style={styles.ruleDetails}>
                {rule.rule_config?.day_of_week !== undefined && <RuleDetail label="Day" value={getDayName(rule.rule_config.day_of_week)} />}
                {rule.rule_config?.hour_of_day !== undefined && <RuleDetail label="Hour" value={`${rule.rule_config.hour_of_day}:00`} />}
                {rule.rule_config?.max_capacity && <RuleDetail label="Max" value={rule.rule_config.max_capacity} />}
                {rule.rule_config?.duration_minutes && <RuleDetail label="Duration" value={`${rule.rule_config.duration_minutes} min`} />}
                <RuleDetail label="Priority" value={rule.priority} />
              </View>
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
  return (
    <View style={detailStyles.row}>
      <Text style={detailStyles.label}>{label}</Text>
      <Text style={detailStyles.value}>{value}</Text>
    </View>
  );
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
  actionsWrap: { paddingHorizontal: spacing.lg, marginTop: spacing.md, marginBottom: spacing.sm },
  loadingWrap: { padding: 40, alignItems: 'center' },
  ruleHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  ruleType: { fontSize: 16, fontWeight: '700', color: colors.textPrimary, textTransform: 'capitalize' },
  ruleDetails: { marginBottom: 12 },
});

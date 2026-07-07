// ─── Premium Slot Configuration ─────────────────────────────────
// Create time slots with premium design system

import React, { useState, useRef } from 'react';
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
import Button from '../../design-system/components/Button';

export default function SlotConfigurationScreen({ navigation }: any) {
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({ start_time: '09:00', end_time: '10:00', max_orders: '10' });
  const fadeAnim = useRef(new Animated.Value(0)).current;

  React.useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }).start();
  }, []);

  const handleCreate = async () => {
    if (!formData.start_time || !formData.end_time || !formData.max_orders) {
      Alert.alert('Error', 'Please fill all fields');
      return;
    }
    const maxOrders = parseInt(formData.max_orders);
    if (isNaN(maxOrders) || maxOrders <= 0) {
      Alert.alert('Error', 'Max orders must be positive');
      return;
    }
    try {
      setLoading(true);
      const today = new Date();
      const [sh, sm] = formData.start_time.split(':').map(Number);
      const [eh, em] = formData.end_time.split(':').map(Number);
      const startTime = new Date(today); startTime.setHours(sh, sm, 0, 0);
      const endTime = new Date(today); endTime.setHours(eh, em, 0, 0);
      if (endTime <= startTime) {
        Alert.alert('Error', 'End time must be after start time');
        setLoading(false); return;
      }
      await slotApi.createSlot({ start_time: startTime.toISOString(), end_time: endTime.toISOString(), max_orders: maxOrders });
      Alert.alert('Success', 'Slot created', [{ text: 'OK', onPress: () => navigation.goBack() }]);
    } catch (err: any) { Alert.alert('Error', err.message || 'Failed to create slot'); }
    finally { setLoading(false); }
  };

  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      <View style={styles.header}>
        <View style={styles.headerDeco1} /><View style={styles.headerDeco2} />
        <Text style={styles.headerTitle}>Create Slot</Text>
        <Text style={styles.headerSubtitle}>Add a new time slot for orders</Text>
      </View>

      <Animated.View style={{ opacity: fadeAnim }}>
        <View style={styles.formSection}>
          <GlassCard padding={18} borderRadius={20}>
            <FormField label="Start Time (HH:MM)" value={formData.start_time} onChange={t => setFormData(p => ({ ...p, start_time: t }))} placeholder="09:00" />
            <FormField label="End Time (HH:MM)" value={formData.end_time} onChange={t => setFormData(p => ({ ...p, end_time: t }))} placeholder="10:00" />
            <FormField label="Max Orders" value={formData.max_orders} onChange={t => setFormData(p => ({ ...p, max_orders: t }))} placeholder="10" keyboard="numeric" />
          </GlassCard>

          <Button title="Create Slot" onPress={handleCreate} loading={loading} variant="primary" size="lg" fullWidth style={{ marginTop: spacing.xxl }} />
        </View>
        <View style={{ height: spacing.huge }} />
      </Animated.View>
    </ScrollView>
  );
}

function FormField({ label, value, onChange, placeholder, keyboard }: { label: string; value: string; onChange: (t: string) => void; placeholder: string; keyboard?: any }) {
  return (
    <View style={fieldStyles.group}>
      <Text style={fieldStyles.label}>{label}</Text>
      <TextInput style={fieldStyles.input} value={value} onChangeText={onChange} placeholder={placeholder} placeholderTextColor={colors.textMuted} keyboardType={keyboard} />
    </View>
  );
}

const fieldStyles = StyleSheet.create({
  group: { marginBottom: 14 },
  label: { fontSize: 13, fontWeight: '600', color: colors.textSecondary, marginBottom: 6 },
  input: { backgroundColor: colors.bgSecondary, borderRadius: 12, padding: 14, fontSize: 16, color: colors.textPrimary, borderWidth: 1, borderColor: colors.border },
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
  formSection: { padding: spacing.lg },
});

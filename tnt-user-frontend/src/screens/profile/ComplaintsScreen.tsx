import React, { useCallback, useEffect, useState } from 'react';
import { Alert, Modal, Pressable, StyleSheet, TextInput, View } from 'react-native';
import { Text } from 'react-native-paper';
import MaterialCommunityIcons from 'react-native-vector-icons/MaterialCommunityIcons';
import { NativeStackScreenProps } from '@react-navigation/native-stack';

import type { RootStackParamList } from '../../types/navigation';
import { Screen } from '../../components/Screen';
import { GradientButton } from '../../components/GradientButton';
import {
  createComplaint,
  getMyComplaints,
} from '../../services/complaintsService';
import type { Complaint, ComplaintCategory } from '../../services/complaintsService';
import { toApiError } from '../../services/apiClient';
import { useAppTheme } from '../../theme/ThemeContext';
import { Chip, EmptyState, FadeInSection, SectionCard, SkeletonBlock } from './profileUi';

type Props = NativeStackScreenProps<RootStackParamList, 'Complaints'>;

const CATEGORY_OPTIONS: { value: ComplaintCategory; label: string; icon: string }[] = [
  { value: 'late_order', label: 'Late Order', icon: 'clock-alert-outline' },
  { value: 'wrong_item', label: 'Wrong Item', icon: 'swap-horizontal' },
  { value: 'quality_issue', label: 'Quality Issue', icon: 'alert-circle-outline' },
  { value: 'other', label: 'Other', icon: 'help-circle-outline' },
];

const STATUS_META: Record<string, { label: string; tone: 'warn' | 'ok' | 'bad' | 'info' }> = {
  open: { label: 'Open', tone: 'warn' },
  assigned: { label: 'Assigned', tone: 'info' },
  in_progress: { label: 'In Progress', tone: 'info' },
  resolved: { label: 'Resolved', tone: 'ok' },
  rejected: { label: 'Rejected', tone: 'bad' },
  escalated: { label: 'Escalated', tone: 'bad' },
};

export function ComplaintsScreen({ navigation }: Props) {
  const { colors } = useAppTheme();
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [category, setCategory] = useState<ComplaintCategory>('other');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [orderId, setOrderId] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    try {
      setComplaints(await getMyComplaints());
    } catch (e) {
      Alert.alert('Failed to load complaints', toApiError(e).message);
    }
  }, []);

  useEffect(() => {
    (async () => {
      await load();
      setLoading(false);
    })();
  }, [load]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }, [load]);

  const toneColor = (tone: 'warn' | 'ok' | 'bad' | 'info') =>
    tone === 'ok'
      ? { fg: colors.success, bg: colors.successSoft }
      : tone === 'bad'
        ? { fg: colors.danger, bg: colors.dangerSoft }
        : tone === 'warn'
          ? { fg: colors.warning, bg: colors.warningSoft }
          : { fg: colors.accent, bg: colors.primarySoft };

  const submit = async () => {
    const trimmedTitle = title.trim();
    if (trimmedTitle.length < 3) {
      Alert.alert('Validation', 'Please give your complaint a short title (min 3 characters).');
      return;
    }
    let orderIdNum: number | undefined;
    if (orderId.trim()) {
      orderIdNum = parseInt(orderId.trim(), 10);
      if (isNaN(orderIdNum) || orderIdNum <= 0) {
        Alert.alert('Validation', 'Order ID must be a number.');
        return;
      }
    }

    setSubmitting(true);
    try {
      await createComplaint({
        category,
        title: trimmedTitle,
        description: description.trim() || undefined,
        order_id: orderIdNum,
      });
      setShowForm(false);
      setTitle('');
      setDescription('');
      setOrderId('');
      setCategory('other');
      await load();
      Alert.alert('Complaint filed', 'Our team will get back to you soon.');
    } catch (e) {
      Alert.alert('Could not file complaint', toApiError(e).message);
    } finally {
      setSubmitting(false);
    }
  };

  const inputStyle = [
    styles.input,
    { backgroundColor: colors.surfaceAlt, borderColor: colors.border, color: colors.text },
  ];

  return (
    <Screen scroll refreshing={refreshing} onRefresh={onRefresh}>
      <View style={styles.header}>
        <Pressable onPress={() => navigation.goBack()} hitSlop={8}>
          <MaterialCommunityIcons name="arrow-left" size={24} color={colors.text} />
        </Pressable>
        <Text style={[styles.title, { color: colors.text }]}>Support & Complaints</Text>
        <View style={{ width: 24 }} />
      </View>

      <Pressable
        onPress={() => setShowForm(true)}
        style={[styles.newBtn, { backgroundColor: colors.primary }]}
      >
        <MaterialCommunityIcons name="plus" size={18} color="#FFFFFF" />
        <Text style={styles.newBtnText}>Raise a Complaint</Text>
      </Pressable>

      {loading ? (
        <View style={{ gap: 12, marginTop: 14 }}>
          <SkeletonBlock width={'100%' as const} height={92} radius={16} />
          <SkeletonBlock width={'100%' as const} height={92} radius={16} />
        </View>
      ) : complaints.length === 0 ? (
        <SectionCard style={{ marginTop: 14 }}>
          <EmptyState
            icon="emoticon-happy-outline"
            title="No complaints"
            subtitle="If something goes wrong with an order, raise it here and track its status."
          />
        </SectionCard>
      ) : (
        <View style={{ gap: 12, marginTop: 14 }}>
          {complaints.map((c, idx) => {
            const meta = STATUS_META[c.status] ?? { label: c.status, tone: 'info' as const };
            const tone = toneColor(meta.tone);
            return (
              <FadeInSection key={c.id} delay={idx * 50}>
                <SectionCard>
                  <View style={styles.cardTop}>
                    <Text style={[styles.cardTitle, { color: colors.text }]} numberOfLines={1}>
                      {c.title}
                    </Text>
                    <View style={[styles.statusBadge, { backgroundColor: tone.bg }]}>
                      <Text style={[styles.statusText, { color: tone.fg }]}>{meta.label}</Text>
                    </View>
                  </View>
                  {c.description ? (
                    <Text style={[styles.cardDesc, { color: colors.subtext }]} numberOfLines={2}>
                      {c.description}
                    </Text>
                  ) : null}
                  <View style={styles.cardMetaRow}>
                    <Text style={[styles.cardMeta, { color: colors.muted }]}>
                      {CATEGORY_OPTIONS.find((o) => o.value === c.category)?.label ?? c.category}
                    </Text>
                    {c.order_id != null && (
                      <Text style={[styles.cardMeta, { color: colors.muted }]}>Order #{c.order_id}</Text>
                    )}
                    <Text style={[styles.cardMeta, { color: colors.muted }]}>
                      {new Date(c.created_at).toLocaleDateString('en-IN', {
                        day: 'numeric',
                        month: 'short',
                      })}
                    </Text>
                  </View>
                </SectionCard>
              </FadeInSection>
            );
          })}
        </View>
      )}

      {/* New complaint modal */}
      <Modal visible={showForm} transparent animationType="slide" onRequestClose={() => setShowForm(false)}>
        <View style={[styles.modalBackdrop, { backgroundColor: colors.overlay }]}>
          <View style={[styles.modalSheet, { backgroundColor: colors.surface }]}>
            <View style={styles.modalHeader}>
              <Text style={[styles.modalTitle, { color: colors.text }]}>New Complaint</Text>
              <Pressable onPress={() => setShowForm(false)} hitSlop={8}>
                <MaterialCommunityIcons name="close" size={22} color={colors.muted} />
              </Pressable>
            </View>

            <Text style={[styles.fieldLabel, { color: colors.subtext }]}>Category</Text>
            <View style={styles.chipRow}>
              {CATEGORY_OPTIONS.map((opt) => (
                <Chip
                  key={opt.value}
                  label={opt.label}
                  icon={opt.icon}
                  active={category === opt.value}
                  onPress={() => setCategory(opt.value)}
                />
              ))}
            </View>

            <Text style={[styles.fieldLabel, { color: colors.subtext }]}>Title</Text>
            <TextInput
              style={inputStyle}
              value={title}
              onChangeText={setTitle}
              placeholder="Short summary"
              placeholderTextColor={colors.muted}
              maxLength={150}
            />

            <Text style={[styles.fieldLabel, { color: colors.subtext }]}>Details (optional)</Text>
            <TextInput
              style={[...inputStyle, styles.multiline]}
              value={description}
              onChangeText={setDescription}
              placeholder="What happened?"
              placeholderTextColor={colors.muted}
              multiline
              numberOfLines={4}
            />

            <Text style={[styles.fieldLabel, { color: colors.subtext }]}>Order ID (optional)</Text>
            <TextInput
              style={inputStyle}
              value={orderId}
              onChangeText={setOrderId}
              placeholder="e.g. 1024"
              placeholderTextColor={colors.muted}
              keyboardType="number-pad"
            />

            <View style={{ marginTop: 16 }}>
              <GradientButton
                label={submitting ? 'Submitting...' : 'Submit Complaint'}
                onPress={submit}
                disabled={submitting}
              />
            </View>
          </View>
        </View>
      </Modal>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 10,
  },
  title: {
    fontSize: 18,
    fontWeight: '800',
  },
  newBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    borderRadius: 14,
    paddingVertical: 12,
    marginTop: 4,
  },
  newBtnText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '800',
  },
  cardTop: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 10,
  },
  cardTitle: {
    flex: 1,
    fontSize: 15,
    fontWeight: '800',
  },
  statusBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
  },
  statusText: {
    fontSize: 11,
    fontWeight: '800',
  },
  cardDesc: {
    fontSize: 13,
    lineHeight: 18,
    marginTop: 6,
  },
  cardMetaRow: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 10,
  },
  cardMeta: {
    fontSize: 12,
    fontWeight: '600',
  },
  modalBackdrop: {
    flex: 1,
    justifyContent: 'flex-end',
  },
  modalSheet: {
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 20,
    paddingBottom: 32,
  },
  modalHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  modalTitle: {
    fontSize: 17,
    fontWeight: '800',
  },
  fieldLabel: {
    fontSize: 13,
    fontWeight: '600',
    marginTop: 14,
    marginBottom: 6,
  },
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  input: {
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 11,
    fontSize: 14,
    borderWidth: 1,
  },
  multiline: {
    minHeight: 90,
    textAlignVertical: 'top',
  },
});

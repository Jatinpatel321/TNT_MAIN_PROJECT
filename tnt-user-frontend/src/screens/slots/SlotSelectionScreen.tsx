import React, { useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  View,
} from 'react-native';
import { Text } from 'react-native-paper';
import MaterialCommunityIcons from 'react-native-vector-icons/MaterialCommunityIcons';
import { NativeStackScreenProps } from '@react-navigation/native-stack';

import type { RootStackParamList } from '../../types/navigation';
import { Screen } from '../../components/Screen';
import { GradientButton } from '../../components/GradientButton';
import {
  getSlots,
  bookSlot,
  cancelSlotBooking,
  combinedBooking,
  type Slot,
  type CombinedBookingResponse,
} from '../../services/slotService';
import { mockPayment, type PaymentMethod } from '../../services/paymentService';
import { toApiError } from '../../services/apiClient';
import { checkout, type CheckoutResponse } from '../../services/cartService';
import { useCart } from '../../context/CartContext';
import { formatTimeRange } from '../../utils/format';

type Props = NativeStackScreenProps<RootStackParamList, 'SlotSelection' | 'Checkout'>;

const PAYMENT_METHODS: { method: PaymentMethod; icon: string; label: string }[] = [
  { method: 'UPI', icon: '⚡', label: 'UPI / QR' },
  { method: 'CARD', icon: '💳', label: 'Debit / Credit Card' },
  { method: 'WALLET', icon: '👛', label: 'Campus Wallet' },
];

type SlotVisualStatus = 'available' | 'limited' | 'full' | 'locked';

function getSlotStatus(slot: Slot): SlotVisualStatus {
  if (slot.is_locked) return 'locked';
  const status = (slot.status ?? '').toLowerCase();
  if (status === 'full') return 'full';
  const available = Math.max((slot.max_orders ?? 0) - (slot.current_orders ?? 0), 0);
  if (available <= 0) return 'full';
  if (status === 'limited' || available <= Math.ceil((slot.max_orders ?? 1) * 0.3)) return 'limited';
  return 'available';
}

const STATUS_CONFIG: Record<SlotVisualStatus, { color: string; bg: string; label: string; icon: string }> = {
  available: { color: '#059669', bg: '#ECFDF5', label: 'Available', icon: 'check-circle' },
  limited: { color: '#D97706', bg: '#FFFBEB', label: 'Limited', icon: 'alert-circle' },
  full: { color: '#6B7280', bg: '#F3F4F6', label: 'Full', icon: 'close-circle' },
  locked: { color: '#DC2626', bg: '#FEF2F2', label: 'Locked', icon: 'lock' },
};

export function SlotSelectionScreen({ route, navigation }: Props) {
  const { vendorId, stationeryItems } = route.params;
  const { clearCart } = useCart();

  const [slots, setSlots] = useState<Slot[]>([]);
  const [estimatedReady, setEstimatedReady] = useState<string | null | undefined>(undefined);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [booking, setBooking] = useState(false);

  // Combined booking state: stationery toggle
  const [addStationery, setAddStationery] = useState(stationeryItems != null && stationeryItems.length > 0);

  // Payment modal
  const [showPayModal, setShowPayModal] = useState(false);
  const [pendingOrderId, setPendingOrderId] = useState<number | null>(null);
  const [pendingOrderAmount, setPendingOrderAmount] = useState<number | null>(null);
  const [pendingPickupToken, setPendingPickupToken] = useState<string | null>(null);
  const [selectedMethod, setSelectedMethod] = useState<PaymentMethod>('UPI');
  const [paying, setPaying] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const { slots: list, estimated_ready_time } = await getSlots(vendorId ?? undefined);
        setSlots(list);
        setEstimatedReady(estimated_ready_time);
      } catch (e) {
        Alert.alert('Failed to load slots', toApiError(e).message);
      } finally {
        setLoading(false);
      }
    })();
  }, [vendorId]);

  const selectedSlot = useMemo(() => slots.find((s) => s.id === selectedId) ?? null, [slots, selectedId]);

  const etaLabel = useMemo(() => {
    if (estimatedReady) return estimatedReady;
    const source = selectedSlot ?? slots.find((s) => getSlotStatus(s) === 'available');
    if (!source) return '--';
    return formatTimeRange(source.start_time, source.end_time);
  }, [selectedSlot, slots, estimatedReady]);

  // Auto-select AI recommended
  useEffect(() => {
    if (!selectedId && slots.length > 0) {
      const ai = slots.find((s) => s.is_ai_recommended && getSlotStatus(s) === 'available');
      if (ai) setSelectedId(ai.id);
      else {
        const first = slots.find((s) => getSlotStatus(s) === 'available');
        if (first) setSelectedId(first.id);
      }
    }
  }, [slots, selectedId]);

  const onConfirm = async () => {
    if (!selectedSlot) return;
    try {
      setBooking(true);

      // If we have stationery items AND the user wants combined booking
      if (addStationery && stationeryItems && stationeryItems.length > 0) {
        // Use the combined booking endpoint
        const foodItemsFromCart = []; // Frontend sends cart items separately
        // Actually, we need to get the current cart food items
        // The cart is stored in context, but here we use the combined booking approach
        const payload = {
          slot_id: selectedSlot.id,
          food_items: [] as { menu_item_id: number; quantity: number }[],
          stationery_items: stationeryItems.map((si) => ({
            service_id: si.service_id,
            quantity: si.quantity,
            file_url: si.file_url ?? null,
          })),
        };

        const res: CombinedBookingResponse = await combinedBooking(payload);
        void clearCart();
        setPendingOrderId(res.order_id);
        setPendingOrderAmount(res.total_amount);
        setPendingPickupToken(res.order_id.toString());
        setShowPayModal(true);
      } else {
        // Standard food-only checkout
        const res: CheckoutResponse = await checkout(selectedSlot.id, selectedMethod);
        void clearCart();
        setPendingOrderId(res.order_id);
        setPendingOrderAmount(res.total_amount);
        setPendingPickupToken(res.pickup_token);
        setShowPayModal(true);
      }
    } catch (e) {
      Alert.alert('Booking failed', toApiError(e).message);
    } finally {
      setBooking(false);
    }
  };

  const onPay = async () => {
    if (!pendingOrderId) return;
    try {
      setPaying(true);
      const result = await mockPayment(pendingOrderId, selectedMethod, pendingOrderAmount ?? undefined);
      setShowPayModal(false);
      const isCombined = addStationery && stationeryItems != null && stationeryItems.length > 0;
      Alert.alert(
        'Payment Successful',
        `${result.message}\n\nPickup Token: ${pendingPickupToken ?? '--'}` +
          (isCombined ? '\n(includes stationery items)' : ''),
        [{ text: 'Track Order', onPress: () => navigation.navigate('OrderTracking', { orderId: pendingOrderId }) }],
      );
    } catch (e) {
      Alert.alert('Payment failed', toApiError(e).message);
    } finally {
      setPaying(false);
    }
  };

  // Summary counts
  const availableCount = slots.filter((s) => getSlotStatus(s) === 'available').length;
  const limitedCount = slots.filter((s) => getSlotStatus(s) === 'limited').length;
  const fullCount = slots.filter((s) => getSlotStatus(s) === 'full').length;

  const hasStationeryItems = stationeryItems != null && stationeryItems.length > 0;

  return (
    <Screen scroll>
      <View style={styles.header}>
        <Pressable onPress={() => navigation.goBack()} hitSlop={8}>
          <MaterialCommunityIcons name="arrow-left" size={24} color="#111827" />
        </Pressable>
        <Text style={styles.title}>Select a Slot</Text>
        <View style={{ width: 24 }} />
      </View>

      {/* ETA Block */}
      <View style={styles.etaBlock}>
        <Text style={styles.etaLabel}>Estimated Ready Time</Text>
        <Text style={styles.etaValue}>{etaLabel}</Text>
      </View>

      {/* Stationery toggle — only shown when the user navigated here with stationery items */}
      {hasStationeryItems && (
        <View style={styles.stationeryToggle}>
          <View style={styles.toggleRow}>
            <View style={styles.toggleInfo}>
              <MaterialCommunityIcons name="file-document-outline" size={20} color="#6C63FF" />
              <Text style={styles.toggleLabel}>Add stationery item to this pickup</Text>
            </View>
            <Switch
              value={addStationery}
              onValueChange={setAddStationery}
              trackColor={{ false: '#E5E7EB', true: '#C4B5FD' }}
              thumbColor={addStationery ? '#6C63FF' : '#9CA3AF'}
            />
          </View>
          {addStationery && (
            <View style={styles.stationerySummary}>
              <Text style={styles.stationerySummaryTitle}>Stationery items:</Text>
              {stationeryItems!.map((item, idx) => (
                <Text key={idx} style={styles.stationeryItemRow}>
                  • Service #{item.service_id} × {item.quantity}
                </Text>
              ))}
            </View>
          )}
        </View>
      )}

      {/* Slot summary */}
      <View style={styles.summaryRow}>
        <View style={[styles.summaryChip, { backgroundColor: '#ECFDF5' }]}>
          <Text style={[styles.summaryCount, { color: '#059669' }]}>{availableCount}</Text>
          <Text style={[styles.summaryLabel, { color: '#059669' }]}>Available</Text>
        </View>
        <View style={[styles.summaryChip, { backgroundColor: '#FFFBEB' }]}>
          <Text style={[styles.summaryCount, { color: '#D97706' }]}>{limitedCount}</Text>
          <Text style={[styles.summaryLabel, { color: '#D97706' }]}>Limited</Text>
        </View>
        <View style={[styles.summaryChip, { backgroundColor: '#F3F4F6' }]}>
          <Text style={[styles.summaryCount, { color: '#6B7280' }]}>{fullCount}</Text>
          <Text style={[styles.summaryLabel, { color: '#6B7280' }]}>Full</Text>
        </View>
      </View>

      {loading ? (
        <View style={styles.center}><ActivityIndicator size="large" color="#6C63FF" /></View>
      ) : slots.length === 0 ? (
        <View style={styles.center}>
          <MaterialCommunityIcons name="clock-outline" size={48} color="#D1D5DB" />
          <Text style={styles.emptyTitle}>No slots available</Text>
          <Text style={styles.emptySub}>Check back later or try a different vendor</Text>
        </View>
      ) : (
        <ScrollView style={styles.slotsList} showsVerticalScrollIndicator={false}>
          {slots.map((slot) => {
            const status = getSlotStatus(slot);
            const cfg = STATUS_CONFIG[status];
            const isSelected = selectedId === slot.id;
            const isSelectable = status === 'available' || status === 'limited';
            const available = Math.max((slot.max_orders ?? 0) - (slot.current_orders ?? 0), 0);

            return (
              <Pressable
                key={slot.id}
                style={[
                  styles.slotCard,
                  { borderLeftColor: cfg.color, borderLeftWidth: 4 },
                  isSelected && styles.slotCardSelected,
                  !isSelectable && styles.slotCardDisabled,
                ]}
                onPress={() => isSelectable && setSelectedId(slot.id)}
                disabled={!isSelectable}
              >
                <View style={styles.slotHeader}>
                  <Text style={styles.slotTime}>
                    {formatTimeRange(slot.start_time, slot.end_time)}
                  </Text>
                  <View style={[styles.statusBadge, { backgroundColor: cfg.bg }]}>
                    <MaterialCommunityIcons name={cfg.icon as any} size={14} color={cfg.color} />
                    <Text style={[styles.statusText, { color: cfg.color }]}>{cfg.label}</Text>
                  </View>
                </View>

                <View style={styles.slotMetaRow}>
                  <View style={styles.metaItem}>
                    <MaterialCommunityIcons name="account-group" size={14} color="#6B7280" />
                    <Text style={styles.metaText}>{slot.current_orders ?? 0}/{slot.max_orders ?? 0}</Text>
                  </View>
                  <View style={styles.metaItem}>
                    <MaterialCommunityIcons name="clock-outline" size={14} color="#6B7280" />
                    <Text style={styles.metaText}>~{slot.estimated_wait ?? 0} min</Text>
                  </View>
                  {available > 0 && (
                    <View style={styles.metaItem}>
                      <MaterialCommunityIcons name="check" size={14} color="#059669" />
                      <Text style={[styles.metaText, { color: '#059669' }]}>{available} left</Text>
                    </View>
                  )}
                </View>

                {slot.faculty_priority && (
                  <View style={styles.facultyBadge}>
                    <MaterialCommunityIcons name="school" size={12} color="#6C63FF" />
                    <Text style={styles.facultyText}>Faculty Priority</Text>
                  </View>
                )}

                {slot.is_ai_recommended && isSelectable && (
                  <View style={styles.aiBadge}>
                    <MaterialCommunityIcons name="lightning-bolt" size={12} color="#F59E0B" />
                    <Text style={styles.aiText}>AI Recommended</Text>
                  </View>
                )}

                {slot.is_locked && (
                  <View style={styles.lockBadge}>
                    <MaterialCommunityIcons name="lock" size={12} color="#DC2626" />
                    <Text style={styles.lockText}>Locked by vendor</Text>
                  </View>
                )}

                {/* Capacity bar */}
                <View style={styles.capacityBar}>
                  <View style={styles.capacityTrack}>
                    <View
                      style={[
                        styles.capacityFill,
                        {
                          width: `${Math.min(((slot.current_orders ?? 0) / Math.max(slot.max_orders ?? 1, 1)) * 100, 100)}%`,
                          backgroundColor: cfg.color,
                        },
                      ]}
                    />
                  </View>
                </View>
              </Pressable>
            );
          })}
        </ScrollView>
      )}

      <View style={styles.actions}>
        <GradientButton
          label={
            booking
              ? 'Booking...'
              : addStationery && hasStationeryItems
              ? 'Confirm Combined Booking'
              : 'Confirm Slot'
          }
          onPress={onConfirm}
          disabled={!selectedSlot || booking}
        />
      </View>

      {/* Payment method modal */}
      <Modal visible={showPayModal} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalSheet}>
            <Text style={styles.modalTitle}>Choose Payment Method</Text>
            {PAYMENT_METHODS.map(({ method, icon, label }) => (
              <Pressable
                key={method}
                style={[styles.methodRow, selectedMethod === method && styles.methodRowSelected]}
                onPress={() => setSelectedMethod(method)}
              >
                <Text style={styles.methodIcon}>{icon}</Text>
                <Text style={styles.methodLabel}>{label}</Text>
                {selectedMethod === method && <Text style={styles.checkmark}>✓</Text>}
              </Pressable>
            ))}
            <View style={styles.modalActions}>
              <Pressable style={styles.cancelBtn} onPress={() => setShowPayModal(false)} disabled={paying}>
                <Text style={styles.cancelLabel}>Cancel</Text>
              </Pressable>
              <Pressable style={[styles.payBtn, paying && styles.btnDisabled]} onPress={onPay} disabled={paying}>
                {paying ? <ActivityIndicator color="#fff" size="small" /> : <Text style={styles.payLabel}>Pay Now</Text>}
              </Pressable>
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
  etaBlock: {
    backgroundColor: '#FFFFFF',
    borderRadius: 18,
    padding: 14,
    shadowColor: 'rgba(0,0,0,0.08)',
    shadowOpacity: 0.08,
    shadowOffset: { width: 0, height: 3 },
    shadowRadius: 8,
    elevation: 4,
    marginTop: 12,
    gap: 6,
  },
  etaLabel: { fontSize: 14, color: '#6B7280' },
  etaValue: { fontSize: 20, fontWeight: '900', color: '#111827' },
  stationeryToggle: {
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
  toggleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  toggleInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flex: 1,
  },
  toggleLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
    flex: 1,
  },
  stationerySummary: {
    backgroundColor: '#F5F3FF',
    borderRadius: 12,
    padding: 12,
    gap: 4,
  },
  stationerySummaryTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: '#6C63FF',
    marginBottom: 4,
  },
  stationeryItemRow: {
    fontSize: 13,
    color: '#374151',
  },
  summaryRow: {
    flexDirection: 'row',
    gap: 10,
    marginTop: 14,
  },
  summaryChip: {
    flex: 1,
    borderRadius: 14,
    paddingVertical: 10,
    alignItems: 'center',
    gap: 2,
  },
  summaryCount: {
    fontSize: 20,
    fontWeight: '800',
  },
  summaryLabel: {
    fontSize: 11,
    fontWeight: '600',
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 40,
  },
  emptyTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#374151',
  },
  emptySub: {
    fontSize: 14,
    color: '#9CA3AF',
  },
  slotsList: {
    marginTop: 14,
  },
  slotCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 14,
    marginBottom: 10,
    shadowColor: 'rgba(0,0,0,0.05)',
    shadowOpacity: 0.05,
    shadowOffset: { width: 0, height: 2 },
    shadowRadius: 6,
    elevation: 3,
    gap: 8,
  },
  slotCardSelected: {
    borderWidth: 2,
    borderColor: '#6C63FF',
  },
  slotCardDisabled: {
    opacity: 0.6,
  },
  slotHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  slotTime: {
    fontSize: 16,
    fontWeight: '700',
    color: '#111827',
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 10,
  },
  statusText: {
    fontSize: 11,
    fontWeight: '700',
  },
  slotMetaRow: {
    flexDirection: 'row',
    gap: 14,
  },
  metaItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  metaText: {
    fontSize: 12,
    color: '#6B7280',
  },
  facultyBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: '#F3F2FF',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 8,
    alignSelf: 'flex-start',
  },
  facultyText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#6C63FF',
  },
  aiBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: '#FFFBEB',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 8,
    alignSelf: 'flex-start',
  },
  aiText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#F59E0B',
  },
  lockBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: '#FEF2F2',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 8,
    alignSelf: 'flex-start',
  },
  lockText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#DC2626',
  },
  capacityBar: {
    marginTop: 2,
  },
  capacityTrack: {
    height: 4,
    borderRadius: 2,
    backgroundColor: '#E5E7EB',
    overflow: 'hidden',
  },
  capacityFill: {
    height: '100%',
    borderRadius: 2,
  },
  actions: {
    marginTop: 18,
    marginBottom: 10,
  },
  // Modal
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.45)',
    justifyContent: 'flex-end',
  },
  modalSheet: {
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 24,
    gap: 12,
  },
  modalTitle: { fontSize: 18, fontWeight: '800', marginBottom: 4 },
  methodRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 14,
    borderRadius: 14,
    backgroundColor: '#F5F7FB',
  },
  methodRowSelected: {
    backgroundColor: '#EDE9FE',
    borderWidth: 1.5,
    borderColor: '#6C63FF',
  },
  methodIcon: { fontSize: 22 },
  methodLabel: { flex: 1, fontSize: 15, fontWeight: '600' },
  checkmark: { fontSize: 18, color: '#6C63FF', fontWeight: '800' },
  modalActions: { flexDirection: 'row', gap: 10, marginTop: 8 },
  cancelBtn: {
    flex: 1, padding: 14, borderRadius: 14,
    alignItems: 'center', backgroundColor: '#F5F7FB',
  },
  cancelLabel: { fontSize: 15, fontWeight: '700', color: '#6B7280' },
  payBtn: {
    flex: 2, padding: 14, borderRadius: 14,
    alignItems: 'center', backgroundColor: '#6C63FF',
  },
  payLabel: { fontSize: 15, fontWeight: '800', color: '#FFFFFF' },
  btnDisabled: { opacity: 0.6 },
});

import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';
import MaterialCommunityIcons from 'react-native-vector-icons/MaterialCommunityIcons';

import type { Slot } from '../services/slotService';

type SlotVisualStatus = 'available' | 'limited' | 'full' | 'locked';

function getSlotStatus(slot: Slot): SlotVisualStatus {
  if (slot.is_locked) return 'locked';
  const status = (slot.status ?? '').toLowerCase();
  if (status === 'full') return 'full';
  const available = Math.max((slot.max_orders ?? 0) - (slot.current_orders ?? 0), 0);
  if (available <= 0) return 'full';
  if (status === 'limited') return 'limited';
  return 'available';
}

const STATUS_COLORS: Record<SlotVisualStatus, string> = {
  available: '#059669',
  limited: '#D97706',
  full: '#9CA3AF',
  locked: '#DC2626',
};

export function SlotCard(props: {
  slot: Slot;
  selected: boolean;
  onPress: () => void;
}) {
  const { slot, selected, onPress } = props;
  const status = getSlotStatus(slot);
  const color = STATUS_COLORS[status];
  const isSelectable = status === 'available' || status === 'limited';
  const available = Math.max((slot.max_orders ?? 0) - (slot.current_orders ?? 0), 0);
  const queueSize = slot.queue_size ?? slot.current_orders ?? 0;
  const estimatedWait = slot.estimated_wait ?? queueSize * 3;

  const content = (
    <View style={[
      styles.card,
      { borderLeftColor: color, borderLeftWidth: 4 },
      selected && styles.cardSelected,
      !isSelectable && styles.cardDisabled,
    ]}>
      <View style={styles.rowBetween}>
        <Text style={styles.time} numberOfLines={1}>{formatRange(slot.start_time, slot.end_time)}</Text>
        <View style={[styles.statusBadge, { backgroundColor: color + '15' }]}>
          <Text style={[styles.statusText, { color }]}>{status.charAt(0).toUpperCase() + status.slice(1)}</Text>
        </View>
      </View>

      <View style={styles.metaRow}>
        <Text style={styles.meta}>{available} left</Text>
        <Text style={styles.meta}>~{estimatedWait} min</Text>
      </View>

      {/* Capacity bar */}
      <View style={styles.capacityTrack}>
        <View style={[styles.capacityFill, {
          width: `${Math.min(((slot.current_orders ?? 0) / Math.max(slot.max_orders ?? 1, 1)) * 100, 100)}%`,
          backgroundColor: color,
        }]} />
      </View>

      {slot.is_ai_recommended && isSelectable && (
        <Text style={styles.aiBadge}>AI Pick</Text>
      )}

      {slot.faculty_priority && (
        <Text style={styles.facultyBadge}>Faculty</Text>
      )}
    </View>
  );

  return (
    <Pressable onPress={onPress} disabled={!isSelectable} style={styles.pressable}>
      {content}
    </Pressable>
  );
}

function formatRange(start: string, end: string): string {
  const s = new Date(start);
  const e = new Date(end);
  return `${formatTime(s)} - ${formatTime(e)}`;
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

const styles = StyleSheet.create({
  pressable: {
    width: '48%',
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 14,
    shadowColor: 'rgba(0,0,0,0.08)',
    shadowOpacity: 0.08,
    shadowOffset: { width: 0, height: 3 },
    shadowRadius: 8,
    elevation: 4,
    gap: 6,
    minHeight: 110,
  },
  cardSelected: {
    borderWidth: 2,
    borderColor: '#6C63FF',
  },
  cardDisabled: {
    opacity: 0.5,
  },
  rowBetween: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  time: {
    fontSize: 15,
    fontWeight: '700',
    color: '#111827',
    flexWrap: 'nowrap',
  },
  statusBadge: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 8,
  },
  statusText: {
    fontSize: 10,
    fontWeight: '800',
  },
  metaRow: {
    flexDirection: 'row',
    gap: 10,
  },
  meta: {
    fontSize: 12,
    color: '#6B7280',
  },
  capacityTrack: {
    height: 3,
    borderRadius: 2,
    backgroundColor: '#E5E7EB',
    overflow: 'hidden',
    marginTop: 2,
  },
  capacityFill: {
    height: '100%',
    borderRadius: 2,
  },
  aiBadge: {
    fontSize: 10,
    fontWeight: '800',
    color: '#F59E0B',
  },
  facultyBadge: {
    fontSize: 10,
    fontWeight: '800',
    color: '#6C63FF',
  },
});

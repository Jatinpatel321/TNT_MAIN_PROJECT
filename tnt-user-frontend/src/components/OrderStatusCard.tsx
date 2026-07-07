import React from 'react';
import {StyleSheet, View} from 'react-native';
import {Text} from 'react-native-paper';

import {
  ORDER_STATUS_LABELS,
  ORDER_STATUS_COLORS,
} from '../services/orderService';

const STATUS_STEPS = [
  'placed',
  'confirmed',
  'preparing',
  'ready',
  'picked',
] as const;

export function OrderStatusCard(props: {
  status: string;
  vendorName: string;
  orderType: 'food' | 'stationery';
}) {
  const statusKey = (props.status || '').toLowerCase();
  const label = ORDER_STATUS_LABELS[statusKey] ?? props.status ?? 'Unknown';
  const color = ORDER_STATUS_COLORS[statusKey] ?? '#6B7280';
  const isCancelled = statusKey === 'cancelled';

  const currentStepIndex = STATUS_STEPS.indexOf(statusKey as any);

  return (
    <View style={[styles.card, isCancelled && styles.cancelledCard]}>
      <Text style={styles.caption}>Status</Text>
      <View style={styles.statusRow}>
        <View style={[styles.statusDot, {backgroundColor: color}]} />
        <Text
          style={[styles.title, {color: isCancelled ? '#EF4444' : '#111827'}]}>
          {label}
        </Text>
      </View>
      <Text style={styles.meta}>{props.vendorName}</Text>
      <Text style={styles.meta}>
        Order Type: {props.orderType === 'stationery' ? 'Stationery' : 'Food'}
      </Text>

      {!isCancelled && currentStepIndex >= 0 && (
        <View style={styles.progressBar}>
          {STATUS_STEPS.map((step, idx) => {
            const isActive = idx <= currentStepIndex;
            const stepColor = isActive
              ? idx === currentStepIndex
                ? color
                : '#10B981'
              : '#E5E7EB';
            return (
              <View key={step} style={styles.progressStep}>
                <View
                  style={[styles.progressDot, {backgroundColor: stepColor}]}
                />
                {idx < STATUS_STEPS.length - 1 && (
                  <View
                    style={[
                      styles.progressLine,
                      {
                        backgroundColor:
                          idx < currentStepIndex ? '#10B981' : '#E5E7EB',
                      },
                    ]}
                  />
                )}
              </View>
            );
          })}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 18,
    padding: 16,
    shadowColor: 'rgba(0,0,0,0.08)',
    shadowOpacity: 0.08,
    shadowOffset: {width: 0, height: 3},
    shadowRadius: 8,
    elevation: 4,
    gap: 6,
  },
  cancelledCard: {
    backgroundColor: '#FEF2F2',
    borderLeftWidth: 4,
    borderLeftColor: '#EF4444',
  },
  caption: {
    fontSize: 13,
    color: '#6B7280',
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  statusDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  title: {
    fontSize: 18,
    fontWeight: '800',
  },
  meta: {
    fontSize: 14,
    color: '#4B5563',
  },
  progressBar: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 12,
    paddingHorizontal: 4,
  },
  progressStep: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  progressDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  progressLine: {
    flex: 1,
    height: 2,
    marginHorizontal: 2,
  },
});

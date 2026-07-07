import React from 'react';
import {StyleSheet, View} from 'react-native';
import {Text} from 'react-native-paper';

import {
  ORDER_STATUS_LABELS,
  ORDER_STATUS_COLORS,
} from '../services/orderService';

export type TimelineItem = {
  status: string;
  changed_at: string;
};

export function OrderTimeline(props: {
  items: TimelineItem[];
  currentStatus?: string;
}) {
  return (
    <View style={styles.card}>
      <Text style={styles.title}>Timeline</Text>
      {props.items.length === 0 ? (
        <Text style={styles.muted}>No events yet.</Text>
      ) : (
        props.items.map((item, idx) => {
          const statusKey = (item.status || '').toLowerCase();
          const label = ORDER_STATUS_LABELS[statusKey] ?? item.status;
          const color = ORDER_STATUS_COLORS[statusKey] ?? '#6B7280';
          const isLast = idx === props.items.length - 1;
          const isCancelled = statusKey === 'cancelled';

          return (
            <View key={`${item.changed_at}-${idx}`} style={styles.step}>
              <View style={styles.lineCol}>
                <View style={[styles.dot, {backgroundColor: color}]} />
                {!isLast && (
                  <View
                    style={[
                      styles.connector,
                      isCancelled && styles.connectorCancelled,
                    ]}
                  />
                )}
              </View>
              <View style={styles.content}>
                <Text
                  style={[styles.label, isCancelled && styles.labelCancelled]}>
                  {label}
                </Text>
                <Text style={styles.time}>
                  {new Date(item.changed_at).toLocaleString()}
                </Text>
              </View>
            </View>
          );
        })
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
    gap: 4,
  },
  title: {
    fontSize: 16,
    fontWeight: '800',
    marginBottom: 8,
  },
  muted: {
    color: '#6B7280',
  },
  step: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
    minHeight: 44,
  },
  lineCol: {
    width: 16,
    alignItems: 'center',
  },
  dot: {
    width: 14,
    height: 14,
    borderRadius: 7,
    borderWidth: 2,
    borderColor: '#FFFFFF',
  },
  connector: {
    width: 2,
    flex: 1,
    backgroundColor: '#D1D5DB',
    marginVertical: 2,
  },
  connectorCancelled: {
    backgroundColor: '#FCA5A5',
  },
  content: {
    flex: 1,
    gap: 2,
    paddingTop: 0,
  },
  label: {
    fontSize: 14,
    fontWeight: '700',
    color: '#111827',
  },
  labelCancelled: {
    color: '#EF4444',
  },
  time: {
    fontSize: 12,
    color: '#6B7280',
  },
});

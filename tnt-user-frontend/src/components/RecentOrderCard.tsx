import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';
import type { Order } from '../types/models';

export function RecentOrderCard(props: { order: Order; vendorName: string; onPress: () => void }) {
  const { order, vendorName } = props;
  return (
    <Pressable style={styles.card} onPress={props.onPress}>
      <View style={styles.row}>
        <Text style={styles.name}>{vendorName}</Text>
        <Text style={styles.status}>{order.status}</Text>
      </View>
      <Text style={styles.time}>{new Date(order.created_at).toLocaleString()}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 18,
    padding: 14,
    marginBottom: 10,
    shadowColor: 'rgba(0,0,0,0.1)',
    shadowOpacity: 0.1,
    shadowOffset: { width: 0, height: 4 },
    shadowRadius: 8,
    elevation: 4,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  name: {
    fontSize: 16,
    fontWeight: '700',
  },
  status: {
    fontSize: 14,
    fontWeight: '700',
    color: '#6C63FF',
  },
  time: {
    marginTop: 6,
    fontSize: 14,
    color: '#6B7280',
  },
});

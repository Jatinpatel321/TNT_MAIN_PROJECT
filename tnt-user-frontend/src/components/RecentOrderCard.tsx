import React, { useMemo } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';
import type { Order } from '../types/models';
import { useAppTheme } from '../theme/ThemeContext';
import type { AppPalette } from '../theme/theme';

export function RecentOrderCard(props: { order: Order; vendorName: string; onPress: () => void }) {
  const { order, vendorName } = props;
  const { colors } = useAppTheme();
  const styles = useMemo(() => makeStyles(colors), [colors]);
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

const makeStyles = (colors: AppPalette) => StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: 18,
    padding: 14,
    marginBottom: 10,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
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
    color: colors.text,
  },
  status: {
    fontSize: 14,
    fontWeight: '700',
    color: colors.primary,
  },
  time: {
    marginTop: 6,
    fontSize: 14,
    color: colors.muted,
  },
});

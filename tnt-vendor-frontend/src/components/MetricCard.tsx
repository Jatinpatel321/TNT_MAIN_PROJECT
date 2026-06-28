import React from 'react';
import { View, Text, StyleSheet, ViewStyle } from 'react-native';
import { Colors, Typography, BorderRadius, Shadows, Spacing } from '../theme';

interface MetricCardProps {
  value: string | number;
  label: string;
  icon?: string;
  color?: string;
  trend?: { value: number; isUp: boolean };
  style?: ViewStyle;
  size?: 'sm' | 'md';
}

export default function MetricCard({
  value,
  label,
  icon,
  color = Colors.primary,
  trend,
  style,
  size = 'md',
}: MetricCardProps) {
  const isSmall = size === 'sm';

  return (
    <View style={[styles.card, style]}>
      {icon && (
        <View style={[styles.iconCircle, { backgroundColor: color + '18' }]}>
          <Text style={[styles.icon, isSmall && styles.smallIcon]}>{icon}</Text>
        </View>
      )}
      <Text style={[styles.value, { color }, isSmall && styles.smallValue]}>
        {value}
      </Text>
      <Text style={[styles.label, isSmall && styles.smallLabel]}>{label}</Text>
      {trend && (
        <View style={styles.trendRow}>
          <Text style={[styles.trendArrow, { color: trend.isUp ? Colors.success : Colors.error }]}>
            {trend.isUp ? '↑' : '↓'}
          </Text>
          <Text style={[styles.trendValue, { color: trend.isUp ? Colors.success : Colors.error }]}>
            {Math.abs(trend.value)}%
          </Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: Colors.bgCard,
    borderRadius: BorderRadius.lg,
    padding: Spacing.lg,
    alignItems: 'center',
    minWidth: '45%',
    ...Shadows.card,
  },
  iconCircle: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: Spacing.sm,
  },
  icon: {
    fontSize: 20,
  },
  smallIcon: {
    fontSize: 16,
  },
  value: {
    fontSize: Typography.h2,
    fontWeight: Typography.bold,
    marginBottom: 2,
  },
  smallValue: {
    fontSize: Typography.h4,
  },
  label: {
    fontSize: Typography.caption,
    color: Colors.textMuted,
    textAlign: 'center',
    fontWeight: Typography.medium,
  },
  smallLabel: {
    fontSize: Typography.tiny,
  },
  trendRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: Spacing.xs,
    gap: 2,
  },
  trendArrow: {
    fontSize: 12,
    fontWeight: Typography.bold,
  },
  trendValue: {
    fontSize: Typography.caption,
    fontWeight: Typography.semibold,
  },
});

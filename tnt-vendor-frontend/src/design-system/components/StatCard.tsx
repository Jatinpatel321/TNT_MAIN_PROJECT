// ─── StatCard ───────────────────────────────────────────────────────
// Premium animated metric card with trend indicator

import React from 'react';
import { View, Text, StyleSheet, ViewStyle } from 'react-native';
import colors from '../tokens/colors';
import shadows from '../tokens/shadows';
import AnimatedCounter from './AnimatedCounter';

interface StatCardProps {
  value: number;
  label: string;
  prefix?: string;
  suffix?: string;
  icon?: string;
  color?: string;
  trend?: { value: number; isUp: boolean };
  format?: 'number' | 'currency' | 'percent';
  size?: 'sm' | 'md' | 'lg';
  style?: ViewStyle;
  onPress?: () => void;
}

export default function StatCard({
  value,
  label,
  prefix = '',
  suffix = '',
  icon,
  color = colors.primary,
  trend,
  format = 'number',
  size = 'md',
  style,
}: StatCardProps) {
  const isSmall = size === 'sm';
  const isLarge = size === 'lg';

  return (
    <View
      style={[
        styles.card,
        isSmall && styles.small,
        isLarge && styles.large,
        style,
      ]}
    >
      {/* Colored top accent bar */}
      <View style={[styles.accentBar, { backgroundColor: color }]} />

      {icon && (
        <View style={[styles.iconCircle, { backgroundColor: color + '15' }]}>
          <Text style={[styles.icon, isSmall && styles.smallIcon]}>{icon}</Text>
        </View>
      )}

      <AnimatedCounter
        value={value}
        prefix={prefix}
        suffix={suffix}
        fontSize={isSmall ? 24 : isLarge ? 36 : 32}
        color={color}
        format={format}
      />

      <Text style={[styles.label, isSmall && styles.smallLabel]}>{label}</Text>

      {trend && (
        <View style={styles.trendRow}>
          <View
            style={[
              styles.trendIndicator,
              {
                backgroundColor: trend.isUp ? colors.successPale : colors.errorPale,
              },
            ]}
          >
            <Text
              style={[
                styles.trendArrow,
                { color: trend.isUp ? colors.success : colors.error },
              ]}
            >
              {trend.isUp ? '↑' : '↓'}
            </Text>
            <Text
              style={[
                styles.trendValue,
                { color: trend.isUp ? colors.success : colors.error },
              ]}
            >
              {Math.abs(trend.value)}%
            </Text>
          </View>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.bgCard,
    borderRadius: 20,
    padding: 16,
    alignItems: 'center',
    overflow: 'hidden',
    ...shadows.card,
  },
  small: {
    padding: 12,
    borderRadius: 16,
  },
  large: {
    padding: 20,
    borderRadius: 24,
  },
  accentBar: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: 3,
  },
  iconCircle: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 8,
  },
  icon: {
    fontSize: 20,
  },
  smallIcon: {
    fontSize: 16,
  },
  label: {
    fontSize: 12,
    color: colors.textMuted,
    textAlign: 'center',
    fontWeight: '600',
    marginTop: 4,
  },
  smallLabel: {
    fontSize: 10,
  },
  trendRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 8,
  },
  trendIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 20,
    gap: 4,
  },
  trendArrow: {
    fontSize: 12,
    fontWeight: '700',
  },
  trendValue: {
    fontSize: 12,
    fontWeight: '600',
  },
});

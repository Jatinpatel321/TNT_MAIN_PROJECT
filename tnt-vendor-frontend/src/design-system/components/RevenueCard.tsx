// ─── RevenueCard ──────────────────────────────────────────────────
// Premium revenue display card with chart preview and trend

import React from 'react';
import { View, Text, StyleSheet, ViewStyle } from 'react-native';
import colors from '../tokens/colors';
import shadows from '../tokens/shadows';
import AnimatedCounter from './AnimatedCounter';

interface RevenueDataPoint {
  value: number;
  label: string;
}

interface RevenueCardProps {
  title: string;
  amount: number;
  subtitle?: string;
  data?: RevenueDataPoint[];
  trend?: { value: number; isUp: boolean };
  format?: 'currency' | 'number' | 'percent';
  color?: string;
  style?: ViewStyle;
  icon?: string;
}

export default function RevenueCard({
  title,
  amount,
  subtitle,
  data,
  trend,
  format = 'currency',
  color = colors.primary,
  style,
  icon = '💰',
}: RevenueCardProps) {
  const maxValue = data ? Math.max(...data.map(d => d.value), 1) : 1;

  return (
    <View style={[styles.card, style]}>
      <View style={[styles.accentBar, { backgroundColor: color }]} />
      <View style={styles.header}>
        <Text style={styles.icon}>{icon}</Text>
        <View style={styles.headerText}>
          <Text style={styles.title}>{title}</Text>
          {subtitle && <Text style={styles.subtitle}>{subtitle}</Text>}
        </View>
        {trend && (
          <View style={[styles.trendBadge, { backgroundColor: trend.isUp ? colors.successPale : colors.errorPale }]}>
            <Text style={[styles.trendArrow, { color: trend.isUp ? colors.success : colors.error }]}>
              {trend.isUp ? '↑' : '↓'}
            </Text>
            <Text style={[styles.trendValue, { color: trend.isUp ? colors.success : colors.error }]}>
              {Math.abs(trend.value)}%
            </Text>
          </View>
        )}
      </View>

      <AnimatedCounter
        value={amount}
        prefix="₹"
        fontSize={32}
        color={color}
        format={format}
      />

      {data && data.length > 0 && (
        <View style={styles.chartContainer}>
          <View style={styles.chart}>
            {data.map((point, index) => {
              const height = (point.value / maxValue) * 60;
              const isLast = index === data.length - 1;
              return (
                <View key={index} style={styles.barCol}>
                  <View style={styles.barWrapper}>
                    <View
                      style={[
                        styles.bar,
                        {
                          height: Math.max(height, 4),
                          backgroundColor: isLast ? color : `${color}50`,
                          borderTopLeftRadius: index === 0 ? 6 : 3,
                          borderTopRightRadius: index === data.length - 1 ? 6 : 3,
                        },
                      ]}
                    />
                  </View>
                  <Text style={[styles.barLabel, isLast && { color, fontWeight: '700' }]}>
                    {point.label}
                  </Text>
                </View>
              );
            })}
          </View>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.bgCard,
    borderRadius: 24,
    padding: 20,
    overflow: 'hidden',
    ...shadows.card,
  },
  accentBar: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: 3,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 12,
    gap: 10,
  },
  icon: { fontSize: 22 },
  headerText: { flex: 1 },
  title: {
    fontSize: 15,
    fontWeight: '600',
    color: colors.textSecondary,
  },
  subtitle: {
    fontSize: 12,
    color: colors.textMuted,
    marginTop: 2,
  },
  trendBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 20,
    gap: 4,
  },
  trendArrow: { fontSize: 12, fontWeight: '700' },
  trendValue: { fontSize: 11, fontWeight: '600' },
  chartContainer: {
    marginTop: 16,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: colors.borderLight,
  },
  chart: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'space-between',
    height: 80,
  },
  barCol: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'flex-end',
    marginHorizontal: 2,
  },
  barWrapper: {
    width: '100%',
    height: 64,
    justifyContent: 'flex-end',
    alignItems: 'center',
  },
  bar: {
    width: '70%',
    minHeight: 4,
    borderRadius: 3,
  },
  barLabel: {
    fontSize: 9,
    color: colors.textMuted,
    fontWeight: '600',
    marginTop: 4,
  },
});

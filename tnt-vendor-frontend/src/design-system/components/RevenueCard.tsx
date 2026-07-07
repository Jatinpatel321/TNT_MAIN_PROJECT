// ─── RevenueCard ──────────────────────────────────────────────────
// Premium revenue display card with chart preview and trend

import React from 'react';
import { View, Text, StyleSheet, ViewStyle } from 'react-native';
import { useTheme } from '../../context/ThemeContext';
import staticColors from '../tokens/colors';
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
  color,
  style,
  icon = '💰',
}: RevenueCardProps) {
  const { colors: themeColors } = useTheme();
  const activeColor = color || themeColors.primary;
  const maxValue = data ? Math.max(...data.map(d => d.value), 1) : 1;

  return (
    <View style={[styles.card, { backgroundColor: themeColors.bgCard }, style]}>
      <View style={[styles.accentBar, { backgroundColor: activeColor }]} />
      <View style={styles.header}>
        <Text style={styles.icon}>{icon}</Text>
        <View style={styles.headerText}>
          <Text style={[styles.title, { color: themeColors.textSecondary }]}>{title}</Text>
          {subtitle && <Text style={[styles.subtitle, { color: themeColors.textMuted }]}>{subtitle}</Text>}
        </View>
        {trend && (
          <View style={[styles.trendBadge, { backgroundColor: trend.isUp ? themeColors.successPale : themeColors.errorPale }]}>
            <Text style={[styles.trendArrow, { color: trend.isUp ? themeColors.success : themeColors.error }]}>
              {trend.isUp ? '↑' : '↓'}
            </Text>
            <Text style={[styles.trendValue, { color: trend.isUp ? themeColors.success : themeColors.error }]}>
              {Math.abs(trend.value)}%
            </Text>
          </View>
        )}
      </View>

      <AnimatedCounter
        value={amount}
        prefix="₹"
        fontSize={32}
        color={activeColor}
        format={format}
      />

      {data && data.length > 0 && (
        <View style={[styles.chartContainer, { borderTopColor: themeColors.borderLight }]}>
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
                          backgroundColor: isLast ? activeColor : `${activeColor}50`,
                          borderTopLeftRadius: index === 0 ? 6 : 3,
                          borderTopRightRadius: index === data.length - 1 ? 6 : 3,
                        },
                      ]}
                    />
                  </View>
                  <Text style={[styles.barLabel, { color: themeColors.textMuted }, isLast && { color: activeColor, fontWeight: '700' }]}>
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

const colors = staticColors;

const styles = StyleSheet.create({
  card: {
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
  },
  subtitle: {
    fontSize: 12,
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
    fontWeight: '600',
    marginTop: 4,
  },
});


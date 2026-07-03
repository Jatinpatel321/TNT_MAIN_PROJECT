// ─── ForecastCard ──────────────────────────────────────────────────
// Premium demand/weather/forecast insight card with trend visualization

import React from 'react';
import { View, Text, StyleSheet, ViewStyle } from 'react-native';
import colors from '../tokens/colors';
import shadows from '../tokens/shadows';

interface ForecastData {
  label: string;
  value: number;
  unit?: string;
  trend?: 'up' | 'down' | 'stable';
  confidence?: number;
}

interface ForecastCardProps {
  title: string;
  icon: string;
  data: ForecastData[];
  color?: string;
  style?: ViewStyle;
  children?: React.ReactNode;
}

const trendConfig = {
  up: { symbol: '↑', color: colors.success },
  down: { symbol: '↓', color: colors.error },
  stable: { symbol: '→', color: colors.textMuted },
};

export default function ForecastCard({
  title,
  icon,
  data,
  color = colors.primary,
  style,
  children,
}: ForecastCardProps) {
  return (
    <View style={[styles.card, style]}>
      <View style={[styles.accentBar, { backgroundColor: color }]} />
      <View style={styles.header}>
        <Text style={styles.icon}>{icon}</Text>
        <Text style={styles.title}>{title}</Text>
      </View>
      <View style={styles.dataGrid}>
        {data.map((item, index) => {
          const trend = item.trend ? trendConfig[item.trend] : null;
          return (
            <View key={index} style={styles.dataItem}>
              <Text style={styles.dataValue}>
                {item.value}
                {item.unit && <Text style={styles.dataUnit}> {item.unit}</Text>}
              </Text>
              <View style={styles.dataMeta}>
                <Text style={styles.dataLabel}>{item.label}</Text>
                {trend && (
                  <Text style={[styles.dataTrend, { color: trend.color }]}>
                    {trend.symbol}
                  </Text>
                )}
              </View>
              {item.confidence !== undefined && (
                <View style={styles.confidenceRow}>
                  <View style={styles.confidenceTrack}>
                    <View
                      style={[
                        styles.confidenceFill,
                        {
                          width: `${item.confidence * 100}%`,
                          backgroundColor: color,
                        },
                      ]}
                    />
                  </View>
                  <Text style={styles.confidenceLabel}>
                    {Math.round(item.confidence * 100)}%
                  </Text>
                </View>
              )}
            </View>
          );
        })}
      </View>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.bgCard,
    borderRadius: 20,
    padding: 18,
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
    alignItems: 'center',
    marginBottom: 14,
    gap: 8,
  },
  icon: { fontSize: 20 },
  title: {
    fontSize: 15,
    fontWeight: '700',
    color: colors.textPrimary,
    flex: 1,
  },
  dataGrid: { gap: 12 },
  dataItem: {
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderLight,
  },
  dataValue: {
    fontSize: 22,
    fontWeight: '700',
    color: colors.textPrimary,
    fontVariant: ['tabular-nums'],
  },
  dataUnit: {
    fontSize: 13,
    fontWeight: '500',
    color: colors.textMuted,
  },
  dataMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 2,
  },
  dataLabel: {
    fontSize: 12,
    color: colors.textSecondary,
    fontWeight: '500',
  },
  dataTrend: {
    fontSize: 14,
    fontWeight: '700',
  },
  confidenceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 4,
  },
  confidenceTrack: {
    flex: 1,
    height: 4,
    backgroundColor: colors.bgTertiary,
    borderRadius: 2,
    overflow: 'hidden',
  },
  confidenceFill: {
    height: '100%',
    borderRadius: 2,
  },
  confidenceLabel: {
    fontSize: 10,
    color: colors.textMuted,
    fontWeight: '600',
    width: 32,
    textAlign: 'right',
  },
});

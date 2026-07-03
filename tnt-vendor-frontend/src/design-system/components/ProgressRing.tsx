// ─── ProgressRing ────────────────────────────────────────────────────
// Circular progress indicator with gradient

import React from 'react';
import { View, StyleSheet, Text } from 'react-native';
import colors from '../tokens/colors';

interface ProgressRingProps {
  progress: number; // 0-100
  size?: number;
  strokeWidth?: number;
  color?: string;
  bgColor?: string;
  label?: string;
  showPercentage?: boolean;
  children?: React.ReactNode;
}

export default function ProgressRing({
  progress,
  size = 80,
  strokeWidth = 6,
  color = colors.primary,
  bgColor = colors.bgTertiary,
  label,
  showPercentage = true,
  children,
}: ProgressRingProps) {
  const clampedProgress = Math.min(100, Math.max(0, progress));
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progressOffset = circumference - (clampedProgress / 100) * circumference;

  return (
    <View style={[styles.container, { width: size, height: size }]}>
      {/* Background Circle */}
      <View
        style={[
          styles.circle,
          {
            width: size,
            height: size,
            borderRadius: size / 2,
            borderWidth: strokeWidth,
            borderColor: bgColor,
          },
        ]}
      />
      {/* Progress Arc */}
      <View
        style={[
          styles.progress,
          {
            width: size,
            height: size,
            borderRadius: size / 2,
            borderWidth: strokeWidth,
            borderColor: 'transparent',
            borderTopColor: color,
            borderRightColor: clampedProgress > 25 ? color : 'transparent',
            borderBottomColor: clampedProgress > 50 ? color : 'transparent',
            borderLeftColor: clampedProgress > 75 ? color : 'transparent',
            transform: [{ rotate: '-45deg' }],
          },
        ]}
      />
      {/* Center Content */}
      <View style={styles.center}>
        {children ? (
          children
        ) : showPercentage ? (
          <Text style={[styles.percentage, { color, fontSize: size * 0.2 }]}>
            {Math.round(clampedProgress)}%
          </Text>
        ) : null}
        {label && (
          <Text style={[styles.label, { fontSize: size * 0.1 }]}>{label}</Text>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  circle: {
    position: 'absolute',
  },
  progress: {
    position: 'absolute',
  },
  center: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  percentage: {
    fontWeight: '700',
    fontVariant: ['tabular-nums'],
  },
  label: {
    color: colors.textMuted,
    fontWeight: '500',
    marginTop: 2,
  },
});


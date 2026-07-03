// ─── GlassCard ──────────────────────────────────────────────────────
// Premium frosted glass effect card

import React from 'react';
import { View, StyleSheet, ViewStyle } from 'react-native';
import colors from '../tokens/colors';
import shadows from '../tokens/shadows';

interface GlassCardProps {
  children: React.ReactNode;
  style?: ViewStyle;
  intensity?: 'light' | 'medium' | 'heavy';
  blur?: number;
  padding?: number;
  borderRadius?: number;
}

export default function GlassCard({
  children,
  style,
  intensity = 'light',
  padding = 20,
  borderRadius = 20,
}: GlassCardProps) {
  const opacityMap = {
    light: 0.7,
    medium: 0.8,
    heavy: 0.9,
  };

  return (
    <View
      style={[
        styles.card,
        {
          padding,
          borderRadius,
          backgroundColor: `rgba(255, 255, 255, ${opacityMap[intensity]})`,
        },
        shadows.glass,
        style,
      ]}
    >
      {/* Frosted overlay */}
      <View
        style={[
          styles.frost,
          {
            borderRadius,
            opacity: intensity === 'heavy' ? 0.15 : 0.08,
          },
        ]}
      />
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderColor: colors.glassBorder,
    overflow: 'hidden',
  },
  frost: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: '#FFFFFF',
  },
});


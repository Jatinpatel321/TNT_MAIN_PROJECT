// ─── GlassCard ──────────────────────────────────────────────────────
// Premium frosted glass effect card

import React from 'react';
import { View, StyleSheet, ViewStyle } from 'react-native';
import colors from '../tokens/colors';
import shadows from '../tokens/shadows';

import { useTheme } from '../../context/ThemeContext';

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
  const { colors, isDark } = useTheme();
  
  const opacityMap = {
    light: isDark ? 0.45 : 0.7,
    medium: isDark ? 0.65 : 0.8,
    heavy: isDark ? 0.85 : 0.9,
  };

  return (
    <View
      style={[
        styles.card,
        {
          padding,
          borderRadius,
          backgroundColor: isDark
            ? `rgba(26, 26, 46, ${opacityMap[intensity]})`
            : `rgba(255, 255, 255, ${opacityMap[intensity]})`,
          borderColor: colors.glassBorder,
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
            backgroundColor: isDark ? '#1A1A2E' : '#FFFFFF',
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
    overflow: 'hidden',
  },
  frost: {
    ...StyleSheet.absoluteFillObject,
  },
});


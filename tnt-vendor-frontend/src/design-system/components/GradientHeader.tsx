// ─── GradientHeader ────────────────────────────────────────────────
// Premium gradient header with decorative elements

import React from 'react';
import { View, Text, StyleSheet, ViewStyle } from 'react-native';
import colors from '../tokens/colors';
import shadows from '../tokens/shadows';
import spacing from '../tokens/spacing';

interface GradientHeaderProps {
  title: string;
  subtitle?: string;
  rightElement?: React.ReactNode;
  gradientColors?: string[];
  style?: ViewStyle;
  height?: number;
}

export default function GradientHeader({
  title,
  subtitle,
  rightElement,
  style,
  height = 140,
}: GradientHeaderProps) {
  return (
    <View style={[styles.header, { height }, style]}>
      {/* Decorative circles */}
      <View style={[styles.deco, styles.deco1]} />
      <View style={[styles.deco, styles.deco2]} />
      <View style={[styles.deco, styles.deco3]} />

      <View style={styles.content}>
        <View style={styles.left}>
          <Text style={styles.title}>{title}</Text>
          {subtitle && <Text style={styles.subtitle}>{subtitle}</Text>}
        </View>
        {rightElement && <View style={styles.right}>{rightElement}</View>}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    backgroundColor: colors.primary,
    paddingTop: spacing.huge,
    paddingBottom: spacing.xxl,
    paddingHorizontal: spacing.xl,
    borderBottomLeftRadius: 24,
    borderBottomRightRadius: 24,
    overflow: 'hidden',
    ...shadows.header,
  },
  deco: {
    position: 'absolute',
    borderRadius: 999,
  },
  deco1: {
    top: -30,
    right: -20,
    width: 140,
    height: 140,
    backgroundColor: 'rgba(255,255,255,0.08)',
  },
  deco2: {
    bottom: -25,
    left: -40,
    width: 100,
    height: 100,
    backgroundColor: 'rgba(255,255,255,0.05)',
  },
  deco3: {
    top: 20,
    right: 80,
    width: 60,
    height: 60,
    backgroundColor: 'rgba(255,255,255,0.06)',
  },
  content: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
    flex: 1,
  },
  left: {
    flex: 1,
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    color: colors.textInverse,
    letterSpacing: -0.3,
  },
  subtitle: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.7)',
    marginTop: 4,
    fontWeight: '500',
  },
  right: {
    marginLeft: spacing.md,
  },
});


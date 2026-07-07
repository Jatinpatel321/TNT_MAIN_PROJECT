// ─── StatusPill ─────────────────────────────────────────────────────
// Animated status badge with icon, color, and pulse effect

import React, { useEffect, useRef } from 'react';
import { View, Text, StyleSheet, Animated, ViewStyle } from 'react-native';
import colors from '../tokens/colors';
import shadows from '../tokens/shadows';

interface StatusPillProps {
  label: string;
  variant?: 'primary' | 'success' | 'warning' | 'error' | 'info' | 'neutral' | 'purple';
  icon?: string;
  size?: 'sm' | 'md' | 'lg';
  animated?: boolean;
  style?: ViewStyle;
  outline?: boolean;
}

import { useTheme } from '../../context/ThemeContext';

export default function StatusPill({
  label,
  variant = 'primary',
  icon,
  size = 'md',
  animated = false,
  style,
  outline = false,
}: StatusPillProps) {
  const { colors } = useTheme();
  
  const variantColors: Record<string, { bg: string; text: string; dot: string }> = {
    primary: { bg: colors.primaryPale, text: colors.primary, dot: colors.primary },
    success: { bg: colors.successPale, text: colors.successDark, dot: colors.success },
    warning: { bg: colors.warningPale, text: colors.warningDark, dot: colors.warning },
    error: { bg: colors.errorPale, text: colors.errorDark, dot: colors.error },
    info: { bg: colors.infoPale, text: colors.info, dot: colors.info },
    neutral: { bg: colors.bgTertiary, text: colors.textSecondary, dot: colors.textMuted },
    purple: { bg: colors.secondaryPale, text: colors.secondary, dot: colors.secondary },
  };

  const pulseAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    if (!animated) return;
    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 0.3,
          duration: 1200,
          useNativeDriver: true,
        }),
        Animated.timing(pulseAnim, {
          toValue: 1,
          duration: 1200,
          useNativeDriver: true,
        }),
      ]),
    );
    pulse.start();
    return () => pulse.stop();
  }, [animated, pulseAnim]);

  const colors_ = variantColors[variant] || variantColors.primary;
  const isSmall = size === 'sm';
  const isLarge = size === 'lg';

  return (
    <View
      style={[
        styles.pill,
        isSmall && styles.sm,
        isLarge && styles.lg,
        outline
          ? { backgroundColor: 'transparent', borderWidth: 1.5, borderColor: colors_.bg }
          : { backgroundColor: colors_.bg },
        style,
      ]}
    >
      {animated ? (
        <Animated.View
          style={[
            styles.dot,
            { backgroundColor: colors_.dot, opacity: pulseAnim },
          ]}
        />
      ) : (
        <View style={[styles.dot, { backgroundColor: colors_.dot }]} />
      )}
      {icon && <Text style={[styles.icon, isSmall && styles.smIcon]}>{icon}</Text>}
      <Text
        style={[
          styles.label,
          { color: colors_.text },
          isSmall && styles.smLabel,
          isLarge && styles.lgLabel,
        ]}
      >
        {label.toUpperCase()}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pill: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 100,
    gap: 6,
    ...shadows.sm,
  },
  sm: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 100,
    gap: 4,
  },
  lg: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 100,
    gap: 8,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  icon: {
    fontSize: 12,
  },
  smIcon: {
    fontSize: 10,
  },
  label: {
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.8,
  },
  smLabel: {
    fontSize: 9,
    letterSpacing: 0.5,
  },
  lgLabel: {
    fontSize: 13,
    letterSpacing: 1,
  },
});


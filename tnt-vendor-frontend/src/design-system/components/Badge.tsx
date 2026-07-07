// ─── Badge ─────────────────────────────────────────────────────────
// Premium badge with icons, colors, and size variants

import React from 'react';
import { View, Text, StyleSheet, ViewStyle } from 'react-native';
import colors from '../tokens/colors';

interface BadgeProps {
  label: string;
  icon?: string;
  variant?: 'primary' | 'success' | 'warning' | 'error' | 'info' | 'neutral' | 'premium';
  size?: 'sm' | 'md' | 'lg';
  outline?: boolean;
  style?: ViewStyle;
}

const variantConfig: Record<string, { bg: string; text: string; border: string }> = {
  primary: { bg: colors.primaryPale, text: colors.primary, border: colors.primary },
  success: { bg: colors.successPale, text: colors.successDark, border: colors.success },
  warning: { bg: colors.warningPale, text: colors.warningDark, border: colors.warning },
  error: { bg: colors.errorPale, text: colors.errorDark, border: colors.error },
  info: { bg: colors.infoPale, text: colors.info, border: colors.info },
  neutral: { bg: colors.bgTertiary, text: colors.textSecondary, border: colors.border },
  premium: { bg: colors.secondaryPale, text: colors.secondary, border: colors.secondary },
};

export default function Badge({
  label,
  icon,
  variant = 'primary',
  size = 'md',
  outline = false,
  style,
}: BadgeProps) {
  const config = variantConfig[variant];
  const isSmall = size === 'sm';
  const isLarge = size === 'lg';

  return (
    <View
      style={[
        styles.badge,
        isSmall && styles.sm,
        isLarge && styles.lg,
        outline
          ? { backgroundColor: 'transparent', borderWidth: 1.5, borderColor: config.border }
          : { backgroundColor: config.bg },
        style,
      ]}
    >
      {icon && <Text style={[styles.icon, isSmall && styles.smIcon]}>{icon}</Text>}
      <Text style={[styles.label, { color: config.text }, isSmall && styles.smLabel, isLarge && styles.lgLabel]}>
        {label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 8,
    gap: 4,
  },
  sm: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 6,
    gap: 3,
  },
  lg: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 10,
    gap: 6,
  },
  icon: {
    fontSize: 12,
  },
  smIcon: {
    fontSize: 10,
  },
  label: {
    fontSize: 12,
    fontWeight: '600',
  },
  smLabel: {
    fontSize: 10,
  },
  lgLabel: {
    fontSize: 14,
  },
});

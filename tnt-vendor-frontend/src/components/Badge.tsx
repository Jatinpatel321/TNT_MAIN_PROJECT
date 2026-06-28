import React from 'react';
import { View, Text, StyleSheet, ViewStyle } from 'react-native';
import { Colors, Typography, BorderRadius, Spacing } from '../theme';

interface BadgeProps {
  label: string;
  variant?: 'primary' | 'success' | 'warning' | 'error' | 'info' | 'neutral';
  size?: 'sm' | 'md';
  icon?: string;
  style?: ViewStyle;
}

export default function Badge({ label, variant = 'primary', size = 'md', icon, style }: BadgeProps) {
  const bgColor = variantColors[variant] || Colors.primary;
  const textColor = variant === 'neutral' ? Colors.textPrimary : Colors.textInverse;

  return (
    <View style={[styles.badge, { backgroundColor: bgColor }, size === 'sm' && styles.sm, style]}>
      {icon && <Text style={[styles.icon, { color: textColor }]}>{icon}</Text>}
      <Text style={[styles.label, size === 'sm' && styles.smLabel, { color: textColor }]}>
        {label.toUpperCase()}
      </Text>
    </View>
  );
}

const variantColors: Record<string, string> = {
  primary: Colors.primary,
  success: Colors.success,
  warning: Colors.warning,
  error: Colors.error,
  info: Colors.info,
  neutral: Colors.bgTertiary,
};

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs + 2,
    borderRadius: BorderRadius.full,
  },
  sm: {
    paddingHorizontal: Spacing.sm + 2,
    paddingVertical: 2,
  },
  icon: {
    fontSize: 12,
    marginRight: 4,
  },
  label: {
    fontSize: Typography.caption,
    fontWeight: Typography.semibold,
    letterSpacing: 0.3,
  },
  smLabel: {
    fontSize: Typography.tiny,
  },
});

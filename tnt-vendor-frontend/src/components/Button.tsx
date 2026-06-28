import React from 'react';
import { TouchableOpacity, Text, StyleSheet, ActivityIndicator, ViewStyle } from 'react-native';
import { Colors, Typography, BorderRadius, Shadows, Spacing } from '../theme';

interface ButtonProps {
  title: string;
  onPress: () => void;
  variant?: 'primary' | 'secondary' | 'danger' | 'outline' | 'ghost' | 'success';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  disabled?: boolean;
  icon?: string;
  style?: ViewStyle;
  fullWidth?: boolean;
}

export default function Button({
  title,
  onPress,
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  icon,
  style,
  fullWidth = false,
}: ButtonProps) {
  const isDisabled = loading || disabled;

  return (
    <TouchableOpacity
      style={[
        styles.base,
        styles[variant],
        styles[`size_${size}`],
        fullWidth && styles.fullWidth,
        isDisabled && styles.disabled,
        style,
      ]}
      onPress={onPress}
      disabled={isDisabled}
      activeOpacity={0.8}
    >
      {loading ? (
        <ActivityIndicator
          size="small"
          color={variant === 'outline' || variant === 'ghost' ? Colors.primary : Colors.textInverse}
        />
      ) : (
        <>
          {icon && <Text style={[styles.icon, styles[`icon_${variant}`]]}>{icon}</Text>}
          <Text style={[styles.text, styles[`text_${variant}`], styles[`textSize_${size}`]]}>
            {title}
          </Text>
        </>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  base: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: BorderRadius.md,
    gap: Spacing.sm,
    ...Shadows.button,
  },
  fullWidth: {
    width: '100%',
  },
  disabled: {
    opacity: 0.5,
  },
  // Variants
  primary: {
    backgroundColor: Colors.primary,
  },
  secondary: {
    backgroundColor: Colors.secondary,
  },
  danger: {
    backgroundColor: Colors.error,
  },
  success: {
    backgroundColor: Colors.success,
  },
  outline: {
    backgroundColor: 'transparent',
    borderWidth: 1.5,
    borderColor: Colors.primary,
    shadowOpacity: 0,
    elevation: 0,
  },
  ghost: {
    backgroundColor: 'transparent',
    shadowOpacity: 0,
    elevation: 0,
  },
  // Sizes
  size_sm: {
    paddingVertical: Spacing.sm,
    paddingHorizontal: Spacing.lg,
  },
  size_md: {
    paddingVertical: Spacing.md + 2,
    paddingHorizontal: Spacing.xl,
  },
  size_lg: {
    paddingVertical: Spacing.lg,
    paddingHorizontal: Spacing.xxl,
  },
  // Text
  text: {
    fontWeight: Typography.semibold,
    textAlign: 'center',
  },
  text_primary: { color: Colors.textInverse },
  text_secondary: { color: Colors.textInverse },
  text_danger: { color: Colors.textInverse },
  text_success: { color: Colors.textInverse },
  text_outline: { color: Colors.primary },
  text_ghost: { color: Colors.primary },
  textSize_sm: { fontSize: Typography.bodySmall },
  textSize_md: { fontSize: Typography.body },
  textSize_lg: { fontSize: Typography.h4 },
  icon: { fontSize: 18 },
  icon_primary: { color: Colors.textInverse },
  icon_secondary: { color: Colors.textInverse },
  icon_danger: { color: Colors.textInverse },
  icon_success: { color: Colors.textInverse },
  icon_outline: { color: Colors.primary },
  icon_ghost: { color: Colors.primary },
});

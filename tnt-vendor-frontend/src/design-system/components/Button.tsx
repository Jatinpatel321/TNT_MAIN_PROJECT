// ─── Button ────────────────────────────────────────────────────────
// Premium button with loading state, icons, gradients, and variants

import React, { useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  Animated,
  ViewStyle,
  TextStyle,
} from 'react-native';
import colors from '../tokens/colors';
import shadows from '../tokens/shadows';

interface ButtonProps {
  title: string;
  onPress: () => void;
  variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  icon?: string;
  iconPosition?: 'left' | 'right';
  loading?: boolean;
  disabled?: boolean;
  fullWidth?: boolean;
  style?: ViewStyle;
  textStyle?: TextStyle;
}

const variantStyles: Record<string, { bg: string; text: string; border?: string }> = {
  primary: { bg: colors.primary, text: colors.textInverse },
  secondary: { bg: colors.secondary, text: colors.textInverse },
  success: { bg: colors.success, text: colors.textInverse },
  warning: { bg: colors.warning, text: colors.textInverse },
  danger: { bg: colors.error, text: colors.textInverse },
  outline: { bg: 'transparent', text: colors.primary, border: colors.primary },
  ghost: { bg: 'transparent', text: colors.primary },
};

const sizeStyles: Record<string, { paddingV: number; paddingH: number; fontSize: number; iconSize: number; borderRadius: number }> = {
  sm: { paddingV: 8, paddingH: 16, fontSize: 13, iconSize: 16, borderRadius: 10 },
  md: { paddingV: 14, paddingH: 24, fontSize: 15, iconSize: 18, borderRadius: 14 },
  lg: { paddingV: 18, paddingH: 32, fontSize: 17, iconSize: 22, borderRadius: 18 },
};

export default function Button({
  title,
  onPress,
  variant = 'primary',
  size = 'md',
  icon,
  iconPosition = 'left',
  loading = false,
  disabled = false,
  fullWidth = false,
  style,
  textStyle,
}: ButtonProps) {
  const scaleAnim = useRef(new Animated.Value(1)).current;
  const variantCfg = variantStyles[variant];
  const sizeCfg = sizeStyles[size];

  const handlePressIn = () => {
    Animated.spring(scaleAnim, {
      toValue: 0.97,
      useNativeDriver: true,
      friction: 8,
    }).start();
  };

  const handlePressOut = () => {
    Animated.spring(scaleAnim, {
      toValue: 1,
      useNativeDriver: true,
      friction: 8,
    }).start();
  };

  const isDisabled = disabled || loading;

  return (
    <Animated.View style={[{ transform: [{ scale: scaleAnim }] }, fullWidth && { width: '100%' }]}>
      <TouchableOpacity
        onPress={onPress}
        onPressIn={handlePressIn}
        onPressOut={handlePressOut}
        disabled={isDisabled}
        activeOpacity={0.9}
        style={[
          styles.button,
          {
            backgroundColor: variantCfg.bg,
            paddingVertical: sizeCfg.paddingV,
            paddingHorizontal: sizeCfg.paddingH,
            borderRadius: sizeCfg.borderRadius,
            borderWidth: variantCfg.border ? 1.5 : 0,
            borderColor: variantCfg.border || 'transparent',
            opacity: isDisabled ? 0.5 : 1,
          },
          variant !== 'ghost' && variant !== 'outline' ? shadows.button : {},
          fullWidth && { width: '100%' },
          style,
        ]}
      >
        {loading ? (
          <ActivityIndicator size="small" color={variantCfg.text} />
        ) : (
          <View style={[styles.content, iconPosition === 'right' && { flexDirection: 'row-reverse' }]}>
            {icon && <Text style={[styles.icon, { fontSize: sizeCfg.iconSize }]}>{icon}</Text>}
            <Text
              style={[
                styles.text,
                {
                  color: variantCfg.text,
                  fontSize: sizeCfg.fontSize,
                },
                textStyle,
              ]}
            >
              {title}
            </Text>
          </View>
        )}
      </TouchableOpacity>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  button: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  content: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  icon: {},
  text: {
    fontWeight: '700',
    letterSpacing: 0.3,
  },
});

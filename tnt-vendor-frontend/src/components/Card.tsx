import React from 'react';
import { View, StyleSheet, ViewStyle } from 'react-native';
import { Colors, BorderRadius, Shadows, Spacing } from '../theme';

interface CardProps {
  children: React.ReactNode;
  style?: ViewStyle;
  variant?: 'default' | 'elevated' | 'flat' | 'outlined';
  padding?: number;
}

export default function Card({
  children,
  style,
  variant = 'default',
  padding = Spacing.lg,
}: CardProps) {
  return (
    <View style={[styles.base, styles[variant], { padding }, style]}>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  base: {
    backgroundColor: Colors.bgCard,
    borderRadius: BorderRadius.lg,
  },
  default: {
    ...Shadows.card,
  },
  elevated: {
    ...Shadows.cardHover,
  },
  flat: {
    borderWidth: 1,
    borderColor: Colors.borderLight,
    shadowOpacity: 0,
    elevation: 0,
  },
  outlined: {
    borderWidth: 1.5,
    borderColor: Colors.border,
    shadowOpacity: 0,
    elevation: 0,
  },
});

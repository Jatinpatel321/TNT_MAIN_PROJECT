// ─── PremiumEmptyState ─────────────────────────────────────────────
// Beautiful illustrated empty state with action

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ViewStyle } from 'react-native';
import { useTheme } from '../../context/ThemeContext';
import staticColors from '../tokens/colors';
import shadows from '../tokens/shadows';


interface PremiumEmptyStateProps {
  icon: string;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  secondaryAction?: { label: string; onPress: () => void };
  style?: ViewStyle;
}

export default function PremiumEmptyState({
  icon,
  title,
  description,
  actionLabel,
  onAction,
  secondaryAction,
  style,
}: PremiumEmptyStateProps) {
  const { colors } = useTheme();

  return (
    <View style={[styles.container, style]}>
      {/* Icon with decorative background */}
      <View style={styles.iconWrapper}>
        <View style={[styles.iconBg, { backgroundColor: colors.primaryPale }]} />
        <View style={[styles.iconCircle, { backgroundColor: colors.bgCard }]}>
          <Text style={styles.icon}>{icon}</Text>
        </View>
      </View>

      <Text style={[styles.title, { color: colors.textPrimary }]}>{title}</Text>
      <Text style={[styles.description, { color: colors.textSecondary }]}>{description}</Text>

      {actionLabel && onAction && (
        <TouchableOpacity style={[styles.actionButton, { backgroundColor: colors.primary }]} onPress={onAction}>
          <Text style={[styles.actionText, { color: colors.textInverse }]}>{actionLabel}</Text>
        </TouchableOpacity>
      )}

      {secondaryAction && (
        <TouchableOpacity style={styles.secondaryButton} onPress={secondaryAction.onPress}>
          <Text style={[styles.secondaryText, { color: colors.textSecondary }]}>{secondaryAction.label}</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

const colors = staticColors;

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 40,
    paddingVertical: 40,
  },
  iconWrapper: {
    marginBottom: 24,
    position: 'relative',
  },
  iconBg: {
    position: 'absolute',
    width: 100,
    height: 100,
    borderRadius: 50,
    top: -10,
    left: -10,
  },
  iconCircle: {
    width: 80,
    height: 80,
    borderRadius: 24,
    justifyContent: 'center',
    alignItems: 'center',
    ...shadows.lg,
  },
  icon: {
    fontSize: 36,
  },
  title: {
    fontSize: 20,
    fontWeight: '700',
    marginBottom: 8,
    textAlign: 'center',
  },
  description: {
    fontSize: 14,
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 24,
  },
  actionButton: {
    paddingHorizontal: 32,
    paddingVertical: 14,
    borderRadius: 14,
    ...shadows.button,
  },
  actionText: {
    fontSize: 16,
    fontWeight: '600',
  },
  secondaryButton: {
    marginTop: 12,
    paddingVertical: 10,
  },
  secondaryText: {
    fontSize: 14,
    fontWeight: '600',
  },
});


// ─── PremiumEmptyState ─────────────────────────────────────────────
// Beautiful illustrated empty state with action

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ViewStyle } from 'react-native';
import colors from '../tokens/colors';
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
  return (
    <View style={[styles.container, style]}>
      {/* Icon with decorative background */}
      <View style={styles.iconWrapper}>
        <View style={styles.iconBg} />
        <View style={styles.iconCircle}>
          <Text style={styles.icon}>{icon}</Text>
        </View>
      </View>

      <Text style={styles.title}>{title}</Text>
      <Text style={styles.description}>{description}</Text>

      {actionLabel && onAction && (
        <TouchableOpacity style={styles.actionButton} onPress={onAction}>
          <Text style={styles.actionText}>{actionLabel}</Text>
        </TouchableOpacity>
      )}

      {secondaryAction && (
        <TouchableOpacity style={styles.secondaryButton} onPress={secondaryAction.onPress}>
          <Text style={styles.secondaryText}>{secondaryAction.label}</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

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
    backgroundColor: colors.primaryPale,
    top: -10,
    left: -10,
  },
  iconCircle: {
    width: 80,
    height: 80,
    borderRadius: 24,
    backgroundColor: colors.bgCard,
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
    color: colors.textPrimary,
    marginBottom: 8,
    textAlign: 'center',
  },
  description: {
    fontSize: 14,
    color: colors.textSecondary,
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 24,
  },
  actionButton: {
    backgroundColor: colors.primary,
    paddingHorizontal: 32,
    paddingVertical: 14,
    borderRadius: 14,
    ...shadows.button,
  },
  actionText: {
    color: colors.textInverse,
    fontSize: 16,
    fontWeight: '600',
  },
  secondaryButton: {
    marginTop: 12,
    paddingVertical: 10,
  },
  secondaryText: {
    color: colors.textLink,
    fontSize: 14,
    fontWeight: '600',
  },
});

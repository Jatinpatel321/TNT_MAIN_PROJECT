// ─── AICard ─────────────────────────────────────────────────────────
// AI-powered insight card with severity, icon, and action

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ViewStyle } from 'react-native';
import colors from '../tokens/colors';
import shadows from '../tokens/shadows';

interface AICardProps {
  icon: string;
  title: string;
  description: string;
  severity?: 'info' | 'success' | 'warning' | 'danger';
  action?: { label: string; onPress: () => void };
  confidence?: number;
  style?: ViewStyle;
}

const severityConfig = {
  info: { bg: colors.primaryPale, border: colors.primary, text: colors.primary },
  success: { bg: colors.successPale, border: colors.success, text: colors.successDark },
  warning: { bg: colors.warningPale, border: colors.warning, text: colors.warningDark },
  danger: { bg: colors.errorPale, border: colors.error, text: colors.errorDark },
};

export default function AICard({
  icon,
  title,
  description,
  severity = 'info',
  action,
  confidence,
  style,
}: AICardProps) {
  const config = severityConfig[severity];

  return (
    <View style={[styles.card, { borderLeftColor: config.border }, style]}>
      <View style={styles.header}>
        <View style={[styles.iconCircle, { backgroundColor: config.bg }]}>
          <Text style={styles.icon}>{icon}</Text>
        </View>
        <View style={styles.content}>
          <Text style={styles.title}>{title}</Text>
          <Text style={styles.description}>{description}</Text>
        </View>
        {confidence !== undefined && (
          <View style={[styles.confidenceBadge, { backgroundColor: config.bg }]}>
            <Text style={[styles.confidenceText, { color: config.text }]}>
              {Math.round(confidence * 100)}%
            </Text>
          </View>
        )}
      </View>
      {action && (
        <TouchableOpacity style={[styles.actionButton, { backgroundColor: config.bg }]} onPress={action.onPress}>
          <Text style={[styles.actionText, { color: config.text }]}>{action.label}</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.bgCard,
    borderRadius: 16,
    padding: 16,
    borderLeftWidth: 4,
    ...shadows.md,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  iconCircle: {
    width: 40,
    height: 40,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  icon: {
    fontSize: 20,
  },
  content: {
    flex: 1,
  },
  title: {
    fontSize: 15,
    fontWeight: '700',
    color: colors.textPrimary,
    marginBottom: 4,
  },
  description: {
    fontSize: 13,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  confidenceBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
    marginLeft: 8,
  },
  confidenceText: {
    fontSize: 11,
    fontWeight: '700',
  },
  actionButton: {
    marginTop: 12,
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 10,
    alignItems: 'center',
  },
  actionText: {
    fontSize: 14,
    fontWeight: '600',
  },
});

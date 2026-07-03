// ─── OrderTimeline ────────────────────────────────────────────────
// Visual progress tracker for order status flow

import React from 'react';
import { View, Text, StyleSheet, ViewStyle } from 'react-native';
import colors from '../tokens/colors';
import shadows from '../tokens/shadows';

interface TimelineStep {
  status: string;
  label: string;
  timestamp?: string;
  icon: string;
  completed: boolean;
  active: boolean;
}

interface OrderTimelineProps {
  steps: TimelineStep[];
  currentStatus: string;
  style?: ViewStyle;
  color?: string;
}

const getStepColor = (step: TimelineStep, color: string): string => {
  if (step.active) return color;
  if (step.completed) return colors.success;
  return colors.bgTertiary;
};

export default function OrderTimeline({
  steps,
  currentStatus,
  style,
  color = colors.primary,
}: OrderTimelineProps) {
  return (
    <View style={[styles.container, style]}>
      {steps.map((step, index) => {
        const isLast = index === steps.length - 1;
        const stepColor = getStepColor(step, color);
        const isActive = step.active;

        return (
          <View key={index} style={styles.stepRow}>
            {/* Timeline line & dot */}
            <View style={styles.timelineCol}>
              {!isLast && (
                <View
                  style={[
                    styles.line,
                    {
                      backgroundColor: step.completed ? colors.success : colors.borderLight,
                    },
                  ]}
                />
              )}
              <View
                style={[
                  styles.dot,
                  {
                    backgroundColor: stepColor,
                    borderWidth: isActive ? 3 : 0,
                    borderColor: isActive ? `${color}30` : 'transparent',
                  },
                ]}
              >
                <Text style={styles.dotIcon}>{step.icon}</Text>
              </View>
            </View>

            {/* Content */}
            <View style={[styles.content, isLast && styles.contentLast]}>
              <View style={styles.contentHeader}>
                <Text
                  style={[
                    styles.stepLabel,
                    isActive && { color, fontWeight: '700' },
                    step.completed && !isActive && { color: colors.success },
                    !step.completed && !isActive && { color: colors.textMuted },
                  ]}
                >
                  {step.label}
                </Text>
                {isActive && (
                  <View style={[styles.activeBadge, { backgroundColor: `${color}15` }]}>
                    <Text style={[styles.activeText, { color }]}>Current</Text>
                  </View>
                )}
              </View>
              {step.timestamp && (
                <Text style={styles.timestamp}>{step.timestamp}</Text>
              )}
            </View>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingLeft: 4,
  },
  stepRow: {
    flexDirection: 'row',
    minHeight: 56,
  },
  timelineCol: {
    width: 36,
    alignItems: 'center',
    position: 'relative',
  },
  line: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    width: 2,
    left: 17,
  },
  dot: {
    width: 36,
    height: 36,
    borderRadius: 18,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 0,
    zIndex: 1,
  },
  dotIcon: {
    fontSize: 14,
  },
  content: {
    flex: 1,
    marginLeft: 12,
    paddingBottom: 20,
    paddingTop: 6,
    borderBottomWidth: 1,
    borderBottomColor: colors.borderLight,
  },
  contentLast: {
    borderBottomWidth: 0,
  },
  contentHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  stepLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.textPrimary,
  },
  activeBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 8,
  },
  activeText: {
    fontSize: 10,
    fontWeight: '700',
  },
  timestamp: {
    fontSize: 12,
    color: colors.textMuted,
    marginTop: 2,
  },
});

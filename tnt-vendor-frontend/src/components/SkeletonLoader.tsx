import React from 'react';
import { View, StyleSheet, Animated } from 'react-native';

interface SkeletonLoaderProps {
  type: 'card' | 'list' | 'metrics' | 'text' | 'image';
  count?: number;
}

export default function SkeletonLoader({ type, count = 1 }: SkeletonLoaderProps) {
  const renderSkeleton = () => {
    switch (type) {
      case 'card':
        return (
          <View style={styles.card}>
            <View style={styles.cardHeader}>
              <View style={[styles.skeleton, styles.titleBlock]} />
              <View style={[styles.skeleton, styles.badgeBlock]} />
            </View>
            <View style={styles.cardBody}>
              <View style={[styles.skeleton, styles.textLineWide]} />
              <View style={[styles.skeleton, styles.textLineMedium]} />
            </View>
            <View style={[styles.skeleton, styles.buttonBlock]} />
          </View>
        );
      
      case 'list':
        return (
          <View style={styles.listItem}>
            <View style={[styles.skeleton, styles.avatarBlock]} />
            <View style={styles.listContent}>
              <View style={[styles.skeleton, styles.textLineWide]} />
              <View style={[styles.skeleton, styles.textLineMedium]} />
            </View>
            <View style={[styles.skeleton, styles.actionBlock]} />
          </View>
        );
      
      case 'metrics':
        return (
          <View style={styles.metricsRow}>
            {[1,2,3,4].map(i => (
              <View key={i} style={styles.metricCard}>
                <View style={[styles.skeleton, styles.metricValueBlock]} />
                <View style={[styles.skeleton, styles.metricLabelBlock]} />
              </View>
            ))}
          </View>
        );
      
      case 'text':
        return (
          <View style={styles.textBlock}>
            <View style={[styles.skeleton, styles.textLineFull]} />
            <View style={[styles.skeleton, styles.textLineWide]} />
            <View style={[styles.skeleton, styles.textLineMedium]} />
          </View>
        );
      
      case 'image':
        return (
          <View style={styles.imageBlock}>
            <View style={[styles.skeleton, { width: '100%', height: 200, borderRadius: 12 }]} />
          </View>
        );
      
      default:
        return (
          <View style={[styles.skeleton, { width: '100%', height: 100 }]} />
        );
    }
  };

  return (
    <View style={styles.container}>
      {Array.from({ length: count }).map((_, i) => (
        <View key={i} style={styles.itemWrapper}>
          {renderSkeleton()}
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 16,
  },
  itemWrapper: {
    marginBottom: 12,
  },
  skeleton: {
    backgroundColor: '#E5E7EB',
    borderRadius: 8,
    opacity: 0.7,
  },
  // Card skeleton
  card: {
    backgroundColor: '#F9FAFB',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  titleBlock: {
    width: '60%',
    height: 20,
  },
  badgeBlock: {
    width: '25%',
    height: 20,
  },
  cardBody: {
    marginBottom: 12,
  },
  textLineWide: {
    width: '80%',
    height: 14,
    marginBottom: 8,
  },
  textLineMedium: {
    width: '50%',
    height: 14,
  },
  buttonBlock: {
    width: '100%',
    height: 44,
    borderRadius: 8,
  },
  // List skeleton
  listItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    backgroundColor: '#F9FAFB',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  avatarBlock: {
    width: 44,
    height: 44,
    borderRadius: 22,
    marginRight: 12,
  },
  listContent: {
    flex: 1,
  },
  actionBlock: {
    width: 60,
    height: 32,
    borderRadius: 8,
    marginLeft: 12,
  },
  // Metrics skeleton
  metricsRow: {
    flexDirection: 'row',
    padding: 16,
    gap: 12,
  },
  metricCard: {
    flex: 1,
    backgroundColor: '#F9FAFB',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  metricValueBlock: {
    width: 40,
    height: 28,
    marginBottom: 8,
  },
  metricLabelBlock: {
    width: 50,
    height: 14,
  },
  // Text skeleton
  textBlock: {
    padding: 16,
  },
  textLineFull: {
    width: '100%',
    height: 16,
    marginBottom: 8,
  },
  // Image skeleton
  imageBlock: {
    padding: 16,
  },
});
// ─── SkeletonScreen ────────────────────────────────────────────────
// Full-page skeleton loader with shimmer animation

import React, { useEffect, useRef } from 'react';
import { View, Text, StyleSheet, Animated, Dimensions, ViewStyle } from 'react-native';
import colors from '../tokens/colors';
import spacing from '../tokens/spacing';

const { width } = Dimensions.get('window');

interface SkeletonBlock {
  width?: number | string;
  height: number;
  borderRadius?: number;
  style?: ViewStyle;
}

interface SkeletonScreenProps {
  header?: boolean;
  headerHeight?: number;
  sections?: {
    title?: boolean;
    blocks: SkeletonBlock[];
    count?: number;
  }[];
  footer?: boolean;
}

function SkeletonBox({ width: w = '100%', height, borderRadius = 12, style }: SkeletonBlock) {
  const opacity = useRef(new Animated.Value(0.3)).current;

  useEffect(() => {
    const anim = Animated.loop(
      Animated.sequence([
        Animated.timing(opacity, { toValue: 0.7, duration: 800, useNativeDriver: true }),
        Animated.timing(opacity, { toValue: 0.3, duration: 800, useNativeDriver: true }),
      ]),
    );
    anim.start();
    return () => anim.stop();
  }, []);

  return (
    <Animated.View
      style={[
        {
          width: w as any,
          height,
          borderRadius,
          backgroundColor: colors.bgTertiary,
          opacity,
        },
        style,
      ]}
    />
  );
}

export default function SkeletonScreen({
  header = true,
  headerHeight = 140,
  sections = [
    {
      title: true,
      blocks: [
        { width: '100%', height: 80 },
        { width: '100%', height: 60 },
        { width: '100%', height: 60 },
        { width: '100%', height: 60 },
      ],
    },
  ],
  footer = false,
}: SkeletonScreenProps) {
  return (
    <View style={styles.container}>
      {/* Header skeleton */}
      {header && (
        <View style={[styles.header, { height: headerHeight }]}>
          <View style={styles.headerContent}>
            <View style={styles.headerLeft}>
              <SkeletonBox width={140} height={14} borderRadius={6} />
              <SkeletonBox width={200} height={24} borderRadius={6} style={{ marginTop: 8 }} />
              <SkeletonBox width={100} height={20} borderRadius={10} style={{ marginTop: 8 }} />
            </View>
            <SkeletonBox width={40} height={40} borderRadius={12} />
          </View>
        </View>
      )}

      {/* Content sections */}
      <View style={styles.content}>
        {sections.map((section, sIdx) => (
          <View key={sIdx} style={styles.section}>
            {section.title && (
              <SkeletonBox width={120} height={18} borderRadius={6} style={{ marginBottom: 12 }} />
            )}
            {Array.from({ length: section.count || 1 }).map((_, cIdx) => (
              <View key={cIdx} style={styles.blockGroup}>
                {section.blocks.map((block, bIdx) => (
              <SkeletonBox key={bIdx} {...block} style={{ ...(block.style as any), marginBottom: 8 }} />
                ))}
              </View>
            ))}
          </View>
        ))}
      </View>

      {/* Footer skeleton */}
      {footer && (
        <View style={styles.footer}>
          <SkeletonBox width="100%" height={60} borderRadius={16} />
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  header: {
    backgroundColor: colors.primary,
    paddingTop: spacing.huge + 20,
    paddingBottom: spacing.xxl,
    paddingHorizontal: spacing.xl,
    borderBottomLeftRadius: 28,
    borderBottomRightRadius: 28,
    justifyContent: 'flex-end',
  },
  headerContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
  },
  headerLeft: {
    flex: 1,
  },
  content: {
    padding: spacing.lg,
    gap: spacing.md,
  },
  section: {
    marginBottom: spacing.md,
  },
  blockGroup: {
    marginBottom: spacing.md,
  },
  footer: {
    padding: spacing.lg,
    paddingBottom: spacing.huge,
  },
});

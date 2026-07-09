/**
 * Shared building blocks for the profile module: skeletons, section cards,
 * stat tiles, action rows, chips and toggles. All theme-aware.
 */
import React, { useEffect, useRef } from 'react';
import { Animated, Easing, Pressable, StyleSheet, Switch, View, ViewStyle } from 'react-native';
import { Text } from 'react-native-paper';
import MaterialCommunityIcons from 'react-native-vector-icons/MaterialCommunityIcons';

import { useAppTheme } from '../../theme/ThemeContext';

// ── Skeleton ────────────────────────────────────────────────────────────────

export function SkeletonBlock({ width, height, radius = 10, style }: {
  width: number | `${number}%`;
  height: number;
  radius?: number;
  style?: ViewStyle;
}) {
  const { colors } = useAppTheme();
  const pulse = useRef(new Animated.Value(0.4)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, { toValue: 1, duration: 700, easing: Easing.ease, useNativeDriver: true }),
        Animated.timing(pulse, { toValue: 0.4, duration: 700, easing: Easing.ease, useNativeDriver: true }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [pulse]);

  return (
    <Animated.View
      style={[
        { width, height, borderRadius: radius, backgroundColor: colors.skeleton, opacity: pulse },
        style,
      ]}
    />
  );
}

export function ProfileSkeleton() {
  const { colors } = useAppTheme();
  return (
    <View style={{ gap: 14, paddingTop: 8 }}>
      <View style={[skStyles.card, { backgroundColor: colors.surface }]}>
        <View style={{ flexDirection: 'row', gap: 14, alignItems: 'center' }}>
          <SkeletonBlock width={72} height={72} radius={36} />
          <View style={{ gap: 8, flex: 1 }}>
            <SkeletonBlock width={'70%'} height={18} />
            <SkeletonBlock width={'45%'} height={12} />
            <SkeletonBlock width={'55%'} height={12} />
          </View>
        </View>
      </View>
      <View style={{ flexDirection: 'row', gap: 10 }}>
        <SkeletonBlock width={'48%' as const} height={86} radius={16} />
        <SkeletonBlock width={'48%' as const} height={86} radius={16} />
      </View>
      <View style={{ flexDirection: 'row', gap: 10 }}>
        <SkeletonBlock width={'48%' as const} height={86} radius={16} />
        <SkeletonBlock width={'48%' as const} height={86} radius={16} />
      </View>
      <SkeletonBlock width={'100%' as const} height={220} radius={18} />
      <SkeletonBlock width={'100%' as const} height={160} radius={18} />
    </View>
  );
}

const skStyles = StyleSheet.create({
  card: {
    borderRadius: 18,
    padding: 16,
  },
});

// ── Animated section mount ──────────────────────────────────────────────────

export function FadeInSection({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
  const opacity = useRef(new Animated.Value(0)).current;
  const translateY = useRef(new Animated.Value(12)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(opacity, { toValue: 1, duration: 320, delay, useNativeDriver: true }),
      Animated.timing(translateY, {
        toValue: 0,
        duration: 320,
        delay,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }),
    ]).start();
  }, [opacity, translateY, delay]);

  return <Animated.View style={{ opacity, transform: [{ translateY }] }}>{children}</Animated.View>;
}

// ── Section card ────────────────────────────────────────────────────────────

export function SectionCard({ title, icon, children, style }: {
  title?: string;
  icon?: string;
  children: React.ReactNode;
  style?: ViewStyle;
}) {
  const { colors } = useAppTheme();
  return (
    <View
      style={[
        {
          backgroundColor: colors.surface,
          borderRadius: 18,
          padding: 16,
          shadowColor: 'rgba(0,0,0,0.10)',
          shadowOpacity: 0.1,
          shadowOffset: { width: 0, height: 3 },
          shadowRadius: 10,
          elevation: 3,
          borderWidth: StyleSheet.hairlineWidth,
          borderColor: colors.border,
        },
        style,
      ]}
    >
      {title ? (
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          {icon ? <MaterialCommunityIcons name={icon as any} size={18} color={colors.primary} /> : null}
          <Text style={{ fontSize: 15, fontWeight: '800', color: colors.text }}>{title}</Text>
        </View>
      ) : null}
      {children}
    </View>
  );
}

// ── Stat tile ───────────────────────────────────────────────────────────────

export function StatTile({ icon, label, value, tint }: {
  icon: string;
  label: string;
  value: string;
  tint?: string;
}) {
  const { colors } = useAppTheme();
  const accent = tint ?? colors.primary;
  return (
    <View
      style={{
        flex: 1,
        minWidth: '46%',
        backgroundColor: colors.surface,
        borderRadius: 16,
        padding: 14,
        gap: 8,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: colors.border,
        shadowColor: 'rgba(0,0,0,0.06)',
        shadowOpacity: 0.06,
        shadowOffset: { width: 0, height: 2 },
        shadowRadius: 6,
        elevation: 2,
      }}
    >
      <View
        style={{
          width: 32,
          height: 32,
          borderRadius: 10,
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: colors.primarySoft,
        }}
      >
        <MaterialCommunityIcons name={icon as any} size={18} color={accent} />
      </View>
      <Text style={{ fontSize: 18, fontWeight: '800', color: colors.text }} numberOfLines={1}>
        {value}
      </Text>
      <Text style={{ fontSize: 12, fontWeight: '600', color: colors.muted }} numberOfLines={1}>
        {label}
      </Text>
    </View>
  );
}

// ── Action row ──────────────────────────────────────────────────────────────

export function ActionRow({ icon, label, sublabel, onPress, danger, last }: {
  icon: string;
  label: string;
  sublabel?: string;
  onPress?: () => void;
  danger?: boolean;
  last?: boolean;
}) {
  const { colors } = useAppTheme();
  const tint = danger ? colors.danger : colors.primary;
  return (
    <Pressable
      onPress={onPress}
      android_ripple={{ color: colors.primarySoft }}
      style={({ pressed }) => ({
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
        paddingVertical: 13,
        opacity: pressed ? 0.7 : 1,
        borderBottomWidth: last ? 0 : StyleSheet.hairlineWidth,
        borderBottomColor: colors.border,
      })}
    >
      <View
        style={{
          width: 34,
          height: 34,
          borderRadius: 10,
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: danger ? colors.dangerSoft : colors.primarySoft,
        }}
      >
        <MaterialCommunityIcons name={icon as any} size={18} color={tint} />
      </View>
      <View style={{ flex: 1 }}>
        <Text style={{ fontSize: 14, fontWeight: '700', color: danger ? colors.danger : colors.text }}>
          {label}
        </Text>
        {sublabel ? (
          <Text style={{ fontSize: 12, color: colors.muted, marginTop: 1 }}>{sublabel}</Text>
        ) : null}
      </View>
      <MaterialCommunityIcons name="chevron-right" size={20} color={colors.muted} />
    </Pressable>
  );
}

// ── Toggle row ──────────────────────────────────────────────────────────────

export function ToggleRow({ icon, label, sublabel, value, onValueChange, disabled, last }: {
  icon: string;
  label: string;
  sublabel?: string;
  value: boolean;
  onValueChange: (v: boolean) => void;
  disabled?: boolean;
  last?: boolean;
}) {
  const { colors } = useAppTheme();
  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
        paddingVertical: 11,
        borderBottomWidth: last ? 0 : StyleSheet.hairlineWidth,
        borderBottomColor: colors.border,
        opacity: disabled ? 0.5 : 1,
      }}
    >
      <View
        style={{
          width: 34,
          height: 34,
          borderRadius: 10,
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: colors.primarySoft,
        }}
      >
        <MaterialCommunityIcons name={icon as any} size={18} color={colors.primary} />
      </View>
      <View style={{ flex: 1 }}>
        <Text style={{ fontSize: 14, fontWeight: '700', color: colors.text }}>{label}</Text>
        {sublabel ? (
          <Text style={{ fontSize: 12, color: colors.muted, marginTop: 1 }}>{sublabel}</Text>
        ) : null}
      </View>
      <Switch
        value={value}
        onValueChange={onValueChange}
        disabled={disabled}
        trackColor={{ false: colors.border, true: colors.primary }}
        thumbColor="#FFFFFF"
      />
    </View>
  );
}

// ── Chip ────────────────────────────────────────────────────────────────────

export function Chip({ label, icon, active, onPress }: {
  label: string;
  icon?: string;
  active?: boolean;
  onPress?: () => void;
}) {
  const { colors } = useAppTheme();
  return (
    <Pressable
      onPress={onPress}
      disabled={!onPress}
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: 5,
        paddingHorizontal: 12,
        paddingVertical: 7,
        borderRadius: 999,
        backgroundColor: active ? colors.primary : colors.primarySoft,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: active ? colors.primary : colors.border,
      }}
    >
      {icon ? (
        <MaterialCommunityIcons
          name={icon as any}
          size={14}
          color={active ? colors.onPrimary : colors.primary}
        />
      ) : null}
      <Text
        style={{
          fontSize: 12,
          fontWeight: '700',
          color: active ? colors.onPrimary : colors.primary,
        }}
      >
        {label}
      </Text>
    </Pressable>
  );
}

// ── Empty state ─────────────────────────────────────────────────────────────

export function EmptyState({ icon, title, subtitle }: {
  icon: string;
  title: string;
  subtitle?: string;
}) {
  const { colors } = useAppTheme();
  return (
    <View style={{ alignItems: 'center', paddingVertical: 22, gap: 6 }}>
      <View
        style={{
          width: 52,
          height: 52,
          borderRadius: 26,
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: colors.primarySoft,
        }}
      >
        <MaterialCommunityIcons name={icon as any} size={26} color={colors.primary} />
      </View>
      <Text style={{ fontSize: 14, fontWeight: '700', color: colors.text }}>{title}</Text>
      {subtitle ? (
        <Text style={{ fontSize: 12, color: colors.muted, textAlign: 'center' }}>{subtitle}</Text>
      ) : null}
    </View>
  );
}

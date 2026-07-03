// ─── Premium Notification Detail Screen ─────────────────────────
// View notification details with premium design system

import React, { useRef } from 'react';
import { View, Text, StyleSheet, ScrollView, Animated } from 'react-native';
import { colors, spacing } from '../../design-system';
import GlassCard from '../../design-system/components/GlassCard';
import Button from '../../design-system/components/Button';

export default function NotificationDetailScreen({ route, navigation }: any) {
  const { notification } = route.params;
  const fadeAnim = useRef(new Animated.Value(0)).current;

  React.useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }).start();
  }, []);

  const getIcon = (type: string) => {
    const icons: Record<string, string> = {
      order_ready: '✅', order_accepted: '📋', order_preparing: '👨‍🍳',
      delay_alert: '⚠️', order_cancelled: '❌', pickup_reminder: '🔔', promo: '🎉',
    };
    return icons[type] || '📢';
  };

  const getColor = (type: string) => {
    const map: Record<string, string> = {
      order_ready: colors.success, delay_alert: colors.warning, order_cancelled: colors.error,
    };
    return map[type] || colors.info;
  };

  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      <View style={styles.header}>
        <View style={styles.headerDeco1} /><View style={styles.headerDeco2} />
        <View style={[styles.iconCircle, { backgroundColor: getColor(notification.notification_type) }]}>
          <Text style={styles.icon}>{getIcon(notification.notification_type)}</Text>
        </View>
        <Text style={styles.headerTitle}>{notification.title}</Text>
      </View>

      <Animated.View style={{ opacity: fadeAnim }}>
        <GlassCard padding={20} borderRadius={20} style={{ marginHorizontal: spacing.lg, marginTop: spacing.md }}>
          <Text style={styles.message}>{notification.message}</Text>
        </GlassCard>

        <GlassCard padding={16} borderRadius={18} style={{ marginHorizontal: spacing.lg, marginTop: spacing.sm }}>
          <DetailRow label="Type" value={notification.notification_type} />
          <DetailRow label="Status" value={notification.is_read ? 'Read' : 'Unread'} valueColor={notification.is_read ? colors.textMuted : colors.primary} />
          {notification.reference_id && <DetailRow label="Reference" value={`#${notification.reference_id}`} />}
          <DetailRow label="Time" value={new Date(notification.created_at).toLocaleString()} />
        </GlassCard>

        {!notification.is_read && (
          <Button title="Mark as Read" onPress={() => navigation.goBack()} variant="primary" size="lg" fullWidth style={{ marginHorizontal: spacing.lg, marginTop: spacing.md }} />
        )}
        <View style={{ height: spacing.huge }} />
      </Animated.View>
    </ScrollView>
  );
}

function DetailRow({ label, value, valueColor }: { label: string; value: string; valueColor?: string }) {
  return (
    <View style={detailStyles.row}>
      <Text style={detailStyles.label}>{label}</Text>
      <Text style={[detailStyles.value, valueColor ? { color: valueColor } : undefined]}>{value}</Text>
    </View>
  );
}

const detailStyles = StyleSheet.create({
  row: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: colors.borderLight },
  label: { fontSize: 14, color: colors.textMuted, fontWeight: '500' },
  value: { fontSize: 14, fontWeight: '600', color: colors.textPrimary },
});

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  header: {
    backgroundColor: colors.primary,
    paddingTop: spacing.huge + 20,
    paddingBottom: spacing.xxl,
    paddingHorizontal: spacing.xl,
    alignItems: 'center',
    borderBottomLeftRadius: 28,
    borderBottomRightRadius: 28,
    overflow: 'hidden',
  },
  headerDeco1: { position: 'absolute', top: -40, right: -30, width: 180, height: 180, borderRadius: 90, backgroundColor: 'rgba(255,255,255,0.08)' },
  headerDeco2: { position: 'absolute', bottom: -30, left: -60, width: 140, height: 140, borderRadius: 70, backgroundColor: 'rgba(255,255,255,0.05)' },
  iconCircle: { width: 72, height: 72, borderRadius: 24, justifyContent: 'center', alignItems: 'center', marginBottom: 12 },
  icon: { fontSize: 36 },
  headerTitle: { fontSize: 22, fontWeight: '700', color: colors.textInverse, textAlign: 'center' },
  message: { fontSize: 16, color: colors.textPrimary, lineHeight: 24 },
});

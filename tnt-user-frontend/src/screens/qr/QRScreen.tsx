import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {ActivityIndicator, Animated, Easing, Pressable, StyleSheet, View} from 'react-native';
import {Text} from 'react-native-paper';
import QRCode from 'react-native-qrcode-svg';
import MaterialCommunityIcons from 'react-native-vector-icons/MaterialCommunityIcons';
import {NativeStackScreenProps} from '@react-navigation/native-stack';

import type {RootStackParamList} from '../../types/navigation';
import {Screen} from '../../components/Screen';
import {
  generateOrderQr,
  getPickupStatus,
  refreshOrderQr,
  isTerminalOrder,
  ORDER_STATUS_LABELS,
  type PickupStatus,
} from '../../services/orderService';
import {toApiError} from '../../services/apiClient';
import {useAuth} from '../../hooks/useAuth';
import {useAppTheme} from '../../theme/ThemeContext';
import {useOrderWebSocket} from '../../hooks/useOrderWebSocket';
import {formatCurrency} from '../../utils/format';

type Props = NativeStackScreenProps<RootStackParamList, 'QR'>;

function fmtWindow(startIso?: string | null, endIso?: string | null): string | null {
  if (!startIso || !endIso) return null;
  const opts: Intl.DateTimeFormatOptions = {hour: '2-digit', minute: '2-digit'};
  return `${new Date(startIso).toLocaleTimeString([], opts)} – ${new Date(endIso).toLocaleTimeString([], opts)}`;
}

function mmss(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export function QRScreen({route, navigation}: Props) {
  const {qrCode: initialQr, orderId} = route.params;
  const {colors, isDark} = useAppTheme();
  const {accessToken} = useAuth();

  const [qrValue, setQrValue] = useState(initialQr ?? '');
  const [pickup, setPickup] = useState<PickupStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [secondsLeft, setSecondsLeft] = useState<number | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [picked, setPicked] = useState(false);

  const successScale = useRef(new Animated.Value(0)).current;
  const pulse = useRef(new Animated.Value(1)).current;

  // ── Initial load: pickup status + ensure a live QR ──────────────────────
  const load = useCallback(async () => {
    try {
      const status = await getPickupStatus(orderId);
      setPickup(status);

      if (isTerminalOrder(status.status)) {
        if (status.is_picked) setPicked(true);
        setLoading(false);
        return;
      }

      // Ensure we have a live QR: use passed-in value, else the live token, else mint one.
      let code = initialQr ?? '';
      let remaining = status.qr_expires_in_seconds ?? null;
      if (!code && status.can_generate_qr) {
        const res = await generateOrderQr(orderId);
        code = res.qr_code;
        remaining = res.expires_in_seconds;
      }
      setQrValue(code);
      setSecondsLeft(remaining);
    } catch (e) {
      // Non-fatal: screen still renders what it can.
      console.warn('[QR] load failed', toApiError(e).message);
    } finally {
      setLoading(false);
    }
  }, [orderId, initialQr]);

  useEffect(() => {
    load();
  }, [load]);

  // ── Rotate the QR when it expires ───────────────────────────────────────
  const doRefresh = useCallback(async () => {
    try {
      setRefreshing(true);
      const res = await refreshOrderQr(orderId);
      setQrValue(res.qr_code);
      setSecondsLeft(res.expires_in_seconds);
    } catch (e) {
      console.warn('[QR] refresh failed', toApiError(e).message);
    } finally {
      setRefreshing(false);
    }
  }, [orderId]);

  // ── Countdown tick ──────────────────────────────────────────────────────
  useEffect(() => {
    if (secondsLeft == null || picked) return;
    if (secondsLeft <= 0) {
      if (!refreshing) doRefresh();
      return;
    }
    const t = setTimeout(() => setSecondsLeft(s => (s == null ? s : s - 1)), 1000);
    return () => clearTimeout(t);
  }, [secondsLeft, picked, refreshing, doRefresh]);

  // ── Gentle pulse on the live QR ─────────────────────────────────────────
  useEffect(() => {
    if (picked) return;
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, {toValue: 1.04, duration: 1100, easing: Easing.inOut(Easing.ease), useNativeDriver: true}),
        Animated.timing(pulse, {toValue: 1, duration: 1100, easing: Easing.inOut(Easing.ease), useNativeDriver: true}),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [picked, pulse]);

  // ── Success animation when the vendor scans ─────────────────────────────
  const triggerSuccess = useCallback(() => {
    setPicked(true);
    Animated.spring(successScale, {toValue: 1, friction: 5, tension: 80, useNativeDriver: true}).start();
  }, [successScale]);

  // ── Realtime: mark picked instantly on scan ─────────────────────────────
  const handleWSEvent = useCallback(
    (evt: {event: string; data: any}) => {
      if (evt.event === 'pickup_confirmed') {
        triggerSuccess();
      } else if (evt.event === 'status_change' && (evt.data?.new_status === 'picked' || evt.data?.new_status === 'completed')) {
        triggerSuccess();
      } else if (evt.event === 'status' && (evt.data?.status === 'picked' || evt.data?.status === 'completed')) {
        triggerSuccess();
      }
    },
    [triggerSuccess],
  );

  const {isConnected} = useOrderWebSocket(orderId, accessToken, handleWSEvent);

  // WS-less fallback: poll pickup status while showing the QR.
  useEffect(() => {
    if (picked || isConnected) return;
    const id = setInterval(async () => {
      try {
        const s = await getPickupStatus(orderId);
        if (s.is_picked) triggerSuccess();
      } catch {
        /* ignore */
      }
    }, 5000);
    return () => clearInterval(id);
  }, [orderId, picked, isConnected, triggerSuccess]);

  const slotWindow = useMemo(
    () => fmtWindow(pickup?.slot?.start_time, pickup?.slot?.end_time),
    [pickup],
  );

  const statusKey = (pickup?.status ?? '').toLowerCase();
  const expirySoon = secondsLeft != null && secondsLeft <= 60;

  // ── Success state ───────────────────────────────────────────────────────
  if (picked) {
    return (
      <Screen>
        <View style={styles.successWrap}>
          <Animated.View style={[styles.successCircle, {backgroundColor: colors.success, transform: [{scale: successScale}]}]}>
            <MaterialCommunityIcons name="check-bold" size={64} color="#FFFFFF" />
          </Animated.View>
          <Text style={[styles.successTitle, {color: colors.text}]}>Picked Up!</Text>
          <Text style={[styles.successSub, {color: colors.muted}]}>
            Order #{orderId} has been collected. Enjoy!
          </Text>
          <View style={styles.successActions}>
            <Pressable
              style={[styles.primaryBtn, {backgroundColor: colors.primary}]}
              onPress={() => navigation.navigate('Receipt', {orderId})}
            >
              <MaterialCommunityIcons name="receipt" size={18} color="#FFFFFF" />
              <Text style={styles.primaryBtnText}>View Receipt</Text>
            </Pressable>
            <Pressable style={styles.secondaryBtn} onPress={() => navigation.goBack()}>
              <Text style={[styles.secondaryBtnText, {color: colors.primary}]}>Done</Text>
            </Pressable>
          </View>
        </View>
      </Screen>
    );
  }

  return (
    <Screen scroll>
      <View style={styles.header}>
        <Pressable onPress={() => navigation.goBack()} hitSlop={8}>
          <MaterialCommunityIcons name="arrow-left" size={24} color={colors.text} />
        </Pressable>
        <Text style={[styles.title, {color: colors.text}]}>Pickup QR</Text>
        <View style={styles.liveChip}>
          <View style={[styles.liveDot, {backgroundColor: isConnected ? colors.success : colors.muted}]} />
          <Text style={[styles.liveText, {color: isConnected ? colors.success : colors.muted}]}>
            {isConnected ? 'Live' : 'Offline'}
          </Text>
        </View>
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color={colors.primary} />
        </View>
      ) : (
        <>
          {/* Status banner */}
          <View style={[styles.statusBanner, {backgroundColor: pickup?.is_ready_for_pickup ? colors.successSoft : colors.warningSoft}]}>
            <MaterialCommunityIcons
              name={pickup?.is_ready_for_pickup ? 'check-circle' : 'clock-outline'}
              size={18}
              color={pickup?.is_ready_for_pickup ? colors.success : colors.warning}
            />
            <Text style={[styles.statusBannerText, {color: pickup?.is_ready_for_pickup ? colors.success : colors.warning}]}>
              {pickup?.is_ready_for_pickup
                ? 'Ready for pickup — show this code at the counter'
                : `Status: ${ORDER_STATUS_LABELS[statusKey] ?? pickup?.status ?? 'Pending'}`}
            </Text>
          </View>

          {/* QR card */}
          <View style={[styles.qrCard, {backgroundColor: colors.surface, borderColor: colors.border}]}>
            {qrValue ? (
              <>
                <Animated.View style={[styles.qrBox, {transform: [{scale: pulse}]}]}>
                  {/* QR foreground stays dark-on-white for scanner contrast even in dark mode */}
                  <View style={styles.qrInner}>
                    <QRCode value={JSON.stringify({order_id: orderId, token: qrValue})} size={224} />
                  </View>
                </Animated.View>

                {/* Countdown / refresh status */}
                <View style={styles.countdownRow}>
                  {refreshing ? (
                    <>
                      <ActivityIndicator size="small" color={colors.primary} />
                      <Text style={[styles.countdownText, {color: colors.muted}]}>Refreshing code…</Text>
                    </>
                  ) : secondsLeft != null ? (
                    <>
                      <MaterialCommunityIcons
                        name="timer-sand"
                        size={15}
                        color={expirySoon ? colors.danger : colors.muted}
                      />
                      <Text style={[styles.countdownText, {color: expirySoon ? colors.danger : colors.muted}]}>
                        Refreshes in {mmss(secondsLeft)}
                      </Text>
                    </>
                  ) : null}
                  <Pressable onPress={doRefresh} hitSlop={8} style={styles.refreshBtn}>
                    <MaterialCommunityIcons name="refresh" size={16} color={colors.primary} />
                    <Text style={[styles.refreshText, {color: colors.primary}]}>Refresh</Text>
                  </Pressable>
                </View>
                <Text style={[styles.secureNote, {color: colors.muted}]}>
                  🔒 This code rotates automatically and is signed for one-time pickup.
                </Text>
              </>
            ) : (
              <View style={styles.center}>
                <MaterialCommunityIcons name="qrcode-remove" size={40} color={colors.muted} />
                <Text style={[styles.noQrText, {color: colors.muted}]}>
                  {pickup?.can_generate_qr
                    ? 'Unable to load QR. Tap refresh.'
                    : 'QR becomes available once your order is ready.'}
                </Text>
                {pickup?.can_generate_qr && (
                  <Pressable onPress={doRefresh} style={[styles.primaryBtn, {backgroundColor: colors.primary, marginTop: 12}]}>
                    <MaterialCommunityIcons name="refresh" size={18} color="#FFFFFF" />
                    <Text style={styles.primaryBtnText}>Generate QR</Text>
                  </Pressable>
                )}
              </View>
            )}
          </View>

          {/* Order info */}
          <View style={[styles.infoCard, {backgroundColor: colors.surface, borderColor: colors.border}]}>
            <InfoRow icon="pound" label="Order" value={`#${orderId}`} colors={colors} />
            <InfoRow icon="store" label="Vendor" value={pickup?.vendor_name ?? 'Vendor'} colors={colors} />
            {pickup?.vendor_location ? (
              <InfoRow icon="map-marker" label="Location" value={pickup.vendor_location} colors={colors} />
            ) : null}
            {slotWindow ? (
              <InfoRow icon="calendar-clock" label="Pickup Window" value={slotWindow} colors={colors} />
            ) : null}
            {pickup?.eta_minutes != null ? (
              <InfoRow icon="timer" label="ETA" value={`${pickup.eta_minutes} min`} colors={colors} />
            ) : null}
            <InfoRow
              icon="currency-inr"
              label="Total"
              value={formatCurrency(pickup?.total_amount ?? 0, {inputType: 'rupees'})}
              colors={colors}
              last
            />
          </View>
        </>
      )}
    </Screen>
  );
}

function InfoRow({icon, label, value, colors, last}: {
  icon: string;
  label: string;
  value: string;
  colors: ReturnType<typeof useAppTheme>['colors'];
  last?: boolean;
}) {
  return (
    <View
      style={[
        styles.infoRow,
        !last && {borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border},
      ]}
    >
      <MaterialCommunityIcons name={icon as any} size={16} color={colors.primary} />
      <Text style={[styles.infoLabel, {color: colors.muted}]}>{label}</Text>
      <Text style={[styles.infoValue, {color: colors.text}]} numberOfLines={1}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    paddingVertical: 10,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  title: {fontSize: 18, fontWeight: '800'},
  liveChip: {flexDirection: 'row', alignItems: 'center', gap: 5},
  liveDot: {width: 8, height: 8, borderRadius: 4},
  liveText: {fontSize: 12, fontWeight: '700'},
  center: {paddingVertical: 30, alignItems: 'center', gap: 8},
  statusBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    borderRadius: 12,
    padding: 12,
    marginTop: 6,
  },
  statusBannerText: {flex: 1, fontSize: 13, fontWeight: '700'},
  qrCard: {
    marginTop: 14,
    borderRadius: 20,
    padding: 20,
    alignItems: 'center',
    borderWidth: StyleSheet.hairlineWidth,
    shadowColor: 'rgba(0,0,0,0.12)',
    shadowOpacity: 0.12,
    shadowOffset: {width: 0, height: 4},
    shadowRadius: 12,
    elevation: 4,
  },
  qrBox: {alignItems: 'center', justifyContent: 'center'},
  qrInner: {
    backgroundColor: '#FFFFFF',
    padding: 16,
    borderRadius: 16,
  },
  countdownRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 16,
  },
  countdownText: {fontSize: 13, fontWeight: '600'},
  refreshBtn: {flexDirection: 'row', alignItems: 'center', gap: 3, marginLeft: 'auto'},
  refreshText: {fontSize: 13, fontWeight: '700'},
  secureNote: {fontSize: 11, marginTop: 10, textAlign: 'center'},
  noQrText: {fontSize: 13, textAlign: 'center', marginTop: 4},
  infoCard: {
    marginTop: 14,
    borderRadius: 18,
    paddingHorizontal: 16,
    borderWidth: StyleSheet.hairlineWidth,
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 12,
  },
  infoLabel: {fontSize: 13, fontWeight: '600', width: 110},
  infoValue: {flex: 1, fontSize: 14, fontWeight: '700', textAlign: 'right'},
  // success
  successWrap: {flex: 1, alignItems: 'center', justifyContent: 'center', gap: 12, paddingHorizontal: 20},
  successCircle: {
    width: 120,
    height: 120,
    borderRadius: 60,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 8,
  },
  successTitle: {fontSize: 24, fontWeight: '900'},
  successSub: {fontSize: 14, textAlign: 'center'},
  successActions: {marginTop: 18, width: '100%', gap: 10},
  primaryBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    borderRadius: 14,
    paddingVertical: 14,
  },
  primaryBtnText: {color: '#FFFFFF', fontSize: 15, fontWeight: '800'},
  secondaryBtn: {alignItems: 'center', paddingVertical: 12},
  secondaryBtnText: {fontSize: 14, fontWeight: '700'},
});

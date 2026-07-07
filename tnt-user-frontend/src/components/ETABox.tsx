import React, {useMemo} from 'react';
import {StyleSheet, View} from 'react-native';
import {Text} from 'react-native-paper';

export function ETABox(props: {
  etaIso?: string | null;
  isDelayed?: boolean;
  delayMinutes?: number;
}) {
  const {etaIso, isDelayed, delayMinutes} = props;

  const {etaLabel, countdown} = useMemo(() => {
    if (!etaIso) return {etaLabel: '—', countdown: '—'};
    const etaDate = new Date(etaIso);
    const now = Date.now();
    const diffMin = Math.max(Math.round((etaDate.getTime() - now) / 60000), 0);
    return {
      etaLabel: etaDate.toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
      }),
      countdown: `${diffMin} Minutes`,
    };
  }, [etaIso]);

  return (
    <View style={[styles.card, isDelayed && styles.delayedCard]}>
      <Text style={styles.caption}>Estimated Ready Time</Text>
      <Text style={[styles.eta, isDelayed && styles.etaDelayed]}>
        {etaLabel}
      </Text>
      <Text style={styles.sub}>Remaining Time</Text>
      <Text style={[styles.countdown, isDelayed && styles.countdownDelayed]}>
        {countdown}
      </Text>
      {isDelayed && delayMinutes != null && delayMinutes > 0 && (
        <Text style={styles.delayText}>Running {delayMinutes} min late</Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 18,
    padding: 16,
    shadowColor: 'rgba(0,0,0,0.08)',
    shadowOpacity: 0.08,
    shadowOffset: {width: 0, height: 3},
    shadowRadius: 8,
    elevation: 4,
    gap: 4,
  },
  delayedCard: {
    backgroundColor: '#FEF2F2',
    borderLeftWidth: 3,
    borderLeftColor: '#EF4444',
  },
  caption: {
    fontSize: 13,
    color: '#6B7280',
  },
  eta: {
    fontSize: 20,
    fontWeight: '900',
    color: '#111827',
  },
  etaDelayed: {
    color: '#EF4444',
  },
  sub: {
    fontSize: 13,
    color: '#6B7280',
    marginTop: 6,
  },
  countdown: {
    fontSize: 16,
    fontWeight: '700',
    color: '#4A90E2',
  },
  countdownDelayed: {
    color: '#EF4444',
  },
  delayText: {
    fontSize: 13,
    fontWeight: '700',
    color: '#EF4444',
    marginTop: 4,
  },
});

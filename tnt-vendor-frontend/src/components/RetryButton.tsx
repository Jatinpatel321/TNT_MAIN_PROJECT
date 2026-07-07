import React from 'react';
import { TouchableOpacity, Text, StyleSheet, ActivityIndicator } from 'react-native';

interface RetryButtonProps {
  onPress: () => void;
  loading?: boolean;
  label?: string;
}

export default function RetryButton({ onPress, loading = false, label = 'Retry' }: RetryButtonProps) {
  return (
    <TouchableOpacity
      style={styles.retryButton}
      onPress={onPress}
      disabled={loading}
      activeOpacity={0.7}
    >
      {loading ? (
        <ActivityIndicator color="white" size="small" />
      ) : (
        <>
          <Text style={styles.retryIcon}>🔄</Text>
          <Text style={styles.retryText}>{label}</Text>
        </>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  retryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#10B981',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 12,
    minWidth: 120,
  },
  retryIcon: {
    fontSize: 16,
    marginRight: 8,
  },
  retryText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
});
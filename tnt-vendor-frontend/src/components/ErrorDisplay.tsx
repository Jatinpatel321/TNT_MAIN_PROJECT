import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import RetryButton from './RetryButton';

interface ErrorDisplayProps {
  message?: string;
  onRetry?: () => void;
  retryLoading?: boolean;
  fullScreen?: boolean;
}

export default function ErrorDisplay({ 
  message = 'Something went wrong', 
  onRetry, 
  retryLoading = false,
  fullScreen = false 
}: ErrorDisplayProps) {
  const content = (
    <View style={[styles.container, fullScreen && styles.fullScreen]}>
      <Text style={styles.errorIcon}>⚠️</Text>
      <Text style={styles.errorTitle}>Oops!</Text>
      <Text style={styles.errorMessage}>{message}</Text>
      {onRetry && (
        <RetryButton onPress={onRetry} loading={retryLoading} />
      )}
    </View>
  );

  return content;
}

const styles = StyleSheet.create({
  container: {
    padding: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  fullScreen: {
    flex: 1,
    backgroundColor: '#F9FAFB',
  },
  errorIcon: {
    fontSize: 48,
    marginBottom: 16,
  },
  errorTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#111827',
    marginBottom: 8,
  },
  errorMessage: {
    fontSize: 14,
    color: '#6B7280',
    textAlign: 'center',
    marginBottom: 24,
    lineHeight: 20,
  },
});
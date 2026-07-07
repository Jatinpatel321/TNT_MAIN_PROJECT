import React from 'react';
import { View, Text, StyleSheet, Animated } from 'react-native';

interface UploadProgressProps {
  progress: number;
  visible: boolean;
}

export default function UploadProgress({ progress, visible }: UploadProgressProps) {
  if (!visible) return null;

  return (
    <View style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.icon}>📤</Text>
        <Text style={styles.title}>Uploading...</Text>
        <Text style={styles.percentage}>{Math.round(progress)}%</Text>
        
        <View style={styles.progressBarContainer}>
          <Animated.View 
            style={[
              styles.progressBar, 
              { width: `${progress}%` }
            ]} 
          />
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1000,
  },
  content: {
    backgroundColor: 'white',
    borderRadius: 16,
    padding: 32,
    alignItems: 'center',
    minWidth: 250,
  },
  icon: {
    fontSize: 48,
    marginBottom: 16,
  },
  title: {
    fontSize: 18,
    fontWeight: '600',
    color: '#111827',
    marginBottom: 8,
  },
  percentage: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#10B981',
    marginBottom: 16,
  },
  progressBarContainer: {
    width: '100%',
    height: 8,
    backgroundColor: '#E5E7EB',
    borderRadius: 4,
    overflow: 'hidden',
  },
  progressBar: {
    height: '100%',
    backgroundColor: '#10B981',
    borderRadius: 4,
  },
});
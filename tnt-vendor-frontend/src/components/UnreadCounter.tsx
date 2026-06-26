import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';

interface UnreadCounterProps {
  count: number;
  onPress?: () => void;
  size?: 'small' | 'medium' | 'large';
  showText?: boolean;
}

export default function UnreadCounter({ 
  count, 
  onPress,
  size = 'medium',
  showText = true 
}: UnreadCounterProps) {
  if (count <= 0) return null;

  const getSizeStyles = () => {
    switch (size) {
      case 'small':
        return { paddingHorizontal: 8, paddingVertical: 4, fontSize: 12 };
      case 'large':
        return { paddingHorizontal: 16, paddingVertical: 8, fontSize: 18 };
      default:
        return { paddingHorizontal: 12, paddingVertical: 6, fontSize: 14 };
    }
  };

  const sizeStyles = getSizeStyles();

  const Container = onPress ? TouchableOpacity : View;

  return (
    <Container 
      style={[styles.container, { paddingHorizontal: sizeStyles.paddingHorizontal, paddingVertical: sizeStyles.paddingVertical }]}
      onPress={onPress}
    >
      <Text style={[styles.text, { fontSize: sizeStyles.fontSize }]}>
        {showText ? `${count} unread` : count}
      </Text>
    </Container>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#EF4444',
    borderRadius: 12,
    alignSelf: 'flex-start',
  },
  text: {
    color: 'white',
    fontWeight: '600',
  },
});
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

interface NotificationBadgeProps {
  count: number;
  size?: 'small' | 'medium' | 'large';
  color?: string;
}

export default function NotificationBadge({ 
  count, 
  size = 'medium',
  color = '#EF4444' 
}: NotificationBadgeProps) {
  if (count <= 0) return null;

  const getSizeStyles = () => {
    switch (size) {
      case 'small':
        return { minWidth: 16, height: 16, paddingHorizontal: 4, fontSize: 10 };
      case 'large':
        return { minWidth: 28, height: 28, paddingHorizontal: 8, fontSize: 16 };
      default:
        return { minWidth: 22, height: 22, paddingHorizontal: 6, fontSize: 12 };
    }
  };

  const sizeStyles = getSizeStyles();

  return (
    <View style={[styles.badge, { backgroundColor: color, minWidth: sizeStyles.minWidth, height: sizeStyles.height }]}>
      <Text style={[styles.text, { fontSize: sizeStyles.fontSize }]}>
        {count > 99 ? '99+' : count}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    borderRadius: 11,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 6,
    borderWidth: 2,
    borderColor: 'white',
  },
  text: {
    color: 'white',
    fontWeight: 'bold',
    textAlign: 'center',
  },
});
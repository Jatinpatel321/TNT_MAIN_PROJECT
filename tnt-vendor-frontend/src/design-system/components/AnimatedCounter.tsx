// ─── AnimatedCounter ─────────────────────────────────────────────────
// Scrolls numbers like a slot machine — premium feel

import React, { useEffect, useRef } from 'react';
import { Text, Animated, StyleSheet, View } from 'react-native';
import { useTheme } from '../../context/ThemeContext';
import staticColors from '../tokens/colors';
import typography from '../tokens/typography';

interface AnimatedCounterProps {
  value: number;
  duration?: number;
  prefix?: string;
  suffix?: string;
  fontSize?: number;
  fontWeight?: string;
  color?: string;
  decimal?: number;
  format?: 'number' | 'currency' | 'percent';
}

export default function AnimatedCounter({
  value,
  duration = 600,
  prefix = '',
  suffix = '',
  fontSize = 32,
  fontWeight = '700',
  color,
  decimal = 0,
  format = 'number',
}: AnimatedCounterProps) {
  const { colors: themeColors } = useTheme();
  const activeColor = color || themeColors.textPrimary;
  const animatedValue = useRef(new Animated.Value(0)).current;

  const displayValue = useRef('0');

  useEffect(() => {
    animatedValue.setValue(0);
    const listener = animatedValue.addListener(({ value: val }) => {
      const display = computeDisplay(val, value, format, decimal);
      displayValue.current = display;
    });

    Animated.timing(animatedValue, {
      toValue: 1,
      duration,
      useNativeDriver: false,
    }).start();

    return () => {
      animatedValue.removeListener(listener);
    };
  }, [value, duration]);

  const computeDisplay = (
    progress: number,
    target: number,
    fmt: string,
    dec: number,
  ): string => {
    const current = progress * target;
    let formatted = '';

    switch (fmt) {
      case 'currency':
        const cleanPrefix = prefix.includes('₹') ? '' : '₹';
        return `${prefix}${cleanPrefix}${current.toFixed(dec)}${suffix}`;
      case 'percent':
        formatted = `${current.toFixed(dec)}%`;
        break;
      default:
        formatted = current.toFixed(dec);
        break;
    }

    return `${prefix}${formatted}${suffix}`;
  };

  const finalDisplay = computeDisplay(1, value, format, decimal);

  return (
    <Text
      style={[
        styles.text,
        {
          fontSize,
          fontWeight: fontWeight as any,
          color: activeColor,
          fontVariant: ['tabular-nums'],
        },
      ]}
    >
      {finalDisplay}
    </Text>
  );
}

const styles = StyleSheet.create({
  text: {
    fontVariant: ['tabular-nums'],
  },
});

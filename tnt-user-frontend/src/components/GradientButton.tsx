import React from 'react';
import { Pressable, StyleSheet, ViewStyle } from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import { Text } from 'react-native-paper';

export function GradientButton(props: {
  label: string;
  onPress: () => void;
  style?: ViewStyle;
  disabled?: boolean;
}) {
  return (
    <Pressable onPress={props.onPress} disabled={props.disabled} style={[styles.wrap, props.style]}>
      <LinearGradient
        colors={props.disabled ? ['#C7CCD1', '#C7CCD1'] : ['#6C63FF', '#4A90E2']}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={styles.gradient}
      >
        <Text style={styles.text}>{props.label}</Text>
      </LinearGradient>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  wrap: {
    borderRadius: 25,
    overflow: 'hidden',
  },
  gradient: {
    height: 50,
    paddingHorizontal: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  text: {
    color: '#FFFFFF',
    fontWeight: '700',
    fontSize: 16,
  },
});

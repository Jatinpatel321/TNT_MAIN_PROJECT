import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';

export function PrintOptionSelector(props: {
  label: string;
  value: string;
  current: string;
  onSelect: (value: string) => void;
}) {
  const active = props.current === props.value;
  return (
    <Pressable onPress={() => props.onSelect(props.value)} style={[styles.chip, active && styles.active]}> 
      <Text style={[styles.text, active && styles.textActive]}>{props.label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  chip: {
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 14,
    backgroundColor: '#F5F7FB',
    shadowColor: 'rgba(0,0,0,0.08)',
    shadowOpacity: 0.08,
    shadowOffset: { width: 0, height: 2 },
    shadowRadius: 6,
    elevation: 3,
  },
  active: {
    backgroundColor: '#6C63FF',
  },
  text: {
    fontSize: 14,
    fontWeight: '600',
    color: '#111827',
  },
  textActive: {
    color: '#FFFFFF',
  },
});

import React from 'react';
import { StyleSheet, ViewStyle } from 'react-native';
import { Card } from 'react-native-paper';

export function RoundedCard(props: { children: React.ReactNode; style?: ViewStyle; onPress?: () => void }) {
  return (
    <Card onPress={props.onPress} style={[styles.card, props.style]} mode="elevated">
      <Card.Content>{props.children}</Card.Content>
    </Card>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 18,
    marginVertical: 8,
  },
});

import React from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

export function Screen(props: { children: React.ReactNode; scroll?: boolean }) {
  const insets = useSafeAreaInsets();
  const content = (
    <View style={[styles.container, { paddingTop: insets.top, paddingBottom: insets.bottom }]}>
      {props.children}
    </View>
  );

  if (props.scroll) {
    return <ScrollView contentContainerStyle={styles.scroll}>{content}</ScrollView>;
  }

  return content;
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingHorizontal: 16,
  },
  scroll: {
    flexGrow: 1,
  },
});

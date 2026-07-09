import React from 'react';
import { RefreshControl, ScrollView, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useAppTheme } from '../theme/ThemeContext';

export function Screen(props: {
  children: React.ReactNode;
  scroll?: boolean;
  refreshing?: boolean;
  onRefresh?: () => void;
}) {
  const insets = useSafeAreaInsets();
  const { colors } = useAppTheme();

  const content = (
    <View
      style={[
        styles.container,
        { paddingTop: insets.top, paddingBottom: insets.bottom, backgroundColor: colors.background },
      ]}
    >
      {props.children}
    </View>
  );

  if (props.scroll) {
    return (
      <ScrollView
        contentContainerStyle={styles.scroll}
        style={{ backgroundColor: colors.background }}
        refreshControl={
          props.onRefresh ? (
            <RefreshControl
              refreshing={props.refreshing ?? false}
              onRefresh={props.onRefresh}
              tintColor={colors.primary}
              colors={[colors.primary]}
              progressBackgroundColor={colors.surface}
            />
          ) : undefined
        }
      >
        {content}
      </ScrollView>
    );
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

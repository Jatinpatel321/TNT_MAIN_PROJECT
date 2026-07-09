import React, { useMemo } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import MaterialCommunityIcons from 'react-native-vector-icons/MaterialCommunityIcons';
import { Text } from 'react-native-paper';
import { useAppTheme } from '../theme/ThemeContext';
import type { AppPalette } from '../theme/theme';

export function ShortcutCard(props: { title: string; subtitle: string; icon: string; onPress: () => void }) {
  const { colors } = useAppTheme();
  const styles = useMemo(() => makeStyles(colors), [colors]);
  return (
    <Pressable onPress={props.onPress} style={styles.card}>
      <View style={styles.iconWrap}>
        <MaterialCommunityIcons name={props.icon as any} size={28} color={colors.primary} />
      </View>
      <Text style={styles.title}>{props.title}</Text>
      <Text style={styles.subtitle}>{props.subtitle}</Text>
    </Pressable>
  );
}

const makeStyles = (colors: AppPalette) => StyleSheet.create({
  card: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: 18,
    padding: 14,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    shadowColor: 'rgba(0,0,0,0.1)',
    shadowOpacity: 0.1,
    shadowOffset: { width: 0, height: 4 },
    shadowRadius: 8,
    elevation: 4,
  },
  iconWrap: {
    width: 44,
    height: 44,
    borderRadius: 12,
    backgroundColor: colors.primarySoft,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 10,
  },
  title: {
    fontSize: 16,
    fontWeight: '700',
    color: colors.text,
  },
  subtitle: {
    fontSize: 14,
    fontWeight: '500',
    color: colors.muted,
    marginTop: 4,
  },
});

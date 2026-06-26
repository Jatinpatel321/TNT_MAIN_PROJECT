import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';
import MaterialCommunityIcons from 'react-native-vector-icons/MaterialCommunityIcons';

export type PickedFile = {
  uri: string;
  name: string;
  size?: number;
  mimeType?: string;
};

export function FileCard(props: { file: PickedFile; onRemove: () => void }) {
  const { file, onRemove } = props;
  return (
    <View style={styles.card}>
      <View style={styles.row}>
        <View style={styles.iconWrap}>
          <MaterialCommunityIcons name="file-pdf-box" size={28} color="#6C63FF" />
        </View>
        <View style={styles.info}>
          <Text style={styles.name} numberOfLines={1}>{file.name}</Text>
          {file.size ? <Text style={styles.meta}>{formatBytes(file.size)}</Text> : null}
        </View>
        <Pressable onPress={onRemove} style={styles.removeBtn}>
          <MaterialCommunityIcons name="close" size={20} color="#EF4444" />
        </Pressable>
      </View>
    </View>
  );
}

function formatBytes(bytes: number): string {
  if (!bytes) return '';
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 18,
    padding: 16,
    shadowColor: 'rgba(0,0,0,0.1)',
    shadowOpacity: 0.1,
    shadowOffset: { width: 0, height: 4 },
    shadowRadius: 8,
    elevation: 4,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  iconWrap: {
    width: 44,
    height: 44,
    borderRadius: 12,
    backgroundColor: '#F5F7FB',
    alignItems: 'center',
    justifyContent: 'center',
  },
  info: {
    flex: 1,
  },
  name: {
    fontSize: 16,
    fontWeight: '700',
  },
  meta: {
    fontSize: 14,
    color: '#6B7280',
    marginTop: 4,
  },
  removeBtn: {
    padding: 8,
  },
});

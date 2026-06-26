import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  FlatList,
  StyleSheet,
  TouchableOpacity,
  View,
} from 'react-native';
import { Text, TextInput } from 'react-native-paper';
import { useNavigation, useFocusEffect } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import MaterialCommunityIcons from 'react-native-vector-icons/MaterialCommunityIcons';

import type { RootStackParamList } from '../../types/navigation';
import { Screen } from '../../components/Screen';
import { RoundedCard } from '../../components/RoundedCard';
import { GradientButton } from '../../components/GradientButton';
import { createGroup, getMyGroups } from '../../services/groupService';
import { toApiError } from '../../services/apiClient';

type Nav = NativeStackNavigationProp<RootStackParamList>;

export function GroupCartScreen() {
  const navigation = useNavigation<Nav>();
  const [loading, setLoading] = useState(true);
  const [groups, setGroups] = useState<any[]>([]);
  const [groupName, setGroupName] = useState('');
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const list = await getMyGroups();
      setGroups(list);
    } catch (e) {
      Alert.alert('Failed to load groups', toApiError(e).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const onCreate = async () => {
    if (!groupName.trim()) return;
    try {
      setCreating(true);
      const created = await createGroup(groupName.trim());
      setGroupName('');
      await load();
      if (created?.id) {
        navigation.navigate('GroupDetail', { groupId: created.id });
      }
    } catch (e) {
      Alert.alert('Create failed', toApiError(e).message);
    } finally {
      setCreating(false);
    }
  };

  const statusColor = (s: string) => {
    if (s === 'active') return '#22C55E';
    if (s === 'ordered') return '#F59E0B';
    if (s === 'completed') return '#6C63FF';
    return '#6B7280';
  };

  return (
    <Screen>
      <View style={styles.header}>
        <Text style={styles.title}>Group Cart</Text>
        <Text style={styles.sub}>Order together with friends and split the bill.</Text>
      </View>

      {/* ── Create ── */}
      <RoundedCard>
        <View style={styles.createRow}>
          <TextInput
            label="New group name"
            value={groupName}
            onChangeText={setGroupName}
            mode="outlined"
            style={styles.createInput}
            dense
          />
          <GradientButton
            label={creating ? '...' : 'Create'}
            onPress={onCreate}
            disabled={!groupName.trim() || creating}
            style={styles.createBtn}
          />
        </View>
      </RoundedCard>

      {/* ── List ── */}
      {loading ? (
        <View style={styles.center}><ActivityIndicator color="#6C63FF" size="large" /></View>
      ) : groups.length === 0 ? (
        <View style={styles.emptyWrap}>
          <MaterialCommunityIcons name="account-group-outline" size={64} color="#D1D5DB" />
          <Text style={styles.emptyText}>No groups yet</Text>
          <Text style={styles.emptyHint}>Create one above and invite your friends!</Text>
        </View>
      ) : (
        <FlatList
          data={groups}
          keyExtractor={(g) => String(g.id)}
          contentContainerStyle={styles.list}
          renderItem={({ item: g }) => (
            <TouchableOpacity
              activeOpacity={0.7}
              onPress={() => navigation.navigate('GroupDetail', { groupId: g.id })}
            >
              <RoundedCard>
                <View style={styles.groupRow}>
                  <View style={styles.avatar}>
                    <MaterialCommunityIcons name="account-group" size={28} color="#6C63FF" />
                  </View>
                  <View style={styles.groupInfo}>
                    <Text style={styles.groupName}>{g.name ?? `Group #${g.id}`}</Text>
                    <View style={styles.statusRow}>
                      <View style={[styles.statusDot, { backgroundColor: statusColor(g.status ?? 'active') }]} />
                      <Text style={styles.statusText}>{(g.status ?? 'active').toUpperCase()}</Text>
                      {g.members && (
                        <Text style={styles.memberCount}> · {g.members.length ?? '?'} members</Text>
                      )}
                    </View>
                  </View>
                  <MaterialCommunityIcons name="chevron-right" size={24} color="#9CA3AF" />
                </View>
              </RoundedCard>
            </TouchableOpacity>
          )}
        />
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { paddingTop: 18, paddingBottom: 4 },
  title: { fontSize: 22, fontWeight: '900', color: '#1F2937' },
  sub: { opacity: 0.6, marginTop: 4, lineHeight: 18, fontSize: 14 },
  createRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  createInput: { flex: 1, backgroundColor: 'transparent' },
  createBtn: { minWidth: 90 },
  center: { paddingVertical: 40, alignItems: 'center' },
  emptyWrap: { alignItems: 'center', paddingTop: 60 },
  emptyText: { fontSize: 18, fontWeight: '700', color: '#9CA3AF', marginTop: 12 },
  emptyHint: { fontSize: 14, color: '#9CA3AF', marginTop: 4 },
  list: { paddingBottom: 20 },
  groupRow: { flexDirection: 'row', alignItems: 'center' },
  avatar: {
    width: 48, height: 48, borderRadius: 24,
    backgroundColor: '#EEF2FF', alignItems: 'center', justifyContent: 'center',
    marginRight: 14,
  },
  groupInfo: { flex: 1 },
  groupName: { fontSize: 16, fontWeight: '800', color: '#1F2937' },
  statusRow: { flexDirection: 'row', alignItems: 'center', marginTop: 4 },
  statusDot: { width: 8, height: 8, borderRadius: 4, marginRight: 6 },
  statusText: { fontSize: 12, fontWeight: '700', color: '#6B7280' },
  memberCount: { fontSize: 12, color: '#9CA3AF' },
});

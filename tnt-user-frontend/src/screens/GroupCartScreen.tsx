import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Alert, StyleSheet, View } from 'react-native';
import { Text, TextInput } from 'react-native-paper';

import { Screen } from '../components/Screen';
import { RoundedCard } from '../components/RoundedCard';
import { GradientButton } from '../components/GradientButton';
import {
  addGroupCartItem,
  createGroup,
  getGroup,
  getMyGroups,
  inviteMember,
  lockGroupSlot,
  placeGroupOrder,
} from '../services/groupService';
import { toApiError } from '../services/apiClient';

export function GroupCartScreen() {
  const [loading, setLoading] = useState(true);
  const [groups, setGroups] = useState<any[]>([]);
  const [groupName, setGroupName] = useState('');

  const [selectedGroupId, setSelectedGroupId] = useState<number | null>(null);
  const [selectedGroup, setSelectedGroup] = useState<any | null>(null);

  const [invitePhone, setInvitePhone] = useState('');
  const [menuItemId, setMenuItemId] = useState('');
  const [quantity, setQuantity] = useState('1');
  const [slotId, setSlotId] = useState('');

  const load = async () => {
    try {
      setLoading(true);
      const list = await getMyGroups();
      setGroups(list);
    } catch (e) {
      Alert.alert('Failed to load groups', toApiError(e).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const selectGroup = async (id: number) => {
    try {
      setSelectedGroupId(id);
      const detail = await getGroup(id);
      setSelectedGroup(detail);
    } catch (e) {
      Alert.alert('Failed to load group', toApiError(e).message);
    }
  };

  const onCreate = async () => {
    try {
      await createGroup(groupName.trim());
      setGroupName('');
      await load();
    } catch (e) {
      Alert.alert('Create failed', toApiError(e).message);
    }
  };

  const onInvite = async () => {
    if (!selectedGroupId) return;
    try {
      await inviteMember(selectedGroupId, invitePhone.trim());
      setInvitePhone('');
      await selectGroup(selectedGroupId);
    } catch (e) {
      Alert.alert('Invite failed', toApiError(e).message);
    }
  };

  const onAddItem = async () => {
    if (!selectedGroupId) return;
    try {
      await addGroupCartItem(selectedGroupId, Number(menuItemId), Number(quantity));
      await selectGroup(selectedGroupId);
    } catch (e) {
      Alert.alert('Add failed', toApiError(e).message);
    }
  };

  const onLockSlot = async () => {
    if (!selectedGroupId) return;
    try {
      await lockGroupSlot(selectedGroupId, Number(slotId), 30);
      await selectGroup(selectedGroupId);
    } catch (e) {
      Alert.alert('Lock failed', toApiError(e).message);
    }
  };

  const onPlaceOrder = async () => {
    if (!selectedGroupId) return;
    try {
      const res = await placeGroupOrder(selectedGroupId);
      Alert.alert('Group order placed', JSON.stringify(res));
      await selectGroup(selectedGroupId);
    } catch (e) {
      Alert.alert('Order failed', toApiError(e).message);
    }
  };

  return (
    <Screen scroll>
      <View style={styles.header}>
        <Text variant="headlineSmall" style={styles.title}>Group Cart</Text>
        <Text style={styles.sub}>Create groups, invite members, lock slots, and place group orders.</Text>
      </View>

      <RoundedCard>
        <TextInput label="New group name" value={groupName} onChangeText={setGroupName} mode="outlined" style={styles.input} />
        <GradientButton label="Create Group" onPress={onCreate} disabled={!groupName.trim()} />
      </RoundedCard>

      {loading ? (
        <View style={styles.center}><ActivityIndicator /></View>
      ) : groups.length === 0 ? (
        <Text style={styles.empty}>No groups yet.</Text>
      ) : (
        groups.map((g) => (
          <RoundedCard key={g.id} onPress={() => selectGroup(g.id)}>
            <Text variant="titleMedium" style={styles.name}>{g.name ?? `Group #${g.id}`}</Text>
            <Text style={styles.meta}>Tap to manage</Text>
          </RoundedCard>
        ))
      )}

      {selectedGroupId && (
        <>
          <View style={styles.sectionHeader}>
            <Text variant="titleMedium" style={styles.sectionTitle}>Manage Group #{selectedGroupId}</Text>
          </View>

          <RoundedCard>
            <Text style={styles.blockTitle}>Group Snapshot</Text>
            <Text style={styles.muted} numberOfLines={10}>{selectedGroup ? JSON.stringify(selectedGroup) : 'Loading…'}</Text>
          </RoundedCard>

          <RoundedCard>
            <Text style={styles.blockTitle}>Invite member</Text>
            <TextInput label="Phone" value={invitePhone} onChangeText={setInvitePhone} mode="outlined" style={styles.input} />
            <GradientButton label="Invite" onPress={onInvite} disabled={!invitePhone.trim()} />
          </RoundedCard>

          <RoundedCard>
            <Text style={styles.blockTitle}>Add item to group cart</Text>
            <TextInput label="Menu Item ID" value={menuItemId} onChangeText={setMenuItemId} mode="outlined" style={styles.input} keyboardType="number-pad" />
            <TextInput label="Quantity" value={quantity} onChangeText={setQuantity} mode="outlined" style={styles.input} keyboardType="number-pad" />
            <GradientButton label="Add Item" onPress={onAddItem} disabled={!menuItemId.trim()} />
          </RoundedCard>

          <RoundedCard>
            <Text style={styles.blockTitle}>Lock slot</Text>
            <TextInput label="Slot ID" value={slotId} onChangeText={setSlotId} mode="outlined" style={styles.input} keyboardType="number-pad" />
            <GradientButton label="Lock Slot (30 min)" onPress={onLockSlot} disabled={!slotId.trim()} />
          </RoundedCard>

          <View style={styles.actions}>
            <GradientButton label="Place Group Order" onPress={onPlaceOrder} />
          </View>
        </>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    paddingTop: 18,
    paddingBottom: 8,
  },
  title: {
    fontWeight: '900',
  },
  sub: {
    opacity: 0.7,
    marginTop: 4,
    lineHeight: 18,
  },
  input: {
    backgroundColor: 'transparent',
    marginBottom: 10,
  },
  center: {
    paddingVertical: 24,
    alignItems: 'center',
  },
  empty: {
    opacity: 0.7,
    paddingTop: 12,
  },
  name: {
    fontWeight: '800',
  },
  meta: {
    opacity: 0.7,
    marginTop: 4,
  },
  sectionHeader: {
    marginTop: 14,
    marginBottom: 6,
  },
  sectionTitle: {
    fontWeight: '900',
  },
  blockTitle: {
    fontWeight: '800',
    marginBottom: 6,
  },
  muted: {
    opacity: 0.75,
  },
  actions: {
    paddingVertical: 14,
  },
});

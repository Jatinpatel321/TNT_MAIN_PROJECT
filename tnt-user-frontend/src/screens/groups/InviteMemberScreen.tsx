import React, { useState } from 'react';
import { Alert, StyleSheet, View } from 'react-native';
import { Text, TextInput } from 'react-native-paper';
import { useNavigation, useRoute } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RouteProp } from '@react-navigation/native';
import MaterialCommunityIcons from 'react-native-vector-icons/MaterialCommunityIcons';

import type { RootStackParamList } from '../../types/navigation';
import { Screen } from '../../components/Screen';
import { RoundedCard } from '../../components/RoundedCard';
import { GradientButton } from '../../components/GradientButton';
import { inviteMember } from '../../services/groupService';
import { toApiError } from '../../services/apiClient';

type Nav = NativeStackNavigationProp<RootStackParamList>;
type Route = RouteProp<RootStackParamList, 'InviteMember'>;

export function InviteMemberScreen() {
  const navigation = useNavigation<Nav>();
  const { params } = useRoute<Route>();
  const groupId = params.groupId;

  const [phone, setPhone] = useState('');
  const [sending, setSending] = useState(false);
  const [invited, setInvited] = useState<string[]>([]);

  const onInvite = async () => {
    const trimmed = phone.trim();
    if (!trimmed) return;
    try {
      setSending(true);
      await inviteMember(groupId, trimmed);
      setInvited(prev => [...prev, trimmed]);
      setPhone('');
      Alert.alert('Invited!', `${trimmed} has been added to the group.`);
    } catch (e) {
      Alert.alert('Invite failed', toApiError(e).message);
    } finally {
      setSending(false);
    }
  };

  return (
    <Screen scroll>
      <View style={styles.header}>
        <MaterialCommunityIcons name="account-multiple-plus" size={48} color="#6C63FF" />
        <Text style={styles.title}>Invite Friends</Text>
        <Text style={styles.subtitle}>Enter a phone number to add them to your group</Text>
      </View>

      <RoundedCard>
        <TextInput
          label="Phone number"
          value={phone}
          onChangeText={setPhone}
          mode="outlined"
          style={styles.input}
          keyboardType="phone-pad"
          left={<TextInput.Icon icon="phone" />}
          autoFocus
        />
        <GradientButton
          label={sending ? 'Inviting...' : 'Send Invite'}
          onPress={onInvite}
          disabled={!phone.trim() || sending}
        />
      </RoundedCard>

      {invited.length > 0 && (
        <RoundedCard>
          <Text style={styles.sectionTitle}>Invited ({invited.length})</Text>
          {invited.map((p, i) => (
            <View key={i} style={styles.invitedRow}>
              <View style={styles.avatar}>
                <MaterialCommunityIcons name="check" size={18} color="#22C55E" />
              </View>
              <Text style={styles.invitedPhone}>{p}</Text>
            </View>
          ))}
        </RoundedCard>
      )}

      <View style={styles.footer}>
        <GradientButton
          label="Back to Group"
          onPress={() => navigation.goBack()}
        />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { alignItems: 'center', paddingTop: 30, paddingBottom: 20 },
  title: { fontSize: 22, fontWeight: '900', color: '#1F2937', marginTop: 12 },
  subtitle: { fontSize: 14, color: '#9CA3AF', marginTop: 4, textAlign: 'center' },
  input: { backgroundColor: 'transparent', marginBottom: 16 },
  sectionTitle: { fontSize: 16, fontWeight: '800', color: '#1F2937', marginBottom: 8 },
  invitedRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 6 },
  avatar: {
    width: 32, height: 32, borderRadius: 16,
    backgroundColor: '#F0FDF4', alignItems: 'center', justifyContent: 'center',
    marginRight: 12,
  },
  invitedPhone: { fontSize: 14, fontWeight: '600', color: '#374151' },
  footer: { marginTop: 20 },
});

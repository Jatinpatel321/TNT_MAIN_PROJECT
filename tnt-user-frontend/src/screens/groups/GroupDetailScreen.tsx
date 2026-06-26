import React, { useCallback, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  View,
} from 'react-native';
import { Text, TextInput } from 'react-native-paper';
import { useNavigation, useRoute, useFocusEffect } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RouteProp } from '@react-navigation/native';
import MaterialCommunityIcons from 'react-native-vector-icons/MaterialCommunityIcons';

import type { RootStackParamList } from '../../types/navigation';
import { Screen } from '../../components/Screen';
import { RoundedCard } from '../../components/RoundedCard';
import { GradientButton } from '../../components/GradientButton';
import { formatMoneyPaise } from '../../utils/format';
import {
  addGroupCartItem,
  getGroup,
  getPaymentSplits,
  inviteMember,
  lockGroupSlot,
  placeGroupOrder,
  removeGroupCartItem,
  setPaymentSplit,
} from '../../services/groupService';
import { mockPayment } from '../../services/paymentService';
import { toApiError } from '../../services/apiClient';
import { useAuth } from '../../hooks/useAuth';
import {
  storeGroupOrderData,
  getStoredGroupOrderData,
  clearGroupOrderData,
  batchCheckPaymentStatus,
  type MemberOrderInfo,
} from '../../services/groupPaymentService';

type Nav = NativeStackNavigationProp<RootStackParamList>;
type Route = RouteProp<RootStackParamList, 'GroupDetail'>;

// ── Helpers ──────────────────────────────────────────────────────────────

/** Extract member name from a member record. */
function memberName(m: any): string {
  const u = m.user ?? {};
  return u.name ?? u.phone ?? `User #${m.user_id}`;
}

/** Initial letters for avatar. */
function memberInitial(m: any): string {
  return memberName(m)[0]?.toUpperCase() ?? '?';
}

// ── Component ────────────────────────────────────────────────────────────

export function GroupDetailScreen() {
  const navigation = useNavigation<Nav>();
  const { params } = useRoute<Route>();
  const { user } = useAuth();
  const groupId = params.groupId;

  const [loading, setLoading] = useState(true);
  const [group, setGroup] = useState<any>(null);
  const [splits, setSplits] = useState<any[]>([]);

  // invites
  const [invitePhone, setInvitePhone] = useState('');
  const [inviting, setInviting] = useState(false);

  // add item
  const [menuItemId, setMenuItemId] = useState('');
  const [quantity, setQuantity] = useState('1');

  // slot
  const [slotId, setSlotId] = useState('');

  // split type chosen by the owner (affects all members)
  const [splitType, setSplitType] = useState<string>('equal');
  // per‑member custom amounts keyed by user_id
  const [customAmounts, setCustomAmounts] = useState<Record<number, string>>({});
  const [savingSplit, setSavingSplit] = useState(false);

  // order placement
  const [placingOrder, setPlacingOrder] = useState(false);

  // payment status after order placed
  const [groupOrders, setGroupOrders] = useState<MemberOrderInfo[]>([]);
  const [paymentStatusMap, setPaymentStatusMap] = useState<Record<number, 'paid' | 'unpaid'>>({});
  const [checkingPayments, setCheckingPayments] = useState(false);

  const isOwner = group?.owner_id === user?.id;
  const members: any[] = group?.members ?? [];
  const cartItems: any[] = group?.cart_items ?? [];
  const slotLock = group?.slot_lock;
  const totalAmount = cartItems.reduce(
    (sum: number, ci: any) => sum + (ci.price_at_time ?? 0) * (ci.quantity ?? 1),
    0,
  );
  const totalAmountPaise = totalAmount * 100;
  const memberCount = members.length || 1;

  // ── Load group data ──────────────────────────────────────────────────

  const reload = useCallback(async () => {
    try {
      setLoading(true);
      const [detail, splitList] = await Promise.all([
        getGroup(groupId),
        getPaymentSplits(groupId).catch(() => []),
      ]);
      setGroup(detail);
      const arr = Array.isArray(splitList) ? splitList : [];
      setSplits(arr);

      // Seed split type and custom amounts from existing splits
      if (arr.length > 0) {
        setSplitType(arr[0].split_type ?? 'equal');
        const customMap: Record<number, string> = {};
        for (const s of arr) {
          if (s.amount != null) customMap[s.user_id] = String(s.amount);
        }
        setCustomAmounts(customMap);
      }

      // Restore stored order data and refresh payment statuses
      const stored = await getStoredGroupOrderData(groupId);
      if (stored && detail?.status === 'ordered') {
        setGroupOrders(stored.orders);
      } else if (stored && detail?.status !== 'ordered') {
        await clearGroupOrderData(groupId);
        setGroupOrders([]);
      }
    } catch (e) {
      Alert.alert('Error', toApiError(e).message);
    } finally {
      setLoading(false);
    }
  }, [groupId]);

  useFocusEffect(useCallback(() => { reload(); }, [reload]));

  // ── Poll payment status when group is ordered ────────────────────────

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const checkPayments = useCallback(async () => {
    if (groupOrders.length === 0) return;
    setCheckingPayments(true);
    const orderIds = groupOrders.map((o) => o.order_id);
    const map = await batchCheckPaymentStatus(orderIds);
    setPaymentStatusMap(map);
    setCheckingPayments(false);
  }, [groupOrders]);

  useFocusEffect(
    useCallback(() => {
      if (group?.status === 'ordered' && groupOrders.length > 0) {
        checkPayments();
        pollRef.current = setInterval(checkPayments, 8000);
      }
      return () => {
        if (pollRef.current) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
      };
    }, [group?.status, groupOrders, checkPayments]),
  );

  // ── Handlers ─────────────────────────────────────────────────────────

  const onInvite = async () => {
    if (!invitePhone.trim()) return;
    try {
      setInviting(true);
      await inviteMember(groupId, invitePhone.trim());
      setInvitePhone('');
      Alert.alert('Invited!', 'Member added to the group.');
      await reload();
    } catch (e) {
      Alert.alert('Invite failed', toApiError(e).message);
    } finally {
      setInviting(false);
    }
  };

  const onAddItem = async () => {
    if (!menuItemId.trim()) return;
    try {
      await addGroupCartItem(groupId, Number(menuItemId), Number(quantity) || 1);
      setMenuItemId('');
      setQuantity('1');
      await reload();
    } catch (e) {
      Alert.alert('Add failed', toApiError(e).message);
    }
  };

  const onRemoveItem = async (itemId: number) => {
    try {
      await removeGroupCartItem(groupId, itemId);
      await reload();
    } catch (e) {
      Alert.alert('Remove failed', toApiError(e).message);
    }
  };

  const onLockSlot = async () => {
    if (!slotId.trim()) return;
    try {
      await lockGroupSlot(groupId, Number(slotId), 30);
      setSlotId('');
      Alert.alert('Slot locked', 'Pickup slot locked for 30 minutes.');
      await reload();
    } catch (e) {
      Alert.alert('Lock failed', toApiError(e).message);
    }
  };

  /** Owner picks the split type for the whole group. */
  const onSelectSplitType = async (type: string) => {
    setSplitType(type);
    if (type !== 'custom') {
      // For equal/unified, set for all members at once
      try {
        setSavingSplit(true);
        for (const m of members) {
          await setPaymentSplit(groupId, { split_type: type });
        }
        await reload();
        Alert.alert('Split updated', `Bill will be split ${type}ly.`);
      } catch (e) {
        Alert.alert('Split failed', toApiError(e).message);
      } finally {
        setSavingSplit(false);
      }
    }
  };

  /** Save custom amounts per member. */
  const onSaveCustomSplit = async () => {
    try {
      setSavingSplit(true);
      for (const m of members) {
        const amtStr = customAmounts[m.user_id]?.trim();
        const amount = amtStr ? parseFloat(amtStr) : 0;
        if (isNaN(amount) || amount < 0) {
          Alert.alert('Invalid amount', `Enter a valid amount for ${memberName(m)}.`);
          setSavingSplit(false);
          return;
        }
        await setPaymentSplit(groupId, {
          split_type: 'custom',
          amount,
        });
      }
      await reload();
      Alert.alert('Custom split saved!');
    } catch (e) {
      Alert.alert('Save failed', toApiError(e).message);
    } finally {
      setSavingSplit(false);
    }
  };

  /** Owner places the group order. */
  const onPlaceOrder = async () => {
    Alert.alert(
      'Confirm Group Order',
      `Total: ${formatMoneyPaise(totalAmountPaise)}\nPlace order for all members?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Place Order',
          onPress: async () => {
            try {
              setPlacingOrder(true);
              const res = await placeGroupOrder(groupId);
              const orders: MemberOrderInfo[] = res.orders ?? [];
              const orderData = {
                groupId,
                orders,
                total_amount: res.total_amount ?? totalAmountPaise,
              };
              await storeGroupOrderData(groupId, orderData);
              setGroupOrders(orders);
              Alert.alert('Order Placed!', `${orders.length} orders created.`);
              await reload();
            } catch (e) {
              Alert.alert('Order failed', toApiError(e).message);
            } finally {
              setPlacingOrder(false);
            }
          },
        },
      ],
    );
  };

  /** Current user pays their share. */
  const onPayShare = async (orderId: number, amountPaise: number) => {
    const rupees = amountPaise / 100;
    Alert.alert(
      'Pay Your Share',
      `Pay ${formatMoneyPaise(amountPaise)} for your order?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: `Pay ₹${rupees.toFixed(2)}`,
          onPress: async () => {
            try {
              const result = await mockPayment(orderId, 'UPI', amountPaise);
              if (result.status === 'SUCCESS') {
                Alert.alert('Payment Successful!', result.message);
                // Refresh payment statuses
                const map = await batchCheckPaymentStatus(
                  groupOrders.map((o) => o.order_id),
                );
                setPaymentStatusMap(map);
              }
            } catch (e) {
              Alert.alert('Payment failed', toApiError(e).message);
            }
          },
        },
      ],
    );
  };

  const equalShare = totalAmountPaise > 0 ? Math.floor(totalAmountPaise / memberCount) : 0;

  const currentUserOrder = groupOrders.find((o) => o.member_id === user?.id);

  // ── Render ───────────────────────────────────────────────────────────

  if (loading) {
    return (
      <Screen>
        <View style={styles.loadingWrap}><ActivityIndicator size="large" color="#6C63FF" /></View>
      </Screen>
    );
  }

  return (
    <Screen scroll>
      {/* ── Header ── */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
          <MaterialCommunityIcons name="arrow-left" size={24} color="#1F2937" />
        </TouchableOpacity>
        <View style={{ flex: 1 }}>
          <Text style={styles.title}>{group?.name ?? `Group #${groupId}`}</Text>
          <Text style={styles.statusBadge}>
            {(group?.status ?? 'active').toUpperCase()}
          </Text>
        </View>
      </View>

      {/* ── Members ── */}
      <RoundedCard>
        <View style={styles.sectionRow}>
          <Text style={styles.sectionTitle}>Members ({members.length})</Text>
          <TouchableOpacity onPress={() => navigation.navigate('InviteMember', { groupId })}>
            <MaterialCommunityIcons name="account-plus" size={24} color="#6C63FF" />
          </TouchableOpacity>
        </View>
        {members.map((m: any) => {
          const myOrderInfo = groupOrders.find((o) => o.member_id === m.user_id);
          const isMe = m.user_id === user?.id;
          const paidStatus = myOrderInfo ? paymentStatusMap[myOrderInfo.order_id] : null;
          return (
            <View key={m.id} style={styles.memberRow}>
              <View style={styles.memberAvatar}>
                <Text style={styles.memberInitial}>{memberInitial(m)}</Text>
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.memberName}>
                  {memberName(m)} {isMe ? '(You)' : ''}
                </Text>
                <Text style={styles.memberRole}>
                  {m.role === 'owner' ? 'Owner' : 'Member'}
                </Text>
              </View>
              {paidStatus && (
                <View style={[styles.paymentBadge, paidStatus === 'paid' ? styles.paidBadge : styles.unpaidBadge]}>
                  <Text style={[styles.paymentBadgeText, paidStatus === 'paid' ? styles.paidText : styles.unpaidText]}>
                    {paidStatus === 'paid' ? 'PAID' : 'UNPAID'}
                  </Text>
                </View>
              )}
            </View>
          );
        })}

        {/* Quick inline invite */}
        <View style={styles.inviteRow}>
          <TextInput
            label="Phone number"
            value={invitePhone}
            onChangeText={setInvitePhone}
            mode="outlined"
            style={styles.inviteInput}
            dense
            keyboardType="phone-pad"
          />
          <GradientButton
            label={inviting ? '...' : 'Invite'}
            onPress={onInvite}
            disabled={!invitePhone.trim() || inviting}
            style={styles.inviteBtn}
          />
        </View>
      </RoundedCard>

      {/* ── Shared Cart ── */}
      <RoundedCard>
        <Text style={styles.sectionTitle}>Shared Cart</Text>
        {cartItems.length === 0 ? (
          <Text style={styles.muted}>No items yet. Add items below.</Text>
        ) : (
          cartItems.map((ci: any) => {
            const mi = ci.menu_item ?? {};
            const owner = ci.owner ?? {};
            const isMyItem = ci.owner_id === user?.id;
            return (
              <View key={ci.id} style={styles.cartItemRow}>
                <View style={styles.cartItemIcon}>
                  <MaterialCommunityIcons name="food" size={20} color="#6C63FF" />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.cartItemName}>{mi.name ?? `Item #${ci.menu_item_id}`}</Text>
                  <Text style={styles.cartItemMeta}>
                    {ci.quantity}x · {formatMoneyPaise((ci.price_at_time ?? 0) * 100)}
                    {' · Added by '}
                    {owner.name ?? owner.phone ?? `User #${ci.owner_id}`}
                  </Text>
                </View>
                {isMyItem && (
                  <TouchableOpacity onPress={() => onRemoveItem(ci.id)}>
                    <MaterialCommunityIcons name="trash-can-outline" size={20} color="#EF4444" />
                  </TouchableOpacity>
                )}
              </View>
            );
          })
        )}
        <View style={styles.totalRow}>
          <Text style={styles.totalLabel}>Total</Text>
          <Text style={styles.totalValue}>{formatMoneyPaise(totalAmountPaise)}</Text>
        </View>
      </RoundedCard>

      {/* ── Add Item ── */}
      {group?.status === 'active' && (
        <RoundedCard>
          <Text style={styles.sectionTitle}>Add Item</Text>
          <TextInput
            label="Menu Item ID"
            value={menuItemId}
            onChangeText={setMenuItemId}
            mode="outlined"
            style={styles.input}
            dense
            keyboardType="number-pad"
          />
          <TextInput
            label="Quantity"
            value={quantity}
            onChangeText={setQuantity}
            mode="outlined"
            style={styles.input}
            dense
            keyboardType="number-pad"
          />
          <GradientButton label="Add to Shared Cart" onPress={onAddItem} disabled={!menuItemId.trim()} />
        </RoundedCard>
      )}

      {/* ── Payment Split (only before ordering) ── */}
      {group?.status === 'active' && (
        <RoundedCard>
          <Text style={styles.sectionTitle}>Split Payment</Text>
          <Text style={styles.muted}>Choose how to split the bill among members.</Text>

          {/* Split type selector – only owner can change */}
          <View style={styles.splitBtns}>
            <TouchableOpacity
              style={[styles.splitBtn, splitType === 'equal' && styles.splitBtnActive]}
              onPress={() => onSelectSplitType('equal')}
              disabled={!isOwner || savingSplit}
            >
              <MaterialCommunityIcons name="scale-balance" size={24} color={splitType === 'equal' ? '#fff' : '#6C63FF'} />
              <Text style={[styles.splitLabel, splitType === 'equal' && styles.splitLabelActive]}>Equal</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.splitBtn, splitType === 'unified' && styles.splitBtnActive]}
              onPress={() => onSelectSplitType('unified')}
              disabled={!isOwner || savingSplit}
            >
              <MaterialCommunityIcons name="credit-card" size={24} color={splitType === 'unified' ? '#fff' : '#F59E0B'} />
              <Text style={[styles.splitLabel, splitType === 'unified' && styles.splitLabelActive]}>One Pays</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.splitBtn, splitType === 'custom' && styles.splitBtnActive]}
              onPress={() => onSelectSplitType('custom')}
              disabled={!isOwner || savingSplit}
            >
              <MaterialCommunityIcons name="pencil-ruler" size={24} color={splitType === 'custom' ? '#fff' : '#22C55E'} />
              <Text style={[styles.splitLabel, splitType === 'custom' && styles.splitLabelActive]}>Custom</Text>
            </TouchableOpacity>
          </View>

          {/* Split summary */}
          <View style={styles.splitSummary}>
            {splitType === 'equal' && (
              <Text style={styles.splitHint}>
                Each person pays {formatMoneyPaise(equalShare)}
              </Text>
            )}
            {splitType === 'unified' && (
              <Text style={styles.splitHint}>
                The group owner (you) pays the full {formatMoneyPaise(totalAmountPaise)}
              </Text>
            )}
          </View>

          {/* Custom per‑member inputs */}
          {splitType === 'custom' && (
            <>
              <Text style={styles.sectionSubTitle}>Set amounts per member:</Text>
              {members.map((m: any) => {
                const isMe = m.user_id === user?.id;
                const currentVal = customAmounts[m.user_id] ?? '';
                return (
                  <View key={m.user_id} style={styles.customRow}>
                    <Text style={styles.customLabel}>
                      {memberName(m)} {isMe ? '(You)' : ''}
                    </Text>
                    <TextInput
                      label="Amount (₹)"
                      value={currentVal}
                      onChangeText={(val) =>
                        setCustomAmounts((prev) => ({ ...prev, [m.user_id]: val }))
                      }
                      mode="outlined"
                      dense
                      keyboardType="decimal-pad"
                      style={styles.customInput}
                    />
                  </View>
                );
              })}
              <View style={{ marginTop: 10 }}>
                <GradientButton
                  label={savingSplit ? 'Saving...' : 'Save Custom Split'}
                  onPress={onSaveCustomSplit}
                  disabled={!isOwner || savingSplit}
                />
              </View>
            </>
          )}

          {savingSplit && (
            <View style={styles.savingOverlay}>
              <ActivityIndicator size="small" color="#6C63FF" />
              <Text style={styles.savingText}>Saving...</Text>
            </View>
          )}
        </RoundedCard>
      )}

      {/* ── Pickup Slot ── */}
      {group?.status === 'active' && (
        <RoundedCard>
          <Text style={styles.sectionTitle}>Pickup Slot</Text>
          {slotLock ? (
            <View style={styles.slotLockedRow}>
              <MaterialCommunityIcons name="lock-clock" size={24} color="#22C55E" />
              <Text style={styles.slotLockedText}>
                Slot #{slotLock.slot_id} locked until{' '}
                {new Date(slotLock.expires_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </Text>
            </View>
          ) : (
            <>
              <TextInput
                label="Slot ID"
                value={slotId}
                onChangeText={setSlotId}
                mode="outlined"
                style={styles.input}
                dense
                keyboardType="number-pad"
              />
              <GradientButton label="Lock Slot (30 min)" onPress={onLockSlot} disabled={!slotId.trim()} />
            </>
          )}
        </RoundedCard>
      )}

      {/* ── Place Order (owner only) ── */}
      {isOwner && group?.status === 'active' && cartItems.length > 0 && slotLock && (
        <View style={styles.checkoutWrap}>
          <GradientButton
            label={placingOrder ? 'Placing...' : 'Place Group Order'}
            onPress={onPlaceOrder}
            disabled={placingOrder}
          />
        </View>
      )}

      {/* ── Payment Status & Pay Your Share ── */}
      {group?.status === 'ordered' && (
        <>
          {/* Payment summary */}
          {groupOrders.length > 0 && (
            <RoundedCard>
              <View style={styles.sectionRow}>
                <Text style={styles.sectionTitle}>Payment Status</Text>
                {checkingPayments && (
                  <ActivityIndicator size="small" color="#6C63FF" />
                )}
              </View>
              {groupOrders.map((o) => {
                const status = paymentStatusMap[o.order_id] ?? 'unpaid';
                const m = members.find((mm: any) => mm.user_id === o.member_id);
                const displayName = m ? memberName(m) : `User #${o.member_id}`;
                const isMe = o.member_id === user?.id;
                return (
                  <View key={o.order_id} style={styles.paymentRow}>
                    <View style={styles.paymentInfo}>
                      <Text style={styles.paymentMember}>
                        {displayName} {isMe ? '(You)' : ''}
                      </Text>
                      <Text style={styles.paymentAmount}>
                        {formatMoneyPaise(o.payable_amount)}
                      </Text>
                    </View>
                    <View
                      style={[
                        styles.paymentStatusPill,
                        status === 'paid' ? styles.paidStatusPill : styles.unpaidStatusPill,
                      ]}
                    >
                      <Text
                        style={[
                          styles.paymentStatusPillText,
                          status === 'paid' ? styles.paidStatusText : styles.unpaidStatusText,
                        ]}
                      >
                        {status === 'paid' ? 'Paid' : 'Unpaid'}
                      </Text>
                    </View>
                    {/* Pay button for current user if unpaid */}
                    {isMe && status === 'unpaid' && (
                      <GradientButton
                        label={`Pay ${formatMoneyPaise(o.payable_amount)}`}
                        onPress={() => onPayShare(o.order_id, o.payable_amount)}
                        style={styles.payBtn}
                      />
                    )}
                  </View>
                );
              })}
            </RoundedCard>
          )}

          {/* Fallback if current user has no stored order data but order exists */}
          {!currentUserOrder && (
            <RoundedCard style={{ backgroundColor: '#FFF7ED' }}>
              <Text style={styles.muted}>
                Group order placed. Payment details will appear here once the owner completes setup.
              </Text>
            </RoundedCard>
          )}
        </>
      )}

      {group?.status === 'completed' && (
        <RoundedCard style={{ backgroundColor: '#F0FDF4' }}>
          <View style={styles.orderedBanner}>
            <MaterialCommunityIcons name="check-circle" size={28} color="#22C55E" />
            <Text style={styles.orderedText}>Group order completed!</Text>
          </View>
        </RoundedCard>
      )}

      <View style={{ height: 40 }} />
    </Screen>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  loadingWrap: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  header: { flexDirection: 'row', alignItems: 'center', paddingTop: 18, paddingBottom: 10 },
  backBtn: { marginRight: 12 },
  title: { fontSize: 22, fontWeight: '900', color: '#1F2937' },
  statusBadge: { fontSize: 12, fontWeight: '700', color: '#6C63FF', marginTop: 2 },

  sectionRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  sectionTitle: { fontSize: 16, fontWeight: '800', color: '#1F2937', marginBottom: 8 },
  sectionSubTitle: { fontSize: 14, fontWeight: '700', color: '#374151', marginTop: 8, marginBottom: 4 },
  muted: { color: '#9CA3AF', fontSize: 13 },

  memberRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 6 },
  memberAvatar: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#EEF2FF',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  memberInitial: { fontSize: 16, fontWeight: '800', color: '#6C63FF' },
  memberName: { fontSize: 14, fontWeight: '700', color: '#374151' },
  memberRole: { fontSize: 12, color: '#9CA3AF' },

  paymentBadge: { borderRadius: 10, paddingHorizontal: 8, paddingVertical: 2 },
  paidBadge: { backgroundColor: '#D1FAE5' },
  unpaidBadge: { backgroundColor: '#FEF3C7' },
  paymentBadgeText: { fontSize: 11, fontWeight: '800' },
  paidText: { color: '#059669' },
  unpaidText: { color: '#D97706' },

  inviteRow: { flexDirection: 'row', alignItems: 'center', marginTop: 10, gap: 10 },
  inviteInput: { flex: 1, backgroundColor: 'transparent' },
  inviteBtn: { minWidth: 80 },

  cartItemRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
  },
  cartItemIcon: {
    width: 36,
    height: 36,
    borderRadius: 10,
    backgroundColor: '#EEF2FF',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  cartItemName: { fontSize: 14, fontWeight: '700', color: '#374151' },
  cartItemMeta: { fontSize: 12, color: '#9CA3AF', marginTop: 2 },

  totalRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 12,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
  },
  totalLabel: { fontSize: 16, fontWeight: '800', color: '#374151' },
  totalValue: { fontSize: 16, fontWeight: '900', color: '#6C63FF' },

  input: { backgroundColor: 'transparent', marginBottom: 10 },

  splitBtns: { flexDirection: 'row', justifyContent: 'space-around', marginTop: 12, gap: 8 },
  splitBtn: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 12,
    borderRadius: 12,
    backgroundColor: '#F9FAFB',
    borderWidth: 2,
    borderColor: '#E5E7EB',
  },
  splitBtnActive: { backgroundColor: '#6C63FF', borderColor: '#6C63FF' },
  splitLabel: { fontSize: 11, fontWeight: '700', color: '#374151', marginTop: 4 },
  splitLabelActive: { color: '#FFFFFF' },
  splitSummary: { marginTop: 10, paddingTop: 8, borderTopWidth: 1, borderTopColor: '#E5E7EB' },
  splitHint: { fontSize: 13, color: '#6B7280', textAlign: 'center' },

  customRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 8, gap: 8 },
  customLabel: { flex: 1, fontSize: 13, fontWeight: '600', color: '#374151' },
  customInput: { width: 120, backgroundColor: 'transparent' },

  savingOverlay: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', marginTop: 10, gap: 8 },
  savingText: { fontSize: 13, color: '#6C63FF', fontWeight: '600' },

  slotLockedRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  slotLockedText: { fontSize: 14, fontWeight: '600', color: '#374151', flex: 1 },

  checkoutWrap: { paddingVertical: 14 },

  orderedBanner: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  orderedText: { fontSize: 16, fontWeight: '700', color: '#22C55E' },

  // Payment status section
  paymentRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
    gap: 8,
  },
  paymentInfo: { flex: 1 },
  paymentMember: { fontSize: 14, fontWeight: '700', color: '#374151' },
  paymentAmount: { fontSize: 13, color: '#6B7280', marginTop: 2 },
  paymentStatusPill: { borderRadius: 12, paddingHorizontal: 10, paddingVertical: 4 },
  paidStatusPill: { backgroundColor: '#D1FAE5' },
  unpaidStatusPill: { backgroundColor: '#FEF3C7' },
  paymentStatusPillText: { fontSize: 12, fontWeight: '800' },
  paidStatusText: { color: '#059669' },
  unpaidStatusText: { color: '#D97706' },
  payBtn: { minWidth: 80 },
});

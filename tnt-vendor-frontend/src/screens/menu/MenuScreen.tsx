import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  TextInput,
  Animated,
  ActivityIndicator,
  Alert,
  Modal,
  Image,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors as staticColors, shadows, spacing, borderRadius } from '../../design-system';
const colors = staticColors;
import GlassCard from '../../design-system/components/GlassCard';
import StatusPill from '../../design-system/components/StatusPill';
import PremiumEmptyState from '../../design-system/components/PremiumEmptyState';
import apiClient from '../../services/apiClient';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { formatRupees } from '../../utils/format';



interface MenuItem {
  id: number;
  vendor_id: number;
  name: string;
  price: number;
  category: string;
  is_available: boolean;
  image_url?: string;
  prep_time_minutes?: number;
  available_quantity?: number;
  stock_level?: number;
  inventory_id?: number;
  is_low_stock?: boolean;
}

const CATEGORIES = ['All', 'Breakfast', 'Beverages', 'Lunch', 'Snacks', 'Specials', 'Stationery'];

export default function MenuScreen({ navigation }: any) {
  const { user } = useAuth();
  const { colors } = useTheme();
  const styles = getStyles(colors);
  // menu_items.vendor_id is a FK to users.id, so the menu endpoints key on the
  // owner's user id — not the business vendors.vendor_id. The two id spaces
  // overlap, so passing the business id returns another stall's menu or nothing.
  const vendorId = user?.owner_id;

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Restock states
  const [isRestockVisible, setIsRestockVisible] = useState(false);
  const [selectedRestockItem, setSelectedRestockItem] = useState<MenuItem | null>(null);
  const [restockQty, setRestockQty] = useState('');
  const [isRestockLoading, setIsRestockLoading] = useState(false);

  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }).start();
    fetchData();
  }, [vendorId]);
  
  const fetchData = async () => {
    if (!vendorId) return;
    setIsLoading(true);
    try {
      // 1. Fetch menu items
      const itemsRes = await apiClient.get(`/v1/menu/items?vendor_id=${vendorId}`);
      const rawItems = itemsRes.data.items || [];

      // 2. Fetch inventory dashboard. It keys rows by `item_id` (the menu item
      // id) and does not expose the inventory row's own id — restocking goes
      // through the item-id endpoint below, which upserts.
      let inventoryMap: Record<number, { current_stock: number; low_stock_threshold: number }> = {};
      try {
        const invRes = await apiClient.get(`/v1/vendors/inventory/dashboard`);
        const invItems = invRes.data.items || [];
        invItems.forEach((inv: any) => {
          inventoryMap[inv.item_id] = {
            current_stock: inv.current_stock,
            low_stock_threshold: inv.low_stock_threshold,
          };
        });
      } catch (e) {
        console.log('Failed to load inventory dashboard metrics, fallback to empty');
      }

      // Merge items and inventory
      const mergedItems = rawItems.map((item: any) => {
        const inv = inventoryMap[item.id];
        return {
          ...item,
          stock_level: inv ? inv.current_stock : undefined,
          is_low_stock: inv ? inv.current_stock <= inv.low_stock_threshold : false,
        };
      });

      setMenuItems(mergedItems);
    } catch (err: any) {
      console.error(err);
      Alert.alert('Error', 'Failed to load menu items.');
    } finally {
      setIsLoading(false);
    }
  };

  const toggleAvailability = async (id: number, currentAvailable: boolean) => {
    try {
      await apiClient.put(`/v1/menu/items/${id}/toggle`);
      setMenuItems(prev =>
        prev.map(item =>
          item.id === id ? { ...item, is_available: !currentAvailable } : item,
        ),
      );
    } catch (err) {
      Alert.alert('Error', 'Failed to toggle availability.');
    }
  };

  const handleDelete = (id: number) => {
    Alert.alert(
      'Confirm Delete',
      'Are you sure you want to delete this menu item?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await apiClient.delete(`/v1/menu/items/${id}`);
              fetchData();
            } catch (err) {
              Alert.alert('Error', 'Failed to delete menu item.');
            }
          },
        },
      ]
    );
  };

  const openRestockModal = (item: MenuItem) => {
    setSelectedRestockItem(item);
    setRestockQty('');
    setIsRestockVisible(true);
  };

  const handleRestock = async () => {
    if (!selectedRestockItem) return;
    const qty = parseInt(restockQty, 10);
    if (isNaN(qty) || qty <= 0) {
      Alert.alert('Validation Error', 'Please enter a valid positive quantity.');
      return;
    }

    setIsRestockLoading(true);
    try {
      // Vendor-scoped restock keyed on the menu item id. It upserts — adds to an
      // existing inventory row or creates one — so we never need the inventory
      // row's id, and it can't fail with "inventory already exists".
      const res = await apiClient.post(
        `/v1/vendors/inventory/restock/${selectedRestockItem.id}?quantity=${qty}`,
      );

      // This endpoint reports failures as 200 + {success:false}, so check it
      // rather than trusting the status code.
      if (res.data?.success === false) {
        Alert.alert('Error', res.data.error || 'Failed to restock item.');
        return;
      }

      setIsRestockVisible(false);
      fetchData();
      Alert.alert('Success', `Stock updated — ${selectedRestockItem.name} now at ${res.data?.new_stock ?? qty}.`);
    } catch (err: any) {
      console.error(err);
      Alert.alert('Error', err.response?.data?.detail || 'Failed to restock item.');
    } finally {
      setIsRestockLoading(false);
    }
  };

  const filteredItems = menuItems.filter(item => {
    const matchesSearch = item.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory =
      selectedCategory === 'All' ||
      item.category?.toLowerCase() === selectedCategory.toLowerCase();
    return matchesSearch && matchesCategory;
  });

  const renderItem = ({ item }: { item: MenuItem }) => (
    <GlassCard style={styles.menuCard} padding={16} borderRadius={20} intensity="light">
      <View style={styles.menuRow}>
        {/* Item photo — falls back to a category emoji when there is no image */}
        <View style={[styles.imagePlaceholder, { backgroundColor: item.is_available ? colors.primaryPale : colors.bgTertiary }]}>
          {item.image_url ? (
            <Image source={{ uri: item.image_url }} style={styles.itemImage} resizeMode="cover" />
          ) : (
            <Text style={styles.imageEmoji}>{item.category === 'stationery' ? '✏️' : '🍽️'}</Text>
          )}
        </View>

        {/* Info */}
        <View style={styles.menuInfo}>
          <View style={styles.menuHeaderRow}>
            <Text style={[styles.menuName, { color: colors.textPrimary }]}>{item.name}</Text>
            {item.is_low_stock && (
              <StatusPill label="Low Stock" variant="error" size="sm" />
            )}
          </View>
          <Text style={[styles.menuCategory, { color: colors.textMuted }]}>{item.category?.toUpperCase()}</Text>
          <View style={styles.menuMeta}>
            <Text style={[styles.menuPrice, { color: colors.primary }]}>{formatRupees(item.price)}</Text>
            {item.prep_time_minutes && (
              <Text style={[styles.prepTime, { color: colors.textSecondary }]}>⏱️ {item.prep_time_minutes}m</Text>
            )}
          </View>

          {/* Stock Info */}
          <View style={styles.stockRow}>
            <Text style={[styles.stockLabel, { color: colors.textSecondary }]}>
              Stock: {item.stock_level !== undefined ? item.stock_level : 'N/A'}
            </Text>
            <TouchableOpacity style={styles.restockBtn} onPress={() => openRestockModal(item)}>
              <Text style={[styles.restockBtnText, { color: colors.primary }]}>+ Restock</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Actions Column */}
        <View style={styles.actionsCol}>
          {/* Toggle */}
          <TouchableOpacity
            style={[
              styles.toggleButton,
              item.is_available ? { backgroundColor: colors.successPale } : { backgroundColor: colors.bgTertiary }
            ]}
            onPress={() => toggleAvailability(item.id, item.is_available)}
          >
            <View style={[styles.toggleCircle, { backgroundColor: item.is_available ? colors.success : colors.textMuted }]} />
            <Text style={[styles.toggleLabel, { color: item.is_available ? colors.success : colors.textMuted }]}>
              {item.is_available ? 'ON' : 'OFF'}
            </Text>
          </TouchableOpacity>

          <View style={styles.btnRow}>
            <TouchableOpacity
              style={[styles.actionBtn, { backgroundColor: colors.bgSecondary, borderColor: colors.border }]}
              onPress={() => navigation.navigate('AddEditMenuItem', { item, onRefresh: fetchData })}
            >
              <Text style={[styles.actionBtnText, { color: colors.textPrimary }]}>✏️</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.actionBtn, { backgroundColor: colors.errorPale, borderColor: colors.errorPale }]}
              onPress={() => handleDelete(item.id)}
            >
              <Text style={[styles.actionBtnText, { color: colors.error }]}>🗑️</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </GlassCard>
  );

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.bg }]} edges={['top']}>
      <Animated.View style={{ flex: 1, opacity: fadeAnim }}>
        {/* Header */}
        <View style={[styles.header, { backgroundColor: colors.primary }]}>
        <View>
          <Text style={[styles.headerTitle, { color: colors.textInverse }]}>Menu Catalog</Text>
          <Text style={styles.headerSubtitle}>
            {menuItems.filter(i => i.is_available).length} items active
          </Text>
        </View>
        <View style={styles.headerBtns}>
          <TouchableOpacity
            style={[styles.headerBtn, { backgroundColor: 'rgba(255,255,255,0.15)' }]}
            onPress={() => navigation.navigate('AddEditMenuItem', { onRefresh: fetchData })}
          >
            <Text style={[styles.headerBtnText, { color: colors.textInverse }]}>+ Add Item</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.headerBtn, { backgroundColor: 'rgba(255,255,255,0.15)' }]}
            onPress={() => navigation.navigate('StationeryServices')}
          >
            <Text style={[styles.headerBtnText, { color: colors.textInverse }]}>✏️ Services</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.headerBtn, { backgroundColor: colors.info }]}
            onPress={() => navigation.navigate('MenuBulkImport')}
          >
            <Text style={[styles.headerBtnText, { color: colors.textInverse }]}>📥 CSV</Text>
          </TouchableOpacity>
        </View>
      </View>


      {/* Search */}
      <View style={[styles.searchContainer, { backgroundColor: colors.bgCard }]}>
        <View style={[styles.searchBar, { backgroundColor: colors.bgSecondary, borderColor: colors.border }]}>
          <Text style={[styles.searchIcon, { color: colors.textMuted }]}>🔍</Text>
          <TextInput
            style={[styles.searchInput, { color: colors.textPrimary }]}
            placeholder="Search catalog items..."
            placeholderTextColor={colors.textMuted}
            value={searchQuery}
            onChangeText={setSearchQuery}
          />
          {searchQuery.length > 0 && (
            <TouchableOpacity onPress={() => setSearchQuery('')}>
              <Text style={[styles.clearIcon, { color: colors.textMuted }]}>✕</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>

      {/* Category Chips */}
      <View style={{ height: 70, marginTop: spacing.sm }}>
        <FlatList
          horizontal
          data={CATEGORIES}
          keyExtractor={item => item}
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.chipsContainer}
          renderItem={({ item }) => (
            <TouchableOpacity
              style={[
                styles.chip,
                { backgroundColor: colors.bgSecondary, borderColor: colors.border },
                selectedCategory === item && [styles.chipActive, { backgroundColor: colors.primary, borderColor: colors.primary }]
              ]}
              onPress={() => setSelectedCategory(item)}
            >
              <Text style={[
                styles.chipText,
                { color: colors.textMuted },
                selectedCategory === item && [styles.chipTextActive, { color: colors.textInverse }]
              ]} numberOfLines={1}>
                {item}
              </Text>
            </TouchableOpacity>
          )}
        />
      </View>

      {/* Menu List */}
      {isLoading && menuItems.length === 0 ? (
        <ActivityIndicator color={colors.primary} size="large" style={{ marginTop: 40 }} />
      ) : (
        <FlatList
          data={filteredItems}
          keyExtractor={item => item.id.toString()}
          renderItem={renderItem}
          contentContainerStyle={[styles.listContent, { paddingBottom: 100 }]}
          showsVerticalScrollIndicator={false}
          refreshing={isLoading}
          onRefresh={fetchData}
          ListEmptyComponent={
            <PremiumEmptyState
              icon="🍽️"
              title="No items found"
              description={searchQuery ? 'Try a different search term.' : 'No items in this category.'}
            />
          }
        />
      )}

      {/* Restock Modal */}
      <Modal visible={isRestockVisible} animationType="slide" transparent>
        <View style={[styles.modalBg, { backgroundColor: colors.bgOverlay || 'rgba(0,0,0,0.5)' }]}>
          <View style={[styles.modalContent, { backgroundColor: colors.bgCard }]}>
            <Text style={[styles.modalTitle, { color: colors.textPrimary }]}>Restock {selectedRestockItem?.name}</Text>
            <Text style={[styles.modalSub, { color: colors.textMuted }]}>
              Current Stock: {selectedRestockItem?.stock_level !== undefined ? selectedRestockItem.stock_level : 'N/A'}
            </Text>

            <TextInput
              style={[styles.qtyInput, { backgroundColor: colors.bgSecondary, borderColor: colors.border, color: colors.textPrimary }]}
              placeholder="Enter Restock Quantity"
              placeholderTextColor={colors.textMuted}
              keyboardType="numeric"
              value={restockQty}
              onChangeText={setRestockQty}
            />

            <View style={styles.modalActions}>
              <TouchableOpacity
                style={[styles.modalBtn, styles.modalBtnCancel, { backgroundColor: colors.bgSecondary }]}
                onPress={() => setIsRestockVisible(false)}
              >
                <Text style={[styles.modalBtnCancelText, { color: colors.textPrimary }]}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.modalBtn, styles.modalBtnSave, { backgroundColor: colors.primary }]}
                onPress={handleRestock}
                disabled={isRestockLoading}
              >
                {isRestockLoading ? (
                  <ActivityIndicator color={colors.textInverse} size="small" />
                ) : (
                  <Text style={[styles.modalBtnSaveText, { color: colors.textInverse }]}>Update Stock</Text>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
      </Animated.View>
    </SafeAreaView>
  );
}


const getStyles = (colors: any) => StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  header: {
    backgroundColor: colors.primary,
    paddingTop: spacing.lg,
    paddingBottom: spacing.xl,
    paddingHorizontal: spacing.xl,
    borderBottomLeftRadius: 28,
    borderBottomRightRadius: 28,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerTitle: { fontSize: 24, fontWeight: '700', color: colors.textInverse, letterSpacing: -0.3 },
  headerSubtitle: { fontSize: 13, color: 'rgba(255,255,255,0.7)', marginTop: 4, fontWeight: '500' },
  headerBtns: {
    gap: spacing.xs,
  },
  headerBtn: {
    backgroundColor: 'rgba(255,255,255,0.2)',
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: borderRadius.md,
    alignItems: 'center',
  },
  stationeryBtn: {
    backgroundColor: 'rgba(255,255,255,0.1)',
  },
  headerBtnText: {
    color: colors.textInverse,
    fontSize: 12,
    fontWeight: '600',
  },

  searchContainer: { paddingHorizontal: spacing.lg, paddingTop: spacing.md },
  searchBar: {
    flexDirection: 'row', alignItems: 'center', backgroundColor: colors.bgCard,
    borderRadius: 16, paddingHorizontal: 16, paddingVertical: 4, ...shadows.sm,
  },
  searchIcon: { fontSize: 16, marginRight: 8 },
  searchInput: { flex: 1, fontSize: 15, color: colors.textPrimary, paddingVertical: 12 },
  clearIcon: { fontSize: 14, color: colors.textMuted, padding: 4 },

  chipsContainer: { paddingHorizontal: spacing.lg, gap: 8, height: 48 },
  chip: {
    paddingHorizontal: 22, paddingVertical: 8, borderRadius: 20,
    backgroundColor: colors.bgCard, borderWidth: 1.5, borderColor: colors.border, marginRight: 8,
    height: 36, justifyContent: 'center',
  },
  chipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  chipText: { fontSize: 13, fontWeight: '600', color: colors.textSecondary },
  chipTextActive: { color: colors.textInverse },

  listContent: { padding: spacing.lg, paddingBottom: spacing.huge },

  menuCard: { marginBottom: spacing.sm, backgroundColor: colors.bgCard },
  menuRow: { flexDirection: 'row', alignItems: 'center' },
  imagePlaceholder: {
    width: 64, height: 64, borderRadius: 16,
    justifyContent: 'center', alignItems: 'center', marginRight: 14,
    overflow: 'hidden',
  },
  itemImage: { width: '100%', height: '100%' },
  imageEmoji: { fontSize: 28 },
  menuInfo: { flex: 1 },
  menuHeaderRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  menuName: { fontSize: 16, fontWeight: '700', color: colors.textPrimary },
  menuCategory: { fontSize: 10, color: colors.textMuted, marginTop: 2, fontWeight: '600' },
  menuMeta: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 4 },
  menuPrice: { fontSize: 18, fontWeight: '700', color: colors.success },
  prepTime: { fontSize: 12, color: colors.textSecondary },

  stockRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginTop: spacing.xs,
  },
  stockLabel: {
    fontSize: 12,
    color: colors.textSecondary,
    fontWeight: '600',
  },
  restockBtn: {
    backgroundColor: colors.primaryPale,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: borderRadius.sm,
  },
  restockBtnText: {
    color: colors.primary,
    fontSize: 11,
    fontWeight: '600',
  },

  actionsCol: {
    alignItems: 'flex-end',
    gap: spacing.sm,
    marginLeft: 8,
  },
  toggleButton: {
    width: 48, height: 42, borderRadius: 14, justifyContent: 'center', alignItems: 'center',
    gap: 2,
  },
  toggleActive: { backgroundColor: colors.successPale },
  toggleInactive: { backgroundColor: colors.bgTertiary },
  toggleCircle: { width: 10, height: 10, borderRadius: 5, backgroundColor: colors.textMuted },
  toggleCircleActive: { backgroundColor: colors.success },
  toggleLabel: { fontSize: 8, fontWeight: '700' },

  btnRow: {
    flexDirection: 'row',
    gap: spacing.xs,
  },
  actionBtn: {
    padding: 6,
    borderRadius: borderRadius.sm,
    backgroundColor: colors.bgSecondary,
    borderWidth: 1,
    borderColor: colors.border,
  },
  deleteBtn: {
    backgroundColor: colors.errorPale,
    borderColor: colors.errorPale,
  },
  actionBtnText: {
    fontSize: 12,
  },

  // Modal styles
  modalBg: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    padding: spacing.lg,
  },
  modalContent: {
    backgroundColor: colors.bgCard,
    borderRadius: borderRadius.xl,
    padding: spacing.lg,
    alignItems: 'center',
    ...shadows.lg,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: colors.textPrimary,
    marginBottom: 4,
  },
  modalSub: {
    fontSize: 13,
    color: colors.textMuted,
    marginBottom: spacing.md,
  },
  qtyInput: {
    backgroundColor: colors.bgSecondary,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: borderRadius.md,
    padding: spacing.md,
    width: '100%',
    color: colors.textPrimary,
    fontSize: 16,
    textAlign: 'center',
    marginBottom: spacing.lg,
  },
  modalActions: {
    flexDirection: 'row',
    gap: spacing.md,
  },
  modalBtn: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: borderRadius.md,
    alignItems: 'center',
  },
  modalBtnCancel: {
    backgroundColor: colors.bgSecondary,
  },
  modalBtnCancelText: {
    color: colors.textPrimary,
    fontWeight: '600',
  },
  modalBtnSave: {
    backgroundColor: colors.primary,
  },
  modalBtnSaveText: {
    color: colors.textInverse,
    fontWeight: '700',
  },
});

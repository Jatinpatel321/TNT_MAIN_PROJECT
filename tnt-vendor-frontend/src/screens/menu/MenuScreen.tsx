// ─── Menu Management ──────────────────────────────────────────────
// Modern catalog with large cards, availability switches, AI insights

import React, { useState, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  TextInput,
  Animated,
} from 'react-native';
import { colors, shadows, spacing } from '../../design-system';
import GlassCard from '../../design-system/components/GlassCard';
import StatusPill from '../../design-system/components/StatusPill';
import PremiumEmptyState from '../../design-system/components/PremiumEmptyState';

interface MenuItem {
  id: number;
  name: string;
  price: number;
  category: string;
  available: boolean;
  image?: string;
  order_count?: number;
  popularity?: number;
  stock_level?: number;
  is_best_seller?: boolean;
  ai_suggested_price?: number;
}

const CATEGORIES = ['All', 'Breakfast', 'Beverages', 'Lunch', 'Snacks', 'Specials'];

const MENU_ITEMS: MenuItem[] = [
  { id: 1, name: 'Masala Dosa', price: 80, category: 'Breakfast', available: true, order_count: 45, popularity: 92, stock_level: 30, is_best_seller: true },
  { id: 2, name: 'Idli Sambar', price: 50, category: 'Breakfast', available: true, order_count: 38, popularity: 85, stock_level: 25 },
  { id: 3, name: 'Filter Coffee', price: 20, category: 'Beverages', available: true, order_count: 62, popularity: 96, stock_level: 50, is_best_seller: true },
  { id: 4, name: 'Vada', price: 30, category: 'Breakfast', available: false, order_count: 12, popularity: 45, stock_level: 0 },
  { id: 5, name: 'Upma', price: 40, category: 'Breakfast', available: true, order_count: 20, popularity: 60, stock_level: 15 },
  { id: 6, name: 'Tea', price: 15, category: 'Beverages', available: true, order_count: 55, popularity: 90, stock_level: 40 },
];

export default function MenuScreen() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [menuItems, setMenuItems] = useState<MenuItem[]>(MENU_ITEMS);

  const fadeAnim = useRef(new Animated.Value(0)).current;
  React.useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }).start();
  }, []);

  const toggleAvailability = (id: number) => {
    setMenuItems(prev =>
      prev.map(item =>
        item.id === id ? { ...item, available: !item.available } : item,
      ),
    );
  };

  const filteredItems = menuItems.filter(item => {
    const matchesSearch = item.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = selectedCategory === 'All' || item.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const renderItem = ({ item }: { item: MenuItem }) => (
    <GlassCard style={styles.menuCard} padding={16} borderRadius={20} intensity="light">
      <View style={styles.menuRow}>
        {/* Image Placeholder */}
        <View style={[styles.imagePlaceholder, { backgroundColor: item.available ? colors.primaryPale : colors.bgTertiary }]}>
          <Text style={styles.imageEmoji}>🍽️</Text>
        </View>

        {/* Info */}
        <View style={styles.menuInfo}>
          <View style={styles.menuHeaderRow}>
            <Text style={styles.menuName}>{item.name}</Text>
            {item.is_best_seller && (
              <StatusPill label="Best Seller" variant="warning" size="sm" icon="🏆" />
            )}
          </View>
          <Text style={styles.menuCategory}>{item.category}</Text>
          <View style={styles.menuMeta}>
            <Text style={styles.menuPrice}>₹{item.price}</Text>
            {item.ai_suggested_price && (
              <Text style={styles.aiPriceSuggestion}>
                AI: ₹{item.ai_suggested_price}
              </Text>
            )}
          </View>

          {/* Stats row */}
          <View style={styles.statsRow}>
            {item.popularity != null && (
              <View style={styles.statItem}>
                <Text style={styles.statValue}>{item.popularity}%</Text>
                <Text style={styles.statLabel}>Popular</Text>
              </View>
            )}
            {item.order_count != null && (
              <View style={styles.statItem}>
                <Text style={styles.statValue}>{item.order_count}</Text>
                <Text style={styles.statLabel}>Orders</Text>
              </View>
            )}
            {item.stock_level != null && (
              <View style={styles.statItem}>
                <Text style={[styles.statValue, { color: item.stock_level < 10 ? colors.error : colors.success }]}>
                  {item.stock_level}
                </Text>
                <Text style={styles.statLabel}>Stock</Text>
              </View>
            )}
          </View>
        </View>

        {/* Toggle */}
        <TouchableOpacity
          style={[styles.toggleButton, item.available ? styles.toggleActive : styles.toggleInactive]}
          onPress={() => toggleAvailability(item.id)}
        >
          <View style={[styles.toggleCircle, item.available && styles.toggleCircleActive]} />
          <Text style={[styles.toggleLabel, { color: item.available ? colors.success : colors.textMuted }]}>
            {item.available ? 'ON' : 'OFF'}
          </Text>
        </TouchableOpacity>
      </View>
    </GlassCard>
  );

  return (
    <Animated.View style={[styles.container, { opacity: fadeAnim }]}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Menu</Text>
        <Text style={styles.headerSubtitle}>{menuItems.filter(i => i.available).length} items available</Text>
      </View>

      {/* Search */}
      <View style={styles.searchContainer}>
        <View style={styles.searchBar}>
          <Text style={styles.searchIcon}>🔍</Text>
          <TextInput
            style={styles.searchInput}
            placeholder="Search menu items..."
            placeholderTextColor={colors.textMuted}
            value={searchQuery}
            onChangeText={setSearchQuery}
          />
          {searchQuery.length > 0 && (
            <TouchableOpacity onPress={() => setSearchQuery('')}>
              <Text style={styles.clearIcon}>✕</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>

      {/* Category Chips */}
      <FlatList
        horizontal
        data={CATEGORIES}
        keyExtractor={item => item}
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.chipsContainer}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={[styles.chip, selectedCategory === item && styles.chipActive]}
            onPress={() => setSelectedCategory(item)}
          >
            <Text style={[styles.chipText, selectedCategory === item && styles.chipTextActive]}>
              {item}
            </Text>
          </TouchableOpacity>
        )}
      />

      {/* Menu List */}
      <FlatList
        data={filteredItems}
        keyExtractor={item => item.id.toString()}
        renderItem={renderItem}
        contentContainerStyle={styles.listContent}
        showsVerticalScrollIndicator={false}
        ListEmptyComponent={
          <PremiumEmptyState
            icon="🍽️"
            title="No items found"
            description={searchQuery ? 'Try a different search term.' : 'No items in this category.'}
          />
        }
      />
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  header: {
    backgroundColor: colors.primary,
    paddingTop: spacing.huge + 20,
    paddingBottom: spacing.xl,
    paddingHorizontal: spacing.xl,
    borderBottomLeftRadius: 28,
    borderBottomRightRadius: 28,
  },
  headerTitle: { fontSize: 28, fontWeight: '700', color: colors.textInverse, letterSpacing: -0.3 },
  headerSubtitle: { fontSize: 14, color: 'rgba(255,255,255,0.7)', marginTop: 4, fontWeight: '500' },

  searchContainer: { paddingHorizontal: spacing.lg, paddingTop: spacing.md },
  searchBar: {
    flexDirection: 'row', alignItems: 'center', backgroundColor: colors.bgCard,
    borderRadius: 16, paddingHorizontal: 16, paddingVertical: 4, ...shadows.sm,
  },
  searchIcon: { fontSize: 16, marginRight: 8 },
  searchInput: { flex: 1, fontSize: 15, color: colors.textPrimary, paddingVertical: 12 },
  clearIcon: { fontSize: 14, color: colors.textMuted, padding: 4 },

  chipsContainer: { paddingHorizontal: spacing.lg, paddingVertical: spacing.md, gap: 8 },
  chip: {
    paddingHorizontal: 18, paddingVertical: 8, borderRadius: 20,
    backgroundColor: colors.bgCard, borderWidth: 1.5, borderColor: colors.border, marginRight: 8,
  },
  chipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  chipText: { fontSize: 13, fontWeight: '600', color: colors.textSecondary },
  chipTextActive: { color: colors.textInverse },

  listContent: { padding: spacing.lg, paddingBottom: spacing.huge },

  menuCard: { marginBottom: spacing.sm },
  menuRow: { flexDirection: 'row', alignItems: 'center' },
  imagePlaceholder: {
    width: 64, height: 64, borderRadius: 16,
    justifyContent: 'center', alignItems: 'center', marginRight: 14,
  },
  imageEmoji: { fontSize: 28 },
  menuInfo: { flex: 1 },
  menuHeaderRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  menuName: { fontSize: 16, fontWeight: '700', color: colors.textPrimary },
  menuCategory: { fontSize: 12, color: colors.textMuted, marginTop: 2 },
  menuMeta: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 4 },
  menuPrice: { fontSize: 18, fontWeight: '700', color: colors.success },
  aiPriceSuggestion: { fontSize: 11, color: colors.aiPrimary, fontWeight: '600', backgroundColor: colors.primaryPale, paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6 },
  statsRow: { flexDirection: 'row', gap: 12, marginTop: 6 },
  statItem: { flexDirection: 'row', alignItems: 'center', gap: 3 },
  statValue: { fontSize: 12, fontWeight: '700', color: colors.textPrimary },
  statLabel: { fontSize: 10, color: colors.textMuted, fontWeight: '500' },

  toggleButton: {
    width: 48, height: 64, borderRadius: 14, justifyContent: 'center', alignItems: 'center',
    marginLeft: 8, gap: 4,
  },
  toggleActive: { backgroundColor: colors.successPale },
  toggleInactive: { backgroundColor: colors.bgTertiary },
  toggleCircle: { width: 14, height: 14, borderRadius: 7, backgroundColor: colors.textMuted },
  toggleCircleActive: { backgroundColor: colors.success },
  toggleLabel: { fontSize: 9, fontWeight: '700' },
});


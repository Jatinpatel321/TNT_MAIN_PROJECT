import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Animated,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { complaintsApi, type Complaint } from '../../services/complaintsApi';
import { colors, shadows, spacing } from '../../design-system';
import GlassCard from '../../design-system/components/GlassCard';
import PremiumEmptyState from '../../design-system/components/PremiumEmptyState';

type FilterType = 'all' | 'open' | 'resolved';

const categoryIcons: Record<string, string> = {
  late_order: '🕐',
  wrong_item: '🍔',
  quality_issue: '⭐',
  other: '📢',
};

const categoryColors: Record<string, string> = {
  late_order: colors.warning || '#F59E0B',
  wrong_item: colors.primary || '#6C63FF',
  quality_issue: colors.error || '#EF4444',
  other: colors.info || '#3B82F6',
};

export default function ComplaintsScreen({ navigation }: any) {
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState<FilterType>('all');
  const [resolving, setResolving] = useState<number | null>(null);
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }).start();
    loadComplaints();
  }, []);

  const loadComplaints = async () => {
    try {
      setLoading(true);
      const response = await complaintsApi.getComplaints();
      setComplaints(response.data || []);
    } catch (error) {
      console.error('Failed to load complaints:', error);
      Alert.alert('Error', 'Failed to fetch complaints list');
    } finally {
      setLoading(false);
    }
  };

  const handleResolve = async (id: number) => {
    try {
      setResolving(id);
      await complaintsApi.resolveComplaint(id);
      setComplaints(prev =>
        prev.map(c => (c.id === id ? { ...c, status: 'resolved' } : c))
      );
      Alert.alert('Success', 'Complaint resolved successfully.');
    } catch (error) {
      console.error('Failed to resolve complaint:', error);
      Alert.alert('Error', 'Failed to resolve the complaint');
    } finally {
      setResolving(null);
    }
  };

  const filtered = complaints.filter(c => {
    if (activeFilter === 'open') return c.status !== 'resolved';
    if (activeFilter === 'resolved') return c.status === 'resolved';
    return true;
  });

  const renderItem = ({ item }: { item: Complaint }) => {
    const icon = categoryIcons[item.category] || '📋';
    const color = categoryColors[item.category] || colors.info;
    const isResolved = item.status === 'resolved';

    return (
      <GlassCard
        padding={16}
        borderRadius={20}
        intensity={isResolved ? 'light' : 'medium'}
        style={styles.card}
      >
        <View style={styles.cardRow}>
          <View style={[styles.iconCircle, { backgroundColor: `${color}15` }]}>
            <Text style={styles.cardIcon}>{icon}</Text>
          </View>
          <View style={styles.cardContent}>
            <View style={styles.cardHeader}>
              <Text style={styles.cardTitle} numberOfLines={1}>
                {item.title}
              </Text>
              <View
                style={[
                  styles.statusTag,
                  { backgroundColor: isResolved ? `${colors.success}15` : `${colors.warning}15` },
                ]}
              >
                <Text
                  style={[
                    styles.statusTagText,
                    { color: isResolved ? colors.success : colors.warning },
                  ]}
                >
                  {item.status.toUpperCase()}
                </Text>
              </View>
            </View>
            {item.description && (
              <Text style={styles.cardDesc} numberOfLines={3}>
                {item.description}
              </Text>
            )}
            <View style={styles.metaRow}>
              {item.order_id && (
                <Text style={styles.metaText}>Order #{item.order_id}</Text>
              )}
              <Text style={styles.metaText}>
                {new Date(item.created_at).toLocaleDateString([], {
                  month: 'short',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </Text>
            </View>

            {!isResolved && (
              <TouchableOpacity
                style={[styles.resolveBtn, { backgroundColor: colors.primary }]}
                onPress={() => handleResolve(item.id)}
                disabled={resolving === item.id}
                activeOpacity={0.8}
              >
                {resolving === item.id ? (
                  <ActivityIndicator size="small" color="#fff" />
                ) : (
                  <Text style={styles.resolveBtnText}>Mark as Resolved</Text>
                )}
              </TouchableOpacity>
            )}
          </View>
        </View>
      </GlassCard>
    );
  };

  const filters: { key: FilterType; label: string }[] = [
    { key: 'all', label: 'All' },
    { key: 'open', label: 'Open' },
    { key: 'resolved', label: 'Resolved' },
  ];

  if (loading) {
    return (
      <View style={[styles.container, styles.centered]}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading complaints...</Text>
      </View>
    );
  }

  return (
    <Animated.View style={[styles.container, { opacity: fadeAnim }]}>
      {/* Filters */}
      <View style={styles.filterRow}>
        {filters.map(f => (
          <TouchableOpacity
            key={f.key}
            style={[styles.filterChip, activeFilter === f.key && styles.filterChipActive]}
            onPress={() => setActiveFilter(f.key)}
          >
            <Text style={[styles.filterText, activeFilter === f.key && styles.filterTextActive]}>
              {f.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* List */}
      <FlatList
        data={filtered}
        keyExtractor={item => item.id.toString()}
        renderItem={renderItem}
        contentContainerStyle={styles.listContent}
        showsVerticalScrollIndicator={false}
        ListEmptyComponent={
          <PremiumEmptyState
            icon="💬"
            title="No complaints"
            description="You have no complaints assigned under this category."
          />
        }
      />
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg || '#F9FAFB' },
  centered: { justifyContent: 'center', alignItems: 'center' },
  loadingText: { marginTop: 12, fontSize: 14, color: colors.textMuted, fontWeight: '600' },
  filterRow: {
    flexDirection: 'row',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    gap: 8,
  },
  filterChip: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: colors.bgCard || '#FFFFFF',
    borderWidth: 1.5,
    borderColor: colors.border || '#E5E7EB',
    ...shadows.sm,
  },
  filterChipActive: {
    backgroundColor: colors.primary || '#6C63FF',
    borderColor: colors.primary || '#6C63FF',
  },
  filterText: { fontSize: 13, fontWeight: '600', color: colors.textSecondary || '#4B5563' },
  filterTextActive: { color: colors.textInverse || '#FFFFFF' },
  listContent: { padding: spacing.lg, paddingBottom: spacing.huge },
  card: { marginBottom: spacing.sm },
  cardRow: { flexDirection: 'row', gap: 12, alignItems: 'flex-start' },
  iconCircle: { width: 44, height: 44, borderRadius: 14, justifyContent: 'center', alignItems: 'center' },
  cardIcon: { fontSize: 20 },
  cardContent: { flex: 1 },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8 },
  cardTitle: { fontSize: 15, fontWeight: '700', color: colors.textPrimary || '#1F2937', flex: 1 },
  statusTag: { paddingHorizontal: 8, paddingVertical: 4, borderRadius: 8 },
  statusTagText: { fontSize: 10, fontWeight: '700' },
  cardDesc: { fontSize: 13, color: colors.textSecondary || '#4B5563', marginTop: 4, lineHeight: 18 },
  metaRow: { flexDirection: 'row', gap: 12, marginTop: 8, marginBottom: 4 },
  metaText: { fontSize: 11, color: colors.textMuted || '#9CA3AF' },
  resolveBtn: {
    marginTop: 12,
    paddingVertical: 8,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    ...shadows.sm,
  },
  resolveBtnText: { fontSize: 12, fontWeight: '700', color: '#fff' },
});

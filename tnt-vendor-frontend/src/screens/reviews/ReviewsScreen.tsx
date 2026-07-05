// ─── Premium Reviews Screen ──────────────────────────────────────
// Customer reviews and ratings management

import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Animated,
  ActivityIndicator,
  RefreshControl,
  TextInput,
  Alert,
} from 'react-native';
import { reviewApi, type Review, type ReviewStats } from '../../services/reviewApi';
import { colors as staticColors, shadows, spacing } from '../../design-system';
const colors = staticColors;
import GlassCard from '../../design-system/components/GlassCard';
import StatCard from '../../design-system/components/StatCard';
import StatusPill from '../../design-system/components/StatusPill';
import PremiumEmptyState from '../../design-system/components/PremiumEmptyState';

const STARS = [5, 4, 3, 2, 1];

export default function ReviewsScreen({ navigation }: any) {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [stats, setStats] = useState<ReviewStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [ratingFilter, setRatingFilter] = useState<number | null>(null);
  const [replyText, setReplyText] = useState<Record<number, string>>({});
  const [replyingId, setReplyingId] = useState<number | null>(null);
  const [sendingReply, setSendingReply] = useState(false);

  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }).start();
    loadData();
  }, []);

  const loadData = async (isRefresh = false) => {
    try {
      if (!isRefresh) setLoading(true);
      const [revRes, statsRes] = await Promise.all([
        reviewApi.getReviews({ per_page: 50 }),
        reviewApi.getReviewStats(),
      ]);
      const reviewData = revRes.data;
      setReviews(Array.isArray(reviewData) ? reviewData : reviewData.reviews || []);
      setStats(statsRes.data);
    } catch (err) {
      console.error('Reviews load error:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const filteredReviews = useMemo(() => {
    if (!ratingFilter) return reviews;
    return reviews.filter(r => r.rating === ratingFilter);
  }, [reviews, ratingFilter]);

  const handleReply = async (reviewId: number) => {
    const reply = replyText[reviewId]?.trim();
    if (!reply) {
      Alert.alert('Error', 'Please enter a reply message.');
      return;
    }
    setSendingReply(true);
    try {
      await reviewApi.replyToReview(reviewId, reply);
      Alert.alert('Success', 'Reply submitted.');
      setReplyingId(null);
      setReplyText(prev => ({ ...prev, [reviewId]: '' }));
    } catch (err: any) {
      Alert.alert('Error', err?.response?.data?.detail || 'Failed to send reply.');
    } finally {
      setSendingReply(false);
    }
  };

  if (loading) {
    return (
      <View style={[styles.container, styles.centered]}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading reviews...</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      showsVerticalScrollIndicator={false}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadData(true); }} tintColor={colors.primary} />}
    >
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerDeco1} />
        <View style={styles.headerDeco2} />
        <Text style={styles.headerTitle}>Reviews</Text>
        <Text style={styles.headerSubtitle}>Customer feedback & ratings</Text>
      </View>

      <Animated.View style={{ opacity: fadeAnim }}>
        {/* Stats */}
        {stats && (
          <View style={styles.statsRow}>
            <StatCard
              value={stats.average_rating || 0}
              label="Avg Rating"
              icon="⭐"
              color={colors.warning}
              style={{ flex: 1 }}
            />
            <StatCard
              value={stats.total_reviews || 0}
              label="Total Reviews"
              icon="💬"
              color={colors.primary}
              style={{ flex: 1 }}
            />
          </View>
        )}

        {/* Rating distribution */}
        {stats?.distribution && (
          <View style={styles.section}>
            <GlassCard padding={16} borderRadius={20}>
              <Text style={styles.sectionTitle}>⭐ Rating Breakdown</Text>
              {STARS.map(star => {
                const count = stats.distribution[star] || 0;
                const total = stats.total_reviews || 1;
                const pct = (count / total) * 100;
                return (
                  <TouchableOpacity
                    key={star}
                    style={styles.distRow}
                    onPress={() => setRatingFilter(ratingFilter === star ? null : star)}
                  >
                    <Text style={styles.distStar}>
                      {star} {star === 1 ? '★' : '★'}
                    </Text>
                    <View style={styles.distBarBg}>
                      <View style={[styles.distBar, { width: `${pct}%` }]} />
                    </View>
                    <Text style={styles.distCount}>{count}</Text>
                    {ratingFilter === star && (
                      <StatusPill label="FILTERED" variant="primary" size="sm" />
                    )}
                  </TouchableOpacity>
                );
              })}
            </GlassCard>
          </View>
        )}

        {/* Filter indicator */}
        {ratingFilter && (
          <View style={styles.filterRow}>
            <StatusPill label={`★ ${ratingFilter} Star Reviews`} variant="primary" size="sm" />
            <TouchableOpacity onPress={() => setRatingFilter(null)}>
              <Text style={{ color: colors.primary, fontSize: 13, fontWeight: '600' }}>Clear filter</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* Reviews list */}
        <View style={styles.section}>
          {filteredReviews.length === 0 ? (
            <PremiumEmptyState
              icon="⭐"
              title="No reviews yet"
              description={ratingFilter ? 'No reviews match the selected rating.' : 'Customer reviews will appear here.'}
            />
          ) : (
            filteredReviews.map(review => (
              <GlassCard key={review.id} padding={16} borderRadius={18} style={{ marginBottom: spacing.sm }}>
                {/* Header */}
                <View style={styles.reviewHeader}>
                  <View style={styles.reviewUser}>
                    <Text style={styles.reviewName}>{review.user_name || 'Anonymous'}</Text>
                    <Text style={styles.reviewDate}>
                      {new Date(review.created_at).toLocaleDateString('en-US', {
                        month: 'short', day: 'numeric', year: 'numeric',
                      })}
                    </Text>
                  </View>
                  <View style={styles.ratingRow}>
                    {[1, 2, 3, 4, 5].map(s => (
                      <Text key={s} style={[styles.starIcon, s <= review.rating && styles.starActive]}>
                        ★
                      </Text>
                    ))}
                  </View>
                </View>

                {/* Comment */}
                <Text style={styles.reviewComment}>{review.comment}</Text>

                {/* Order reference */}
                <Text style={styles.reviewOrder}>Order #{review.order_id}</Text>

                {/* Reply section */}
                {replyingId === review.id ? (
                  <View style={styles.replySection}>
                    <TextInput
                      style={styles.replyInput}
                      value={replyText[review.id] || ''}
                      onChangeText={t => setReplyText(prev => ({ ...prev, [review.id]: t }))}
                      placeholder="Write your reply..."
                      placeholderTextColor={colors.textMuted}
                      multiline
                    />
                    <View style={styles.replyActions}>
                      <TouchableOpacity
                        style={[styles.replyBtn, { backgroundColor: colors.bgSecondary }]}
                        onPress={() => setReplyingId(null)}
                      >
                        <Text style={{ color: colors.textSecondary, fontWeight: '600', fontSize: 13 }}>Cancel</Text>
                      </TouchableOpacity>
                      <TouchableOpacity
                        style={[styles.replyBtn, { backgroundColor: colors.primary }]}
                        onPress={() => handleReply(review.id)}
                        disabled={sendingReply}
                      >
                        {sendingReply ? (
                          <ActivityIndicator color={colors.textInverse} size="small" />
                        ) : (
                          <Text style={{ color: colors.textInverse, fontWeight: '700', fontSize: 13 }}>Send Reply</Text>
                        )}
                      </TouchableOpacity>
                    </View>
                  </View>
                ) : (
                  <TouchableOpacity
                    style={[styles.replyButton, { backgroundColor: colors.primaryPale }]}
                    onPress={() => setReplyingId(review.id)}
                  >
                    <Text style={[styles.replyButtonText, { color: colors.primary }]}>💬 Reply</Text>
                  </TouchableOpacity>
                )}
              </GlassCard>
            ))
          )}
        </View>

        <View style={{ height: spacing.huge }} />
      </Animated.View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  centered: { justifyContent: 'center', alignItems: 'center' },
  loadingText: { marginTop: 12, fontSize: 14, color: colors.textMuted, fontWeight: '600' },
  header: {
    backgroundColor: colors.primary,
    paddingTop: spacing.huge + 20,
    paddingBottom: spacing.xxl,
    paddingHorizontal: spacing.xl,
    borderBottomLeftRadius: 28,
    borderBottomRightRadius: 28,
    overflow: 'hidden',
  },
  headerDeco1: { position: 'absolute', top: -40, right: -30, width: 180, height: 180, borderRadius: 90, backgroundColor: 'rgba(255,255,255,0.08)' },
  headerDeco2: { position: 'absolute', bottom: -30, left: -60, width: 140, height: 140, borderRadius: 70, backgroundColor: 'rgba(255,255,255,0.05)' },
  headerTitle: { fontSize: 28, fontWeight: '700', color: colors.textInverse, letterSpacing: -0.3 },
  headerSubtitle: { fontSize: 14, color: 'rgba(255,255,255,0.7)', marginTop: 4, fontWeight: '500' },
  statsRow: { flexDirection: 'row', paddingHorizontal: spacing.lg, marginTop: -16, marginBottom: spacing.md, gap: spacing.sm },
  section: { paddingHorizontal: spacing.lg, marginBottom: spacing.sm },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: colors.textPrimary, marginBottom: 12 },
  distRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 8, gap: 8 },
  distStar: { fontSize: 14, color: colors.textSecondary, fontWeight: '600', width: 30 },
  distBarBg: { flex: 1, height: 8, borderRadius: 4, backgroundColor: colors.bgSecondary, overflow: 'hidden' },
  distBar: { height: '100%', borderRadius: 4, backgroundColor: colors.warning },
  distCount: { fontSize: 13, color: colors.textMuted, fontWeight: '600', width: 30, textAlign: 'right' },
  filterRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: spacing.lg, marginBottom: spacing.sm },
  reviewHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 },
  reviewUser: { flex: 1 },
  reviewName: { fontSize: 15, fontWeight: '700', color: colors.textPrimary },
  reviewDate: { fontSize: 11, color: colors.textMuted, marginTop: 2 },
  ratingRow: { flexDirection: 'row', gap: 2 },
  starIcon: { fontSize: 16, color: colors.border },
  starActive: { color: colors.warning },
  reviewComment: { fontSize: 14, color: colors.textSecondary, lineHeight: 20, marginBottom: 6 },
  reviewOrder: { fontSize: 11, color: colors.textMuted, fontWeight: '500', marginBottom: 8 },
  replySection: { marginTop: 8 },
  replyInput: {
    backgroundColor: colors.bgSecondary,
    borderRadius: 12,
    padding: 12,
    fontSize: 13,
    color: colors.textPrimary,
    borderWidth: 1,
    borderColor: colors.border,
    minHeight: 60,
    textAlignVertical: 'top',
  },
  replyActions: { flexDirection: 'row', gap: 8, marginTop: 8, justifyContent: 'flex-end' },
  replyBtn: { paddingHorizontal: 16, paddingVertical: 8, borderRadius: 10, alignItems: 'center', minWidth: 80 },
  replyButton: { paddingHorizontal: 12, paddingVertical: 8, borderRadius: 10, alignSelf: 'flex-start', marginTop: 4 },
  replyButtonText: { fontSize: 12, fontWeight: '700' },
});

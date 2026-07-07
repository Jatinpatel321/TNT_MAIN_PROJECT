import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';
import { Text } from 'react-native-paper';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../types/navigation';
import { Screen } from '../../components/Screen';
import {
  getVendorFeedbackSummary,
  getVendorReviews,
} from '../../services/feedbackService';
import type { VendorFeedbackSummary, VendorReview } from '../../types/models';

type Props = NativeStackScreenProps<RootStackParamList, 'ReviewHistory'>;

function RatingBar({ label, value, max }: { label: string; value: number; max: number }) {
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <View style={rStyles.row}>
      <Text style={rStyles.label}>{label}</Text>
      <View style={rStyles.barBg}>
        <View style={[rStyles.barFill, { width: `${pct}%` }]} />
      </View>
      <Text style={rStyles.value}>{value.toFixed(1)}</Text>
    </View>
  );
}

const ratingBarConfig = [
  { key: 'avg_quality_rating', label: 'Quality' },
  { key: 'avg_time_rating', label: 'Speed' },
  { key: 'avg_behavior_rating', label: 'Behavior' },
] as const;

export function ReviewHistoryScreen({ route }: Props) {
  const { vendorId, vendorName } = route.params;
  const [summary, setSummary] = useState<VendorFeedbackSummary | null>(null);
  const [reviews, setReviews] = useState<VendorReview[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadData = async () => {
    try {
      const [s, r] = await Promise.all([
        getVendorFeedbackSummary(vendorId),
        getVendorReviews(vendorId),
      ]);
      setSummary(s);
      setReviews(r);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [vendorId]);

  const onRefresh = () => {
    setRefreshing(true);
    loadData();
  };

  if (loading) {
    return (
      <Screen>
        <View style={styles.center}>
          <ActivityIndicator size="large" color="#3B82F6" />
        </View>
      </Screen>
    );
  }

  return (
    <Screen>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.header}>
          <Text style={styles.title}>
            {vendorName || 'Vendor'} Reviews
          </Text>
        </View>

        {summary && (
          <View style={styles.summaryCard}>
            <View style={styles.overallBadge}>
              <Text style={styles.overallNum}>
                {summary.avg_overall_rating.toFixed(1)}
              </Text>
              <Text style={styles.overallMax}>/5</Text>
            </View>
            <Text style={styles.totalReviews}>
              {summary.total_reviews} review{summary.total_reviews !== 1 ? 's' : ''}
            </Text>

            <View style={styles.ratingBars}>
              {ratingBarConfig.map((cfg) => (
                <RatingBar
                  key={cfg.key}
                  label={cfg.label}
                  value={summary[cfg.key]}
                  max={5}
                />
              ))}
            </View>

            {Object.keys(summary.rating_distribution).length > 0 && (
              <View style={styles.distSection}>
                <Text style={styles.distTitle}>Rating Breakdown</Text>
                {[5, 4, 3, 2, 1].map((star) => {
                  const count = summary.rating_distribution[star] || 0;
                  const total = Object.values(
                    summary.rating_distribution,
                  ).reduce((a, b) => a + b, 0);
                  const pct = total > 0 ? (count / total) * 100 : 0;
                  return (
                    <View key={star} style={dStyles.row}>
                      <Text style={dStyles.starLabel}>
                        {star} {'\u2605'}
                      </Text>
                      <View style={dStyles.barBg}>
                        <View
                          style={[dStyles.barFill, { width: `${pct}%` }]}
                        />
                      </View>
                      <Text style={dStyles.count}>{count}</Text>
                    </View>
                  );
                })}
              </View>
            )}
          </View>
        )}

        <View style={styles.reviewsSection}>
          <Text style={styles.sectionTitle}>
            Customer Reviews ({reviews.length})
          </Text>

          {reviews.length === 0 && (
            <View style={styles.emptyState}>
              <Text style={styles.emptyText}>
                No reviews yet. Be the first to review!
              </Text>
            </View>
          )}

          {reviews.map((review) => (
            <Pressable key={review.id} style={styles.reviewCard}>
              <View style={styles.reviewHeader}>
                <View style={styles.reviewStars}>
                  {[1, 2, 3, 4, 5].map((n) => (
                    <Text
                      key={n}
                      style={[
                        styles.reviewStarChar,
                        n <= review.rating && styles.reviewStarFilled,
                      ]}
                    >
                      {'\u2605'}
                    </Text>
                  ))}
                </View>
                <Text style={styles.reviewDate}>
                  {new Date(review.created_at).toLocaleDateString()}
                </Text>
              </View>
              {review.title && (
                <Text style={styles.reviewTitle}>{review.title}</Text>
              )}
              {review.reviewer_name && !review.is_anonymous && (
                <Text style={styles.reviewerName}>
                  by {review.reviewer_name}
                </Text>
              )}
              {review.is_anonymous && (
                <Text style={styles.reviewerName}>by Anonymous</Text>
              )}
              {review.review_text && (
                <Text style={styles.reviewBody}>{review.review_text}</Text>
              )}
            </Pressable>
          ))}
        </View>
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  scroll: {
    paddingBottom: 32,
    gap: 16,
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  header: {
    paddingVertical: 8,
  },
  title: {
    fontSize: 22,
    fontWeight: '900',
    color: '#111827',
  },
  summaryCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    padding: 20,
    gap: 12,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowOffset: { width: 0, height: 3 },
    shadowRadius: 8,
    elevation: 3,
  },
  overallBadge: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: 2,
  },
  overallNum: {
    fontSize: 36,
    fontWeight: '900',
    color: '#111827',
  },
  overallMax: {
    fontSize: 16,
    color: '#9CA3AF',
  },
  totalReviews: {
    fontSize: 14,
    color: '#6B7280',
    marginTop: -4,
  },
  ratingBars: {
    gap: 8,
    marginTop: 4,
  },
  distSection: {
    marginTop: 8,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#F3F4F6',
    gap: 6,
  },
  distTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#374151',
    marginBottom: 4,
  },
  reviewsSection: {
    gap: 12,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '800',
    color: '#111827',
  },
  emptyState: {
    backgroundColor: '#F9FAFB',
    borderRadius: 16,
    padding: 24,
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 14,
    color: '#9CA3AF',
    textAlign: 'center',
  },
  reviewCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 16,
    gap: 6,
    shadowColor: '#000',
    shadowOpacity: 0.04,
    shadowOffset: { width: 0, height: 2 },
    shadowRadius: 6,
    elevation: 2,
  },
  reviewHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  reviewStars: {
    flexDirection: 'row',
    gap: 2,
  },
  reviewStarChar: {
    fontSize: 16,
    color: '#D1D5DB',
  },
  reviewStarFilled: {
    color: '#FBBF24',
  },
  reviewDate: {
    fontSize: 12,
    color: '#9CA3AF',
  },
  reviewTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: '#111827',
  },
  reviewerName: {
    fontSize: 12,
    color: '#9CA3AF',
    fontStyle: 'italic',
  },
  reviewBody: {
    fontSize: 14,
    color: '#4B5563',
    lineHeight: 20,
  },
});

const rStyles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  label: {
    fontSize: 13,
    fontWeight: '600',
    color: '#6B7280',
    width: 60,
  },
  barBg: {
    flex: 1,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#F3F4F6',
    overflow: 'hidden',
  },
  barFill: {
    height: '100%',
    borderRadius: 4,
    backgroundColor: '#3B82F6',
  },
  value: {
    fontSize: 13,
    fontWeight: '700',
    color: '#111827',
    width: 30,
    textAlign: 'right',
  },
});

const dStyles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  starLabel: {
    fontSize: 12,
    color: '#6B7280',
    width: 30,
  },
  barBg: {
    flex: 1,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#F3F4F6',
    overflow: 'hidden',
  },
  barFill: {
    height: '100%',
    borderRadius: 3,
    backgroundColor: '#FBBF24',
  },
  count: {
    fontSize: 12,
    color: '#9CA3AF',
    width: 24,
    textAlign: 'right',
  },
});

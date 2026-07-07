import React, { useState } from 'react';
import {
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  TextInput,
  View,
} from 'react-native';
import { Text } from 'react-native-paper';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../types/navigation';
import { Screen } from '../../components/Screen';
import { GradientButton } from '../../components/GradientButton';
import {
  submitFeedback,
  submitVendorReview,
} from '../../services/feedbackService';
import { toApiError } from '../../services/apiClient';

type Props = NativeStackScreenProps<RootStackParamList, 'Feedback'>;

const STAR_CATEGORIES: {
  key: 'quality_rating' | 'time_rating' | 'behavior_rating';
  label: string;
  emoji: string;
}[] = [
  { key: 'quality_rating', label: 'Food Quality', emoji: '\u{1F354}' },
  { key: 'time_rating', label: 'Pickup Speed', emoji: '\u26A1' },
  { key: 'behavior_rating', label: 'Staff Behavior', emoji: '\u{1F60A}' },
];

function StarRow({
  label,
  emoji,
  value,
  onChange,
}: {
  label: string;
  emoji: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <View style={styles.starRow}>
      <View style={styles.starLabel}>
        <Text style={styles.starEmoji}>{emoji}</Text>
        <Text style={styles.starLabelText}>{label}</Text>
      </View>
      <View style={styles.stars}>
        {[1, 2, 3, 4, 5].map((n) => (
          <Pressable key={n} onPress={() => onChange(n)} style={styles.starBtn}>
            <Text style={[styles.star, n <= value && styles.starFilled]}>
              {'\u2605'}
            </Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

export function FeedbackScreen({ route, navigation }: Props) {
  const { orderId, vendorName } = route.params;

  const [ratings, setRatings] = useState<Record<string, number>>({
    quality_rating: 0,
    time_rating: 0,
    behavior_rating: 0,
  });
  const [comment, setComment] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const [showVendorReview, setShowVendorReview] = useState(false);
  const [vendorRating, setVendorRating] = useState(0);
  const [reviewTitle, setReviewTitle] = useState('');
  const [reviewText, setReviewText] = useState('');
  const [isAnonymous, setIsAnonymous] = useState(false);

  const allRated = STAR_CATEGORIES.every((c) => (ratings[c.key] ?? 0) > 0);
  const overallRating = allRated
    ? Math.round(
        (ratings.quality_rating +
          ratings.time_rating +
          ratings.behavior_rating) /
          3,
      )
    : 0;

  const canSubmitVendorReview = vendorRating > 0;
  const canSubmit = allRated && (!showVendorReview || canSubmitVendorReview);

  const onSubmit = async () => {
    if (!allRated) {
      Alert.alert('Please rate all categories before submitting.');
      return;
    }
    if (showVendorReview && !canSubmitVendorReview) {
      Alert.alert('Please rate the vendor before submitting.');
      return;
    }
    try {
      setSubmitting(true);
      const result = await submitFeedback(orderId, {
        quality_rating: ratings.quality_rating,
        time_rating: ratings.time_rating,
        behavior_rating: ratings.behavior_rating,
        overall_rating: overallRating,
        comment: comment.trim() || undefined,
      });

      if (showVendorReview && canSubmitVendorReview) {
        try {
          await submitVendorReview(result.feedback_id, {
            rating: vendorRating,
            title: reviewTitle.trim() || undefined,
            review_text: reviewText.trim() || undefined,
            is_anonymous: isAnonymous,
            order_id: orderId,
          });
        } catch {
          // Vendor review failure doesn't block feedback success
        }
      }

      Alert.alert('Thank you!', 'Your feedback has been recorded.', [
        { text: 'Done', onPress: () => navigation.goBack() },
      ]);
    } catch (e) {
      const err = toApiError(e);
      if (err.status === 400) {
        Alert.alert('Already rated', err.message, [
          { text: 'OK', onPress: () => navigation.goBack() },
        ]);
      } else {
        Alert.alert('Submission failed', err.message);
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Screen>
      <ScrollView
        contentContainerStyle={styles.scroll}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.header}>
          <Text style={styles.title}>Rate your order</Text>
          <Text style={styles.sub}>
            {vendorName
              ? `from ${vendorName}`
              : `Order #${orderId}`}
          </Text>
        </View>

        <View style={styles.card}>
          {STAR_CATEGORIES.map((cat) => (
            <StarRow
              key={cat.key}
              label={cat.label}
              emoji={cat.emoji}
              value={ratings[cat.key] ?? 0}
              onChange={(v) =>
                setRatings((prev) => ({ ...prev, [cat.key]: v }))
              }
            />
          ))}

          {allRated && (
            <View style={styles.overallRow}>
              <Text style={styles.overallLabel}>Overall Rating</Text>
              <View style={styles.overallValue}>
                <Text style={styles.overallStar}>{'\u2605'}</Text>
                <Text style={styles.overallNumber}>{overallRating}</Text>
                <Text style={styles.overallMax}>/5</Text>
              </View>
            </View>
          )}
        </View>

        <View style={styles.commentCard}>
          <Text style={styles.commentLabel}>
            Additional comments (optional)
          </Text>
          <TextInput
            style={styles.commentInput}
            multiline
            numberOfLines={4}
            placeholder="Tell us more about your experience..."
            placeholderTextColor="#9CA3AF"
            value={comment}
            onChangeText={setComment}
            maxLength={500}
          />
          <Text style={styles.charCount}>{comment.length}/500</Text>
        </View>

        <View style={styles.toggleRow}>
          <Text style={styles.toggleLabel}>Write a vendor review</Text>
          <Switch
            value={showVendorReview}
            onValueChange={setShowVendorReview}
            trackColor={{ false: '#D1D5DB', true: '#3B82F6' }}
            thumbColor="#FFFFFF"
          />
        </View>

        {showVendorReview && (
          <View style={styles.reviewCard}>
            <Text style={styles.reviewTitle}>
              Review {vendorName || 'Vendor'}
            </Text>

            <View style={styles.vendorStars}>
              {[1, 2, 3, 4, 5].map((n) => (
                <Pressable
                  key={n}
                  onPress={() => setVendorRating(n)}
                  style={styles.starBtn}
                >
                  <Text
                    style={[
                      styles.vendorStar,
                      n <= vendorRating && styles.starFilled,
                    ]}
                  >
                    {'\u2605'}
                  </Text>
                </Pressable>
              ))}
              {vendorRating > 0 && (
                <Text style={styles.vendorRatingNum}>{vendorRating}/5</Text>
              )}
            </View>

            <TextInput
              style={styles.reviewInput}
              placeholder="Review title (optional)"
              placeholderTextColor="#9CA3AF"
              value={reviewTitle}
              onChangeText={setReviewTitle}
              maxLength={100}
            />
            <TextInput
              style={[styles.reviewInput, styles.reviewTextArea]}
              multiline
              numberOfLines={3}
              placeholder="Share your experience with this vendor..."
              placeholderTextColor="#9CA3AF"
              value={reviewText}
              onChangeText={setReviewText}
              maxLength={300}
            />

            <View style={styles.anonymousRow}>
              <Text style={styles.anonymousLabel}>Post anonymously</Text>
              <Switch
                value={isAnonymous}
                onValueChange={setIsAnonymous}
                trackColor={{ false: '#D1D5DB', true: '#3B82F6' }}
                thumbColor="#FFFFFF"
              />
            </View>
          </View>
        )}

        <GradientButton
          label={submitting ? 'Submitting...' : 'Submit Feedback'}
          onPress={onSubmit}
          disabled={!canSubmit || submitting}
        />
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  scroll: {
    paddingBottom: 32,
    gap: 16,
  },
  header: {
    paddingVertical: 12,
  },
  title: {
    fontSize: 22,
    fontWeight: '900',
    color: '#111827',
  },
  sub: {
    fontSize: 14,
    color: '#6B7280',
    marginTop: 4,
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    padding: 16,
    gap: 16,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowOffset: { width: 0, height: 3 },
    shadowRadius: 8,
    elevation: 3,
  },
  starRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  starLabel: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flex: 1,
  },
  starEmoji: {
    fontSize: 18,
  },
  starLabelText: {
    fontSize: 15,
    fontWeight: '700',
    color: '#111827',
  },
  stars: {
    flexDirection: 'row',
    gap: 4,
  },
  starBtn: {
    padding: 2,
  },
  star: {
    fontSize: 26,
    color: '#D1D5DB',
  },
  starFilled: {
    color: '#FBBF24',
  },
  overallRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#F3F4F6',
  },
  overallLabel: {
    fontSize: 15,
    fontWeight: '700',
    color: '#374151',
  },
  overallValue: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  overallStar: {
    fontSize: 20,
    color: '#FBBF24',
  },
  overallNumber: {
    fontSize: 18,
    fontWeight: '900',
    color: '#111827',
  },
  overallMax: {
    fontSize: 14,
    color: '#9CA3AF',
  },
  commentCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    padding: 16,
    shadowColor: '#000',
    shadowOpacity: 0.04,
    shadowOffset: { width: 0, height: 3 },
    shadowRadius: 6,
    elevation: 2,
    gap: 8,
  },
  commentLabel: {
    fontSize: 14,
    fontWeight: '700',
    color: '#374151',
  },
  commentInput: {
    borderWidth: 1,
    borderColor: '#E5E7EB',
    borderRadius: 12,
    padding: 12,
    fontSize: 14,
    color: '#111827',
    minHeight: 90,
    textAlignVertical: 'top',
  },
  charCount: {
    fontSize: 12,
    color: '#9CA3AF',
    textAlign: 'right',
  },
  toggleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 4,
  },
  toggleLabel: {
    fontSize: 15,
    fontWeight: '600',
    color: '#374151',
  },
  reviewCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    padding: 16,
    gap: 12,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowOffset: { width: 0, height: 3 },
    shadowRadius: 8,
    elevation: 3,
  },
  reviewTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#111827',
  },
  vendorStars: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  vendorStar: {
    fontSize: 30,
    color: '#D1D5DB',
  },
  vendorRatingNum: {
    fontSize: 14,
    fontWeight: '700',
    color: '#374151',
    marginLeft: 8,
  },
  reviewInput: {
    borderWidth: 1,
    borderColor: '#E5E7EB',
    borderRadius: 12,
    padding: 12,
    fontSize: 14,
    color: '#111827',
  },
  reviewTextArea: {
    minHeight: 80,
    textAlignVertical: 'top',
  },
  anonymousRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  anonymousLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#6B7280',
  },
});

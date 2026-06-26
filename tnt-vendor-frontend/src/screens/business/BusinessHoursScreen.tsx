import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { businessSettingsApi } from '../../services/businessSettingsApi';

const DAYS = [
  { key: 'monday', label: 'Monday', short: 'Mon' },
  { key: 'tuesday', label: 'Tuesday', short: 'Tue' },
  { key: 'wednesday', label: 'Wednesday', short: 'Wed' },
  { key: 'thursday', label: 'Thursday', short: 'Thu' },
  { key: 'friday', label: 'Friday', short: 'Fri' },
  { key: 'saturday', label: 'Saturday', short: 'Sat' },
  { key: 'sunday', label: 'Sunday', short: 'Sun' },
];

interface DayHours {
  open: string;
  close: string;
  is_closed: boolean;
}

export default function BusinessHoursScreen({ navigation }: any) {
  const [hours, setHours] = useState<{ [key: string]: DayHours }>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadBusinessHours();
  }, []);

  const loadBusinessHours = async () => {
    try {
      setLoading(true);
      const response = await businessSettingsApi.getSettings();
      const businessHours = response.data.business_hours || {};
      
      // Initialize default hours if not set
      const defaultHours: { [key: string]: DayHours } = {};
      DAYS.forEach(day => {
        defaultHours[day.key] = businessHours[day.key] || {
          open: '09:00',
          close: '18:00',
          is_closed: false,
        };
      });
      
      setHours(defaultHours);
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Failed to load business hours');
    } finally {
      setLoading(false);
    }
  };

  const updateDayHours = (dayKey: string, field: keyof DayHours, value: string | boolean) => {
    setHours({
      ...hours,
      [dayKey]: {
        ...hours[dayKey],
        [field]: value,
      },
    });
  };

  const copyToAllDays = (sourceDay: string) => {
    const sourceHours = hours[sourceDay];
    const newHours: { [key: string]: DayHours } = {};
    
    DAYS.forEach(day => {
      newHours[day.key] = { ...sourceHours };
    });
    
    setHours(newHours);
    Alert.alert('Success', 'Hours copied to all days');
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await businessSettingsApi.updateBusinessHours(hours);
      Alert.alert('Success', 'Business hours updated successfully');
      navigation.goBack();
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Failed to save business hours');
    } finally {
      setSaving(false);
    }
  };

  const toggleDayClosed = (dayKey: string) => {
    updateDayHours(dayKey, 'is_closed', !hours[dayKey].is_closed);
  };

  if (loading) {
    return (
      <View style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Business Hours</Text>
        </View>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#10B981" />
          <Text style={styles.loadingText}>Loading business hours...</Text>
        </View>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Business Hours</Text>
        <Text style={styles.headerSubtitle}>Set your operating hours for each day</Text>
      </View>

      <View style={styles.content}>
        {DAYS.map((day, index) => (
          <View key={day.key} style={styles.dayCard}>
            <View style={styles.dayHeader}>
              <View style={styles.dayInfo}>
                <Text style={styles.dayLabel}>{day.label}</Text>
                <TouchableOpacity
                  style={[
                    styles.closedBadge,
                    hours[day.key].is_closed && styles.closedBadgeActive,
                  ]}
                  onPress={() => toggleDayClosed(day.key)}
                >
                  <Text style={[
                    styles.closedBadgeText,
                    hours[day.key].is_closed && styles.closedBadgeTextActive,
                  ]}>
                    {hours[day.key].is_closed ? 'CLOSED' : 'OPEN'}
                  </Text>
                </TouchableOpacity>
              </View>
              
              {index === 0 && (
                <TouchableOpacity
                  style={styles.copyButton}
                  onPress={() => copyToAllDays(day.key)}
                >
                  <Text style={styles.copyButtonText}>📋 Copy to All</Text>
                </TouchableOpacity>
              )}
            </View>

            {!hours[day.key].is_closed && (
              <View style={styles.timeRow}>
                <View style={styles.timeInputContainer}>
                  <Text style={styles.timeLabel}>Opening Time</Text>
                  <TouchableOpacity style={styles.timeButton}>
                    <Text style={styles.timeText}>{hours[day.key].open}</Text>
                  </TouchableOpacity>
                </View>

                <Text style={styles.timeSeparator}>→</Text>

                <View style={styles.timeInputContainer}>
                  <Text style={styles.timeLabel}>Closing Time</Text>
                  <TouchableOpacity style={styles.timeButton}>
                    <Text style={styles.timeText}>{hours[day.key].close}</Text>
                  </TouchableOpacity>
                </View>
              </View>
            )}
          </View>
        ))}

        <TouchableOpacity
          style={[styles.saveButton, saving && styles.saveButtonDisabled]}
          onPress={handleSave}
          disabled={saving}
        >
          {saving ? (
            <ActivityIndicator color="white" />
          ) : (
            <Text style={styles.saveButtonText}>Save Business Hours</Text>
          )}
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F9FAFB',
  },
  header: {
    padding: 20,
    paddingTop: 60,
    backgroundColor: '#10B981',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: 'white',
    marginBottom: 4,
  },
  headerSubtitle: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.8)',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 40,
    marginTop: 100,
  },
  loadingText: {
    fontSize: 16,
    color: '#6B7280',
    marginTop: 12,
  },
  content: {
    padding: 16,
  },
  dayCard: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  dayHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  dayInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  dayLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
  },
  closedBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
    backgroundColor: '#D1FAE5',
    borderWidth: 1,
    borderColor: '#10B981',
  },
  closedBadgeActive: {
    backgroundColor: '#FEE2E2',
    borderColor: '#EF4444',
  },
  closedBadgeText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#10B981',
  },
  closedBadgeTextActive: {
    color: '#EF4444',
  },
  copyButton: {
    backgroundColor: '#3B82F6',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
  },
  copyButtonText: {
    fontSize: 12,
    color: 'white',
    fontWeight: '600',
  },
  timeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
  },
  timeInputContainer: {
    flex: 1,
  },
  timeLabel: {
    fontSize: 12,
    color: '#6B7280',
    marginBottom: 6,
  },
  timeButton: {
    backgroundColor: '#F3F4F6',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#D1D5DB',
  },
  timeText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
  },
  timeSeparator: {
    fontSize: 20,
    color: '#6B7280',
    marginTop: 20,
  },
  saveButton: {
    backgroundColor: '#10B981',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    marginTop: 20,
    marginBottom: 40,
  },
  saveButtonDisabled: {
    backgroundColor: '#9CA3AF',
  },
  saveButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
});
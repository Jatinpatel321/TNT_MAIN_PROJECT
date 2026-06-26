import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { slotApi } from '../../services/slotApi';

interface CapacityRule {
  id: number;
  rule_type: string;
  rule_config: {
    day_of_week?: number;
    hour_of_day?: number;
    max_capacity?: number;
    duration_minutes?: number;
  };
  is_enabled: boolean;
  priority: number;
}

export default function CapacitySettingsScreen({ navigation }: any) {
  const [rules, setRules] = useState<CapacityRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    rule_type: 'time_based',
    day_of_week: '0',
    hour_of_day: '9',
    max_capacity: '20',
    duration_minutes: '60',
    priority: '1',
  });

  useEffect(() => {
    fetchRules();
  }, []);

  const fetchRules = async () => {
    try {
      setLoading(true);
      const response = await slotApi.getCapacityRules();
      setRules(response.data);
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Failed to load capacity rules');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateRule = async () => {
    if (!formData.max_capacity || !formData.priority) {
      Alert.alert('Error', 'Please fill required fields');
      return;
    }

    try {
      setLoading(true);
      await slotApi.createCapacityRule({
        rule_type: formData.rule_type,
        rule_config: {
          day_of_week: formData.day_of_week ? parseInt(formData.day_of_week) : undefined,
          hour_of_day: formData.hour_of_day ? parseInt(formData.hour_of_day) : undefined,
          max_capacity: parseInt(formData.max_capacity),
          duration_minutes: formData.duration_minutes ? parseInt(formData.duration_minutes) : undefined,
        },
        is_enabled: true,
        priority: parseInt(formData.priority),
      });

      Alert.alert('Success', 'Capacity rule created successfully');
      setShowForm(false);
      fetchRules();
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Failed to create rule');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteRule = (ruleId: number) => {
    Alert.alert(
      'Delete Rule',
      'Are you sure you want to delete this rule?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await slotApi.deleteCapacityRule(ruleId);
              Alert.alert('Success', 'Rule deleted successfully');
              fetchRules();
            } catch (err: any) {
              Alert.alert('Error', err.message || 'Failed to delete rule');
            }
          },
        },
      ]
    );
  };

  const getDayName = (day: number): string => {
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    return days[day] || 'Every day';
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Capacity Settings</Text>
      </View>

      <View style={styles.section}>
        <TouchableOpacity
          style={styles.addButton}
          onPress={() => setShowForm(!showForm)}
        >
          <Text style={styles.addButtonText}>
            {showForm ? '❌ Cancel' : '➕ Add Capacity Rule'}
          </Text>
        </TouchableOpacity>

        {showForm && (
          <View style={styles.form}>
            <View style={styles.formGroup}>
              <Text style={styles.label}>Rule Type</Text>
              <TextInput
                style={styles.input}
                value={formData.rule_type}
                onChangeText={(text) => setFormData({ ...formData, rule_type: text })}
                placeholder="time_based"
                placeholderTextColor="#9CA3AF"
              />
            </View>

            <View style={styles.formGroup}>
              <Text style={styles.label}>Day of Week (0-6, 0=Sunday)</Text>
              <TextInput
                style={styles.input}
                value={formData.day_of_week}
                onChangeText={(text) => setFormData({ ...formData, day_of_week: text })}
                placeholder="0"
                placeholderTextColor="#9CA3AF"
                keyboardType="numeric"
              />
            </View>

            <View style={styles.formGroup}>
              <Text style={styles.label}>Hour of Day (0-23)</Text>
              <TextInput
                style={styles.input}
                value={formData.hour_of_day}
                onChangeText={(text) => setFormData({ ...formData, hour_of_day: text })}
                placeholder="9"
                placeholderTextColor="#9CA3AF"
                keyboardType="numeric"
              />
            </View>

            <View style={styles.formGroup}>
              <Text style={styles.label}>Max Capacity</Text>
              <TextInput
                style={styles.input}
                value={formData.max_capacity}
                onChangeText={(text) => setFormData({ ...formData, max_capacity: text })}
                placeholder="20"
                placeholderTextColor="#9CA3AF"
                keyboardType="numeric"
              />
            </View>

            <View style={styles.formGroup}>
              <Text style={styles.label}>Duration (minutes)</Text>
              <TextInput
                style={styles.input}
                value={formData.duration_minutes}
                onChangeText={(text) => setFormData({ ...formData, duration_minutes: text })}
                placeholder="60"
                placeholderTextColor="#9CA3AF"
                keyboardType="numeric"
              />
            </View>

            <View style={styles.formGroup}>
              <Text style={styles.label}>Priority (1-10)</Text>
              <TextInput
                style={styles.input}
                value={formData.priority}
                onChangeText={(text) => setFormData({ ...formData, priority: text })}
                placeholder="1"
                placeholderTextColor="#9CA3AF"
                keyboardType="numeric"
              />
            </View>

            <TouchableOpacity
              style={[styles.submitButton, loading && styles.submitButtonDisabled]}
              onPress={handleCreateRule}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator color="white" />
              ) : (
                <Text style={styles.submitButtonText}>Create Rule</Text>
              )}
            </TouchableOpacity>
          </View>
        )}
      </View>

      {/* Rules List */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Active Rules ({rules.length})</Text>
        {loading ? (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color="#10B981" />
          </View>
        ) : (
          rules.map((rule) => (
            <View key={rule.id} style={styles.ruleCard}>
              <View style={styles.ruleHeader}>
                <Text style={styles.ruleType}>{rule.rule_type}</Text>
                <View style={[
                  styles.statusBadge,
                  { backgroundColor: rule.is_enabled ? '#10B981' : '#EF4444' }
                ]}>
                  <Text style={styles.statusText}>
                    {rule.is_enabled ? 'Enabled' : 'Disabled'}
                  </Text>
                </View>
              </View>

              <View style={styles.ruleDetails}>
                {rule.rule_config.day_of_week !== undefined && (
                  <Text style={styles.ruleDetail}>
                    Day: {getDayName(rule.rule_config.day_of_week)}
                  </Text>
                )}
                {rule.rule_config.hour_of_day !== undefined && (
                  <Text style={styles.ruleDetail}>
                    Hour: {rule.rule_config.hour_of_day}:00
                  </Text>
                )}
                {rule.rule_config.max_capacity && (
                  <Text style={styles.ruleDetail}>
                    Max Capacity: {rule.rule_config.max_capacity}
                  </Text>
                )}
                {rule.rule_config.duration_minutes && (
                  <Text style={styles.ruleDetail}>
                    Duration: {rule.rule_config.duration_minutes} min
                  </Text>
                )}
                <Text style={styles.ruleDetail}>Priority: {rule.priority}</Text>
              </View>

              <TouchableOpacity
                style={styles.deleteButton}
                onPress={() => handleDeleteRule(rule.id)}
              >
                <Text style={styles.deleteButtonText}>Delete</Text>
              </TouchableOpacity>
            </View>
          ))
        )}
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
  },
  section: {
    padding: 16,
  },
  addButton: {
    backgroundColor: '#10B981',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    marginBottom: 16,
  },
  addButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  form: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  formGroup: {
    marginBottom: 16,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 8,
  },
  input: {
    backgroundColor: '#F9FAFB',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    borderWidth: 1,
    borderColor: '#D1D5DB',
    color: '#111827',
  },
  submitButton: {
    backgroundColor: '#10B981',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    marginTop: 8,
  },
  submitButtonDisabled: {
    backgroundColor: '#9CA3AF',
  },
  submitButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#111827',
    marginBottom: 12,
  },
  ruleCard: {
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
  ruleHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  ruleType: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
    textTransform: 'capitalize',
  },
  statusBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
  },
  statusText: {
    fontSize: 12,
    color: 'white',
    fontWeight: '600',
    textTransform: 'uppercase',
  },
  ruleDetails: {
    marginBottom: 12,
  },
  ruleDetail: {
    fontSize: 14,
    color: '#6B7280',
    marginBottom: 4,
  },
  deleteButton: {
    backgroundColor: '#EF4444',
    padding: 10,
    borderRadius: 8,
    alignItems: 'center',
  },
  deleteButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '600',
  },
  loadingContainer: {
    padding: 40,
    alignItems: 'center',
  },
});
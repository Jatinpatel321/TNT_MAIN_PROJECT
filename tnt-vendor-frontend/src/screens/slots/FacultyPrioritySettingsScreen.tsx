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

interface SlotRule {
  id: number;
  rule_type: string;
  rule_config: {
    auto_block_enabled?: boolean;
    block_threshold?: number;
    peak_hours?: { start: string; end: string; multiplier: number };
    faculty_priority_hours?: { start: number; end: number };
  };
  is_enabled: boolean;
  priority: number;
}

export default function FacultyPrioritySettingsScreen({ navigation }: any) {
  const [rules, setRules] = useState<SlotRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    rule_type: 'faculty_priority',
    start_hour: '9',
    end_hour: '17',
    priority: '5',
  });

  useEffect(() => {
    fetchRules();
  }, []);

  const fetchRules = async () => {
    try {
      setLoading(true);
      const response = await slotApi.getRules();
      setRules(response.data);
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Failed to load rules');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateRule = async () => {
    if (!formData.start_hour || !formData.end_hour) {
      Alert.alert('Error', 'Please fill required fields');
      return;
    }

    try {
      setLoading(true);
      await slotApi.createRule({
        rule_type: 'faculty_priority',
        rule_config: {
          faculty_priority_hours: {
            start: parseInt(formData.start_hour),
            end: parseInt(formData.end_hour),
          },
        },
        is_enabled: true,
        priority: parseInt(formData.priority),
      });

      Alert.alert('Success', 'Faculty priority rule created successfully');
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
              await slotApi.deleteRule(ruleId);
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

  const facultyRules = rules.filter(r => r.rule_type === 'faculty_priority');

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Faculty Priority Settings</Text>
      </View>

      <View style={styles.infoBox}>
        <Text style={styles.infoIcon}>ℹ️</Text>
        <Text style={styles.infoText}>
          Faculty priority slots are reserved for faculty members during specified hours. 
          Only faculty and admin users can book these slots.
        </Text>
      </View>

      <View style={styles.section}>
        <TouchableOpacity
          style={styles.addButton}
          onPress={() => setShowForm(!showForm)}
        >
          <Text style={styles.addButtonText}>
            {showForm ? '❌ Cancel' : '➕ Add Faculty Priority Rule'}
          </Text>
        </TouchableOpacity>

        {showForm && (
          <View style={styles.form}>
            <View style={styles.formGroup}>
              <Text style={styles.label}>Start Hour (0-23)</Text>
              <TextInput
                style={styles.input}
                value={formData.start_hour}
                onChangeText={(text) => setFormData({ ...formData, start_hour: text })}
                placeholder="9"
                placeholderTextColor="#9CA3AF"
                keyboardType="numeric"
              />
            </View>

            <View style={styles.formGroup}>
              <Text style={styles.label}>End Hour (0-23)</Text>
              <TextInput
                style={styles.input}
                value={formData.end_hour}
                onChangeText={(text) => setFormData({ ...formData, end_hour: text })}
                placeholder="17"
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
                placeholder="5"
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
        <Text style={styles.sectionTitle}>Faculty Priority Rules ({facultyRules.length})</Text>
        {loading ? (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color="#10B981" />
          </View>
        ) : (
          facultyRules.map((rule) => (
            <View key={rule.id} style={styles.ruleCard}>
              <View style={styles.ruleHeader}>
                <View style={styles.facultyIconContainer}>
                  <Text style={styles.facultyIcon}>👨‍🏫</Text>
                  <Text style={styles.ruleType}>Faculty Priority</Text>
                </View>
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
                {rule.rule_config.faculty_priority_hours && (
                  <Text style={styles.ruleDetail}>
                    Hours: {rule.rule_config.faculty_priority_hours.start}:00 - {rule.rule_config.faculty_priority_hours.end}:00
                  </Text>
                )}
                <Text style={styles.ruleDetail}>Priority: {rule.priority}</Text>
              </View>

              <View style={styles.noteBox}>
                <Text style={styles.noteText}>
                  During these hours, only faculty members can book slots
                </Text>
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
  infoBox: {
    backgroundColor: '#DBEAFE',
    borderRadius: 12,
    padding: 16,
    margin: 16,
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  infoIcon: {
    fontSize: 20,
    marginRight: 12,
  },
  infoText: {
    flex: 1,
    fontSize: 14,
    color: '#1E40AF',
    lineHeight: 20,
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
  facultyIconContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  facultyIcon: {
    fontSize: 20,
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
  noteBox: {
    backgroundColor: '#FEF3C7',
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
  },
  noteText: {
    fontSize: 13,
    color: '#92400E',
    lineHeight: 18,
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
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
import { useAuth } from '../../context/AuthContext';
import { slotApi } from '../../services/slotApi';

export default function SlotConfigurationScreen({ navigation }: any) {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    start_time: '09:00',
    end_time: '10:00',
    max_orders: '10',
  });

  const handleCreateSlot = async () => {
    if (!formData.start_time || !formData.end_time || !formData.max_orders) {
      Alert.alert('Error', 'Please fill all fields');
      return;
    }

    const maxOrders = parseInt(formData.max_orders);
    if (isNaN(maxOrders) || maxOrders <= 0) {
      Alert.alert('Error', 'Max orders must be a positive number');
      return;
    }

    try {
      setLoading(true);
      const today = new Date();
      const [startHours, startMinutes] = formData.start_time.split(':').map(Number);
      const [endHours, endMinutes] = formData.end_time.split(':').map(Number);

      const startTime = new Date(today);
      startTime.setHours(startHours, startMinutes, 0, 0);

      const endTime = new Date(today);
      endTime.setHours(endHours, endMinutes, 0, 0);

      if (endTime <= startTime) {
        Alert.alert('Error', 'End time must be after start time');
        return;
      }

      await slotApi.createSlot({
        start_time: startTime.toISOString(),
        end_time: endTime.toISOString(),
        max_orders: maxOrders,
      });

      Alert.alert('Success', 'Slot created successfully', [
        { text: 'OK', onPress: () => navigation.goBack() }
      ]);
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Failed to create slot');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Create Slot</Text>
      </View>

      <View style={styles.form}>
        <View style={styles.formGroup}>
          <Text style={styles.label}>Start Time</Text>
          <TextInput
            style={styles.input}
            value={formData.start_time}
            onChangeText={(text) => setFormData({ ...formData, start_time: text })}
            placeholder="09:00"
            placeholderTextColor="#9CA3AF"
          />
        </View>

        <View style={styles.formGroup}>
          <Text style={styles.label}>End Time</Text>
          <TextInput
            style={styles.input}
            value={formData.end_time}
            onChangeText={(text) => setFormData({ ...formData, end_time: text })}
            placeholder="10:00"
            placeholderTextColor="#9CA3AF"
          />
        </View>

        <View style={styles.formGroup}>
          <Text style={styles.label}>Max Orders</Text>
          <TextInput
            style={styles.input}
            value={formData.max_orders}
            onChangeText={(text) => setFormData({ ...formData, max_orders: text })}
            placeholder="10"
            placeholderTextColor="#9CA3AF"
            keyboardType="numeric"
          />
        </View>

        <TouchableOpacity
          style={[styles.submitButton, loading && styles.submitButtonDisabled]}
          onPress={handleCreateSlot}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="white" />
          ) : (
            <Text style={styles.submitButtonText}>Create Slot</Text>
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
  },
  form: {
    padding: 16,
  },
  formGroup: {
    marginBottom: 20,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 8,
  },
  input: {
    backgroundColor: 'white',
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
    marginTop: 20,
  },
  submitButtonDisabled: {
    backgroundColor: '#9CA3AF',
  },
  submitButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
});
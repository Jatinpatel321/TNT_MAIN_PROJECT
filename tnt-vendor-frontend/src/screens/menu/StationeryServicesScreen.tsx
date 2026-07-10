import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  TextInput,
  ActivityIndicator,
  Alert,
  Modal,
  ScrollView,
} from 'react-native';
import { colors, spacing, borderRadius, shadows } from '../../design-system';
import GlassCard from '../../design-system/components/GlassCard';
import StatusPill from '../../design-system/components/StatusPill';
import apiClient from '../../services/apiClient';
import { useAuth } from '../../context/AuthContext';
import { formatRupees } from '../../utils/format';

interface StationeryService {
  id: number;
  service_type: 'xerox' | 'color_print' | 'bw_print';
  name: string;
  description?: string;
  price_per_page: number;
  max_capacity: number;
  current_load: number;
  is_available: boolean;
}

export default function StationeryServicesScreen({ navigation }: any) {
  const { user } = useAuth();
  // stationery_services.vendor_id is a FK to users.id — use the owner's user id,
  // not the business vendors.vendor_id (overlapping id spaces).
  const vendorId = user?.owner_id;

  const [services, setServices] = useState<StationeryService[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isModalVisible, setIsModalVisible] = useState(false);

  // Form states
  const [editingService, setEditingService] = useState<StationeryService | null>(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [price, setPrice] = useState('');
  const [maxCapacity, setMaxCapacity] = useState('');
  const [serviceType, setServiceType] = useState<'xerox' | 'color_print' | 'bw_print'>('xerox');

  useEffect(() => {
    fetchServices();
  }, []);

  const fetchServices = async () => {
    if (!vendorId) return;
    setIsLoading(true);
    try {
      const res = await apiClient.get(`/v1/menu/stationery?vendor_id=${vendorId}`);
      // Backend returns PaginatedResponse: { items: [], total: int, ... }
      setServices(res.data.items || []);
    } catch (err: any) {
      console.error(err);
      Alert.alert('Error', 'Failed to load stationery services.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleOpenAdd = () => {
    setEditingService(null);
    setName('');
    setDescription('');
    setPrice('');
    setMaxCapacity('');
    setServiceType('xerox');
    setIsModalVisible(true);
  };

  const handleOpenEdit = (service: StationeryService) => {
    setEditingService(service);
    setName(service.name);
    setDescription(service.description || '');
    setPrice(service.price_per_page.toString());
    setMaxCapacity(service.max_capacity?.toString() || '');
    setServiceType(service.service_type);
    setIsModalVisible(true);
  };

  const handleSave = async () => {
    if (!name.trim()) {
      Alert.alert('Validation Error', 'Service name is required.');
      return;
    }
    const priceVal = parseFloat(price);
    if (isNaN(priceVal) || priceVal <= 0) {
      Alert.alert('Validation Error', 'Price per page must be a positive number.');
      return;
    }
    const capVal = maxCapacity ? parseInt(maxCapacity, 10) : null;

    try {
      const formData = new FormData();
      formData.append('name', name.trim());
      formData.append('description', description.trim());
      formData.append('price_per_page', priceVal.toString());
      if (capVal !== null) {
        formData.append('max_capacity', capVal.toString());
      }
      formData.append('service_type', serviceType);

      if (editingService) {
        await apiClient.put(`/v1/menu/stationery/${editingService.id}`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
      } else {
        await apiClient.post(`/v1/menu/stationery`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
      }

      setIsModalVisible(false);
      fetchServices();
      Alert.alert('Success', `Service saved successfully!`);
    } catch (err: any) {
      console.error(err);
      Alert.alert('Error', err.response?.data?.detail || 'Failed to save service.');
    }
  };

  const handleDelete = async (id: number) => {
    Alert.alert(
      'Confirm Delete',
      'Are you sure you want to delete this service?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await apiClient.delete(`/v1/menu/stationery/${id}`);
              fetchServices();
            } catch (err) {
              Alert.alert('Error', 'Failed to delete service.');
            }
          },
        },
      ]
    );
  };

  const handleToggleAvailability = async (service: StationeryService) => {
    try {
      const formData = new FormData();
      formData.append('is_available', (!service.is_available).toString());
      await apiClient.put(`/v1/menu/stationery/${service.id}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      fetchServices();
    } catch (err) {
      Alert.alert('Error', 'Failed to toggle availability.');
    }
  };

  const renderServiceCard = ({ item }: { item: StationeryService }) => {
    const usage = item.max_capacity ? item.current_load / item.max_capacity : 0;
    const usagePercentage = Math.round(usage * 100);

    return (
      <GlassCard padding={16} borderRadius={18} style={styles.card}>
        <View style={styles.cardHeader}>
          <View>
            <Text style={styles.cardTitle}>{item.name}</Text>
            <Text style={styles.cardSub}>{item.service_type.toUpperCase()}</Text>
          </View>
          <TouchableOpacity onPress={() => handleToggleAvailability(item)}>
            <StatusPill
              label={item.is_available ? 'Available' : 'Unavailable'}
              variant={item.is_available ? 'success' : 'error'}
              size="sm"
            />
          </TouchableOpacity>
        </View>

        <Text style={styles.description} numberOfLines={2}>
          {item.description || 'No description provided.'}
        </Text>

        <View style={styles.metaRow}>
          <Text style={styles.price}>{formatRupees(item.price_per_page)}/page</Text>
          <View style={styles.capacityRow}>
            <Text style={styles.capacityText}>
              Load: {item.current_load}/{item.max_capacity || '∞'}
            </Text>
          </View>
        </View>

        {/* Capacity utilization indicator */}
        {item.max_capacity > 0 && (
          <View style={styles.progressContainer}>
            <View style={styles.progressBar}>
              <View
                style={[
                  styles.progressFill,
                  {
                    width: `${Math.min(usagePercentage, 100)}%`,
                    backgroundColor: usagePercentage > 80 ? colors.error : colors.primary,
                  },
                ]}
              />
            </View>
            <Text style={styles.progressLabel}>{usagePercentage}% load capacity</Text>
          </View>
        )}

        {/* Action Row */}
        <View style={styles.actionRow}>
          <TouchableOpacity style={styles.editButton} onPress={() => handleOpenEdit(item)}>
            <Text style={styles.editButtonText}>Edit Parameters</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.deleteButton} onPress={() => handleDelete(item.id)}>
            <Text style={styles.deleteButtonText}>Delete</Text>
          </TouchableOpacity>
        </View>
      </GlassCard>
    );
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Stationery Services</Text>
        <TouchableOpacity style={styles.addButton} onPress={handleOpenAdd}>
          <Text style={styles.addButtonText}>+ Add Service</Text>
        </TouchableOpacity>
      </View>

      {isLoading && services.length === 0 ? (
        <ActivityIndicator color={colors.primary} size="large" style={{ marginTop: 40 }} />
      ) : (
        <FlatList
          data={services}
          keyExtractor={(item) => item.id.toString()}
          renderItem={renderServiceCard}
          contentContainerStyle={styles.list}
          refreshing={isLoading}
          onRefresh={fetchServices}
          ListEmptyComponent={
            <View style={styles.emptyState}>
              <Text style={styles.emptyText}>No stationery services added yet.</Text>
            </View>
          }
        />
      )}

      {/* Add / Edit Modal */}
      <Modal visible={isModalVisible} animationType="slide" transparent>
        <View style={styles.modalBg}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>
              {editingService ? 'Edit Service' : 'Add Service'}
            </Text>

            <ScrollView contentContainerStyle={styles.modalForm}>
              <View style={styles.formGroup}>
                <Text style={styles.modalLabel}>Service Type</Text>
                <View style={styles.typeRow}>
                  {(['xerox', 'color_print', 'bw_print'] as const).map((type) => (
                    <TouchableOpacity
                      key={type}
                      style={[styles.typeChip, serviceType === type && styles.typeChipActive]}
                      onPress={() => setServiceType(type)}
                    >
                      <Text style={[styles.typeChipText, serviceType === type && styles.typeChipTextActive]}>
                        {type.replace('_', ' ').toUpperCase()}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </View>

              <View style={styles.formGroup}>
                <Text style={styles.modalLabel}>Name *</Text>
                <TextInput
                  style={styles.modalInput}
                  placeholder="e.g. Standard Color Photocopy"
                  placeholderTextColor={colors.textMuted}
                  value={name}
                  onChangeText={setName}
                />
              </View>

              <View style={styles.formGroup}>
                <Text style={styles.modalLabel}>Description</Text>
                <TextInput
                  style={styles.modalInput}
                  placeholder="e.g. Single sided, high quality printout"
                  placeholderTextColor={colors.textMuted}
                  value={description}
                  onChangeText={setDescription}
                />
              </View>

              <View style={styles.formGroup}>
                <Text style={styles.modalLabel}>Price per Page (₹) *</Text>
                <TextInput
                  style={styles.modalInput}
                  placeholder="e.g. 5"
                  placeholderTextColor={colors.textMuted}
                  keyboardType="numeric"
                  value={price}
                  onChangeText={setPrice}
                />
              </View>

              <View style={styles.formGroup}>
                <Text style={styles.modalLabel}>Max Capacity (Pages/hr)</Text>
                <TextInput
                  style={styles.modalInput}
                  placeholder="e.g. 200 (Leave blank for unlimited)"
                  placeholderTextColor={colors.textMuted}
                  keyboardType="numeric"
                  value={maxCapacity}
                  onChangeText={setMaxCapacity}
                />
              </View>

              <View style={styles.modalActions}>
                <TouchableOpacity
                  style={[styles.modalBtn, styles.modalBtnCancel]}
                  onPress={() => setIsModalVisible(false)}
                >
                  <Text style={styles.modalBtnCancelText}>Cancel</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.modalBtn, styles.modalBtnSave]}
                  onPress={handleSave}
                >
                  <Text style={styles.modalBtnSaveText}>Save</Text>
                </TouchableOpacity>
              </View>
            </ScrollView>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: spacing.lg,
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    color: colors.textPrimary,
  },
  addButton: {
    backgroundColor: colors.primary,
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: borderRadius.md,
  },
  addButtonText: {
    color: colors.textInverse,
    fontWeight: '600',
    fontSize: 14,
  },
  list: {
    padding: spacing.lg,
    gap: spacing.md,
  },
  card: {
    marginBottom: spacing.sm,
    backgroundColor: colors.bgCard,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: colors.textPrimary,
  },
  cardSub: {
    fontSize: 11,
    color: colors.textMuted,
    marginTop: 2,
    fontWeight: '600',
  },
  description: {
    fontSize: 13,
    color: colors.textSecondary,
    marginTop: spacing.sm,
    lineHeight: 18,
  },
  metaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: spacing.md,
  },
  price: {
    fontSize: 16,
    fontWeight: '700',
    color: colors.success,
  },
  capacityRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  capacityText: {
    fontSize: 13,
    color: colors.textSecondary,
    fontWeight: '600',
  },
  progressContainer: {
    marginTop: spacing.sm,
  },
  progressBar: {
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.bgSecondary,
    width: '100%',
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
  },
  progressLabel: {
    fontSize: 11,
    color: colors.textMuted,
    marginTop: 4,
    textAlign: 'right',
  },
  actionRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginTop: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    paddingTop: spacing.md,
  },
  editButton: {
    flex: 1,
    paddingVertical: 10,
    backgroundColor: colors.primaryPale,
    borderRadius: borderRadius.sm,
    alignItems: 'center',
  },
  editButtonText: {
    color: colors.primary,
    fontWeight: '600',
    fontSize: 13,
  },
  deleteButton: {
    paddingVertical: 10,
    paddingHorizontal: 16,
    backgroundColor: colors.errorPale,
    borderRadius: borderRadius.sm,
    alignItems: 'center',
  },
  deleteButtonText: {
    color: colors.error,
    fontWeight: '600',
    fontSize: 13,
  },
  emptyState: {
    paddingVertical: 60,
    alignItems: 'center',
  },
  emptyText: {
    color: colors.textMuted,
    fontSize: 14,
  },
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
    maxHeight: '80%',
    ...shadows.lg,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: colors.textPrimary,
    marginBottom: spacing.md,
  },
  modalForm: {
    gap: spacing.md,
  },
  formGroup: {
    gap: spacing.xs,
  },
  modalLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: colors.textSecondary,
  },
  typeRow: {
    flexDirection: 'row',
    gap: spacing.xs,
  },
  typeChip: {
    flex: 1,
    paddingVertical: 8,
    borderRadius: borderRadius.md,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    backgroundColor: colors.bgSecondary,
  },
  typeChipActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  typeChipText: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.textSecondary,
  },
  typeChipTextActive: {
    color: colors.textInverse,
  },
  modalInput: {
    backgroundColor: colors.bgSecondary,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: borderRadius.md,
    padding: spacing.md,
    color: colors.textPrimary,
    fontSize: 14,
  },
  modalActions: {
    flexDirection: 'row',
    gap: spacing.md,
    marginTop: spacing.md,
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

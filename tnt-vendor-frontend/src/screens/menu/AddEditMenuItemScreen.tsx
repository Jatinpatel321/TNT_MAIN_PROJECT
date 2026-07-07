import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { colors as staticColors, spacing, borderRadius, shadows } from '../../design-system';
const colors = staticColors;
import ImagePicker from '../../components/ImagePicker';
import apiClient from '../../services/apiClient';
import { useTheme } from '../../context/ThemeContext';

export default function AddEditMenuItemScreen({ route, navigation }: any) {
  const { colors: themeColors } = useTheme();
  const item = route.params?.item;

  const isEdit = !!item;

  const [name, setName] = useState(item?.name || '');
  const [price, setPrice] = useState(item?.price !== undefined ? item.price.toString() : '');
  const [description, setDescription] = useState(item?.description || '');
  const [category, setCategory] = useState(item?.category || 'food');
  const [prepTime, setPrepTime] = useState(item?.prep_time_minutes?.toString() || '');
  const [quantity, setQuantity] = useState(item?.available_quantity?.toString() || '');
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSave = async () => {
    if (!name.trim()) {
      Alert.alert('Validation Error', 'Item name is required.');
      return;
    }
    const priceNum = parseFloat(price);
    if (isNaN(priceNum) || priceNum <= 0) {
      Alert.alert('Validation Error', 'Please enter a valid positive price.');
      return;
    }
    setIsLoading(true);
    try {
      const formData = new FormData();
      formData.append('name', name.trim());
      formData.append('price', priceNum.toString());
      formData.append('description', description.trim());
      formData.append('category', category);
      
      if (prepTime) {
        formData.append('prep_time_minutes', parseInt(prepTime, 10).toString());
      }
      if (quantity) {
        formData.append('available_quantity', parseInt(quantity, 10).toString());
      }
      if (imageUri) {
        formData.append('image', {
          uri: imageUri,
          type: 'image/jpeg',
          name: 'menu_item.jpg',
        } as any);
      }

      if (isEdit) {
        await apiClient.put(`/v1/menu/items/${item.id}`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
      } else {
        await apiClient.post(`/v1/menu/items`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
      }

      Alert.alert('Success', `Menu item ${isEdit ? 'updated' : 'created'} successfully!`);
      if (route.params?.onRefresh) {
        route.params.onRefresh();
      }
      navigation.goBack();
    } catch (err: any) {
      console.error(err);
      Alert.alert('Error', err.response?.data?.detail || 'Failed to save menu item.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <ScrollView style={[styles.container, { backgroundColor: themeColors.bg }]} contentContainerStyle={styles.content}>
      <Text style={[styles.title, { color: themeColors.textPrimary }]}>{isEdit ? 'Edit Menu Item' : 'New Menu Item'}</Text>

      {/* Image Section */}
      <View style={styles.imageSection}>
        <Text style={[styles.label, { color: themeColors.textSecondary }]}>Item Image</Text>
        <ImagePicker onImageSelected={setImageUri} />
        {imageUri && (
          <Text style={[styles.imageSelectedText, { color: themeColors.textSecondary }]} numberOfLines={1}>
            Selected: {imageUri.substring(imageUri.lastIndexOf('/') + 1)}
          </Text>
        )}
      </View>

      {/* Basic Info */}
      <View style={styles.fieldGroup}>
        <Text style={[styles.label, { color: themeColors.textSecondary }]}>Name *</Text>
        <TextInput
          style={[styles.input, { backgroundColor: themeColors.bgCard, color: themeColors.textPrimary, borderColor: themeColors.border }]}
          placeholder="e.g. Masala Dosa"
          placeholderTextColor={themeColors.textMuted}
          value={name}
          onChangeText={setName}
        />
      </View>

      <View style={styles.fieldGroup}>
        <Text style={[styles.label, { color: themeColors.textSecondary }]}>Price (₹) *</Text>
        <TextInput
          style={[styles.input, { backgroundColor: themeColors.bgCard, color: themeColors.textPrimary, borderColor: themeColors.border }]}
          placeholder="e.g. 80"
          placeholderTextColor={themeColors.textMuted}
          keyboardType="numeric"
          value={price}
          onChangeText={setPrice}
        />
      </View>

      <View style={styles.fieldGroup}>
        <Text style={[styles.label, { color: themeColors.textSecondary }]}>Description</Text>
        <TextInput
          style={[styles.input, styles.multilineInput, { backgroundColor: themeColors.bgCard, color: themeColors.textPrimary, borderColor: themeColors.border }]}
          placeholder="Describe the taste, ingredients, or size..."
          placeholderTextColor={themeColors.textMuted}
          multiline
          numberOfLines={3}
          value={description}
          onChangeText={setDescription}
        />
      </View>

      {/* Category Chips */}
      <View style={styles.fieldGroup}>
        <Text style={[styles.label, { color: themeColors.textSecondary }]}>Category</Text>
        <View style={styles.chipRow}>
          <TouchableOpacity
            style={[
              styles.chip,
              { backgroundColor: themeColors.bgCard, borderColor: themeColors.border },
              category === 'food' && [styles.chipActive, { backgroundColor: themeColors.primary, borderColor: themeColors.primary }]
            ]}
            onPress={() => setCategory('food')}
          >
            <Text style={[
              styles.chipText,
              { color: themeColors.textSecondary },
              category === 'food' && [styles.chipTextActive, { color: themeColors.textInverse }]
            ]}>
              Food
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[
              styles.chip,
              { backgroundColor: themeColors.bgCard, borderColor: themeColors.border },
              category === 'stationery' && [styles.chipActive, { backgroundColor: themeColors.primary, borderColor: themeColors.primary }]
            ]}
            onPress={() => setCategory('stationery')}
          >
            <Text style={[
              styles.chipText,
              { color: themeColors.textSecondary },
              category === 'stationery' && [styles.chipTextActive, { color: themeColors.textInverse }]
            ]}>
              Stationery
            </Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Extra settings based on category */}
      {category === 'food' ? (
        <View style={styles.fieldGroup}>
          <Text style={[styles.label, { color: themeColors.textSecondary }]}>Prep Time (Minutes)</Text>
          <TextInput
            style={[styles.input, { backgroundColor: themeColors.bgCard, color: themeColors.textPrimary, borderColor: themeColors.border }]}
            placeholder="e.g. 15"
            placeholderTextColor={themeColors.textMuted}
            keyboardType="numeric"
            value={prepTime}
            onChangeText={setPrepTime}
          />
        </View>
      ) : (
        <View style={styles.fieldGroup}>
          <Text style={[styles.label, { color: themeColors.textSecondary }]}>Available Quantity</Text>
          <TextInput
            style={[styles.input, { backgroundColor: themeColors.bgCard, color: themeColors.textPrimary, borderColor: themeColors.border }]}
            placeholder="e.g. 50"
            placeholderTextColor={themeColors.textMuted}
            keyboardType="numeric"
            value={quantity}
            onChangeText={setQuantity}
          />
        </View>
      )}

      {/* Save Button */}
      <TouchableOpacity
        style={[styles.saveButton, { backgroundColor: themeColors.primary }, isLoading && styles.saveButtonDisabled]}
        onPress={handleSave}
        disabled={isLoading}
      >
        {isLoading ? (
          <ActivityIndicator color={themeColors.textInverse} size="small" />
        ) : (
          <Text style={[styles.saveButtonText, { color: themeColors.textInverse }]}>Save Item</Text>
        )}
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  content: {
    padding: spacing.lg,
    paddingBottom: spacing.huge,
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    color: colors.textPrimary,
    marginBottom: spacing.lg,
  },
  imageSection: {
    marginBottom: spacing.lg,
    alignItems: 'center',
    width: '100%',
  },
  imageSelectedText: {
    marginTop: spacing.xs,
    fontSize: 12,
    color: colors.textSecondary,
  },
  fieldGroup: {
    marginBottom: spacing.md,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.textSecondary,
    marginBottom: spacing.xs,
  },
  input: {
    backgroundColor: colors.bgCard,
    borderRadius: borderRadius.md,
    padding: spacing.md,
    fontSize: 15,
    color: colors.textPrimary,
    borderWidth: 1,
    borderColor: colors.border,
  },
  multilineInput: {
    height: 80,
    textAlignVertical: 'top',
  },
  chipRow: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  chip: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: borderRadius.lg,
    backgroundColor: colors.bgCard,
    borderWidth: 1.5,
    borderColor: colors.border,
  },
  chipActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  chipText: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.textSecondary,
  },
  chipTextActive: {
    color: colors.textInverse,
  },
  saveButton: {
    backgroundColor: colors.primary,
    paddingVertical: 16,
    borderRadius: borderRadius.md,
    alignItems: 'center',
    marginTop: spacing.lg,
    ...shadows.md,
  },
  saveButtonDisabled: {
    opacity: 0.8,
  },
  saveButtonText: {
    color: colors.textInverse,
    fontWeight: '700',
    fontSize: 16,
  },
});

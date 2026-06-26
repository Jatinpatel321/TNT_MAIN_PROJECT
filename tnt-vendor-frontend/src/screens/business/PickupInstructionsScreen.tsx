import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  TextInput,
} from 'react-native';
import { businessSettingsApi } from '../../services/businessSettingsApi';

export default function PickupInstructionsScreen({ navigation }: any) {
  const [instructions, setInstructions] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadInstructions();
  }, []);

  const loadInstructions = async () => {
    try {
      setLoading(true);
      const response = await businessSettingsApi.getSettings();
      setInstructions(response.data.pickup_instructions || '');
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Failed to load pickup instructions');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await businessSettingsApi.updatePickupInstructions(instructions);
      Alert.alert('Success', 'Pickup instructions updated successfully');
      navigation.goBack();
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Failed to save pickup instructions');
    } finally {
      setSaving(false);
    }
  };

  const insertFormatting = (before: string, after: string = '') => {
    const textInput = instructions;
    setInstructions(before + textInput + after);
  };

  if (loading) {
    return (
      <View style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Pickup Instructions</Text>
        </View>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#10B981" />
          <Text style={styles.loadingText}>Loading instructions...</Text>
        </View>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Pickup Instructions</Text>
        <Text style={styles.headerSubtitle}>
          Provide clear instructions for customers picking up orders
        </Text>
      </View>

      <View style={styles.content}>
        {/* Rich Text Toolbar */}
        <View style={styles.toolbar}>
          <TouchableOpacity
            style={styles.toolbarButton}
            onPress={() => insertFormatting('**', '**')}
          >
            <Text style={styles.toolbarButtonText}>B</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.toolbarButton}
            onPress={() => insertFormatting('*', '*')}
          >
            <Text style={styles.toolbarButtonText}>I</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.toolbarButton}
            onPress={() => insertFormatting('\n• ')}
          >
            <Text style={styles.toolbarButtonText}>• List</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.toolbarButton}
            onPress={() => insertFormatting('\n1. ')}
          >
            <Text style={styles.toolbarButtonText}>1. List</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.toolbarButton}
            onPress={() => insertFormatting('\n---\n')}
          >
            <Text style={styles.toolbarButtonText}>— Line</Text>
          </TouchableOpacity>
        </View>

        {/* Instructions Editor */}
        <View style={styles.editorContainer}>
          <Text style={styles.editorLabel}>Instructions (Markdown supported)</Text>
          <TextInput
            style={styles.editor}
            value={instructions}
            onChangeText={setInstructions}
            placeholder="Enter pickup instructions here...

Example:
**Pickup Location:**
Ground Floor, Shop #5

**Hours:**
Mon-Sat: 9:00 AM - 6:00 PM
Sun: Closed

**Instructions:**
• Please bring your order confirmation
• Call us if you can't find the location
• Free parking available"
            placeholderTextColor="#9CA3AF"
            multiline
            numberOfLines={20}
            textAlignVertical="top"
          />
        </View>

        {/* Preview Section */}
        {instructions ? (
          <View style={styles.previewContainer}>
            <Text style={styles.previewLabel}>Preview:</Text>
            <View style={styles.preview}>
              <Text style={styles.previewText}>{instructions}</Text>
            </View>
          </View>
        ) : null}

        {/* Save Button */}
        <TouchableOpacity
          style={[styles.saveButton, saving && styles.saveButtonDisabled]}
          onPress={handleSave}
          disabled={saving}
        >
          {saving ? (
            <ActivityIndicator color="white" />
          ) : (
            <Text style={styles.saveButtonText}>Save Instructions</Text>
          )}
        </TouchableOpacity>

        {/* Help Text */}
        <View style={styles.helpContainer}>
          <Text style={styles.helpIcon}>💡</Text>
          <Text style={styles.helpText}>
            Use Markdown formatting for better readability:
            {'\n'}- **bold** for emphasis
            {'\n'}- *italic* for highlights
            {'\n'}- • for bullet points
            {'\n'}- 1. for numbered lists
          </Text>
        </View>
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
  toolbar: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 16,
    padding: 12,
    backgroundColor: 'white',
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  toolbarButton: {
    backgroundColor: '#F3F4F6',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#D1D5DB',
  },
  toolbarButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
  },
  editorContainer: {
    marginBottom: 20,
  },
  editorLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 8,
  },
  editor: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    fontSize: 16,
    borderWidth: 1,
    borderColor: '#D1D5DB',
    color: '#111827',
    minHeight: 300,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  previewContainer: {
    marginBottom: 20,
  },
  previewLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 8,
  },
  preview: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#D1D5DB',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  previewText: {
    fontSize: 14,
    color: '#374151',
    lineHeight: 20,
  },
  saveButton: {
    backgroundColor: '#10B981',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    marginBottom: 16,
  },
  saveButtonDisabled: {
    backgroundColor: '#9CA3AF',
  },
  saveButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  helpContainer: {
    backgroundColor: '#DBEAFE',
    borderRadius: 12,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 40,
  },
  helpIcon: {
    fontSize: 20,
    marginRight: 12,
  },
  helpText: {
    flex: 1,
    fontSize: 14,
    color: '#1E40AF',
    lineHeight: 20,
  },
});
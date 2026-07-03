// ─── Premium Pickup Instructions Screen ─────────────────────────
// Edit pickup instructions with premium design system

import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  Animated,
} from 'react-native';
import { businessSettingsApi } from '../../services/businessSettingsApi';
import { colors, spacing } from '../../design-system';
import GlassCard from '../../design-system/components/GlassCard';
import Button from '../../design-system/components/Button';

export default function PickupInstructionsScreen({ navigation }: any) {
  const [instructions, setInstructions] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }).start();
    (async () => {
      try {
        setLoading(true);
        const response = await businessSettingsApi.getSettings();
        setInstructions(response.data.pickup_instructions || '');
      } catch (err: any) { Alert.alert('Error', err.message || 'Failed to load'); }
      finally { setLoading(false); }
    })();
  }, []);

  const handleSave = async () => {
    try {
      setSaving(true);
      await businessSettingsApi.updatePickupInstructions(instructions);
      Alert.alert('Success', 'Instructions updated', [{ text: 'OK', onPress: () => navigation.goBack() }]);
    } catch (err: any) { Alert.alert('Error', err.message || 'Failed to save'); }
    finally { setSaving(false); }
  };

  if (loading) {
    return (
      <View style={[styles.container, styles.centered]}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading instructions...</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      <View style={styles.header}>
        <View style={styles.headerDeco1} /><View style={styles.headerDeco2} />
        <Text style={styles.headerTitle}>Pickup Instructions</Text>
        <Text style={styles.headerSubtitle}>Guide customers to find your store</Text>
      </View>

      <Animated.View style={{ opacity: fadeAnim }}>
        <View style={styles.content}>
          {/* Toolbar */}
          <GlassCard padding={12} borderRadius={16} style={{ marginBottom: spacing.sm }}>
            <View style={styles.toolbar}>
              {[
                { label: 'B', action: () => setInstructions(prev => `**${prev}**`) },
                { label: 'I', action: () => setInstructions(prev => `*${prev}*`) },
                { label: '•', action: () => setInstructions(prev => `${prev}\n• `) },
                { label: '1.', action: () => setInstructions(prev => `${prev}\n1. `) },
                { label: '—', action: () => setInstructions(prev => `${prev}\n---\n`) },
              ].map((btn, i) => (
                <TouchableOpacity key={i} style={styles.toolBtn} onPress={btn.action}>
                  <Text style={styles.toolBtnText}>{btn.label}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </GlassCard>

          {/* Editor */}
          <Text style={styles.editorLabel}>Instructions (Markdown supported)</Text>
          <GlassCard padding={4} borderRadius={16} style={{ marginBottom: spacing.md }}>
            <TextInput
              style={styles.editor}
              value={instructions}
              onChangeText={setInstructions}
              placeholder="Enter pickup instructions here..."
              placeholderTextColor={colors.textMuted}
              multiline
              numberOfLines={15}
              textAlignVertical="top"
            />
          </GlassCard>

          {/* Preview */}
          {instructions ? (
            <GlassCard padding={16} borderRadius={16} style={{ marginBottom: spacing.md }}>
              <Text style={styles.previewLabel}>Preview:</Text>
              <Text style={styles.previewText}>{instructions}</Text>
            </GlassCard>
          ) : null}

          {/* Save */}
          <Button title="Save Instructions" onPress={handleSave} loading={saving} variant="primary" size="lg" fullWidth />

          {/* Help */}
          <GlassCard padding={16} borderRadius={16} style={{ marginTop: spacing.sm, backgroundColor: colors.infoPale }}>
            <Text style={styles.helpText}>💡 Use Markdown: **bold** *italic* • bullets 1. numbered lists</Text>
          </GlassCard>
        </View>
        <View style={{ height: spacing.huge }} />
      </Animated.View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  loadingText: { marginTop: 12, fontSize: 14, color: colors.textMuted, fontWeight: '600' },
  header: {
    backgroundColor: colors.primary, paddingTop: spacing.huge + 20, paddingBottom: spacing.xxl, paddingHorizontal: spacing.xl,
    borderBottomLeftRadius: 28, borderBottomRightRadius: 28, overflow: 'hidden',
  },
  headerDeco1: { position: 'absolute', top: -40, right: -30, width: 180, height: 180, borderRadius: 90, backgroundColor: 'rgba(255,255,255,0.08)' },
  headerDeco2: { position: 'absolute', bottom: -30, left: -60, width: 140, height: 140, borderRadius: 70, backgroundColor: 'rgba(255,255,255,0.05)' },
  headerTitle: { fontSize: 28, fontWeight: '700', color: colors.textInverse, letterSpacing: -0.3 },
  headerSubtitle: { fontSize: 14, color: 'rgba(255,255,255,0.7)', marginTop: 4, fontWeight: '500' },
  content: { padding: spacing.lg },
  toolbar: { flexDirection: 'row', gap: 8 },
  toolBtn: { backgroundColor: colors.bgSecondary, paddingHorizontal: 14, paddingVertical: 8, borderRadius: 8, borderWidth: 1, borderColor: colors.border },
  toolBtnText: { fontSize: 14, fontWeight: '600', color: colors.textPrimary },
  editorLabel: { fontSize: 14, fontWeight: '600', color: colors.textSecondary, marginBottom: 8 },
  editor: { padding: 16, fontSize: 16, color: colors.textPrimary, minHeight: 250, lineHeight: 22 },
  previewLabel: { fontSize: 12, fontWeight: '600', color: colors.textMuted, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 },
  previewText: { fontSize: 14, color: colors.textPrimary, lineHeight: 20 },
  helpText: { fontSize: 13, color: colors.info, lineHeight: 18 },
});

import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Image,
  Pressable,
  StyleSheet,
  TextInput,
  View,
} from 'react-native';
import { Text } from 'react-native-paper';
import MaterialCommunityIcons from 'react-native-vector-icons/MaterialCommunityIcons';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { launchImageLibrary } from 'react-native-image-picker';

import type { RootStackParamList } from '../../types/navigation';
import type { User } from '../../types/models';
import { Screen } from '../../components/Screen';
import { GradientButton } from '../../components/GradientButton';
import {
  getProfile,
  updateProfile,
  uploadProfileImage,
} from '../../services/profileService';
import { toApiError } from '../../services/apiClient';
import { useAuth } from '../../hooks/useAuth';
import { API_BASE_URL } from '../../constants/api';

type Props = NativeStackScreenProps<RootStackParamList, 'EditProfile'>;

const DEPARTMENTS = [
  'Computer Science',
  'Electronics',
  'Mechanical',
  'Civil',
  'Electrical',
  'Chemical',
  'Biotechnology',
  'Information Technology',
  'Physics',
  'Mathematics',
  'Other',
];

export function EditProfileScreen({ navigation }: Props) {
  const { user, setSession, accessToken } = useAuth();
  const [profile, setProfile] = useState<User | null>(null);
  const [fullName, setFullName] = useState('');
  const [universityId, setUniversityId] = useState('');
  const [department, setDepartment] = useState('');
  const [semester, setSemester] = useState('');
  const [showDeptPicker, setShowDeptPicker] = useState(false);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const p = await getProfile();
        setProfile(p);
        setFullName(p.full_name ?? p.name ?? '');
        setUniversityId(p.university_id ?? '');
        setDepartment(p.department ?? '');
        setSemester(p.semester != null ? String(p.semester) : '');
      } catch (e) {
        Alert.alert('Error', toApiError(e).message);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const profileImageUrl = profile?.profile_image
    ? `${API_BASE_URL}${profile.profile_image}`
    : null;

  const handleImagePick = async () => {
    try {
      const result = await launchImageLibrary({
        mediaType: 'photo',
        quality: 0.8,
        maxWidth: 512,
        maxHeight: 512,
      });

      if (result.didCancel || !result.assets?.length) return;

      const asset = result.assets[0];
      if (!asset.uri || !asset.fileName) return;

      setUploading(true);
      const mimeType = asset.type ?? 'image/jpeg';
      const res = await uploadProfileImage(asset.uri, asset.fileName, mimeType);
      setProfile((prev) => (prev ? { ...prev, profile_image: res.profile_image } : prev));

      // Update auth context with new profile image
      if (accessToken && profile) {
        setSession(accessToken, { ...profile, profile_image: res.profile_image });
      }
    } catch (e) {
      Alert.alert('Upload Failed', toApiError(e).message);
    } finally {
      setUploading(false);
    }
  };

  const handleSave = async () => {
    const trimmedName = fullName.trim();
    if (!trimmedName) {
      Alert.alert('Validation', 'Full name is required.');
      return;
    }

    const payload: Record<string, any> = { full_name: trimmedName };
    if (universityId.trim()) payload.university_id = universityId.trim();
    if (department.trim()) payload.department = department.trim();
    if (semester.trim()) {
      const sem = parseInt(semester, 10);
      if (isNaN(sem) || sem < 1 || sem > 12) {
        Alert.alert('Validation', 'Semester must be between 1 and 12.');
        return;
      }
      payload.semester = sem;
    }

    setSaving(true);
    try {
      const updated = await updateProfile(payload);
      setProfile(updated);

      // Update auth context
      if (accessToken) {
        setSession(accessToken, updated);
      }

      Alert.alert('Success', 'Profile updated successfully.', [
        { text: 'OK', onPress: () => navigation.goBack() },
      ]);
    } catch (e) {
      Alert.alert('Update Failed', toApiError(e).message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Screen>
        <View style={styles.center}>
          <ActivityIndicator size="large" />
        </View>
      </Screen>
    );
  }

  return (
    <Screen scroll>
      <View style={styles.header}>
        <Pressable onPress={() => navigation.goBack()} hitSlop={8}>
          <MaterialCommunityIcons name="arrow-left" size={24} color="#111827" />
        </Pressable>
        <Text style={styles.title}>Edit Profile</Text>
        <View style={{ width: 24 }} />
      </View>

      {/* Avatar Section */}
      <View style={styles.avatarSection}>
        <Pressable onPress={handleImagePick} disabled={uploading}>
          <View style={styles.avatarContainer}>
            {profileImageUrl ? (
              <Image source={{ uri: profileImageUrl }} style={styles.avatarImage} />
            ) : (
              <View style={styles.avatarPlaceholder}>
                <MaterialCommunityIcons name="account" size={40} color="#6C63FF" />
              </View>
            )}
            {uploading ? (
              <View style={styles.avatarBadge}>
                <ActivityIndicator size="small" color="#FFFFFF" />
              </View>
            ) : (
              <View style={styles.avatarBadge}>
                <MaterialCommunityIcons name="camera" size={14} color="#FFFFFF" />
              </View>
            )}
          </View>
        </Pressable>
        <Text style={styles.avatarHint}>Tap to change photo</Text>
      </View>

      {/* Form Fields */}
      <View style={styles.form}>
        <View style={styles.fieldGroup}>
          <Text style={styles.label}>Full Name</Text>
          <TextInput
            style={styles.input}
            value={fullName}
            onChangeText={setFullName}
            placeholder="Enter your full name"
            placeholderTextColor="#9CA3AF"
          />
        </View>

        <View style={styles.fieldGroup}>
          <Text style={styles.label}>University ID</Text>
          <TextInput
            style={styles.input}
            value={universityId}
            onChangeText={setUniversityId}
            placeholder="e.g. 2024CSE001"
            placeholderTextColor="#9CA3AF"
            autoCapitalize="characters"
          />
        </View>

        <View style={styles.fieldGroup}>
          <Text style={styles.label}>Department</Text>
          <Pressable
            style={styles.selectField}
            onPress={() => setShowDeptPicker(!showDeptPicker)}
          >
            <Text style={department ? styles.selectText : styles.selectPlaceholder}>
              {department || 'Select department'}
            </Text>
            <MaterialCommunityIcons
              name={showDeptPicker ? 'chevron-up' : 'chevron-down'}
              size={20}
              color="#6B7280"
            />
          </Pressable>
          {showDeptPicker && (
            <View style={styles.pickerContainer}>
              {DEPARTMENTS.map((dept) => (
                <Pressable
                  key={dept}
                  style={[
                    styles.pickerItem,
                    department === dept && styles.pickerItemActive,
                  ]}
                  onPress={() => {
                    setDepartment(dept);
                    setShowDeptPicker(false);
                  }}
                >
                  <Text
                    style={[
                      styles.pickerItemText,
                      department === dept && styles.pickerItemTextActive,
                    ]}
                  >
                    {dept}
                  </Text>
                </Pressable>
              ))}
            </View>
          )}
        </View>

        <View style={styles.fieldGroup}>
          <Text style={styles.label}>Semester</Text>
          <TextInput
            style={styles.input}
            value={semester}
            onChangeText={setSemester}
            placeholder="1-12"
            placeholderTextColor="#9CA3AF"
            keyboardType="number-pad"
            maxLength={2}
          />
        </View>

        <View style={styles.fieldGroup}>
          <Text style={styles.label}>Role</Text>
          <View style={[styles.input, styles.disabledInput]}>
            <Text style={styles.disabledText}>
              {profile?.role?.charAt(0).toUpperCase() + (profile?.role?.slice(1) ?? '')}
            </Text>
          </View>
        </View>
      </View>

      <View style={styles.actions}>
        <GradientButton label={saving ? 'Saving...' : 'Save Changes'} onPress={handleSave} disabled={saving} />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 10,
  },
  title: {
    fontSize: 18,
    fontWeight: '800',
  },
  avatarSection: {
    alignItems: 'center',
    marginVertical: 16,
  },
  avatarContainer: {
    position: 'relative',
  },
  avatarImage: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: '#E5E7EB',
  },
  avatarPlaceholder: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: '#F3F2FF',
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarBadge: {
    position: 'absolute',
    bottom: 0,
    right: 0,
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#6C63FF',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: '#FFFFFF',
  },
  avatarHint: {
    marginTop: 8,
    fontSize: 13,
    color: '#6B7280',
  },
  form: {
    gap: 16,
  },
  fieldGroup: {
    gap: 6,
  },
  label: {
    fontSize: 13,
    fontWeight: '600',
    color: '#374151',
  },
  input: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 15,
    color: '#111827',
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  disabledInput: {
    backgroundColor: '#F9FAFB',
    justifyContent: 'center',
  },
  disabledText: {
    fontSize: 15,
    color: '#9CA3AF',
  },
  selectField: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  selectText: {
    fontSize: 15,
    color: '#111827',
  },
  selectPlaceholder: {
    fontSize: 15,
    color: '#9CA3AF',
  },
  pickerContainer: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    marginTop: 4,
    overflow: 'hidden',
  },
  pickerItem: {
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
  },
  pickerItemActive: {
    backgroundColor: '#F3F2FF',
  },
  pickerItemText: {
    fontSize: 14,
    color: '#374151',
  },
  pickerItemTextActive: {
    color: '#6C63FF',
    fontWeight: '600',
  },
  actions: {
    marginTop: 24,
    marginBottom: 16,
  },
});

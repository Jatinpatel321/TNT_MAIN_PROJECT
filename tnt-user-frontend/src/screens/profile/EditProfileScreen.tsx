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
import type { DietaryPreference, ResidenceType, User } from '../../types/models';
import { Screen } from '../../components/Screen';
import { GradientButton } from '../../components/GradientButton';
import {
  getPreferences,
  getProfile,
  updatePreferences,
  updateProfile,
  uploadProfileImage,
} from '../../services/profileService';
import type { ProfileUpdatePayload, UserPreferences } from '../../services/profileService';
import { toApiError } from '../../services/apiClient';
import { useAuth } from '../../hooks/useAuth';
import { useAppTheme } from '../../theme/ThemeContext';
import { API_BASE_URL } from '../../constants/api';
import { Chip } from './profileUi';

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

const DIETARY_OPTIONS: { value: DietaryPreference; label: string; icon: string }[] = [
  { value: 'vegetarian', label: 'Vegetarian', icon: 'leaf' },
  { value: 'non_vegetarian', label: 'Non-Veg', icon: 'food-drumstick' },
  { value: 'vegan', label: 'Vegan', icon: 'sprout' },
  { value: 'jain', label: 'Jain', icon: 'flower-tulip' },
  { value: 'other', label: 'Other', icon: 'silverware-fork-knife' },
];

const RESIDENCE_OPTIONS: { value: ResidenceType; label: string; icon: string }[] = [
  { value: 'hostel', label: 'Hostel', icon: 'bed' },
  { value: 'day_scholar', label: 'Day Scholar', icon: 'bus' },
];

const CATEGORY_OPTIONS: { value: string; label: string }[] = [
  { value: 'south_indian', label: 'South Indian' },
  { value: 'north_indian', label: 'North Indian' },
  { value: 'chinese', label: 'Chinese' },
  { value: 'fast_food', label: 'Fast Food' },
  { value: 'healthy', label: 'Healthy' },
  { value: 'snacks', label: 'Snacks' },
  { value: 'beverages', label: 'Beverages' },
];

export function EditProfileScreen({ navigation }: Props) {
  const { setSession, accessToken } = useAuth();
  const { colors } = useAppTheme();
  const [profile, setProfile] = useState<User | null>(null);
  const [fullName, setFullName] = useState('');
  const [universityId, setUniversityId] = useState('');
  const [department, setDepartment] = useState('');
  const [semester, setSemester] = useState('');
  const [email, setEmail] = useState('');
  const [campus, setCampus] = useState('');
  const [residence, setResidence] = useState<ResidenceType | null>(null);
  const [dietary, setDietary] = useState<DietaryPreference | null>(null);
  const [pickupLocations, setPickupLocations] = useState<string[]>([]);
  const [pickupInput, setPickupInput] = useState('');
  const [favCategories, setFavCategories] = useState<string[]>([]);
  const [showDeptPicker, setShowDeptPicker] = useState(false);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [p, prefs] = await Promise.all([
          getProfile(),
          getPreferences().catch(() => ({} as UserPreferences)),
        ]);
        setProfile(p);
        setFullName(p.full_name ?? p.name ?? '');
        setUniversityId(p.university_id ?? '');
        setDepartment(p.department ?? '');
        setSemester(p.semester != null ? String(p.semester) : '');
        setEmail(p.email ?? '');
        setCampus(p.campus ?? '');
        setResidence(p.residence_type ?? null);
        setDietary(p.dietary_preference ?? null);
        setPickupLocations(prefs.preferred_pickup_locations ?? []);
        setFavCategories(prefs.favourite_categories ?? []);
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

  const addPickupLocation = () => {
    const value = pickupInput.trim();
    if (!value) return;
    if (pickupLocations.length >= 10) {
      Alert.alert('Limit reached', 'You can save up to 10 pickup spots.');
      return;
    }
    if (!pickupLocations.some((l) => l.toLowerCase() === value.toLowerCase())) {
      setPickupLocations([...pickupLocations, value]);
    }
    setPickupInput('');
  };

  const toggleCategory = (value: string) => {
    setFavCategories((prev) =>
      prev.includes(value) ? prev.filter((c) => c !== value) : [...prev, value],
    );
  };

  const handleSave = async () => {
    const trimmedName = fullName.trim();
    if (!trimmedName) {
      Alert.alert('Validation', 'Full name is required.');
      return;
    }
    const trimmedEmail = email.trim();
    if (trimmedEmail && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(trimmedEmail)) {
      Alert.alert('Validation', 'Please enter a valid email address.');
      return;
    }

    const payload: ProfileUpdatePayload = { full_name: trimmedName };
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
    if (trimmedEmail) payload.email = trimmedEmail;
    if (campus.trim()) payload.campus = campus.trim();
    if (residence) payload.residence_type = residence;
    if (dietary) payload.dietary_preference = dietary;

    setSaving(true);
    try {
      const updated = await updateProfile(payload);
      await updatePreferences({
        preferred_pickup_locations: pickupLocations,
        favourite_categories: favCategories,
      });
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
          <ActivityIndicator size="large" color={colors.primary} />
        </View>
      </Screen>
    );
  }

  const inputStyle = [
    styles.input,
    { backgroundColor: colors.surface, borderColor: colors.border, color: colors.text },
  ];
  const labelStyle = [styles.label, { color: colors.subtext }];

  return (
    <Screen scroll>
      <View style={styles.header}>
        <Pressable onPress={() => navigation.goBack()} hitSlop={8}>
          <MaterialCommunityIcons name="arrow-left" size={24} color={colors.text} />
        </Pressable>
        <Text style={[styles.title, { color: colors.text }]}>Edit Profile</Text>
        <View style={{ width: 24 }} />
      </View>

      {/* Avatar Section */}
      <View style={styles.avatarSection}>
        <Pressable onPress={handleImagePick} disabled={uploading}>
          <View style={styles.avatarContainer}>
            {profileImageUrl ? (
              <Image source={{ uri: profileImageUrl }} style={styles.avatarImage} />
            ) : (
              <View style={[styles.avatarPlaceholder, { backgroundColor: colors.primarySoft }]}>
                <MaterialCommunityIcons name="account" size={40} color={colors.primary} />
              </View>
            )}
            <View style={[styles.avatarBadge, { backgroundColor: colors.primary, borderColor: colors.surface }]}>
              {uploading ? (
                <ActivityIndicator size="small" color="#FFFFFF" />
              ) : (
                <MaterialCommunityIcons name="camera" size={14} color="#FFFFFF" />
              )}
            </View>
          </View>
        </Pressable>
        <Text style={[styles.avatarHint, { color: colors.muted }]}>Tap to change photo</Text>
      </View>

      {/* Form Fields */}
      <View style={styles.form}>
        <View style={styles.fieldGroup}>
          <Text style={labelStyle}>Full Name</Text>
          <TextInput
            style={inputStyle}
            value={fullName}
            onChangeText={setFullName}
            placeholder="Enter your full name"
            placeholderTextColor={colors.muted}
          />
        </View>

        <View style={styles.fieldGroup}>
          <Text style={labelStyle}>Email</Text>
          <TextInput
            style={inputStyle}
            value={email}
            onChangeText={setEmail}
            placeholder="you@university.edu"
            placeholderTextColor={colors.muted}
            keyboardType="email-address"
            autoCapitalize="none"
            autoCorrect={false}
          />
        </View>

        <View style={styles.fieldGroup}>
          <Text style={labelStyle}>University ID</Text>
          <TextInput
            style={inputStyle}
            value={universityId}
            onChangeText={setUniversityId}
            placeholder="e.g. 2024CSE001"
            placeholderTextColor={colors.muted}
            autoCapitalize="characters"
          />
        </View>

        <View style={styles.fieldGroup}>
          <Text style={labelStyle}>Department</Text>
          <Pressable
            style={[styles.selectField, { backgroundColor: colors.surface, borderColor: colors.border }]}
            onPress={() => setShowDeptPicker(!showDeptPicker)}
          >
            <Text style={department ? [styles.selectText, { color: colors.text }] : [styles.selectText, { color: colors.muted }]}>
              {department || 'Select department'}
            </Text>
            <MaterialCommunityIcons
              name={showDeptPicker ? 'chevron-up' : 'chevron-down'}
              size={20}
              color={colors.muted}
            />
          </Pressable>
          {showDeptPicker && (
            <View style={[styles.pickerContainer, { backgroundColor: colors.surface, borderColor: colors.border }]}>
              {DEPARTMENTS.map((dept) => (
                <Pressable
                  key={dept}
                  style={[
                    styles.pickerItem,
                    { borderBottomColor: colors.border },
                    department === dept && { backgroundColor: colors.primarySoft },
                  ]}
                  onPress={() => {
                    setDepartment(dept);
                    setShowDeptPicker(false);
                  }}
                >
                  <Text
                    style={[
                      styles.pickerItemText,
                      { color: department === dept ? colors.primary : colors.subtext },
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
          <Text style={labelStyle}>Semester</Text>
          <TextInput
            style={inputStyle}
            value={semester}
            onChangeText={setSemester}
            placeholder="1-12"
            placeholderTextColor={colors.muted}
            keyboardType="number-pad"
            maxLength={2}
          />
        </View>

        <View style={styles.fieldGroup}>
          <Text style={labelStyle}>Campus</Text>
          <TextInput
            style={inputStyle}
            value={campus}
            onChangeText={setCampus}
            placeholder="e.g. North Campus"
            placeholderTextColor={colors.muted}
          />
        </View>

        <View style={styles.fieldGroup}>
          <Text style={labelStyle}>Residence</Text>
          <View style={styles.chipRow}>
            {RESIDENCE_OPTIONS.map((opt) => (
              <Chip
                key={opt.value}
                label={opt.label}
                icon={opt.icon}
                active={residence === opt.value}
                onPress={() => setResidence(residence === opt.value ? null : opt.value)}
              />
            ))}
          </View>
        </View>

        <View style={styles.fieldGroup}>
          <Text style={labelStyle}>Dietary Preference</Text>
          <View style={styles.chipRow}>
            {DIETARY_OPTIONS.map((opt) => (
              <Chip
                key={opt.value}
                label={opt.label}
                icon={opt.icon}
                active={dietary === opt.value}
                onPress={() => setDietary(dietary === opt.value ? null : opt.value)}
              />
            ))}
          </View>
        </View>

        <View style={styles.fieldGroup}>
          <Text style={labelStyle}>Preferred Pickup Spots</Text>
          <View style={styles.pickupInputRow}>
            <TextInput
              style={[...inputStyle, { flex: 1 }]}
              value={pickupInput}
              onChangeText={setPickupInput}
              placeholder="e.g. Library Gate"
              placeholderTextColor={colors.muted}
              onSubmitEditing={addPickupLocation}
              returnKeyType="done"
            />
            <Pressable
              onPress={addPickupLocation}
              style={[styles.addBtn, { backgroundColor: colors.primary }]}
            >
              <MaterialCommunityIcons name="plus" size={20} color="#FFFFFF" />
            </Pressable>
          </View>
          {pickupLocations.length > 0 && (
            <View style={styles.chipRow}>
              {pickupLocations.map((loc) => (
                <Chip
                  key={loc}
                  label={`${loc}  ✕`}
                  icon="map-marker"
                  onPress={() => setPickupLocations(pickupLocations.filter((l) => l !== loc))}
                />
              ))}
            </View>
          )}
        </View>

        <View style={styles.fieldGroup}>
          <Text style={labelStyle}>Favourite Categories</Text>
          <View style={styles.chipRow}>
            {CATEGORY_OPTIONS.map((opt) => (
              <Chip
                key={opt.value}
                label={opt.label}
                active={favCategories.includes(opt.value)}
                onPress={() => toggleCategory(opt.value)}
              />
            ))}
          </View>
        </View>

        <View style={styles.fieldGroup}>
          <Text style={labelStyle}>Role</Text>
          <View style={[styles.input, styles.disabledInput, { backgroundColor: colors.surfaceAlt, borderColor: colors.border }]}>
            <Text style={[styles.disabledText, { color: colors.muted }]}>
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
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
  },
  avatarHint: {
    marginTop: 8,
    fontSize: 13,
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
  },
  input: {
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 15,
    borderWidth: 1,
  },
  disabledInput: {
    justifyContent: 'center',
  },
  disabledText: {
    fontSize: 15,
  },
  selectField: {
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    borderWidth: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  selectText: {
    fontSize: 15,
  },
  pickerContainer: {
    borderRadius: 12,
    borderWidth: 1,
    marginTop: 4,
    overflow: 'hidden',
  },
  pickerItem: {
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderBottomWidth: 1,
  },
  pickerItemText: {
    fontSize: 14,
  },
  pickerItemTextActive: {
    fontWeight: '600',
  },
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  pickupInputRow: {
    flexDirection: 'row',
    gap: 8,
    alignItems: 'center',
  },
  addBtn: {
    width: 44,
    height: 44,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  actions: {
    marginTop: 24,
    marginBottom: 16,
  },
});

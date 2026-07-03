import { Platform, PermissionsAndroid } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import axios from 'axios';
import { API_BASE_URL, STORAGE_KEYS } from '../config/api';

export async function registerFCMToken(): Promise<void> {
  console.log('FCM: Disabled in vendor preview build');
  return;
}

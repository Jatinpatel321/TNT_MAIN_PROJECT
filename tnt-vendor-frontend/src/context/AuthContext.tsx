import React, { createContext, useContext, useState, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import axios from 'axios';
import { registerFCMToken } from '../services/pushRegistrationService';

const API_BASE_URL = 'http://localhost:8000';

interface User {
  id: number;
  vendor_id: number;
  vendor_name: string;
  phone: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (vendorId: number, password: string) => Promise<void>;
  logout: () => Promise<void>;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadStoredAuth();
  }, []);

  const loadStoredAuth = async () => {
    try {
      const storedToken = await AsyncStorage.getItem('vendor_token');
      const storedUser = await AsyncStorage.getItem('vendor_user');
      if (storedToken && storedUser) {
        setToken(storedToken);
        setUser(JSON.parse(storedUser));
      }
    } catch (error) {
      console.error('Failed to load auth:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (vendorId: number, password: string) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/v1/vendor/login`, {
        vendor_id: vendorId,
        password,
      });
      const { access_token, vendor } = response.data;
      setToken(access_token);
      setUser(vendor);
      await AsyncStorage.setItem('vendor_token', access_token);
      await AsyncStorage.setItem('vendor_user', JSON.stringify(vendor));
      // Register FCM token after successful login
      registerFCMToken();
    } catch (error) {
      throw new Error('Login failed');
    }
  };

  const logout = async () => {
    try {
      setUser(null);
      setToken(null);
      await AsyncStorage.removeItem('vendor_token');
      await AsyncStorage.removeItem('vendor_user');
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

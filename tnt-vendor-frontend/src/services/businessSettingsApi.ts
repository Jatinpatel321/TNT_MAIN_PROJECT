import apiClient from './apiClient';
import { API_BASE_URL } from '../config/api';

export interface BusinessHours {
  [key: string]: {
    open: string;
    close: string;
    is_closed: boolean;
  };
}

export interface Holiday {
  date: string;
  reason: string;
  id?: number;
}

export interface BusinessSettings {
  business_hours: BusinessHours;
  holidays: Holiday[];
  pickup_instructions: string;
}

export const businessSettingsApi = {
  getSettings: () =>
    apiClient.get<BusinessSettings>(`${API_BASE_URL}/v1/vendors/profile/`),

  updateBusinessHours: (hours: BusinessHours) =>
    apiClient.put<BusinessSettings>(`${API_BASE_URL}/v1/vendors/profile/`, {
      business_hours: hours,
    }),

  updateHolidays: (holidays: Holiday[]) =>
    apiClient.put<BusinessSettings>(`${API_BASE_URL}/v1/vendors/profile/`, {
      holidays,
    }),

  updatePickupInstructions: (instructions: string) =>
    apiClient.put<BusinessSettings>(`${API_BASE_URL}/v1/vendors/profile/`, {
      pickup_instructions: instructions,
    }),

  updateAllSettings: (settings: Partial<BusinessSettings>) =>
    apiClient.put<BusinessSettings>(`${API_BASE_URL}/v1/vendors/profile/`, settings),
};

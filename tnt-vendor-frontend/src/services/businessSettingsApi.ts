import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

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
    axios.get<BusinessSettings>(`${API_BASE_URL}/v1/vendors/profile/`),

  updateBusinessHours: (hours: BusinessHours) =>
    axios.put<BusinessSettings>(`${API_BASE_URL}/v1/vendors/profile/`, {
      business_hours: hours,
    }),

  updateHolidays: (holidays: Holiday[]) =>
    axios.put<BusinessSettings>(`${API_BASE_URL}/v1/vendors/profile/`, {
      holidays,
    }),

  updatePickupInstructions: (instructions: string) =>
    axios.put<BusinessSettings>(`${API_BASE_URL}/v1/vendors/profile/`, {
      pickup_instructions: instructions,
    }),

  updateAllSettings: (settings: Partial<BusinessSettings>) =>
    axios.put<BusinessSettings>(`${API_BASE_URL}/v1/vendors/profile/`, settings),
};
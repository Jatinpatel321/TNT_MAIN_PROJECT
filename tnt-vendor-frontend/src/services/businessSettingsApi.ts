import apiClient from './apiClient';

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
    apiClient.get<BusinessSettings>(`/v1/vendors/business-hours/`),

  updateBusinessHours: (hours: BusinessHours) =>
    apiClient.put<BusinessSettings>(`/v1/vendors/business-hours/`, {
      business_hours: hours,
    }),

  updateHolidays: (holidays: Holiday[]) =>
    apiClient.put<BusinessSettings>(`/v1/vendors/business-hours/holidays`, {
      holidays,
    }),

  updatePickupInstructions: (instructions: string) =>
    apiClient.put<BusinessSettings>(`/v1/vendors/business-hours/pickup-instructions`, {
      pickup_instructions: instructions,
    }),

  updateAllSettings: (settings: Partial<BusinessSettings>) =>
    apiClient.put<BusinessSettings>(`/v1/vendors/business-hours/`, settings),
};

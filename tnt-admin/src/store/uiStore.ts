import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface UIStore {
  sidebarOpen: boolean;
  theme: 'light';
  emergencyShutdown: boolean;
  pendingVendorsCount: number;
  openComplaintsCount: number;
  notificationsCount: number;

  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setEmergencyShutdown: (active: boolean) => void;
  setPendingVendorsCount: (count: number) => void;
  setOpenComplaintsCount: (count: number) => void;
  setNotificationsCount: (count: number) => void;
}

export const useUIStore = create<UIStore>()(
  persist(
    (set, get) => ({
      sidebarOpen: true,
      theme: 'light',
      emergencyShutdown: false,
      pendingVendorsCount: 0,
      openComplaintsCount: 0,
      notificationsCount: 0,

      toggleSidebar: () =>
        set({ sidebarOpen: !get().sidebarOpen }),

      setSidebarOpen: (open: boolean) =>
        set({ sidebarOpen: open }),

      setEmergencyShutdown: (active: boolean) =>
        set({ emergencyShutdown: active }),

      setPendingVendorsCount: (count: number) =>
        set({ pendingVendorsCount: count }),

      setOpenComplaintsCount: (count: number) =>
        set({ openComplaintsCount: count }),

      setNotificationsCount: (count: number) =>
        set({ notificationsCount: count }),
    }),
    {
      name: 'tnt-admin-ui',
      partialize: (state) => ({ sidebarOpen: state.sidebarOpen }),
    }
  )
);
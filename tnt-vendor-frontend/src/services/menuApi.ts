import apiClient from './apiClient';

export interface MenuItem {
  id: number;
  vendor_id: number;
  name: string;
  price: number;
  category: string;
  description?: string;
  is_available: boolean;
  image_url?: string;
  prep_time_minutes?: number;
  available_quantity?: number;
  // Extended fields from inventory merge
  stock_level?: number;
  inventory_id?: number;
  is_low_stock?: boolean;
}

export interface StationeryService {
  id: number;
  service_type: 'xerox' | 'color_print' | 'bw_print';
  name: string;
  description?: string;
  price_per_page: number;
  max_capacity: number;
  current_load: number;
  is_available: boolean;
}

export interface InventoryDashboardData {
  items: Array<{
    id: number;
    menu_item_id: number;
    name: string;
    current_stock: number;
    low_stock_threshold: number;
  }>;
}

export const menuApi = {
  // ── Menu Items ────────────────────────────────────────────────

  getItems: (vendorId: number) =>
    apiClient.get<{ items: MenuItem[] }>(`/v1/menu/items?vendor_id=${vendorId}`),

  getItem: (itemId: number) =>
    apiClient.get<MenuItem>(`/v1/menu/items/${itemId}`),

  createItem: (data: FormData) =>
    apiClient.post<MenuItem>(`/v1/menu/items`, data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  createItemJson: (data: Record<string, any>) =>
    apiClient.post<MenuItem>(`/v1/menu/items`, data),

  updateItem: (itemId: number, data: FormData) =>
    apiClient.put<MenuItem>(`/v1/menu/items/${itemId}`, data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  toggleAvailability: (itemId: number) =>
    apiClient.put(`/v1/menu/items/${itemId}/toggle`),

  deleteItem: (itemId: number) =>
    apiClient.delete(`/v1/menu/items/${itemId}`),

  exportCsv: (vendorId: number) =>
    apiClient.get(`/v1/menu/items?vendor_id=${vendorId}&format=csv`, {
      responseType: 'blob',
    }),

  // ── Inventory (menu-level) ────────────────────────────────────

  getInventoryDashboard: () =>
    apiClient.get<InventoryDashboardData>(`/v1/vendors/inventory/dashboard`),

  createInventory: (menuItemId: number, stock: number, threshold: number) =>
    apiClient.post(`/v1/menu/inventory`, {
      menu_item_id: menuItemId,
      current_stock: stock,
      low_stock_threshold: threshold,
      auto_disable: true,
    }),

  restockItem: (inventoryId: number, quantity: number) =>
    apiClient.post(`/v1/menu/inventory/${inventoryId}/restock`, { quantity }),

  restockItemForm: (inventoryId: number, quantity: number) => {
    const formData = new FormData();
    formData.append('quantity', quantity.toString());
    return apiClient.post(`/v1/menu/inventory/${inventoryId}/restock`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  createInventoryForm: (menuItemId: number, stock: number, threshold: number) => {
    const formData = new FormData();
    formData.append('menu_item_id', menuItemId.toString());
    formData.append('current_stock', stock.toString());
    formData.append('low_stock_threshold', threshold.toString());
    formData.append('auto_disable', 'true');
    return apiClient.post(`/v1/menu/inventory`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  // ── Stationery Services ───────────────────────────────────────

  getStationeryServices: (vendorId: number) =>
    apiClient.get<{ items: StationeryService[] }>(
      `/v1/menu/stationery?vendor_id=${vendorId}`,
    ),

  createStationeryService: (data: FormData) =>
    apiClient.post(`/v1/menu/stationery`, data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  updateStationeryService: (serviceId: number, data: FormData) =>
    apiClient.put(`/v1/menu/stationery/${serviceId}`, data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  toggleStationeryAvailability: (serviceId: number, isAvailable: boolean) => {
    const formData = new FormData();
    formData.append('is_available', isAvailable.toString());
    return apiClient.put(`/v1/menu/stationery/${serviceId}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  deleteStationeryService: (serviceId: number) =>
    apiClient.delete(`/v1/menu/stationery/${serviceId}`),
};

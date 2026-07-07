import api from './axios';

export interface MenuItem {
  id: number;
  vendor_id: number;
  name: string;
  description: string | null;
  price: number;
  image_url: string | null;
  is_available: boolean;
  prep_time_minutes: number | null;
  available_quantity: number | null;
  category: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface Inventory {
  id: number;
  menu_item_id: number;
  current_stock: number;
  low_stock_threshold: number;
  last_restocked_at: string | null;
  auto_disable: boolean;
  created_at: string | null;
  updated_at: string | null;
  menu_item?: MenuItem;
}

export interface StationeryService {
  id: number;
  vendor_id: number;
  service_type: string;
  name: string;
  description: string | null;
  price_per_page: number;
  max_capacity: number | null;
  current_load: number;
  is_available: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface PaginatedResponse {
  items: any[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface LowStockAlert {
  inventory_id: number;
  menu_item_id: number;
  item_name: string;
  current_stock: number;
  threshold: number;
  is_available: boolean;
  urgency: 'critical' | 'low';
}

export const menuApi = {
  // Menu Items
  addItem: (data: FormData) =>
    api.post<MenuItem>('/v1/menu/items', data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  getItems: (vendorId: number, params?: {
    page?: number;
    page_size?: number;
    search?: string;
    category?: string;
    available_only?: boolean;
  }) =>
    api.get<PaginatedResponse>('/v1/menu/items', {
      params: { vendor_id: vendorId, ...params },
    }),

  getItem: (itemId: number) =>
    api.get<MenuItem>(`/v1/menu/items/${itemId}`),

  updateItem: (itemId: number, data: FormData) =>
    api.put<MenuItem>(`/v1/menu/items/${itemId}`, data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  deleteItem: (itemId: number) =>
    api.delete(`/v1/menu/items/${itemId}`),

  toggleItem: (itemId: number) =>
    api.put<MenuItem>(`/v1/menu/items/${itemId}/toggle`),

  // Inventory
  createInventory: (data: {
    menu_item_id: number;
    current_stock: number;
    low_stock_threshold?: number;
    auto_disable?: boolean;
  }) =>
    api.post<Inventory>('/v1/menu/inventory', data),

  getInventory: (vendorId: number, params?: {
    page?: number;
    page_size?: number;
    low_stock_only?: boolean;
  }) =>
    api.get<PaginatedResponse>('/v1/menu/inventory', {
      params: { vendor_id: vendorId, ...params },
    }),

  getInventoryById: (inventoryId: number) =>
    api.get<Inventory>(`/v1/menu/inventory/${inventoryId}`),

  updateInventory: (inventoryId: number, data: {
    current_stock?: number;
    low_stock_threshold?: number;
    auto_disable?: boolean;
  }) =>
    api.put<Inventory>(`/v1/menu/inventory/${inventoryId}`, data),

  restockInventory: (inventoryId: number, quantity: number) =>
    api.post<Inventory>(`/v1/menu/inventory/${inventoryId}/restock`, null, {
      params: { quantity },
    }),

  getLowStockAlerts: () =>
    api.get<{ alerts: LowStockAlert[]; count: number }>('/v1/menu/inventory/alerts/low-stock'),

  // Stationery Services
  addStationeryService: (data: FormData) =>
    api.post<StationeryService>('/v1/menu/stationery', data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  getStationeryServices: (vendorId: number, params?: {
    page?: number;
    page_size?: number;
    service_type?: string;
  }) =>
    api.get<PaginatedResponse>('/v1/menu/stationery', {
      params: { vendor_id: vendorId, ...params },
    }),

  getStationeryService: (serviceId: number) =>
    api.get<StationeryService>(`/v1/menu/stationery/${serviceId}`),

  updateStationeryService: (serviceId: number, data: FormData) =>
    api.put<StationeryService>(`/v1/menu/stationery/${serviceId}`, data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  deleteStationeryService: (serviceId: number) =>
    api.delete(`/v1/menu/stationery/${serviceId}`),

  updateServiceLoad: (serviceId: number, pages: number) =>
    api.post<StationeryService>(`/v1/menu/stationery/${serviceId}/load`, null, {
      params: { pages },
    }),
};
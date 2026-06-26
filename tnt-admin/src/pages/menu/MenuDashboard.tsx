import React, { useEffect, useState } from 'react';
import { Plus, Search, Filter, Edit, Trash2, ToggleLeft, ToggleRight, Package, AlertTriangle, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';
import { menuApi, type MenuItem, type Inventory, type LowStockAlert, type PaginatedResponse } from '../../api/menu';

export default function MenuDashboard() {
  const [items, setItems] = useState<MenuItem[]>([]);
  const [inventory, setInventory] = useState<Inventory[]>([]);
  const [alerts, setAlerts] = useState<LowStockAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState<string>('');
  const [vendorId, setVendorId] = useState<number>(1);
  const [activeTab, setActiveTab] = useState<'menu' | 'inventory' | 'alerts'>('menu');

  useEffect(() => {
    loadData();
  }, [vendorId, page, activeTab]);

  const loadData = async () => {
    setLoading(true);
    try {
      if (activeTab === 'menu') {
        const res = await menuApi.getItems(vendorId, {
          page,
          page_size: 10,
          search: search || undefined,
          category: category || undefined,
        });
        setItems(res.data.items);
        setTotalPages(res.data.total_pages);
      } else if (activeTab === 'inventory') {
        const res = await menuApi.getInventory(vendorId, { page, page_size: 10 });
        setInventory(res.data.items);
        setTotalPages(res.data.total_pages);
      } else if (activeTab === 'alerts') {
        const res = await menuApi.getLowStockAlerts();
        setAlerts(res.data.alerts);
      }
    } catch {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = async (itemId: number) => {
    try {
      await menuApi.toggleItem(itemId);
      toast.success('Item status updated');
      loadData();
    } catch {
      toast.error('Failed to update item');
    }
  };

  const handleDelete = async (itemId: number) => {
    if (!confirm('Are you sure you want to delete this item?')) return;
    try {
      await menuApi.deleteItem(itemId);
      toast.success('Item deleted');
      loadData();
    } catch {
      toast.error('Failed to delete item');
    }
  };

  const handleRestock = async (inventoryId: number) => {
    const quantity = prompt('Enter quantity to restock:');
    if (!quantity || isNaN(Number(quantity))) return;
    try {
      await menuApi.restockInventory(inventoryId, parseInt(quantity));
      toast.success('Inventory restocked');
      loadData();
    } catch {
      toast.error('Failed to restock');
    }
  };

  const getStatusColor = (isAvailable: boolean) => {
    return isAvailable ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700';
  };

  const getUrgencyColor = (urgency: string) => {
    return urgency === 'critical' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700';
  };

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[#111827]">Menu & Inventory</h1>
          <p className="text-sm text-[#6B7280]">Manage your food items and stationery services</p>
        </div>
        <button
          onClick={() => window.location.href = '/menu/add'}
          className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-2 px-4 rounded-lg text-sm transition-colors"
        >
          <Plus className="w-4 h-4" /> Add Item
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-[#E5E7EB]">
        <button
          onClick={() => setActiveTab('menu')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'menu'
              ? 'border-emerald-600 text-emerald-600'
              : 'border-transparent text-[#6B7280] hover:text-[#111827]'
          }`}
        >
          Menu Items
        </button>
        <button
          onClick={() => setActiveTab('inventory')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'inventory'
              ? 'border-emerald-600 text-emerald-600'
              : 'border-transparent text-[#6B7280] hover:text-[#111827]'
          }`}
        >
          Inventory
        </button>
        <button
          onClick={() => setActiveTab('alerts')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors relative ${
            activeTab === 'alerts'
              ? 'border-emerald-600 text-emerald-600'
              : 'border-transparent text-[#6B7280] hover:text-[#111827]'
          }`}
        >
          Alerts
          {alerts.length > 0 && (
            <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
              {alerts.length}
            </span>
          )}
        </button>
      </div>

      {/* Filters */}
      {activeTab === 'menu' && (
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#9CA3AF]" />
            <input
              type="text"
              placeholder="Search items..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && loadData()}
              className="w-full pl-10 pr-4 py-2 bg-white border border-[#E5E7EB] rounded-lg text-sm focus:outline-none focus:border-emerald-500"
            />
          </div>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="px-4 py-2 bg-white border border-[#E5E7EB] rounded-lg text-sm focus:outline-none focus:border-emerald-500"
          >
            <option value="">All Categories</option>
            <option value="food">Food</option>
            <option value="stationery">Stationery</option>
          </select>
          <button
            onClick={loadData}
            className="px-4 py-2 bg-white border border-[#E5E7EB] rounded-lg text-sm hover:bg-gray-50"
          >
            <Filter className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <>
          {/* Menu Items Tab */}
          {activeTab === 'menu' && (
            <div className="grid gap-4">
              {items.length === 0 ? (
                <div className="text-center py-12 text-[#6B7280]">No menu items found</div>
              ) : (
                items.map((item) => (
                  <div key={item.id} className="bg-white rounded-xl border border-[#E5E7EB] p-4 flex items-center gap-4">
                    <div className="w-16 h-16 bg-gray-100 rounded-lg flex items-center justify-center">
                      {item.image_url ? (
                        <img src={item.image_url} alt={item.name} className="w-full h-full object-cover rounded-lg" />
                      ) : (
                        <Package className="w-8 h-8 text-[#9CA3AF]" />
                      )}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-[#111827]">{item.name}</h3>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(item.is_available)}`}>
                          {item.is_available ? 'Available' : 'Unavailable'}
                        </span>
                        <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
                          {item.category}
                        </span>
                      </div>
                      <p className="text-sm text-[#6B7280] mt-1">{item.description || 'No description'}</p>
                      <div className="flex items-center gap-4 mt-2 text-xs text-[#6B7280]">
                        <span>₹{(item.price / 100).toFixed(2)}</span>
                        {item.prep_time_minutes && <span>⏱️ {item.prep_time_minutes} min</span>}
                        {item.available_quantity !== null && <span>📦 {item.available_quantity} left</span>}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleToggle(item.id)}
                        className="p-2 rounded-lg hover:bg-gray-100 text-[#6B7280]"
                        title={item.is_available ? 'Disable' : 'Enable'}
                      >
                        {item.is_available ? <ToggleRight className="w-5 h-5 text-emerald-600" /> : <ToggleLeft className="w-5 h-5" />}
                      </button>
                      <button
                        onClick={() => window.location.href = `/menu/edit/${item.id}`}
                        className="p-2 rounded-lg hover:bg-gray-100 text-[#6B7280]"
                        title="Edit"
                      >
                        <Edit className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(item.id)}
                        className="p-2 rounded-lg hover:bg-red-50 text-red-600"
                        title="Delete"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Inventory Tab */}
          {activeTab === 'inventory' && (
            <div className="grid gap-4">
              {inventory.length === 0 ? (
                <div className="text-center py-12 text-[#6B7280]">No inventory records found</div>
              ) : (
                inventory.map((inv) => (
                  <div key={inv.id} className="bg-white rounded-xl border border-[#E5E7EB] p-4 flex items-center gap-4">
                    <div className="flex-1">
                      <h3 className="font-semibold text-[#111827]">{inv.menu_item?.name || 'Unknown Item'}</h3>
                      <div className="flex items-center gap-4 mt-2 text-sm">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          inv.current_stock <= inv.low_stock_threshold ? 'bg-red-100 text-red-700' : 'bg-emerald-100 text-emerald-700'
                        }`}>
                          Stock: {inv.current_stock}
                        </span>
                        <span className="text-[#6B7280]">Threshold: {inv.low_stock_threshold}</span>
                        {inv.last_restocked_at && (
                          <span className="text-[#6B7280]">Last restocked: {new Date(inv.last_restocked_at).toLocaleDateString()}</span>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={() => handleRestock(inv.id)}
                      className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg text-sm transition-colors"
                    >
                      <RefreshCw className="w-4 h-4" /> Restock
                    </button>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Alerts Tab */}
          {activeTab === 'alerts' && (
            <div className="grid gap-4">
              {alerts.length === 0 ? (
                <div className="text-center py-12 text-[#6B7280]">No low stock alerts</div>
              ) : (
                alerts.map((alert) => (
                  <div key={alert.inventory_id} className="bg-white rounded-xl border border-[#E5E7EB] p-4 flex items-center gap-4">
                    <div className={`p-3 rounded-full ${alert.urgency === 'critical' ? 'bg-red-100' : 'bg-yellow-100'}`}>
                      <AlertTriangle className={`w-6 h-6 ${alert.urgency === 'critical' ? 'text-red-600' : 'text-yellow-600'}`} />
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-[#111827]">{alert.item_name}</h3>
                      <div className="flex items-center gap-3 mt-1 text-sm">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getUrgencyColor(alert.urgency)}`}>
                          {alert.urgency.toUpperCase()}
                        </span>
                        <span className="text-[#6B7280]">Stock: {alert.current_stock} / Threshold: {alert.threshold}</span>
                      </div>
                    </div>
                    <button
                      onClick={() => {
                        setActiveTab('inventory');
                        setTimeout(() => handleRestock(alert.inventory_id), 100);
                      }}
                      className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-2 px-4 rounded-lg text-sm transition-colors"
                    >
                      <RefreshCw className="w-4 h-4" /> Restock
                    </button>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Pagination */}
          {activeTab !== 'alerts' && totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <button
                onClick={() => setPage(page - 1)}
                disabled={page === 1}
                className="px-3 py-1 border border-[#E5E7EB] rounded-lg text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
              >
                Previous
              </button>
              <span className="text-sm text-[#6B7280]">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage(page + 1)}
                disabled={page === totalPages}
                className="px-3 py-1 border border-[#E5E7EB] rounded-lg text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
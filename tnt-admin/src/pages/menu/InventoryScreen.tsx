import React, { useEffect, useState } from 'react';
import { ArrowLeft, RefreshCw, AlertTriangle, Package } from 'lucide-react';
import toast from 'react-hot-toast';
import { menuApi, type Inventory, type LowStockAlert } from '../../api/menu';

export default function InventoryScreen() {
  const [inventory, setInventory] = useState<Inventory[]>([]);
  const [alerts, setAlerts] = useState<LowStockAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [vendorId] = useState<number>(1);

  useEffect(() => {
    loadData();
  }, [vendorId, page]);

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await menuApi.getInventory(vendorId, { page, page_size: 10 });
      setInventory(res.data.items);
      setTotalPages(res.data.total_pages);

      const alertsRes = await menuApi.getLowStockAlerts();
      setAlerts(alertsRes.data.alerts);
    } catch {
      toast.error('Failed to load inventory');
    } finally {
      setLoading(false);
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

  const getStockColor = (current: number, threshold: number) => {
    if (current === 0) return 'bg-red-100 text-red-700';
    if (current <= threshold) return 'bg-yellow-100 text-yellow-700';
    return 'bg-emerald-100 text-emerald-700';
  };

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[#111827]">Inventory Management</h1>
          <p className="text-sm text-[#6B7280]">Track stock levels and manage restocking</p>
        </div>
        <button
          onClick={() => window.location.href = '/menu'}
          className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-2 px-4 rounded-lg text-sm transition-colors"
        >
          <Package className="w-4 h-4" /> Menu Dashboard
        </button>
      </div>

      {/* Low Stock Alerts */}
      {alerts.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-5 h-5 text-red-600" />
            <h2 className="font-semibold text-red-900">Low Stock Alerts ({alerts.length})</h2>
          </div>
          <div className="grid gap-2">
            {alerts.slice(0, 5).map((alert) => (
              <div key={alert.inventory_id} className="flex items-center justify-between bg-white rounded-lg p-3">
                <div>
                  <p className="font-medium text-[#111827]">{alert.item_name}</p>
                  <p className="text-sm text-[#6B7280]">
                    Stock: {alert.current_stock} / Threshold: {alert.threshold}
                  </p>
                </div>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  alert.urgency === 'critical' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'
                }`}>
                  {alert.urgency.toUpperCase()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Inventory List */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="grid gap-4">
          {inventory.length === 0 ? (
            <div className="text-center py-12 text-[#6B7280]">No inventory records found</div>
          ) : (
            inventory.map((inv) => (
              <div key={inv.id} className="bg-white rounded-xl border border-[#E5E7EB] p-4 flex items-center gap-4">
                <div className="flex-1">
                  <h3 className="font-semibold text-[#111827]">{inv.menu_item?.name || 'Unknown Item'}</h3>
                  <div className="flex items-center gap-4 mt-2 text-sm">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStockColor(inv.current_stock, inv.low_stock_threshold)}`}>
                      Stock: {inv.current_stock}
                    </span>
                    <span className="text-[#6B7280]">Threshold: {inv.low_stock_threshold}</span>
                    {inv.last_restocked_at && (
                      <span className="text-[#6B7280]">
                        Last restocked: {new Date(inv.last_restocked_at).toLocaleDateString()}
                      </span>
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

      {/* Pagination */}
      {totalPages > 1 && (
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
    </div>
  );
}
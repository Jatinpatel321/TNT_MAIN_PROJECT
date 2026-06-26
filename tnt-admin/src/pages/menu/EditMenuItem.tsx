import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Upload, Package } from 'lucide-react';
import toast from 'react-hot-toast';
import { menuApi, type MenuItem } from '../../api/menu';

export default function EditMenuItem() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    price: '',
    prep_time_minutes: '',
    available_quantity: '',
  });
  const [isAvailable, setIsAvailable] = useState(true);
  const [image, setImage] = useState<File | null>(null);

  useEffect(() => {
    if (id) {
      loadItem(parseInt(id));
    }
  }, [id]);

  const loadItem = async (itemId: number) => {
    try {
      const res = await menuApi.getItem(itemId);
      const item = res.data;
      setFormData({
        name: item.name,
        description: item.description || '',
        price: item.price.toString(),
        prep_time_minutes: item.prep_time_minutes?.toString() || '',
        available_quantity: item.available_quantity?.toString() || '',
      });
      setIsAvailable(item.is_available);
    } catch {
      toast.error('Failed to load item');
      navigate('/menu');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name || !formData.price) {
      toast.error('Name and price are required');
      return;
    }

    setSaving(true);
    try {
      const data = new FormData();
      data.append('name', formData.name);
      data.append('price', formData.price);
      data.append('description', formData.description);
      data.append('is_available', isAvailable.toString());
      if (formData.prep_time_minutes) data.append('prep_time_minutes', formData.prep_time_minutes);
      if (formData.available_quantity) data.append('available_quantity', formData.available_quantity);
      if (image) data.append('image', image);

      await menuApi.updateItem(parseInt(id!), data);
      toast.success('Item updated successfully');
      navigate('/menu');
    } catch {
      toast.error('Failed to update item');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto p-6">
      <button
        onClick={() => navigate('/menu')}
        className="flex items-center gap-2 text-[#6B7280] hover:text-[#111827] mb-6"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Menu
      </button>

      <div className="bg-white rounded-2xl border border-[#E5E7EB] p-6 shadow-sm">
        <h1 className="text-2xl font-bold text-[#111827] mb-6">Edit Item</h1>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[#374151] mb-1.5">Item Name *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full bg-[#F3F5F9] border border-[#E5E7EB] rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-emerald-500"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[#374151] mb-1.5">Description</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full bg-[#F3F5F9] border border-[#E5E7EB] rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-emerald-500"
              rows={3}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-[#374151] mb-1.5">Price (₹) *</label>
              <input
                type="number"
                value={formData.price}
                onChange={(e) => setFormData({ ...formData, price: e.target.value })}
                className="w-full bg-[#F3F5F9] border border-[#E5E7EB] rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-emerald-500"
                min="0"
                step="0.01"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-[#374151] mb-1.5">Prep Time (min)</label>
              <input
                type="number"
                value={formData.prep_time_minutes}
                onChange={(e) => setFormData({ ...formData, prep_time_minutes: e.target.value })}
                className="w-full bg-[#F3F5F9] border border-[#E5E7EB] rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-emerald-500"
                min="0"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-[#374151] mb-1.5">Available Quantity</label>
              <input
                type="number"
                value={formData.available_quantity}
                onChange={(e) => setFormData({ ...formData, available_quantity: e.target.value })}
                className="w-full bg-[#F3F5F9] border border-[#E5E7EB] rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-emerald-500"
                min="0"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-[#374151] mb-1.5">Status</label>
              <button
                type="button"
                onClick={() => setIsAvailable(!isAvailable)}
                className={`w-full px-4 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                  isAvailable
                    ? 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200'
                    : 'bg-red-100 text-red-700 hover:bg-red-200'
                }`}
              >
                {isAvailable ? '✓ Available' : '✕ Unavailable'}
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-[#374151] mb-1.5">Update Image</label>
            <div className="flex items-center gap-4">
              <label className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-[#F3F5F9] border-2 border-dashed border-[#E5E7EB] rounded-xl cursor-pointer hover:border-emerald-500 transition-colors">
                <Upload className="w-5 h-5 text-[#6B7280]" />
                <span className="text-sm text-[#6B7280]">{image ? image.name : 'Choose new image'}</span>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setImage(e.target.files?.[0] || null)}
                  className="hidden"
                />
              </label>
            </div>
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="submit"
              disabled={saving}
              className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-2.5 px-4 rounded-xl transition-colors disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
            <button
              type="button"
              onClick={() => navigate('/menu')}
              className="px-6 py-2.5 bg-gray-100 hover:bg-gray-200 text-[#374151] font-medium rounded-xl transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
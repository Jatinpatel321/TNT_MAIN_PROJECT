import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Upload, Package } from 'lucide-react';
import toast from 'react-hot-toast';
import { menuApi } from '../../api/menu';

export default function AddMenuItem() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    price: '',
    category: 'food',
    prep_time_minutes: '',
    available_quantity: '',
  });
  const [image, setImage] = useState<File | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name || !formData.price) {
      toast.error('Name and price are required');
      return;
    }

    setLoading(true);
    try {
      const data = new FormData();
      data.append('name', formData.name);
      data.append('price', formData.price);
      data.append('description', formData.description);
      data.append('category', formData.category);
      if (formData.prep_time_minutes) data.append('prep_time_minutes', formData.prep_time_minutes);
      if (formData.available_quantity) data.append('available_quantity', formData.available_quantity);
      if (image) data.append('image', image);

      await menuApi.addItem(data);
      toast.success('Item added successfully');
      navigate('/menu');
    } catch {
      toast.error('Failed to add item');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6">
      <button
        onClick={() => navigate('/menu')}
        className="flex items-center gap-2 text-[#6B7280] hover:text-[#111827] mb-6"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Menu
      </button>

      <div className="bg-white rounded-2xl border border-[#E5E7EB] p-6 shadow-sm">
        <h1 className="text-2xl font-bold text-[#111827] mb-6">Add New Item</h1>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[#374151] mb-1.5">Item Name *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full bg-[#F3F5F9] border border-[#E5E7EB] rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-emerald-500"
              placeholder="e.g., Chicken Biryani"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[#374151] mb-1.5">Description</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full bg-[#F3F5F9] border border-[#E5E7EB] rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-emerald-500"
              placeholder="Describe your item..."
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
                placeholder="0.00"
                min="0"
                step="0.01"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-[#374151] mb-1.5">Category</label>
              <select
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                className="w-full bg-[#F3F5F9] border border-[#E5E7EB] rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-emerald-500"
              >
                <option value="food">Food</option>
                <option value="stationery">Stationery</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-[#374151] mb-1.5">Prep Time (min)</label>
              <input
                type="number"
                value={formData.prep_time_minutes}
                onChange={(e) => setFormData({ ...formData, prep_time_minutes: e.target.value })}
                className="w-full bg-[#F3F5F9] border border-[#E5E7EB] rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-emerald-500"
                placeholder="15"
                min="0"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-[#374151] mb-1.5">Initial Quantity</label>
              <input
                type="number"
                value={formData.available_quantity}
                onChange={(e) => setFormData({ ...formData, available_quantity: e.target.value })}
                className="w-full bg-[#F3F5F9] border border-[#E5E7EB] rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-emerald-500"
                placeholder="100"
                min="0"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-[#374151] mb-1.5">Image</label>
            <div className="flex items-center gap-4">
              <label className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-[#F3F5F9] border-2 border-dashed border-[#E5E7EB] rounded-xl cursor-pointer hover:border-emerald-500 transition-colors">
                <Upload className="w-5 h-5 text-[#6B7280]" />
                <span className="text-sm text-[#6B7280]">{image ? image.name : 'Choose file'}</span>
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
              disabled={loading}
              className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-2.5 px-4 rounded-xl transition-colors disabled:opacity-50"
            >
              {loading ? 'Adding...' : 'Add Item'}
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
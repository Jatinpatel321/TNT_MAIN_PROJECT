import React, { useState } from 'react';
import { Download, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { cn } from '../utils/cn';

interface ExportButtonProps {
  label?: string;
  exportFn: () => Promise<any>;
  filename?: string;
  className?: string;
}

export function ExportButton({
  label = 'Export CSV',
  exportFn,
  filename,
  className = '',
}: ExportButtonProps) {
  const [loading, setLoading] = useState(false);

  const handleExport = async () => {
    setLoading(true);
    try {
      const res = await exportFn();
      const blob = new Blob([res.data], { type: 'text/csv' });
      const objectUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = objectUrl;
      a.download = filename || `tnt_export_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(objectUrl);
      toast.success('Export downloaded');
    } catch (err) {
      console.error(err);
      toast.error('Export failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleExport}
      disabled={loading}
      className={cn(
        'inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-[#E5E7EB] bg-white text-sm font-medium text-[#4B5563] hover:bg-[#F3F5F9] transition disabled:opacity-50 disabled:cursor-not-allowed',
        className
      )}
    >
      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
      {loading ? 'Exporting...' : label}
    </button>
  );
}
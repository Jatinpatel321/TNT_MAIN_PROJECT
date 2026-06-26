import React from 'react';

interface LoadingSkeletonProps {
  rows?: number;
  columns?: number;
  type?: 'table' | 'card' | 'list';
}

export function LoadingSkeleton({ rows = 5, columns = 4, type = 'table' }: LoadingSkeletonProps) {
  if (type === 'card') {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="tnt-card">
            <div className="flex items-start justify-between mb-4">
              <div className="skeleton w-10 h-10 rounded-lg" />
              <div className="skeleton w-16 h-5 rounded-full" />
            </div>
            <div className="skeleton w-24 h-7 rounded mb-2" />
            <div className="skeleton w-32 h-4 rounded" />
          </div>
        ))}
      </div>
    );
  }

  if (type === 'list') {
    return (
      <div className="space-y-3">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex items-center gap-4 p-4 tnt-card">
            <div className="skeleton w-10 h-10 rounded-full shrink-0" />
            <div className="flex-1 space-y-2">
              <div className="skeleton w-1/3 h-4 rounded" />
              <div className="skeleton w-1/2 h-3 rounded" />
            </div>
            <div className="skeleton w-16 h-6 rounded-full" />
          </div>
        ))}
      </div>
    );
  }

  // Table skeleton
  return (
    <div className="tnt-card overflow-hidden p-0">
      {/* Header */}
      <div className="flex gap-4 px-4 py-3 border-b border-[#2E2E50]">
        {Array.from({ length: columns }).map((_, i) => (
          <div key={i} className="skeleton h-4 rounded flex-1" />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="flex gap-4 px-4 py-3.5 border-b border-[#2E2E50]/50"
          style={{ opacity: 1 - i * 0.1 }}
        >
          {Array.from({ length: columns }).map((_, j) => (
            <div
              key={j}
              className="skeleton h-4 rounded flex-1"
              style={{ width: `${Math.random() * 40 + 60}%` }}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

// Simple spinner for inline use
export function Spinner({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const sizes = { sm: 'w-4 h-4', md: 'w-6 h-6', lg: 'w-10 h-10' };
  return (
    <div className={`${sizes[size]} border-2 border-[#2E2E50] border-t-[#E85D24] rounded-full animate-spin`} />
  );
}

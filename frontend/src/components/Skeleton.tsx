/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';

export const SkeletonCard: React.FC = () => {
  return (
    <div className="bg-white border border-[#E5E2D9] rounded-xl p-5 shadow-sm animate-pulse space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-20 h-5 bg-stone-200 rounded" />
          <div className="w-16 h-5 bg-stone-200 rounded-full" />
        </div>
        <div className="w-24 h-4 bg-stone-200 rounded" />
      </div>

      <div className="space-y-2">
        <div className="w-3/4 h-5 bg-stone-200 rounded" />
        <div className="w-full h-4 bg-stone-150 rounded" />
        <div className="w-5/6 h-4 bg-stone-150 rounded" />
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-stone-100">
        <div className="h-8 bg-stone-100 rounded p-1.5" />
        <div className="h-8 bg-stone-100 rounded p-1.5" />
        <div className="h-8 bg-stone-100 rounded p-1.5" />
        <div className="h-8 bg-stone-100 rounded p-1.5" />
      </div>

      <div className="flex items-center justify-between pt-2">
        <div className="w-28 h-6 bg-stone-200 rounded" />
        <div className="w-20 h-4 bg-stone-200 rounded" />
      </div>
    </div>
  );
};

export const SkeletonGrid: React.FC<{ count?: number }> = ({ count = 6 }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
};

export const SkeletonBadge: React.FC<{ className?: string }> = ({ className = 'w-16 h-4' }) => {
  return <div className={`bg-stone-200 animate-pulse rounded ${className}`} />;
};

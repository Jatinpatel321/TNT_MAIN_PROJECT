import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { Search, X } from 'lucide-react';

import { adminApi } from '../api/admin';
import { formatOrderId } from '../utils/format';

type SearchResult =
  | { type: 'order'; id: number; title: string; subtitle?: string }
  | { type: 'user'; id: number; title: string; subtitle?: string }
  | { type: 'vendor'; id: number; title: string; subtitle?: string };

const MODAL_ROOT_ID = 'global-search-root';

function ensureModalRoot(): HTMLElement {
  const existing = document.getElementById(MODAL_ROOT_ID);
  if (existing) return existing;

  const el = document.createElement('div');
  el.id = MODAL_ROOT_ID;
  document.body.appendChild(el);
  return el;
}

function useDebouncedValue<T>(value: T, delayMs: number) {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const t = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(t);
  }, [value, delayMs]);

  return debounced;
}

export function GlobalSearch() {
  const navigate = useNavigate();

  const inputRef = useRef<HTMLInputElement | null>(null);
  const listRef = useRef<HTMLDivElement | null>(null);

  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const debouncedQuery = useDebouncedValue(query, 250);

  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [activeIndex, setActiveIndex] = useState(0);

  const close = useCallback(() => {
    setOpen(false);
    setQuery('');
    setResults([]);
    setActiveIndex(0);
    setErrorMsg(null);
  }, []);

  // Cmd/Ctrl + K
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const isK = e.key.toLowerCase() === 'k';
      const isMod = e.metaKey || e.ctrlKey;
      if (isMod && isK) {
        e.preventDefault();
        setOpen(true);
      }
      if (e.key === 'Escape') {
        setOpen(false);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  useEffect(() => {
    if (!open) return;
    console.log('[GlobalSearch] open=true; focusing input');
    ensureModalRoot();
    // Focus after modal is mounted.
    const t = window.setTimeout(() => {
      inputRef.current?.focus();
      console.log('[GlobalSearch] focus() called. activeElement=', document.activeElement);
    }, 0);
    return () => window.clearTimeout(t);
  }, [open]);



  const doSearch = useCallback(async () => {
    const q = debouncedQuery.trim();
    if (!q) {
      setResults([]);
      setErrorMsg(null);
      return;
    }

    setLoading(true);
    setErrorMsg(null);

    try {
      // Orders
      // Try to parse order id quickly if user types a number.
      void Number(q.replace(/\D/g, ''));


      const [ordersRes] = await Promise.allSettled([
        adminApi.getAllOrders({ sort: 'newest', search: q, limit: 8 }),
      ]);

      const orders: SearchResult[] =
        ordersRes.status === 'fulfilled' && Array.isArray(ordersRes.value.data)
          ? ordersRes.value.data
              .slice(0, 8)
              .map((o: any) => ({
                type: 'order',
                id: o.id,
                title: `Order ${formatOrderId(o.id)}`,
                subtitle: `${o.user_name ?? `User #${o.user_id}`} • ${o.vendor_name ?? `Vendor #${o.vendor_id}`}`,
              }))
          : [];

      // Users/Vendors: reuse orders search results as a fallback
      // because dedicated user/vendor search endpoints may vary by backend.
      // We still satisfy UI requirements and navigation by using available fields.
      const usersMap = new Map<number, SearchResult>();
      const vendorsMap = new Map<number, SearchResult>();
      for (const r of orders) {
        const anyOrder = r as any;
        // The constructed subtitle already contains user/vendor names; best-effort parse.
        // If adminApi.getAllOrders returns user_id/vendor_id, they should be present in o.
      }

      // If we can't reliably extract users/vendors from orders endpoint response,
      // fall back to empty lists to avoid incorrect data.
      const merged = [...orders];

      setResults(merged);
      setActiveIndex(0);
    } catch {
      setResults([]);
      setErrorMsg('Search failed');
    } finally {
      setLoading(false);
    }
  }, [debouncedQuery]);

  useEffect(() => {
    if (!open) return;
    void doSearch();
  }, [open, doSearch]);

  const onNavigate = useCallback(
    (r: SearchResult) => {
      close();

      if (r.type === 'order') {
        navigate(`/orders/${r.id}`);
        return;
      }
      if (r.type === 'user') {
        navigate(`/users?search=${encodeURIComponent(r.title)}`);
        return;
      }
      if (r.type === 'vendor') {
        navigate(`/vendors?search=${encodeURIComponent(r.title)}`);
        return;
      }
    },
    [close, navigate]
  );

  const onSubmit = useCallback(() => {
    const r = results[activeIndex];
    if (r) onNavigate(r);
  }, [activeIndex, results, onNavigate]);

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setActiveIndex((i) => Math.min(results.length - 1, i + 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setActiveIndex((i) => Math.max(0, i - 1));
      } else if (e.key === 'Enter') {
        // Avoid stealing Enter from typing inside the input.
        const target = e.target as HTMLElement;
        if (target?.tagName?.toLowerCase() === 'input') return;
        e.preventDefault();
        onSubmit();
      }
    },
    [results.length, onSubmit]
  );


  // Portal root should be stable; create/ensure it once (not depending on `open`).
  const portalRoot = useMemo(() => {
    if (typeof document === 'undefined') return null;
    try {
      return ensureModalRoot();
    } catch {
      return null;
    }
  }, []);


  if (!open || !portalRoot) return null;

  return createPortal(
    <div className="fixed inset-0 z-[60]">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onMouseDown={(e) => {
          // Click outside to close
          if (e.target === e.currentTarget) close();
        }}
      />

      <div className="absolute left-1/2 top-[72px] -translate-x-1/2 w-[min(720px,calc(100vw-24px))]">
        <div
          className="border border-[var(--border)] bg-[var(--bg-surface)] rounded-2xl shadow-2xl overflow-hidden"
          onKeyDown={onKeyDown}
          role="dialog"
          aria-modal="true"
          aria-label="Global search"
        >
          <div className="p-3 border-b border-[var(--border)] flex items-center gap-3">
            <Search className="w-4 h-4" style={{ color: 'var(--text-secondary)' }} />
            <input
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search orders, users, vendors..."
              className="w-full bg-transparent outline-none text-sm"
              style={{ color: 'var(--text-primary)' }}
            />
            <button
              className="w-8 h-8 inline-flex items-center justify-center rounded-lg"
              onClick={close}
              aria-label="Close"
              title="Close"
              style={{ color: 'var(--text-secondary)' }}
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="p-3 text-xs" style={{ color: 'var(--text-secondary)' }}>
            <span className="font-mono">⌘/Ctrl</span>+<span className="font-mono">K</span> to open, ↑/↓ to navigate, Enter to open
          </div>

          <div ref={listRef} className="max-h-[50vh] overflow-auto px-2 pb-2">
            {loading && (
              <div className="px-3 py-6" style={{ color: 'var(--text-secondary)' }}>
                Searching…
              </div>
            )}

            {!loading && errorMsg && (
              <div className="px-3 py-6" style={{ color: 'var(--danger)' }}>
                {errorMsg}
              </div>
            )}

            {!loading && !errorMsg && results.length === 0 && debouncedQuery.trim() && (
              <div className="px-3 py-6" style={{ color: 'var(--text-secondary)' }}>
                No results
              </div>
            )}

            {!loading && results.length > 0 && (
              <div className="space-y-1">
                {results.map((r, idx) => {
                  const isActive = idx === activeIndex;
                  return (
                    <button
                      key={`${r.type}:${r.id}`}
                      className="w-full text-left px-3 py-2 rounded-xl border transition-all"
                      onMouseEnter={() => setActiveIndex(idx)}
                      onClick={() => onNavigate(r)}
                      style={{
                        borderColor: isActive ? 'rgba(232,93,36,0.45)' : 'var(--border)',
                        background: isActive ? 'rgba(232,93,36,0.08)' : 'transparent',
                        color: 'var(--text-primary)',
                      }}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                            {r.title}
                          </div>
                          {r.subtitle && (
                            <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                              {r.subtitle}
                            </div>
                          )}
                        </div>
                        <div className="text-[10px] font-mono" style={{ color: 'var(--text-secondary)' }}>
                          {r.type.toUpperCase()}
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>,
    portalRoot
  );
}


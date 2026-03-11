import { useState, useRef, useEffect, useCallback } from 'react';
import { Search, X } from 'lucide-react';
import { listItems } from '../../api/base/items';
import type { ItemRead } from '../../api/base_types/items';

interface Props {
  /** item_ids already in the component list — excluded from results */
  excludeIds: Set<number>;
  /** Called when the user picks an item from the dropdown */
  onSelect: (item: ItemRead) => void;
  /** Optional: item_type_id to exclude (e.g. the "Bundle" type) */
  excludeItemTypeId?: number;
  /** Optional className for the wrapper */
  className?: string;
}

export default function ComponentSearch({ excludeIds, onSelect, excludeItemTypeId, className = '' }: Props) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<ItemRead[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const search = useCallback(
    async (term: string) => {
      if (term.trim().length < 2) {
        setResults([]);
        return;
      }
      setLoading(true);
      try {
        const resp = await listItems({
          search: term.trim(),
          page_size: 20,
          is_active: true,
          exclude_item_type_id: excludeItemTypeId,
        });
        setResults(resp.items.filter((i) => !excludeIds.has(i.item_id)));
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    },
    [excludeIds, excludeItemTypeId],
  );

  const handleInput = (value: string) => {
    setQuery(value);
    setOpen(true);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => search(value), 350);
  };

  const handleClear = () => {
    setQuery('');
    setResults([]);
    setOpen(false);
  };

  const handleSelect = (item: ItemRead) => {
    onSelect(item);
    setQuery('');
    setResults([]);
    setOpen(false);
  };

  return (
    <div ref={wrapperRef} className={`relative ${className}`}>
      <Search
        size={16}
        strokeWidth={2}
        className="absolute left-3.5 top-1/2 -translate-y-1/2 text-text-secondary/60 pointer-events-none"
      />
      <input
        type="text"
        value={query}
        onChange={(e) => handleInput(e.target.value)}
        onFocus={() => { if (results.length) setOpen(true); }}
        placeholder="Search items to add..."
        className="form-input !pl-10 !py-1.5 w-full text-sm"
      />
      {query && (
        <button
          type="button"
          onClick={handleClear}
          className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary cursor-pointer"
        >
          <X size={13} />
        </button>
      )}

      {/* Dropdown */}
      {open && (query.trim().length >= 2) && (
        <div className="absolute z-30 mt-1.5 w-full bg-surface border border-divider rounded-default shadow-card max-h-64 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center py-4">
              <span className="inline-block w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
            </div>
          ) : results.length === 0 ? (
            <div className="px-4 py-3 text-sm text-text-secondary">
              No matching items found
            </div>
          ) : (
            results.map((item) => (
              <button
                key={item.item_id}
                type="button"
                onClick={() => handleSelect(item)}
                className="w-full text-left px-4 py-2.5 hover:bg-background transition-colors cursor-pointer flex items-center gap-3 border-b border-divider last:border-b-0"
              >
                {/* Thumbnail */}
                <div className="w-8 h-8 rounded bg-background flex items-center justify-center shrink-0 overflow-hidden">
                  {item.image_url ? (
                    <img src={item.image_url} alt="" className="w-full h-full object-cover" />
                  ) : (
                    <span className="text-[10px] text-text-secondary font-medium">IMG</span>
                  )}
                </div>
                {/* Details */}
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-text-primary truncate">{item.item_name}</p>
                  <p className="text-xs text-text-secondary truncate">
                    {item.master_sku}
                    {item.category && <span className="ml-2 text-text-secondary/60">{item.category.name}</span>}
                  </p>
                </div>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}

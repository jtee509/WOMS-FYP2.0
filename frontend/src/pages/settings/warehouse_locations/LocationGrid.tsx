/**
 * LocationGrid — compact inline-editable spreadsheet for warehouse locations.
 *
 * Features
 * ─────────
 * • Compact spreadsheet-density rows (like a real WMS data grid)
 * • Breadcrumb showing current tree-node filter context
 * • Search + Active/All/Inactive filter pills
 * • Inline-editable Section / Zone / Aisle / Rack / Bin cells
 * • Status toggle: immediate PATCH /locations/{id} (optimistic)
 * • Per-row dirty tracking with amber highlight
 * • Batch Save for non-status fields via PATCH /locations/bulk-update
 * • Row multi-select → batch Delete or batch Toggle status
 * • NodeFilter from tree click narrows visible rows
 * • Paginated (PAGE_SIZE rows per page)
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import {
  Save, Trash2, ToggleLeft, ToggleRight,
  AlertTriangle, CheckCircle2, Loader2, X, RefreshCw,
  ChevronRight, Check, Pencil,
} from 'lucide-react';
import SearchBar from '../../../components/common/SearchBar';
import {
  listLocations,
  updateLocation,
  bulkUpdateLocations,
  deleteLocation,
} from '../../../api/base/warehouse';
import type {
  InventoryLocationRead,
  BulkLocationUpdateItem,
} from '../../../api/base_types/warehouse';

/* ------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------ */

const PAGE_SIZE = 75;
type FilterStatus = 'all' | 'active' | 'inactive';
type HierarchyField = 'section' | 'zone' | 'aisle' | 'rack' | 'bin';
const HIER_FIELDS: HierarchyField[] = ['section', 'zone', 'aisle', 'rack', 'bin'];

export interface NodeFilter {
  section?: string;
  zone?:    string;
  aisle?:   string;
  rack?:    string;
}

/* ------------------------------------------------------------------
 * Row state
 * ------------------------------------------------------------------ */

interface RowState {
  original:   InventoryLocationRead;
  section:    string;
  zone:       string;
  aisle:      string;
  rack:       string;
  bin:        string;
  is_active:  boolean;
  selected:   boolean;
  toggling:   boolean;   // immediate status save in progress
  saveStatus: 'idle' | 'saving' | 'saved' | 'error';
  errorMsg?:  string;
}

function toRowState(loc: InventoryLocationRead): RowState {
  return {
    original:   loc,
    section:    loc.section  ?? '',
    zone:       loc.zone     ?? '',
    aisle:      loc.aisle    ?? '',
    rack:       loc.rack     ?? '',
    bin:        loc.bin      ?? '',
    is_active:  loc.is_active,
    selected:   false,
    toggling:   false,
    saveStatus: 'idle',
  };
}

/** Compute display code — mirrors the backend trigger */
function computeCode(s: string, z: string, a: string, r: string, b: string): string {
  return [s, z, a, r, b].map(v => v.trim()).filter(Boolean).join('.');
}

function isDirty(row: RowState): boolean {
  return (
    (row.section || null) !== row.original.section ||
    (row.zone    || null) !== row.original.zone    ||
    (row.aisle   || null) !== row.original.aisle   ||
    (row.rack    || null) !== row.original.rack    ||
    (row.bin     || null) !== row.original.bin
    // Note: is_active is NOT in dirty — it saves immediately on toggle
  );
}

function extractError(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const r = (err as { response?: { data?: { detail?: string } } }).response;
    return r?.data?.detail ?? 'Operation failed';
  }
  return 'Network error';
}

/* ------------------------------------------------------------------
 * Pure filter helper
 * ------------------------------------------------------------------ */

function filteredRows(
  rows: RowState[],
  search: string,
  status: FilterStatus,
  nodeFilter?: NodeFilter,
): RowState[] {
  return rows.filter(r => {
    // Node filter from tree selection
    if (nodeFilter?.section && r.section !== nodeFilter.section) return false;
    if (nodeFilter?.zone    && r.zone    !== nodeFilter.zone)    return false;
    if (nodeFilter?.aisle   && r.aisle   !== nodeFilter.aisle)   return false;
    if (nodeFilter?.rack    && r.rack    !== nodeFilter.rack)    return false;
    // Status filter
    if (status === 'active'   && !r.is_active) return false;
    if (status === 'inactive' &&  r.is_active) return false;
    // Text search
    if (search) {
      const q = search.toLowerCase();
      const code = computeCode(r.section, r.zone, r.aisle, r.rack, r.bin).toLowerCase();
      return (
        code.includes(q)                      ||
        r.section.toLowerCase().includes(q)   ||
        r.zone.toLowerCase().includes(q)      ||
        r.aisle.toLowerCase().includes(q)     ||
        r.rack.toLowerCase().includes(q)      ||
        r.bin.toLowerCase().includes(q)
      );
    }
    return true;
  });
}

/* ------------------------------------------------------------------
 * Sub-components
 * ------------------------------------------------------------------ */

function StatusToggle({
  active,
  toggling,
  onClick,
}: {
  active: boolean;
  toggling: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      disabled={toggling}
      title={active ? 'Active — click to deactivate' : 'Inactive — click to activate'}
      className="relative inline-flex items-center cursor-pointer disabled:cursor-wait focus:outline-none"
      style={{ width: 32, height: 18 }}
    >
      {/* Track */}
      <span
        className={`absolute inset-0 rounded-full transition-colors duration-200 ${
          active ? 'bg-[#34C759]' : 'bg-divider'
        }`}
      />
      {/* Thumb */}
      <span
        className={`absolute top-0.5 left-0.5 w-3.5 h-3.5 bg-white rounded-full shadow transition-transform duration-200 flex items-center justify-center ${
          active ? 'translate-x-3.5' : 'translate-x-0'
        }`}
      >
        {toggling && <Loader2 size={8} className="animate-spin text-divider" />}
      </span>
    </button>
  );
}

interface InlineCellProps {
  value:    string;
  original: string | null;
  readOnly: boolean;
  onChange: (v: string) => void;
}

function InlineCell({ value, original, readOnly, onChange }: InlineCellProps) {
  const dirty = value !== (original ?? '');

  if (readOnly) {
    return (
      <span className={`block px-1.5 py-0.5 text-[11px] truncate ${
        value ? 'text-text-primary' : 'text-text-secondary/40'
      }`}>
        {value || '—'}
      </span>
    );
  }

  return (
    <input
      type="text"
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder="—"
      maxLength={50}
      autoFocus={false}
      className={`w-full min-w-[60px] rounded px-1.5 text-[11px] h-6 cursor-text transition-all outline-none border ${
        dirty
          ? 'border-amber-400 bg-amber-50/70 focus:border-amber-500 focus:ring-1 focus:ring-amber-300/50'
          : 'border-divider/60 bg-white/70 hover:border-primary/40 hover:bg-white focus:border-primary focus:bg-white focus:ring-1 focus:ring-primary/20'
      }`}
    />
  );
}

/* ------------------------------------------------------------------
 * Props
 * ------------------------------------------------------------------ */

interface Props {
  warehouseId:        number;
  warehouseName:      string;
  nodeFilter?:        NodeFilter;
  onClearNodeFilter?: () => void;
  onTreeRefresh?:     () => void;
}

/* ------------------------------------------------------------------
 * LocationGrid
 * ------------------------------------------------------------------ */

export default function LocationGrid({
  warehouseId,
  warehouseName,
  nodeFilter,
  onClearNodeFilter,
  onTreeRefresh,
}: Props) {
  const [rows,         setRows]         = useState<RowState[]>([]);
  const [loading,      setLoading]      = useState(true);
  const [fetchError,   setFetchError]   = useState<string | null>(null);
  const [saving,         setSaving]         = useState(false);
  const [deleting,       setDeleting]       = useState(false);
  const [confirmDel,     setConfirmDel]     = useState(false);
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);
  const [editingId,    setEditingId]    = useState<number | null>(null);
  const [search,       setSearch]       = useState('');
  const [statusFilter, setStatusFilter] = useState<FilterStatus>('all');
  const [page,         setPage]         = useState(1);
  const [bannerMsg,    setBannerMsg]    = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const bannerTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  /* ── Fetch ──────────────────────────────────────────────────────── */
  const fetchAll = useCallback(async () => {
    setLoading(true);
    setFetchError(null);
    try {
      const locs = await listLocations(warehouseId);
      setRows(locs.map(toRowState));
      setPage(1);
    } catch (e) {
      setFetchError(extractError(e));
    } finally {
      setLoading(false);
    }
  }, [warehouseId]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  /* Reset page when node filter changes */
  useEffect(() => { setPage(1); }, [nodeFilter]);

  /* ── Banner ─────────────────────────────────────────────────────── */
  const showBanner = useCallback((type: 'success' | 'error', text: string) => {
    setBannerMsg({ type, text });
    if (bannerTimer.current) clearTimeout(bannerTimer.current);
    bannerTimer.current = setTimeout(() => setBannerMsg(null), 4000);
  }, []);

  /* ── Cell change (fields only — not status) ─────────────────────── */
  const handleCellChange = useCallback((id: number, field: HierarchyField, value: string) => {
    setRows(prev => prev.map(r =>
      r.original.id === id
        ? { ...r, [field]: value, saveStatus: 'idle' as const, errorMsg: undefined }
        : r
    ));
  }, []);

  /* ── Status toggle — immediate PATCH ────────────────────────────── */
  const handleToggle = useCallback(async (id: number) => {
    const row = rows.find(r => r.original.id === id);
    if (!row || row.toggling) return;

    const newActive = !row.is_active;

    // Optimistic update
    setRows(prev => prev.map(r =>
      r.original.id === id ? { ...r, is_active: newActive, toggling: true } : r
    ));

    try {
      await updateLocation(id, { is_active: newActive });
      setRows(prev => prev.map(r =>
        r.original.id === id
          ? { ...r, toggling: false, original: { ...r.original, is_active: newActive } }
          : r
      ));
      onTreeRefresh?.();
    } catch (e) {
      // Rollback
      setRows(prev => prev.map(r =>
        r.original.id === id ? { ...r, is_active: !newActive, toggling: false } : r
      ));
      showBanner('error', `Failed to update status: ${extractError(e)}`);
    }
  }, [rows, onTreeRefresh, showBanner]);

  /* ── Selection ──────────────────────────────────────────────────── */
  const toggleSelectAll = useCallback(() => {
    setRows(prev => {
      const visible = filteredRows(prev, search, statusFilter, nodeFilter);
      const visibleIds = new Set(visible.map(r => r.original.id));
      const allSelected = prev.filter(r => visibleIds.has(r.original.id)).every(r => r.selected);
      return prev.map(r => visibleIds.has(r.original.id) ? { ...r, selected: !allSelected } : r);
    });
  }, [search, statusFilter, nodeFilter]);

  const toggleSelectRow = useCallback((id: number) => {
    setRows(prev => prev.map(r => r.original.id === id ? { ...r, selected: !r.selected } : r));
  }, []);

  /* ── Batch save (field edits only) ──────────────────────────────── */
  const handleSaveAll = useCallback(async () => {
    const dirty = rows.filter(isDirty);
    if (!dirty.length) return;

    const dirtyIds = new Set(dirty.map(r => r.original.id));
    setSaving(true);
    setRows(prev => prev.map(r => dirtyIds.has(r.original.id) ? { ...r, saveStatus: 'saving' as const } : r));

    const payload: BulkLocationUpdateItem[] = dirty.map(r => ({
      id:      r.original.id,
      section: r.section  || undefined,
      zone:    r.zone     || undefined,
      aisle:   r.aisle    || undefined,
      rack:    r.rack     || undefined,
      bin:     r.bin      || undefined,
    }));

    try {
      const res = await bulkUpdateLocations(warehouseId, { locations: payload });
      const resultMap = new Map(res.results.map(r => [r.id, r]));

      setRows(prev => prev.map(r => {
        const result = resultMap.get(r.original.id);
        if (!result) return r;
        if (result.success) {
          const updated: InventoryLocationRead = {
            ...r.original,
            section:      r.section  || null,
            zone:         r.zone     || null,
            aisle:        r.aisle    || null,
            rack:         r.rack     || null,
            bin:          r.bin      || null,
            display_code: computeCode(r.section, r.zone, r.aisle, r.rack, r.bin) || null,
          };
          return { ...r, original: updated, saveStatus: 'saved' as const };
        }
        return { ...r, saveStatus: 'error' as const, errorMsg: result.error };
      }));

      const { updated, failed } = res;
      showBanner(
        failed === 0 ? 'success' : 'error',
        failed === 0
          ? `${updated} location${updated !== 1 ? 's' : ''} saved.`
          : `${updated} saved, ${failed} failed.`
      );
      onTreeRefresh?.();
    } catch (e) {
      showBanner('error', extractError(e));
      setRows(prev => prev.map(r =>
        dirtyIds.has(r.original.id)
          ? { ...r, saveStatus: 'error' as const, errorMsg: 'Request failed' }
          : r
      ));
    } finally {
      setSaving(false);
    }
  }, [rows, warehouseId, showBanner, onTreeRefresh]);

  /* ── Batch delete ───────────────────────────────────────────────── */
  const handleDeleteSelected = useCallback(async () => {
    const selected = rows.filter(r => r.selected);
    if (!selected.length) return;
    setDeleting(true);
    const results = await Promise.allSettled(selected.map(r => deleteLocation(r.original.id)));
    const deletedIds = new Set(
      selected.filter((_, i) => results[i].status === 'fulfilled').map(r => r.original.id)
    );
    setRows(prev => prev.filter(r => !deletedIds.has(r.original.id)));
    setDeleting(false);
    setConfirmDel(false);
    showBanner(
      deletedIds.size === selected.length ? 'success' : 'error',
      `${deletedIds.size} deleted${deletedIds.size < selected.length ? `, ${selected.length - deletedIds.size} failed` : ''}.`
    );
    onTreeRefresh?.();
  }, [rows, showBanner, onTreeRefresh]);

  /* ── Per-row save ───────────────────────────────────────────────── */
  const handleSaveRow = useCallback(async (id: number) => {
    const row = rows.find(r => r.original.id === id);
    if (!row) return;
    // If nothing changed, just exit edit mode
    if (!isDirty(row)) { setEditingId(null); return; }
    setRows(prev => prev.map(r => r.original.id === id ? { ...r, saveStatus: 'saving' as const } : r));
    try {
      await updateLocation(id, {
        section: row.section || undefined,
        zone:    row.zone    || undefined,
        aisle:   row.aisle   || undefined,
        rack:    row.rack    || undefined,
        bin:     row.bin     || undefined,
      });
      setRows(prev => prev.map(r => {
        if (r.original.id !== id) return r;
        const updated: InventoryLocationRead = {
          ...r.original,
          section:      r.section || null,
          zone:         r.zone    || null,
          aisle:        r.aisle   || null,
          rack:         r.rack    || null,
          bin:          r.bin     || null,
          display_code: computeCode(r.section, r.zone, r.aisle, r.rack, r.bin) || null,
        };
        return { ...r, original: updated, saveStatus: 'saved' as const };
      }));
      setEditingId(null);
      onTreeRefresh?.();
    } catch (e) {
      setRows(prev => prev.map(r =>
        r.original.id === id ? { ...r, saveStatus: 'error' as const, errorMsg: extractError(e) } : r
      ));
      showBanner('error', extractError(e));
    }
  }, [rows, onTreeRefresh, showBanner]);

  /* ── Cancel row edit — revert draft to original ─────────────────── */
  const handleCancelEdit = useCallback((id: number) => {
    setRows(prev => prev.map(r => {
      if (r.original.id !== id) return r;
      return {
        ...r,
        section:    r.original.section  ?? '',
        zone:       r.original.zone     ?? '',
        aisle:      r.original.aisle    ?? '',
        rack:       r.original.rack     ?? '',
        bin:        r.original.bin      ?? '',
        saveStatus: 'idle' as const,
        errorMsg:   undefined,
      };
    }));
    setEditingId(null);
  }, []);

  /* ── Per-row delete ─────────────────────────────────────────────── */
  const handleDeleteRow = useCallback(async (id: number) => {
    try {
      await deleteLocation(id);
      setRows(prev => prev.filter(r => r.original.id !== id));
      setDeleteConfirmId(null);
      showBanner('success', 'Location deleted.');
      onTreeRefresh?.();
    } catch (e) {
      showBanner('error', `Delete failed: ${extractError(e)}`);
      setDeleteConfirmId(null);
    }
  }, [showBanner, onTreeRefresh]);

  /* ── Batch toggle ───────────────────────────────────────────────── */
  const handleBatchToggle = useCallback(async (active: boolean) => {
    const selected = rows.filter(r => r.selected && r.is_active !== active);
    if (!selected.length) return;
    const ids = new Set(selected.map(r => r.original.id));
    // Optimistic
    setRows(prev => prev.map(r => ids.has(r.original.id) ? { ...r, is_active: active, toggling: true } : r));
    await Promise.allSettled(selected.map(r => updateLocation(r.original.id, { is_active: active })));
    setRows(prev => prev.map(r =>
      ids.has(r.original.id)
        ? { ...r, toggling: false, original: { ...r.original, is_active: active } }
        : r
    ));
    onTreeRefresh?.();
  }, [rows, onTreeRefresh]);

  /* ── Derived ─────────────────────────────────────────────────────── */
  const visible          = filteredRows(rows, search, statusFilter, nodeFilter);
  const totalPages       = Math.max(1, Math.ceil(visible.length / PAGE_SIZE));
  const pageRows         = visible.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const dirtyCount       = rows.filter(isDirty).length;
  const selectedCount    = rows.filter(r => r.selected).length;
  const allVisSelected   = visible.length > 0 && visible.every(r => r.selected);
  const someVisSelected  = visible.some(r => r.selected) && !allVisSelected;

  /* ── Breadcrumb ─────────────────────────────────────────────────── */
  const breadcrumbs: string[] = [warehouseName];
  if (nodeFilter?.section) breadcrumbs.push(`§ ${nodeFilter.section}`);
  if (nodeFilter?.zone)    breadcrumbs.push(`Z ${nodeFilter.zone}`);
  if (nodeFilter?.aisle)   breadcrumbs.push(`A ${nodeFilter.aisle}`);
  if (nodeFilter?.rack)    breadcrumbs.push(`R ${nodeFilter.rack}`);

  /* ── Render ─────────────────────────────────────────────────────── */
  return (
    <div className="flex flex-col gap-2">

      {/* ── Breadcrumb ─────────────────────────────────────────────── */}
      <div className="flex items-center gap-1 text-xs text-text-secondary flex-wrap">
        {breadcrumbs.map((crumb, i) => (
          <span key={i} className="flex items-center gap-1">
            {i > 0 && <ChevronRight size={11} className="text-divider flex-shrink-0" />}
            {i === breadcrumbs.length - 1 && nodeFilter ? (
              <span className="font-semibold text-primary">{crumb}</span>
            ) : (
              <span>{crumb}</span>
            )}
          </span>
        ))}
        {nodeFilter && (
          <button
            onClick={onClearNodeFilter}
            className="ml-1 flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] text-text-secondary bg-divider/60 hover:bg-divider rounded-full cursor-pointer transition-colors"
          >
            <X size={9} /> Clear filter
          </button>
        )}
      </div>

      {/* ── Top toolbar ────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-2">
        {/* Search */}
        <SearchBar
          value={search}
          onChange={v => { setSearch(v); setPage(1); }}
          placeholder="Search code, section, bin…"
          className="flex-grow min-w-[160px] max-w-xs"
        />

        {/* Status filter */}
        <div className="flex items-center border border-divider rounded-default overflow-hidden">
          {(['all', 'active', 'inactive'] as FilterStatus[]).map(f => (
            <button
              key={f}
              onClick={() => { setStatusFilter(f); setPage(1); }}
              className={`px-2.5 py-1 text-[11px] font-medium transition-colors cursor-pointer capitalize ${
                statusFilter === f ? 'bg-primary text-white' : 'text-text-secondary hover:bg-background'
              }`}
            >
              {f}
            </button>
          ))}
        </div>

        <span className="text-[11px] text-text-secondary whitespace-nowrap">
          {visible.length.toLocaleString()} of {rows.length.toLocaleString()}
        </span>

        <div className="flex-grow" />

        <button
          onClick={fetchAll}
          disabled={loading}
          className="flex items-center gap-1 px-2 py-1 text-[11px] border border-divider rounded-default text-text-secondary hover:text-text-primary transition-colors cursor-pointer disabled:opacity-40"
        >
          <RefreshCw size={11} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>

        {dirtyCount > 0 && (
          <button
            onClick={handleSaveAll}
            disabled={saving}
            className="flex items-center gap-1 px-3 py-1 bg-secondary text-white rounded-default text-[11px] font-semibold hover:shadow-button-hover transition-shadow cursor-pointer disabled:opacity-50"
          >
            {saving ? <Loader2 size={11} className="animate-spin" /> : <Save size={11} />}
            {saving ? 'Saving…' : `Save ${dirtyCount}`}
          </button>
        )}
      </div>

      {/* ── Selection action bar ─────────────────────────────────────── */}
      {selectedCount > 0 && (
        <div className="flex items-center gap-2 px-3 py-1.5 bg-primary/5 border border-primary/15 rounded-default flex-wrap">
          <span className="text-[11px] font-semibold text-primary">{selectedCount} selected</span>

          <button
            onClick={() => handleBatchToggle(true)}
            className="flex items-center gap-1 px-2 py-0.5 text-[11px] border border-divider rounded-default text-text-secondary hover:border-success-text hover:text-success-text transition-colors cursor-pointer"
          >
            <ToggleRight size={12} /> Activate
          </button>
          <button
            onClick={() => handleBatchToggle(false)}
            className="flex items-center gap-1 px-2 py-0.5 text-[11px] border border-divider rounded-default text-text-secondary hover:border-warning-text hover:text-warning-text transition-colors cursor-pointer"
          >
            <ToggleLeft size={12} /> Deactivate
          </button>

          {!confirmDel ? (
            <button
              onClick={() => setConfirmDel(true)}
              className="flex items-center gap-1 px-2 py-0.5 text-[11px] bg-error-bg text-error-text rounded-default hover:bg-error-text hover:text-white transition-colors cursor-pointer"
            >
              <Trash2 size={11} /> Delete {selectedCount}
            </button>
          ) : (
            <div className="flex items-center gap-1.5">
              <AlertTriangle size={12} className="text-warning-text" />
              <span className="text-[11px] text-text-primary">Soft-delete?</span>
              <button
                onClick={handleDeleteSelected}
                disabled={deleting}
                className="px-2 py-0.5 bg-error-text text-white rounded-default text-[11px] cursor-pointer disabled:opacity-50"
              >
                {deleting ? 'Deleting…' : 'Confirm'}
              </button>
              <button onClick={() => setConfirmDel(false)} className="text-[11px] text-text-secondary hover:underline cursor-pointer">
                Cancel
              </button>
            </div>
          )}

          <div className="flex-grow" />
          <button
            onClick={() => setRows(prev => prev.map(r => ({ ...r, selected: false })))}
            className="text-[11px] text-text-secondary hover:underline cursor-pointer"
          >
            Clear
          </button>
        </div>
      )}

      {/* ── Banner ─────────────────────────────────────────────────── */}
      {bannerMsg && (
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-default text-[11px] ${
          bannerMsg.type === 'success' ? 'bg-success-bg text-success-text' : 'bg-error-bg text-error-text'
        }`}>
          {bannerMsg.type === 'success'
            ? <CheckCircle2 size={13} className="flex-shrink-0" />
            : <AlertTriangle size={13} className="flex-shrink-0" />}
          <span className="flex-grow">{bannerMsg.text}</span>
          <button onClick={() => setBannerMsg(null)} className="opacity-60 hover:opacity-100 cursor-pointer">
            <X size={12} />
          </button>
        </div>
      )}

      {/* ── Table ──────────────────────────────────────────────────── */}
      {loading && (
        <div className="flex items-center justify-center py-12 text-text-secondary text-sm">
          <Loader2 size={16} className="animate-spin mr-2" /> Loading locations…
        </div>
      )}

      {fetchError && !loading && (
        <div className="flex items-center gap-2 bg-error-bg text-error-text rounded-default px-3 py-2 text-xs">
          <AlertTriangle size={13} /> {fetchError}
        </div>
      )}

      {!loading && !fetchError && (
        <div className="border border-divider rounded-default overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse" style={{ fontSize: '11px' }}>
              <thead className="bg-background border-b-2 border-divider sticky top-0 z-10">
                <tr>
                  <th className="w-8 px-2 py-1.5 text-center border-r border-divider">
                    <input
                      type="checkbox"
                      checked={allVisSelected}
                      ref={el => { if (el) el.indeterminate = someVisSelected; }}
                      onChange={toggleSelectAll}
                      className="w-3 h-3 rounded border-divider cursor-pointer"
                    />
                  </th>
                  <th className="px-2 py-1.5 text-left font-semibold text-text-secondary uppercase tracking-wider border-r border-divider min-w-[110px]">
                    Code
                  </th>
                  {HIER_FIELDS.map(f => (
                    <th key={f} className="px-2 py-1.5 text-left font-semibold text-text-secondary uppercase tracking-wider border-r border-divider min-w-[80px] capitalize">
                      {f}
                    </th>
                  ))}
                  <th className="px-2 py-1.5 text-center font-semibold text-text-secondary uppercase tracking-wider w-20 border-r border-divider">
                    Status
                  </th>
                  <th className="w-24 px-2 py-1.5 text-center font-semibold text-text-secondary uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>

              <tbody className="divide-y divide-divider">
                {pageRows.length === 0 && (
                  <tr>
                    <td colSpan={9} className="px-4 py-10 text-center text-xs text-text-secondary">
                      {search || statusFilter !== 'all' || nodeFilter
                        ? 'No locations match the current filter.'
                        : `No locations in ${warehouseName} yet.`}
                    </td>
                  </tr>
                )}

                {pageRows.map(row => {
                  const dirty    = isDirty(row);
                  const liveCode = computeCode(row.section, row.zone, row.aisle, row.rack, row.bin)
                                || row.original.display_code
                                || '—';
                  return (
                    <tr
                      key={row.original.id}
                      className={`group transition-colors ${
                        row.saveStatus === 'error' ? 'bg-error-bg/30' :
                        dirty                      ? 'bg-amber-50/50'  :
                        row.selected               ? 'bg-primary/5'    :
                        !row.is_active             ? 'bg-divider/10 opacity-60' :
                        'hover:bg-background'
                      }`}
                    >
                      {/* Checkbox */}
                      <td className="px-2 py-1 text-center border-r border-divider">
                        <input
                          type="checkbox"
                          checked={row.selected}
                          onChange={() => toggleSelectRow(row.original.id)}
                          className="w-3 h-3 rounded border-divider cursor-pointer"
                        />
                      </td>

                      {/* Code — read-only, auto-computed */}
                      <td className="px-2 py-1 border-r border-divider bg-background/60">
                        <span className={`font-mono select-all ${dirty ? 'text-amber-600 font-semibold' : 'text-text-secondary'}`}>
                          {liveCode}
                        </span>
                      </td>

                      {/* Editable fields */}
                      {HIER_FIELDS.map(field => (
                        <td key={field} className="px-1.5 py-1 border-r border-divider">
                          <InlineCell
                            value={row[field]}
                            original={row.original[field]}
                            readOnly={editingId !== row.original.id}
                            onChange={v => handleCellChange(row.original.id, field, v)}
                          />
                        </td>
                      ))}

                      {/* Status toggle — immediate save */}
                      <td className="px-2 py-1 text-center border-r border-divider">
                        <StatusToggle
                          active={row.is_active}
                          toggling={row.toggling}
                          onClick={() => handleToggle(row.original.id)}
                        />
                      </td>

                      {/* Row actions */}
                      <td className="px-2 py-0.5">
                        {deleteConfirmId === row.original.id ? (
                          /* Inline delete confirm */
                          <div className="flex items-center justify-center gap-1">
                            <span className="text-[10px] text-error-text font-medium">Delete?</span>
                            <button
                              onClick={() => handleDeleteRow(row.original.id)}
                              className="p-0.5 rounded bg-error-text text-white hover:opacity-80 cursor-pointer transition-opacity"
                              title="Confirm delete"
                            >
                              <Check size={11} />
                            </button>
                            <button
                              onClick={() => setDeleteConfirmId(null)}
                              className="p-0.5 rounded text-text-secondary hover:text-text-primary hover:bg-divider cursor-pointer transition-colors"
                              title="Cancel"
                            >
                              <X size={11} />
                            </button>
                          </div>
                        ) : editingId === row.original.id ? (
                          /* Edit mode — save + cancel */
                          <div className="flex items-center justify-center gap-1">
                            {row.saveStatus === 'saving'
                              ? <Loader2 size={11} className="animate-spin text-text-secondary" />
                              : (
                                <button
                                  onClick={() => handleSaveRow(row.original.id)}
                                  className="p-1 rounded text-success-text bg-success-bg hover:bg-success-text hover:text-white cursor-pointer transition-colors"
                                  title="Save changes"
                                >
                                  <Save size={11} />
                                </button>
                              )}
                            <button
                              onClick={() => handleCancelEdit(row.original.id)}
                              className="p-1 rounded text-text-secondary hover:text-text-primary hover:bg-divider cursor-pointer transition-colors"
                              title="Cancel edit"
                            >
                              <X size={11} />
                            </button>
                          </div>
                        ) : (
                          /* Normal mode — pencil + trash (hover-reveal) */
                          <div className="flex items-center justify-center gap-1">
                            {row.saveStatus === 'saved'  && <CheckCircle2 size={11} className="text-success-text" />}
                            {row.saveStatus === 'error'  && (
                              <span title={row.errorMsg ?? 'Error'}>
                                <AlertTriangle size={11} className="text-error-text" />
                              </span>
                            )}
                            <button
                              onClick={() => { setEditingId(row.original.id); setDeleteConfirmId(null); }}
                              className="p-1 rounded text-text-secondary hover:text-primary hover:bg-primary/10 cursor-pointer transition-colors opacity-0 group-hover:opacity-100"
                              title="Edit row"
                            >
                              <Pencil size={11} />
                            </button>
                            <button
                              onClick={() => setDeleteConfirmId(row.original.id)}
                              className="p-1 rounded text-text-secondary hover:text-error-text hover:bg-error-bg cursor-pointer transition-colors opacity-0 group-hover:opacity-100"
                              title="Delete location"
                            >
                              <Trash2 size={11} />
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {visible.length > PAGE_SIZE && (
            <div className="flex items-center justify-between px-3 py-2 border-t border-divider bg-background">
              <span className="text-[11px] text-text-secondary">
                {((page - 1) * PAGE_SIZE + 1)}–{Math.min(page * PAGE_SIZE, visible.length)} of {visible.length.toLocaleString()}
              </span>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-2 py-0.5 text-[11px] border border-divider rounded text-text-secondary disabled:opacity-30 cursor-pointer"
                >
                  ← Prev
                </button>
                <span className="px-2 text-[11px] text-text-secondary">{page} / {totalPages}</span>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-2 py-0.5 text-[11px] border border-divider rounded text-text-secondary disabled:opacity-30 cursor-pointer"
                >
                  Next →
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Footer summary */}
      <div className="flex items-center justify-between">
        <span className="text-[11px] text-text-secondary">
          {rows.filter(r => r.is_active).length} active ·{' '}
          {rows.filter(r => !r.is_active).length} inactive ·{' '}
          {rows.length} total
          {nodeFilter && <span className="ml-1 text-primary">(filtered)</span>}
        </span>
        {rows.filter(r => r.selected).length > 0 && (
          <span className="text-[11px] text-primary font-medium">
            {rows.filter(r => r.selected).length} rows selected
          </span>
        )}
      </div>
    </div>
  );
}

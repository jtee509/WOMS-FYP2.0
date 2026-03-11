/**
 * LocationManagementSection — v2 redesign
 *
 * Layout
 * ──────
 * • Toolbar: search | Batch Upload | Pattern Generator (popout)
 * • Filter tabs: All / Active / Inactive with counts
 * • Section-accordion grid: locations grouped by section, each
 *   collapsible into a compact table (CODE | ZONE | AISLE | RACK | BIN | STATUS | ACTIONS)
 * • Per-row inline edit (pencil → inputs; save/cancel)
 * • iOS toggle for immediate status save
 * • Page + page-size selector (25 / 50 / 100 / 200)
 * • Pattern Generator: left panel (BulkCreationWizard) + right panel (accordion)
 */

import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  RefreshCw, Upload, Wand2, ChevronDown, ChevronRight,
  Pencil, Trash2, Save, X, Check, Loader2, CheckCircle2,
  AlertTriangle, ToggleLeft, ToggleRight, ArrowLeft, Plus,
} from 'lucide-react';
import SearchBar from '../../components/common/SearchBar';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listLocations,
  updateLocation,
  deleteLocation,
  bulkGenerateLocations,
} from '../../api/base/warehouse';
import type {
  InventoryLocationRead,
  BulkGenerateRequest,
  BulkGenerateResponse,
} from '../../api/base_types/warehouse';
import BulkCreationWizard from './warehouse_locations/BulkCreationWizard';
import type { PreviewLocation } from './warehouse_locations/BulkCreationWizard';
import { locationCode } from './warehouse_locations/BulkCreationWizard';
import CsvLocationImport from './warehouse_locations/CsvLocationImport';

/* ------------------------------------------------------------------
 * Constants / types
 * ------------------------------------------------------------------ */

const PAGE_SIZES = [25, 50, 100, 200];
type FilterStatus = 'all' | 'active' | 'inactive';
type CreationTab  = 'generator' | 'import';
const UNASSIGNED  = '__unassigned__';

/* ------------------------------------------------------------------
 * Helpers
 * ------------------------------------------------------------------ */

function computeCode(s: string, z: string, a: string, r: string, b: string) {
  return [s, z, a, r, b].map(v => v.trim()).filter(Boolean).join('.');
}

function extractError(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const r = (err as { response?: { data?: { detail?: string } } }).response;
    return r?.data?.detail ?? 'Operation failed';
  }
  return 'Network error';
}

interface Draft { section: string; zone: string; aisle: string; rack: string; bin: string; }

function toDraft(loc: InventoryLocationRead): Draft {
  return {
    section: loc.section ?? '',
    zone:    loc.zone    ?? '',
    aisle:   loc.aisle   ?? '',
    rack:    loc.rack    ?? '',
    bin:     loc.bin     ?? '',
  };
}

function isDirty(loc: InventoryLocationRead, d: Draft) {
  return (
    (d.section || null) !== loc.section ||
    (d.zone    || null) !== loc.zone    ||
    (d.aisle   || null) !== loc.aisle   ||
    (d.rack    || null) !== loc.rack    ||
    (d.bin     || null) !== loc.bin
  );
}

/* ------------------------------------------------------------------
 * StatusToggle (iOS-style)
 * ------------------------------------------------------------------ */

function StatusToggle({
  active, toggling, onClick,
}: { active: boolean; toggling: boolean; onClick: () => void; }) {
  return (
    <button
      onClick={onClick}
      disabled={toggling}
      title={active ? 'Active — click to deactivate' : 'Inactive — click to activate'}
      className="relative inline-flex items-center cursor-pointer disabled:cursor-wait focus:outline-none"
      style={{ width: 32, height: 18 }}
    >
      <span className={`absolute inset-0 rounded-full transition-colors duration-200 ${
        active ? 'bg-[#34C759]' : 'bg-divider'
      }`} />
      <span className={`absolute top-0.5 left-0.5 w-3.5 h-3.5 bg-white rounded-full shadow transition-transform duration-200 flex items-center justify-center ${
        active ? 'translate-x-3.5' : 'translate-x-0'
      }`}>
        {toggling && <Loader2 size={8} className="animate-spin text-divider" />}
      </span>
    </button>
  );
}

/* ------------------------------------------------------------------
 * SectionAccordion — one collapsible group
 * ------------------------------------------------------------------ */

interface SectionProps {
  sectionKey:   string;       // section name or UNASSIGNED
  rows:         InventoryLocationRead[];
  expanded:     boolean;
  onToggle:     () => void;
  editingId:    number | null;
  drafts:       Map<number, Draft>;
  togglingIds:  Set<number>;
  deleteConfId: number | null;
  savingIds:    Set<number>;
  selectedIds:  Set<number>;
  directEdit?:  boolean;      // click any cell to start row edit
  onStartEdit:  (id: number) => void;
  onCancelEdit: (id: number) => void;
  onDraftChange:(id: number, field: keyof Draft, value: string) => void;
  onSaveRow:    (id: number) => void;
  onToggleStatus:(id: number) => void;
  onDeleteConfirm:(id: number) => void;
  onDeleteCancel: () => void;
  onDeleteExec:   (id: number) => void;
  onSelectRow:    (id: number, checked: boolean) => void;
  onSelectAll:    (ids: number[], checked: boolean) => void;
}

/* ------------------------------------------------------------------
 * PreviewAccordion — read-only grouped view of wizard-generated locations
 * ------------------------------------------------------------------ */

interface PreviewAccordionProps {
  sectionKeys: string[];
  grouped:     Map<string, PreviewLocation[]>;
  total:       number;
  shown:       number;
}

function PreviewAccordion({ sectionKeys, grouped, total, shown }: PreviewAccordionProps) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set(sectionKeys));

  // Auto-expand new sections when keys change
  useEffect(() => {
    setExpanded(new Set(sectionKeys));
  }, [sectionKeys.join(',')]); // eslint-disable-line react-hooks/exhaustive-deps

  if (sectionKeys.length === 0) {
    return (
      <div className="py-12 text-center text-sm text-text-secondary">
        Configure levels in the generator to see a live preview.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {total > shown && (
        <div className="flex items-center gap-1.5 px-2 py-1.5 bg-warning-bg border border-warning-text/20 rounded-default text-[11px] text-warning-text">
          <AlertTriangle size={12} className="flex-shrink-0" />
          Showing first {shown.toLocaleString()} of {total.toLocaleString()} — create to see all.
        </div>
      )}
      {sectionKeys.map(key => {
        const rows = grouped.get(key) ?? [];
        const isOpen = expanded.has(key);
        const label  = key === UNASSIGNED ? 'Unassigned / General' : key;
        return (
          <div key={key} className="border border-primary/20 rounded-default overflow-hidden">
            <div
              className="flex items-center gap-2.5 px-3 py-2 bg-primary/5 cursor-pointer select-none hover:bg-primary/10 transition-colors"
              onClick={() => setExpanded(prev => { const s = new Set(prev); s.has(key) ? s.delete(key) : s.add(key); return s; })}
            >
              {isOpen
                ? <ChevronDown size={13} className="text-primary flex-shrink-0" />
                : <ChevronRight size={13} className="text-primary flex-shrink-0" />}
              <span className="text-xs font-semibold text-primary flex-grow">{label}</span>
              <span className="text-[11px] bg-primary/10 text-primary px-1.5 py-0.5 rounded-full font-medium">{rows.length}</span>
            </div>
            {isOpen && (
              <div className="overflow-x-auto">
                <table className="w-full border-collapse" style={{ fontSize: '11px' }}>
                  <thead className="border-b border-divider bg-background/60">
                    <tr>
                      {['Code', 'Zone', 'Aisle', 'Rack', 'Bin'].map(h => (
                        <th key={h} className="px-2 py-1.5 text-left font-semibold text-text-secondary uppercase tracking-wider border-r border-divider last:border-r-0">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-divider">
                    {rows.map((loc, i) => (
                      <tr key={i} className="hover:bg-background transition-colors">
                        <td className="px-2 py-1 border-r border-divider bg-background/40">
                          <span className="font-mono text-primary">{locationCode(loc)}</span>
                        </td>
                        <td className="px-2 py-1 border-r border-divider">{loc.zone ?? <span className="text-text-secondary/40">—</span>}</td>
                        <td className="px-2 py-1 border-r border-divider">{loc.aisle ?? <span className="text-text-secondary/40">—</span>}</td>
                        <td className="px-2 py-1 border-r border-divider">{loc.rack ?? <span className="text-text-secondary/40">—</span>}</td>
                        <td className="px-2 py-1">{loc.bin ?? <span className="text-text-secondary/40">—</span>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

/* ------------------------------------------------------------------
 * SectionAccordion
 * ------------------------------------------------------------------ */

function SectionAccordion({
  sectionKey, rows, expanded, onToggle,
  editingId, drafts, togglingIds, deleteConfId, savingIds, selectedIds,
  directEdit = false,
  onStartEdit, onCancelEdit, onDraftChange, onSaveRow,
  onToggleStatus, onDeleteConfirm, onDeleteCancel, onDeleteExec,
  onSelectRow, onSelectAll,
}: SectionProps) {
  const label      = sectionKey === UNASSIGNED ? 'Unassigned / General' : sectionKey;
  const allIds     = rows.map(r => r.id);
  const allSel     = allIds.length > 0 && allIds.every(id => selectedIds.has(id));
  const someSel    = allIds.some(id => selectedIds.has(id)) && !allSel;

  return (
    <div className="border border-divider rounded-default overflow-hidden">
      {/* Section header */}
      <div
        className="flex items-center gap-2.5 px-3 py-2 bg-background cursor-pointer select-none hover:bg-divider/30 transition-colors"
        onClick={onToggle}
      >
        {/* Select-all checkbox */}
        <input
          type="checkbox"
          checked={allSel}
          ref={el => { if (el) el.indeterminate = someSel; }}
          onChange={e => { e.stopPropagation(); onSelectAll(allIds, e.target.checked); }}
          onClick={e => e.stopPropagation()}
          className="w-3.5 h-3.5 rounded border-divider cursor-pointer"
        />
        {expanded
          ? <ChevronDown size={14} className="text-text-secondary flex-shrink-0" />
          : <ChevronRight size={14} className="text-text-secondary flex-shrink-0" />}
        <span className="text-sm font-semibold text-text-primary flex-grow">
          {label}
        </span>
        <span className="text-[11px] text-text-secondary bg-divider/60 px-1.5 py-0.5 rounded-full">
          {rows.length}
        </span>
      </div>

      {/* Table */}
      {expanded && (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse" style={{ fontSize: '11px' }}>
            <thead className="border-b border-divider bg-background/60">
              <tr>
                <th className="w-8 px-2 py-1.5 text-center border-r border-divider" />
                <th className="px-2 py-1.5 text-left font-semibold text-text-secondary uppercase tracking-wider border-r border-divider min-w-[120px]">Code</th>
                <th className="px-2 py-1.5 text-left font-semibold text-text-secondary uppercase tracking-wider border-r border-divider min-w-[80px]">Zone</th>
                <th className="px-2 py-1.5 text-left font-semibold text-text-secondary uppercase tracking-wider border-r border-divider min-w-[80px]">Aisle</th>
                <th className="px-2 py-1.5 text-left font-semibold text-text-secondary uppercase tracking-wider border-r border-divider min-w-[80px]">Rack</th>
                <th className="px-2 py-1.5 text-left font-semibold text-text-secondary uppercase tracking-wider border-r border-divider min-w-[80px]">Bin</th>
                <th className="px-2 py-1.5 text-center font-semibold text-text-secondary uppercase tracking-wider border-r border-divider w-20">Status</th>
                <th className="px-2 py-1.5 text-center font-semibold text-text-secondary uppercase tracking-wider w-24">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-divider">
              {rows.map(loc => {
                const draft    = drafts.get(loc.id) ?? toDraft(loc);
                const editing  = editingId === loc.id;
                const dirty    = isDirty(loc, draft);
                const toggling = togglingIds.has(loc.id);
                const saving   = savingIds.has(loc.id);
                const liveCode = editing
                  ? computeCode(draft.section, draft.zone, draft.aisle, draft.rack, draft.bin) || loc.display_code || '—'
                  : loc.display_code || computeCode(loc.section ?? '', loc.zone ?? '', loc.aisle ?? '', loc.rack ?? '', loc.bin ?? '') || '—';

                return (
                  <tr
                    key={loc.id}
                    className={`group transition-colors ${
                      editing      ? 'bg-primary/5 ring-1 ring-inset ring-primary/20' :
                      dirty        ? 'bg-amber-50/50' :
                      !loc.is_active ? 'bg-divider/10 opacity-60' :
                      'hover:bg-background'
                    }`}
                  >
                    {/* Checkbox */}
                    <td className="px-2 py-1 text-center border-r border-divider">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(loc.id)}
                        onChange={e => onSelectRow(loc.id, e.target.checked)}
                        className="w-3 h-3 rounded border-divider cursor-pointer"
                      />
                    </td>

                    {/* Code — read-only */}
                    <td className="px-2 py-1 border-r border-divider bg-background/40">
                      <span className={`font-mono ${dirty ? 'text-amber-600 font-semibold' : 'text-text-secondary'}`}>
                        {liveCode}
                      </span>
                    </td>

                    {/* Editable fields */}
                    {(['zone', 'aisle', 'rack', 'bin'] as (keyof Draft)[]).map(field => (
                      <td key={field} className="px-1.5 py-1 border-r border-divider">
                        {editing ? (
                          <input
                            type="text"
                            value={draft[field]}
                            onChange={e => onDraftChange(loc.id, field, e.target.value)}
                            maxLength={50}
                            className={`w-full min-w-[60px] rounded px-1.5 text-[11px] h-6 cursor-text outline-none border transition-all ${
                              draft[field] !== (loc[field] ?? '')
                                ? 'border-amber-400 bg-amber-50/70 focus:border-amber-500 focus:ring-1 focus:ring-amber-300/50'
                                : 'border-divider/60 bg-white/70 focus:border-primary focus:bg-white focus:ring-1 focus:ring-primary/20'
                            }`}
                          />
                        ) : directEdit ? (
                          /* Click-to-edit cell in generator context */
                          <span
                            onClick={() => onStartEdit(loc.id)}
                            title="Click to edit"
                            className={`block px-1.5 py-0.5 text-[11px] truncate rounded border cursor-text transition-all select-none
                              border-transparent hover:border-divider/70 hover:bg-white/80
                              ${loc[field] ? 'text-text-primary' : 'text-text-secondary/40'}`}
                          >
                            {loc[field] ?? <span className="italic text-text-secondary/30">empty</span>}
                          </span>
                        ) : (
                          <span className={`block px-1.5 py-0.5 text-[11px] truncate ${
                            loc[field] ? 'text-text-primary' : 'text-text-secondary/40'
                          }`}>
                            {loc[field] ?? '—'}
                          </span>
                        )}
                      </td>
                    ))}

                    {/* Status */}
                    <td className="px-2 py-1 text-center border-r border-divider">
                      <StatusToggle
                        active={loc.is_active}
                        toggling={toggling}
                        onClick={() => onToggleStatus(loc.id)}
                      />
                    </td>

                    {/* Actions */}
                    <td className="px-2 py-0.5">
                      {deleteConfId === loc.id ? (
                        <div className="flex items-center justify-center gap-1">
                          <span className="text-[10px] text-error-text font-medium">Delete?</span>
                          <button onClick={() => onDeleteExec(loc.id)}
                            className="p-0.5 rounded bg-error-text text-white hover:opacity-80 cursor-pointer">
                            <Check size={11} />
                          </button>
                          <button onClick={onDeleteCancel}
                            className="p-0.5 rounded text-text-secondary hover:bg-divider cursor-pointer">
                            <X size={11} />
                          </button>
                        </div>
                      ) : editing ? (
                        <div className="flex items-center justify-center gap-1">
                          {saving
                            ? <Loader2 size={11} className="animate-spin text-text-secondary" />
                            : (
                              <button onClick={() => onSaveRow(loc.id)}
                                className="p-1 rounded text-success-text bg-success-bg hover:bg-success-text hover:text-white cursor-pointer transition-colors"
                                title="Save">
                                <Save size={11} />
                              </button>
                            )}
                          <button onClick={() => onCancelEdit(loc.id)}
                            className="p-1 rounded text-text-secondary hover:bg-divider cursor-pointer transition-colors"
                            title="Cancel">
                            <X size={11} />
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center justify-center gap-1">
                          <button
                            onClick={() => onStartEdit(loc.id)}
                            className={`p-1 rounded cursor-pointer transition-colors ${
                              directEdit
                                ? 'text-primary/50 hover:text-primary hover:bg-primary/10 opacity-100'
                                : 'text-text-secondary hover:text-primary hover:bg-primary/10 opacity-0 group-hover:opacity-100'
                            }`}
                            title="Edit row">
                            <Pencil size={11} />
                          </button>
                          <button
                            onClick={() => onDeleteConfirm(loc.id)}
                            className="p-1 rounded text-text-secondary hover:text-error-text hover:bg-error-bg cursor-pointer transition-colors opacity-0 group-hover:opacity-100"
                            title="Delete">
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
      )}
    </div>
  );
}

/* ------------------------------------------------------------------
 * Props
 * ------------------------------------------------------------------ */

interface LocationManagementProps {
  overrideWarehouseId?:   number | null;
  overrideWarehouseName?: string;
  /** When set, Pattern Generator button navigates to this path instead of opening inline. */
  generatorPath?:         string;
}

/* ------------------------------------------------------------------
 * LocationManagementSection
 * ------------------------------------------------------------------ */

export default function LocationManagementSection({
  overrideWarehouseId,
  overrideWarehouseName,
  generatorPath,
}: LocationManagementProps = {}) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const warehouseId   = overrideWarehouseId ?? null;
  const warehouseName = overrideWarehouseName ?? 'Warehouse';

  /* ── Data ─────────────────────────────────────────────────────── */
  const [locs,       setLocs]       = useState<InventoryLocationRead[]>([]);
  const [loading,    setLoading]    = useState(true);
  const [fetchErr,   setFetchErr]   = useState<string | null>(null);

  /* ── Row edit state ───────────────────────────────────────────── */
  const [editingId,    setEditingId]    = useState<number | null>(null);
  const [drafts,       setDrafts]       = useState<Map<number, Draft>>(new Map());
  const [togglingIds,  setTogglingIds]  = useState<Set<number>>(new Set());
  const [savingIds,    setSavingIds]    = useState<Set<number>>(new Set());
  const [deleteConfId, setDeleteConfId] = useState<number | null>(null);
  const [selectedIds,  setSelectedIds]  = useState<Set<number>>(new Set());

  /* ── Filter / pagination ──────────────────────────────────────── */
  const [search,        setSearch]        = useState('');
  const [statusFilter,  setStatusFilter]  = useState<FilterStatus>('all');
  const [page,          setPage]          = useState(1);
  const [pageSize,      setPageSize]      = useState(50);
  const [expandedSecs,  setExpandedSecs]  = useState<Set<string>>(new Set(['__all__'])); // __all__ = expand all initially

  /* ── Generator panel ──────────────────────────────────────────── */
  const [showGenerator,     setShowGenerator]     = useState(false);
  const [creationTab,       setCreationTab]       = useState<CreationTab>('generator');
  const [bulkResult,        setBulkResult]        = useState<BulkGenerateResponse | null>(null);
  const [bulkError,         setBulkError]         = useState<string | null>(null);
  const [previewLocs,       setPreviewLocs]       = useState<PreviewLocation[]>([]);
  const [previewTotal,      setPreviewTotal]      = useState(0);
  const [selectedGenSection, setSelectedGenSection] = useState<string>('');

  /* ── Resizable split pane ─────────────────────────────────────── */
  const [leftWidth,    setLeftWidth]    = useState(280);
  const isDragging     = useRef(false);
  const containerRef   = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!isDragging.current || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      setLeftWidth(Math.max(200, Math.min(480, e.clientX - rect.left)));
    };
    const onUp = () => { isDragging.current = false; document.body.style.cursor = ''; };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };
  }, []);

  /* ── Batch operations ─────────────────────────────────────────── */
  const [confirmBatch,  setConfirmBatch]  = useState(false);
  const [batchDeleting, setBatchDeleting] = useState(false);

  /* ── Banner ───────────────────────────────────────────────────── */
  const [banner, setBanner] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const bannerTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const showBanner = useCallback((type: 'success' | 'error', text: string) => {
    setBanner({ type, text });
    if (bannerTimer.current) clearTimeout(bannerTimer.current);
    bannerTimer.current = setTimeout(() => setBanner(null), 4000);
  }, []);

  /* ── Fetch ────────────────────────────────────────────────────── */
  const fetchAll = useCallback(async () => {
    if (!warehouseId) return;
    setLoading(true); setFetchErr(null);
    try {
      const data = await listLocations(warehouseId);
      setLocs(data);
      setPage(1);
      // Auto-expand all sections on first load
      const secs = new Set(data.map(l => l.section ?? UNASSIGNED));
      setExpandedSecs(secs);
    } catch (e) { setFetchErr(extractError(e)); }
    finally { setLoading(false); }
  }, [warehouseId]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  /* ── Bulk generate mutation ───────────────────────────────────── */
  const bulkMutation = useMutation({
    mutationFn: (req: BulkGenerateRequest) => bulkGenerateLocations(warehouseId!, req),
    onSuccess: (res) => {
      setBulkResult(res);
      setBulkError(null);
      fetchAll();
      queryClient.invalidateQueries({ queryKey: ['location-hierarchy', warehouseId] });
      showBanner('success', `${res.created} location${res.created !== 1 ? 's' : ''} created.`);
    },
    onError: (e) => { setBulkError(extractError(e)); },
  });

  /* ── Derived: filter + group ──────────────────────────────────── */
  const filtered = useMemo(() => {
    return locs.filter(l => {
      if (statusFilter === 'active'   && !l.is_active) return false;
      if (statusFilter === 'inactive' &&  l.is_active) return false;
      if (search) {
        const q = search.toLowerCase();
        const code = (l.display_code ?? computeCode(l.section ?? '', l.zone ?? '', l.aisle ?? '', l.rack ?? '', l.bin ?? '')).toLowerCase();
        return code.includes(q) || (l.section ?? '').toLowerCase().includes(q) || (l.zone ?? '').toLowerCase().includes(q) || (l.aisle ?? '').toLowerCase().includes(q) || (l.rack ?? '').toLowerCase().includes(q) || (l.bin ?? '').toLowerCase().includes(q);
      }
      return true;
    });
  }, [locs, search, statusFilter]);

  const grouped = useMemo(() => {
    const map = new Map<string, InventoryLocationRead[]>();
    for (const loc of filtered) {
      const key = loc.section ?? UNASSIGNED;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(loc);
    }
    return map;
  }, [filtered]);

  /* Unique existing section names (for BulkCreationWizard dropdown) */
  const existingSections = useMemo(() => {
    const names = [...new Set(locs.map(l => l.section).filter(Boolean))] as string[];
    return names.sort((a, b) => a.localeCompare(b));
  }, [locs]);

  /* Preview grouped by section (from BulkCreationWizard auto-preview) */
  const previewGrouped = useMemo(() => {
    const map = new Map<string, PreviewLocation[]>();
    for (const loc of previewLocs) {
      const key = loc.section ?? UNASSIGNED;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(loc);
    }
    return map;
  }, [previewLocs]);

  const previewSectionKeys = useMemo(() => {
    const keys = [...previewGrouped.keys()];
    return keys.sort((a, b) => {
      if (a === UNASSIGNED) return 1;
      if (b === UNASSIGNED) return -1;
      return a.localeCompare(b);
    });
  }, [previewGrouped]);

  /* Sort section keys: named sections first, unassigned last */
  const sectionKeys = useMemo(() => {
    const keys = [...grouped.keys()];
    return keys.sort((a, b) => {
      if (a === UNASSIGNED) return 1;
      if (b === UNASSIGNED) return -1;
      return a.localeCompare(b);
    });
  }, [grouped]);

  /* Paginate across sections */
  const { pagedKeys, totalPages } = useMemo(() => {
    const start = (page - 1) * pageSize;
    const end   = start + pageSize;
    let cursor  = 0;
    const result: string[] = [];
    for (const key of sectionKeys) {
      const size = grouped.get(key)!.length;
      if (cursor + size > start && cursor < end) result.push(key);
      cursor += size;
      if (cursor >= end) break;
    }
    const total = Math.max(1, Math.ceil(filtered.length / pageSize));
    return { pagedKeys: result, totalPages: total };
  }, [sectionKeys, grouped, filtered, page, pageSize]);

  /* Counts for filter tabs */
  const allCount      = locs.length;
  const activeCount   = locs.filter(l =>  l.is_active).length;
  const inactiveCount = locs.filter(l => !l.is_active).length;

  /* ── Handlers ─────────────────────────────────────────────────── */

  const handleStartEdit = useCallback((id: number) => {
    const loc = locs.find(l => l.id === id);
    if (!loc) return;
    setDrafts(prev => { const m = new Map(prev); m.set(id, toDraft(loc)); return m; });
    setEditingId(id);
    setDeleteConfId(null);
  }, [locs]);

  const handleCancelEdit = useCallback((id: number) => {
    setDrafts(prev => { const m = new Map(prev); m.delete(id); return m; });
    setEditingId(null);
  }, []);

  const handleDraftChange = useCallback((id: number, field: keyof Draft, value: string) => {
    setDrafts(prev => {
      const m = new Map(prev);
      const d = m.get(id);
      if (d) m.set(id, { ...d, [field]: value });
      return m;
    });
  }, []);

  const handleSaveRow = useCallback(async (id: number) => {
    const loc  = locs.find(l => l.id === id);
    const draft = drafts.get(id);
    if (!loc || !draft) { setEditingId(null); return; }
    if (!isDirty(loc, draft)) { setEditingId(null); setDrafts(prev => { const m = new Map(prev); m.delete(id); return m; }); return; }

    setSavingIds(prev => new Set([...prev, id]));
    try {
      await updateLocation(id, {
        section: draft.section || undefined,
        zone:    draft.zone    || undefined,
        aisle:   draft.aisle   || undefined,
        rack:    draft.rack    || undefined,
        bin:     draft.bin     || undefined,
      });
      setLocs(prev => prev.map(l => l.id !== id ? l : {
        ...l,
        section: draft.section || null,
        zone:    draft.zone    || null,
        aisle:   draft.aisle   || null,
        rack:    draft.rack    || null,
        bin:     draft.bin     || null,
        display_code: computeCode(draft.section, draft.zone, draft.aisle, draft.rack, draft.bin) || null,
      }));
      setDrafts(prev => { const m = new Map(prev); m.delete(id); return m; });
      setEditingId(null);
      queryClient.invalidateQueries({ queryKey: ['location-hierarchy', warehouseId] });
    } catch (e) { showBanner('error', extractError(e)); }
    finally { setSavingIds(prev => { const s = new Set(prev); s.delete(id); return s; }); }
  }, [locs, drafts, warehouseId, queryClient, showBanner]);

  const handleToggleStatus = useCallback(async (id: number) => {
    const loc = locs.find(l => l.id === id);
    if (!loc || togglingIds.has(id)) return;
    const newActive = !loc.is_active;
    setTogglingIds(prev => new Set([...prev, id]));
    setLocs(prev => prev.map(l => l.id === id ? { ...l, is_active: newActive } : l));
    try {
      await updateLocation(id, { is_active: newActive });
      queryClient.invalidateQueries({ queryKey: ['location-hierarchy', warehouseId] });
    } catch (e) {
      setLocs(prev => prev.map(l => l.id === id ? { ...l, is_active: !newActive } : l));
      showBanner('error', `Status update failed: ${extractError(e)}`);
    } finally {
      setTogglingIds(prev => { const s = new Set(prev); s.delete(id); return s; });
    }
  }, [locs, togglingIds, warehouseId, queryClient, showBanner]);

  const handleDeleteExec = useCallback(async (id: number) => {
    try {
      await deleteLocation(id);
      setLocs(prev => prev.filter(l => l.id !== id));
      setDeleteConfId(null);
      showBanner('success', 'Location deleted.');
      queryClient.invalidateQueries({ queryKey: ['location-hierarchy', warehouseId] });
    } catch (e) {
      showBanner('error', `Delete failed: ${extractError(e)}`);
      setDeleteConfId(null);
    }
  }, [warehouseId, queryClient, showBanner]);

  const handleSelectRow = useCallback((id: number, checked: boolean) => {
    setSelectedIds(prev => { const s = new Set(prev); checked ? s.add(id) : s.delete(id); return s; });
  }, []);

  const handleSelectAll = useCallback((ids: number[], checked: boolean) => {
    setSelectedIds(prev => {
      const s = new Set(prev);
      ids.forEach(id => checked ? s.add(id) : s.delete(id));
      return s;
    });
  }, []);

  const handleBatchDelete = useCallback(async () => {
    setBatchDeleting(true);
    await Promise.allSettled([...selectedIds].map(id => deleteLocation(id)));
    setLocs(prev => prev.filter(l => !selectedIds.has(l.id)));
    setSelectedIds(new Set()); setConfirmBatch(false); setBatchDeleting(false);
    showBanner('success', 'Selected locations deleted.');
    queryClient.invalidateQueries({ queryKey: ['location-hierarchy', warehouseId] });
  }, [selectedIds, warehouseId, queryClient, showBanner]);

  const handleBatchToggle = useCallback(async (active: boolean) => {
    const ids = [...selectedIds].filter(id => locs.find(l => l.id === id)?.is_active !== active);
    if (!ids.length) return;
    const idSet = new Set(ids);
    setLocs(prev => prev.map(l => idSet.has(l.id) ? { ...l, is_active: active } : l));
    await Promise.allSettled(ids.map(id => updateLocation(id, { is_active: active })));
    queryClient.invalidateQueries({ queryKey: ['location-hierarchy', warehouseId] });
  }, [selectedIds, locs, warehouseId, queryClient]);

  const toggleSection = useCallback((key: string) => {
    setExpandedSecs(prev => {
      const s = new Set(prev);
      s.has(key) ? s.delete(key) : s.add(key);
      return s;
    });
  }, []);

  /* ── Early exit ───────────────────────────────────────────────── */
  if (!warehouseId) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-text-secondary">
        <p className="text-sm">Select a warehouse above to manage its locations.</p>
      </div>
    );
  }

  /* ── Shared accordion renderer ────────────────────────────────── */
  const renderAccordion = (keys: string[], directEdit = false) => (
    <div className="flex flex-col gap-2">
      {keys.map(key => (
        <SectionAccordion
          key={key}
          sectionKey={key}
          rows={grouped.get(key) ?? []}
          expanded={expandedSecs.has(key)}
          onToggle={() => toggleSection(key)}
          editingId={editingId}
          drafts={drafts}
          togglingIds={togglingIds}
          deleteConfId={deleteConfId}
          savingIds={savingIds}
          selectedIds={selectedIds}
          directEdit={directEdit}
          onStartEdit={handleStartEdit}
          onCancelEdit={handleCancelEdit}
          onDraftChange={handleDraftChange}
          onSaveRow={handleSaveRow}
          onToggleStatus={handleToggleStatus}
          onDeleteConfirm={id => setDeleteConfId(id)}
          onDeleteCancel={() => setDeleteConfId(null)}
          onDeleteExec={handleDeleteExec}
          onSelectRow={handleSelectRow}
          onSelectAll={handleSelectAll}
        />
      ))}
      {keys.length === 0 && (
        <div className="py-12 text-center text-sm text-text-secondary">
          {directEdit
            ? 'No locations found in this section yet.'
            : (search || statusFilter !== 'all' ? 'No locations match the current filter.' : `No locations in ${warehouseName} yet.`)}
        </div>
      )}
    </div>
  );

  /* ── Render ───────────────────────────────────────────────────── */
  return (
    <div className="flex flex-col gap-3">

      {/* Banner */}
      {banner && (
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-default text-xs ${
          banner.type === 'success' ? 'bg-success-bg text-success-text' : 'bg-error-bg text-error-text'
        }`}>
          {banner.type === 'success'
            ? <CheckCircle2 size={13} className="flex-shrink-0" />
            : <AlertTriangle size={13} className="flex-shrink-0" />}
          <span className="flex-grow">{banner.text}</span>
          <button onClick={() => setBanner(null)} className="opacity-60 hover:opacity-100 cursor-pointer"><X size={12} /></button>
        </div>
      )}

      {/* Bulk-generate result banner */}
      {bulkResult && (
        <div className={`flex items-center gap-2 px-3 py-2 rounded-default text-xs ${
          bulkResult.created > 0 ? 'bg-success-bg text-success-text' : 'bg-warning-bg text-warning-text'
        }`}>
          {bulkResult.created > 0
            ? <CheckCircle2 size={13} className="flex-shrink-0" />
            : <AlertTriangle size={13} className="flex-shrink-0" />}
          <span className="flex-grow">
            {bulkResult.created > 0
              ? `${bulkResult.created} location${bulkResult.created !== 1 ? 's' : ''} created.`
              : 'No new locations created.'}
            {bulkResult.skipped > 0 && ` ${bulkResult.skipped} skipped.`}
          </span>
          <button onClick={() => setBulkResult(null)} className="opacity-60 hover:opacity-100 cursor-pointer"><X size={12} /></button>
        </div>
      )}

      {/* ── Pattern Generator layout OR normal layout ─────────────── */}
      {showGenerator ? (
        <div className="flex flex-col gap-3">

          {/* Go Back — detached, sits above the split pane */}
          <div>
            <button
              onClick={() => {
                setShowGenerator(false);
                setPreviewLocs([]);
                setPreviewTotal(0);
                setSelectedGenSection('');
              }}
              className="flex items-center gap-2 px-3 py-1.5 border border-divider rounded-default text-xs font-medium text-text-secondary hover:text-text-primary hover:border-text-primary/40 hover:bg-white transition-colors cursor-pointer"
            >
              <ArrowLeft size={12} />
              Go Back
            </button>
          </div>

          {/* Generator open: resizable left panel + right preview */}
          <div ref={containerRef} className="flex items-start" style={{ gap: 0 }}>

          {/* Left generator panel */}
          <div
            className="flex-shrink-0 border border-divider rounded-default overflow-hidden flex flex-col"
            style={{ width: leftWidth }}
          >
            {/* Panel header — label only */}
            <div className="px-3 py-2.5 border-b border-divider bg-background">
              <p className="text-[10px] font-bold text-secondary uppercase tracking-widest text-center">
                Pattern Generator
              </p>
            </div>

            {/* Tab strip */}
            <div className="flex border-b border-divider bg-background">
              {(['generator', 'import'] as CreationTab[]).map(tab => {
                const labels: Record<CreationTab, string> = { generator: 'Generator', import: 'CSV Import' };
                return (
                  <button
                    key={tab}
                    onClick={() => setCreationTab(tab)}
                    className={`flex-1 py-2 text-[11px] font-medium border-b-2 transition-colors cursor-pointer -mb-px ${
                      creationTab === tab
                        ? 'border-secondary text-secondary'
                        : 'border-transparent text-text-secondary hover:text-text-primary'
                    }`}
                  >
                    {labels[tab]}
                  </button>
                );
              })}
            </div>

            {/* Panel body — no internal scroll; content must fit */}
            <div className="p-3">
              {creationTab === 'generator' && (
                <>
                  {bulkError && (
                    <div className="flex items-start gap-1.5 bg-error-bg text-error-text rounded px-2 py-1.5 text-[11px] mb-3">
                      <AlertTriangle size={12} className="flex-shrink-0 mt-0.5" />
                      {bulkError}
                    </div>
                  )}
                  <BulkCreationWizard
                    existingSections={existingSections}
                    onPreview={(locs, total) => { setPreviewLocs(locs); setPreviewTotal(total); }}
                    onSectionSelect={sec => {
                      setSelectedGenSection(sec);
                      if (sec) setExpandedSecs(prev => new Set([...prev, sec]));
                    }}
                    onSave={req => {
                      setBulkError(null);
                      setBulkResult(null);
                      bulkMutation.mutate(req);
                    }}
                    saving={bulkMutation.isPending}
                  />
                </>
              )}
              {creationTab === 'import' && warehouseId && (
                <CsvLocationImport
                  warehouseId={warehouseId}
                  onImportComplete={() => {
                    fetchAll();
                    queryClient.invalidateQueries({ queryKey: ['location-hierarchy', warehouseId] });
                  }}
                />
              )}
            </div>
          </div>

          {/* ── Drag handle ─────────────────────────────────────────── */}
          <div
            onMouseDown={() => { isDragging.current = true; document.body.style.cursor = 'col-resize'; }}
            className="flex-shrink-0 w-5 self-stretch flex items-center justify-center cursor-col-resize group select-none"
            title="Drag to resize"
          >
            <div className="flex flex-col items-center gap-[3px] px-1.5 py-2 rounded group-hover:bg-primary/8 transition-colors">
              {[0,1,2,3,4,5].map(i => (
                <div key={i} className="w-[3px] h-[3px] rounded-full bg-divider group-hover:bg-primary/50 transition-colors" />
              ))}
            </div>
          </div>

          {/* Right: live Preview Tree */}
          <div className="flex-grow min-w-0 flex flex-col gap-3">
            {/* Header */}
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-text-primary">
                {selectedGenSection
                  ? `Section: ${selectedGenSection}`
                  : previewLocs.length > 0
                    ? 'Preview Tree'
                    : 'All Locations'}
              </h3>
              <span className="text-xs text-text-secondary">
                {selectedGenSection ? (
                  previewLocs.length > 0
                    ? <><span className="font-semibold text-primary">{(grouped.get(selectedGenSection)?.length ?? 0).toLocaleString()}</span> existing · <span className="font-semibold text-secondary">{previewTotal.toLocaleString()}</span> draft</>
                    : <><span className="font-semibold text-primary">{(grouped.get(selectedGenSection)?.length ?? 0).toLocaleString()}</span> locations</>
                ) : previewLocs.length > 0
                    ? <><span className="font-semibold text-primary">{previewTotal.toLocaleString()}</span> to create</>
                    : `${locs.length} existing`}
              </span>
            </div>

            {/* Editable hint — only shown when a section is selected */}
            {selectedGenSection && (
              <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-primary/5 border border-primary/15 rounded-default text-[11px] text-primary/80">
                <Pencil size={11} className="flex-shrink-0" />
                Click any cell to edit • changes save immediately when you confirm
              </div>
            )}

            {/* Bulk action bar — shown when rows are selected in generator view */}
            {selectedGenSection && selectedIds.size > 0 && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-primary/5 border border-primary/15 rounded-default flex-wrap">
                <span className="text-xs font-semibold text-primary">{selectedIds.size} selected</span>
                <button
                  onClick={() => handleBatchToggle(true)}
                  className="flex items-center gap-1 px-2 py-0.5 text-xs border border-divider rounded-default text-text-secondary hover:border-success-text hover:text-success-text transition-colors cursor-pointer"
                >
                  <ToggleRight size={12} /> Activate
                </button>
                <button
                  onClick={() => handleBatchToggle(false)}
                  className="flex items-center gap-1 px-2 py-0.5 text-xs border border-divider rounded-default text-text-secondary hover:border-warning-text hover:text-warning-text transition-colors cursor-pointer"
                >
                  <ToggleLeft size={12} /> Deactivate
                </button>
                {!confirmBatch ? (
                  <button
                    onClick={() => setConfirmBatch(true)}
                    className="flex items-center gap-1 px-2 py-0.5 text-xs bg-error-bg text-error-text rounded-default hover:bg-error-text hover:text-white transition-colors cursor-pointer"
                  >
                    <Trash2 size={11} /> Delete {selectedIds.size}
                  </button>
                ) : (
                  <div className="flex items-center gap-1.5">
                    <AlertTriangle size={12} className="text-warning-text" />
                    <span className="text-xs text-text-primary">Confirm delete?</span>
                    <button
                      onClick={handleBatchDelete}
                      disabled={batchDeleting}
                      className="px-2 py-0.5 bg-error-text text-white rounded-default text-xs cursor-pointer disabled:opacity-50"
                    >
                      {batchDeleting ? 'Deleting…' : 'Confirm'}
                    </button>
                    <button onClick={() => setConfirmBatch(false)} className="text-xs text-text-secondary hover:underline cursor-pointer">
                      Cancel
                    </button>
                  </div>
                )}
                <div className="flex-grow" />
                <button onClick={() => setSelectedIds(new Set())} className="text-xs text-text-secondary hover:underline cursor-pointer">
                  Clear
                </button>
              </div>
            )}

            {/* Right panel content */}
            {selectedGenSection ? (
              /* Existing section selected — editable existing rows + draft rows stacked */
              <div className="flex flex-col gap-3">
                {renderAccordion(grouped.has(selectedGenSection) ? [selectedGenSection] : [], true)}

                {/* Draft / pending new locations generated by the wizard */}
                {previewLocs.length > 0 && (
                  <div className="flex flex-col gap-2">
                    {/* Divider */}
                    <div className="flex items-center gap-2">
                      <div className="flex-grow border-t border-dashed border-divider" />
                      <span className="flex items-center gap-1 text-[11px] font-semibold text-secondary whitespace-nowrap">
                        <Plus size={11} />
                        {previewTotal.toLocaleString()} new to add
                      </span>
                      <div className="flex-grow border-t border-dashed border-divider" />
                    </div>
                    <PreviewAccordion
                      sectionKeys={previewSectionKeys}
                      grouped={previewGrouped}
                      total={previewTotal}
                      shown={previewLocs.length}
                    />
                  </div>
                )}
              </div>
            ) : previewLocs.length > 0 ? (
              /* New section mode — show generated preview only */
              <PreviewAccordion
                sectionKeys={previewSectionKeys}
                grouped={previewGrouped}
                total={previewTotal}
                shown={previewLocs.length}
              />
            ) : loading ? (
              <div className="flex items-center justify-center py-12 text-text-secondary text-sm">
                <Loader2 size={16} className="animate-spin mr-2" />Loading…
              </div>
            ) : (
              renderAccordion(pagedKeys)
            )}
          </div>
        </div>
        </div>
      ) : (
        /* Normal layout: full-width */
        <div className="flex flex-col gap-3">
          {/* Toolbar */}
          <div className="flex flex-wrap items-center gap-2">
            {/* Title */}
            <span className="text-sm text-text-secondary">
              <span className="font-medium text-text-primary">{warehouseName}</span>
              {' '}&mdash; {locs.length.toLocaleString()} location{locs.length !== 1 ? 's' : ''}
            </span>

            <div className="flex-grow" />

            {/* Refresh */}
            <button
              onClick={fetchAll}
              disabled={loading}
              className="flex items-center gap-1 px-2 py-1.5 text-xs border border-divider rounded-default text-text-secondary hover:text-text-primary transition-colors cursor-pointer disabled:opacity-40"
            >
              <RefreshCw size={11} className={loading ? 'animate-spin' : ''} />
              Refresh
            </button>
          </div>

          {/* Search + action buttons row */}
          <div className="flex flex-wrap items-center gap-2">
            {/* Search */}
            <SearchBar
              value={search}
              onChange={v => { setSearch(v); setPage(1); }}
              placeholder="Search locations…"
              className="flex-grow min-w-[240px] max-w-md"
            />

            <div className="flex-grow" />

            {/* Batch Upload */}
            <button className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-text-secondary border border-divider rounded-default hover:bg-background transition-colors cursor-pointer">
              <Upload size={13} />
              Batch Upload
            </button>

            {/* Pattern Generator */}
            <button
              onClick={() => generatorPath ? navigate(generatorPath) : setShowGenerator(true)}
              className="flex items-center gap-1.5 px-4 py-1.5 bg-secondary text-white rounded-default text-sm font-medium hover:shadow-button-hover transition-shadow cursor-pointer"
            >
              <Wand2 size={13} />
              Pattern Generator
            </button>
          </div>

          {/* Filter tabs */}
          <div className="flex items-center gap-6 border-b border-divider">
            {([
              ['all',      'All',      allCount],
              ['active',   'Active',   activeCount],
              ['inactive', 'Inactive', inactiveCount],
            ] as [FilterStatus, string, number][]).map(([f, label, count]) => (
              <button
                key={f}
                onClick={() => { setStatusFilter(f); setPage(1); }}
                className={`flex items-center gap-1.5 pb-2.5 text-sm font-medium border-b-2 transition-colors cursor-pointer -mb-px ${
                  statusFilter === f
                    ? 'border-text-primary text-text-primary'
                    : 'border-transparent text-text-secondary hover:text-text-primary'
                }`}
              >
                {label}
                <span className={`text-xs px-1.5 py-0.5 rounded-full font-semibold ${
                  statusFilter === f ? 'bg-text-primary text-surface' : 'bg-divider text-text-secondary'
                }`}>
                  {count}
                </span>
              </button>
            ))}
          </div>

          {/* Batch action bar */}
          {selectedIds.size > 0 && (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-primary/5 border border-primary/15 rounded-default flex-wrap">
              <span className="text-xs font-semibold text-primary">{selectedIds.size} selected</span>
              <button onClick={() => handleBatchToggle(true)}
                className="flex items-center gap-1 px-2 py-0.5 text-xs border border-divider rounded-default text-text-secondary hover:border-success-text hover:text-success-text transition-colors cursor-pointer">
                <ToggleRight size={12} /> Activate
              </button>
              <button onClick={() => handleBatchToggle(false)}
                className="flex items-center gap-1 px-2 py-0.5 text-xs border border-divider rounded-default text-text-secondary hover:border-warning-text hover:text-warning-text transition-colors cursor-pointer">
                <ToggleLeft size={12} /> Deactivate
              </button>
              {!confirmBatch ? (
                <button onClick={() => setConfirmBatch(true)}
                  className="flex items-center gap-1 px-2 py-0.5 text-xs bg-error-bg text-error-text rounded-default hover:bg-error-text hover:text-white transition-colors cursor-pointer">
                  <Trash2 size={11} /> Delete {selectedIds.size}
                </button>
              ) : (
                <div className="flex items-center gap-1.5">
                  <AlertTriangle size={12} className="text-warning-text" />
                  <span className="text-xs text-text-primary">Confirm soft-delete?</span>
                  <button onClick={handleBatchDelete} disabled={batchDeleting}
                    className="px-2 py-0.5 bg-error-text text-white rounded-default text-xs cursor-pointer disabled:opacity-50">
                    {batchDeleting ? 'Deleting…' : 'Confirm'}
                  </button>
                  <button onClick={() => setConfirmBatch(false)} className="text-xs text-text-secondary hover:underline cursor-pointer">Cancel</button>
                </div>
              )}
              <div className="flex-grow" />
              <button onClick={() => setSelectedIds(new Set())} className="text-xs text-text-secondary hover:underline cursor-pointer">Clear</button>
            </div>
          )}

          {/* Error */}
          {fetchErr && !loading && (
            <div className="flex items-center gap-2 bg-error-bg text-error-text rounded-default px-3 py-2 text-xs">
              <AlertTriangle size={13} /> {fetchErr}
            </div>
          )}

          {/* Loading */}
          {loading && (
            <div className="flex items-center justify-center py-12 text-text-secondary text-sm">
              <Loader2 size={16} className="animate-spin mr-2" /> Loading locations…
            </div>
          )}

          {/* Accordion */}
          {!loading && !fetchErr && renderAccordion(pagedKeys)}

          {/* Pagination + page size */}
          {!loading && filtered.length > 0 && (
            <div className="flex items-center justify-between pt-1">
              <span className="text-xs text-text-secondary">
                {((page - 1) * pageSize + 1)}–{Math.min(page * pageSize, filtered.length)} of {filtered.length.toLocaleString()}
              </span>

              <div className="flex items-center gap-2">
                <select
                  value={pageSize}
                  onChange={e => { setPageSize(Number(e.target.value)); setPage(1); }}
                  className="form-input !py-1 !px-2 text-xs !w-auto"
                >
                  {PAGE_SIZES.map(s => <option key={s} value={s}>{s} / page</option>)}
                </select>

                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="px-2 py-1 text-xs border border-divider rounded text-text-secondary disabled:opacity-30 cursor-pointer hover:bg-background"
                  >
                    ← Prev
                  </button>
                  <span className="px-2 text-xs text-text-secondary">{page} / {totalPages}</span>
                  <button
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="px-2 py-1 text-xs border border-divider rounded text-text-secondary disabled:opacity-30 cursor-pointer hover:bg-background"
                  >
                    Next →
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Footer summary */}
          <div className="flex items-center gap-3 text-xs text-text-secondary">
            <span>{activeCount} active</span>
            <span>·</span>
            <span>{inactiveCount} inactive</span>
            <span>·</span>
            <span>{locs.length} total</span>
          </div>
        </div>
      )}
    </div>
  );
}

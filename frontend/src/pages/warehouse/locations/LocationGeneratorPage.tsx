import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Loader2, CheckCircle2, AlertTriangle, X, Plus,
} from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import WarehouseIcon from '@mui/icons-material/Warehouse';
import PageHeader from '../../components/layout/PageHeader';
import { useWarehouse } from '../../api/contexts/WarehouseContext';
import {
  listLocations,
  bulkGenerateLocations,
} from '../../api/base/warehouse';
import type {
  InventoryLocationRead,
  BulkGenerateRequest,
  BulkGenerateResponse,
} from '../../api/base_types/warehouse';
import BulkCreationWizard from '../settings/warehouse_locations/BulkCreationWizard';
import type { PreviewLocation } from '../settings/warehouse_locations/BulkCreationWizard';
import { locationCode } from '../settings/warehouse_locations/BulkCreationWizard';
import CsvLocationImport from '../settings/warehouse_locations/CsvLocationImport';

/* ------------------------------------------------------------------
 * Constants
 * ------------------------------------------------------------------ */

type CreationTab = 'generator' | 'import';
const UNASSIGNED = '__unassigned__';

function extractError(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const r = (err as { response?: { data?: { detail?: string } } }).response;
    return r?.data?.detail ?? 'Operation failed';
  }
  return 'Network error';
}

/* ------------------------------------------------------------------
 * PreviewAccordion — read-only grouped preview of wizard-generated locs
 * ------------------------------------------------------------------ */

function PreviewAccordion({
  sectionKeys, grouped, total, shown,
}: {
  sectionKeys: string[];
  grouped: Map<string, PreviewLocation[]>;
  total: number;
  shown: number;
}) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set(sectionKeys));
  const toggle = (k: string) => setExpanded(prev => {
    const s = new Set(prev); s.has(k) ? s.delete(k) : s.add(k); return s;
  });

  return (
    <div className="flex flex-col gap-2">
      {sectionKeys.map(key => {
        const rows = grouped.get(key) ?? [];
        const open = expanded.has(key);
        return (
          <div key={key} className="border border-dashed border-secondary/30 rounded-default overflow-hidden">
            <button
              onClick={() => toggle(key)}
              className="w-full flex items-center gap-2 px-3 py-2 bg-secondary/5 hover:bg-secondary/10 transition-colors cursor-pointer"
            >
              <span className={`transition-transform ${open ? 'rotate-90' : ''}`}>
                <svg width="10" height="10" viewBox="0 0 10 10"><path d="M3 1l4 4-4 4" fill="none" stroke="currentColor" strokeWidth="1.5" /></svg>
              </span>
              <span className="text-xs font-semibold text-secondary">
                {key === UNASSIGNED ? 'Unassigned' : key}
              </span>
              <span className="text-[10px] text-secondary/70 ml-auto">{rows.length}</span>
            </button>
            {open && (
              <div className="max-h-[260px] overflow-y-auto">
                <table className="w-full text-[11px]">
                  <thead>
                    <tr className="border-b border-secondary/15 text-secondary/70">
                      <th className="text-left px-3 py-1 font-medium">CODE</th>
                      <th className="text-left px-2 py-1 font-medium">ZONE</th>
                      <th className="text-left px-2 py-1 font-medium">AISLE</th>
                      <th className="text-left px-2 py-1 font-medium">RACK</th>
                      <th className="text-left px-2 py-1 font-medium">BIN</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((loc, idx) => (
                      <tr key={idx} className="border-b border-secondary/8 last:border-0">
                        <td className="px-3 py-1 font-mono text-secondary">{locationCode(loc)}</td>
                        <td className="px-2 py-1 text-text-secondary">{loc.zone || '--'}</td>
                        <td className="px-2 py-1 text-text-secondary">{loc.aisle || '--'}</td>
                        <td className="px-2 py-1 text-text-secondary">{loc.rack || '--'}</td>
                        <td className="px-2 py-1 text-text-secondary">{loc.bin || '--'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        );
      })}
      {shown < total && (
        <p className="text-[11px] text-secondary/60 text-center py-1">
          Showing {shown} of {total.toLocaleString()} locations
        </p>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------
 * LocationGeneratorPage
 * ------------------------------------------------------------------ */

export default function LocationGeneratorPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { selectedWarehouse, loading: whLoading } = useWarehouse();
  const warehouseId = selectedWarehouse?.id ?? null;
  const warehouseName = selectedWarehouse?.warehouse_name ?? 'Warehouse';

  /* ── Data ────────────────────────────────────────────────── */
  const [locs, setLocs] = useState<InventoryLocationRead[]>([]);
  const [loading, setLoading] = useState(true);

  /* ── Creation tab ────────────────────────────────────────── */
  const [creationTab, setCreationTab] = useState<CreationTab>('generator');

  /* ── Generator state ─────────────────────────────────────── */
  const [bulkResult, setBulkResult] = useState<BulkGenerateResponse | null>(null);
  const [bulkError, setBulkError] = useState<string | null>(null);
  const [previewLocs, setPreviewLocs] = useState<PreviewLocation[]>([]);
  const [previewTotal, setPreviewTotal] = useState(0);
  const [selectedGenSection, setSelectedGenSection] = useState<string>('');

  /* ── Resizable split pane ────────────────────────────────── */
  const [leftWidth, setLeftWidth] = useState(320);
  const isDragging = useRef(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!isDragging.current || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      setLeftWidth(Math.max(240, Math.min(520, e.clientX - rect.left)));
    };
    const onUp = () => { isDragging.current = false; document.body.style.cursor = ''; };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };
  }, []);

  /* ── Fetch locations ─────────────────────────────────────── */
  const fetchAll = useCallback(async () => {
    if (!warehouseId) return;
    setLoading(true);
    try {
      const data = await listLocations(warehouseId);
      setLocs(data);
    } catch {
      // silently fail — we still show the generator
    } finally {
      setLoading(false);
    }
  }, [warehouseId]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  /* ── Existing section names ──────────────────────────────── */
  const existingSections = useMemo(() => {
    const names = [...new Set(locs.map(l => l.section).filter(Boolean))] as string[];
    return names.sort((a, b) => a.localeCompare(b));
  }, [locs]);

  /* ── Preview grouping ────────────────────────────────────── */
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

  /* ── Bulk generate mutation ──────────────────────────────── */
  const bulkMutation = useMutation({
    mutationFn: (req: BulkGenerateRequest) => bulkGenerateLocations(warehouseId!, req),
    onSuccess: (res) => {
      setBulkResult(res);
      setBulkError(null);
      fetchAll();
      queryClient.invalidateQueries({ queryKey: ['location-hierarchy', warehouseId] });
    },
    onError: (e) => { setBulkError(extractError(e)); },
  });

  /* ── Early returns ───────────────────────────────────────── */
  if (whLoading) {
    return (
      <div className="flex flex-col gap-6">
        <PageHeader title="Pattern Generator" description="Bulk-create warehouse locations from patterns or CSV import" />
        <div className="flex justify-center py-16">
          <span className="inline-block w-6 h-6 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  if (!selectedWarehouse) {
    return (
      <div className="flex flex-col gap-6">
        <PageHeader title="Pattern Generator" description="Bulk-create warehouse locations from patterns or CSV import" />
        <div className="bg-surface rounded-card shadow-card p-12 flex flex-col items-center gap-4 text-center">
          <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-background text-text-secondary">
            <WarehouseIcon style={{ fontSize: 32 }} />
          </div>
          <div>
            <p className="text-base font-medium text-text-primary">No warehouse selected</p>
            <p className="text-sm text-text-secondary mt-1">
              Select a warehouse from the sidebar to generate locations.
            </p>
          </div>
        </div>
      </div>
    );
  }

  /* ── Render ───────────────────────────────────────────────── */
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Pattern Generator"
        description="Bulk-create warehouse locations from patterns or CSV import"
      />

      {/* Warehouse context banner */}
      <div className="flex items-center gap-3 bg-surface rounded-card shadow-card px-5 py-3">
        <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-primary/10 text-primary">
          <WarehouseIcon fontSize="small" />
        </div>
        <div className="min-w-0 flex-grow">
          <p className="text-sm font-semibold text-text-primary truncate">
            {selectedWarehouse.warehouse_name}
          </p>
          <p className="text-xs text-text-secondary">
            {locs.length} existing location{locs.length !== 1 ? 's' : ''}
            {' '}&middot;{' '}
            <span className={selectedWarehouse.is_active ? 'text-emerald-600' : 'text-text-secondary'}>
              {selectedWarehouse.is_active ? 'Active' : 'Inactive'}
            </span>
          </p>
        </div>
        <button
          onClick={() => navigate('/warehouse/locations')}
          className="px-3 py-1.5 text-xs font-medium text-text-secondary border border-divider rounded-default hover:text-text-primary hover:border-text-primary/40 transition-colors cursor-pointer"
        >
          Back to Locations
        </button>
      </div>

      {/* Result banners */}
      {bulkResult && (
        <div className={`flex items-center gap-2 px-3 py-2 rounded-default text-sm ${
          bulkResult.created > 0 ? 'bg-success-bg text-success-text' : 'bg-warning-bg text-warning-text'
        }`}>
          {bulkResult.created > 0
            ? <CheckCircle2 size={14} className="flex-shrink-0" />
            : <AlertTriangle size={14} className="flex-shrink-0" />}
          <span className="flex-grow">
            {bulkResult.created > 0
              ? `${bulkResult.created} location${bulkResult.created !== 1 ? 's' : ''} created successfully.`
              : 'No new locations created.'}
            {bulkResult.skipped > 0 && ` ${bulkResult.skipped} skipped (duplicates).`}
          </span>
          <button onClick={() => setBulkResult(null)} className="opacity-60 hover:opacity-100 cursor-pointer"><X size={14} /></button>
        </div>
      )}

      {/* Resizable split layout */}
      <div ref={containerRef} className="flex items-start" style={{ gap: 0 }}>

        {/* Left panel — Generator / Import */}
        <div
          className="flex-shrink-0 bg-surface border border-divider rounded-card shadow-card overflow-hidden flex flex-col"
          style={{ width: leftWidth }}
        >
          {/* Tab strip */}
          <div className="flex border-b border-divider">
            {(['generator', 'import'] as CreationTab[]).map(tab => {
              const labels: Record<CreationTab, string> = { generator: 'Pattern Generator', import: 'CSV / Excel Import' };
              return (
                <button
                  key={tab}
                  onClick={() => setCreationTab(tab)}
                  className={`flex-1 py-3 text-sm font-medium border-b-2 transition-colors cursor-pointer -mb-px ${
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

          {/* Panel body */}
          <div className="p-4">
            {creationTab === 'generator' && (
              <>
                {bulkError && (
                  <div className="flex items-start gap-1.5 bg-error-bg text-error-text rounded px-2 py-1.5 text-xs mb-3">
                    <AlertTriangle size={12} className="flex-shrink-0 mt-0.5" />
                    {bulkError}
                  </div>
                )}
                <BulkCreationWizard
                  existingSections={existingSections}
                  onPreview={(locs, total) => { setPreviewLocs(locs); setPreviewTotal(total); }}
                  onSectionSelect={sec => setSelectedGenSection(sec)}
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

        {/* Drag handle */}
        <div
          onMouseDown={() => { isDragging.current = true; document.body.style.cursor = 'col-resize'; }}
          className="flex-shrink-0 w-5 self-stretch flex items-center justify-center cursor-col-resize group select-none"
          title="Drag to resize"
        >
          <div className="flex flex-col items-center gap-[3px] px-1.5 py-2 rounded group-hover:bg-primary/8 transition-colors">
            {[0, 1, 2, 3, 4, 5].map(i => (
              <div key={i} className="w-[3px] h-[3px] rounded-full bg-divider group-hover:bg-primary/50 transition-colors" />
            ))}
          </div>
        </div>

        {/* Right panel — Preview */}
        <div className="flex-grow min-w-0 bg-surface rounded-card shadow-card border border-divider overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-divider bg-background/30">
            <h3 className="text-sm font-semibold text-text-primary">
              {previewLocs.length > 0 ? 'Preview' : 'Existing Locations'}
            </h3>
            <span className="text-xs text-text-secondary">
              {previewLocs.length > 0 ? (
                <>
                  <span className="font-semibold text-secondary">{previewTotal.toLocaleString()}</span> to create
                  {selectedGenSection && (
                    <> &middot; Section: <span className="font-medium text-text-primary">{selectedGenSection}</span></>
                  )}
                </>
              ) : (
                <>{locs.length.toLocaleString()} total</>
              )}
            </span>
          </div>

          {/* Body */}
          <div className="p-4">
            {loading ? (
              <div className="flex items-center justify-center py-12 text-text-secondary text-sm">
                <Loader2 size={16} className="animate-spin mr-2" /> Loading locations...
              </div>
            ) : previewLocs.length > 0 ? (
              <PreviewAccordion
                sectionKeys={previewSectionKeys}
                grouped={previewGrouped}
                total={previewTotal}
                shown={previewLocs.length}
              />
            ) : locs.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-text-secondary gap-2">
                <Plus size={24} className="text-divider" />
                <p className="text-sm">No locations yet in <span className="font-medium text-text-primary">{warehouseName}</span>.</p>
                <p className="text-xs">Use the generator or CSV import to create locations.</p>
              </div>
            ) : (
              /* Summary of existing locations grouped by section */
              <div className="flex flex-col gap-2">
                {existingSections.map(sec => {
                  const count = locs.filter(l => l.section === sec).length;
                  return (
                    <div key={sec} className="flex items-center justify-between px-3 py-2 bg-background/50 rounded-default">
                      <span className="text-sm font-medium text-text-primary">{sec}</span>
                      <span className="text-xs text-text-secondary">{count} location{count !== 1 ? 's' : ''}</span>
                    </div>
                  );
                })}
                {(() => {
                  const unassigned = locs.filter(l => !l.section).length;
                  if (unassigned === 0) return null;
                  return (
                    <div className="flex items-center justify-between px-3 py-2 bg-background/50 rounded-default">
                      <span className="text-sm font-medium text-text-secondary italic">Unassigned</span>
                      <span className="text-xs text-text-secondary">{unassigned} location{unassigned !== 1 ? 's' : ''}</span>
                    </div>
                  );
                })()}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

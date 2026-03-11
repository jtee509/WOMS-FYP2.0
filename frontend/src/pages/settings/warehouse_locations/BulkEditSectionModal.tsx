import { useState, useEffect, useCallback, useRef } from 'react';
import { Plus, X, Trash2, Save, AlertTriangle, CheckCircle2, Loader2, ArrowLeft } from 'lucide-react';
import {
  listLocations,
  createLocation,
  updateLocation,
  deleteLocation,
} from '../../../api/base/warehouse';
import type { InventoryLocationRead } from '../../../api/base_types/warehouse';
import type { LocationTreeNode } from '../../../api/base_types/warehouse';
import type { HierarchyPath } from './LocationTree';

/* ------------------------------------------------------------------
 * Row state
 * ------------------------------------------------------------------ */

type Field = 'zone' | 'aisle' | 'rack' | 'bin';

interface RowState {
  /** Positive = existing DB id; negative = temporary new-row key */
  id:        number;
  zone:      string;
  aisle:     string;
  rack:      string;
  bin:       string;
  origZone:  string;
  origAisle: string;
  origRack:  string;
  origBin:   string;
  isNew:     boolean;
  selected:  boolean;
  status:    'idle' | 'saving' | 'saved' | 'error';
  errorMsg?: string;
}

let _tmpKey = -1;
const nextTmpId = () => _tmpKey--;

function toRowState(loc: InventoryLocationRead): RowState {
  return {
    id:        loc.id,
    zone:      loc.zone  ?? '',
    aisle:     loc.aisle ?? '',
    rack:      loc.rack  ?? '',
    bin:       loc.bin   ?? '',
    origZone:  loc.zone  ?? '',
    origAisle: loc.aisle ?? '',
    origRack:  loc.rack  ?? '',
    origBin:   loc.bin   ?? '',
    isNew:     false,
    selected:  false,
    status:    'idle',
  };
}

function newEmptyRow(): RowState {
  return {
    id:        nextTmpId(),
    zone:      '',
    aisle:     '',
    rack:      '',
    bin:       '',
    origZone:  '',
    origAisle: '',
    origRack:  '',
    origBin:   '',
    isNew:     true,
    selected:  false,
    status:    'idle',
  };
}

function getOrigValue(row: RowState, field: Field): string {
  switch (field) {
    case 'zone':  return row.origZone;
    case 'aisle': return row.origAisle;
    case 'rack':  return row.origRack;
    case 'bin':   return row.origBin;
  }
}

function isFieldDirty(row: RowState, field: Field): boolean {
  return row[field] !== getOrigValue(row, field);
}

function isRowDirty(row: RowState): boolean {
  if (row.isNew) return true;
  return (['zone', 'aisle', 'rack', 'bin'] as Field[]).some((f) => isFieldDirty(row, f));
}

function extractErrorMessage(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const resp = (err as { response?: { data?: { detail?: string } } }).response;
    return resp?.data?.detail ?? 'Operation failed';
  }
  return 'Network error';
}

/* ------------------------------------------------------------------
 * Props
 * ------------------------------------------------------------------ */

interface Props {
  node:        LocationTreeNode;  // type must be 'section'
  path:        HierarchyPath;
  warehouseId: number;
  onClose:     () => void;
  onComplete:  () => void;  // triggers tree refresh when changes were made
}

/* ------------------------------------------------------------------
 * Component
 * ------------------------------------------------------------------ */

const FIELDS: Field[] = ['zone', 'aisle', 'rack', 'bin'];
const FIELD_LABELS: Record<Field, string> = {
  zone:  'Zone',
  aisle: 'Aisle',
  rack:  'Rack',
  bin:   'Bin',
};

export default function BulkEditSectionModal({
  node,
  warehouseId,
  onClose,
  onComplete,
}: Props) {
  const [rows,       setRows]       = useState<RowState[]>([]);
  const [loading,    setLoading]    = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [saving,     setSaving]     = useState(false);
  const [deleting,   setDeleting]   = useState(false);
  const [confirmDel, setConfirmDel] = useState(false);
  const [anyChanged, setAnyChanged] = useState(false);
  const [banner,     setBanner]     = useState<{ type: 'success' | 'error'; msg: string } | null>(null);

  const newRowRef = useRef<HTMLInputElement | null>(null);

  /* ── Fetch locations for this section on mount ─────────────────── */
  useEffect(() => {
    setLoading(true);
    setFetchError(null);
    listLocations(warehouseId)
      .then((locs) => {
        const filtered = locs.filter((l) => l.section === node.name);
        setRows(filtered.map(toRowState));
      })
      .catch((e) => setFetchError(extractErrorMessage(e)))
      .finally(() => setLoading(false));
  }, [warehouseId, node.name]);

  /* ── Cell editing ───────────────────────────────────────────────── */
  const handleCellChange = useCallback((id: number, field: Field, value: string) => {
    setRows((prev) =>
      prev.map((r) =>
        r.id === id
          ? { ...r, [field]: value, status: 'idle' as const, errorMsg: undefined }
          : r,
      ),
    );
  }, []);

  /* ── Row selection ──────────────────────────────────────────────── */
  const toggleSelect = useCallback((id: number) => {
    setRows((prev) => prev.map((r) => (r.id === id ? { ...r, selected: !r.selected } : r)));
  }, []);

  const toggleSelectAll = useCallback(() => {
    setRows((prev) => {
      const allSelected = prev.every((r) => r.selected);
      return prev.map((r) => ({ ...r, selected: !allSelected }));
    });
  }, []);

  /* ── Add new empty row ──────────────────────────────────────────── */
  const handleAddRow = useCallback(() => {
    setRows((prev) => [...prev, newEmptyRow()]);
    // Focus first cell of new row after render
    setTimeout(() => newRowRef.current?.focus(), 50);
  }, []);

  /* ── Save all dirty rows ────────────────────────────────────────── */
  const handleSaveAll = useCallback(async () => {
    const dirty = rows.filter(isRowDirty);
    if (dirty.length === 0) return;

    const dirtyIds = new Set(dirty.map((r) => r.id));
    setSaving(true);
    setBanner(null);
    setRows((prev) =>
      prev.map((r) => (dirtyIds.has(r.id) ? { ...r, status: 'saving' as const } : r)),
    );

    const tasks = dirty.map(async (row) => {
      try {
        if (row.isNew) {
          // Create new location
          const created = await createLocation(warehouseId, {
            section: node.name,
            zone:    row.zone  || undefined,
            aisle:   row.aisle || undefined,
            rack:    row.rack  || undefined,
            bin:     row.bin   || undefined,
          });
          return { tmpId: row.id, realId: created.id, success: true, error: '' };
        } else {
          // Update existing
          await updateLocation(row.id, {
            zone:  row.zone  || undefined,
            aisle: row.aisle || undefined,
            rack:  row.rack  || undefined,
            bin:   row.bin   || undefined,
          });
          return { tmpId: row.id, realId: row.id, success: true, error: '' };
        }
      } catch (e) {
        return { tmpId: row.id, realId: row.id, success: false, error: extractErrorMessage(e) };
      }
    });

    const results = await Promise.all(tasks);
    const byTmpId = new Map(results.map((r) => [r.tmpId, r]));

    let savedCount = 0;
    let failCount = 0;

    setRows((prev) =>
      prev.map((r) => {
        const res = byTmpId.get(r.id);
        if (!res) return r;
        if (res.success) {
          savedCount++;
          return {
            ...r,
            id:        res.realId,
            isNew:     false,
            origZone:  r.zone,
            origAisle: r.aisle,
            origRack:  r.rack,
            origBin:   r.bin,
            status: 'saved' as const,
          };
        }
        failCount++;
        return { ...r, status: 'error' as const, errorMsg: res.error };
      }),
    );

    setSaving(false);
    setAnyChanged(true);

    if (failCount === 0) {
      setBanner({ type: 'success', msg: `${savedCount} change${savedCount !== 1 ? 's' : ''} saved.` });
    } else {
      setBanner({ type: 'error', msg: `${failCount} row${failCount !== 1 ? 's' : ''} failed to save.` });
    }
  }, [rows, warehouseId, node.name]);

  /* ── Delete selected rows ───────────────────────────────────────── */
  const handleDeleteSelected = useCallback(async () => {
    const selected = rows.filter((r) => r.selected);
    if (selected.length === 0) return;
    setDeleting(true);
    // New (unsaved) rows can be removed client-side; existing ones need the API
    const toDelete = selected.filter((r) => !r.isNew);
    await Promise.allSettled(toDelete.map((r) => deleteLocation(r.id)));
    setRows((prev) => prev.filter((r) => !r.selected));
    setDeleting(false);
    setConfirmDel(false);
    setAnyChanged(true);
    setBanner({ type: 'success', msg: `${selected.length} row${selected.length !== 1 ? 's' : ''} removed.` });
  }, [rows]);

  /* ── Close handler ──────────────────────────────────────────────── */
  const handleClose = useCallback(() => {
    if (anyChanged) onComplete();
    onClose();
  }, [anyChanged, onComplete, onClose]);

  /* ── Derived values ─────────────────────────────────────────────── */
  const dirtyCount    = rows.filter(isRowDirty).length;
  const newCount      = rows.filter((r) => r.isNew).length;
  const selectedCount = rows.filter((r) => r.selected).length;
  const allSelected   = rows.length > 0 && rows.every((r) => r.selected);
  const someSelected  = rows.some((r) => r.selected) && !allSelected;

  /* ── Render — inline panel, no fixed overlay ─────────────────────── */
  return (
    <div className="flex flex-col h-full border border-divider rounded-default overflow-hidden bg-surface">

      {/* ── Header ───────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-divider bg-background flex-shrink-0">
        <button
          onClick={handleClose}
          className="p-1.5 text-text-secondary hover:text-text-primary hover:bg-divider/40 rounded-default cursor-pointer transition-colors"
          title="Back to generator"
        >
          <ArrowLeft size={14} />
        </button>

        <div className="flex-grow min-w-0">
          <h3 className="text-sm font-semibold text-text-primary truncate">
            Section &ldquo;{node.name}&rdquo;
          </h3>
          <p className="text-xs text-text-secondary mt-0.5">
            {loading
              ? 'Loading…'
              : `${rows.filter((r) => !r.isNew).length} existing · ${newCount} new`}
          </p>
        </div>

        <button
          onClick={handleAddRow}
          className="flex items-center gap-1.5 px-2.5 py-1.5 bg-primary/10 text-primary rounded-default text-xs font-medium hover:bg-primary/20 transition-colors cursor-pointer flex-shrink-0"
        >
          <Plus size={12} />
          Add Row
        </button>
      </div>

      {/* ── Action bar (shown when rows selected OR dirty) ────────── */}
      {(selectedCount > 0 || dirtyCount > 0) && (
        <div className="flex items-center gap-2 px-4 py-2 border-b border-divider bg-primary/5 flex-shrink-0 flex-wrap gap-y-1.5">

          {/* Delete selected */}
          {selectedCount > 0 && !confirmDel && (
            <button
              onClick={() => setConfirmDel(true)}
              disabled={deleting}
              className="flex items-center gap-1 px-2.5 py-1 bg-error-bg text-error-text rounded-default text-xs font-medium hover:bg-error-text hover:text-white transition-colors cursor-pointer disabled:opacity-50"
            >
              <Trash2 size={11} />
              Delete {selectedCount}
            </button>
          )}

          {/* Confirm delete */}
          {confirmDel && (
            <div className="flex items-center gap-2">
              <AlertTriangle size={13} className="text-warning-text flex-shrink-0" />
              <span className="text-xs text-text-primary">Delete {selectedCount}?</span>
              <button
                onClick={handleDeleteSelected}
                disabled={deleting}
                className="px-2 py-0.5 bg-error-text text-white rounded-default text-xs font-medium cursor-pointer disabled:opacity-50"
              >
                {deleting ? 'Deleting…' : 'Confirm'}
              </button>
              <button
                onClick={() => setConfirmDel(false)}
                disabled={deleting}
                className="text-xs text-text-secondary hover:underline cursor-pointer disabled:opacity-40"
              >
                Cancel
              </button>
            </div>
          )}

          <div className="flex-grow" />

          {/* Save button */}
          {dirtyCount > 0 && (
            <button
              onClick={handleSaveAll}
              disabled={saving}
              className="flex items-center gap-1.5 px-3 py-1 bg-secondary text-white rounded-default text-xs font-medium hover:shadow-button-hover transition-shadow cursor-pointer disabled:opacity-50"
            >
              {saving ? <Loader2 size={11} className="animate-spin" /> : <Save size={11} />}
              {saving ? 'Saving…' : `Save ${dirtyCount}`}
            </button>
          )}
        </div>
      )}

      {/* ── Banner ───────────────────────────────────────────────── */}
      {banner && (
        <div
          className={`flex items-center gap-2 px-4 py-2 text-xs flex-shrink-0 ${
            banner.type === 'success'
              ? 'bg-success-bg text-success-text'
              : 'bg-error-bg text-error-text'
          }`}
        >
          {banner.type === 'success'
            ? <CheckCircle2 size={13} className="flex-shrink-0" />
            : <AlertTriangle size={13} className="flex-shrink-0" />}
          <span className="flex-grow">{banner.msg}</span>
          <button onClick={() => setBanner(null)} className="opacity-60 hover:opacity-100 cursor-pointer">
            <X size={12} />
          </button>
        </div>
      )}

      {/* ── Body (scrollable table) ───────────────────────────────── */}
      <div className="flex-grow overflow-y-auto min-h-0">

        {loading && (
          <div className="flex items-center justify-center py-12 text-text-secondary text-sm">
            <Loader2 size={16} className="animate-spin mr-2" />
            Loading locations…
          </div>
        )}

        {fetchError && !loading && (
          <div className="flex items-center gap-3 m-4 bg-error-bg text-error-text rounded-default px-3 py-2.5 text-sm">
            <AlertTriangle size={14} className="flex-shrink-0" />
            {fetchError}
          </div>
        )}

        {!loading && !fetchError && (
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-background border-b border-divider z-10">
              <tr>
                <th className="w-9 px-3 py-2.5 text-center">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    ref={(el) => { if (el) el.indeterminate = someSelected; }}
                    onChange={toggleSelectAll}
                    className="w-3.5 h-3.5 rounded border-divider text-primary focus:ring-0 cursor-pointer"
                  />
                </th>
                {FIELDS.map((f) => (
                  <th
                    key={f}
                    className="px-2 py-2.5 text-left text-xs font-semibold text-text-secondary uppercase tracking-wide"
                  >
                    {FIELD_LABELS[f]}
                  </th>
                ))}
                {/* Status */}
                <th className="w-7 px-2 py-2.5" />
              </tr>
            </thead>

            <tbody>
              {rows.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-10 text-center text-xs text-text-secondary">
                    No locations in this section yet.{' '}
                    <button onClick={handleAddRow} className="text-primary hover:underline cursor-pointer">
                      Add a row
                    </button>{' '}
                    to get started.
                  </td>
                </tr>
              )}

              {rows.map((row, rowIdx) => {
                const dirty = isRowDirty(row);
                const isFirst = rowIdx === rows.filter((r) => r.isNew).indexOf(row) + rows.filter((r) => !r.isNew).length && row.isNew;
                return (
                  <tr
                    key={row.id}
                    className={`border-b border-divider last:border-0 transition-colors ${
                      row.isNew
                        ? 'bg-primary/3'
                        : row.selected
                          ? 'bg-primary/5'
                          : 'hover:bg-background'
                    }`}
                  >
                    {/* Checkbox */}
                    <td className="px-3 py-1.5 text-center">
                      <input
                        type="checkbox"
                        checked={row.selected}
                        onChange={() => toggleSelect(row.id)}
                        className="w-3.5 h-3.5 rounded border-divider text-primary focus:ring-0 cursor-pointer"
                      />
                    </td>

                    {/* Editable fields */}
                    {FIELDS.map((field, fi) => {
                      const fieldDirty = isFieldDirty(row, field);
                      const isFirstNew = row.isNew && fi === 0 && isFirst;
                      return (
                        <td key={field} className="px-2 py-1.5">
                          <input
                            type="text"
                            ref={isFirstNew ? newRowRef : undefined}
                            value={row[field]}
                            onChange={(e) => handleCellChange(row.id, field, e.target.value)}
                            placeholder={row.isNew ? `Enter ${FIELD_LABELS[field]}` : '—'}
                            maxLength={50}
                            className={`w-full form-input text-xs py-1 ${
                              row.isNew
                                ? 'border-primary/40 focus:border-primary bg-white'
                                : fieldDirty
                                  ? 'border-warning-text/60 focus:border-warning-text'
                                  : ''
                            }`}
                          />
                        </td>
                      );
                    })}

                    {/* Row status */}
                    <td className="px-2 py-1.5 text-center">
                      {row.status === 'saving' && (
                        <Loader2 size={12} className="animate-spin text-text-secondary mx-auto" />
                      )}
                      {row.status === 'saved' && (
                        <CheckCircle2 size={12} className="text-success-text mx-auto" />
                      )}
                      {row.status === 'error' && (
                        <span title={row.errorMsg ?? 'Error'}>
                          <AlertTriangle size={12} className="text-error-text mx-auto" />
                        </span>
                      )}
                      {row.status === 'idle' && dirty && (
                        <span
                          className={`w-2 h-2 rounded-full inline-block ${row.isNew ? 'bg-primary' : 'bg-warning-text'}`}
                          title={row.isNew ? 'New row' : 'Unsaved changes'}
                        />
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* ── Footer ───────────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-4 py-3 border-t border-divider bg-background flex-shrink-0">
        <span className="text-xs text-text-secondary">
          {dirtyCount > 0
            ? `${dirtyCount} unsaved change${dirtyCount !== 1 ? 's' : ''}`
            : anyChanged
              ? 'All changes saved'
              : `${rows.filter((r) => !r.isNew).length} location${rows.filter((r) => !r.isNew).length !== 1 ? 's' : ''}`}
        </span>
        <div className="flex items-center gap-2">
          <button
            onClick={handleAddRow}
            className="flex items-center gap-1 px-2.5 py-1 text-xs text-primary border border-primary/30 rounded-default hover:bg-primary/5 transition-colors cursor-pointer"
          >
            <Plus size={11} />
            Add Row
          </button>
          {dirtyCount > 0 && (
            <button
              onClick={handleSaveAll}
              disabled={saving}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-secondary text-white rounded-default text-xs font-medium hover:shadow-button-hover transition-shadow disabled:opacity-50 cursor-pointer"
            >
              {saving ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
              {saving ? 'Saving…' : 'Save All'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

import { useState, useCallback, useEffect } from 'react';
import { Plus, ChevronRight, ChevronDown, X, XCircle, Upload, MapPin } from 'lucide-react';
import DataTable, { type Column } from '../../components/common/DataTable';
import StandardActionMenu from '../../components/common/StandardActionMenu';
import LocationManagementSection from './LocationManagementSection';
import type { WarehouseRead, WarehouseCreate, WarehouseUpdate } from '../../api/base_types/warehouse';
import {
  listWarehouses,
  createWarehouse,
  updateWarehouse,
  toggleWarehouseStatus,
  deleteWarehouse,
  duplicateWarehouse,
} from '../../api/base/warehouse';

/* ------------------------------------------------------------------
 * Helpers
 * ------------------------------------------------------------------ */

function extractErrorMessage(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const resp = (err as { response?: { data?: { detail?: string } } }).response;
    return resp?.data?.detail ?? 'Operation failed';
  }
  return 'Network error';
}

type FilterActive = 'all' | 'active' | 'inactive';
type SubTab = 'list' | 'locations';

/* ------------------------------------------------------------------
 * iOS-style Toggle Switch
 * ------------------------------------------------------------------ */

function ToggleSwitch({
  checked,
  onChange,
  loading = false,
}: {
  checked: boolean;
  onChange: () => void;
  loading?: boolean;
}) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      onClick={onChange}
      disabled={loading}
      className={`relative inline-flex h-6 w-11 flex-shrink-0 items-center rounded-full transition-colors duration-200 focus:outline-none disabled:opacity-50 cursor-pointer ${
        checked ? 'bg-accent-teal' : 'bg-divider'
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform duration-200 ${
          checked ? 'translate-x-6' : 'translate-x-1'
        }`}
      />
    </button>
  );
}

/* ------------------------------------------------------------------
 * WarehouseSettingsTab
 * ------------------------------------------------------------------ */

export default function WarehouseSettingsTab() {
  /* ── Sub-tab ─────────────────────────────────────────────────── */
  const [subTab, setSubTab] = useState<SubTab>('list');
  const [managingWarehouse, setManagingWarehouse] = useState<WarehouseRead | null>(null);

  /* ── Data state ──────────────────────────────────────────────── */
  const [warehouses, setWarehouses]     = useState<WarehouseRead[]>([]);
  const [loading, setLoading]           = useState(true);
  const [error, setError]               = useState<string | null>(null);
  const [search, setSearch]             = useState('');
  const [filterActive, setFilterActive] = useState<FilterActive>('active');
  const [togglingId, setTogglingId]     = useState<number | null>(null);
  const [page, setPage]                 = useState(1);
  const PAGE_SIZE = 20;

  /* ── Modal state ─────────────────────────────────────────────── */
  const [showModal, setShowModal]   = useState(false);
  const [editTarget, setEditTarget] = useState<WarehouseRead | null>(null);
  const [formName, setFormName]     = useState('');
  const [formStreet, setFormStreet] = useState('');
  const [formCity, setFormCity]     = useState('');
  const [formState, setFormState]   = useState('');
  const [formCountry, setFormCountry] = useState('');
  const [formPostcode, setFormPostcode] = useState('');
  const [formActive, setFormActive] = useState(true);
  const [saving, setSaving]         = useState(false);
  const [formError, setFormError]   = useState<string | null>(null);

  /* ── Fetch ───────────────────────────────────────────────────── */
  /* Always fetch ALL warehouses so we can count per-status client-side */
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listWarehouses();
      setWarehouses(data);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  /* ── Counts for tab badges ───────────────────────────────────── */
  const activeCount   = warehouses.filter((w) =>  w.is_active).length;
  const inactiveCount = warehouses.filter((w) => !w.is_active).length;
  const counts: Record<FilterActive, number> = {
    all:      warehouses.length,
    active:   activeCount,
    inactive: inactiveCount,
  };

  /* ── Client-side status + search filter ─────────────────────── */
  const filtered = warehouses.filter((w) => {
    if (filterActive === 'active'   && !w.is_active) return false;
    if (filterActive === 'inactive' &&  w.is_active) return false;
    if (search && !w.warehouse_name.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  /* ── Actions ─────────────────────────────────────────────────── */
  const handleToggle = async (w: WarehouseRead) => {
    setTogglingId(w.id);
    try {
      const updated = await toggleWarehouseStatus(w.id);
      setWarehouses((prev) => prev.map((x) => (x.id === updated.id ? updated : x)));
      if (managingWarehouse?.id === updated.id) setManagingWarehouse(updated);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setTogglingId(null);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteWarehouse(id);
      setWarehouses((prev) => prev.filter((w) => w.id !== id));
      if (managingWarehouse?.id === id) {
        setManagingWarehouse(null);
        setSubTab('list');
      }
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  };

  const handleDuplicate = async (id: number) => {
    try {
      const result = await duplicateWarehouse(id);
      setWarehouses((prev) => [...prev, result.new_warehouse]);
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  };

  const handleManage = (w: WarehouseRead) => {
    setManagingWarehouse(w);
    setSubTab('locations');
  };

  /* ── Modal helpers ───────────────────────────────────────────── */
  const openAdd = () => {
    setEditTarget(null);
    setFormName(''); setFormStreet(''); setFormCity('');
    setFormState(''); setFormCountry(''); setFormPostcode('');
    setFormActive(true); setFormError(null);
    setShowModal(true);
  };

  const openEdit = (w: WarehouseRead) => {
    setEditTarget(w);
    setFormName(w.warehouse_name);
    setFormStreet(w.address?.street   ?? '');
    setFormCity(w.address?.city       ?? '');
    setFormState(w.address?.state     ?? '');
    setFormCountry(w.address?.country ?? '');
    setFormPostcode(w.address?.postcode ?? '');
    setFormActive(w.is_active);
    setFormError(null);
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!formName.trim()) { setFormError('Warehouse name is required.'); return; }
    setSaving(true); setFormError(null);

    const address: Record<string, string> = {};
    if (formStreet.trim())   address.street   = formStreet.trim();
    if (formCity.trim())     address.city     = formCity.trim();
    if (formState.trim())    address.state    = formState.trim();
    if (formCountry.trim())  address.country  = formCountry.trim();
    if (formPostcode.trim()) address.postcode = formPostcode.trim();

    try {
      if (editTarget) {
        const data: WarehouseUpdate = {
          warehouse_name: formName.trim(),
          address: Object.keys(address).length ? address : undefined,
          is_active: formActive,
        };
        const updated = await updateWarehouse(editTarget.id, data);
        setWarehouses((prev) => prev.map((w) => (w.id === updated.id ? updated : w)));
        if (managingWarehouse?.id === updated.id) setManagingWarehouse(updated);
      } else {
        const data: WarehouseCreate = {
          warehouse_name: formName.trim(),
          address: Object.keys(address).length ? address : undefined,
          is_active: formActive,
        };
        const created = await createWarehouse(data);
        setWarehouses((prev) => [...prev, created]);
      }
      setShowModal(false);
    } catch (err) {
      setFormError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  /* ── Table columns ───────────────────────────────────────────── */
  const columns: Column<WarehouseRead>[] = [
    {
      header: 'ID',
      accessor: (w) => <span className="text-text-secondary">{w.id}</span>,
      className: 'w-12',
    },
    {
      header: 'WAREHOUSE NAME',
      accessor: (w) => <span className="font-semibold text-text-primary">{w.warehouse_name}</span>,
      className: 'min-w-[160px]',
    },
    {
      header: 'PRIMARY LOCATION',
      accessor: (w) =>
        w.address?.street
          ? <span>{w.address.street}</span>
          : <span className="text-text-secondary">—</span>,
      className: 'min-w-[180px]',
    },
    {
      header: 'State',
      accessor: (w) =>
        w.address?.state
          ? <span>{w.address.state}</span>
          : <span className="text-text-secondary">—</span>,
      className: 'w-24',
    },
    {
      header: 'Country',
      accessor: (w) =>
        w.address?.country
          ? <span>{w.address.country}</span>
          : <span className="text-text-secondary">—</span>,
      className: 'w-24',
    },
    {
      header: 'STATUS',
      accessor: (w) => (
        <ToggleSwitch
          checked={w.is_active}
          onChange={() => handleToggle(w)}
          loading={togglingId === w.id}
        />
      ),
      className: 'w-20',
    },
    {
      header: 'MANAGE',
      accessor: (w) => (
        <div className="flex items-center gap-1.5">
          <button
            onClick={(e) => { e.stopPropagation(); handleManage(w); }}
            className="flex items-center gap-1 px-3 py-1 text-xs font-medium text-text-primary border border-divider rounded-full hover:border-primary/40 hover:text-primary transition-colors cursor-pointer"
          >
            <ChevronRight size={12} />
            Manage
          </button>
          <div onClick={(e) => e.stopPropagation()}>
            <StandardActionMenu
              usePortal
              onEdit={() => openEdit(w)}
              onDuplicate={() => handleDuplicate(w.id)}
              onDelete={() => handleDelete(w.id)}
              deleteLabel="Delete Warehouse"
              confirmMessage="This will soft-delete the warehouse and all its locations. Historical data is preserved."
            />
          </div>
        </div>
      ),
      className: 'w-40',
    },
  ];

  /* ── Render ──────────────────────────────────────────────────── */
  return (
    <div className="flex flex-col">

      {/* Sub-tab strip */}
      <div className="flex gap-8 border-b border-divider mb-5 -mt-1">
        {(['list', 'locations'] as SubTab[]).map((tab) => {
          const labels: Record<SubTab, string> = {
            list:      'Warehouse List',
            locations: 'Location Setup',
          };
          const isActive = subTab === tab;
          return (
            <button
              key={tab}
              onClick={() => setSubTab(tab)}
              className={`pb-3 text-sm font-medium border-b-2 transition-colors cursor-pointer -mb-px ${
                isActive
                  ? 'border-text-primary text-text-primary'
                  : 'border-transparent text-text-secondary hover:text-text-primary'
              }`}
            >
              {labels[tab]}
            </button>
          );
        })}
      </div>

      {/* ── Warehouse List sub-tab ───────────────────────────── */}
      {subTab === 'list' && (
        <div className="flex flex-col gap-0">

          {/* Error banner */}
          {error && (
            <div className="flex items-center gap-2 bg-error-bg text-error-text rounded-default px-4 py-2.5 text-sm mb-4">
              <XCircle size={15} className="flex-shrink-0" />
              <span className="flex-grow">{error}</span>
              <button onClick={() => setError(null)} className="opacity-60 hover:opacity-100 cursor-pointer">
                <X size={14} />
              </button>
            </div>
          )}

          {/* Toolbar */}
          <div className="flex items-center justify-end gap-2 pb-4">
            <button
              className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-text-secondary border border-divider rounded-default hover:bg-background transition-colors cursor-pointer"
            >
              <Upload size={14} />
              Batch Upload
            </button>
            <button
              onClick={openAdd}
              className="flex items-center gap-1.5 px-4 py-2 bg-secondary text-white rounded-default text-sm font-medium hover:shadow-button-hover transition-shadow cursor-pointer"
            >
              <Plus size={14} />
              Add Warehouse
            </button>
          </div>

          {/* Filter tabs */}
          <div className="flex items-center gap-6 border-b border-divider mb-4">
            {(['all', 'active', 'inactive'] as FilterActive[]).map((f) => {
              const labels: Record<FilterActive, string> = {
                all:      'All',
                active:   'Active',
                inactive: 'Inactive',
              };
              const isSelected = filterActive === f;
              return (
                <button
                  key={f}
                  onClick={() => { setFilterActive(f); setPage(1); }}
                  className={`flex items-center gap-1.5 pb-2.5 text-sm font-medium border-b-2 transition-colors cursor-pointer -mb-px ${
                    isSelected
                      ? 'border-text-primary text-text-primary'
                      : 'border-transparent text-text-secondary hover:text-text-primary'
                  }`}
                >
                  {labels[f]}
                  <span
                    className={`text-xs px-1.5 py-0.5 rounded-full font-semibold ${
                      isSelected
                        ? 'bg-text-primary text-surface'
                        : 'bg-divider text-text-secondary'
                    }`}
                  >
                    {counts[f]}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Table */}
          <DataTable
            columns={columns}
            data={filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)}
            total={filtered.length}
            page={page}
            pageSize={PAGE_SIZE}
            onPageChange={(p) => setPage(p)}
            loading={loading}
            error={null}
            emptyMessage="No warehouses found."
            searchValue={search}
            onSearchChange={(v) => { setSearch(v); setPage(1); }}
            searchPlaceholder="Search warehouses..."
            getRowId={(w) => w.id}
            noCard
          />
        </div>
      )}

      {/* ── Location Setup sub-tab ───────────────────────────── */}
      {subTab === 'locations' && (
        <div className="flex flex-col gap-5">

          {/* Warehouse selector bar */}
          <div className="flex items-center gap-3 p-4 bg-background border border-divider rounded-default">
            <MapPin size={15} className="text-text-secondary flex-shrink-0" />
            <label className="text-sm font-medium text-text-secondary flex-shrink-0">
              Warehouse
            </label>
            <div className="relative flex-grow max-w-sm">
              <select
                value={managingWarehouse?.id ?? ''}
                onChange={(e) => {
                  const id = Number(e.target.value);
                  setManagingWarehouse(warehouses.find((w) => w.id === id) ?? null);
                }}
                className="form-input w-full pr-8 appearance-none cursor-pointer"
                disabled={loading}
              >
                <option value="">— Select a warehouse —</option>
                {warehouses.filter((w) => w.is_active).map((w) => (
                  <option key={w.id} value={w.id}>{w.warehouse_name}</option>
                ))}
                {warehouses.some((w) => !w.is_active) && (
                  <optgroup label="Inactive">
                    {warehouses.filter((w) => !w.is_active).map((w) => (
                      <option key={w.id} value={w.id}>{w.warehouse_name}</option>
                    ))}
                  </optgroup>
                )}
              </select>
              <ChevronDown
                size={14}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-secondary pointer-events-none"
              />
            </div>

            {managingWarehouse && (
              <span
                className={`text-xs px-2 py-0.5 rounded-full font-medium flex-shrink-0 ${
                  managingWarehouse.is_active
                    ? 'bg-success-bg text-success-text'
                    : 'bg-divider text-text-secondary'
                }`}
              >
                {managingWarehouse.is_active ? 'Active' : 'Inactive'}
              </span>
            )}

            {managingWarehouse && (
              <span className="text-xs text-text-secondary flex-shrink-0">
                {managingWarehouse.location_count.toLocaleString()} location{managingWarehouse.location_count !== 1 ? 's' : ''}
              </span>
            )}
          </div>

          {managingWarehouse ? (
            <LocationManagementSection
              overrideWarehouseId={managingWarehouse.id}
              overrideWarehouseName={managingWarehouse.warehouse_name}
            />
          ) : (
            <div className="flex flex-col items-center justify-center py-20 gap-3 text-text-secondary">
              <MapPin size={36} className="opacity-15" />
              <p className="text-sm">Select a warehouse above to manage its locations.</p>
            </div>
          )}
        </div>
      )}

      {/* Add / Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-surface rounded-card shadow-card w-full max-w-md overflow-hidden">

            <div className="flex items-center justify-between px-6 py-4 border-b border-divider">
              <h3 className="text-base font-semibold text-text-primary">
                {editTarget ? 'Edit Warehouse' : 'Add Warehouse'}
              </h3>
              <button
                onClick={() => setShowModal(false)}
                className="p-1 text-text-secondary hover:text-text-primary cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>

            <div className="px-6 py-5 space-y-4 max-h-[70vh] overflow-y-auto">
              {formError && (
                <div className="flex items-start gap-2 bg-error-bg text-error-text rounded-default px-3 py-2 text-sm">
                  <XCircle size={15} className="flex-shrink-0 mt-0.5" />
                  {formError}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1">
                  Warehouse Name <span className="text-error-text">*</span>
                </label>
                <input
                  type="text"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  className="form-input w-full"
                  placeholder="e.g. Main Warehouse"
                  autoFocus
                  disabled={saving}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">
                  Address{' '}
                  <span className="text-text-secondary font-normal">(optional)</span>
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <div className="col-span-2">
                    <input
                      type="text"
                      value={formStreet}
                      onChange={(e) => setFormStreet(e.target.value)}
                      className="form-input w-full"
                      placeholder="Street"
                      disabled={saving}
                    />
                  </div>
                  <input
                    type="text"
                    value={formCity}
                    onChange={(e) => setFormCity(e.target.value)}
                    className="form-input w-full"
                    placeholder="City"
                    disabled={saving}
                  />
                  <input
                    type="text"
                    value={formState}
                    onChange={(e) => setFormState(e.target.value)}
                    className="form-input w-full"
                    placeholder="State"
                    disabled={saving}
                  />
                  <input
                    type="text"
                    value={formCountry}
                    onChange={(e) => setFormCountry(e.target.value)}
                    className="form-input w-full"
                    placeholder="Country"
                    disabled={saving}
                  />
                  <input
                    type="text"
                    value={formPostcode}
                    onChange={(e) => setFormPostcode(e.target.value)}
                    className="form-input w-full"
                    placeholder="Postcode"
                    disabled={saving}
                  />
                </div>
              </div>

              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={formActive}
                  onChange={(e) => setFormActive(e.target.checked)}
                  className="w-4 h-4 rounded border-divider text-primary focus:ring-primary"
                  disabled={saving}
                />
                <span className="text-sm font-medium text-text-primary">Active</span>
              </label>
            </div>

            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-divider">
              <button
                onClick={() => setShowModal(false)}
                disabled={saving}
                className="px-4 py-2 border border-divider rounded-default text-sm font-medium text-text-primary hover:bg-background transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving || !formName.trim()}
                className="px-4 py-2 bg-secondary text-white rounded-default text-sm font-medium hover:shadow-button-hover transition-shadow disabled:opacity-50"
              >
                {saving ? 'Saving…' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

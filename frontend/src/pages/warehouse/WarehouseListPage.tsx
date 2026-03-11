import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import AddIcon from '@mui/icons-material/Add';
import CloseIcon from '@mui/icons-material/Close';
import DataTable, { type Column } from '../../components/common/DataTable';
import StandardActionMenu from '../../components/common/StandardActionMenu';
import PageHeader from '../../components/layout/PageHeader';
import type { WarehouseRead, WarehouseCreate, WarehouseUpdate } from '../../api/base_types/warehouse';
import {
  listWarehouses,
  createWarehouse,
  updateWarehouse,
  toggleWarehouseStatus,
  deleteWarehouse,
  duplicateWarehouse,
} from '../../api/base/warehouse';

function extractErrorMessage(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const resp = (err as { response?: { data?: { detail?: string } } }).response;
    return resp?.data?.detail ?? 'Operation failed';
  }
  return 'Network error';
}

type FilterActive = 'all' | 'active' | 'inactive';

export default function WarehouseListPage() {
  const navigate = useNavigate();

  const [warehouses, setWarehouses] = useState<WarehouseRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [filterActive, setFilterActive] = useState<FilterActive>('all');
  const [successBanner, setSuccessBanner] = useState<string | null>(null);

  /* Modal state */
  const [showModal, setShowModal] = useState(false);
  const [editTarget, setEditTarget] = useState<WarehouseRead | null>(null);
  const [formName, setFormName] = useState('');
  const [formStreet, setFormStreet] = useState('');
  const [formCity, setFormCity] = useState('');
  const [formState, setFormState] = useState('');
  const [formPostcode, setFormPostcode] = useState('');
  const [formActive, setFormActive] = useState(true);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  /* Fetch */
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const isActive = filterActive === 'all' ? undefined : filterActive === 'active';
      const data = await listWarehouses(isActive);
      setWarehouses(data);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [filterActive]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const showSuccess = (msg: string) => {
    setSuccessBanner(msg);
    setTimeout(() => setSuccessBanner(null), 4000);
  };

  /* Search filter (client-side — warehouse counts are small) */
  const filtered = warehouses.filter((w) =>
    !search || w.warehouse_name.toLowerCase().includes(search.toLowerCase()),
  );

  /* Toggle active via dedicated endpoint */
  const handleToggle = async (w: WarehouseRead) => {
    try {
      const updated = await toggleWarehouseStatus(w.id);
      setWarehouses((prev) => prev.map((x) => (x.id === updated.id ? updated : x)));
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  };

  /* Soft delete */
  const handleDelete = async (id: number) => {
    try {
      await deleteWarehouse(id);
      setWarehouses((prev) => prev.filter((w) => w.id !== id));
      showSuccess('Warehouse deleted.');
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  };

  /* Deep duplicate */
  const handleDuplicate = async (id: number) => {
    try {
      const result = await duplicateWarehouse(id);
      setWarehouses((prev) => [...prev, result.new_warehouse]);
      showSuccess(
        `Duplicated as "${result.new_warehouse.warehouse_name}" — ${result.locations_copied} location${result.locations_copied !== 1 ? 's' : ''} copied.`,
      );
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  };

  /* Modal helpers */
  const openAdd = () => {
    setEditTarget(null);
    setFormName('');
    setFormStreet('');
    setFormCity('');
    setFormState('');
    setFormPostcode('');
    setFormActive(true);
    setFormError(null);
    setShowModal(true);
  };

  const openEdit = (w: WarehouseRead) => {
    setEditTarget(w);
    setFormName(w.warehouse_name);
    setFormStreet(w.address?.street ?? '');
    setFormCity(w.address?.city ?? '');
    setFormState(w.address?.state ?? '');
    setFormPostcode(w.address?.postcode ?? '');
    setFormActive(w.is_active);
    setFormError(null);
    setShowModal(true);
  };

  /* Save (create or update) */
  const handleSave = async () => {
    if (!formName.trim()) {
      setFormError('Warehouse name is required');
      return;
    }
    setSaving(true);
    setFormError(null);

    const address: Record<string, string> = {};
    if (formStreet.trim()) address.street = formStreet.trim();
    if (formCity.trim())   address.city   = formCity.trim();
    if (formState.trim())  address.state  = formState.trim();
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

  /* Columns */
  const columns: Column<WarehouseRead>[] = [
    { header: 'ID', accessor: 'id', className: 'w-16' },
    {
      header: 'Name',
      accessor: (w) => (
        <button
          className="text-primary font-medium hover:underline text-left"
          onClick={(e) => {
            e.stopPropagation();
            navigate(`/inventory/levels?warehouse_id=${w.id}`);
          }}
        >
          {w.warehouse_name}
        </button>
      ),
      className: 'min-w-[200px]',
    },
    {
      header: 'Address',
      accessor: (w) => {
        if (!w.address) return <span className="text-text-secondary">—</span>;
        const parts = [w.address.city, w.address.state, w.address.postcode].filter(Boolean);
        return parts.join(', ') || <span className="text-text-secondary">—</span>;
      },
      className: 'min-w-[180px]',
    },
    {
      header: 'Status',
      accessor: (w) => (
        <span
          className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${
            w.is_active
              ? 'bg-success-bg text-success-text'
              : 'bg-background text-text-secondary'
          }`}
        >
          <span className={`w-1.5 h-1.5 rounded-full ${w.is_active ? 'bg-success-text' : 'bg-text-secondary/50'}`} />
          {w.is_active ? 'Active' : 'Inactive'}
        </span>
      ),
      className: 'w-28',
    },
    {
      header: 'Created',
      accessor: (w) => new Date(w.created_at).toLocaleDateString(),
      className: 'w-28',
    },
    {
      header: '',
      accessor: (w) => (
        <StandardActionMenu
          onEdit={() => openEdit(w)}
          onToggleStatus={() => handleToggle(w)}
          isActive={w.is_active}
          onDuplicate={() => handleDuplicate(w.id)}
          onDelete={() => handleDelete(w.id)}
          deleteLabel="Delete Warehouse"
          confirmMessage="This will soft-delete the warehouse and all its locations. Historical inventory data is preserved."
        />
      ),
      className: 'w-12',
    },
  ];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Warehouses"
        description="Manage physical warehouse facilities and their configurations"
      />

      {/* Success banner */}
      {successBanner && (
        <div className="bg-success-bg text-success-text rounded-default px-4 py-3 text-sm font-medium">
          {successBanner}
        </div>
      )}

      {/* Card */}
      <div className="bg-surface rounded-card shadow-card overflow-hidden">
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-4 px-6 py-5 border-b border-divider">
          <div className="flex items-center gap-3">
            <select
              value={filterActive}
              onChange={(e) => setFilterActive(e.target.value as FilterActive)}
              className="h-9 px-3 border border-divider rounded-default bg-surface text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
            >
              <option value="all">All</option>
              <option value="active">Active only</option>
              <option value="inactive">Inactive only</option>
            </select>
          </div>

          <button
            onClick={openAdd}
            className="flex items-center gap-1.5 px-4 py-2 bg-secondary text-white rounded-default text-sm font-medium hover:shadow-button-hover transition-shadow"
          >
            <AddIcon fontSize="small" />
            Add Warehouse
          </button>
        </div>

        {/* DataTable */}
        <DataTable
          columns={columns}
          data={filtered}
          total={filtered.length}
          page={1}
          pageSize={filtered.length || 1}
          onPageChange={() => {}}
          loading={loading}
          error={error}
          emptyMessage="No warehouses found."
          searchValue={search}
          onSearchChange={setSearch}
          searchPlaceholder="Search warehouses..."
          getRowId={(w) => w.id}
          noCard
        />
      </div>

      {/* Create / Edit modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-surface rounded-card shadow-card w-full max-w-md overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-divider">
              <h3 className="text-lg font-semibold text-text-primary">
                {editTarget ? 'Edit Warehouse' : 'Add Warehouse'}
              </h3>
              <button
                onClick={() => setShowModal(false)}
                className="p-1 text-text-secondary hover:text-text-primary cursor-pointer"
              >
                <CloseIcon fontSize="small" />
              </button>
            </div>

            {/* Body */}
            <div className="px-6 py-5 space-y-4 max-h-[70vh] overflow-y-auto">
              {formError && (
                <div className="bg-error-bg text-error-text rounded-default px-3 py-2 text-sm">
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
                  Address <span className="text-text-secondary font-normal">(optional)</span>
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

            {/* Footer */}
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

import { useCallback, useEffect, useState } from 'react';
import AddIcon from '@mui/icons-material/Add';
import CloseIcon from '@mui/icons-material/Close';
import DeleteIcon from '@mui/icons-material/Delete';
import DataTable, { type Column } from '../../components/common/DataTable';
import type {
  InventoryMovementRead,
  InventoryMovementCreate,
  InventoryTransactionCreate,
  InventoryLocationRead,
  MovementTypeRead,
} from '../../api/base_types/warehouse';
import type { ItemRead } from '../../api/base_types/items';
import {
  listMovements,
  createMovement,
  listMovementTypes,
  listLocations,
} from '../../api/base/warehouse';
import { listItems } from '../../api/base/items';
import { useWarehouse } from '../../api/contexts/WarehouseContext';

function extractErrorMessage(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const resp = (err as { response?: { data?: { detail?: string } } }).response;
    return resp?.data?.detail ?? 'Operation failed';
  }
  return 'Network error';
}

interface TxRow {
  location_id: number | '';
  is_inbound: boolean;
  quantity_change: string;
}

const EMPTY_TX: TxRow = { location_id: '', is_inbound: true, quantity_change: '' };

export default function InventoryMovementsPage() {
  const { selectedWarehouseId } = useWarehouse();
  const warehouseId = selectedWarehouseId ?? undefined;
  const [movements, setMovements] = useState<InventoryMovementRead[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /* Modal state */
  const [showModal, setShowModal] = useState(false);
  const [movementTypes, setMovementTypes] = useState<MovementTypeRead[]>([]);
  const [locations, setLocations] = useState<InventoryLocationRead[]>([]);
  const [formTypeId, setFormTypeId] = useState<number | ''>('');
  const [formItemId, setFormItemId] = useState<number | ''>('');
  const [formItemSearch, setFormItemSearch] = useState('');
  const [itemResults, setItemResults] = useState<ItemRead[]>([]);
  const [formRef, setFormRef] = useState('');
  const [formNotes, setFormNotes] = useState('');
  const [txRows, setTxRows] = useState<TxRow[]>([{ ...EMPTY_TX }]);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  /* Fetch movements */
  const fetchMovements = useCallback(async () => {
    if (!warehouseId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await listMovements(warehouseId, { page, page_size: pageSize });
      setMovements(res.items);
      setTotal(res.total);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [warehouseId, page, pageSize]);

  useEffect(() => { fetchMovements(); }, [fetchMovements]);

  /* Load movement types once */
  useEffect(() => {
    listMovementTypes().then(setMovementTypes).catch(() => {});
  }, []);

  /* Load locations when warehouse changes */
  useEffect(() => {
    if (warehouseId) {
      listLocations(warehouseId).then(setLocations).catch(() => {});
    }
  }, [warehouseId]);

  /* Item search autocomplete */
  useEffect(() => {
    if (formItemSearch.length < 2) { setItemResults([]); return; }
    const t = setTimeout(async () => {
      try {
        const res = await listItems({ search: formItemSearch, page_size: 15 });
        setItemResults(res.items);
      } catch { /* ignore */ }
    }, 300);
    return () => clearTimeout(t);
  }, [formItemSearch]);

  /* Open modal */
  const openRecord = () => {
    setFormTypeId('');
    setFormItemId('');
    setFormItemSearch('');
    setItemResults([]);
    setFormRef('');
    setFormNotes('');
    setTxRows([{ ...EMPTY_TX }]);
    setFormError(null);
    setShowModal(true);
  };

  /* Transaction rows */
  const updateTx = (idx: number, patch: Partial<TxRow>) => {
    setTxRows((prev) => prev.map((r, i) => (i === idx ? { ...r, ...patch } : r)));
  };
  const addTxRow = () => setTxRows((prev) => [...prev, { ...EMPTY_TX }]);
  const removeTxRow = (idx: number) => setTxRows((prev) => prev.filter((_, i) => i !== idx));

  /* Submit */
  const handleSubmit = async () => {
    if (!warehouseId || !formTypeId || !formItemId) {
      setFormError('Please fill all required fields');
      return;
    }
    const transactions: InventoryTransactionCreate[] = [];
    for (const tx of txRows) {
      if (!tx.location_id || !tx.quantity_change) {
        setFormError('Fill all transaction fields');
        return;
      }
      transactions.push({
        location_id: Number(tx.location_id),
        is_inbound: tx.is_inbound,
        quantity_change: Number(tx.quantity_change),
      });
    }

    setSaving(true);
    setFormError(null);
    try {
      const body: InventoryMovementCreate = {
        warehouse_id: warehouseId,
        movement_type_id: Number(formTypeId),
        item_id: Number(formItemId),
        transactions,
        reference_number: formRef.trim() || undefined,
        notes: formNotes.trim() || undefined,
      };
      await createMovement(body);
      setShowModal(false);
      await fetchMovements();
    } catch (err) {
      setFormError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  /* Columns */
  const columns: Column<InventoryMovementRead>[] = [
    {
      header: 'Date',
      accessor: (m) => new Date(m.created_at).toLocaleString(),
      className: 'w-44',
    },
    {
      header: 'Type',
      accessor: (m) => (
        <span className="px-2 py-0.5 rounded text-xs font-medium bg-background">
          {m.movement_type.name}
        </span>
      ),
      className: 'w-28',
    },
    {
      header: 'Item',
      accessor: (m) => (
        <div>
          <div className="font-medium text-text-primary">{m.item_name}</div>
          <div className="text-xs text-text-secondary">{m.master_sku}</div>
        </div>
      ),
      className: 'min-w-[180px]',
    },
    { header: 'Ref', accessor: (m) => m.reference_number, className: 'w-28' },
    {
      header: 'Qty',
      accessor: (m) => (
        <span className={`font-semibold ${m.is_inbound ? 'text-success-text' : 'text-error-text'}`}>
          {m.is_inbound ? '+' : '-'}{m.quantity}
        </span>
      ),
      className: 'w-20 text-right',
    },
  ];

  return (
    <div className="space-y-0">
      <div className="bg-surface rounded-card shadow-card overflow-hidden">
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-4 px-6 py-5 border-b border-divider">
          <h2 className="text-xl font-semibold text-text-primary">Inventory Movements</h2>
          <div className="flex items-center gap-3">
            {warehouseId && (
              <button
                onClick={openRecord}
                className="flex items-center gap-1.5 px-4 py-2 bg-secondary text-white rounded-default text-sm font-medium hover:shadow-button-hover transition-shadow"
              >
                <AddIcon fontSize="small" />
                Record Movement
              </button>
            )}
          </div>
        </div>

        {/* No warehouse */}
        {!warehouseId && !loading && (
          <div className="flex items-center justify-center py-16 text-text-secondary">
            Select a warehouse to view movement history.
          </div>
        )}

        {/* DataTable */}
        {warehouseId && (
          <DataTable
            columns={columns}
            data={movements}
            total={total}
            page={page}
            pageSize={pageSize}
            onPageChange={setPage}
            onPageSizeChange={setPageSize}
            loading={loading}
            error={error}
            emptyMessage="No movements recorded."
            getRowId={(m) => m.id}
            noCard
          />
        )}
      </div>

      {/* Record Movement Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-surface rounded-card shadow-card w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-divider">
              <h3 className="text-lg font-semibold text-text-primary">Record Movement</h3>
              <button onClick={() => setShowModal(false)} className="text-text-secondary hover:text-text-primary">
                <CloseIcon fontSize="small" />
              </button>
            </div>

            {/* Body */}
            <div className="px-6 py-5 space-y-4">
              {formError && (
                <div className="bg-error-bg text-error-text rounded-default px-3 py-2 text-sm">{formError}</div>
              )}

              {/* Movement Type */}
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1">Movement Type *</label>
                <select
                  value={formTypeId}
                  onChange={(e) => setFormTypeId(Number(e.target.value))}
                  className="form-input w-full"
                >
                  <option value="" disabled>Select type...</option>
                  {movementTypes.map((mt) => (
                    <option key={mt.id} value={mt.id}>{mt.name}</option>
                  ))}
                </select>
              </div>

              {/* Item search */}
              <div className="relative">
                <label className="block text-sm font-medium text-text-secondary mb-1">Item *</label>
                <input
                  type="text"
                  value={formItemSearch}
                  onChange={(e) => {
                    setFormItemSearch(e.target.value);
                    setFormItemId('');
                  }}
                  className="form-input w-full"
                  placeholder="Search by name or SKU..."
                />
                {itemResults.length > 0 && !formItemId && (
                  <div className="absolute z-10 mt-1 w-full bg-surface border border-divider rounded-default shadow-card max-h-48 overflow-y-auto">
                    {itemResults.map((item) => (
                      <button
                        key={item.item_id}
                        onClick={() => {
                          setFormItemId(item.item_id);
                          setFormItemSearch(`${item.item_name} (${item.master_sku})`);
                          setItemResults([]);
                        }}
                        className="w-full text-left px-3 py-2 hover:bg-background text-sm"
                      >
                        <span className="font-medium">{item.item_name}</span>
                        <span className="text-text-secondary ml-2">{item.master_sku}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Ref & Notes */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-1">Reference No.</label>
                  <input type="text" value={formRef} onChange={(e) => setFormRef(e.target.value)} className="form-input w-full" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-1">Notes</label>
                  <input type="text" value={formNotes} onChange={(e) => setFormNotes(e.target.value)} className="form-input w-full" />
                </div>
              </div>

              {/* Transactions */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-text-secondary">Transactions</label>
                  <button onClick={addTxRow} className="text-xs text-primary hover:underline">+ Add location</button>
                </div>
                <div className="space-y-3">
                  {txRows.map((tx, idx) => (
                    <div key={idx} className="flex items-end gap-2 p-3 bg-background rounded-default">
                      <div className="flex-1">
                        <label className="block text-xs text-text-secondary mb-1">Location *</label>
                        <select
                          value={tx.location_id}
                          onChange={(e) => updateTx(idx, { location_id: Number(e.target.value) })}
                          className="form-input w-full text-sm"
                        >
                          <option value="" disabled>Select...</option>
                          {locations.map((loc) => {
                            const code = [loc.section, loc.zone, loc.aisle, loc.rack, loc.bin]
                              .filter(Boolean).join('-') || `Loc ${loc.id}`;
                            return <option key={loc.id} value={loc.id}>{code}</option>;
                          })}
                        </select>
                      </div>
                      <div className="w-24">
                        <label className="block text-xs text-text-secondary mb-1">Direction</label>
                        <select
                          value={tx.is_inbound ? 'in' : 'out'}
                          onChange={(e) => updateTx(idx, { is_inbound: e.target.value === 'in' })}
                          className="form-input w-full text-sm"
                        >
                          <option value="in">In</option>
                          <option value="out">Out</option>
                        </select>
                      </div>
                      <div className="w-20">
                        <label className="block text-xs text-text-secondary mb-1">Qty *</label>
                        <input
                          type="number"
                          min={1}
                          value={tx.quantity_change}
                          onChange={(e) => updateTx(idx, { quantity_change: e.target.value })}
                          className="form-input w-full text-sm"
                        />
                      </div>
                      {txRows.length > 1 && (
                        <button
                          onClick={() => removeTxRow(idx)}
                          className="text-error-text hover:text-error-text/70 p-1"
                        >
                          <DeleteIcon fontSize="small" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-divider">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 border border-divider rounded-default text-sm font-medium text-text-primary hover:bg-background transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                disabled={saving}
                className="px-4 py-2 bg-secondary text-white rounded-default text-sm font-medium hover:shadow-button-hover transition-shadow disabled:opacity-50"
              >
                {saving ? 'Submitting...' : 'Submit'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

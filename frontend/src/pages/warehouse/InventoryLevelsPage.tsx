import { useCallback, useEffect, useRef, useState } from 'react';
import DataTable, { type Column } from '../../components/common/DataTable';
import type { InventoryLevelEnrichedRead, StockStatus } from '../../api/base_types/warehouse';
import { listInventoryLevels } from '../../api/base/warehouse';
import { useWarehouse } from '../../api/contexts/WarehouseContext';
import StockStatusBadge from './StockStatusBadge';

function extractErrorMessage(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const resp = (err as { response?: { data?: { detail?: string } } }).response;
    return resp?.data?.detail ?? 'Operation failed';
  }
  return 'Network error';
}

const STATUS_TABS: { key: StockStatus | 'all'; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'ok', label: 'OK' },
  { key: 'low', label: 'Low' },
  { key: 'critical', label: 'Critical' },
  { key: 'out_of_stock', label: 'Out of Stock' },
  { key: 'overstock', label: 'Overstock' },
];


/* ------------------------------------------------------------------
 * Main Page
 * ------------------------------------------------------------------ */

export default function InventoryLevelsPage() {
  const { selectedWarehouseId } = useWarehouse();
  const warehouseId = selectedWarehouseId ?? undefined;
  const [levels, setLevels] = useState<InventoryLevelEnrichedRead[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<StockStatus | 'all'>('all');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  /* Summary counts */
  const [counts, setCounts] = useState<Record<string, number>>({});

  const handleSearchChange = (value: string) => {
    setSearch(value);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebouncedSearch(value);
      setPage(1);
    }, 400);
  };

  const fetchLevels = useCallback(async () => {
    if (!warehouseId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await listInventoryLevels(warehouseId, {
        page,
        page_size: pageSize,
        search: debouncedSearch || undefined,
        stock_status: statusFilter !== 'all' ? statusFilter : undefined,
      });
      setLevels(res.items);
      setTotal(res.total);

      /* Also fetch "all" to compute summary counts when not filtering */
      if (statusFilter === 'all' && !debouncedSearch) {
        const countMap: Record<string, number> = {};
        for (const lv of res.items) {
          countMap[lv.stock_status] = (countMap[lv.stock_status] ?? 0) + 1;
        }
        setCounts(countMap);
      }
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [warehouseId, page, pageSize, debouncedSearch, statusFilter]);

  useEffect(() => { fetchLevels(); }, [fetchLevels]);

  /* Columns */
  const columns: Column<InventoryLevelEnrichedRead>[] = [
    {
      header: 'Item',
      accessor: (lv) => (
        <div>
          <div className="font-medium text-text-primary">{lv.item_name}</div>
          <div className="text-xs text-text-secondary">{lv.master_sku}</div>
        </div>
      ),
      className: 'min-w-[200px]',
    },
    {
      header: 'Location',
      accessor: (lv) => (
        <span className="text-xs font-mono bg-background px-2 py-0.5 rounded">
          {lv.location.code}
        </span>
      ),
      className: 'min-w-[120px]',
    },
    {
      header: 'Qty',
      accessor: (lv) => (
        <div className="text-right">
          <div className="font-semibold">{lv.quantity_available}</div>
          {lv.reserved_quantity > 0 && (
            <div className="text-xs text-text-secondary">{lv.reserved_quantity} reserved</div>
          )}
        </div>
      ),
      className: 'w-24 text-right',
    },
    {
      header: 'Reorder Pt',
      accessor: (lv) => lv.reorder_point ?? null,
      className: 'w-24 text-right',
    },
    {
      header: 'Safety Stock',
      accessor: (lv) => lv.safety_stock ?? null,
      className: 'w-24 text-right',
    },
    {
      header: 'Max Stock',
      accessor: (lv) => lv.max_stock ?? null,
      className: 'w-24 text-right',
    },
    {
      header: 'Status',
      accessor: (lv) => <StockStatusBadge status={lv.stock_status} />,
      className: 'w-32',
    },
  ];

  return (
    <div>
      <div className="bg-surface rounded-card shadow-card overflow-hidden">
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-4 px-6 py-5 border-b border-divider">
          <h2 className="text-xl font-semibold text-text-primary">Inventory Levels</h2>
        </div>

        {/* Summary chips */}
        {warehouseId && Object.keys(counts).length > 0 && (
          <div className="flex flex-wrap gap-2 px-6 py-3 border-b border-divider">
            {STATUS_TABS.filter((t) => t.key !== 'all').map((t) => (
              <span
                key={t.key}
                className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-background text-text-secondary"
              >
                {t.label}: <span className="font-semibold text-text-primary">{counts[t.key] ?? 0}</span>
              </span>
            ))}
          </div>
        )}

        {/* Status filter tabs */}
        {warehouseId && (
          <div className="flex items-center gap-0 px-6 border-b border-divider overflow-x-auto">
            {STATUS_TABS.map((t) => (
              <button
                key={t.key}
                onClick={() => { setStatusFilter(t.key); setPage(1); }}
                className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                  statusFilter === t.key
                    ? 'border-secondary text-secondary'
                    : 'border-transparent text-text-secondary hover:text-text-primary'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        )}

        {/* No warehouse selected */}
        {!warehouseId && !loading && (
          <div className="flex items-center justify-center py-16 text-text-secondary">
            Select a warehouse to view inventory levels.
          </div>
        )}

        {/* DataTable */}
        {warehouseId && (
          <DataTable
            columns={columns}
            data={levels}
            total={total}
            page={page}
            pageSize={pageSize}
            onPageChange={setPage}
            onPageSizeChange={setPageSize}
            loading={loading}
            error={error}
            emptyMessage="No inventory records found."
            searchValue={search}
            onSearchChange={handleSearchChange}
            searchPlaceholder="Search by item name or SKU..."
            getRowId={(lv) => lv.id}
            noCard
          />
        )}
      </div>

    </div>
  );
}

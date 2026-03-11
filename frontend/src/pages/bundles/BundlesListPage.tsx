import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import RestoreFromTrashIcon from '@mui/icons-material/RestoreFromTrash';
import ImageIcon from '@mui/icons-material/Image';
import LayersIcon from '@mui/icons-material/Layers';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import DataTable, { type Column } from '../../components/common/DataTable';
import BundleFilters from './BundleFilters';
import type { BundleListItem, BundleComponentRead } from '../../api/base_types/items';
import {
  listBundles,
  deleteBundle,
  restoreBundle,
  updateBundle,
  getBundleCounts,
  getBundle,
  type ItemCounts,
} from '../../api/base/items';

type Tab = 'all' | 'live' | 'unpublished' | 'deleted';

const TAB_LABELS: { key: Tab; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'live', label: 'Live' },
  { key: 'unpublished', label: 'Unpublished' },
  { key: 'deleted', label: 'Deleted' },
];

function extractErrorMessage(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const e = err as { response?: { data?: { detail?: string } } };
    return e.response?.data?.detail ?? 'Operation failed.';
  }
  return 'Operation failed.';
}

export default function BundlesListPage() {
  const navigate = useNavigate();

  /* ---- State ---- */
  const [bundles, setBundles] = useState<BundleListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [tab, setTab] = useState<Tab>('all');
  const [categoryId, setCategoryId] = useState<number | undefined>();
  const [brandId, setBrandId] = useState<number | undefined>();
  const [selectedIds, setSelectedIds] = useState<Set<number | string>>(new Set());
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [expandedComponents, setExpandedComponents] = useState<BundleComponentRead[]>([]);
  const [expandLoading, setExpandLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<number | null>(null);
  const [restoring, setRestoring] = useState<number | null>(null);
  const [toggling, setToggling] = useState<number | null>(null);
  const [counts, setCounts] = useState<ItemCounts>({ all: 0, live: 0, unpublished: 0, deleted: 0 });

  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  /* ---- Tab → API param mapping ---- */
  const tabParams = useMemo(() => {
    switch (tab) {
      case 'all': return { is_active: undefined, include_deleted: false };
      case 'live': return { is_active: true as const, include_deleted: false };
      case 'unpublished': return { is_active: false as const, include_deleted: false };
      case 'deleted': return { is_active: undefined, include_deleted: true };
    }
  }, [tab]);

  /* ---- Data fetching ---- */
  const fetchCounts = useCallback(async () => {
    try {
      const c = await getBundleCounts();
      setCounts(c);
    } catch { /* silent */ }
  }, []);

  const fetchBundles = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listBundles({
        page,
        page_size: pageSize,
        search: debouncedSearch || undefined,
        is_active: tabParams.is_active,
        include_deleted: tabParams.include_deleted || undefined,
        category_id: categoryId,
        brand_id: brandId,
      });
      setBundles(res.items);
      setTotal(res.total);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, debouncedSearch, tabParams, categoryId, brandId]);

  useEffect(() => { fetchBundles(); }, [fetchBundles]);
  useEffect(() => { fetchCounts(); }, [fetchCounts]);

  /* ---- Search debounce ---- */
  const handleSearchChange = (value: string) => {
    setSearch(value);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebouncedSearch(value);
      setPage(1);
    }, 400);
  };

  /* ---- Tab change ---- */
  const handleTabChange = (t: Tab) => {
    setTab(t);
    setPage(1);
    setSelectedIds(new Set());
    setExpandedId(null);
  };

  /* ---- Delete ---- */
  const handleDelete = async (e: React.MouseEvent, itemId: number, itemName: string) => {
    e.stopPropagation();
    if (!confirm(`Delete "${itemName}"? This action can be undone by an admin.`)) return;
    setDeleting(itemId);
    try {
      await deleteBundle(itemId);
      await Promise.all([fetchBundles(), fetchCounts()]);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setDeleting(null);
    }
  };

  /* ---- Restore ---- */
  const handleRestore = async (e: React.MouseEvent, itemId: number, itemName: string) => {
    e.stopPropagation();
    if (!confirm(`Restore "${itemName}"?`)) return;
    setRestoring(itemId);
    try {
      await restoreBundle(itemId);
      await Promise.all([fetchBundles(), fetchCounts()]);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setRestoring(null);
    }
  };

  /* ---- Toggle active status ---- */
  const handleToggleStatus = async (e: React.MouseEvent, row: BundleListItem) => {
    e.stopPropagation();
    if (row.deleted_at) return;
    setToggling(row.item_id);
    try {
      await updateBundle(row.item_id, { is_active: !row.is_active });
      setBundles((prev) =>
        prev.map((b) => b.item_id === row.item_id ? { ...b, is_active: !b.is_active } : b),
      );
      fetchCounts();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setToggling(null);
    }
  };

  /* ---- Expand: fetch components ---- */
  const handleRowClick = async (row: BundleListItem) => {
    if (row.component_count === 0) return;
    if (expandedId === row.item_id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(row.item_id);
    setExpandLoading(true);
    setExpandedComponents([]);
    try {
      const resp = await getBundle(row.item_id);
      setExpandedComponents(resp.components);
    } catch {
      setExpandedComponents([]);
    } finally {
      setExpandLoading(false);
    }
  };

  /* ---- Columns ---- */
  const columns: Column<BundleListItem>[] = [
    {
      header: 'Bundle',
      accessor: (row) => (
        <div className="flex items-center gap-3">
          {row.image_url ? (
            <img
              src={row.image_url}
              alt=""
              className="w-10 h-10 object-cover rounded-default flex-shrink-0"
            />
          ) : (
            <div className="w-10 h-10 bg-background rounded-default flex-shrink-0 flex items-center justify-center text-text-secondary/40">
              <LayersIcon style={{ fontSize: 18 }} />
            </div>
          )}
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <p className="font-medium text-text-primary truncate">{row.item_name}</p>
              {row.component_count > 0 && (
                <ExpandMoreIcon
                  style={{ fontSize: 16 }}
                  className={`text-text-secondary/60 flex-shrink-0 transition-transform duration-200 ${
                    expandedId === row.item_id ? 'rotate-180' : ''
                  }`}
                />
              )}
            </div>
            <p className="text-xs text-text-secondary">SKU: {row.master_sku}</p>
          </div>
        </div>
      ),
      className: 'min-w-[250px]',
    },
    {
      header: 'Components',
      accessor: (row) => {
        if (row.component_count === 0) {
          return <span className="text-text-secondary">--</span>;
        }
        return (
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-primary/10 text-primary">
              <LayersIcon style={{ fontSize: 12 }} />
              {row.component_count} {row.component_count === 1 ? 'Item' : 'Items'}
            </span>
            <span className="text-xs text-text-secondary">
              ({row.total_quantity} qty)
            </span>
          </div>
        );
      },
    },
    {
      header: 'Category',
      accessor: (row) => row.category?.name ?? '--',
    },
    {
      header: 'Status',
      accessor: (row) => {
        if (row.deleted_at) {
          return (
            <span className="inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-error-bg text-error-text">
              Deleted
            </span>
          );
        }
        const isLoading = toggling === row.item_id;
        return (
          <button
            type="button"
            role="switch"
            aria-checked={row.is_active}
            onClick={(e) => handleToggleStatus(e, row)}
            disabled={isLoading}
            className={`relative inline-flex h-5 w-9 flex-shrink-0 items-center rounded-full transition-colors focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer ${
              row.is_active ? 'bg-primary' : 'bg-divider'
            }`}
            title={row.is_active ? 'Active -- click to deactivate' : 'Inactive -- click to activate'}
          >
            <span
              className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${
                row.is_active ? 'translate-x-4' : 'translate-x-0.5'
              }`}
            />
          </button>
        );
      },
    },
    {
      header: 'Brand',
      accessor: (row) => row.brand?.name ?? '--',
    },
    {
      header: 'Actions',
      accessor: (row) => (
        <div className="flex items-center gap-1">
          <button
            onClick={(e) => { e.stopPropagation(); navigate(`/catalog/bundles/${row.item_id}/edit`); }}
            disabled={!!row.deleted_at}
            className="p-1 text-text-secondary hover:text-primary cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
            title="Edit"
          >
            <EditIcon fontSize="small" />
          </button>
          {row.deleted_at ? (
            <button
              onClick={(e) => handleRestore(e, row.item_id, row.item_name)}
              disabled={restoring === row.item_id}
              className="p-1 text-text-secondary hover:text-success cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
              title="Restore"
            >
              <RestoreFromTrashIcon fontSize="small" />
            </button>
          ) : (
            <button
              onClick={(e) => handleDelete(e, row.item_id, row.item_name)}
              disabled={deleting === row.item_id}
              className="p-1 text-text-secondary hover:text-error cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
              title="Delete"
            >
              <DeleteIcon fontSize="small" />
            </button>
          )}
        </div>
      ),
      className: 'w-24',
    },
  ];

  /* ---- Expanded row: component breakdown ---- */
  const renderExpandedRow = (row: BundleListItem) => {
    if (expandLoading && expandedId === row.item_id) {
      return (
        <div className="flex items-center gap-2 py-3 pl-6">
          <span className="inline-block w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
          <span className="text-sm text-text-secondary">Loading components...</span>
        </div>
      );
    }

    if (expandedComponents.length === 0) {
      return (
        <p className="text-sm text-text-secondary italic py-2 pl-6">
          No components found.
        </p>
      );
    }

    return (
      <div className="pl-6">
        <p className="text-xs font-semibold text-text-secondary mb-2 uppercase tracking-wide">
          Bundle Components ({expandedComponents.length})
        </p>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-text-secondary text-xs">
              <th className="pb-1 pr-6">Item</th>
              <th className="pb-1 pr-6">SKU</th>
              <th className="pb-1 pr-4">Qty</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-divider">
            {expandedComponents.map((c) => (
              <tr key={c.id}>
                <td className="py-1.5 pr-6 font-medium">{c.item_name}</td>
                <td className="py-1.5 pr-6 font-mono text-xs text-text-secondary">{c.master_sku}</td>
                <td className="py-1.5 pr-4">
                  <span className="inline-block px-2 py-0.5 rounded bg-background text-xs font-medium">
                    x{c.quantity}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div className="bg-surface rounded-card shadow-card overflow-hidden">
      {/* Card Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 px-6 py-5 border-b border-divider">
        <h2 className="text-xl font-semibold text-text-primary">My Bundles</h2>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/catalog/bundles/new')}
            className="flex items-center gap-1.5 px-4 py-2 bg-secondary text-white rounded-default text-sm font-medium hover:bg-secondary-dark cursor-pointer shadow-button-hover"
          >
            <AddIcon fontSize="small" />
            Create New Bundle
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap items-center border-b border-divider px-6 gap-3">
        <div className="flex">
          {TAB_LABELS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => handleTabChange(key)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors cursor-pointer ${
                tab === key
                  ? 'border-secondary text-secondary'
                  : 'border-transparent text-text-secondary hover:text-text-primary'
              }`}
            >
              {label} ({counts[key]})
            </button>
          ))}
        </div>
      </div>

      {/* Filters */}
      <BundleFilters
        search={search}
        onSearchChange={handleSearchChange}
        categoryId={categoryId}
        brandId={brandId}
        onCategoryChange={(id) => { setCategoryId(id); setPage(1); }}
        onBrandChange={(id) => { setBrandId(id); setPage(1); }}
      />

      {/* DataTable (embedded in card — noCard) */}
      <DataTable<BundleListItem>
        columns={columns}
        data={bundles}
        total={total}
        page={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={(size) => { setPageSize(size); setPage(1); }}
        loading={loading}
        error={error}
        emptyMessage="No bundles found. Create your first bundle to get started."
        selectable
        selectedIds={selectedIds}
        onSelectChange={setSelectedIds}
        expandedRowId={expandedId}
        onRowClick={handleRowClick}
        renderExpandedRow={renderExpandedRow}
        getRowId={(row) => row.item_id}
        noCard
      />
    </div>
  );
}

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import RestoreFromTrashIcon from '@mui/icons-material/RestoreFromTrash';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ImageIcon from '@mui/icons-material/Image';
import LayersIcon from '@mui/icons-material/Layers';
import ArrowDropDownIcon from '@mui/icons-material/ArrowDropDown';
import DataTable, { type Column } from '../../components/common/DataTable';
import ItemFilters from './ItemFilters';
import type { ItemRead, BundleListItem, BundleComponentRead } from '../../api/base_types/items';
import type { AttributeItem } from '../../api/base_types/items';
import {
  listItems,
  listBundles,
  deleteItem,
  deleteBundle,
  restoreItem,
  restoreBundle,
  updateItem,
  updateBundle,
  getItemCounts,
  getBundleCounts,
  getBundle,
  listItemTypes,
  type ItemCounts,
} from '../../api/base/items';

/* ------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------ */

type PrimaryTab = 'all' | 'items' | 'bundles';
type StatusTab = 'all' | 'live' | 'unpublished' | 'deleted';

/** Union row type — items use ItemRead, bundles extend with component fields */
type UnifiedRow = ItemRead & {
  component_count?: number;
  total_quantity?: number;
};

const PRIMARY_TABS: { key: PrimaryTab; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'items', label: 'Items' },
  { key: 'bundles', label: 'Bundles' },
];

const STATUS_TABS: { key: StatusTab; label: string }[] = [
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

/* ------------------------------------------------------------------
 * Component
 * ------------------------------------------------------------------ */

export default function ItemsListPage() {
  const navigate = useNavigate();

  /* ---- State ---- */
  const [rows, setRows] = useState<UnifiedRow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [primaryTab, setPrimaryTab] = useState<PrimaryTab>('all');
  const [statusTab, setStatusTab] = useState<StatusTab>('all');
  const [categoryId, setCategoryId] = useState<number | undefined>();
  const [brandId, setBrandId] = useState<number | undefined>();
  const [itemTypeId, setItemTypeId] = useState<number | undefined>();
  const [selectedIds, setSelectedIds] = useState<Set<number | string>>(new Set());
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [expandedComponents, setExpandedComponents] = useState<BundleComponentRead[]>([]);
  const [expandLoading, setExpandLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<number | null>(null);
  const [restoring, setRestoring] = useState<number | null>(null);
  const [toggling, setToggling] = useState<number | null>(null);
  const [itemCounts, setItemCounts] = useState<ItemCounts>({ all: 0, live: 0, unpublished: 0, deleted: 0 });
  const [bundleCounts, setBundleCounts] = useState<ItemCounts>({ all: 0, live: 0, unpublished: 0, deleted: 0 });
  const [itemTypes, setItemTypes] = useState<AttributeItem[]>([]);
  const [bundleTypeId, setBundleTypeId] = useState<number | null>(null);
  const [addMenuOpen, setAddMenuOpen] = useState(false);
  const addMenuRef = useRef<HTMLDivElement>(null);

  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  /* ---- Resolve bundle type ID ---- */
  useEffect(() => {
    listItemTypes().then((types) => {
      setItemTypes(types);
      const bt = types.find((t) => t.name === 'Bundle');
      if (bt) setBundleTypeId(bt.id);
    }).catch(() => {});
  }, []);

  /* ---- Close add menu on outside click ---- */
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (addMenuRef.current && !addMenuRef.current.contains(e.target as Node)) {
        setAddMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  /* ---- Status tab -> API param mapping ---- */
  const statusParams = useMemo(() => {
    switch (statusTab) {
      case 'all': return { is_active: undefined, include_deleted: false };
      case 'live': return { is_active: true as const, include_deleted: false };
      case 'unpublished': return { is_active: false as const, include_deleted: false };
      case 'deleted': return { is_active: undefined, include_deleted: true };
    }
  }, [statusTab]);

  /* ---- Combined counts for status tabs ---- */
  const statusCounts = useMemo((): ItemCounts => {
    if (primaryTab === 'items') return itemCounts;
    if (primaryTab === 'bundles') return bundleCounts;
    return {
      all: itemCounts.all + bundleCounts.all,
      live: itemCounts.live + bundleCounts.live,
      unpublished: itemCounts.unpublished + bundleCounts.unpublished,
      deleted: itemCounts.deleted + bundleCounts.deleted,
    };
  }, [primaryTab, itemCounts, bundleCounts]);

  /* ---- Data fetching ---- */
  const fetchCounts = useCallback(async () => {
    try {
      const [ic, bc] = await Promise.allSettled([
        getItemCounts(bundleTypeId ? { exclude_item_type_id: bundleTypeId } : undefined),
        getBundleCounts(),
      ]);
      if (ic.status === 'fulfilled') setItemCounts(ic.value);
      if (bc.status === 'fulfilled') setBundleCounts(bc.value);
    } catch { /* silent */ }
  }, [bundleTypeId]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (primaryTab === 'bundles') {
        const res = await listBundles({
          page,
          page_size: pageSize,
          search: debouncedSearch || undefined,
          is_active: statusParams.is_active,
          include_deleted: statusParams.include_deleted || undefined,
          category_id: categoryId,
          brand_id: brandId,
        });
        setRows(res.items);
        setTotal(res.total);
      } else {
        const res = await listItems({
          page,
          page_size: pageSize,
          search: debouncedSearch || undefined,
          is_active: statusParams.is_active,
          include_deleted: statusParams.include_deleted || undefined,
          category_id: categoryId,
          brand_id: brandId,
          item_type_id: itemTypeId,
          exclude_item_type_id: primaryTab === 'items' && bundleTypeId ? bundleTypeId : undefined,
        });
        setRows(res.items);
        setTotal(res.total);
      }
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, debouncedSearch, statusParams, categoryId, brandId, itemTypeId, primaryTab, bundleTypeId]);

  useEffect(() => { fetchData(); }, [fetchData]);
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

  /* ---- Tab changes ---- */
  const handlePrimaryTabChange = (t: PrimaryTab) => {
    setPrimaryTab(t);
    setPage(1);
    setSelectedIds(new Set());
    setExpandedId(null);
    setItemTypeId(undefined);
  };

  const handleStatusTabChange = (t: StatusTab) => {
    setStatusTab(t);
    setPage(1);
    setSelectedIds(new Set());
    setExpandedId(null);
  };

  /* ---- Is this row a bundle? ---- */
  const isBundle = useCallback((row: UnifiedRow): boolean => {
    if (bundleTypeId && row.item_type_id === bundleTypeId) return true;
    if (row.item_type?.name === 'Bundle') return true;
    return false;
  }, [bundleTypeId]);

  /* ---- Delete ---- */
  const handleDelete = async (e: React.MouseEvent, row: UnifiedRow) => {
    e.stopPropagation();
    if (!confirm(`Delete "${row.item_name}"? This action can be undone by an admin.`)) return;
    setDeleting(row.item_id);
    try {
      if (isBundle(row)) {
        await deleteBundle(row.item_id);
      } else {
        await deleteItem(row.item_id);
      }
      await Promise.all([fetchData(), fetchCounts()]);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setDeleting(null);
    }
  };

  /* ---- Restore ---- */
  const handleRestore = async (e: React.MouseEvent, row: UnifiedRow) => {
    e.stopPropagation();
    if (!confirm(`Restore "${row.item_name}"?`)) return;
    setRestoring(row.item_id);
    try {
      if (isBundle(row)) {
        await restoreBundle(row.item_id);
      } else {
        await restoreItem(row.item_id);
      }
      await Promise.all([fetchData(), fetchCounts()]);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setRestoring(null);
    }
  };

  /* ---- Toggle active status ---- */
  const handleToggleStatus = async (e: React.MouseEvent, row: UnifiedRow) => {
    e.stopPropagation();
    if (row.deleted_at) return;
    setToggling(row.item_id);
    try {
      if (isBundle(row)) {
        await updateBundle(row.item_id, { is_active: !row.is_active });
      } else {
        await updateItem(row.item_id, { is_active: !row.is_active });
      }
      setRows((prev) => prev.map((i) => (i.item_id === row.item_id ? { ...i, is_active: !i.is_active } : i)));
      fetchCounts();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setToggling(null);
    }
  };

  /* ---- Expand: fetch components (bundle) or show variations (item) ---- */
  const handleRowClick = async (row: UnifiedRow) => {
    const isBundleRow = isBundle(row);
    const hasExpandable = isBundleRow
      ? ((row as BundleListItem).component_count ?? 0) > 0
      : row.has_variation;

    if (!hasExpandable) return;

    if (expandedId === row.item_id) {
      setExpandedId(null);
      return;
    }

    setExpandedId(row.item_id);

    if (isBundleRow) {
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
    }
  };

  /* ---- Columns ---- */
  const columns: Column<UnifiedRow>[] = [
    {
      header: 'Item',
      accessor: (row) => {
        const isBundleRow = isBundle(row);
        const hasExpandable = isBundleRow
          ? ((row as BundleListItem).component_count ?? 0) > 0
          : row.has_variation;

        return (
          <div className="flex items-center gap-3">
            {row.image_url ? (
              <img
                src={row.image_url}
                alt=""
                className="w-10 h-10 object-cover rounded-default flex-shrink-0"
              />
            ) : (
              <div className="w-10 h-10 bg-background rounded-default flex-shrink-0 flex items-center justify-center text-text-secondary/40">
                {isBundleRow ? <LayersIcon style={{ fontSize: 18 }} /> : <ImageIcon style={{ fontSize: 18 }} />}
              </div>
            )}
            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <p className="font-medium text-text-primary truncate">{row.item_name}</p>
                {hasExpandable && (
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
        );
      },
      className: 'min-w-[250px]',
    },
    {
      header: 'Category',
      accessor: (row) => row.category?.name ?? '—',
    },
    {
      header: 'Item Type',
      accessor: (row) => {
        const typeName = row.item_type?.name ?? '—';
        if (typeName === 'Bundle') {
          return (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-violet-50 text-violet-700">
              <LayersIcon style={{ fontSize: 12 }} />
              Bundle
            </span>
          );
        }
        return typeName;
      },
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
            title={row.is_active ? 'Active — click to deactivate' : 'Inactive — click to activate'}
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
      header: 'UOM',
      accessor: (row) => row.uom?.name ?? '—',
    },
    {
      header: 'Actions',
      accessor: (row) => {
        const isBundleRow = isBundle(row);
        const editPath = isBundleRow
          ? `/catalog/bundles/${row.item_id}/edit`
          : `/catalog/items/${row.item_id}/edit`;

        return (
          <div className="flex items-center gap-1">
            <button
              onClick={(e) => { e.stopPropagation(); navigate(editPath); }}
              disabled={!!row.deleted_at}
              className="p-1 text-text-secondary hover:text-primary cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
              title="Edit"
            >
              <EditIcon fontSize="small" />
            </button>
            {row.deleted_at ? (
              <button
                onClick={(e) => handleRestore(e, row)}
                disabled={restoring === row.item_id}
                className="p-1 text-text-secondary hover:text-success cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                title="Restore"
              >
                <RestoreFromTrashIcon fontSize="small" />
              </button>
            ) : (
              <button
                onClick={(e) => handleDelete(e, row)}
                disabled={deleting === row.item_id}
                className="p-1 text-text-secondary hover:text-error cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                title="Delete"
              >
                <DeleteIcon fontSize="small" />
              </button>
            )}
          </div>
        );
      },
      className: 'w-24',
    },
  ];

  /* ---- Expanded row ---- */
  const renderExpandedRow = (row: UnifiedRow) => {
    const isBundleRow = isBundle(row);

    if (isBundleRow) {
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
            Listing Components ({expandedComponents.length})
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
    }

    // Item: show variations
    const data = row.variations_data as {
      attributes?: { name: string; values: string[] }[];
      combinations?: { values: string[]; sku: string; image: string | null }[];
    } | null;

    const attributes = data?.attributes ?? [];
    const combinations = data?.combinations ?? [];

    if (combinations.length === 0) {
      return (
        <p className="text-sm text-text-secondary italic py-2">
          No variations configured yet.
        </p>
      );
    }

    return (
      <div className="pl-6">
        <p className="text-xs font-semibold text-text-secondary mb-2 uppercase tracking-wide">
          Variations ({combinations.length})
        </p>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-text-secondary text-xs">
              {attributes.map((attr) => (
                <th key={attr.name} className="pb-1 pr-6">{attr.name}</th>
              ))}
              <th className="pb-1 pr-4">SKU</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-divider">
            {combinations.map((combo, i) => (
              <tr key={i}>
                {combo.values.map((val, j) => (
                  <td key={j} className="py-1.5 pr-6">{val}</td>
                ))}
                <td className="py-1.5 pr-4 font-mono text-xs text-text-secondary">
                  {combo.sku || <span className="italic">—</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  /* ---- Primary tab counts ---- */
  const primaryTabCounts = useMemo(() => ({
    all: itemCounts.all + bundleCounts.all,
    items: itemCounts.all,
    bundles: bundleCounts.all,
  }), [itemCounts, bundleCounts]);

  return (
    <div className="bg-surface rounded-card shadow-card overflow-hidden">
      {/* Card Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 px-6 py-5 border-b border-divider">
        <h2 className="text-xl font-semibold text-text-primary">My Items</h2>
        <div className="flex items-center gap-3">
          {/* Mass Upload */}
          <button
            onClick={() => navigate('/catalog/items/upload')}
            className="flex items-center gap-1.5 px-4 py-2 border border-divider rounded-default text-sm font-medium text-text-primary hover:bg-background cursor-pointer"
          >
            <UploadFileIcon fontSize="small" />
            Mass Upload
          </button>
          {/* Add New dropdown */}
          <div ref={addMenuRef} className="relative">
            <button
              onClick={() => setAddMenuOpen(!addMenuOpen)}
              className="flex items-center gap-1 px-4 py-2 bg-secondary text-white rounded-default text-sm font-medium hover:bg-secondary-dark cursor-pointer shadow-button-hover"
            >
              <AddIcon fontSize="small" />
              Add New
              <ArrowDropDownIcon fontSize="small" style={{ marginLeft: -2, marginRight: -4 }} />
            </button>
            {addMenuOpen && (
              <div className="absolute right-0 top-full mt-1 w-48 bg-surface rounded-default shadow-lg border border-divider z-50 py-1">
                <button
                  onClick={() => { setAddMenuOpen(false); navigate('/catalog/items/new'); }}
                  className="w-full text-left px-4 py-2.5 text-sm text-text-primary hover:bg-background transition-colors cursor-pointer flex items-center gap-2"
                >
                  <ImageIcon style={{ fontSize: 16 }} className="text-text-secondary" />
                  Create Item
                </button>
                <button
                  onClick={() => { setAddMenuOpen(false); navigate('/catalog/items/new?type=bundle'); }}
                  className="w-full text-left px-4 py-2.5 text-sm text-text-primary hover:bg-background transition-colors cursor-pointer flex items-center gap-2"
                >
                  <LayersIcon style={{ fontSize: 16 }} className="text-text-secondary" />
                  Create Bundle
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Primary Tabs (All / Items / Bundles) */}
      <div className="flex items-center border-b border-divider px-6">
        {PRIMARY_TABS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => handlePrimaryTabChange(key)}
            className={`px-5 py-3 text-sm font-semibold border-b-2 transition-colors cursor-pointer ${
              primaryTab === key
                ? 'border-primary text-primary'
                : 'border-transparent text-text-secondary hover:text-text-primary'
            }`}
          >
            {label}
            <span className={`ml-1.5 text-xs px-1.5 py-0.5 rounded-full ${
              primaryTab === key
                ? 'bg-primary/10 text-primary'
                : 'bg-background text-text-secondary'
            }`}>
              {primaryTabCounts[key]}
            </span>
          </button>
        ))}
      </div>

      {/* Status Tabs + Item Type filter */}
      <div className="flex flex-wrap items-center justify-between border-b border-divider px-6 gap-3">
        <div className="flex">
          {STATUS_TABS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => handleStatusTabChange(key)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors cursor-pointer ${
                statusTab === key
                  ? 'border-secondary text-secondary'
                  : 'border-transparent text-text-secondary hover:text-text-primary'
              }`}
            >
              {label} ({statusCounts[key]})
            </button>
          ))}
        </div>
        {primaryTab !== 'bundles' && (
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-text-secondary whitespace-nowrap">Item Type :</span>
            <select
              value={itemTypeId ?? ''}
              onChange={(e) => { setItemTypeId(e.target.value ? Number(e.target.value) : undefined); setPage(1); }}
              className="form-input !w-auto !py-1.5 text-sm min-w-[150px]"
            >
              <option value="">Select</option>
              {itemTypes
                .filter((t) => primaryTab === 'items' && bundleTypeId ? t.id !== bundleTypeId : true)
                .map((t) => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
            </select>
          </div>
        )}
      </div>

      {/* Filters */}
      <ItemFilters
        search={search}
        onSearchChange={handleSearchChange}
        categoryId={categoryId}
        brandId={brandId}
        onCategoryChange={(id) => { setCategoryId(id); setPage(1); }}
        onBrandChange={(id) => { setBrandId(id); setPage(1); }}
      />

      {/* DataTable */}
      <DataTable<UnifiedRow>
        columns={columns}
        data={rows}
        total={total}
        page={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={(size) => { setPageSize(size); setPage(1); }}
        loading={loading}
        error={error}
        emptyMessage={
          primaryTab === 'bundles'
            ? 'No bundles found. Create your first bundle to get started.'
            : 'No items found. Create your first item to get started.'
        }
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

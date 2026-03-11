import { useState, useEffect } from 'react';
import PageHeader from '../../components/layout/PageHeader';
import AttributeCard from './AttributeCard';
import PlatformCard from './PlatformCard';
import WarehouseSettingsTab from './WarehouseSettingsTab';
import type { AttributeItem } from '../../api/base_types/items';
import {
  listStatuses, createStatus, updateStatus, deleteStatus,
  listItemTypes, createItemType, updateItemType, deleteItemType,
  listCategories, createCategory, updateCategory, deleteCategory,
  listBrands, createBrand, updateBrand, deleteBrand,
  listUOMs, createUOM, updateUOM, deleteUOM,
} from '../../api/base/items';

/* ── Types ──────────────────────────────────────────────────── */

interface AttrState {
  items: AttributeItem[];
  loading: boolean;
  error: string | null;
}

const initialState: AttrState = { items: [], loading: true, error: null };

function makeHandlers(
  setState: React.Dispatch<React.SetStateAction<AttrState>>,
  createFn: (name: string) => Promise<AttributeItem>,
  updateFn: (id: number, name: string) => Promise<AttributeItem>,
  deleteFn: (id: number) => Promise<void>,
) {
  return {
    onCreate: async (name: string) => {
      const item = await createFn(name);
      setState((p) => ({ ...p, items: [...p.items, item] }));
    },
    onUpdate: async (id: number, name: string) => {
      const item = await updateFn(id, name);
      setState((p) => ({ ...p, items: p.items.map((i) => (i.id === id ? item : i)) }));
    },
    onDelete: async (id: number) => {
      await deleteFn(id);
      setState((p) => ({ ...p, items: p.items.filter((i) => i.id !== id) }));
    },
  };
}

/* ── Tab definitions ────────────────────────────────────────── */

type TabKey = 'items' | 'platforms' | 'warehouse';

const TABS: { key: TabKey; label: string }[] = [
  { key: 'items',     label: 'Items Data' },
  { key: 'platforms', label: 'Platforms'  },
  { key: 'warehouse', label: 'Warehouse'  },
];

/* ── Page ───────────────────────────────────────────────────── */

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabKey>('items');

  const [statuses,   setStatuses]   = useState<AttrState>(initialState);
  const [itemTypes,  setItemTypes]  = useState<AttrState>(initialState);
  const [categories, setCategories] = useState<AttrState>(initialState);
  const [brands,     setBrands]     = useState<AttrState>(initialState);
  const [uoms,       setUOMs]       = useState<AttrState>(initialState);

  useEffect(() => {
    const load = async () => {
      const [s, t, c, b, u] = await Promise.allSettled([
        listStatuses(), listItemTypes(), listCategories(), listBrands(), listUOMs(),
      ]);
      const toState = (r: PromiseSettledResult<AttributeItem[]>): AttrState =>
        r.status === 'fulfilled'
          ? { items: r.value, loading: false, error: null }
          : { items: [], loading: false, error: 'Failed to load.' };
      setStatuses(toState(s));
      setItemTypes(toState(t));
      setCategories(toState(c));
      setBrands(toState(b));
      setUOMs(toState(u));
    };
    load();
  }, []);

  const statusHandlers   = makeHandlers(setStatuses,   createStatus,   updateStatus,   deleteStatus);
  const typeHandlers     = makeHandlers(setItemTypes,   createItemType, updateItemType, deleteItemType);
  const categoryHandlers = makeHandlers(setCategories,  createCategory, updateCategory, deleteCategory);
  const brandHandlers    = makeHandlers(setBrands,      createBrand,    updateBrand,    deleteBrand);
  const uomHandlers      = makeHandlers(setUOMs,        createUOM,      updateUOM,      deleteUOM);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Settings"
        description="System configuration and lookup table management"
      />

      <div className="bg-surface rounded-card shadow-card overflow-hidden">

        {/* Tab strip */}
        <div className="flex border-b border-divider px-6">
          {TABS.map(({ key, label }) => {
            const isActive = key === activeTab;
            return (
              <button
                key={key}
                onClick={() => setActiveTab(key)}
                className={`px-4 py-4 text-sm font-medium border-b-2 transition-colors cursor-pointer -mb-px ${
                  isActive
                    ? 'border-secondary text-secondary'
                    : 'border-transparent text-text-secondary hover:text-text-primary'
                }`}
              >
                {label}
              </button>
            );
          })}
        </div>

        {/* Tab body */}
        <div className="p-6">

          {activeTab === 'items' && (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
              <AttributeCard title="Item Types"       {...itemTypes}   {...typeHandlers} />
              <AttributeCard title="Categories"       {...categories}  {...categoryHandlers} />
              <AttributeCard title="Brands"           {...brands}      {...brandHandlers} />
              <AttributeCard title="Units of Measure" {...uoms}        {...uomHandlers} />
              <AttributeCard title="Statuses"         {...statuses}    {...statusHandlers} />
            </div>
          )}

          {activeTab === 'platforms' && (
            <PlatformCard />
          )}

          {activeTab === 'warehouse' && (
            <WarehouseSettingsTab />
          )}

        </div>
      </div>
    </div>
  );
}

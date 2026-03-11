import { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import type { ReactNode } from 'react';
import type { WarehouseRead } from '../base_types/warehouse';
import { listWarehouses } from '../base/warehouse';

interface WarehouseContextType {
  warehouses: WarehouseRead[];
  selectedWarehouseId: number | null;
  selectedWarehouse: WarehouseRead | null;
  setSelectedWarehouseId: (id: number) => void;
  loading: boolean;
}

const WarehouseContext = createContext<WarehouseContextType | undefined>(undefined);

const STORAGE_KEY = 'selected_warehouse_id';

export function WarehouseProvider({ children }: { children: ReactNode }) {
  const [warehouses, setWarehouses] = useState<WarehouseRead[]>([]);
  const [selectedWarehouseId, setSelectedWarehouseIdState] = useState<number | null>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? Number(stored) : null;
  });
  const [loading, setLoading] = useState(true);

  // Fetch active warehouses on mount
  useEffect(() => {
    let cancelled = false;
    listWarehouses(true)
      .then((data) => {
        if (cancelled) return;
        setWarehouses(data);

        // Auto-select first warehouse if nothing persisted or persisted ID not in list
        const storedId = localStorage.getItem(STORAGE_KEY);
        const parsed = storedId ? Number(storedId) : null;
        const exists = parsed !== null && data.some((w) => w.id === parsed);

        if (!exists && data.length > 0) {
          const firstId = data[0].id;
          setSelectedWarehouseIdState(firstId);
          localStorage.setItem(STORAGE_KEY, String(firstId));
        }
      })
      .catch(() => {
        // Silently fail — warehouses will be empty
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const setSelectedWarehouseId = useCallback((id: number) => {
    setSelectedWarehouseIdState(id);
    localStorage.setItem(STORAGE_KEY, String(id));
  }, []);

  const selectedWarehouse = useMemo(
    () => warehouses.find((w) => w.id === selectedWarehouseId) ?? null,
    [warehouses, selectedWarehouseId],
  );

  return (
    <WarehouseContext.Provider
      value={{
        warehouses,
        selectedWarehouseId,
        selectedWarehouse,
        setSelectedWarehouseId,
        loading,
      }}
    >
      {children}
    </WarehouseContext.Provider>
  );
}

export function useWarehouse(): WarehouseContextType {
  const ctx = useContext(WarehouseContext);
  if (ctx === undefined) {
    throw new Error('useWarehouse must be used within a WarehouseProvider');
  }
  return ctx;
}

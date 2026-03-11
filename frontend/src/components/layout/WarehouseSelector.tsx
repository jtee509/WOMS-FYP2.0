import { useState, useRef, useEffect } from 'react';
import WarehouseIcon from '@mui/icons-material/Warehouse';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import CheckIcon from '@mui/icons-material/Check';
import { useWarehouse } from '../../api/contexts/WarehouseContext';

interface LayoutWarehouseSelectorProps {
  collapsed: boolean;
}

export default function LayoutWarehouseSelector({ collapsed }: LayoutWarehouseSelectorProps) {
  const { warehouses, selectedWarehouseId, selectedWarehouse, setSelectedWarehouseId, loading } =
    useWarehouse();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const displayName = selectedWarehouse?.warehouse_name ?? 'Select warehouse';

  if (loading) {
    return (
      <div
        className="flex items-center gap-2 px-3 py-2"
        style={{ justifyContent: collapsed ? 'center' : 'flex-start' }}
      >
        <WarehouseIcon fontSize="small" className="text-text-secondary" />
        {!collapsed && (
          <span className="text-sm text-text-secondary animate-pulse">Loading...</span>
        )}
      </div>
    );
  }

  if (warehouses.length === 0) {
    return (
      <div
        className="flex items-center gap-2 px-3 py-2"
        style={{ justifyContent: collapsed ? 'center' : 'flex-start' }}
      >
        <WarehouseIcon fontSize="small" className="text-text-secondary" />
        {!collapsed && <span className="text-xs text-text-secondary">No warehouses</span>}
      </div>
    );
  }

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((prev) => !prev)}
        className={`flex items-center gap-2 w-full rounded-full bg-primary/10 text-primary cursor-pointer transition-colors hover:bg-primary/15 ${
          collapsed ? 'justify-center p-2' : 'px-3 py-2'
        }`}
        title={collapsed ? displayName : undefined}
      >
        <WarehouseIcon fontSize="small" />
        {!collapsed && (
          <>
            <span className="text-sm font-medium truncate flex-1 text-left">{displayName}</span>
            <KeyboardArrowDownIcon
              fontSize="small"
              className={`transition-transform shrink-0 ${open ? 'rotate-180' : ''}`}
            />
          </>
        )}
      </button>

      {open && (
        <div
          className={`absolute z-50 mt-1 bg-surface rounded-default shadow-card border border-divider py-1 max-h-60 overflow-y-auto ${
            collapsed ? 'left-full top-0 ml-2 w-52' : 'left-0 right-0 w-full'
          }`}
        >
          {warehouses.map((w) => {
            const isSelected = w.id === selectedWarehouseId;
            return (
              <button
                key={w.id}
                onClick={() => {
                  setSelectedWarehouseId(w.id);
                  setOpen(false);
                }}
                className={`flex items-center gap-2 w-full px-3 py-2 text-sm text-left cursor-pointer transition-colors ${
                  isSelected
                    ? 'bg-primary/10 text-primary font-medium'
                    : 'text-text-primary hover:bg-background'
                }`}
              >
                <span className="truncate flex-1">{w.warehouse_name}</span>
                {isSelected && <CheckIcon fontSize="small" className="text-primary shrink-0" />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

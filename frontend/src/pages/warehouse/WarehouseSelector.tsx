import { useEffect, useState } from 'react';
import type { WarehouseRead } from '../../api/base_types/warehouse';
import { listWarehouses } from '../../api/base/warehouse';

interface WarehouseSelectorProps {
  value: number | undefined;
  onChange: (id: number) => void;
}

export default function WarehouseSelector({ value, onChange }: WarehouseSelectorProps) {
  const [warehouses, setWarehouses] = useState<WarehouseRead[]>([]);

  useEffect(() => {
    listWarehouses(true).then(setWarehouses).catch(() => {});
  }, []);

  return (
    <select
      value={value ?? ''}
      onChange={(e) => onChange(Number(e.target.value))}
      className="h-10 px-3 border border-divider rounded-default bg-surface text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
    >
      <option value="" disabled>Select warehouse...</option>
      {warehouses.map((w) => (
        <option key={w.id} value={w.id}>{w.warehouse_name}</option>
      ))}
    </select>
  );
}

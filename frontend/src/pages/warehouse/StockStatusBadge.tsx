import type { StockStatus } from '../../api/base_types/warehouse';

const STATUS_CONFIG: Record<StockStatus, { label: string; classes: string }> = {
  ok:           { label: 'OK',           classes: 'bg-success-bg text-success-text' },
  low:          { label: 'Low',          classes: 'bg-warning-bg text-warning-text' },
  critical:     { label: 'Critical',     classes: 'bg-error-bg text-error-text' },
  out_of_stock: { label: 'Out of Stock', classes: 'bg-error-bg text-error-text' },
  overstock:    { label: 'Overstock',    classes: 'bg-info-bg text-info-text' },
};

interface StockStatusBadgeProps {
  status: StockStatus;
}

export default function StockStatusBadge({ status }: StockStatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? STATUS_CONFIG.ok;
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${config.classes}`}>
      {config.label}
    </span>
  );
}

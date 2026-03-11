import { useCallback, useEffect, useState } from 'react';
import CloseIcon from '@mui/icons-material/Close';
import DataTable, { type Column } from '../../components/common/DataTable';
import type { InventoryAlertRead } from '../../api/base_types/warehouse';
import { listAlerts, resolveAlert } from '../../api/base/warehouse';
import { useWarehouse } from '../../api/contexts/WarehouseContext';

function extractErrorMessage(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const resp = (err as { response?: { data?: { detail?: string } } }).response;
    return resp?.data?.detail ?? 'Operation failed';
  }
  return 'Network error';
}

type ResolvedFilter = 'unresolved' | 'all' | 'resolved';

const ALERT_ICON: Record<string, { icon: string; classes: string }> = {
  critical:     { icon: '!!', classes: 'bg-error-bg text-error-text' },
  out_of_stock: { icon: 'X',  classes: 'bg-error-bg text-error-text' },
  low_stock:    { icon: '!',  classes: 'bg-warning-bg text-warning-text' },
  overstock:    { icon: 'i',  classes: 'bg-info-bg text-info-text' },
};

export default function InventoryAlertsPage() {
  const { selectedWarehouseId } = useWarehouse();
  const warehouseId = selectedWarehouseId ?? undefined;
  const [alerts, setAlerts] = useState<InventoryAlertRead[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterResolved, setFilterResolved] = useState<ResolvedFilter>('unresolved');

  /* Resolve modal */
  const [resolveTarget, setResolveTarget] = useState<InventoryAlertRead | null>(null);
  const [resolveNotes, setResolveNotes] = useState('');
  const [resolving, setResolving] = useState(false);
  const [resolveError, setResolveError] = useState<string | null>(null);

  const fetchAlerts = useCallback(async () => {
    if (!warehouseId) return;
    setLoading(true);
    setError(null);
    try {
      const isResolved = filterResolved === 'all' ? undefined : filterResolved === 'resolved';
      const data = await listAlerts(warehouseId, isResolved);
      setAlerts(data);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [warehouseId, filterResolved]);

  useEffect(() => { fetchAlerts(); }, [fetchAlerts]);

  /* Summary counts */
  const counts: Record<string, number> = {};
  alerts.forEach((a) => {
    counts[a.alert_type] = (counts[a.alert_type] ?? 0) + 1;
  });

  /* Open resolve modal */
  const openResolve = (alert: InventoryAlertRead) => {
    setResolveTarget(alert);
    setResolveNotes('');
    setResolveError(null);
  };

  /* Submit resolve */
  const handleResolve = async () => {
    if (!resolveTarget) return;
    setResolving(true);
    setResolveError(null);
    try {
      await resolveAlert(resolveTarget.id, {
        resolution_notes: resolveNotes.trim() || undefined,
      });
      setResolveTarget(null);
      await fetchAlerts();
    } catch (err) {
      setResolveError(extractErrorMessage(err));
    } finally {
      setResolving(false);
    }
  };

  /* Columns */
  const columns: Column<InventoryAlertRead>[] = [
    {
      header: 'Type',
      accessor: (a) => {
        const cfg = ALERT_ICON[a.alert_type] ?? ALERT_ICON.low_stock;
        return (
          <span className={`inline-flex items-center justify-center w-8 h-8 rounded-full text-xs font-bold ${cfg.classes}`}>
            {cfg.icon}
          </span>
        );
      },
      className: 'w-16',
    },
    {
      header: 'Alert Type',
      accessor: (a) => (
        <span className="text-sm font-medium capitalize">
          {a.alert_type.replace(/_/g, ' ')}
        </span>
      ),
      className: 'w-32',
    },
    {
      header: 'Message',
      accessor: (a) => a.alert_message,
      className: 'min-w-[200px]',
    },
    {
      header: 'Current Qty',
      accessor: 'current_quantity',
      className: 'w-24 text-right',
    },
    {
      header: 'Threshold',
      accessor: 'threshold_quantity',
      className: 'w-24 text-right',
    },
    {
      header: 'Status',
      accessor: (a) => (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
          a.is_resolved
            ? 'bg-success-bg text-success-text'
            : 'bg-warning-bg text-warning-text'
        }`}>
          {a.is_resolved ? 'Resolved' : 'Open'}
        </span>
      ),
      className: 'w-24',
    },
    {
      header: 'Action',
      accessor: (a) =>
        !a.is_resolved ? (
          <button
            onClick={(e) => { e.stopPropagation(); openResolve(a); }}
            className="px-3 py-1 border border-primary text-primary rounded-default text-xs font-medium hover:bg-primary/10 transition-colors"
          >
            Resolve
          </button>
        ) : (
          <span className="text-xs text-text-secondary">
            {a.resolved_at ? new Date(a.resolved_at).toLocaleDateString() : ''}
          </span>
        ),
      className: 'w-24',
    },
  ];

  return (
    <div className="space-y-0">
      <div className="bg-surface rounded-card shadow-card overflow-hidden">
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-4 px-6 py-5 border-b border-divider">
          <h2 className="text-xl font-semibold text-text-primary">Inventory Alerts</h2>
          <div className="flex items-center gap-3">
            <select
              value={filterResolved}
              onChange={(e) => setFilterResolved(e.target.value as ResolvedFilter)}
              className="h-10 px-3 border border-divider rounded-default bg-surface text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
            >
              <option value="unresolved">Unresolved</option>
              <option value="all">All</option>
              <option value="resolved">Resolved</option>
            </select>
          </div>
        </div>

        {/* Summary chips */}
        {warehouseId && Object.keys(counts).length > 0 && (
          <div className="flex flex-wrap gap-2 px-6 py-3 border-b border-divider">
            {Object.entries(counts).map(([type, count]) => {
              const cfg = ALERT_ICON[type] ?? ALERT_ICON.low_stock;
              return (
                <span key={type} className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${cfg.classes}`}>
                  <span className="capitalize">{type.replace(/_/g, ' ')}</span>: <span className="font-semibold">{count}</span>
                </span>
              );
            })}
          </div>
        )}

        {/* No warehouse */}
        {!warehouseId && !loading && (
          <div className="flex items-center justify-center py-16 text-text-secondary">
            Select a warehouse to view alerts.
          </div>
        )}

        {/* DataTable */}
        {warehouseId && (
          <DataTable
            columns={columns}
            data={alerts}
            total={alerts.length}
            page={1}
            pageSize={alerts.length || 1}
            onPageChange={() => {}}
            loading={loading}
            error={error}
            emptyMessage="No alerts found."
            getRowId={(a) => a.id}
            noCard
          />
        )}
      </div>

      {/* Resolve Modal */}
      {resolveTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-surface rounded-card shadow-card w-full max-w-sm mx-4">
            <div className="flex items-center justify-between px-6 py-4 border-b border-divider">
              <h3 className="text-lg font-semibold text-text-primary">Resolve Alert</h3>
              <button onClick={() => setResolveTarget(null)} className="text-text-secondary hover:text-text-primary">
                <CloseIcon fontSize="small" />
              </button>
            </div>

            <div className="px-6 py-5 space-y-4">
              <div className="text-sm text-text-secondary">
                <span className="font-medium capitalize">{resolveTarget.alert_type.replace(/_/g, ' ')}</span>
                {resolveTarget.alert_message && <span> — {resolveTarget.alert_message}</span>}
                <div className="mt-1">Current qty: <span className="font-semibold text-text-primary">{resolveTarget.current_quantity}</span></div>
              </div>

              {resolveError && (
                <div className="bg-error-bg text-error-text rounded-default px-3 py-2 text-sm">{resolveError}</div>
              )}

              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1">Resolution notes (optional)</label>
                <textarea
                  value={resolveNotes}
                  onChange={(e) => setResolveNotes(e.target.value)}
                  rows={3}
                  className="form-input w-full resize-none"
                  placeholder="What was done to resolve this alert?"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-divider">
              <button
                onClick={() => setResolveTarget(null)}
                className="px-4 py-2 border border-divider rounded-default text-sm font-medium text-text-primary hover:bg-background transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleResolve}
                disabled={resolving}
                className="px-4 py-2 bg-secondary text-white rounded-default text-sm font-medium hover:shadow-button-hover transition-shadow disabled:opacity-50"
              >
                {resolving ? 'Resolving...' : 'Confirm'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

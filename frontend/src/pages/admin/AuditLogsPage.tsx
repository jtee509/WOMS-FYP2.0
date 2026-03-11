import { useState } from 'react';
import PageHeader from '../../components/layout/PageHeader';
import SearchBar from '../../components/common/SearchBar';
import FileDownloadIcon from '@mui/icons-material/FileDownload';
import FilterListIcon from '@mui/icons-material/FilterList';
import AssignmentIcon from '@mui/icons-material/Assignment';

/* ── Column headers ──────────────────────────────────────────── */

const COLUMNS = ['Timestamp', 'User', 'Action', 'Module', 'Description', 'IP Address'];

/* ── Action type badge ───────────────────────────────────────── */

type ActionType = 'CREATE' | 'UPDATE' | 'DELETE' | 'LOGIN' | 'EXPORT';

const ACTION_STYLES: Record<ActionType, string> = {
  CREATE: 'bg-success-bg text-success-text',
  UPDATE: 'bg-primary/10 text-primary',
  DELETE: 'bg-error-bg text-error-text',
  LOGIN:  'bg-secondary/10 text-secondary',
  EXPORT: 'bg-warning-bg text-warning-text',
};

function ActionBadge({ action }: { action: ActionType }) {
  const cls = ACTION_STYLES[action] ?? 'bg-background text-text-secondary';
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${cls}`}>
      {action}
    </span>
  );
}

/* ── Skeleton rows ───────────────────────────────────────────── */

function SkeletonRows() {
  return (
    <>
      {[...Array(5)].map((_, i) => (
        <tr key={i} className="border-b border-divider animate-pulse">
          {COLUMNS.map((col) => (
            <td key={col} className="px-4 py-3">
              <div
                className="h-3.5 bg-divider rounded-full"
                style={{ width: `${50 + (i * 11 + col.length * 5) % 40}%` }}
              />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

/* ── Empty / coming-soon state ───────────────────────────────── */

function ComingSoonState() {
  return (
    <tr>
      <td colSpan={COLUMNS.length}>
        <div className="flex flex-col items-center justify-center py-16 gap-3">
          <div className="w-14 h-14 rounded-full bg-primary/8 flex items-center justify-center text-primary opacity-70">
            <AssignmentIcon style={{ fontSize: 28 }} />
          </div>
          <div className="text-center">
            <p className="text-sm font-semibold text-text-secondary">Audit logging is not yet active.</p>
            <p className="text-xs text-text-secondary/70 mt-1">
              Once enabled, all system events (creates, updates, deletes, logins) will appear here.
            </p>
          </div>
        </div>
      </td>
    </tr>
  );
}

/* ── Filter bar ──────────────────────────────────────────────── */

const MODULE_OPTIONS = ['All Modules', 'Items', 'Inventory', 'Orders', 'Warehouse', 'Settings', 'Users'];
const ACTION_OPTIONS = ['All Actions', 'CREATE', 'UPDATE', 'DELETE', 'LOGIN', 'EXPORT'];

function FilterBar({
  search,
  onSearchChange,
  module,
  onModuleChange,
  action,
  onActionChange,
}: {
  search: string;
  onSearchChange: (v: string) => void;
  module: string;
  onModuleChange: (v: string) => void;
  action: string;
  onActionChange: (v: string) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-3 p-4 border-b border-divider bg-background/40">
      {/* Search */}
      <SearchBar
        value={search}
        onChange={onSearchChange}
        placeholder="Search user or description…"
        className="flex-1 min-w-[200px] max-w-xs"
      />

      <div className="flex items-center gap-2 text-text-secondary">
        <FilterListIcon style={{ fontSize: 16 }} />
        <span className="text-xs font-medium">Filter:</span>
      </div>

      {/* Module filter */}
      <select
        value={module}
        onChange={(e) => onModuleChange(e.target.value)}
        className="form-input !w-auto !py-1.5 text-sm"
      >
        {MODULE_OPTIONS.map((m) => (
          <option key={m} value={m}>{m}</option>
        ))}
      </select>

      {/* Action filter */}
      <select
        value={action}
        onChange={(e) => onActionChange(e.target.value)}
        className="form-input !w-auto !py-1.5 text-sm"
      >
        {ACTION_OPTIONS.map((a) => (
          <option key={a} value={a}>{a}</option>
        ))}
      </select>

      {/* Date range placeholder */}
      <div className="flex items-center gap-1.5">
        <input type="date" className="form-input !w-auto !py-1.5 text-sm" disabled title="Coming soon" />
        <span className="text-text-secondary text-xs">to</span>
        <input type="date" className="form-input !w-auto !py-1.5 text-sm" disabled title="Coming soon" />
      </div>

      {/* Export button */}
      <button
        disabled
        className="ml-auto flex items-center gap-1.5 px-3 py-1.5 border border-divider rounded-default text-sm font-medium text-text-secondary opacity-50 cursor-not-allowed"
        title="Coming soon"
      >
        <FileDownloadIcon style={{ fontSize: 16 }} />
        Export
      </button>
    </div>
  );
}

/* ── Page ───────────────────────────────────────────────────── */

export default function AuditLogsPage() {
  const [search, setSearch]     = useState('');
  const [module, setModule]     = useState('All Modules');
  const [action, setAction]     = useState('All Actions');

  /* Demo preview data — illustrative only */
  const PREVIEW_ROWS: {
    timestamp: string;
    user: string;
    action: ActionType;
    module: string;
    description: string;
    ip: string;
  }[] = [
    { timestamp: '2026-03-07 09:14:22', user: 'admin@woms.local', action: 'LOGIN',  module: 'Auth',      description: 'Successful login',              ip: '192.168.1.10' },
    { timestamp: '2026-03-07 09:18:05', user: 'admin@woms.local', action: 'CREATE', module: 'Items',     description: 'Created item "Product A"',       ip: '192.168.1.10' },
    { timestamp: '2026-03-07 09:22:47', user: 'admin@woms.local', action: 'UPDATE', module: 'Warehouse', description: 'Updated warehouse "Main Store"',  ip: '192.168.1.10' },
    { timestamp: '2026-03-07 09:31:58', user: 'admin@woms.local', action: 'DELETE', module: 'Items',     description: 'Soft-deleted item "Old SKU"',     ip: '192.168.1.10' },
    { timestamp: '2026-03-07 09:45:10', user: 'admin@woms.local', action: 'EXPORT', module: 'Orders',    description: 'Exported 142 orders to CSV',      ip: '192.168.1.10' },
  ];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Audit Logs"
        description="Track all system activity — user actions, changes, and access events"
      />

      <div className="bg-surface rounded-card shadow-card overflow-hidden">
        {/* Filter bar */}
        <FilterBar
          search={search}
          onSearchChange={setSearch}
          module={module}
          onModuleChange={setModule}
          action={action}
          onActionChange={setAction}
        />

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b border-divider bg-background">
              <tr>
                {COLUMNS.map((col) => (
                  <th
                    key={col}
                    className="px-4 py-3 text-left text-xs font-semibold text-text-secondary uppercase tracking-wide whitespace-nowrap"
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>

            <tbody className="divide-y divide-divider">
              {/* Preview rows — greyed out with "preview" label */}
              {PREVIEW_ROWS.map((row, i) => (
                <tr key={i} className="opacity-40 pointer-events-none">
                  <td className="px-4 py-3 font-mono text-xs text-text-secondary whitespace-nowrap">
                    {row.timestamp}
                  </td>
                  <td className="px-4 py-3 text-text-primary whitespace-nowrap">{row.user}</td>
                  <td className="px-4 py-3"><ActionBadge action={row.action} /></td>
                  <td className="px-4 py-3 text-text-secondary whitespace-nowrap">{row.module}</td>
                  <td className="px-4 py-3 text-text-secondary">{row.description}</td>
                  <td className="px-4 py-3 font-mono text-xs text-text-secondary whitespace-nowrap">
                    {row.ip}
                  </td>
                </tr>
              ))}

              <ComingSoonState />
            </tbody>
          </table>
        </div>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-divider bg-background/30 flex items-center justify-between">
          <p className="text-xs text-text-secondary/70">
            Audit logging backend is under development. Preview data shown above is illustrative only.
          </p>
          <span className="text-xs font-mono text-text-secondary/50">0 records</span>
        </div>
      </div>
    </div>
  );
}

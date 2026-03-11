import { useState } from 'react';
import PageHeader from '../../components/layout/PageHeader';
import PeopleIcon from '@mui/icons-material/People';
import ShieldIcon from '@mui/icons-material/Shield';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import AddIcon from '@mui/icons-material/Add';
import SearchBar from '../../components/common/SearchBar';

/* ── Tab definitions ─────────────────────────────────────────── */

type Tab = 'users' | 'roles';

const TABS: { key: Tab; label: string; icon: React.ReactNode }[] = [
  { key: 'users', label: 'Users',       icon: <PeopleIcon style={{ fontSize: 16 }} /> },
  { key: 'roles', label: 'Roles',       icon: <ShieldIcon style={{ fontSize: 16 }} /> },
];

/* ── Role badge ──────────────────────────────────────────────── */

const ROLE_COLORS: Record<string, string> = {
  Admin:   'bg-primary/10 text-primary',
  Manager: 'bg-secondary/10 text-secondary',
  Staff:   'bg-success-bg text-success-text',
  Viewer:  'bg-background text-text-secondary border border-divider',
};

function RoleBadge({ role }: { role: string }) {
  const cls = ROLE_COLORS[role] ?? 'bg-background text-text-secondary border border-divider';
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${cls}`}>
      {role}
    </span>
  );
}

/* ── Status badge ────────────────────────────────────────────── */

function StatusBadge({ active }: { active: boolean }) {
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${
        active
          ? 'bg-success-bg text-success-text'
          : 'bg-background text-text-secondary border border-divider'
      }`}
    >
      {active ? 'Active' : 'Inactive'}
    </span>
  );
}

/* ── Empty state ─────────────────────────────────────────────── */

function EmptyState({ icon, title, description, action }: {
  icon: React.ReactNode;
  title: string;
  description: string;
  action: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-4">
      <div className="w-16 h-16 rounded-full bg-primary/8 flex items-center justify-center text-primary">
        {icon}
      </div>
      <div className="text-center">
        <p className="text-base font-semibold text-text-primary">{title}</p>
        <p className="text-sm text-text-secondary mt-1">{description}</p>
      </div>
      {action}
    </div>
  );
}

/* ── Coming-soon column header ───────────────────────────────── */

const USER_COLUMNS  = ['User', 'Email', 'Role', 'Status', 'Last Login', 'Actions'];
const ROLE_COLUMNS  = ['Role Name', 'Description', 'Permissions', 'Assigned Users', 'Actions'];

function TableSkeleton({ columns }: { columns: string[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="border-b border-divider bg-background">
          <tr>
            {columns.map((col) => (
              <th
                key={col}
                className="px-4 py-3 text-left text-xs font-semibold text-text-secondary uppercase tracking-wide whitespace-nowrap"
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {[...Array(3)].map((_, i) => (
            <tr key={i} className="border-b border-divider animate-pulse">
              {columns.map((col) => (
                <td key={col} className="px-4 py-3">
                  <div className="h-4 bg-divider rounded-full" style={{ width: `${60 + (i * 13 + col.length * 4) % 30}%` }} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="flex flex-col items-center justify-center py-12 gap-3">
        <div className="w-10 h-10 rounded-full bg-primary/8 flex items-center justify-center text-primary opacity-60">
          <PeopleIcon style={{ fontSize: 22 }} />
        </div>
        <p className="text-sm font-medium text-text-secondary">User management is not yet available.</p>
        <p className="text-xs text-text-secondary/70">This module is under development. Check back soon.</p>
      </div>
    </div>
  );
}

/* ── Users tab ───────────────────────────────────────────────── */

function UsersTab() {
  const [search, setSearch] = useState('');

  return (
    <div className="flex flex-col gap-4">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Search */}
        <SearchBar
          value={search}
          onChange={setSearch}
          placeholder="Search users…"
          className="w-56"
        />
        {/* Invite button */}
        <button
          disabled
          className="flex items-center gap-1.5 px-4 py-1.5 bg-primary text-white rounded-default text-sm font-medium opacity-50 cursor-not-allowed"
          title="Coming soon"
        >
          <PersonAddIcon style={{ fontSize: 16 }} />
          Invite User
        </button>
      </div>

      {/* Table */}
      <div className="border border-divider rounded-default overflow-hidden">
        <TableSkeleton columns={USER_COLUMNS} />
      </div>
    </div>
  );
}

/* ── Roles tab ───────────────────────────────────────────────── */

function RolesTab() {
  /* Preview role cards — illustrative, not live data */
  const PREVIEW_ROLES = [
    { name: 'Admin',   description: 'Full system access — manage all modules, users, and configuration.',   users: 1 },
    { name: 'Manager', description: 'Can manage inventory, orders, and warehouse but cannot edit system settings.',  users: 0 },
    { name: 'Staff',   description: 'Day-to-day operations: view and update inventory levels and orders.',   users: 0 },
    { name: 'Viewer',  description: 'Read-only access to all modules. Cannot create or modify records.',      users: 0 },
  ];

  return (
    <div className="flex flex-col gap-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-text-secondary">
          Roles control what each user can see and do in the system.
        </p>
        <button
          disabled
          className="flex items-center gap-1.5 px-4 py-1.5 bg-primary text-white rounded-default text-sm font-medium opacity-50 cursor-not-allowed"
          title="Coming soon"
        >
          <AddIcon style={{ fontSize: 16 }} />
          Create Role
        </button>
      </div>

      {/* Role cards preview */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {PREVIEW_ROLES.map((role) => (
          <div
            key={role.name}
            className="border border-divider rounded-default p-4 flex flex-col gap-2 opacity-60"
          >
            <div className="flex items-center justify-between">
              <RoleBadge role={role.name} />
              <span className="text-xs text-text-secondary">{role.users} user{role.users !== 1 ? 's' : ''}</span>
            </div>
            <p className="text-sm text-text-secondary leading-relaxed">{role.description}</p>
          </div>
        ))}
      </div>

      <p className="text-xs text-text-secondary/70 text-center mt-2">
        Role management is under development. The above is a preview of planned roles.
      </p>
    </div>
  );
}

/* ── Page ───────────────────────────────────────────────────── */

export default function UsersRolesPage() {
  const [tab, setTab] = useState<Tab>('users');

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Users & Roles"
        description="Manage system users, permissions, and role assignments"
      />

      <div className="bg-surface rounded-card shadow-card overflow-hidden">
        {/* Tab strip */}
        <div className="flex border-b border-divider px-6">
          {TABS.map(({ key, label, icon }) => {
            const isActive = key === tab;
            return (
              <button
                key={key}
                onClick={() => setTab(key)}
                className={`flex items-center gap-2 px-4 py-4 text-sm font-medium border-b-2 transition-colors cursor-pointer -mb-px ${
                  isActive
                    ? 'border-primary text-primary'
                    : 'border-transparent text-text-secondary hover:text-text-primary'
                }`}
              >
                {icon}
                {label}
              </button>
            );
          })}
        </div>

        {/* Tab body */}
        <div className="p-6">
          {tab === 'users' && <UsersTab />}
          {tab === 'roles' && <RolesTab />}
        </div>
      </div>
    </div>
  );
}

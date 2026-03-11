import { useState, useEffect } from 'react';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import CloseIcon from '@mui/icons-material/Close';
import StorefrontIcon from '@mui/icons-material/Storefront';
import LanguageIcon from '@mui/icons-material/Language';
import type { PlatformRead } from '../../api/base_types/platform';
import { listPlatforms, createPlatform, updatePlatform } from '../../api/base/platform';

function extractErrorMessage(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const e = err as { response?: { data?: { detail?: string } } };
    return e.response?.data?.detail ?? 'Operation failed.';
  }
  return 'Operation failed.';
}

interface PlatformFormData {
  platform_name: string;
  address: string;
  postcode: string;
  api_endpoint: string;
  is_active: boolean;
  is_online: boolean;
}

const emptyForm: PlatformFormData = {
  platform_name: '',
  address: '',
  postcode: '',
  api_endpoint: '',
  is_active: true,
  is_online: true,
};

type FilterTab = 'all' | 'active' | 'inactive';

export default function PlatformCard() {
  const [platforms, setPlatforms] = useState<PlatformRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [addingNew, setAddingNew] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<PlatformFormData>(emptyForm);
  const [saving, setSaving] = useState(false);
  const [filterTab, setFilterTab] = useState<FilterTab>('all');
  const [togglingId, setTogglingId] = useState<number | null>(null);

  useEffect(() => {
    listPlatforms()
      .then(setPlatforms)
      .catch(() => setError('Failed to load platforms.'))
      .finally(() => setLoading(false));
  }, []);

  const resetForm = () => {
    setAddingNew(false);
    setEditingId(null);
    setForm(emptyForm);
    setError(null);
  };

  const handleCreate = async () => {
    if (!form.platform_name.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const created = await createPlatform({
        platform_name: form.platform_name.trim(),
        address: form.address.trim() || undefined,
        postcode: form.postcode.trim() || undefined,
        api_endpoint: form.api_endpoint.trim() || undefined,
        is_active: form.is_active,
        is_online: form.is_online,
      });
      setPlatforms((prev) => [...prev, created]);
      resetForm();
    } catch (err: unknown) {
      setError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const handleUpdate = async () => {
    if (editingId === null || !form.platform_name.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await updatePlatform(editingId, {
        platform_name: form.platform_name.trim(),
        address: form.address.trim() || undefined,
        postcode: form.postcode.trim() || undefined,
        api_endpoint: form.api_endpoint.trim() || undefined,
        is_active: form.is_active,
        is_online: form.is_online,
      });
      setPlatforms((prev) =>
        prev.map((p) => (p.platform_id === editingId ? updated : p)),
      );
      resetForm();
    } catch (err: unknown) {
      setError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const handleToggleActive = async (platform: PlatformRead) => {
    setTogglingId(platform.platform_id);
    try {
      const updated = await updatePlatform(platform.platform_id, {
        is_active: !platform.is_active,
      });
      setPlatforms((prev) =>
        prev.map((p) => (p.platform_id === platform.platform_id ? updated : p)),
      );
    } catch (err: unknown) {
      setError(extractErrorMessage(err));
    } finally {
      setTogglingId(null);
    }
  };

  const startEdit = (p: PlatformRead) => {
    setEditingId(p.platform_id);
    setAddingNew(false);
    setForm({
      platform_name: p.platform_name,
      address: p.address ?? '',
      postcode: p.postcode ?? '',
      api_endpoint: p.api_endpoint ?? '',
      is_active: p.is_active,
      is_online: p.is_online,
    });
    setError(null);
  };

  const isFormOpen = addingNew || editingId !== null;

  /* Filtered platforms */
  const filteredPlatforms = platforms.filter((p) => {
    if (filterTab === 'active') return p.is_active;
    if (filterTab === 'inactive') return !p.is_active;
    return true;
  });

  const activeCount = platforms.filter((p) => p.is_active).length;
  const inactiveCount = platforms.filter((p) => !p.is_active).length;

  const FILTER_TABS: { key: FilterTab; label: string; count: number }[] = [
    { key: 'all', label: 'All', count: platforms.length },
    { key: 'active', label: 'Active', count: activeCount },
    { key: 'inactive', label: 'Inactive', count: inactiveCount },
  ];

  return (
    <div className="flex flex-col gap-4 col-span-full">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold text-text-primary">Platforms</h3>
        <button
          onClick={() => {
            setAddingNew(true);
            setEditingId(null);
            setForm(emptyForm);
            setError(null);
          }}
          disabled={saving || isFormOpen}
          className="flex items-center gap-1 text-sm text-primary hover:underline cursor-pointer disabled:opacity-40"
        >
          <AddIcon fontSize="small" />
          Add Platform
        </button>
      </div>

      {/* Error banner */}
      {error && (
        <div className="bg-error-bg text-error-text rounded-default px-3 py-2 text-sm">
          {error}
        </div>
      )}

      {/* Inline form — slide-down panel */}
      {isFormOpen && (
        <div className="bg-surface border border-divider rounded-card shadow-card p-5 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-text-primary">
              {addingNew ? 'New Platform' : 'Edit Platform'}
            </p>
            <button
              onClick={resetForm}
              className="text-text-secondary hover:text-text-primary cursor-pointer"
            >
              <CloseIcon fontSize="small" />
            </button>
          </div>

          {/* Platform Name */}
          <div>
            <label className="block text-xs text-text-secondary mb-1">
              Platform Name <span className="text-error-text">*</span>
            </label>
            <input
              className="form-input w-full"
              value={form.platform_name}
              onChange={(e) => setForm((prev) => ({ ...prev, platform_name: e.target.value }))}
              placeholder="e.g. Shopee, Lazada"
              disabled={saving}
              autoFocus
            />
          </div>

          {/* Address */}
          <div>
            <label className="block text-xs text-text-secondary mb-1">Address</label>
            <input
              className="form-input w-full"
              value={form.address}
              onChange={(e) => setForm((prev) => ({ ...prev, address: e.target.value }))}
              placeholder="Office or HQ address (optional)"
              disabled={saving}
            />
          </div>

          {/* Postcode + API Endpoint */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-text-secondary mb-1">Postcode</label>
              <input
                className="form-input w-full"
                value={form.postcode}
                onChange={(e) => setForm((prev) => ({ ...prev, postcode: e.target.value }))}
                placeholder="e.g. 50480"
                disabled={saving}
              />
            </div>
            <div>
              <label className="block text-xs text-text-secondary mb-1">API Endpoint</label>
              <input
                className="form-input w-full"
                value={form.api_endpoint}
                onChange={(e) => setForm((prev) => ({ ...prev, api_endpoint: e.target.value }))}
                placeholder="https://api.platform.com"
                disabled={saving}
              />
            </div>
          </div>

          {/* Toggles row */}
          <div className="flex items-center gap-6">
            {/* Store Type toggle */}
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <div
                onClick={() => !saving && setForm((prev) => ({ ...prev, is_online: !prev.is_online }))}
                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors cursor-pointer ${
                  form.is_online ? 'bg-blue-500' : 'bg-amber-500'
                }`}
              >
                <span
                  className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${
                    form.is_online ? 'translate-x-4.5' : 'translate-x-0.5'
                  }`}
                />
              </div>
              <span className="text-sm text-text-primary">
                {form.is_online ? 'Online Store' : 'Offline Store'}
              </span>
            </label>

            {/* Active toggle */}
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <div
                onClick={() => !saving && setForm((prev) => ({ ...prev, is_active: !prev.is_active }))}
                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors cursor-pointer ${
                  form.is_active ? 'bg-primary' : 'bg-divider'
                }`}
              >
                <span
                  className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${
                    form.is_active ? 'translate-x-4.5' : 'translate-x-0.5'
                  }`}
                />
              </div>
              <span className="text-sm text-text-primary">Active</span>
            </label>
          </div>

          {/* Form actions */}
          <div className="flex justify-end gap-2 pt-1">
            <button
              onClick={resetForm}
              className="px-3 py-1.5 text-sm text-text-secondary hover:underline cursor-pointer"
            >
              Cancel
            </button>
            <button
              onClick={addingNew ? handleCreate : handleUpdate}
              disabled={saving || !form.platform_name.trim()}
              className="px-4 py-1.5 bg-primary text-white rounded-default text-sm hover:bg-primary-dark disabled:opacity-50 cursor-pointer"
            >
              {saving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="flex justify-center py-8">
          <span className="inline-block w-6 h-6 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
        </div>
      )}

      {/* Filter tabs + Table */}
      {!loading && (
        <div className="bg-surface rounded-card shadow-card overflow-hidden">
          {/* Filter tab strip */}
          <div className="flex border-b border-divider px-4">
            {FILTER_TABS.map(({ key, label, count }) => {
              const isActive = key === filterTab;
              return (
                <button
                  key={key}
                  onClick={() => setFilterTab(key)}
                  className={`px-3 py-2.5 text-sm font-medium border-b-2 transition-colors cursor-pointer -mb-px flex items-center gap-1.5 ${
                    isActive
                      ? 'border-secondary text-secondary'
                      : 'border-transparent text-text-secondary hover:text-text-primary'
                  }`}
                >
                  {label}
                  <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                    isActive
                      ? 'bg-secondary/10 text-secondary'
                      : 'bg-background text-text-secondary'
                  }`}>
                    {count}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Table */}
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-divider bg-background/50">
                <th className="text-left px-4 py-3 font-medium text-text-secondary">Platform</th>
                <th className="text-left px-4 py-3 font-medium text-text-secondary">Address</th>
                <th className="text-center px-4 py-3 font-medium text-text-secondary">Store Type</th>
                <th className="text-center px-4 py-3 font-medium text-text-secondary">Status</th>
                <th className="text-center px-4 py-3 font-medium text-text-secondary w-16">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-divider">
              {filteredPlatforms.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-text-secondary italic">
                    {filterTab === 'all'
                      ? 'No platforms yet. Click "Add Platform" to get started.'
                      : `No ${filterTab} platforms.`}
                  </td>
                </tr>
              )}
              {filteredPlatforms.map((p) => {
                const isToggling = togglingId === p.platform_id;
                return (
                  <tr
                    key={p.platform_id}
                    className={`hover:bg-background/30 transition-colors ${
                      editingId === p.platform_id ? 'opacity-40' : ''
                    }`}
                  >
                    {/* Platform name + postcode */}
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2.5">
                        <div className={`flex items-center justify-center w-8 h-8 rounded-lg ${
                          p.is_online
                            ? 'bg-blue-50 text-blue-600'
                            : 'bg-amber-50 text-amber-600'
                        }`}>
                          {p.is_online
                            ? <LanguageIcon fontSize="small" />
                            : <StorefrontIcon fontSize="small" />
                          }
                        </div>
                        <div className="min-w-0">
                          <p className="font-medium text-text-primary truncate">{p.platform_name}</p>
                          {p.postcode && (
                            <p className="text-xs text-text-secondary">{p.postcode}</p>
                          )}
                        </div>
                      </div>
                    </td>

                    {/* Address */}
                    <td className="px-4 py-3 text-text-secondary truncate max-w-[200px]">
                      {p.address || <span className="italic text-text-secondary/50">--</span>}
                    </td>

                    {/* Store Type badge */}
                    <td className="px-4 py-3 text-center">
                      <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${
                        p.is_online
                          ? 'bg-blue-50 text-blue-700'
                          : 'bg-amber-50 text-amber-700'
                      }`}>
                        {p.is_online ? 'Online' : 'Offline'}
                      </span>
                    </td>

                    {/* Status — inline toggle switch */}
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-center gap-2">
                        <button
                          onClick={() => handleToggleActive(p)}
                          disabled={isToggling || isFormOpen}
                          className="cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                          aria-label={`Toggle ${p.platform_name} ${p.is_active ? 'inactive' : 'active'}`}
                        >
                          <div
                            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                              p.is_active ? 'bg-emerald-500' : 'bg-gray-300'
                            }`}
                          >
                            <span
                              className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${
                                p.is_active ? 'translate-x-4.5' : 'translate-x-0.5'
                              }`}
                            />
                          </div>
                        </button>
                        <span className={`text-xs font-medium min-w-[50px] ${
                          p.is_active ? 'text-emerald-600' : 'text-text-secondary'
                        }`}>
                          {p.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </div>
                    </td>

                    {/* Edit action */}
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => startEdit(p)}
                        disabled={saving || isFormOpen}
                        className="text-text-secondary hover:text-primary cursor-pointer disabled:opacity-40 p-1 rounded-md hover:bg-background transition-colors"
                        aria-label={`Edit ${p.platform_name}`}
                      >
                        <EditIcon fontSize="small" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

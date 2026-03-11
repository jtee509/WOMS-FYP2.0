import { useState } from 'react';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import type { AttributeItem } from '../../api/base_types/items';

function extractErrorMessage(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const e = err as { response?: { data?: { detail?: string } } };
    return e.response?.data?.detail ?? 'Operation failed.';
  }
  return 'Operation failed.';
}

interface AttributeCardProps {
  title: string;
  items: AttributeItem[];
  loading: boolean;
  error: string | null;
  onCreate: (name: string) => Promise<void>;
  onUpdate: (id: number, name: string) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
}

export default function AttributeCard({
  title,
  items,
  loading,
  error,
  onCreate,
  onUpdate,
  onDelete,
}: AttributeCardProps) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editValue, setEditValue] = useState('');
  const [addingNew, setAddingNew] = useState(false);
  const [newValue, setNewValue] = useState('');
  const [saving, setSaving] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!newValue.trim()) return;
    setSaving(true);
    setLocalError(null);
    try {
      await onCreate(newValue.trim());
      setNewValue('');
      setAddingNew(false);
    } catch (err: unknown) {
      setLocalError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const handleSaveEdit = async () => {
    if (!editValue.trim() || editingId === null) return;
    setSaving(true);
    setLocalError(null);
    try {
      await onUpdate(editingId, editValue.trim());
      setEditingId(null);
    } catch (err: unknown) {
      setLocalError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    setSaving(true);
    setLocalError(null);
    try {
      await onDelete(id);
    } catch (err: unknown) {
      setLocalError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const singularLabel = title.toLowerCase().replace(/s$/, '');

  return (
    <div className="bg-surface rounded-card shadow-card p-5 flex flex-col gap-3">
      {/* Card header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
        <button
          onClick={() => { setAddingNew(true); setLocalError(null); }}
          className="flex items-center gap-0.5 text-xs font-medium text-primary hover:underline cursor-pointer disabled:opacity-40"
          disabled={saving || addingNew}
        >
          <AddIcon sx={{ fontSize: 16 }} />
          Add
        </button>
      </div>

      {/* Error banner */}
      {(error || localError) && (
        <div className="bg-error-bg text-error-text rounded-default px-3 py-2 text-xs">
          {localError || error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex justify-center py-6">
          <span className="inline-block w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
        </div>
      )}

      {/* Add new row */}
      {addingNew && (
        <div className="flex items-center gap-2 py-1">
          <input
            className="form-input !py-1.5 flex-grow text-sm"
            value={newValue}
            onChange={(e) => setNewValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleCreate();
              if (e.key === 'Escape') { setAddingNew(false); setNewValue(''); }
            }}
            placeholder={`New ${singularLabel}`}
            autoFocus
            disabled={saving}
          />
          <button
            onClick={handleCreate}
            disabled={saving || !newValue.trim()}
            className="shrink-0 px-3 py-1.5 bg-primary text-white rounded-default text-xs font-medium hover:bg-primary-dark disabled:opacity-50 cursor-pointer"
          >
            Save
          </button>
          <button
            onClick={() => { setAddingNew(false); setNewValue(''); }}
            className="shrink-0 text-xs text-text-secondary hover:underline cursor-pointer"
          >
            Cancel
          </button>
        </div>
      )}

      {/* Item list */}
      {!loading && (
        <ul className="divide-y divide-divider">
          {items.length === 0 && !addingNew && (
            <li className="py-4 text-center text-xs text-text-secondary italic">
              No {singularLabel}s yet
            </li>
          )}
          {items.map((item) => (
            <li
              key={item.id}
              className="py-2 flex items-center gap-1.5"
            >
              {editingId === item.id ? (
                <>
                  <input
                    className="form-input !py-1 flex-grow text-sm"
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleSaveEdit();
                      if (e.key === 'Escape') setEditingId(null);
                    }}
                    autoFocus
                    disabled={saving}
                  />
                  <button
                    onClick={handleSaveEdit}
                    disabled={saving || !editValue.trim()}
                    className="shrink-0 px-2.5 py-1 bg-primary text-white rounded-default text-xs font-medium hover:bg-primary-dark disabled:opacity-50 cursor-pointer"
                  >
                    Save
                  </button>
                  <button
                    onClick={() => setEditingId(null)}
                    className="shrink-0 text-xs text-text-secondary hover:underline cursor-pointer"
                  >
                    ✕
                  </button>
                </>
              ) : (
                <>
                  <span className="flex-grow text-sm text-text-primary truncate">
                    {item.name}
                  </span>
                  <button
                    onClick={() => { setEditingId(item.id); setEditValue(item.name); setLocalError(null); }}
                    className="p-1 rounded text-text-secondary hover:text-primary cursor-pointer transition-colors"
                    disabled={saving}
                    aria-label={`Edit ${item.name}`}
                  >
                    <EditIcon sx={{ fontSize: 16 }} />
                  </button>
                  <button
                    onClick={() => handleDelete(item.id)}
                    className="p-1 rounded text-text-secondary hover:text-error cursor-pointer transition-colors"
                    disabled={saving}
                    aria-label={`Delete ${item.name}`}
                  >
                    <DeleteIcon sx={{ fontSize: 16 }} />
                  </button>
                </>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

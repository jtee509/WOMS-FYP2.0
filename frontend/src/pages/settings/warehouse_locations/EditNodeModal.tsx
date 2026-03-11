import { useState } from 'react';
import { Pencil, X } from 'lucide-react';
import type { LocationTreeNode } from '../../../api/base_types/warehouse';
import type { HierarchyPath } from './LocationTree';

interface Props {
  node:      LocationTreeNode;
  path:      HierarchyPath;
  onConfirm: (newValue: string) => Promise<void>;
  onCancel:  () => void;
}

function extractErrorMessage(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const resp = (err as { response?: { data?: { detail?: string } } }).response;
    return resp?.data?.detail ?? 'Operation failed';
  }
  return 'Network error';
}

export default function EditNodeModal({ node, path, onConfirm, onCancel }: Props) {
  const [value, setValue] = useState(node.is_orphan ? '' : node.name);
  const [saving, setSaving] = useState(false);
  const [err, setErr]       = useState<string | null>(null);

  const typeLabel = node.type.charAt(0).toUpperCase() + node.type.slice(1);

  /* Build path label e.g. "Section A > Zone Z1" */
  const pathParts = [
    path.section ? `Section ${path.section}` : null,
    path.zone    ? `Zone ${path.zone}`    : null,
    path.aisle   ? `Aisle ${path.aisle}`  : null,
    path.rack    ? `Rack ${path.rack}`    : null,
  ].filter(Boolean);

  const handleConfirm = async () => {
    if (!value.trim()) { setErr('Value cannot be empty.'); return; }
    if (value.trim().length > 50) { setErr('Value must not exceed 50 characters.'); return; }

    setSaving(true);
    setErr(null);
    try {
      await onConfirm(value.trim());
    } catch (e) {
      setErr(extractErrorMessage(e));
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm"
      onClick={onCancel}
    >
      <div
        className="bg-surface rounded-card shadow-card border border-divider w-full max-w-sm mx-4 p-5 flex flex-col gap-4"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <div className="w-9 h-9 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
              <Pencil size={16} className="text-primary" />
            </div>
            <div>
              <p className="text-sm font-semibold text-text-primary">
                Rename {typeLabel}
              </p>
              {pathParts.length > 0 && (
                <p className="text-xs text-text-secondary mt-0.5">
                  {pathParts.join(' › ')}
                </p>
              )}
            </div>
          </div>
          <button
            onClick={onCancel}
            className="p-1 text-text-secondary hover:text-text-primary cursor-pointer"
          >
            <X size={15} />
          </button>
        </div>

        {/* Input */}
        <div>
          <label className="block text-xs font-medium text-text-secondary mb-1">
            New name for this {typeLabel.toLowerCase()}
          </label>
          <input
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleConfirm(); }}
            className="form-input w-full"
            autoFocus
            disabled={saving}
            maxLength={50}
            placeholder={`e.g. ${typeLabel.charAt(0)}1`}
          />
        </div>

        {err && (
          <p className="text-xs text-error-text bg-error-bg rounded-default px-3 py-2">{err}</p>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-2">
          <button
            onClick={onCancel}
            disabled={saving}
            className="px-3 py-1.5 text-sm text-text-secondary hover:underline cursor-pointer disabled:opacity-40"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={saving || !value.trim()}
            className="flex items-center gap-1.5 px-4 py-1.5 bg-secondary text-white rounded-default text-sm font-medium hover:shadow-button-hover transition-shadow disabled:opacity-50 cursor-pointer"
          >
            <Pencil size={13} />
            {saving ? 'Saving…' : 'Rename'}
          </button>
        </div>
      </div>
    </div>
  );
}

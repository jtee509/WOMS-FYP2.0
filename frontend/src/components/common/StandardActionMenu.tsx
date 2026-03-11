import { useEffect, useRef, useState, useCallback } from 'react';
import { createPortal } from 'react-dom';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import EditIcon from '@mui/icons-material/Edit';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import PowerSettingsNewIcon from '@mui/icons-material/PowerSettingsNew';
import DeleteIcon from '@mui/icons-material/Delete';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';

export interface StandardActionMenuProps {
  /** Opens an edit form / modal for the entity */
  onEdit?: () => void;
  /** Toggles active/inactive status */
  onToggleStatus?: () => void;
  /** Whether the entity is currently active (controls label text) */
  isActive?: boolean;
  /** Deep-duplicates the entity */
  onDuplicate?: () => void;
  /** Soft-deletes the entity — triggers confirm step first */
  onDelete?: () => void;
  /** Label shown on the Delete menu item (default: "Delete") */
  deleteLabel?: string;
  /** Confirmation message shown before the delete executes */
  confirmMessage?: string;
  /** Disables all interactions */
  disabled?: boolean;
  /**
   * Render the dropdown via a React portal at document.body.
   * Use when the trigger sits inside a container with overflow:hidden
   * (e.g. a DataTable) to prevent the menu from being clipped.
   */
  usePortal?: boolean;
}

type MenuState = 'closed' | 'open' | 'confirming';

interface DropPos { top: number; right: number; }

export default function StandardActionMenu({
  onEdit,
  onToggleStatus,
  isActive = true,
  onDuplicate,
  onDelete,
  deleteLabel    = 'Delete',
  confirmMessage = 'This action cannot be undone.',
  disabled       = false,
  usePortal      = false,
}: StandardActionMenuProps) {
  const [state, setState] = useState<MenuState>('closed');
  const [acting, setActing] = useState(false);
  const [dropPos, setDropPos] = useState<DropPos | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef   = useRef<HTMLButtonElement>(null);

  /* ── Close on outside click ────────────────────────────────── */
  useEffect(() => {
    if (state === 'closed') return;
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      /* For portalled menus the dropdown is outside containerRef */
      if (containerRef.current?.contains(target)) return;
      /* Check if click is inside a portalled menu by id */
      const portalEl = document.getElementById('sam-portal-menu');
      if (portalEl?.contains(target)) return;
      setState('closed');
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [state]);

  /* ── Close on scroll (portal mode only) ────────────────────── */
  useEffect(() => {
    if (!usePortal || state === 'closed') return;
    const handler = () => setState('closed');
    window.addEventListener('scroll', handler, true);
    return () => window.removeEventListener('scroll', handler, true);
  }, [usePortal, state]);

  /* ── Recalculate position when menu opens (portal mode) ────── */
  const calcPos = useCallback(() => {
    if (!usePortal || !triggerRef.current) return;
    const rect = triggerRef.current.getBoundingClientRect();
    setDropPos({
      top:   rect.bottom + 4,
      right: window.innerWidth - rect.right,
    });
  }, [usePortal]);

  const close = () => setState('closed');

  const wrap = (fn?: () => void) => () => { close(); fn?.(); };

  const handleOpen = () => {
    if (state !== 'closed') { close(); return; }
    calcPos();
    setState('open');
  };

  const handleDeleteConfirm = async () => {
    if (!onDelete) return;
    setActing(true);
    try {
      await onDelete();
    } finally {
      setActing(false);
      close();
    }
  };

  const hasActions = onEdit || onToggleStatus || onDuplicate || onDelete;
  if (!hasActions) return null;

  /* ── Shared dropdown JSX ────────────────────────────────────── */
  const posStyle: React.CSSProperties | undefined =
    usePortal && dropPos
      ? { position: 'fixed', top: dropPos.top, right: dropPos.right, zIndex: 9999 }
      : undefined;

  const dropdownMenu = state === 'open' && (
    <div
      id={usePortal ? 'sam-portal-menu' : undefined}
      style={posStyle}
      className={`${
        usePortal ? '' : 'absolute right-0 top-full mt-1 z-50'
      } bg-surface border border-divider rounded-default shadow-card min-w-[160px] py-1 text-sm`}
    >
      {onEdit && (
        <button
          onClick={wrap(onEdit)}
          className="flex items-center gap-2.5 w-full px-4 py-2 text-text-primary hover:bg-background cursor-pointer transition-colors"
        >
          <EditIcon sx={{ fontSize: 16 }} className="text-text-secondary" />
          Edit
        </button>
      )}

      {onToggleStatus && (
        <button
          onClick={wrap(onToggleStatus)}
          className="flex items-center gap-2.5 w-full px-4 py-2 text-text-primary hover:bg-background cursor-pointer transition-colors"
        >
          <PowerSettingsNewIcon
            sx={{ fontSize: 16 }}
            className={isActive ? 'text-warning-text' : 'text-success-text'}
          />
          {isActive ? 'Deactivate' : 'Activate'}
        </button>
      )}

      {onDuplicate && (
        <button
          onClick={wrap(onDuplicate)}
          className="flex items-center gap-2.5 w-full px-4 py-2 text-text-primary hover:bg-background cursor-pointer transition-colors"
        >
          <ContentCopyIcon sx={{ fontSize: 16 }} className="text-text-secondary" />
          Duplicate
        </button>
      )}

      {onDelete && (
        <>
          {(onEdit || onToggleStatus || onDuplicate) && (
            <div className="border-t border-divider my-1" />
          )}
          <button
            onClick={() => setState('confirming')}
            className="flex items-center gap-2.5 w-full px-4 py-2 text-error-text hover:bg-error-bg cursor-pointer transition-colors"
          >
            <DeleteIcon sx={{ fontSize: 16 }} />
            {deleteLabel}
          </button>
        </>
      )}
    </div>
  );

  const confirmMenu = state === 'confirming' && (
    <div
      id={usePortal ? 'sam-portal-menu' : undefined}
      style={posStyle}
      className={`${
        usePortal ? '' : 'absolute right-0 top-full mt-1 z-50'
      } bg-surface border border-divider rounded-default shadow-card w-64 p-4`}
    >
      <div className="flex items-start gap-2 mb-3">
        <WarningAmberIcon sx={{ fontSize: 18 }} className="text-warning-text shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-medium text-text-primary mb-0.5">Are you sure?</p>
          <p className="text-xs text-text-secondary">{confirmMessage}</p>
        </div>
      </div>
      <div className="flex justify-end gap-2">
        <button
          onClick={close}
          disabled={acting}
          className="px-3 py-1.5 text-xs text-text-secondary hover:underline cursor-pointer disabled:opacity-40"
        >
          Cancel
        </button>
        <button
          onClick={handleDeleteConfirm}
          disabled={acting}
          className="px-3 py-1.5 bg-error-text text-white rounded-default text-xs font-medium hover:opacity-90 disabled:opacity-50 cursor-pointer"
        >
          {acting ? 'Deleting…' : 'Delete'}
        </button>
      </div>
    </div>
  );

  /* ── Render ─────────────────────────────────────────────────── */
  return (
    <div
      ref={containerRef}
      className="relative inline-block"
      onClick={(e) => e.stopPropagation()}
    >
      {/* Trigger */}
      <button
        ref={triggerRef}
        onClick={handleOpen}
        disabled={disabled || acting}
        className="p-1 rounded text-text-secondary hover:text-text-primary hover:bg-background transition-colors cursor-pointer disabled:opacity-40"
        aria-label="Actions"
      >
        <MoreVertIcon sx={{ fontSize: 18 }} />
      </button>

      {/* Dropdown — either inline or via portal */}
      {usePortal
        ? createPortal(<>{dropdownMenu}{confirmMenu}</>, document.body)
        : <>{dropdownMenu}{confirmMenu}</>
      }
    </div>
  );
}

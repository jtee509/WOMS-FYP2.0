import { useState } from 'react';
import { ChevronRight, ChevronDown, Pencil, Trash2, EyeOff, FolderOpen } from 'lucide-react';
import type { LocationTreeNode } from '../../../api/base_types/warehouse';

/* ------------------------------------------------------------------
 * HierarchyPath — tracks the parent context of a tree node
 * ------------------------------------------------------------------ */

export interface HierarchyPath {
  section?: string;
  zone?:    string;
  aisle?:   string;
  rack?:    string;
}

/* ------------------------------------------------------------------
 * Helpers
 * ------------------------------------------------------------------ */

/** Collect every location_id that is a descendant of (or equal to) a node */
function collectBinIds(node: LocationTreeNode): number[] {
  if (node.type === 'bin') {
    return node.location_id !== undefined ? [node.location_id] : [];
  }
  return (node.children ?? []).flatMap(collectBinIds);
}

type CheckState = 'none' | 'some' | 'all';

function getCheckState(node: LocationTreeNode, selectedIds: Set<number>): CheckState {
  const ids = collectBinIds(node);
  if (ids.length === 0) return 'none';
  const selectedCount = ids.filter((id) => selectedIds.has(id)).length;
  if (selectedCount === 0)          return 'none';
  if (selectedCount === ids.length) return 'all';
  return 'some';
}

/** Stable key for identifying a tree node (used for active highlight) */
export function nodeKey(node: LocationTreeNode, path: HierarchyPath): string {
  return [
    node.type,
    path.section ?? '',
    path.zone    ?? '',
    path.aisle   ?? '',
    path.rack    ?? '',
    node.name,
  ].join('|');
}

/* ------------------------------------------------------------------
 * Type badge styling
 * ------------------------------------------------------------------ */

const TYPE_STYLES: Record<string, { badge: string; row: string }> = {
  warehouse: { badge: 'bg-primary/10 text-primary',           row: '' },
  section:   { badge: 'bg-info-bg text-info-text',            row: '' },
  zone:      { badge: 'bg-warning-bg text-warning-text',      row: '' },
  aisle:     { badge: 'bg-success-bg text-success-text',      row: '' },
  rack:      { badge: 'bg-divider text-text-secondary',        row: '' },
  bin:       { badge: 'bg-background border border-divider text-text-secondary', row: '' },
};

/* ------------------------------------------------------------------
 * Checkbox — supports indeterminate state
 * ------------------------------------------------------------------ */

function TreeCheckbox({
  checkState,
  onChange,
}: {
  checkState: CheckState;
  onChange: (checked: boolean) => void;
}) {
  const ref = (el: HTMLInputElement | null) => {
    if (!el) return;
    el.indeterminate = checkState === 'some';
  };

  return (
    <input
      ref={ref}
      type="checkbox"
      checked={checkState === 'all'}
      onChange={(e) => onChange(e.target.checked)}
      onClick={(e) => e.stopPropagation()}
      className="w-3.5 h-3.5 rounded border-divider text-primary focus:ring-0 cursor-pointer flex-shrink-0"
    />
  );
}

/* ------------------------------------------------------------------
 * Single tree node
 * ------------------------------------------------------------------ */

interface TreeNodeProps {
  node:        LocationTreeNode;
  path:        HierarchyPath;
  depth:       number;
  selectedIds: Set<number>;
  activeKey?:  string;
  onSelect:    (ids: number[], checked: boolean) => void;
  onDelete:    (node: LocationTreeNode, path: HierarchyPath) => void;
  onEdit:      (node: LocationTreeNode, path: HierarchyPath) => void;
  onNodeClick?: (node: LocationTreeNode, path: HierarchyPath) => void;
}

function TreeNode({
  node, path, depth, selectedIds, activeKey, onSelect, onDelete, onEdit, onNodeClick,
}: TreeNodeProps) {
  const [expanded, setExpanded] = useState(depth < 2);

  const hasChildren = (node.children?.length ?? 0) > 0;
  const indent      = depth * 14;

  const childPath: HierarchyPath = {
    section: node.type === 'section' ? node.name : path.section,
    zone:    node.type === 'zone'    ? node.name : path.zone,
    aisle:   node.type === 'aisle'   ? node.name : path.aisle,
    rack:    node.type === 'rack'    ? node.name : path.rack,
  };

  const styles     = TYPE_STYLES[node.type] ?? TYPE_STYLES.bin;
  const typeLabel  = node.type.charAt(0).toUpperCase() + node.type.slice(1);
  const checkState = getCheckState(node, selectedIds);
  const binIds     = collectBinIds(node);
  const isInactive = node.is_active === false;
  const myKey      = nodeKey(node, path);
  const isActive   = activeKey === myKey;

  const handleCheck = (checked: boolean) => {
    if (binIds.length > 0) onSelect(binIds, checked);
  };

  const handleNameClick = () => {
    if (onNodeClick && node.type !== 'warehouse') {
      onNodeClick(node, path);
    }
    if (hasChildren) setExpanded(v => !v);
  };

  return (
    <>
      <div
        className={`group flex items-center gap-1 py-0.5 px-1 rounded-default transition-colors ${
          isActive
            ? 'bg-primary/10 ring-1 ring-primary/20'
            : 'hover:bg-background'
        } ${isInactive ? 'opacity-50' : ''}`}
        style={{ paddingLeft: `${6 + indent}px` }}
      >
        {/* Checkbox — controls all descendant bins */}
        {binIds.length > 0 ? (
          <TreeCheckbox checkState={checkState} onChange={handleCheck} />
        ) : (
          <span className="w-3.5 flex-shrink-0" />
        )}

        {/* Expand / collapse */}
        {hasChildren ? (
          <button
            onClick={() => setExpanded(v => !v)}
            className="flex-shrink-0 text-text-secondary hover:text-text-primary cursor-pointer p-0.5"
          >
            {expanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
          </button>
        ) : (
          <span className="w-4 flex-shrink-0" />
        )}

        {/* Type badge */}
        <span className={`text-[9px] font-bold px-1 py-0.5 rounded uppercase tracking-wider flex-shrink-0 ${styles.badge}`}>
          {typeLabel}
        </span>

        {/* Name — clickable to filter grid */}
        <button
          onClick={handleNameClick}
          className={`text-xs truncate flex-grow min-w-0 text-left cursor-pointer transition-colors ${
            isActive
              ? 'text-primary font-semibold'
              : 'text-text-primary hover:text-primary'
          } ${node.is_orphan ? 'italic text-text-secondary' : ''}`}
          title={onNodeClick && node.type !== 'warehouse' ? `Filter grid to ${typeLabel} "${node.name}"` : undefined}
        >
          {node.is_orphan ? `(unlinked) ${node.name}` : node.name}
        </button>

        {/* Inactive badge */}
        {isInactive && (
          <EyeOff size={11} className="text-text-secondary flex-shrink-0" title="Inactive" />
        )}

        {/* Count pill */}
        {node.total_locations !== undefined && node.total_locations > 0 && node.type !== 'bin' && (
          <span className="text-[9px] text-text-secondary bg-background border border-divider px-1.5 py-0.5 rounded-full flex-shrink-0">
            {node.total_locations}
          </span>
        )}

        {/* Hover actions */}
        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
          <button
            onClick={(e) => { e.stopPropagation(); onEdit(node, path); }}
            className="p-1 rounded text-text-secondary hover:text-primary hover:bg-primary/10 cursor-pointer transition-colors"
            title={node.type === 'section' ? 'Manage section' : 'Rename'}
          >
            <Pencil size={11} />
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onDelete(node, path); }}
            className="p-1 rounded text-text-secondary hover:text-error-text hover:bg-error-bg cursor-pointer transition-colors"
            title="Delete subtree"
          >
            <Trash2 size={11} />
          </button>
        </div>
      </div>

      {/* Children */}
      {expanded && hasChildren && (
        <>
          {node.children!.map((child, i) => (
            <TreeNode
              key={`${child.type}-${child.name}-${i}`}
              node={child}
              path={childPath}
              depth={depth + 1}
              selectedIds={selectedIds}
              activeKey={activeKey}
              onSelect={onSelect}
              onDelete={onDelete}
              onEdit={onEdit}
              onNodeClick={onNodeClick}
            />
          ))}
        </>
      )}
    </>
  );
}

/* ------------------------------------------------------------------
 * Unassigned group — wraps orphan nodes under a virtual folder
 * ------------------------------------------------------------------ */

interface UnassignedGroupProps {
  nodes:       LocationTreeNode[];
  selectedIds: Set<number>;
  activeKey?:  string;
  onSelect:    (ids: number[], checked: boolean) => void;
  onDelete:    (node: LocationTreeNode, path: HierarchyPath) => void;
  onEdit:      (node: LocationTreeNode, path: HierarchyPath) => void;
  onNodeClick?: (node: LocationTreeNode, path: HierarchyPath) => void;
}

function UnassignedGroup({ nodes, selectedIds, activeKey, onSelect, onDelete, onEdit, onNodeClick }: UnassignedGroupProps) {
  const [expanded, setExpanded] = useState(false);
  const allBinIds = nodes.flatMap(collectBinIds);
  const groupCheckState = getCheckState(
    { name: '', type: 'section', summary: '', children: nodes },
    selectedIds,
  );

  return (
    <>
      {/* Group header row */}
      <div className="group flex items-center gap-1 py-0.5 px-1 rounded-default hover:bg-background transition-colors">
        {allBinIds.length > 0 ? (
          <TreeCheckbox checkState={groupCheckState} onChange={(c) => onSelect(allBinIds, c)} />
        ) : (
          <span className="w-3.5 flex-shrink-0" />
        )}
        <button
          onClick={() => setExpanded(v => !v)}
          className="flex-shrink-0 text-text-secondary hover:text-text-primary cursor-pointer p-0.5"
        >
          {expanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        </button>
        <FolderOpen size={13} className="text-text-secondary flex-shrink-0" />
        <span className="text-xs text-text-secondary italic truncate flex-grow ml-1">
          Unassigned / General
        </span>
        <span className="text-[9px] text-text-secondary bg-background border border-divider px-1.5 py-0.5 rounded-full flex-shrink-0">
          {nodes.reduce((s, n) => s + (n.total_locations ?? 0), 0)}
        </span>
      </div>

      {/* Children */}
      {expanded && nodes.map((node, i) => (
        <TreeNode
          key={`orphan-${node.type}-${node.name}-${i}`}
          node={node}
          path={{}}
          depth={1}
          selectedIds={selectedIds}
          activeKey={activeKey}
          onSelect={onSelect}
          onDelete={onDelete}
          onEdit={onEdit}
          onNodeClick={onNodeClick}
        />
      ))}
    </>
  );
}

/* ------------------------------------------------------------------
 * LocationTree
 * ------------------------------------------------------------------ */

interface LocationTreeProps {
  nodes:        LocationTreeNode[];
  loading:      boolean;
  selectedIds:  Set<number>;
  activeKey?:   string;
  onSelect:     (ids: number[], checked: boolean) => void;
  onDeleteNode: (node: LocationTreeNode, path: HierarchyPath) => void;
  onEditNode:   (node: LocationTreeNode, path: HierarchyPath) => void;
  onNodeClick?: (node: LocationTreeNode, path: HierarchyPath) => void;
}

export default function LocationTree({
  nodes,
  loading,
  selectedIds,
  activeKey,
  onSelect,
  onDeleteNode,
  onEditNode,
  onNodeClick,
}: LocationTreeProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-8 text-text-secondary text-sm">
        Loading…
      </div>
    );
  }

  if (nodes.length === 0) {
    return (
      <div className="flex items-center justify-center py-8 text-text-secondary text-sm">
        No locations yet.
      </div>
    );
  }

  /* Separate orphan top-level nodes from regular hierarchy */
  const regularNodes = nodes.filter(n => !n.is_orphan);
  const orphanNodes  = nodes.filter(n => n.is_orphan);

  const allBinIds = nodes.flatMap(collectBinIds);
  const rootCheck = getCheckState(
    { type: 'warehouse', name: '', summary: '', children: nodes },
    selectedIds,
  );

  return (
    <div className="flex flex-col gap-0">
      {/* Select all row */}
      {allBinIds.length > 0 && (
        <div className="flex items-center gap-2 px-1 py-1 border-b border-divider mb-1">
          <TreeCheckbox
            checkState={rootCheck}
            onChange={(checked) => onSelect(allBinIds, checked)}
          />
          <span className="text-[10px] text-text-secondary">
            {rootCheck === 'none'
              ? 'Select all bins'
              : `${[...selectedIds].filter(id => allBinIds.includes(id)).length} / ${allBinIds.length} selected`}
          </span>
          {activeKey && (
            <span className="ml-auto text-[10px] text-primary italic">
              Filter active — click grid to clear
            </span>
          )}
        </div>
      )}

      {/* Regular hierarchy nodes */}
      {regularNodes.map((node, i) => (
        <TreeNode
          key={`${node.type}-${node.name}-${i}`}
          node={node}
          path={{}}
          depth={0}
          selectedIds={selectedIds}
          activeKey={activeKey}
          onSelect={onSelect}
          onDelete={onDeleteNode}
          onEdit={onEditNode}
          onNodeClick={onNodeClick}
        />
      ))}

      {/* Orphan nodes grouped under "Unassigned" */}
      {orphanNodes.length > 0 && (
        <div className="mt-1 border-t border-divider pt-1">
          <UnassignedGroup
            nodes={orphanNodes}
            selectedIds={selectedIds}
            activeKey={activeKey}
            onSelect={onSelect}
            onDelete={onDeleteNode}
            onEdit={onEditNode}
            onNodeClick={onNodeClick}
          />
        </div>
      )}
    </div>
  );
}

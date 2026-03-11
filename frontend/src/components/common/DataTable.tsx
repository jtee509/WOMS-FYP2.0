import { Fragment, useRef, useEffect, type ReactNode } from 'react';
import SearchBar from './SearchBar';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import FirstPageIcon from '@mui/icons-material/FirstPage';
import LastPageIcon from '@mui/icons-material/LastPage';

/* ------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------ */

export interface Column<T> {
  header: string;
  accessor: keyof T | ((row: T) => ReactNode);
  className?: string;
}

export interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
  loading?: boolean;
  error?: string | null;
  emptyMessage?: string;
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  searchPlaceholder?: string;
  expandedRowId?: number | string | null;
  onRowClick?: (row: T) => void;
  renderExpandedRow?: (row: T) => ReactNode;
  getRowId: (row: T) => number | string;
  headerActions?: ReactNode;
  /** Render checkbox column for row selection */
  selectable?: boolean;
  selectedIds?: Set<number | string>;
  onSelectChange?: (ids: Set<number | string>) => void;
  /** When true, omit the card wrapper styling */
  noCard?: boolean;
}

/* ------------------------------------------------------------------
 * Helpers
 * ------------------------------------------------------------------ */

function getCellValue<T>(row: T, accessor: Column<T>['accessor']): ReactNode {
  if (typeof accessor === 'function') return accessor(row);
  const val = row[accessor];
  if (val === null || val === undefined) return <span className="text-text-secondary">—</span>;
  return String(val);
}

const PAGE_SIZES = [10, 20, 50, 100];

function getPageNumbers(current: number, total: number): (number | '...')[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);

  const pages: (number | '...')[] = [1];
  if (current > 3) pages.push('...');

  const start = Math.max(2, current - 1);
  const end = Math.min(total - 1, current + 1);
  for (let i = start; i <= end; i++) pages.push(i);

  if (current < total - 2) pages.push('...');
  pages.push(total);
  return pages;
}

/* ------------------------------------------------------------------
 * IndeterminateCheckbox
 * ------------------------------------------------------------------ */

function IndeterminateCheckbox({
  checked,
  indeterminate,
  onChange,
}: {
  checked: boolean;
  indeterminate: boolean;
  onChange: () => void;
}) {
  const ref = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (ref.current) ref.current.indeterminate = indeterminate;
  }, [indeterminate]);
  return (
    <input
      ref={ref}
      type="checkbox"
      checked={checked}
      onChange={onChange}
      className="w-4 h-4 rounded border-divider text-primary focus:ring-primary cursor-pointer"
    />
  );
}

/* ------------------------------------------------------------------
 * Component
 * ------------------------------------------------------------------ */

export default function DataTable<T>({
  columns,
  data,
  total,
  page,
  pageSize,
  onPageChange,
  onPageSizeChange,
  loading = false,
  error = null,
  emptyMessage = 'No data found.',
  searchValue,
  onSearchChange,
  searchPlaceholder = 'Search...',
  expandedRowId,
  onRowClick,
  renderExpandedRow,
  getRowId,
  headerActions,
  selectable = false,
  selectedIds,
  onSelectChange,
  noCard = false,
}: DataTableProps<T>) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const start = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);

  const allSelected = data.length > 0 && data.every((r) => selectedIds?.has(getRowId(r)));
  const someSelected = data.some((r) => selectedIds?.has(getRowId(r)));

  const handleSelectAll = () => {
    if (!onSelectChange) return;
    const next = new Set(selectedIds);
    if (allSelected) {
      data.forEach((r) => next.delete(getRowId(r)));
    } else {
      data.forEach((r) => next.add(getRowId(r)));
    }
    onSelectChange(next);
  };

  const handleToggleRow = (id: number | string) => {
    if (!onSelectChange) return;
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    onSelectChange(next);
  };

  const colSpan = columns.length + (selectable ? 1 : 0);

  return (
    <div className={noCard ? '' : 'bg-surface rounded-card shadow-card overflow-hidden'}>
      {/* Toolbar */}
      {(onSearchChange || headerActions) && (
        <div className="flex flex-wrap items-center gap-3 p-4 border-b border-divider">
          {onSearchChange && (
            <SearchBar
              value={searchValue ?? ''}
              onChange={onSearchChange}
              placeholder={searchPlaceholder}
              className="flex-grow max-w-xs"
            />
          )}
          {headerActions && <div className="flex items-center gap-2 ml-auto">{headerActions}</div>}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mx-4 mt-4 bg-error-bg text-error-text rounded-default px-3 py-2 text-sm">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex justify-center py-12">
          <span className="inline-block w-8 h-8 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
        </div>
      )}

      {/* Table */}
      {!loading && (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-divider bg-background">
                  {selectable && (
                    <th className="px-4 py-3 w-10">
                      <div className="flex items-center justify-center">
                        <IndeterminateCheckbox
                          checked={allSelected}
                          indeterminate={!allSelected && someSelected}
                          onChange={handleSelectAll}
                        />
                      </div>
                    </th>
                  )}
                  {columns.map((col, i) => (
                    <th
                      key={i}
                      className={`px-4 py-3 text-left text-xs font-semibold text-text-secondary whitespace-nowrap uppercase tracking-wider ${col.className ?? ''}`}
                    >
                      {col.header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-divider">
                {data.length === 0 && (
                  <tr>
                    <td colSpan={colSpan} className="px-4 py-12 text-center text-text-secondary">
                      {emptyMessage}
                    </td>
                  </tr>
                )}
                {data.map((row) => {
                  const rowId = getRowId(row);
                  const isExpanded = expandedRowId === rowId;
                  return (
                    <Fragment key={rowId}>
                      <tr
                        className={`transition-colors ${onRowClick ? 'cursor-pointer hover:bg-background' : ''} ${isExpanded ? 'bg-background' : ''}`}
                        onClick={() => onRowClick?.(row)}
                      >
                        {selectable && (
                          <td className="px-4 py-3 w-10">
                            <div className="flex items-center justify-center">
                              <input
                                type="checkbox"
                                checked={selectedIds?.has(rowId) ?? false}
                                onChange={() => handleToggleRow(rowId)}
                                onClick={(e) => e.stopPropagation()}
                                className="w-4 h-4 rounded border-divider text-primary focus:ring-primary cursor-pointer"
                              />
                            </div>
                          </td>
                        )}
                        {columns.map((col, i) => (
                          <td key={i} className={`px-4 py-3 ${col.className ?? ''}`}>
                            {getCellValue(row, col.accessor)}
                          </td>
                        ))}
                      </tr>
                      {isExpanded && renderExpandedRow && (
                        <tr>
                          <td colSpan={colSpan} className="px-4 py-3 bg-background/50">
                            {renderExpandedRow(row)}
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-t border-divider text-sm text-text-secondary">
            <span>
              {total > 0 ? `Showing ${start}–${end} of ${total}` : 'No results'}
            </span>

            <div className="flex items-center gap-1">
              {onPageSizeChange && (
                /* !py-1 !px-2 needed — form-input is unlayered CSS and wins over utilities without ! */
                <select
                  value={pageSize}
                  onChange={(e) => onPageSizeChange(Number(e.target.value))}
                  className="form-input !py-1 !px-2 text-sm !w-auto mr-3"
                >
                  {PAGE_SIZES.map((s) => (
                    <option key={s} value={s}>{s} / page</option>
                  ))}
                </select>
              )}

              {/* Nav buttons — uniform w-7 h-7 for visual consistency with page number buttons */}
              <button
                onClick={() => onPageChange(1)}
                disabled={page <= 1}
                className="w-7 h-7 flex items-center justify-center rounded-default hover:bg-background disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
                title="First page"
              >
                <FirstPageIcon fontSize="small" />
              </button>
              <button
                onClick={() => onPageChange(page - 1)}
                disabled={page <= 1}
                className="w-7 h-7 flex items-center justify-center rounded-default hover:bg-background disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
              >
                <ChevronLeftIcon fontSize="small" />
              </button>

              {getPageNumbers(page, pages).map((p, i) =>
                p === '...' ? (
                  <span key={`ellipsis-${i}`} className="w-7 h-7 flex items-center justify-center text-text-secondary/50 select-none cursor-default text-xs">
                    …
                  </span>
                ) : (
                  <button
                    key={p}
                    onClick={() => onPageChange(p)}
                    className={`w-7 h-7 flex items-center justify-center rounded-default text-xs font-medium cursor-pointer transition-colors ${
                      p === page
                        ? 'bg-primary text-white'
                        : 'text-text-secondary hover:bg-background'
                    }`}
                  >
                    {p}
                  </button>
                ),
              )}

              <button
                onClick={() => onPageChange(page + 1)}
                disabled={page >= pages}
                className="w-7 h-7 flex items-center justify-center rounded-default hover:bg-background disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
              >
                <ChevronRightIcon fontSize="small" />
              </button>
              <button
                onClick={() => onPageChange(pages)}
                disabled={page >= pages}
                className="w-7 h-7 flex items-center justify-center rounded-default hover:bg-background disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
                title="Last page"
              >
                <LastPageIcon fontSize="small" />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

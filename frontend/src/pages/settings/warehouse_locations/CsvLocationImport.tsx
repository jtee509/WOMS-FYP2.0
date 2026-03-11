import { useState, useRef, useCallback } from 'react';
import * as XLSX from 'xlsx';
import {
  Download,
  Upload,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
  FileSpreadsheet,
} from 'lucide-react';
import { createLocation } from '../../../api/base/warehouse';

/* ------------------------------------------------------------------
 * Constants & template
 * ------------------------------------------------------------------ */

const ALLOWED_EXTENSIONS = ['.csv', '.xlsx', '.xls'];
const MAX_FILE_SIZE_MB   = 5;
const MAX_FILE_SIZE      = MAX_FILE_SIZE_MB * 1024 * 1024;

const CSV_TEMPLATE =
  'section,zone,aisle,rack,bin,is_active\n' +
  'A,Z1,A01,R1,B01,true\n' +
  'A,Z1,A01,R1,B02,true\n' +
  'A,Z2,A02,R1,B01,true\n' +
  'B,,,,,true\n';

/* ------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------ */

interface ParsedRow {
  rowIndex: number;
  section:  string | undefined;
  zone:     string | undefined;
  aisle:    string | undefined;
  rack:     string | undefined;
  bin:      string | undefined;
  isActive: boolean;
  errors:   string[];
}

interface ImportResult {
  created: number;
  failed:  number;
  errors:  Array<{ row: number; error: string }>;
}

/* ------------------------------------------------------------------
 * Props
 * ------------------------------------------------------------------ */

interface Props {
  warehouseId:      number;
  onImportComplete: () => void;
}

/* ------------------------------------------------------------------
 * Helpers
 * ------------------------------------------------------------------ */

function extractErrorMessage(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const resp = (err as { response?: { data?: { detail?: string } } }).response;
    return resp?.data?.detail ?? 'Operation failed';
  }
  return 'Network error';
}

function normalizeStr(v: unknown): string | undefined {
  if (v === null || v === undefined) return undefined;
  const s = String(v).trim();
  return s || undefined;
}

/** Accept true/1/yes/TRUE variants */
function parseBool(v: unknown): boolean {
  if (typeof v === 'boolean') return v;
  const s = String(v).trim().toLowerCase();
  return s === 'true' || s === '1' || s === 'yes';
}

function downloadTemplate() {
  const blob = new Blob([CSV_TEMPLATE], { type: 'text/csv;charset=utf-8;' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = 'location_import_template.csv';
  a.click();
  URL.revokeObjectURL(url);
}

function validateRow(raw: Record<string, unknown>, index: number): ParsedRow {
  const section = normalizeStr(raw['section'] ?? raw['Section'] ?? raw['SECTION']);
  const zone    = normalizeStr(raw['zone']    ?? raw['Zone']    ?? raw['ZONE']);
  const aisle   = normalizeStr(raw['aisle']   ?? raw['Aisle']   ?? raw['AISLE']);
  const rack    = normalizeStr(raw['rack']    ?? raw['Rack']    ?? raw['RACK']);
  const bin     = normalizeStr(raw['bin']     ?? raw['Bin']     ?? raw['BIN']);
  const isActive = parseBool(
    raw['is_active'] ?? raw['Is_Active'] ?? raw['IsActive'] ?? raw['Active'] ?? true,
  );

  const errors: string[] = [];

  if (!section && !zone && !aisle && !rack && !bin) {
    errors.push('At least one hierarchy field must be specified.');
  }

  const allValues = [section, zone, aisle, rack, bin].filter(Boolean) as string[];
  if (allValues.some((v) => v.length > 50)) {
    errors.push('Field values must not exceed 50 characters.');
  }

  return { rowIndex: index, section, zone, aisle, rack, bin, isActive, errors };
}

/* ------------------------------------------------------------------
 * Component
 * ------------------------------------------------------------------ */

export default function CsvLocationImport({ warehouseId, onImportComplete }: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [isDragOver, setIsDragOver]     = useState(false);
  const [file, setFile]                 = useState<File | null>(null);
  const [parsedRows, setParsedRows]     = useState<ParsedRow[]>([]);
  const [fileError, setFileError]       = useState<string | null>(null);
  const [importing, setImporting]       = useState(false);
  const [importProgress, setImportProgress] = useState<{ current: number; total: number } | null>(null);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);

  const validRows   = parsedRows.filter((r) => r.errors.length === 0);
  const invalidRows = parsedRows.filter((r) => r.errors.length > 0);

  /* ── Parse file ─────────────────────────────────────────────── */
  const parseFile = useCallback((f: File) => {
    const ext = '.' + (f.name.split('.').pop() ?? '').toLowerCase();

    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setFileError(`Unsupported file type "${ext}". Use .csv, .xlsx, or .xls.`);
      return;
    }
    if (f.size === 0) {
      setFileError('The file is empty.');
      return;
    }
    if (f.size > MAX_FILE_SIZE) {
      setFileError(
        `File is too large (${(f.size / 1024 / 1024).toFixed(1)} MB). Maximum ${MAX_FILE_SIZE_MB} MB.`,
      );
      return;
    }

    const reader = new FileReader();

    reader.onload = (e) => {
      try {
        const data      = e.target?.result;
        const workbook  = XLSX.read(data, { type: 'array' });
        const sheet     = workbook.Sheets[workbook.SheetNames[0]];
        const rows      = XLSX.utils.sheet_to_json<Record<string, unknown>>(sheet, { defval: '' });

        if (rows.length === 0) {
          setFileError('The file contains no data rows.');
          return;
        }

        /* Detect duplicates within the file */
        const seen = new Set<string>();
        const parsed = rows.map((row, i) => {
          const p   = validateRow(row, i + 1);
          const key = [p.section ?? '', p.zone ?? '', p.aisle ?? '', p.rack ?? '', p.bin ?? ''].join('|');

          if (key !== '||||' && seen.has(key)) {
            p.errors.push('Duplicate location in this file.');
          } else {
            seen.add(key);
          }

          return p;
        });

        setFile(f);
        setParsedRows(parsed);
        setFileError(null);
        setImportResult(null);
      } catch {
        setFileError('Failed to parse file. Ensure it matches the template format.');
      }
    };

    reader.readAsArrayBuffer(f);
  }, []);

  /* ── Drop / file change handlers ────────────────────────────── */
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) parseFile(f);
    e.target.value = '';
  };

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const f = e.dataTransfer.files[0];
      if (f) parseFile(f);
    },
    [parseFile],
  );

  /* ── Import ─────────────────────────────────────────────────── */
  const handleImport = async () => {
    if (validRows.length === 0 || importing) return;

    setImporting(true);
    setImportProgress({ current: 0, total: validRows.length });
    setImportResult(null);

    let created = 0;
    const errors: Array<{ row: number; error: string }> = [];

    for (let i = 0; i < validRows.length; i++) {
      const row = validRows[i];
      try {
        await createLocation(warehouseId, {
          section:  row.section,
          zone:     row.zone,
          aisle:    row.aisle,
          rack:     row.rack,
          bin:      row.bin,
          is_active: row.isActive,
        });
        created++;
      } catch (err) {
        errors.push({ row: row.rowIndex, error: extractErrorMessage(err) });
      }
      setImportProgress({ current: i + 1, total: validRows.length });
    }

    setImporting(false);
    setImportProgress(null);
    setImportResult({ created, failed: errors.length, errors });

    if (created > 0) {
      onImportComplete();
      if (errors.length === 0) {
        /* Full success — reset to allow another import */
        setFile(null);
        setParsedRows([]);
      }
    }
  };

  const resetFile = () => {
    setFile(null);
    setParsedRows([]);
    setFileError(null);
    setImportResult(null);
  };

  /* ── Render ──────────────────────────────────────────────────── */
  return (
    <div className="flex flex-col gap-4">

      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h4 className="text-sm font-semibold text-text-primary">
            Import from CSV / Excel
          </h4>
          <p className="text-xs text-text-secondary mt-0.5">
            Upload a spreadsheet with columns:{' '}
            <code className="font-mono bg-background px-1 rounded">
              section, zone, aisle, rack, bin, is_active
            </code>
          </p>
        </div>
        <button
          onClick={downloadTemplate}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-primary border border-primary/30 rounded-default hover:bg-primary/5 transition-colors cursor-pointer flex-shrink-0"
        >
          <Download size={13} />
          Template
        </button>
      </div>

      {/* Drop zone — shown when no file loaded */}
      {!file && (
        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`flex flex-col items-center justify-center gap-2 border-2 border-dashed rounded-default py-8 px-4 cursor-pointer transition-colors select-none ${
            isDragOver
              ? 'border-primary bg-primary/5'
              : 'border-divider hover:border-primary/40 hover:bg-background'
          }`}
        >
          <FileSpreadsheet
            size={28}
            className={isDragOver ? 'text-primary' : 'text-text-secondary'}
          />
          <div className="text-center">
            <p className="text-sm font-medium text-text-primary">
              Drop file here or click to browse
            </p>
            <p className="text-xs text-text-secondary mt-0.5">
              .csv, .xlsx, .xls — max {MAX_FILE_SIZE_MB} MB
            </p>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.xlsx,.xls"
            className="hidden"
            onChange={handleFileChange}
          />
        </div>
      )}

      {/* File parse error */}
      {fileError && (
        <div className="flex items-center gap-2 bg-error-bg text-error-text rounded-default px-3 py-2 text-xs">
          <AlertTriangle size={14} className="flex-shrink-0" />
          {fileError}
        </div>
      )}

      {/* File loaded — preview & actions */}
      {file && parsedRows.length > 0 && (
        <div className="flex flex-col gap-3">

          {/* File info bar */}
          <div className="flex items-center justify-between gap-2 bg-background border border-divider rounded-default px-3 py-2">
            <div className="flex items-center flex-wrap gap-x-3 gap-y-1 text-xs">
              <span className="flex items-center gap-1.5 text-text-primary font-medium">
                <Upload size={12} className="text-text-secondary" />
                {file.name}
              </span>
              <span className="text-text-secondary">{parsedRows.length} row{parsedRows.length !== 1 ? 's' : ''}</span>
              {validRows.length > 0 && (
                <span className="text-success-text font-medium">
                  {validRows.length} ready
                </span>
              )}
              {invalidRows.length > 0 && (
                <span className="text-error-text font-medium">
                  {invalidRows.length} invalid
                </span>
              )}
            </div>
            <button
              onClick={resetFile}
              className="text-text-secondary hover:text-text-primary cursor-pointer flex-shrink-0"
              title="Remove file"
            >
              <XCircle size={14} />
            </button>
          </div>

          {/* Preview table — first 20 rows */}
          <div className="border border-divider rounded-default overflow-auto max-h-56">
            <table className="w-full text-xs whitespace-nowrap">
              <thead>
                <tr className="bg-background border-b border-divider">
                  <th className="px-3 py-2 text-left font-semibold text-text-secondary w-8">#</th>
                  <th className="px-3 py-2 text-left font-semibold text-text-secondary">Section</th>
                  <th className="px-3 py-2 text-left font-semibold text-text-secondary">Zone</th>
                  <th className="px-3 py-2 text-left font-semibold text-text-secondary">Aisle</th>
                  <th className="px-3 py-2 text-left font-semibold text-text-secondary">Rack</th>
                  <th className="px-3 py-2 text-left font-semibold text-text-secondary">Bin</th>
                  <th className="px-3 py-2 text-left font-semibold text-text-secondary">Active</th>
                  <th className="px-3 py-2 text-left font-semibold text-text-secondary">Status</th>
                </tr>
              </thead>
              <tbody>
                {parsedRows.slice(0, 20).map((row) => (
                  <tr
                    key={row.rowIndex}
                    className={`border-b border-divider last:border-0 ${
                      row.errors.length > 0 ? 'bg-error-bg/40' : ''
                    }`}
                  >
                    <td className="px-3 py-1.5 text-text-secondary">{row.rowIndex}</td>
                    <td className="px-3 py-1.5">{row.section ?? <span className="text-text-secondary">—</span>}</td>
                    <td className="px-3 py-1.5">{row.zone    ?? <span className="text-text-secondary">—</span>}</td>
                    <td className="px-3 py-1.5">{row.aisle   ?? <span className="text-text-secondary">—</span>}</td>
                    <td className="px-3 py-1.5">{row.rack    ?? <span className="text-text-secondary">—</span>}</td>
                    <td className="px-3 py-1.5">{row.bin     ?? <span className="text-text-secondary">—</span>}</td>
                    <td className="px-3 py-1.5">
                      <span className={row.isActive ? 'text-success-text' : 'text-text-secondary'}>
                        {row.isActive ? 'Yes' : 'No'}
                      </span>
                    </td>
                    <td className="px-3 py-1.5">
                      {row.errors.length > 0 ? (
                        <span
                          className="text-error-text cursor-help underline decoration-dotted"
                          title={row.errors.join(' | ')}
                        >
                          Invalid
                        </span>
                      ) : (
                        <span className="text-success-text">OK</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {parsedRows.length > 20 && (
              <p className="px-3 py-2 text-xs text-text-secondary text-center border-t border-divider">
                Showing first 20 of {parsedRows.length} rows
              </p>
            )}
          </div>

          {/* Invalid row details */}
          {invalidRows.length > 0 && (
            <div className="bg-error-bg rounded-default px-3 py-2.5">
              <p className="text-xs font-semibold text-error-text mb-1">
                {invalidRows.length} row{invalidRows.length !== 1 ? 's' : ''} with errors
                {' '}(will be skipped during import):
              </p>
              <ul className="text-xs text-error-text space-y-0.5">
                {invalidRows.slice(0, 5).map((r) => (
                  <li key={r.rowIndex}>
                    Row {r.rowIndex}: {r.errors.join(' — ')}
                  </li>
                ))}
                {invalidRows.length > 5 && (
                  <li className="text-error-text/70">
                    …and {invalidRows.length - 5} more
                  </li>
                )}
              </ul>
            </div>
          )}

          {/* Import progress bar */}
          {importing && importProgress && (
            <div className="flex items-center gap-3 bg-background border border-divider rounded-default px-3 py-2.5">
              <Loader2 size={14} className="animate-spin text-primary flex-shrink-0" />
              <span className="text-xs text-text-secondary flex-shrink-0">
                Importing {importProgress.current} of {importProgress.total}…
              </span>
              <div className="flex-grow h-1.5 bg-divider rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full transition-all duration-150"
                  style={{
                    width: `${Math.round((importProgress.current / importProgress.total) * 100)}%`,
                  }}
                />
              </div>
            </div>
          )}

          {/* Import result banner */}
          {importResult && (
            <div
              className={`rounded-default px-3 py-2.5 text-xs ${
                importResult.created > 0
                  ? 'bg-success-bg text-success-text'
                  : 'bg-error-bg text-error-text'
              }`}
            >
              <div className="flex items-center gap-2 font-semibold">
                {importResult.created > 0
                  ? <CheckCircle2 size={14} />
                  : <XCircle size={14} />}
                {importResult.created > 0
                  ? `${importResult.created} location${importResult.created !== 1 ? 's' : ''} imported successfully.`
                  : 'No locations imported.'}
                {importResult.failed > 0 && (
                  <span className="text-error-text font-normal ml-1">
                    {importResult.failed} failed.
                  </span>
                )}
              </div>
              {importResult.errors.length > 0 && (
                <ul className="mt-1 space-y-0.5 text-error-text font-normal">
                  {importResult.errors.slice(0, 5).map((e, i) => (
                    <li key={i}>Row {e.row}: {e.error}</li>
                  ))}
                  {importResult.errors.length > 5 && (
                    <li>…and {importResult.errors.length - 5} more</li>
                  )}
                </ul>
              )}
            </div>
          )}

          {/* Import action button */}
          {validRows.length > 0 && !importing && (
            <button
              onClick={handleImport}
              className="flex items-center justify-center gap-2 w-full py-2.5 bg-secondary text-white rounded-default text-sm font-medium hover:shadow-button-hover transition-shadow cursor-pointer"
            >
              <Upload size={14} />
              Import {validRows.length} Location{validRows.length !== 1 ? 's' : ''}
            </button>
          )}

        </div>
      )}
    </div>
  );
}

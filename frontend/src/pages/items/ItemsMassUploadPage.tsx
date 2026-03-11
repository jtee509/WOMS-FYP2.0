import { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import * as XLSX from 'xlsx';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import DownloadIcon from '@mui/icons-material/Download';
import CloseIcon from '@mui/icons-material/Close';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import type { ItemsImportResult } from '../../api/base_types/items';
import { importItems } from '../../api/base/items';

/* ------------------------------------------------------------------
 * Constants
 * ------------------------------------------------------------------ */

const ALLOWED_EXTENSIONS = ['.csv', '.xlsx', '.xls'];
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB
const PREVIEW_ROWS = 5;

const CSV_TEMPLATE =
  'item_name,master_sku,sku_name,description,uom,brand,category,item_type,is_active,variation_name_1,variation_values_1,variation_name_2,variation_values_2\n' +
  'Plain Tee,PLAIN-001,Plain Tee Display,A plain tee,Each,My Brand,Apparel,Outgoing Product,true,,,,\n' +
  'T-Shirt,TSHIRT-001,,A t-shirt with variations,Each,My Brand,Apparel,Outgoing Product,true,Colour,Red;Blue;Green,Size,S;M;L\n';

/* ------------------------------------------------------------------
 * Helpers
 * ------------------------------------------------------------------ */

function extractErrorMessage(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const e = err as { response?: { data?: { detail?: string | object } } };
    const detail = e.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (typeof detail === 'object') return JSON.stringify(detail);
  }
  return 'Upload failed. Please try again.';
}

function downloadTemplate() {
  const blob = new Blob([CSV_TEMPLATE], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'items_upload_template.csv';
  a.click();
  URL.revokeObjectURL(url);
}

/* ------------------------------------------------------------------
 * Component
 * ------------------------------------------------------------------ */

export default function ItemsMassUploadPage({ hideHeader = false }: { hideHeader?: boolean } = {}) {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [previewHeaders, setPreviewHeaders] = useState<string[]>([]);
  const [previewRows, setPreviewRows] = useState<Record<string, unknown>[]>([]);
  const [clientError, setClientError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [result, setResult] = useState<ItemsImportResult | null>(null);

  /* ---- File validation ---- */
  const validateFile = (f: File): string | null => {
    const ext = '.' + f.name.split('.').pop()?.toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      return `Invalid file type "${ext}". Please upload a .csv, .xlsx, or .xls file.`;
    }
    if (f.size === 0) return 'The selected file is empty.';
    if (f.size > MAX_FILE_SIZE) return `File is too large (${(f.size / 1024 / 1024).toFixed(1)} MB). Maximum is 10 MB.`;
    return null;
  };

  /* ---- Parse file for preview using xlsx ---- */
  const parseForPreview = (f: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = e.target?.result;
        const workbook = XLSX.read(data, { type: 'binary' });
        const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
        const rows = XLSX.utils.sheet_to_json<Record<string, unknown>>(firstSheet, {
          defval: '',
        });
        const headers = rows.length > 0 ? Object.keys(rows[0]) : [];
        setPreviewHeaders(headers);
        setPreviewRows(rows.slice(0, PREVIEW_ROWS));
      } catch {
        setClientError('Could not parse the file for preview. The file may be corrupted.');
        setFile(null);
      }
    };
    reader.readAsBinaryString(f);
  };

  /* ---- Handle file selection ---- */
  const handleFileSelect = (f: File) => {
    setClientError(null);
    setSubmitError(null);
    setResult(null);
    setPreviewHeaders([]);
    setPreviewRows([]);

    const err = validateFile(f);
    if (err) {
      setClientError(err);
      setFile(null);
      return;
    }

    setFile(f);
    parseForPreview(f);
  };

  /* ---- Drag and drop handlers ---- */
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) handleFileSelect(dropped);
  }, []);

  /* ---- Clear selection ---- */
  const clearFile = () => {
    setFile(null);
    setPreviewHeaders([]);
    setPreviewRows([]);
    setClientError(null);
    setSubmitError(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  /* ---- Submit ---- */
  const handleConfirmUpload = async () => {
    if (!file) return;
    setUploading(true);
    setSubmitError(null);
    try {
      const res = await importItems(file);
      setResult(res);
      setFile(null);
      setPreviewHeaders([]);
      setPreviewRows([]);
      if (fileInputRef.current) fileInputRef.current.value = '';
    } catch (err) {
      setSubmitError(extractErrorMessage(err));
    } finally {
      setUploading(false);
    }
  };

  const hasPreview = previewRows.length > 0;

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      {!hideHeader && (
        <div className="flex items-center gap-3 mb-6">
          <button
            onClick={() => navigate('/catalog/items')}
            className="p-1.5 rounded-default hover:bg-background text-text-secondary cursor-pointer"
          >
            <ArrowBackIcon fontSize="small" />
          </button>
          <h1 className="text-2xl font-semibold text-text-primary">Mass Upload Items</h1>
        </div>
      )}

      {/* Instructions card */}
      <div className="bg-surface rounded-card shadow-card p-5 mb-5">
        <h2 className="text-sm font-semibold text-text-primary mb-3">How to use</h2>
        <ol className="text-sm text-text-secondary space-y-1.5 list-decimal list-inside mb-4">
          <li>Download the CSV template and open it in Excel or Google Sheets.</li>
          <li>
            Fill in your items.{' '}
            <span className="font-medium text-text-primary">item_name</span> and{' '}
            <span className="font-medium text-text-primary">master_sku</span> are required.
          </li>
          <li>UOM, Brand, Category, and Item Type must match names already in Settings.</li>
          <li>
            For items with variations, fill in{' '}
            <span className="font-medium text-text-primary">variation_name_1</span> (e.g. <em>Colour</em>) and{' '}
            <span className="font-medium text-text-primary">variation_values_1</span> (e.g. <em>Red;Blue;Green</em>,
            semicolon-separated). Add a second dimension via{' '}
            <span className="font-medium text-text-primary">variation_name_2</span> /{' '}
            <span className="font-medium text-text-primary">variation_values_2</span> (optional).
            Combination SKUs can be set later in the item edit form.
          </li>
          <li>Upload the completed file and review the preview before confirming.</li>
        </ol>
        <button
          onClick={downloadTemplate}
          className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline cursor-pointer font-medium"
        >
          <DownloadIcon fontSize="small" />
          Download CSV Template
        </button>
      </div>

      {/* Upload card — hidden after result shown */}
      {!result && (
        <div className="bg-surface rounded-card shadow-card p-6 mb-5">
          {/* Drop zone — hide when preview is ready */}
          {!hasPreview && (
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-default flex flex-col items-center justify-center gap-3 py-14 cursor-pointer transition-colors ${
                isDragOver
                  ? 'border-primary bg-primary/5'
                  : 'border-divider hover:border-primary hover:bg-primary/5'
              }`}
            >
              <UploadFileIcon
                style={{ fontSize: 40 }}
                className={isDragOver ? 'text-primary' : 'text-text-secondary/40'}
              />
              <div className="text-center">
                <p className="text-sm font-medium text-text-primary">
                  Drag & drop or click to select file
                </p>
                <p className="text-xs text-text-secondary mt-1">
                  Accepted: .csv, .xlsx, .xls — max 10 MB
                </p>
              </div>
            </div>
          )}

          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.xlsx,.xls"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleFileSelect(f);
            }}
          />

          {/* Client error */}
          {clientError && (
            <div className="mt-4 bg-error-bg text-error-text rounded-default px-4 py-3 text-sm flex items-start gap-2">
              <ErrorOutlineIcon fontSize="small" className="flex-shrink-0 mt-0.5" />
              {clientError}
            </div>
          )}

          {/* Submit error */}
          {submitError && (
            <div className="mt-4 bg-error-bg text-error-text rounded-default px-4 py-3 text-sm flex items-start gap-2">
              <ErrorOutlineIcon fontSize="small" className="flex-shrink-0 mt-0.5" />
              {submitError}
            </div>
          )}

          {/* File badge + preview */}
          {file && (
            <div className="mt-4">
              {/* Selected file badge */}
              <div className="flex items-center gap-2 mb-4">
                <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-background rounded-default text-sm text-text-primary border border-divider">
                  <UploadFileIcon fontSize="small" className="text-primary" />
                  {file.name}
                  <span className="text-text-secondary text-xs">
                    ({(file.size / 1024).toFixed(0)} KB)
                  </span>
                </span>
                <button
                  type="button"
                  onClick={clearFile}
                  className="p-1 text-text-secondary hover:text-error cursor-pointer"
                  title="Remove file"
                >
                  <CloseIcon fontSize="small" />
                </button>
              </div>

              {/* Preview table */}
              {hasPreview && (
                <div className="mb-5">
                  <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">
                    Preview — first {previewRows.length} row{previewRows.length !== 1 ? 's' : ''}
                  </p>
                  <div className="overflow-x-auto rounded-default border border-divider">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="bg-background border-b border-divider">
                          {previewHeaders.map((h) => (
                            <th
                              key={h}
                              className="px-3 py-2 text-left font-semibold text-text-secondary whitespace-nowrap uppercase tracking-wider"
                            >
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-divider">
                        {previewRows.map((row, i) => (
                          <tr key={i} className="hover:bg-background/50">
                            {previewHeaders.map((h) => (
                              <td key={h} className="px-3 py-2 whitespace-nowrap text-text-primary">
                                {row[h] !== undefined && row[h] !== '' ? String(row[h]) : (
                                  <span className="text-text-secondary/40">—</span>
                                )}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <p className="text-xs text-text-secondary mt-1.5">
                    Showing first {previewRows.length} of your data rows. All rows will be processed on upload.
                  </p>
                </div>
              )}

              {/* Actions */}
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={handleConfirmUpload}
                  disabled={uploading || !!clientError}
                  className="flex items-center gap-1.5 px-5 py-2.5 bg-secondary text-white rounded-default text-sm font-medium hover:bg-secondary-dark disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer shadow-button-hover"
                >
                  {uploading ? 'Uploading...' : 'Confirm & Upload'}
                </button>
                <button
                  type="button"
                  onClick={() => navigate('/catalog/items')}
                  className="px-5 py-2.5 text-sm text-text-secondary hover:text-text-primary cursor-pointer border border-divider rounded-default"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Result card */}
      {result && (
        <div className="bg-surface rounded-card shadow-card p-6">
          {/* Summary */}
          <div className="flex flex-wrap gap-3 mb-5">
            {result.success_rows > 0 && (
              <div className="flex items-center gap-2 px-4 py-3 bg-success-bg text-success-text rounded-default text-sm font-medium">
                <CheckCircleOutlineIcon fontSize="small" />
                {result.success_rows} item{result.success_rows !== 1 ? 's' : ''} imported successfully
              </div>
            )}
            {result.error_rows > 0 && (
              <div className="flex items-center gap-2 px-4 py-3 bg-error-bg text-error-text rounded-default text-sm font-medium">
                <ErrorOutlineIcon fontSize="small" />
                {result.error_rows} row{result.error_rows !== 1 ? 's' : ''} had errors
              </div>
            )}
            {result.success_rows === 0 && result.error_rows === 0 && (
              <div className="flex items-center gap-2 px-4 py-3 bg-background text-text-secondary rounded-default text-sm">
                No data rows were found in the file.
              </div>
            )}
          </div>

          {/* Error table */}
          {result.errors.length > 0 && (
            <div className="mb-5">
              <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">
                Row Errors
              </p>
              <div className="overflow-x-auto rounded-default border border-divider">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-background border-b border-divider">
                      <th className="px-4 py-2.5 text-left text-xs font-semibold text-text-secondary uppercase tracking-wider w-16">Row</th>
                      <th className="px-4 py-2.5 text-left text-xs font-semibold text-text-secondary uppercase tracking-wider w-40">Master SKU</th>
                      <th className="px-4 py-2.5 text-left text-xs font-semibold text-text-secondary uppercase tracking-wider">Error</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-divider">
                    {result.errors.map((err, i) => (
                      <tr key={i} className="hover:bg-background/50">
                        <td className="px-4 py-2.5 text-text-secondary">{err.row}</td>
                        <td className="px-4 py-2.5 font-mono text-xs">{err.master_sku || '—'}</td>
                        <td className="px-4 py-2.5 text-error-text">{err.error}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setResult(null)}
              className="flex items-center gap-1.5 px-5 py-2.5 bg-secondary text-white rounded-default text-sm font-medium hover:bg-secondary-dark cursor-pointer shadow-button-hover"
            >
              <UploadFileIcon fontSize="small" />
              Upload Another File
            </button>
            <button
              type="button"
              onClick={() => navigate('/catalog/items')}
              className="px-5 py-2.5 text-sm text-text-secondary hover:text-text-primary cursor-pointer border border-divider rounded-default"
            >
              Back to Items
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

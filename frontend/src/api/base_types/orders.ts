export interface ImportRequest {
  platform: 'shopee' | 'lazada' | 'tiktok';
  seller_id: number;
  file: File;
}

export interface ImportError {
  row: number;
  error: string;
}

export interface ImportResult {
  import_batch_id: string;
  platform: string;
  seller_id: number;
  total_rows: number;
  success_rows: number;
  skipped_rows: number;
  error_rows: number;
  errors: ImportError[];
}

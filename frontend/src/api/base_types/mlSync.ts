export interface SyncRequest {
  platform_source?: string;
  seller_id?: number;
}

export interface SyncResult {
  staging_synced: number;
  staging_skipped: number;
  platforms_synced: number;
  sellers_synced: number;
  errors: string[];
}

/**
 * JSONB column type definitions matching PostgreSQL schema.
 * These provide TypeScript safety for JSONB fields stored in the database.
 */

/** Raw import data stored in order_import_raw.raw_data (full platform export row) */
export type RawImportData = Record<string, unknown>;

/** Platform-specific raw data on orders (platform_raw_data column) */
export type PlatformRawData = Record<string, unknown>;

/** Product variation attributes on items (variations_data column) */
export interface VariationsData {
  [attribute: string]: string | number | boolean;
}

/** Historical snapshot of an item record (items_history.snapshot_data) */
export type SnapshotData = Record<string, unknown>;

/** Audit log before-state (audit_log.old_data) */
export type AuditOldData = Record<string, unknown>;

/** Audit log after-state (audit_log.new_data) */
export type AuditNewData = Record<string, unknown>;

/** Role permissions stored as JSONB (roles.permissions) */
export interface RolePermissions {
  [resource: string]: string[];
}

/**
 * WOMS Warehouse & Inventory TypeScript types.
 * Mirrors backend schemas in backend/app/schemas/warehouse.py.
 */

/* ------------------------------------------------------------------
 * Warehouse
 * ------------------------------------------------------------------ */

export interface WarehouseRead {
  id: number;
  warehouse_name: string;
  address: Record<string, string> | null;
  is_active: boolean;
  location_count: number;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface WarehouseDuplicateResponse {
  original_id: number;
  new_warehouse: WarehouseRead;
  locations_copied: number;
}

export interface WarehouseCreate {
  warehouse_name: string;
  address?: Record<string, string>;
  is_active?: boolean;
}

export interface WarehouseUpdate {
  warehouse_name?: string;
  address?: Record<string, string>;
  is_active?: boolean;
}

/* ------------------------------------------------------------------
 * Inventory Location
 * ------------------------------------------------------------------ */

export interface InventoryLocationCreate {
  section?: string;
  zone?: string;
  aisle?: string;
  rack?: string;
  bin?: string;
  inventory_type_id?: number;
  sort_order?: number;
  is_active?: boolean;
}

export interface InventoryLocationUpdate {
  section?: string;
  zone?: string;
  aisle?: string;
  rack?: string;
  bin?: string;
  inventory_type_id?: number;
  sort_order?: number;
  is_active?: boolean;
}

export interface InventoryLocationRead {
  id: number;
  warehouse_id: number;
  section: string | null;
  zone: string | null;
  aisle: string | null;
  rack: string | null;
  bin: string | null;
  inventory_type_id: number | null;
  display_code: string | null;
  is_active: boolean;
  sort_order: number | null;
  created_at: string;
}

export interface LocationSummary {
  id: number;
  code: string;
  section: string | null;
  zone: string | null;
  aisle: string | null;
  rack: string | null;
  bin: string | null;
}

/* ------------------------------------------------------------------
 * Inventory Level (enriched)
 * ------------------------------------------------------------------ */

export type StockStatus = 'ok' | 'low' | 'critical' | 'out_of_stock' | 'overstock';

export interface InventoryLevelEnrichedRead {
  id: number;
  location_id: number;
  item_id: number;
  item_name: string;
  master_sku: string;
  location: LocationSummary;
  lot_id: number | null;
  quantity_available: number;
  reserved_quantity: number;
  reorder_point: number | null;
  safety_stock: number | null;
  max_stock: number | null;
  stock_status: StockStatus;
  alert_triggered_at: string | null;
  alert_acknowledged: boolean;
  created_at: string;
  updated_at: string;
}

/* ------------------------------------------------------------------
 * Inventory Alert
 * ------------------------------------------------------------------ */

export type AlertType = 'low_stock' | 'out_of_stock' | 'critical' | 'overstock';

export interface InventoryAlertRead {
  id: number;
  inventory_level_id: number;
  item_id: number;
  warehouse_id: number;
  alert_type: AlertType;
  current_quantity: number;
  threshold_quantity: number;
  alert_message: string | null;
  is_resolved: boolean;
  resolved_at: string | null;
  resolution_notes: string | null;
  resolved_by_user_id: number | null;
  created_at: string;
}

/* ------------------------------------------------------------------
 * Movement Type
 * ------------------------------------------------------------------ */

export interface MovementTypeRead {
  id: number;
  name: string;
}

/* ------------------------------------------------------------------
 * Inventory Movement
 * ------------------------------------------------------------------ */

export interface InventoryMovementRead {
  id: number;
  warehouse_id: number;
  movement_type_id: number;
  movement_type: MovementTypeRead;
  item_id: number;
  item_name: string;
  master_sku: string;
  reference_number: string | null;
  notes: string | null;
  quantity: number;
  is_inbound: boolean;
  created_at: string;
  created_by: number | null;
}

export interface InventoryTransactionCreate {
  location_id: number;
  is_inbound: boolean;
  quantity_change: number;
}

export interface InventoryMovementCreate {
  warehouse_id: number;
  movement_type_id: number;
  item_id: number;
  transactions: InventoryTransactionCreate[];
  reference_number?: string;
  notes?: string;
}

/* ------------------------------------------------------------------
 * Bundle Fulfillment / Reservation
 * ------------------------------------------------------------------ */

export interface ReserveRequest {
  item_id: number;
  quantity: number;
  warehouse_id: number;
}

export interface ReserveResponse {
  item_id: number;
  quantity_reserved: number;
  warehouse_id: number;
}

export interface ReleaseRequest {
  item_id: number;
  quantity: number;
  warehouse_id: number;
}

/* ------------------------------------------------------------------
 * Location Hierarchy Tree (from GET /hierarchy)
 * ------------------------------------------------------------------ */

export interface LocationTreeNode {
  name: string;
  type: 'warehouse' | 'section' | 'zone' | 'aisle' | 'rack' | 'bin';
  total_locations?: number;
  summary: string;
  children?: LocationTreeNode[];
  location_id?: number;
  display_code?: string;
  is_active?: boolean;
  sort_order?: number;
  is_orphan?: boolean;
}

/* ------------------------------------------------------------------
 * Bulk Location Update
 * ------------------------------------------------------------------ */

export interface BulkLocationUpdateItem {
  id: number;
  section?: string;
  zone?: string;
  aisle?: string;
  rack?: string;
  bin?: string;
  is_active?: boolean;
  sort_order?: number;
}

export interface BulkLocationUpdateRequest {
  locations: BulkLocationUpdateItem[];
}

export interface BulkLocationUpdateResult {
  id: number;
  success: boolean;
  error?: string;
}

export interface BulkLocationUpdateResponse {
  updated: number;
  failed: number;
  results: BulkLocationUpdateResult[];
}

/* ------------------------------------------------------------------
 * Bulk Location Generation
 * ------------------------------------------------------------------ */

export interface SegmentRangeInput {
  prefix: string;
  start: number | null;
  end: number | null;
  pad: number;
  values: string[] | null;
}

export interface BulkGenerateRequest {
  section?: SegmentRangeInput;
  zone?: SegmentRangeInput;
  aisle?: SegmentRangeInput;
  rack?: SegmentRangeInput;
  bin?: SegmentRangeInput;
  inventory_type_id?: number;
  is_active?: boolean;
}

export interface BulkGenerateError {
  location: string;
  reason: string;
}

export interface BulkGenerateResponse {
  warehouse_id: number;
  total_requested: number;
  created: number;
  skipped: number;
  errors: BulkGenerateError[];
}

/* ------------------------------------------------------------------
 * Rename Level
 * ------------------------------------------------------------------ */

export type HierarchyLevel = 'section' | 'zone' | 'aisle' | 'rack' | 'bin';

export interface RenameLevelRequest {
  level: HierarchyLevel;
  old_value: string;
  new_value: string;
  section?: string;
  zone?: string;
  aisle?: string;
  rack?: string;
}

export interface RenameLevelResponse {
  updated_count: number;
  level: string;
  old_value: string;
  new_value: string;
}


/**
 * Generic shape for any item attribute lookup table.
 * Used for: ItemType, Category, Brand, BaseUOM.
 */
export interface AttributeItem {
  id: number;
  name: string;
}

/* ------------------------------------------------------------------
 * Paginated response wrapper (mirrors backend PaginatedResponse[T])
 * ------------------------------------------------------------------ */

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

/* ------------------------------------------------------------------
 * Item CRUD types (mirrors backend ItemRead / ItemCreate / ItemUpdate)
 * ------------------------------------------------------------------ */

export interface ItemRead {
  item_id: number;
  parent_id: number | null;
  item_name: string;
  master_sku: string;
  sku_name: string | null;
  description: string | null;
  image_url: string | null;
  uom_id: number | null;
  brand_id: number | null;
  item_type_id: number | null;
  category_id: number | null;
  is_active: boolean;
  has_variation: boolean;
  variations_data: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
  uom: AttributeItem | null;
  brand: AttributeItem | null;
  item_type: AttributeItem | null;
  category: AttributeItem | null;
}

export interface ItemCreate {
  item_name: string;
  master_sku: string;
  sku_name?: string;
  description?: string;
  image_url?: string;
  uom_id?: number;
  brand_id?: number;
  item_type_id?: number;
  category_id?: number;
  is_active?: boolean;
  parent_id?: number;
  has_variation?: boolean;
  variations_data?: Record<string, unknown>;
}

export interface ItemUpdate {
  item_name?: string;
  sku_name?: string;
  description?: string;
  image_url?: string;
  uom_id?: number;
  brand_id?: number;
  item_type_id?: number;
  category_id?: number;
  is_active?: boolean;
  has_variation?: boolean;
  variations_data?: Record<string, unknown>;
}


/* ------------------------------------------------------------------
 * Mass Import types (mirrors backend ImportResult / ImportRowError)
 * ------------------------------------------------------------------ */

export interface ImportRowError {
  row: number;
  master_sku: string;
  error: string;
}

export interface ItemsImportResult {
  total_rows: number;
  success_rows: number;
  error_rows: number;
  errors: ImportRowError[];
}


/* ------------------------------------------------------------------
 * Bundle types (mirrors backend BundleCreateRequest / BundleReadResponse)
 * ------------------------------------------------------------------ */

export interface BundleComponentInput {
  item_id: number;
  quantity: number;
}

export interface BundleCreateRequest {
  item_name: string;
  master_sku: string;
  sku_name?: string;
  description?: string;
  image_url?: string;
  uom_id?: number;
  brand_id?: number;
  category_id?: number;
  is_active?: boolean;
  platform_id?: number;
  seller_id?: number;
  components: BundleComponentInput[];
}

export interface BundleUpdateRequest {
  item_name?: string;
  master_sku?: string;
  sku_name?: string;
  description?: string;
  image_url?: string;
  uom_id?: number;
  brand_id?: number;
  category_id?: number;
  is_active?: boolean;
  components?: BundleComponentInput[];
}

export interface BundleComponentRead {
  id: number;
  item_id: number;
  item_name: string;
  master_sku: string;
  quantity: number;
}

export interface BundleReadResponse {
  item: ItemRead;
  listing_id: number;
  platform_sku: string;
  components: BundleComponentRead[];
}

export interface BundleListItem extends ItemRead {
  component_count: number;
  total_quantity: number;
}

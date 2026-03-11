import apiClient from './client';
import type {
  AttributeItem,
  ItemRead,
  ItemCreate,
  ItemUpdate,
  ItemsImportResult,
  PaginatedResponse,
  BundleCreateRequest,
  BundleUpdateRequest,
  BundleReadResponse,
  BundleListItem,
} from '../base_types/items';

/* ------------------------------------------------------------------
 * Normaliser helpers — map backend field names to generic { id, name }
 * ------------------------------------------------------------------ */

function normaliseType(r: { item_type_id: number; item_type_name: string }): AttributeItem {
  return { id: r.item_type_id, name: r.item_type_name };
}
function normaliseCategory(r: { category_id: number; category_name: string }): AttributeItem {
  return { id: r.category_id, name: r.category_name };
}
function normaliseBrand(r: { brand_id: number; brand_name: string }): AttributeItem {
  return { id: r.brand_id, name: r.brand_name };
}
function normaliseUOM(r: { uom_id: number; uom_name: string }): AttributeItem {
  return { id: r.uom_id, name: r.uom_name };
}
function normaliseStatus(r: { status_id: number; status_name: string }): AttributeItem {
  return { id: r.status_id, name: r.status_name };
}

/* ------------------------------------------------------------------
 * Status
 * ------------------------------------------------------------------ */

export async function listStatuses(): Promise<AttributeItem[]> {
  const res = await apiClient.get('/items/statuses');
  return res.data.map(normaliseStatus);
}

export async function createStatus(name: string): Promise<AttributeItem> {
  const res = await apiClient.post('/items/statuses', { status_name: name });
  return normaliseStatus(res.data);
}

export async function updateStatus(id: number, name: string): Promise<AttributeItem> {
  const res = await apiClient.patch(`/items/statuses/${id}`, { status_name: name });
  return normaliseStatus(res.data);
}

export async function deleteStatus(id: number): Promise<void> {
  await apiClient.delete(`/items/statuses/${id}`);
}

/* ------------------------------------------------------------------
 * Item Type
 * ------------------------------------------------------------------ */

export async function listItemTypes(): Promise<AttributeItem[]> {
  const res = await apiClient.get('/items/types');
  return res.data.map(normaliseType);
}

export async function createItemType(name: string): Promise<AttributeItem> {
  const res = await apiClient.post('/items/types', { item_type_name: name });
  return normaliseType(res.data);
}

export async function updateItemType(id: number, name: string): Promise<AttributeItem> {
  const res = await apiClient.patch(`/items/types/${id}`, { item_type_name: name });
  return normaliseType(res.data);
}

export async function deleteItemType(id: number): Promise<void> {
  await apiClient.delete(`/items/types/${id}`);
}

/* ------------------------------------------------------------------
 * Category
 * ------------------------------------------------------------------ */

export async function listCategories(): Promise<AttributeItem[]> {
  const res = await apiClient.get('/items/categories');
  return res.data.map(normaliseCategory);
}

export async function createCategory(name: string): Promise<AttributeItem> {
  const res = await apiClient.post('/items/categories', { category_name: name });
  return normaliseCategory(res.data);
}

export async function updateCategory(id: number, name: string): Promise<AttributeItem> {
  const res = await apiClient.patch(`/items/categories/${id}`, { category_name: name });
  return normaliseCategory(res.data);
}

export async function deleteCategory(id: number): Promise<void> {
  await apiClient.delete(`/items/categories/${id}`);
}

/* ------------------------------------------------------------------
 * Brand
 * ------------------------------------------------------------------ */

export async function listBrands(): Promise<AttributeItem[]> {
  const res = await apiClient.get('/items/brands');
  return res.data.map(normaliseBrand);
}

export async function createBrand(name: string): Promise<AttributeItem> {
  const res = await apiClient.post('/items/brands', { brand_name: name });
  return normaliseBrand(res.data);
}

export async function updateBrand(id: number, name: string): Promise<AttributeItem> {
  const res = await apiClient.patch(`/items/brands/${id}`, { brand_name: name });
  return normaliseBrand(res.data);
}

export async function deleteBrand(id: number): Promise<void> {
  await apiClient.delete(`/items/brands/${id}`);
}

/* ------------------------------------------------------------------
 * Base UOM
 * ------------------------------------------------------------------ */

export async function listUOMs(): Promise<AttributeItem[]> {
  const res = await apiClient.get('/items/uoms');
  return res.data.map(normaliseUOM);
}

export async function createUOM(name: string): Promise<AttributeItem> {
  const res = await apiClient.post('/items/uoms', { uom_name: name });
  return normaliseUOM(res.data);
}

export async function updateUOM(id: number, name: string): Promise<AttributeItem> {
  const res = await apiClient.patch(`/items/uoms/${id}`, { uom_name: name });
  return normaliseUOM(res.data);
}

export async function deleteUOM(id: number): Promise<void> {
  await apiClient.delete(`/items/uoms/${id}`);
}

/* ------------------------------------------------------------------
 * Item CRUD
 * ------------------------------------------------------------------ */

export interface ListItemsParams {
  page?: number;
  page_size?: number;
  search?: string;
  is_active?: boolean;
  category_id?: number;
  brand_id?: number;
  item_type_id?: number;
  exclude_item_type_id?: number;
  include_deleted?: boolean;
}

export interface ItemCounts {
  all: number;
  live: number;
  unpublished: number;
  deleted: number;
}

export async function getItemCounts(params: { exclude_item_type_id?: number } = {}): Promise<ItemCounts> {
  const res = await apiClient.get('/items/counts', { params });
  return res.data;
}

export async function listItems(params: ListItemsParams = {}): Promise<PaginatedResponse<ItemRead>> {
  const res = await apiClient.get('/items', { params });
  return res.data;
}

export async function getItem(itemId: number): Promise<ItemRead> {
  const res = await apiClient.get(`/items/${itemId}`);
  return res.data;
}

export async function createItem(data: ItemCreate): Promise<ItemRead> {
  const res = await apiClient.post('/items', data);
  return res.data;
}

export async function updateItem(itemId: number, data: ItemUpdate): Promise<ItemRead> {
  const res = await apiClient.patch(`/items/${itemId}`, data);
  return res.data;
}

export async function deleteItem(itemId: number): Promise<void> {
  await apiClient.delete(`/items/${itemId}`);
}

export async function restoreItem(itemId: number): Promise<ItemRead> {
  const res = await apiClient.post<ItemRead>(`/items/${itemId}/restore`);
  return res.data;
}

/* ------------------------------------------------------------------
 * Image Upload
 * ------------------------------------------------------------------ */

export async function uploadItemImage(file: File): Promise<{ url: string }> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await apiClient.post<{ url: string }>('/items/upload-image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
}


/* ------------------------------------------------------------------
 * Mass Import
 * ------------------------------------------------------------------ */

export async function importItems(file: File): Promise<ItemsImportResult> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await apiClient.post<ItemsImportResult>('/items/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
}

export async function importBundles(file: File): Promise<ItemsImportResult> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await apiClient.post<ItemsImportResult>('/items/bundles/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
}


/* ------------------------------------------------------------------
 * Bundles
 * ------------------------------------------------------------------ */

export interface ListBundlesParams {
  page?: number;
  page_size?: number;
  search?: string;
  is_active?: boolean;
  category_id?: number;
  brand_id?: number;
  include_deleted?: boolean;
}

export async function listBundles(params: ListBundlesParams = {}): Promise<PaginatedResponse<BundleListItem>> {
  const res = await apiClient.get('/items/bundles', { params });
  return res.data;
}

export async function getBundleCounts(): Promise<ItemCounts> {
  const res = await apiClient.get('/items/bundles/counts');
  return res.data;
}

export async function getBundle(itemId: number): Promise<BundleReadResponse> {
  const res = await apiClient.get<BundleReadResponse>(`/items/bundles/${itemId}`);
  return res.data;
}

export async function createBundle(data: BundleCreateRequest): Promise<BundleReadResponse> {
  const res = await apiClient.post<BundleReadResponse>('/items/bundles', data);
  return res.data;
}

export async function updateBundle(
  itemId: number,
  data: BundleUpdateRequest,
): Promise<BundleReadResponse> {
  const res = await apiClient.patch<BundleReadResponse>(`/items/bundles/${itemId}`, data);
  return res.data;
}

export async function deleteBundle(itemId: number): Promise<void> {
  await apiClient.delete(`/items/bundles/${itemId}`);
}

export async function restoreBundle(itemId: number): Promise<BundleReadResponse> {
  const res = await apiClient.post<BundleReadResponse>(`/items/bundles/${itemId}/restore`);
  return res.data;
}

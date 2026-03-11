/**
 * WOMS Warehouse & Inventory API functions.
 * All endpoints under /api/v1/warehouse.
 */

import apiClient from './client';
import type {
  WarehouseRead,
  WarehouseCreate,
  WarehouseUpdate,
  WarehouseDuplicateResponse,
  InventoryLocationRead,
  InventoryLocationCreate,
  InventoryLocationUpdate,
  BulkLocationUpdateRequest,
  BulkLocationUpdateResponse,
  InventoryLevelEnrichedRead,
  InventoryAlertRead,
  InventoryMovementRead,
  InventoryMovementCreate,
  MovementTypeRead,
  ReserveRequest,
  ReserveResponse,
  ReleaseRequest,
  LocationTreeNode,
  BulkGenerateRequest,
  BulkGenerateResponse,
  RenameLevelRequest,
  RenameLevelResponse,
} from '../base_types/warehouse';
import type { PaginatedResponse } from '../base_types/items';

/* ------------------------------------------------------------------
 * Warehouses
 * ------------------------------------------------------------------ */

export async function listWarehouses(isActive?: boolean): Promise<WarehouseRead[]> {
  const params = isActive !== undefined ? { is_active: isActive } : {};
  const res = await apiClient.get('/warehouse', { params });
  return res.data;
}

export async function getWarehouse(id: number): Promise<WarehouseRead> {
  const res = await apiClient.get(`/warehouse/${id}`);
  return res.data;
}

export async function createWarehouse(data: WarehouseCreate): Promise<WarehouseRead> {
  const res = await apiClient.post('/warehouse', data);
  return res.data;
}

export async function updateWarehouse(id: number, data: WarehouseUpdate): Promise<WarehouseRead> {
  const res = await apiClient.patch(`/warehouse/${id}`, data);
  return res.data;
}

export async function toggleWarehouseStatus(id: number): Promise<WarehouseRead> {
  const res = await apiClient.patch(`/warehouse/${id}/toggle-status`);
  return res.data;
}

export async function deleteWarehouse(id: number): Promise<void> {
  await apiClient.delete(`/warehouse/${id}`);
}

export async function duplicateWarehouse(id: number): Promise<WarehouseDuplicateResponse> {
  const res = await apiClient.post(`/warehouse/${id}/duplicate`);
  return res.data;
}

/* ------------------------------------------------------------------
 * Inventory Locations
 * ------------------------------------------------------------------ */

export async function listLocations(warehouseId: number): Promise<InventoryLocationRead[]> {
  const res = await apiClient.get(`/warehouse/${warehouseId}/locations`);
  return res.data;
}

export async function createLocation(
  warehouseId: number,
  data: InventoryLocationCreate,
): Promise<InventoryLocationRead> {
  const res = await apiClient.post(`/warehouse/${warehouseId}/locations`, data);
  return res.data;
}

export async function updateLocation(
  locationId: number,
  data: InventoryLocationUpdate,
): Promise<InventoryLocationRead> {
  const res = await apiClient.patch(`/warehouse/locations/${locationId}`, data);
  return res.data;
}

export async function deleteLocation(locationId: number): Promise<void> {
  await apiClient.delete(`/warehouse/locations/${locationId}`);
}

export interface LocationSubtreeFilter {
  section?: string;
  zone?: string;
  aisle?: string;
  rack?: string;
}

export async function deleteLocationSubtree(
  warehouseId: number,
  filter: LocationSubtreeFilter,
): Promise<{ deleted: number }> {
  const res = await apiClient.delete(`/warehouse/${warehouseId}/locations/subtree`, {
    params: filter,
  });
  return res.data;
}

export async function bulkUpdateLocations(
  warehouseId: number,
  data: BulkLocationUpdateRequest,
): Promise<BulkLocationUpdateResponse> {
  const res = await apiClient.patch(`/warehouse/${warehouseId}/locations/bulk-update`, data);
  return res.data;
}


export async function getLocationHierarchy(warehouseId: number): Promise<LocationTreeNode[]> {
  const res = await apiClient.get(`/warehouse/${warehouseId}/locations/hierarchy`);
  return res.data;
}

export async function bulkGenerateLocations(
  warehouseId: number,
  data: BulkGenerateRequest,
): Promise<BulkGenerateResponse> {
  const res = await apiClient.post(`/warehouse/${warehouseId}/locations/bulk-generate`, data);
  return res.data;
}

export async function renameLevel(
  warehouseId: number,
  data: RenameLevelRequest,
): Promise<RenameLevelResponse> {
  const res = await apiClient.patch(`/warehouse/${warehouseId}/locations/rename-level`, data);
  return res.data;
}

/* ------------------------------------------------------------------
 * Inventory Levels (enriched — item name + location code + stock status)
 * ------------------------------------------------------------------ */

export interface ListInventoryParams {
  page?: number;
  page_size?: number;
  item_id?: number;
  search?: string;
  stock_status?: string;
}

export async function listInventoryLevels(
  warehouseId: number,
  params: ListInventoryParams = {},
): Promise<PaginatedResponse<InventoryLevelEnrichedRead>> {
  const res = await apiClient.get(`/warehouse/${warehouseId}/inventory`, { params });
  return res.data;
}

/* ------------------------------------------------------------------
 * Inventory Alerts
 * ------------------------------------------------------------------ */

export async function listAlerts(
  warehouseId: number,
  isResolved?: boolean,
): Promise<InventoryAlertRead[]> {
  const params = isResolved !== undefined ? { is_resolved: isResolved } : {};
  const res = await apiClient.get(`/warehouse/${warehouseId}/alerts`, { params });
  return res.data;
}

export async function resolveAlert(
  alertId: number,
  data: { resolution_notes?: string },
): Promise<InventoryAlertRead> {
  const res = await apiClient.patch(`/warehouse/alerts/${alertId}/resolve`, data);
  return res.data;
}

/* ------------------------------------------------------------------
 * Movement Types
 * ------------------------------------------------------------------ */

export async function listMovementTypes(): Promise<MovementTypeRead[]> {
  const res = await apiClient.get('/warehouse/movement-types');
  return res.data;
}

/* ------------------------------------------------------------------
 * Inventory Movements
 * ------------------------------------------------------------------ */

export interface ListMovementsParams {
  page?: number;
  page_size?: number;
}

export async function listMovements(
  warehouseId: number,
  params: ListMovementsParams = {},
): Promise<PaginatedResponse<InventoryMovementRead>> {
  const res = await apiClient.get(`/warehouse/${warehouseId}/movements`, { params });
  return res.data;
}

export async function createMovement(
  data: InventoryMovementCreate,
): Promise<InventoryMovementRead> {
  const res = await apiClient.post('/warehouse/movements', data);
  return res.data;
}

/* ------------------------------------------------------------------
 * Bundle Fulfillment / Reservation
 * ------------------------------------------------------------------ */

export async function reserveStock(data: ReserveRequest): Promise<ReserveResponse> {
  const res = await apiClient.post('/warehouse/reserve', data);
  return res.data;
}

export async function releaseStock(data: ReleaseRequest): Promise<void> {
  await apiClient.post('/warehouse/release', data);
}


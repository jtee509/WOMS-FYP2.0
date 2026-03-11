/**
 * WOMS Platform & Seller API functions.
 * All endpoints under /api/v1/platforms and /api/v1/sellers.
 */

import apiClient from './client';
import type {
  PlatformRead,
  PlatformCreate,
  PlatformUpdate,
  SellerRead,
  SellerCreate,
  SellerUpdate,
} from '../base_types/platform';
import type { PaginatedResponse } from '../base_types/items';

/* ------------------------------------------------------------------
 * Platforms
 * ------------------------------------------------------------------ */

export async function listPlatforms(isActive?: boolean): Promise<PlatformRead[]> {
  const params = isActive !== undefined ? { is_active: isActive } : {};
  const res = await apiClient.get('/platforms', { params });
  return res.data;
}

export async function getPlatform(id: number): Promise<PlatformRead> {
  const res = await apiClient.get(`/platforms/${id}`);
  return res.data;
}

export async function createPlatform(data: PlatformCreate): Promise<PlatformRead> {
  const res = await apiClient.post('/platforms', data);
  return res.data;
}

export async function updatePlatform(id: number, data: PlatformUpdate): Promise<PlatformRead> {
  const res = await apiClient.patch(`/platforms/${id}`, data);
  return res.data;
}

/* ------------------------------------------------------------------
 * Sellers
 * ------------------------------------------------------------------ */

export interface ListSellersParams {
  page?: number;
  page_size?: number;
  platform_id?: number;
  is_active?: boolean;
  search?: string;
}

export async function listSellers(
  params: ListSellersParams = {},
): Promise<PaginatedResponse<SellerRead>> {
  const res = await apiClient.get('/sellers', { params });
  return res.data;
}

export async function getSeller(id: number): Promise<SellerRead> {
  const res = await apiClient.get(`/sellers/${id}`);
  return res.data;
}

export async function createSeller(data: SellerCreate): Promise<SellerRead> {
  const res = await apiClient.post('/sellers', data);
  return res.data;
}

export async function updateSeller(id: number, data: SellerUpdate): Promise<SellerRead> {
  const res = await apiClient.patch(`/sellers/${id}`, data);
  return res.data;
}

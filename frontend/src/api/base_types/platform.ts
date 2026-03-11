/**
 * WOMS Platform & Seller TypeScript types.
 * Mirrors backend schemas in backend/app/schemas/platform.py.
 */

/* ------------------------------------------------------------------
 * Platform
 * ------------------------------------------------------------------ */

export interface PlatformRead {
  platform_id: number;
  platform_name: string;
  address: string | null;
  postcode: string | null;
  api_endpoint: string | null;
  is_active: boolean;
  is_online: boolean;
  created_at: string;
}

export interface PlatformCreate {
  platform_name: string;
  address?: string;
  postcode?: string;
  api_endpoint?: string;
  is_active?: boolean;
  is_online?: boolean;
}

export interface PlatformUpdate {
  platform_name?: string;
  address?: string;
  postcode?: string;
  api_endpoint?: string;
  is_active?: boolean;
  is_online?: boolean;
}

/* ------------------------------------------------------------------
 * Seller
 * ------------------------------------------------------------------ */

export interface SellerRead {
  seller_id: number;
  store_name: string;
  platform_id: number | null;
  platform_store_id: string | null;
  company_name: string | null;
  is_active: boolean;
  created_at: string;
  platform: PlatformRead | null;
}

export interface SellerCreate {
  store_name: string;
  platform_id?: number;
  platform_store_id?: string;
  company_name?: string;
  is_active?: boolean;
}

export interface SellerUpdate {
  store_name?: string;
  platform_id?: number;
  platform_store_id?: string;
  company_name?: string;
  is_active?: boolean;
}

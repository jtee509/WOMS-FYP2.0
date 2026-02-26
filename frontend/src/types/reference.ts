export interface LoadResult {
  status: string;
  message: string;
  created: number;
  updated: number;
  total: number;
}

export interface Platform {
  platform_id: number;
  platform_name: string;
  address: string | null;
  postcode: string | null;
  is_active: boolean;
}

export interface Seller {
  seller_id: number;
  seller_name: string;
  company_name: string | null;
  platform_id: number;
  platform_store_id: string | null;
  is_active: boolean;
}

export interface Item {
  item_id: number;
  master_sku: string;
  product_name: string;
  sku_name: string | null;
  base_uom_id: number | null;
  is_active: boolean;
  variations_data: Record<string, unknown> | null;
}

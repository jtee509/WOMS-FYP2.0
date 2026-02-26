import apiClient from './client';
import type { ImportResult } from '../types/orders';

export async function importOrders(
  platform: string,
  sellerId: number,
  file: File,
): Promise<ImportResult> {
  const formData = new FormData();
  formData.append('platform', platform);
  formData.append('seller_id', sellerId.toString());
  formData.append('file', file);

  const response = await apiClient.post<ImportResult>('/orders/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

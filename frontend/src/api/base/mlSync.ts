import apiClient from './client';
import type { SyncRequest, SyncResult } from '../base_types/mlSync';

export async function syncStaging(request?: SyncRequest): Promise<SyncResult> {
  const response = await apiClient.post<SyncResult>('/ml/sync', request ?? {});
  return response.data;
}

export async function initSchema(): Promise<{ status: string; message: string }> {
  const response = await apiClient.post<{ status: string; message: string }>('/ml/init-schema');
  return response.data;
}

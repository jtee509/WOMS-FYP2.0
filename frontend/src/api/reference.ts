import apiClient from './client';
import type { LoadResult } from '../types/reference';

export async function loadPlatforms(file: File): Promise<LoadResult> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post<LoadResult>('/reference/load-platforms', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

export async function loadSellers(
  sellersFile: File,
  platformsFile?: File,
): Promise<LoadResult> {
  const formData = new FormData();
  formData.append('sellers_file', sellersFile);
  if (platformsFile) {
    formData.append('platforms_file', platformsFile);
  }

  const response = await apiClient.post<LoadResult>('/reference/load-sellers', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

export async function loadItems(file: File): Promise<LoadResult> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post<LoadResult>('/reference/load-items', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

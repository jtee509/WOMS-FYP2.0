import apiClient from '../api/client';

export type DatabaseTarget = 'woms_db' | 'ml_woms_db';

/**
 * Service layer for PostgreSQL data fetching with multi-DB toggle.
 *
 * Passes X-Database-Target header so the backend can route queries to
 * either woms_db or ml_woms_db. Defaults to woms_db.
 *
 * NOTE: Backend does not yet implement this header — this is a forward-
 * looking abstraction. Currently all calls go to the default database.
 */
export async function fetchData<T>(
  endpoint: string,
  target: DatabaseTarget = 'woms_db',
): Promise<T> {
  const response = await apiClient.get<T>(endpoint, {
    headers: { 'X-Database-Target': target },
  });
  return response.data;
}

export async function postData<T>(
  endpoint: string,
  data: unknown,
  target: DatabaseTarget = 'woms_db',
): Promise<T> {
  const response = await apiClient.post<T>(endpoint, data, {
    headers: { 'X-Database-Target': target },
  });
  return response.data;
}

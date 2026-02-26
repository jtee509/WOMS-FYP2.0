import apiClient from './client';
import type { LoginRequest, LoginResponse } from '../base_types/auth';

export async function login(credentials: LoginRequest): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>('/auth/login', credentials);
  return response.data;
}

export async function getMe(): Promise<LoginResponse> {
  const response = await apiClient.get<LoginResponse>('/auth/me');
  return response.data;
}

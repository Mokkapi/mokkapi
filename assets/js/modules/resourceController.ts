// resourceController.js

import { apiClient, ApiResponse } from './apiClient';
import type { Endpoint, Handler, AuthProfile } from '../types';


export class ResourceController<T> {
  constructor(private path: string) {}

  /** GET   /path/        → list */
  async list(): Promise<T[]> {
    const { data } = await apiClient<T[]>(`${this.path}/`, 'GET');
    return data!;
  }

  /** GET   /path/:id/   → single */
  async get(id: string): Promise<T> {
    const { data } = await apiClient<T>(`${this.path}/${encodeURIComponent(id)}/`, 'GET');
    return data!;
  }

  /** POST  /path/       → created */
  async create(payload: Partial<T>): Promise<T> {
    const { data } = await apiClient<T>(`${this.path}/`, 'POST', payload);
    return data!;
  }

  /** PUT   /path/:id/   → updated */
  async update(id: string, payload: Partial<T>): Promise<T> {
    const { data } = await apiClient<T>(`${this.path}/${encodeURIComponent(id)}/`, 'PUT', payload);
    return data!;
  }

  /** DELETE /path/:id/  → null on 204 */
  async delete(id: string): Promise<null> {
    const { data } = await apiClient<null>(`${this.path}/${encodeURIComponent(id)}/`, 'DELETE');
    return data;
  }
}

// exports
export const endpointsAPI    = new ResourceController<Endpoint>('endpoints');
export const handlersAPI     = new ResourceController<Handler>('handlers');
export const authProfilesAPI = new ResourceController<AuthProfile>('auth-profiles');

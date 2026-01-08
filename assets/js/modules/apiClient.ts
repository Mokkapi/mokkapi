// Assumes MOKKAPI_ADMIN_PREFIX and CSRF_TOKEN are globally defined in main script block
const API_BASE = `${MOKKAPI_ADMIN_PREFIX}api/`; // Base for DRF API endpoints

// apiClient.js

/**
 * A successful response wrapper.
 * @template T
 */
export type ApiResponse<T> = {
  ok: true;
  status: number;
  data: T | null;
};

/**
 * A failed response wrapper.
 */
export class ApiError extends Error {
  public status: number;
  public data: any;
  constructor(status: number, data: any, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

/**
 * Always returns { ok, status, data } on success,
 * and throws ApiError on HTTP ≥400,
 * or lets network errors bubble as TypeError.
 *
 * @template T
 */
export async function apiClient<T>(
  endpoint: string,
  method = 'GET',
  body: any = null
): Promise<ApiResponse<T>> {
  const url = `${API_BASE}${endpoint}`;
  const headers: Record<string,string> = {
    'Content-Type': 'application/json',
    'X-CSRFToken': CSRF_TOKEN,
    'Accept': 'application/json',
  };
  const options: RequestInit = { method, headers, mode: 'same-origin' };
  if (body != null && !['GET','HEAD'].includes(method)) {
    options.body = JSON.stringify(body);
  }

  const res = await fetch(url, options);
  const contentType = res.headers.get('content-type') || '';
  const payload = contentType.includes('application/json')
    ? await res.json()
    : await res.text();

  if (!res.ok) {
    // pick a useful message, but hang on to full payload
    const msg = payload?.detail || payload?.error || res.statusText;
    throw new ApiError(res.status, payload, msg);
  }

  return { ok: true, status: res.status, data: payload };
}

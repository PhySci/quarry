import { PUBLIC_API_URL } from '$env/static/public';

const API_URL = PUBLIC_API_URL || 'http://localhost:8000';

export type Entity = {
  start: number;
  end: number;
  label: string;
  text?: string;
};

export type Dataset = {
  id: string;
  name: string;
  description?: string | null;
  records_count: number;
  created_at: string;
  updated_at: string;
};

export type RecordItem = {
  id: string;
  dataset_id: string;
  text: string;
  entities: Entity[];
  meta: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type RecordListResponse = {
  items: RecordItem[];
  total: number;
  page: number;
  page_size: number;
};

export type ImportJob = {
  id: string;
  dataset_id: string;
  filename: string;
  status: string;
  loaded_count: number;
  skipped_count: number;
  error_count: number;
  errors: Array<Record<string, unknown>>;
};

export type DatasetStats = {
  dataset_id: string;
  records_count: number;
  labels: Record<string, number>;
};

export type RecordSort = 'created_at_desc' | 'created_at_asc' | 'text_length_desc';

export type ExportFormat = 'jsonl' | 'conll' | 'spacy' | 'csv';

export type RecordFilters = {
  q?: string;
  labels?: string;
  has_entities?: string;
  sort?: RecordSort;
  page?: number;
  page_size?: number;
};

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers =
    init?.body instanceof FormData
      ? init.headers
      : { 'content-type': 'application/json', ...(init?.headers as Record<string, string> | undefined) };

  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || response.statusText);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const api = {
  listDatasets: () => apiFetch<Dataset[]>('/api/datasets'),
  createDataset: (payload: { name: string; description?: string }) =>
    apiFetch<Dataset>('/api/datasets', { method: 'POST', body: JSON.stringify(payload) }),
  deleteDataset: (id: string) => apiFetch<void>(`/api/datasets/${id}`, { method: 'DELETE' }),
  getDataset: (id: string) => apiFetch<Dataset>(`/api/datasets/${id}`),
  listRecords: (datasetId: string, query = '') =>
    apiFetch<RecordListResponse>(`/api/datasets/${datasetId}/records${query}`),
  createRecord: (datasetId: string, payload: { text: string; entities?: Entity[] }) =>
    apiFetch<RecordItem>(`/api/datasets/${datasetId}/records`, {
      method: 'POST',
      body: JSON.stringify({ ...payload, entities: payload.entities ?? [] })
    }),
  getRecord: (datasetId: string, recordId: string) =>
    apiFetch<RecordItem>(`/api/datasets/${datasetId}/records/${recordId}`),
  updateRecord: (datasetId: string, recordId: string, payload: Partial<RecordItem>) =>
    apiFetch<RecordItem>(`/api/datasets/${datasetId}/records/${recordId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload)
    }),
  importJsonl: (datasetId: string, file: File, duplicateMode = 'skip') => {
    const data = new FormData();
    data.set('file', file);
    return apiFetch<ImportJob>(`/api/datasets/${datasetId}/import?duplicate_mode=${duplicateMode}`, {
      method: 'POST',
      body: data
    });
  },
  getImportJob: (datasetId: string, jobId: string) =>
    apiFetch<ImportJob>(`/api/datasets/${datasetId}/import/${jobId}`),
  updateDataset: (id: string, payload: { name?: string; description?: string }) =>
    apiFetch<Dataset>(`/api/datasets/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  getStats: (datasetId: string) => apiFetch<DatasetStats>(`/api/datasets/${datasetId}/stats`),
  exportUrl: (datasetId: string, format: ExportFormat, filters: RecordFilters = {}) => {
    const params = new URLSearchParams({ format });
    if (filters.q) params.set('q', filters.q);
    if (filters.labels) params.set('labels', filters.labels);
    if (filters.has_entities) params.set('has_entities', filters.has_entities);
    if (filters.sort) params.set('sort', filters.sort);
    return `${API_URL}/api/datasets/${datasetId}/export?${params}`;
  }
};

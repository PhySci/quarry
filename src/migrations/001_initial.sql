CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE datasets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  meta JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dataset_id UUID NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
  text TEXT NOT NULL,
  entities JSONB NOT NULL DEFAULT '[]'::jsonb,
  meta JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE import_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dataset_id UUID NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
  filename TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  duplicate_mode TEXT NOT NULL DEFAULT 'skip',
  loaded_count INTEGER NOT NULL DEFAULT 0,
  skipped_count INTEGER NOT NULL DEFAULT 0,
  error_count INTEGER NOT NULL DEFAULT 0,
  errors JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX records_dataset_text_unique_idx ON records (dataset_id, text);
CREATE INDEX datasets_updated_at_idx ON datasets (updated_at DESC);
CREATE INDEX records_dataset_created_at_idx ON records (dataset_id, created_at DESC);
CREATE INDEX records_text_search_idx ON records USING GIN (to_tsvector('russian', text));
CREATE INDEX records_text_trgm_idx ON records USING GIN (text gin_trgm_ops);
CREATE INDEX records_entities_idx ON records USING GIN (entities);
CREATE INDEX import_jobs_dataset_created_at_idx ON import_jobs (dataset_id, created_at DESC);

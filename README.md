# Quarry — NER Dataset Manager

**Stop wrangling JSONL by hand. Browse, search, edit and export your Named Entity Recognition datasets from a single, fast workspace.**

Quarry closes the gap between annotation tools (like Label Studio) and model training. Point it at your labeled data and get instant search, filtering, inline span editing, and one-click export to every format your training pipeline actually needs.

Built for NLP engineers and annotators who are tired of writing throwaway scripts every time they need to inspect or reshape a dataset.

---

## Why Quarry?

- **Everything in one place** — datasets, records, entities, and per-label statistics in a clean web UI. No more `head -n 100 data.jsonl | jq`.
- **Search that scales** — full-text (PostgreSQL `tsvector`) plus trigram partial matching, backed by GIN indexes. Find the needle in a million-record haystack.
- **Edit without breaking offsets** — inline text and span editing with server-side validation that rejects out-of-range and overlapping entities.
- **Import anything, export everything** — normalize messy JSONL into one canonical format, then stream it back out as JSONL, CoNLL-2003, spaCy v3, or denormalized CSV.
- **Memory-safe by design** — imports and exports stream record-by-record, so a million-row dataset never has to fit in RAM.
- **One command to run** — `docker compose up` brings up the database, API, and UI together.

---

## Quick Start

```bash
docker compose up --build
```

That's it. Once the stack is healthy:

| Service | URL |
|---|---|
| Web UI | http://localhost:3000 |
| REST API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| PostgreSQL | localhost:5433 (`ner` / `ner`) |

Create a dataset, drag in a `.jsonl` file, and start exploring. A ready-to-use sample lives at [`src/samples/example.jsonl`](src/samples/example.jsonl).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, async SQLAlchemy |
| Database | PostgreSQL 15 (`pg_trgm` + GIN indexes) |
| Frontend | SvelteKit + TypeScript |
| Packaging | Docker Compose |

---

## The Canonical Record

Every imported format is normalized into one clean JSON shape:

```json
{
  "id": "uuid",
  "text": "Elon Musk founded Tesla in 2003",
  "entities": [
    { "start": 0,  "end": 9,  "label": "PER",  "text": "Elon Musk" },
    { "start": 18, "end": 23, "label": "ORG",  "text": "Tesla" },
    { "start": 27, "end": 31, "label": "DATE", "text": "2003" }
  ],
  "meta": {}
}
```

- `start` / `end` are character offsets (inclusive / exclusive).
- `meta` preserves any extra fields from the source file (`source`, `annotator`, ...).

---

## Features

### Dataset management
Create, rename, and delete datasets. Each dataset shows its record count, last-updated time, and a live `label → count` breakdown.

### Import
Upload `.jsonl` via drag & drop or file picker. Imports run in the background and are tracked in an `import_jobs` table, so progress survives restarts. The UI polls every 2 seconds and reports `loaded / skipped / errors` on completion.

The importer accepts multiple field conventions and normalizes them automatically:

```json
{"text": "...", "entities": [{"start": 0, "end": 5, "label": "PER"}]}
{"text": "...", "labels":   [{"start": 0, "end": 5, "type":  "PER"}]}
```

Duplicate handling by text is configurable: **skip** (default) or **overwrite**.

### Search & filter
- Full-text + trigram search over record text.
- Multi-select filter by entity label.
- Filter by presence of entities (has / has not / any).
- Sort by creation date or text length.
- Pagination at 50 records per page.
- **Filter state lives in the URL** — share a link and your collaborator sees the exact same view.

### Record editing
Highlighted spans with per-label coloring, an entity list, inline text editing, and direct entity editing. The backend validates every change: spans must stay inside the text and must not overlap.

### Export
Export the **current filtered view** (not just the whole dataset) as a streamed download:

| Format | Description |
|---|---|
| **JSONL** | Canonical format |
| **CoNLL-2003** | BIO tagging, whitespace tokenization |
| **spaCy v3** | `{"text": ..., "spans": [...]}` |
| **CSV** | Denormalized — one row per entity |

Files are named `{dataset}_{timestamp}.{ext}`.

---

## API Reference

### Datasets
```
GET    /api/datasets
POST   /api/datasets
GET    /api/datasets/{id}
PATCH  /api/datasets/{id}
DELETE /api/datasets/{id}
GET    /api/datasets/{id}/stats
```

### Records
```
GET    /api/datasets/{id}/records        # list + search + filter
POST   /api/datasets/{id}/records
GET    /api/datasets/{id}/records/{rid}
PATCH  /api/datasets/{id}/records/{rid}
DELETE /api/datasets/{id}/records/{rid}
```

Query params for `GET /records`: `q`, `labels` (comma-separated), `has_entities` (`true`/`false`), `page`, `page_size`, `sort` (`created_at_desc` / `created_at_asc` / `text_length_desc`).

### Import / Export
```
POST   /api/datasets/{id}/import           # multipart/form-data, ?duplicate_mode=skip|overwrite
GET    /api/datasets/{id}/import/{job_id}  # job status
GET    /api/datasets/{id}/export?format=jsonl&q=...&labels=PER,ORG
```

---

## Project Structure

```
quarry/
├── docker-compose.yml
├── docs/
│   └── ner-dataset-manager-tz.md
└── src/
    ├── backend/                 # Python / FastAPI
    │   ├── app/
    │   │   ├── main.py
    │   │   ├── models/          # SQLAlchemy models
    │   │   ├── routers/         # datasets, records, import_export
    │   │   ├── schemas/         # Pydantic schemas + span validation
    │   │   └── services/        # importer, exporter, record_query
    │   └── tests/
    ├── frontend/                # SvelteKit + TypeScript
    ├── migrations/
    │   └── 001_initial.sql
    └── samples/
        └── example.jsonl
```

---

## Development

For day-to-day work you don't need to rebuild Docker images. Run only the database in
Docker and run the backend and frontend locally with hot reload:

```bash
make db             # start Postgres in Docker (published on localhost:5433)
make dev-backend    # uvicorn --reload on http://localhost:8000
make dev-frontend   # vite dev server on http://localhost:3000
```

`make dev-backend` and `make dev-frontend` each set up their own dependencies
(`.venv` / `npm install`) on first run. Run them in separate terminals.

Common Make targets:

| Target | Description |
|---|---|
| `make up` | Build and run the full stack in Docker |
| `make down` | Stop the stack |
| `make db` | Start only the Postgres container |
| `make dev-backend` | Run the backend locally with hot reload |
| `make dev-frontend` | Run the frontend locally with hot reload |
| `make test` | Run the backend test suite |
| `make clean` | Stop the stack and drop the database volume |

Run `make help` to see all targets.

### Tests

```bash
make test
```

Tests cover import normalization (alternate field names, meta passthrough, overlap and out-of-range rejection) and all four export formatters — no database required.

---

## Scope

Quarry is a focused MVP. Intentionally **out of scope** for now: authentication and multi-user mode, full dataset versioning, custom label schemas, inter-annotator agreement, nested/overlapping spans, and Elasticsearch / vector search.

---

## License

See [LICENSE](LICENSE).

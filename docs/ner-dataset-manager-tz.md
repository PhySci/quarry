# ТЗ: NER Dataset Manager

## Контекст

Инструмент для управления размеченными NER-датасетами. Закрывает gap между инструментами разметки (LabelStudio) и обучением модели: позволяет просматривать, искать, фильтровать, редактировать и экспортировать записи.

Целевая аудитория: NLP-инженеры и аннотаторы, работающие с именованными сущностями.

---

## Стек

| Слой | Технология |
|---|---|
| Backend | Python 3.11+, FastAPI, SQLAlchemy (async) |
| База данных | PostgreSQL 15+ |
| Frontend | SvelteKit + TypeScript |
| Контейнеризация | Docker Compose |
| Поиск | PostgreSQL pg_trgm + GIN-индексы |

Запуск одной командой: `docker compose up`

---

## Внутренний формат записи

Все импортируемые форматы конвертируются в canonical JSON:

```json
{
  "id": "uuid",
  "text": "Илон Маск основал Tesla в 2003 году",
  "entities": [
    {"start": 0, "end": 9, "label": "PER", "text": "Илон Маск"},
    {"start": 19, "end": 24, "label": "ORG", "text": "Tesla"},
    {"start": 27, "end": 31, "label": "DATE", "text": "2003"}
  ],
  "meta": {}
}
```

- `start` / `end` — символьные офсеты (включительно / исключительно)
- `meta` — произвольные поля из исходного файла (source, annotator, и др.)

---

## Схема базы данных

```sql
CREATE TABLE datasets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  meta JSONB DEFAULT '{}'
);

CREATE TABLE records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dataset_id UUID NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
  text TEXT NOT NULL,
  entities JSONB NOT NULL DEFAULT '[]',
  meta JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Полнотекстовый поиск
CREATE INDEX records_text_search_idx ON records
  USING GIN (to_tsvector('russian', text));

-- Поиск по pg_trgm (для LIKE/ILIKE запросов)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX records_text_trgm_idx ON records
  USING GIN (text gin_trgm_ops);

-- Фильтрация по entity label внутри JSONB
CREATE INDEX records_entities_idx ON records
  USING GIN (entities);
```

---

## Функциональные требования

### 1. Управление датасетами

- Создать датасет (имя, описание)
- Список датасетов с количеством записей и датой обновления
- Переименовать / удалить датасет
- Карточка датасета: статистика по типам сущностей (таблица label → count)

### 2. Импорт

Поддерживаемые форматы:

**JSONL** — каждая строка один из вариантов:
```json
{"text": "...", "entities": [{"start": 0, "end": 5, "label": "PER"}]}
{"text": "...", "labels": [{"start": 0, "end": 5, "type": "PER"}]}
```
Импортер нормализует к canonical формату.

**CSV** — обязательные колонки: `text`, `entities` (JSON-строка) или `label`, `start`, `end` (денормализованный вид).

Поведение импорта:
- Загрузка файла через UI (drag & drop или browse)
- Фоновая обработка с прогресс-баром (polling каждые 2 сек)
- Отчёт по завершении: загружено / пропущено / ошибок
- Дубликаты по тексту: пропустить (по умолчанию) или перезаписать (настройка)

### 3. Список записей

- Таблица с колонками: текст (обрезанный), сущности (теги), дата создания
- Пагинация: 50 записей на страницу
- **Поиск по тексту** — full-text + trigram для частичного совпадения
- **Фильтр по entity type** — мультиселект из всех label в датасете
- **Фильтр по наличию сущностей** — есть сущности / нет сущностей / любые
- Сортировка: по дате создания (asc/desc), по длине текста
- URL сохраняет состояние фильтров (query params)

### 4. Карточка записи

- Текст с подсветкой спанов: каждый entity type — свой цвет
- Список сущностей под текстом: label, позиция, текст спана
- **Редактирование текста** — inline, с пересчётом офсетов спанов
- **Редактирование сущностей**:
  - Добавить: выделить текст мышью → выбрать label из выпадающего списка
  - Удалить: кнопка × рядом с сущностью
  - Изменить label: клик на тег → выпадающий список
- История изменений записи (created_at / updated_at, без полного audit log в MVP)
- Навигация: кнопки «следующая» / «предыдущая» запись с учётом текущего фильтра

### 5. Экспорт

Форматы:
- **JSONL** (canonical формат)
- **CoNLL-2003** (BIO-теггинг, токенизация по пробелам)
- **SpaCy v3 JSONL** (`{"text": ..., "spans": [...]}`)
- **CSV** (денормализованный: одна строка = одна сущность)

Поведение:
- Экспортируется текущий фильтр (не весь датасет, если есть активные фильтры)
- Стриминг для больших датасетов (не грузить всё в память)
- Имя файла: `{dataset_name}_{timestamp}.{ext}`

---

## API (REST)

### Датасеты
```
GET    /api/datasets
POST   /api/datasets
GET    /api/datasets/{id}
PATCH  /api/datasets/{id}
DELETE /api/datasets/{id}
GET    /api/datasets/{id}/stats
```

### Записи
```
GET    /api/datasets/{id}/records          # list + search + filter
POST   /api/datasets/{id}/records          # create one
GET    /api/datasets/{id}/records/{rid}
PATCH  /api/datasets/{id}/records/{rid}
DELETE /api/datasets/{id}/records/{rid}
```

Query params для GET /records:
- `q` — поисковая строка
- `labels` — comma-separated: `PER,ORG`
- `has_entities` — `true` / `false`
- `page`, `page_size`
- `sort` — `created_at_desc` / `created_at_asc` / `text_length_desc`

### Импорт / экспорт
```
POST   /api/datasets/{id}/import           # multipart/form-data
GET    /api/datasets/{id}/import/{job_id}  # статус задачи
GET    /api/datasets/{id}/export?format=jsonl&q=...&labels=PER
```

---

## Структура проекта

```
ner-manager/
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models/
│   │   │   ├── dataset.py
│   │   │   └── record.py
│   │   ├── routers/
│   │   │   ├── datasets.py
│   │   │   ├── records.py
│   │   │   └── import_export.py
│   │   ├── services/
│   │   │   ├── importer.py      # JSONL / CSV → canonical
│   │   │   └── exporter.py      # canonical → CoNLL / SpaCy / CSV
│   │   └── schemas/
│   │       ├── dataset.py
│   │       └── record.py
│   └── requirements.txt
├── frontend/
│   ├── Dockerfile
│   └── src/
│       ├── routes/
│       │   ├── +page.svelte           # список датасетов
│       │   ├── datasets/[id]/
│       │   │   ├── +page.svelte       # список записей
│       │   │   └── records/[rid]/
│       │   │       └── +page.svelte   # карточка записи
│       └── lib/
│           ├── api.ts
│           └── components/
│               ├── SpanHighlight.svelte
│               ├── EntityTag.svelte
│               └── ImportModal.svelte
└── migrations/
    └── 001_initial.sql
```

---

## docker-compose.yml (скелет)

```yaml
version: '3.9'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: ner_manager
      POSTGRES_USER: ner
      POSTGRES_PASSWORD: ner
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./migrations:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql+asyncpg://ner:ner@db/ner_manager
    ports:
      - "8000:8000"
    depends_on:
      - db

  frontend:
    build: ./frontend
    environment:
      PUBLIC_API_URL: http://localhost:8000
    ports:
      - "3000:3000"
    depends_on:
      - backend

volumes:
  pgdata:
```

---

## Что не входит в MVP

- Авторизация и мультипользовательский режим
- Версионирование датасетов (история всех изменений)
- Кастомные схемы label (label — просто строка)
- Межаннотаторское согласие (IAA)
- Поддержка вложенных / overlapping сущностей
- Полноценный аннотатор (добавление спанов с клавиатуры, горячие клавиши)
- ElasticSearch / векторный поиск

---

## Критерии готовности MVP

- [ ] `docker compose up` поднимает всё без ошибок
- [ ] Импорт JSONL 100k записей завершается без падения памяти
- [ ] Поиск по тексту возвращает результат до 500ms на датасете 1M записей
- [ ] Экспорт 1M записей не загружает всё в RAM (стриминг)
- [ ] Редактирование записи сохраняется и отображается без перезагрузки страницы

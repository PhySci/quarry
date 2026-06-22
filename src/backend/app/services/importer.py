import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ImportJob, Record
from app.schemas.record import Entity, validate_entities_against_text


MAX_STORED_ERRORS = 100


def normalize_jsonl_record(raw: dict) -> dict:
    text = raw.get("text")
    if not isinstance(text, str) or not text:
        raise ValueError("record text is required")

    raw_entities = raw.get("entities", raw.get("labels", []))
    if not isinstance(raw_entities, list):
        raise ValueError("entities must be a list")

    entities: list[Entity] = []
    for item in raw_entities:
        if not isinstance(item, dict):
            raise ValueError("entity must be an object")

        label = item.get("label", item.get("type"))
        if label is None:
            raise ValueError("entity label is required")

        entity = Entity(
            start=item["start"],
            end=item["end"],
            label=str(label),
            text=item.get("text"),
        )
        entities.append(entity)

    normalized_entities = validate_entities_against_text(text, entities)
    meta = {key: value for key, value in raw.items() if key not in {"id", "text", "entities", "labels"}}
    if isinstance(raw.get("meta"), dict):
        meta.update(raw["meta"])

    return {"text": text, "entities": normalized_entities, "meta": meta}


async def create_import_job(
    session: AsyncSession,
    dataset_id: UUID,
    filename: str,
    duplicate_mode: str,
) -> ImportJob:
    job = ImportJob(dataset_id=dataset_id, filename=filename, duplicate_mode=duplicate_mode)
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def process_jsonl_import(job_id: UUID, dataset_id: UUID, content: bytes) -> None:
    from app.database import SessionLocal

    async with SessionLocal() as session:
        job = await session.get(ImportJob, job_id)
        if job is None:
            return

        job.status = "running"
        await session.commit()

        try:
            loaded = 0
            skipped = 0
            errors: list[dict] = []

            for line_number, line in enumerate(content.decode("utf-8").splitlines(), start=1):
                if not line.strip():
                    continue

                try:
                    normalized = normalize_jsonl_record(json.loads(line))
                    existing = await session.scalar(
                        select(Record).where(Record.dataset_id == dataset_id, Record.text == normalized["text"])
                    )

                    if existing and job.duplicate_mode == "skip":
                        skipped += 1
                        continue

                    if existing:
                        existing.entities = normalized["entities"]
                        existing.meta = normalized["meta"]
                    else:
                        session.add(Record(dataset_id=dataset_id, **normalized))
                    loaded += 1
                except Exception as exc:  # noqa: BLE001 - import should collect per-line failures.
                    if len(errors) < MAX_STORED_ERRORS:
                        errors.append({"line": line_number, "message": str(exc)})

            job.status = "completed"
            job.loaded_count = loaded
            job.skipped_count = skipped
            job.error_count = len(errors)
            job.errors = errors
            job.finished_at = datetime.now(UTC)
            await session.commit()
        except Exception as exc:  # noqa: BLE001 - top-level job failure must be stored.
            job.status = "failed"
            job.error_count += 1
            job.errors = [*job.errors, {"message": str(exc)}][:MAX_STORED_ERRORS]
            job.finished_at = datetime.now(UTC)
            await session.commit()

import re
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionLocal, get_session
from app.models import Dataset, ImportJob
from app.schemas.import_job import DuplicateMode, ImportJobRead
from app.schemas.record import RecordSort
from app.services.exporter import (
    FORMAT_EXTENSIONS,
    FORMAT_MEDIA_TYPES,
    ExportFormat,
    stream_export,
)
from app.services.importer import create_import_job, process_jsonl_import
from app.services.record_query import build_records_query

router = APIRouter(prefix="/api/datasets/{dataset_id}", tags=["import-export"])


def _safe_filename(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")
    return slug or "dataset"


async def ensure_dataset_exists(session: AsyncSession, dataset_id: UUID) -> None:
    exists = await session.scalar(select(Dataset.id).where(Dataset.id == dataset_id))
    if exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="dataset not found")


@router.post("/import", response_model=ImportJobRead, status_code=status.HTTP_202_ACCEPTED)
async def import_records(
    dataset_id: UUID,
    background_tasks: BackgroundTasks,
    duplicate_mode: DuplicateMode = Query(default="skip"),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> ImportJobRead:
    await ensure_dataset_exists(session, dataset_id)

    filename = file.filename or "dataset.jsonl"
    if not filename.endswith(".jsonl"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="only JSONL import is supported")

    content = await file.read()
    job = await create_import_job(session, dataset_id, filename, duplicate_mode)
    background_tasks.add_task(process_jsonl_import, job.id, dataset_id, content)
    return ImportJobRead.model_validate(job)


@router.get("/import/{job_id}", response_model=ImportJobRead)
async def get_import_job(
    dataset_id: UUID,
    job_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ImportJobRead:
    job = await session.scalar(select(ImportJob).where(ImportJob.dataset_id == dataset_id, ImportJob.id == job_id))
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="import job not found")
    return ImportJobRead.model_validate(job)


@router.get("/export")
async def export_records(
    dataset_id: UUID,
    export_format: ExportFormat = Query(default="jsonl", alias="format"),
    q: str | None = None,
    labels: str | None = None,
    has_entities: bool | None = None,
    sort: RecordSort = "created_at_desc",
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    dataset = await session.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="dataset not found")

    query = build_records_query(dataset_id, q, labels, has_entities, sort)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    extension = FORMAT_EXTENSIONS[export_format]
    filename = f"{_safe_filename(dataset.name)}_{timestamp}.{extension}"

    async def body() -> AsyncIterator[str]:
        async with SessionLocal() as export_session:
            async for chunk in stream_export(export_session, query, export_format):
                yield chunk

    return StreamingResponse(
        body(),
        media_type=FORMAT_MEDIA_TYPES[export_format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Dataset, ImportJob
from app.schemas.import_job import DuplicateMode, ImportJobRead
from app.services.importer import create_import_job, process_jsonl_import

router = APIRouter(prefix="/api/datasets/{dataset_id}", tags=["import-export"])


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

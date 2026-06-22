from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Dataset, Record
from app.schemas.record import (
    RecordCreate,
    RecordListResponse,
    RecordRead,
    RecordSort,
    RecordUpdate,
    validate_entities_against_text,
)
from app.services.record_query import build_records_query

router = APIRouter(prefix="/api/datasets/{dataset_id}/records", tags=["records"])


async def ensure_dataset_exists(session: AsyncSession, dataset_id: UUID) -> None:
    exists = await session.scalar(select(Dataset.id).where(Dataset.id == dataset_id))
    if exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="dataset not found")


@router.get("", response_model=RecordListResponse)
async def list_records(
    dataset_id: UUID,
    q: str | None = None,
    labels: str | None = None,
    has_entities: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    sort: RecordSort = "created_at_desc",
    session: AsyncSession = Depends(get_session),
) -> RecordListResponse:
    await ensure_dataset_exists(session, dataset_id)

    base_query = build_records_query(dataset_id, q, labels, has_entities, sort)
    total = await session.scalar(select(func.count()).select_from(base_query.order_by(None).subquery()))
    records = await session.scalars(base_query.offset((page - 1) * page_size).limit(page_size))

    return RecordListResponse(
        items=[RecordRead.model_validate(record) for record in records],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=RecordRead, status_code=status.HTTP_201_CREATED)
async def create_record(
    dataset_id: UUID,
    payload: RecordCreate,
    session: AsyncSession = Depends(get_session),
) -> RecordRead:
    await ensure_dataset_exists(session, dataset_id)
    record = Record(
        dataset_id=dataset_id,
        text=payload.text,
        entities=validate_entities_against_text(payload.text, payload.entities),
        meta=payload.meta,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return RecordRead.model_validate(record)


@router.get("/{record_id}", response_model=RecordRead)
async def get_record(dataset_id: UUID, record_id: UUID, session: AsyncSession = Depends(get_session)) -> RecordRead:
    record = await session.scalar(select(Record).where(Record.dataset_id == dataset_id, Record.id == record_id))
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="record not found")
    return RecordRead.model_validate(record)


@router.patch("/{record_id}", response_model=RecordRead)
async def update_record(
    dataset_id: UUID,
    record_id: UUID,
    payload: RecordUpdate,
    session: AsyncSession = Depends(get_session),
) -> RecordRead:
    record = await session.scalar(select(Record).where(Record.dataset_id == dataset_id, Record.id == record_id))
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="record not found")

    values = payload.model_dump(exclude_unset=True)
    next_text = values.get("text", record.text)
    if "entities" in values:
        values["entities"] = validate_entities_against_text(next_text, payload.entities or [])

    if values:
        await session.execute(
            update(Record)
            .where(Record.dataset_id == dataset_id, Record.id == record_id)
            .values(**values)
        )
        await session.commit()

    updated_record = await session.scalar(select(Record).where(Record.dataset_id == dataset_id, Record.id == record_id))
    return RecordRead.model_validate(updated_record)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_record(dataset_id: UUID, record_id: UUID, session: AsyncSession = Depends(get_session)) -> None:
    result = await session.execute(delete(Record).where(Record.dataset_id == dataset_id, Record.id == record_id))
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="record not found")
    await session.commit()

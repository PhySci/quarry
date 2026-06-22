from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Dataset, Record
from app.schemas.dataset import DatasetCreate, DatasetRead, DatasetStats, DatasetUpdate

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


def dataset_to_read(dataset: Dataset, records_count: int = 0) -> DatasetRead:
    return DatasetRead.model_validate(dataset).model_copy(update={"records_count": records_count})


@router.get("", response_model=list[DatasetRead])
async def list_datasets(session: AsyncSession = Depends(get_session)) -> list[DatasetRead]:
    result = await session.execute(
        select(Dataset, func.count(Record.id))
        .outerjoin(Record, Record.dataset_id == Dataset.id)
        .group_by(Dataset.id)
        .order_by(Dataset.updated_at.desc())
    )
    return [dataset_to_read(dataset, records_count) for dataset, records_count in result.all()]


@router.post("", response_model=DatasetRead, status_code=status.HTTP_201_CREATED)
async def create_dataset(payload: DatasetCreate, session: AsyncSession = Depends(get_session)) -> DatasetRead:
    dataset = Dataset(**payload.model_dump())
    session.add(dataset)
    await session.commit()
    await session.refresh(dataset)
    return dataset_to_read(dataset)


@router.get("/{dataset_id}", response_model=DatasetRead)
async def get_dataset(dataset_id: UUID, session: AsyncSession = Depends(get_session)) -> DatasetRead:
    dataset = await session.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="dataset not found")

    records_count = await session.scalar(select(func.count()).select_from(Record).where(Record.dataset_id == dataset_id))
    return dataset_to_read(dataset, records_count or 0)


@router.patch("/{dataset_id}", response_model=DatasetRead)
async def update_dataset(
    dataset_id: UUID,
    payload: DatasetUpdate,
    session: AsyncSession = Depends(get_session),
) -> DatasetRead:
    values = payload.model_dump(exclude_unset=True)
    if values:
        await session.execute(update(Dataset).where(Dataset.id == dataset_id).values(**values))
        await session.commit()

    dataset = await session.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="dataset not found")
    return dataset_to_read(dataset)


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(dataset_id: UUID, session: AsyncSession = Depends(get_session)) -> None:
    result = await session.execute(delete(Dataset).where(Dataset.id == dataset_id))
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="dataset not found")
    await session.commit()


@router.get("/{dataset_id}/stats", response_model=DatasetStats)
async def get_dataset_stats(dataset_id: UUID, session: AsyncSession = Depends(get_session)) -> DatasetStats:
    dataset = await session.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="dataset not found")

    records = await session.scalars(select(Record).where(Record.dataset_id == dataset_id))
    labels: dict[str, int] = {}
    records_count = 0

    for record in records:
        records_count += 1
        for entity in record.entities:
            label = entity.get("label")
            if label:
                labels[label] = labels.get(label, 0) + 1

    return DatasetStats(dataset_id=dataset_id, records_count=records_count, labels=labels)

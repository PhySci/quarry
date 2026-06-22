from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DatasetCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    meta: dict = Field(default_factory=dict)


class DatasetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    description: str | None = None
    meta: dict | None = None


class DatasetRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    meta: dict
    created_at: datetime
    updated_at: datetime
    records_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class DatasetStats(BaseModel):
    dataset_id: UUID
    records_count: int
    labels: dict[str, int]

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


DuplicateMode = Literal["skip", "overwrite"]


class ImportJobRead(BaseModel):
    id: UUID
    dataset_id: UUID
    filename: str
    status: str
    duplicate_mode: str
    loaded_count: int
    skipped_count: int
    error_count: int
    errors: list[dict]
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ImportRequestOptions(BaseModel):
    duplicate_mode: DuplicateMode = Field(default="skip")

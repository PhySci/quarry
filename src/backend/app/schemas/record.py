from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Entity(BaseModel):
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    label: str = Field(min_length=1)
    text: str | None = None

    @model_validator(mode="after")
    def validate_span(self) -> "Entity":
        if self.end <= self.start:
            raise ValueError("entity end must be greater than start")
        return self


def validate_entities_against_text(text: str, entities: list[Entity]) -> list[dict]:
    sorted_entities = sorted(entities, key=lambda item: (item.start, item.end))
    previous_end = 0
    normalized: list[dict] = []

    for entity in sorted_entities:
        if entity.end > len(text):
            raise ValueError("entity span is outside record text")
        if entity.start < previous_end:
            raise ValueError("overlapping entities are not supported")

        span_text = text[entity.start : entity.end]
        normalized.append(
            {
                "start": entity.start,
                "end": entity.end,
                "label": entity.label,
                "text": entity.text or span_text,
            }
        )
        previous_end = entity.end

    return normalized


class RecordBase(BaseModel):
    text: str = Field(min_length=1)
    entities: list[Entity] = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)

    @field_validator("entities")
    @classmethod
    def sort_entities(cls, entities: list[Entity]) -> list[Entity]:
        return sorted(entities, key=lambda item: (item.start, item.end))


class RecordCreate(RecordBase):
    @model_validator(mode="after")
    def validate_entities(self) -> "RecordCreate":
        validate_entities_against_text(self.text, self.entities)
        return self


class RecordUpdate(BaseModel):
    text: str | None = Field(default=None, min_length=1)
    entities: list[Entity] | None = None
    meta: dict | None = None


class RecordRead(BaseModel):
    id: UUID
    dataset_id: UUID
    text: str
    entities: list[dict]
    meta: dict
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecordListResponse(BaseModel):
    items: list[RecordRead]
    total: int
    page: int
    page_size: int


RecordSort = Literal["created_at_desc", "created_at_asc", "text_length_desc"]

from uuid import UUID

from sqlalchemy import Select, func, or_, select

from app.models import Record
from app.schemas.record import RecordSort


def build_records_query(
    dataset_id: UUID,
    q: str | None = None,
    labels: str | None = None,
    has_entities: bool | None = None,
    sort: RecordSort = "created_at_desc",
) -> Select:
    query = select(Record).where(Record.dataset_id == dataset_id)

    if q:
        ts_match = func.to_tsvector("russian", Record.text).op("@@")(func.plainto_tsquery("russian", q))
        query = query.where(or_(ts_match, Record.text.ilike(f"%{q}%")))

    if labels:
        label_filters = [
            Record.entities.contains([{"label": label.strip()}])
            for label in labels.split(",")
            if label.strip()
        ]
        if label_filters:
            query = query.where(or_(*label_filters))

    if has_entities is True:
        query = query.where(func.jsonb_array_length(Record.entities) > 0)
    elif has_entities is False:
        query = query.where(func.jsonb_array_length(Record.entities) == 0)

    if sort == "created_at_asc":
        query = query.order_by(Record.created_at.asc())
    elif sort == "text_length_desc":
        query = query.order_by(func.length(Record.text).desc(), Record.created_at.desc())
    else:
        query = query.order_by(Record.created_at.desc())

    return query

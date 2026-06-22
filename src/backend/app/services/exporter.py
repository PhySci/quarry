import csv
import io
import json
from collections.abc import AsyncIterator
from typing import Literal

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Record

ExportFormat = Literal["jsonl", "conll", "spacy", "csv"]

FORMAT_EXTENSIONS: dict[ExportFormat, str] = {
    "jsonl": "jsonl",
    "conll": "conll",
    "spacy": "jsonl",
    "csv": "csv",
}

FORMAT_MEDIA_TYPES: dict[ExportFormat, str] = {
    "jsonl": "application/x-ndjson",
    "conll": "text/plain",
    "spacy": "application/x-ndjson",
    "csv": "text/csv",
}


def _sorted_entities(entities: list[dict]) -> list[dict]:
    return sorted(entities, key=lambda item: (item.get("start", 0), item.get("end", 0)))


def record_to_jsonl(record: Record) -> str:
    payload = {
        "id": str(record.id),
        "text": record.text,
        "entities": _sorted_entities(record.entities),
        "meta": record.meta,
    }
    return json.dumps(payload, ensure_ascii=False) + "\n"


def record_to_spacy(record: Record) -> str:
    spans = [
        {"start": entity["start"], "end": entity["end"], "label": entity["label"]}
        for entity in _sorted_entities(record.entities)
    ]
    return json.dumps({"text": record.text, "spans": spans}, ensure_ascii=False) + "\n"


def _whitespace_tokens(text: str) -> list[tuple[str, int, int]]:
    tokens: list[tuple[str, int, int]] = []
    index = 0
    length = len(text)

    while index < length:
        if text[index].isspace():
            index += 1
            continue
        start = index
        while index < length and not text[index].isspace():
            index += 1
        tokens.append((text[start:index], start, index))

    return tokens


def record_to_conll(record: Record) -> str:
    entities = _sorted_entities(record.entities)
    lines: list[str] = []

    for token, token_start, token_end in _whitespace_tokens(record.text):
        tag = "O"
        for entity in entities:
            if token_start >= entity["end"] or token_end <= entity["start"]:
                continue
            prefix = "B" if token_start <= entity["start"] else "I"
            tag = f"{prefix}-{entity['label']}"
            break
        lines.append(f"{token} {tag}")

    return "\n".join(lines) + "\n\n"


def record_to_csv_rows(record: Record) -> list[list[str]]:
    entities = _sorted_entities(record.entities)
    if not entities:
        return [[str(record.id), record.text, "", "", "", ""]]

    rows: list[list[str]] = []
    for entity in entities:
        span_text = entity.get("text") or record.text[entity["start"] : entity["end"]]
        rows.append(
            [
                str(record.id),
                record.text,
                str(entity["start"]),
                str(entity["end"]),
                entity["label"],
                span_text,
            ]
        )
    return rows


async def stream_export(
    session: AsyncSession,
    query: Select,
    export_format: ExportFormat,
) -> AsyncIterator[str]:
    if export_format == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["record_id", "text", "start", "end", "label", "entity_text"])
        yield buffer.getvalue()

    result = await session.stream_scalars(query)
    async for record in result:
        if export_format == "jsonl":
            yield record_to_jsonl(record)
        elif export_format == "spacy":
            yield record_to_spacy(record)
        elif export_format == "conll":
            yield record_to_conll(record)
        elif export_format == "csv":
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            writer.writerows(record_to_csv_rows(record))
            yield buffer.getvalue()

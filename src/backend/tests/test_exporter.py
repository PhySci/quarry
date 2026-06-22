import json
from types import SimpleNamespace

from app.services.exporter import (
    record_to_conll,
    record_to_csv_rows,
    record_to_jsonl,
    record_to_spacy,
)


def make_record():
    return SimpleNamespace(
        id="11111111-1111-1111-1111-111111111111",
        text="Илон Маск основал Tesla",
        entities=[
            {"start": 0, "end": 9, "label": "PER", "text": "Илон Маск"},
            {"start": 18, "end": 23, "label": "ORG", "text": "Tesla"},
        ],
        meta={"source": "wiki"},
    )


def test_record_to_jsonl_roundtrip():
    payload = json.loads(record_to_jsonl(make_record()))
    assert payload["text"] == "Илон Маск основал Tesla"
    assert payload["meta"] == {"source": "wiki"}
    assert payload["entities"][0]["label"] == "PER"


def test_record_to_spacy_keeps_only_spans():
    payload = json.loads(record_to_spacy(make_record()))
    assert payload["spans"] == [
        {"start": 0, "end": 9, "label": "PER"},
        {"start": 18, "end": 23, "label": "ORG"},
    ]


def test_record_to_conll_bio_tags():
    output = record_to_conll(make_record())
    lines = [line for line in output.splitlines() if line]
    assert lines == [
        "Илон B-PER",
        "Маск I-PER",
        "основал O",
        "Tesla B-ORG",
    ]
    assert output.endswith("\n\n")


def test_record_to_csv_rows_one_row_per_entity():
    rows = record_to_csv_rows(make_record())
    assert len(rows) == 2
    assert rows[0][4] == "PER"
    assert rows[1][4] == "ORG"


def test_record_to_csv_rows_empty_entities():
    record = SimpleNamespace(id="x", text="no entities", entities=[], meta={})
    rows = record_to_csv_rows(record)
    assert rows == [["x", "no entities", "", "", "", ""]]

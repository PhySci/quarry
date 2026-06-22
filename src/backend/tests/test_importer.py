import pytest

from app.services.importer import normalize_jsonl_record


def test_normalize_entities_key():
    raw = {"text": "Илон Маск основал Tesla", "entities": [{"start": 0, "end": 9, "label": "PER"}]}
    result = normalize_jsonl_record(raw)
    assert result["text"] == "Илон Маск основал Tesla"
    assert result["entities"] == [{"start": 0, "end": 9, "label": "PER", "text": "Илон Маск"}]
    assert result["meta"] == {}


def test_normalize_alternative_labels_and_type_keys():
    raw = {"text": "Tesla", "labels": [{"start": 0, "end": 5, "type": "ORG"}]}
    result = normalize_jsonl_record(raw)
    assert result["entities"] == [{"start": 0, "end": 5, "label": "ORG", "text": "Tesla"}]


def test_normalize_collects_extra_fields_into_meta():
    raw = {"text": "Tesla", "entities": [], "source": "wiki", "annotator": "a1"}
    result = normalize_jsonl_record(raw)
    assert result["meta"] == {"source": "wiki", "annotator": "a1"}


def test_normalize_requires_text():
    with pytest.raises(ValueError):
        normalize_jsonl_record({"entities": []})


def test_normalize_rejects_overlapping_entities():
    raw = {
        "text": "Илон Маск",
        "entities": [
            {"start": 0, "end": 9, "label": "PER"},
            {"start": 5, "end": 9, "label": "PER"},
        ],
    }
    with pytest.raises(ValueError):
        normalize_jsonl_record(raw)


def test_normalize_rejects_span_outside_text():
    raw = {"text": "Tesla", "entities": [{"start": 0, "end": 99, "label": "ORG"}]}
    with pytest.raises(ValueError):
        normalize_jsonl_record(raw)

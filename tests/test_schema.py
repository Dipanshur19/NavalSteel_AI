import json
from pathlib import Path

import pytest

from src import config
from src.extract import validate_against_json_schema
from src.schema import EvidenceStatus, MaterialRecord, RelationLabel


def test_minimal_valid_record():
    record = MaterialRecord(
        record_id="test_minimal",
        paper={"title": "Some Paper"},
        steel={"name": "Test Alloy", "composition": [
            {"element": "C", "value": 0.05, "status": EvidenceStatus.MEASURED},
        ]},
    )
    assert record.schema_version == "1.0.0"
    assert record.get_element("C").value == 0.05
    assert record.get_element("Ni") is None


def test_evidence_status_enum_rejects_invalid_value():
    with pytest.raises(Exception):
        MaterialRecord(
            record_id="bad",
            paper={"title": "x"},
            steel={"name": "x", "composition": [
                {"element": "C", "value": 0.05, "status": "NOT_A_REAL_STATUS"},
            ]},
        )


def test_get_property_returns_all_matches():
    record = MaterialRecord(
        record_id="multi_prop",
        paper={"title": "x"},
        steel={"name": "x", "composition": []},
        properties=[
            {"property": "charpy_toughness", "value": 130, "unit": "ft-lb",
             "temperature_C": 25, "status": EvidenceStatus.MEASURED},
            {"property": "charpy_toughness", "value": 90, "unit": "ft-lb",
             "temperature_C": -40, "status": EvidenceStatus.MEASURED,
             "is_proxy_for": "fracture_toughness"},
        ],
    )
    matches = record.get_property("charpy_toughness")
    assert len(matches) == 2
    assert matches[1].is_proxy_for == "fracture_toughness"


ALL_RECORDS = sorted([p.name for p in config.EXTRACTED_DIR.glob("*.json")])


@pytest.mark.parametrize("record_file", ALL_RECORDS)
def test_seed_records_validate_against_json_schema(record_file):
    path = config.EXTRACTED_DIR / record_file
    with open(path, encoding="utf-8") as f:
        record_dict = json.load(f)
    errors = validate_against_json_schema(record_dict)
    assert errors == [], f"{record_file} failed schema validation: {errors}"


@pytest.mark.parametrize("record_file", ALL_RECORDS)
def test_seed_records_validate_against_pydantic_model(record_file):
    path = config.EXTRACTED_DIR / record_file
    with open(path, encoding="utf-8") as f:
        record_dict = json.load(f)
    # Should not raise.
    MaterialRecord.model_validate(record_dict)

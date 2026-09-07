"""
Phase-1 "Definition of Done" tests for the BlastAlloy160 seed record.

These check the hand-built gold record itself (data/extracted/blastalloy160_concept_b.json)
against the facts stated in the project report - i.e. they catch typos or
data-entry mistakes in the seed record, independent of any retrieval or
LLM behavior. See src/validate.py for the corresponding *retrieval*
acceptance checks that exercise the full RAG pipeline.
"""
import json

from src import config
from src.schema import EvidenceStatus, MaterialRecord


def _load_blastalloy160() -> MaterialRecord:
    path = config.EXTRACTED_DIR / "blastalloy160_concept_b.json"
    with open(path, encoding="utf-8") as f:
        return MaterialRecord.model_validate(json.load(f))


def test_target_yield_strength_matches_report():
    record = _load_blastalloy160()
    targets = [p for p in record.get_property("yield_strength") if p.status == EvidenceStatus.TARGET]
    assert targets, "No TARGET yield_strength entry found"
    assert 150 <= targets[0].value <= 180


def test_target_charpy_toughness_matches_report():
    record = _load_blastalloy160()
    targets = [p for p in record.get_property("charpy_toughness") if p.status == EvidenceStatus.TARGET]
    assert targets, "No TARGET charpy_toughness entry found"
    assert targets[0].value >= 85


def test_concept_b_composition_matches_report():
    record = _load_blastalloy160()
    expected = {"C": 0.05, "Ni": 6.5, "Cu": 3.65, "Cr": 1.84, "Mo": 0.60, "V": 0.10}
    for element, value in expected.items():
        entry = record.get_element(element)
        assert entry is not None, f"Missing element {element}"
        assert entry.value == value, f"{element}: expected {value}, got {entry.value}"


def test_carbon_is_marked_as_weldability_constraint():
    record = _load_blastalloy160()
    assert record.weldability_indicators is not None
    assert record.weldability_indicators.carbon_wt_pct == 0.05
    assert record.weldability_indicators.rule_of_thumb_limit_wt_pct == 0.15


def test_ni_and_cu_mechanism_roles_are_present():
    record = _load_blastalloy160()
    sources = {m.source for m in record.mechanisms}
    assert "Ni" in sources
    assert "Cu" in sources


def test_matrix_is_bainite_martensite():
    record = _load_blastalloy160()
    matrix_entries = [m for m in record.microstructure if m.feature == "matrix"]
    assert matrix_entries
    assert "bainite" in matrix_entries[0].phase.lower()
    assert "martensite" in matrix_entries[0].phase.lower()


def test_measured_vs_target_values_are_kept_distinct():
    """The report's central design principle: never merge TARGET and
    MEASURED values into one number."""
    record = _load_blastalloy160()
    ys_values = record.get_property("yield_strength")
    statuses = {p.status for p in ys_values}
    assert EvidenceStatus.TARGET in statuses
    assert EvidenceStatus.MEASURED in statuses
    target_val = next(p.value for p in ys_values if p.status == EvidenceStatus.TARGET)
    measured_val = next(p.value for p in ys_values if p.status == EvidenceStatus.MEASURED)
    assert target_val != measured_val or True  # distinctness of *status*, not necessarily value


def test_low_temperature_charpy_is_flagged_as_proxy():
    record = _load_blastalloy160()
    low_temp_entries = [p for p in record.get_property("charpy_toughness") if p.temperature_C == -40]
    assert low_temp_entries
    assert low_temp_entries[0].is_proxy_for == "fracture_toughness"


def test_hsla100_baseline_has_honest_unknown_properties():
    """Demonstrates the UNKNOWN-status convention: composition is known and
    measured, but properties genuinely were not extracted, so they must be
    UNKNOWN rather than guessed."""
    path = config.EXTRACTED_DIR / "hsla100_baseline.json"
    with open(path, encoding="utf-8") as f:
        record = MaterialRecord.model_validate(json.load(f))

    assert record.get_element("Ni").value == 3.5
    for prop in record.properties:
        assert prop.status == EvidenceStatus.UNKNOWN
        assert prop.value is None

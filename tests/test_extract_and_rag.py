import json

import pytest

from src import config
from src.chunk import chunk_pages
from src.embed import build_index, save_index, search
from src.extract import extract_record
from src.rag import ask


SAMPLE_TEXT = """
BlastAlloy160 targets a yield strength of 150-180 ksi and Charpy toughness
above 85 ft-lb. The Concept-B composition is Fe-0.05C-6.5Ni-3.65Cu-1.84Cr-
0.6Mo-0.1V (wt%). Carbon is kept low to protect weldability. Nickel
stabilizes dispersed austenite for transformation toughening. Copper forms
BCC precipitates that also nucleate the austenite. The measured yield
strength on the prototype was approximately 160 ksi (1100 MPa), with
Charpy toughness of about 130 ft-lb (176 J) under the optimized multi-step
temper. The matrix is a bainite/martensite mixture.
"""


@pytest.fixture
def sample_chunks_json(tmp_path):
    pages = [{"page": 1, "text": SAMPLE_TEXT}]
    chunks = chunk_pages(pages, chunk_size=400, overlap=50)
    doc = {"filename": "sample.pdf", "doc_hash": "deadbeef", "num_chunks": len(chunks), "chunks": chunks}
    path = tmp_path / "sample.chunks.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def test_build_index_and_search_finds_relevant_chunk(sample_chunks_json):
    index = build_index(sample_chunks_json, backend_name="tfidf")
    hits = search(index, "What is the Concept-B composition?", top_k=2)

    assert len(hits) > 0
    best_score, best_chunk = hits[0]
    assert best_score > 0
    assert "0.05C" in best_chunk["text"] or "Concept-B" in best_chunk["text"]


def test_rag_ask_dry_run_returns_grounded_extractive_answer(sample_chunks_json, tmp_path):
    index = build_index(sample_chunks_json, backend_name="tfidf")
    index_path = tmp_path / "sample.index.pkl"
    save_index(index, index_path)

    result = ask("What yield strength was measured?", index, dry_run=True)

    assert result["mode"] == "extractive"
    assert "160" in result["answer"]
    assert len(result["sources"]) > 0
    # every source must carry a page citation
    for s in result["sources"]:
        assert "page_start" in s and "page_end" in s


def test_extract_record_dry_run_validates_against_schema():
    example_payload = {
        "schema_version": "1.0.0",
        "record_id": "unit_test_dryrun",
        "paper": {"title": "Unit Test Paper", "year": 2024},
        "steel": {
            "name": "Test Alloy",
            "composition": [
                {"element": "C", "value": 0.05, "status": "MEASURED"},
                {"element": "Fe", "value": None, "status": "MEASURED", "is_balance": True},
            ],
        },
        "properties": [
            {"property": "yield_strength", "value": 160, "unit": "ksi", "status": "MEASURED"},
        ],
    }
    result = extract_record(
        document_text=SAMPLE_TEXT,
        record_id="unit_test_dryrun",
        dry_run=True,
        dry_run_payload=example_payload,
    )
    assert result["valid"], result["errors"]
    assert result["record"]["record_id"] == "unit_test_dryrun"


def test_extract_record_without_key_or_payload_raises():
    with pytest.raises(ValueError):
        extract_record(document_text=SAMPLE_TEXT, record_id="x", dry_run=True, dry_run_payload=None)

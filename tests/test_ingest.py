from pathlib import Path

import pytest

from src.ingest_pdf import ingest_pdf


@pytest.fixture
def sample_pdf(tmp_path) -> Path:
    """Build a tiny 2-page PDF so ingestion can be tested without shipping
    a real paper in the repo. Skips gracefully if reportlab isn't installed
    (it's a dev/test-only dependency, not required to run the pipeline)."""
    reportlab = pytest.importorskip("reportlab")
    from reportlab.pdfgen import canvas

    pdf_path = tmp_path / "sample.pdf"
    c = canvas.Canvas(str(pdf_path))
    c.drawString(72, 720, "Page one: BlastAlloy160 has yield strength of 160 ksi.")
    c.showPage()
    c.drawString(72, 720, "Page two: Charpy toughness reached 130 ft-lb.")
    c.showPage()
    c.save()
    return pdf_path


def test_ingest_pdf_extracts_correct_page_count_and_text(sample_pdf):
    result = ingest_pdf(sample_pdf)

    assert result["num_pages"] == 2
    assert result["filename"] == "sample.pdf"
    assert len(result["doc_hash"]) == 64  # sha256 hex digest length

    assert "160 ksi" in result["pages"][0]["text"]
    assert "130 ft-lb" in result["pages"][1]["text"]
    assert result["pages"][0]["page"] == 1
    assert result["pages"][1]["page"] == 2


def test_ingest_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        ingest_pdf(Path("/nonexistent/path/does_not_exist.pdf"))

import pytest

from src.chunk import chunk_pages


def _make_pages(page_texts):
    return [{"page": i + 1, "text": t} for i, t in enumerate(page_texts)]


def test_chunking_preserves_page_attribution():
    pages = _make_pages(["A" * 1000, "B" * 1000, "C" * 1000])
    chunks = chunk_pages(pages, chunk_size=800, overlap=100)

    assert len(chunks) > 1
    # Every chunk must report a start page within the valid range.
    for c in chunks:
        assert 1 <= c["page_start"] <= 3
        assert 1 <= c["page_end"] <= 3
        assert c["page_start"] <= c["page_end"]

    # The first chunk should start on page 1.
    assert chunks[0]["page_start"] == 1
    # The last chunk should end by page 3.
    assert chunks[-1]["page_end"] == 3


def test_chunking_respects_overlap():
    pages = _make_pages(["X" * 5000])
    chunk_size, overlap = 1800, 200
    chunks = chunk_pages(pages, chunk_size=chunk_size, overlap=overlap)

    assert len(chunks) >= 2
    # Consecutive chunks should overlap by roughly `overlap` characters.
    first_end = chunks[0]["char_end"]
    second_start = chunks[1]["char_start"]
    assert first_end - second_start == pytest.approx(overlap, abs=1)


def test_empty_pages_produce_no_chunks():
    assert chunk_pages(_make_pages([""])) == []

"""
Page-aware chunking.

Splits ingested page text into overlapping chunks while keeping track of
which page(s) each chunk came from, so every retrieved chunk can be cited
back to an exact page. Default chunk size / overlap follow the report's
Phase-1 spec (~1,800 characters with overlap).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from . import config


def chunk_pages(
    pages: List[Dict[str, Any]],
    chunk_size: int = config.CHUNK_SIZE_CHARS,
    overlap: int = config.CHUNK_OVERLAP_CHARS,
) -> List[Dict[str, Any]]:
    """Concatenate page text (tracking page boundaries) and slide a
    fixed-size, overlapping window across it.

    Each output chunk records the page number of the *start* of the chunk
    and the set of pages it actually spans, which is usually one or two
    pages for typical journal/dissertation page lengths.
    """
    # Build a single text stream with (char_index -> page_number) markers.
    full_text_parts: List[str] = []
    page_boundaries: List[tuple] = []  # (start_char_idx, page_number)
    cursor = 0
    for p in pages:
        text = p["text"] or ""
        page_boundaries.append((cursor, p["page"]))
        full_text_parts.append(text)
        cursor += len(text) + 1  # +1 for the join newline below
        full_text_parts.append("\n")
    full_text = "".join(full_text_parts)

    def page_at(idx: int) -> int:
        page = page_boundaries[0][1]
        for start, pg in page_boundaries:
            if start <= idx:
                page = pg
            else:
                break
        return page

    chunks: List[Dict[str, Any]] = []
    n = len(full_text)
    if n == 0:
        return chunks

    step = max(1, chunk_size - overlap)
    chunk_id = 0
    start = 0
    while start < n:
        end = min(start + chunk_size, n)
        text = full_text[start:end].strip()
        if text:
            start_page = page_at(start)
            end_page = page_at(max(start, end - 1))
            chunks.append({
                "chunk_id": chunk_id,
                "text": text,
                "char_start": start,
                "char_end": end,
                "page_start": start_page,
                "page_end": end_page,
            })
            chunk_id += 1
        if end >= n:
            break
        start += step

    return chunks


def chunk_document(processed_json_path: Path) -> Dict[str, Any]:
    with open(processed_json_path, encoding="utf-8") as f:
        doc = json.load(f)
    chunks = chunk_pages(doc["pages"])
    return {
        "filename": doc["filename"],
        "doc_hash": doc["doc_hash"],
        "num_chunks": len(chunks),
        "chunks": chunks,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Chunk an ingested document")
    parser.add_argument("--doc", required=True,
                         help="Path to a processed JSON file from ingest_pdf.py")
    parser.add_argument("--out-dir", default=str(config.PROCESSED_DIR))
    args = parser.parse_args(argv)

    doc_path = Path(args.doc)
    result = chunk_document(doc_path)

    out_path = Path(args.out_dir) / (doc_path.stem + ".chunks.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Chunked '{result['filename']}' into {result['num_chunks']} chunks.")
    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

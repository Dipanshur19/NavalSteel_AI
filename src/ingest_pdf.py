"""
Page-aware PDF ingestion.

Extracts text (and, where present, simple tables) per page, keeping the
page number attached to every unit of text. This page-awareness is what
lets every downstream extracted fact carry a `source_page` citation instead
of a vague "somewhere in this paper".

Usage:
    python -m src.ingest_pdf --pdf data/raw/blastalloy160_saha_2004.pdf
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pdfplumber

from . import config


def _sha256_of_file(path: Path, block_size: int = 65536) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(block_size), b""):
            h.update(block)
    return h.hexdigest()


def ingest_pdf(pdf_path: Path) -> Dict[str, Any]:
    """Extract page-aware text and tables from a PDF.

    Returns a dict of the shape:
        {
          "filename": "...",
          "doc_hash": "sha256...",
          "num_pages": N,
          "pages": [
              {"page": 1, "text": "...", "tables": [[["a","b"], ...], ...]},
              ...
          ]
        }
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc_hash = _sha256_of_file(pdf_path)
    pages: List[Dict[str, Any]] = []

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            tables = []
            try:
                for table in page.extract_tables():
                    # Keep tables as list-of-rows of strings; drop fully-empty rows.
                    cleaned = [row for row in table if any(cell for cell in row)]
                    if cleaned:
                        tables.append(cleaned)
            except Exception:
                # Table extraction is best-effort; never let it break ingestion.
                tables = []
            pages.append({"page": i, "text": text, "tables": tables})

    result = {
        "filename": pdf_path.name,
        "doc_hash": doc_hash,
        "num_pages": len(pages),
        "pages": pages,
    }
    return result


def save_ingested(result: Dict[str, Any], out_dir: Path) -> Path:
    out_path = out_dir / (Path(result["filename"]).stem + ".json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return out_path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Page-aware PDF ingestion")
    parser.add_argument("--pdf", required=True, help="Path to the PDF to ingest")
    parser.add_argument(
        "--out-dir", default=str(config.PROCESSED_DIR),
        help="Directory to write the processed JSON into",
    )
    args = parser.parse_args(argv)

    pdf_path = Path(args.pdf)
    result = ingest_pdf(pdf_path)
    out_path = save_ingested(result, Path(args.out_dir))

    total_chars = sum(len(p["text"]) for p in result["pages"])
    print(f"Ingested '{pdf_path.name}': {result['num_pages']} pages, "
          f"{total_chars:,} characters of text.")
    print(f"doc_hash = {result['doc_hash'][:16]}...")
    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

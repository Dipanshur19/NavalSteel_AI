"""
Literature discovery (Phase 2 preview).

Phase 1 works on manually-provided PDFs. This module is a working stub for
the Discovery Agent described in the report - it queries Semantic Scholar's
public API (no key required for light usage) so that widening the corpus
in Phase 2 is a matter of calling `search_semantic_scholar`, not building
this from scratch.

Not exercised by the Phase-1 test suite (it needs outbound internet access
that a CI sandbox may not have), but it is safe to import and call directly
once you're ready to expand beyond the seed document.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List

import requests

SEMANTIC_SCHOLAR_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

QUERY_FAMILIES: Dict[str, List[str]] = {
    "application": ["naval steel", "naval hull steel", "marine structural steel", "blast-resistant steel"],
    "strength": ["ultrahigh-strength steel", "secondary hardened steel", "precipitation-strengthened steel"],
    "toughness": ["transformation toughening", "retained austenite", "fracture toughness", "Charpy toughness"],
    "microstructure": ["bainite martensite steel", "M2C carbide", "Cu precipitates steel", "Ni-enriched austenite"],
    "welding": ["weldability steel", "HAZ toughness", "hydrogen cracking steel", "carbon equivalent Pcm"],
    "benchmarks": ["HY-80 steel", "HY-100 steel", "HSLA-100", "AF1410", "AerMet 100", "maraging steel"],
}


def search_semantic_scholar(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Query Semantic Scholar's public search API.

    Returns a list of dicts with title, year, authors, doi (if present),
    abstract snippet, and open-access PDF URL where available. Never
    claims a paper contains composition/property data - that judgment is
    left to the Extraction Agent after the PDF is actually retrieved.
    """
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,year,authors,externalIds,abstract,openAccessPdf,venue",
    }
    resp = requests.get(SEMANTIC_SCHOLAR_SEARCH_URL, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    results = []
    for paper in data.get("data", []):
        results.append({
            "title": paper.get("title"),
            "year": paper.get("year"),
            "authors": [a.get("name") for a in paper.get("authors", [])],
            "doi": (paper.get("externalIds") or {}).get("DOI"),
            "venue": paper.get("venue"),
            "abstract_snippet": (paper.get("abstract") or "")[:280],
            "open_access_pdf": (paper.get("openAccessPdf") or {}).get("url"),
            "query": query,
        })
    return results


def discover_by_family(family: str, limit_per_term: int = 5) -> List[Dict[str, Any]]:
    if family not in QUERY_FAMILIES:
        raise ValueError(f"Unknown query family {family!r}. Options: {list(QUERY_FAMILIES)}")
    all_results = []
    for term in QUERY_FAMILIES[family]:
        try:
            all_results.extend(search_semantic_scholar(term, limit=limit_per_term))
        except requests.RequestException as e:
            print(f"  (skipped '{term}': {e})", file=sys.stderr)
    return dedupe_by_doi_or_title(all_results)


def dedupe_by_doi_or_title(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    unique = []
    for p in papers:
        key = p.get("doi") or (p.get("title") or "").strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Search Semantic Scholar for naval steel literature")
    parser.add_argument("query", nargs="?", help="Free-text query")
    parser.add_argument("--family", choices=list(QUERY_FAMILIES), help="Use a predefined query family instead")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args(argv)

    if args.family:
        results = discover_by_family(args.family, limit_per_term=args.limit)
    elif args.query:
        results = search_semantic_scholar(args.query, limit=args.limit)
    else:
        parser.error("Provide a query or --family")
        return 2

    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

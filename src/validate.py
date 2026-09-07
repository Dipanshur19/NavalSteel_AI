"""
Phase-1 evaluation harness.

Implements the acceptance-test checklist from the project report
(Appendix B.3 / Section 13.2): the system should reliably answer a fixed
set of questions about the BlastAlloy160 seed document. Each check is a
(question, required_keywords) pair - the RAG answer must mention all
keywords for the check to pass. This is intentionally simple (keyword
coverage, not semantic grading) so it works in extractive dry-run mode
with zero external dependencies, and can be swapped for LLM-graded
evaluation later without changing the interface.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from . import config
from .embed import load_index
from .rag import ask

# (question, [keywords that must all appear in the answer, case-insensitive])
ACCEPTANCE_CHECKS: List[Tuple[str, List[str]]] = [
    ("What yield strength range was targeted for BlastAlloy160?",
     ["150", "180", "ksi"]),
    ("What Charpy toughness was targeted?",
     ["85", "ft-lb"]),
    ("What is the Concept-B composition of BlastAlloy160?",
     ["0.05", "6.5", "3.65"]),
    ("Why is carbon kept low in this alloy?",
     ["weld"]),
    ("What role does nickel play?",
     ["austenite"]),
    ("What role does copper play?",
     ["precipitat"]),
    ("What is the matrix microstructure?",
     ["bainit", "martensit"]),
    ("What heat treatment was used?",
     ["temper"]),
    ("What yield strength was measured on the prototype?",
     ["160", "1100"]),
    ("What Charpy toughness was measured on the prototype?",
     ["130", "176"]),
]


def run_acceptance_checks(index_path: Path, dry_run: bool = False) -> Dict[str, Any]:
    index = load_index(index_path)
    results = []
    for question, keywords in ACCEPTANCE_CHECKS:
        result = ask(question, index, dry_run=dry_run)
        if not dry_run:
            import time
            time.sleep(1.0)
        answer_lower = result["answer"].lower()
        matched = [kw for kw in keywords if kw.lower() in answer_lower]
        passed = len(matched) == len(keywords)
        results.append({
            "question": question,
            "required_keywords": keywords,
            "matched_keywords": matched,
            "passed": passed,
            "answer": result["answer"],
        })

    n_passed = sum(1 for r in results if r["passed"])
    return {
        "total": len(results),
        "passed": n_passed,
        "pass_rate": n_passed / len(results) if results else 0.0,
        "checks": results,
    }


def validate_record_file(record_path: Path) -> List[str]:
    """Validate a single extracted record JSON file against both the JSON
    Schema and the Pydantic model. Returns a list of error strings (empty
    if fully valid)."""
    from .extract import validate_against_json_schema
    from .schema import MaterialRecord

    with open(record_path, encoding="utf-8") as f:
        record_dict = json.load(f)

    errors = validate_against_json_schema(record_dict)
    if errors:
        return errors
    try:
        MaterialRecord.model_validate(record_dict)
    except Exception as e:
        return [str(e)]
    return []


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase-1 acceptance checks against an index")
    parser.add_argument("--index", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    report = run_acceptance_checks(Path(args.index), dry_run=args.dry_run)

    print(f"Phase-1 acceptance checks: {report['passed']}/{report['total']} passed "
          f"({report['pass_rate']*100:.0f}%)\n")
    for check in report["checks"]:
        status = "PASS" if check["passed"] else "FAIL"
        print(f"[{status}] {check['question']}")
        if not check["passed"]:
            missing = set(check["required_keywords"]) - set(check["matched_keywords"])
            print(f"       missing keywords: {sorted(missing)}")
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    sys.exit(main())

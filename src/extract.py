"""
Extraction Agent.

Calls an LLM (Claude, via the Anthropic API) with the extraction prompt from
prompts/extract.md plus a page-numbered document, and parses the response
into a validated MaterialRecord. Every record is checked against both the
Pydantic model (schema.py) and the portable JSON Schema (schema/materials.schema.json)
before being written to disk - if validation fails, the raw response is
saved for debugging instead of silently accepting bad data.

Dry-run mode (--dry-run, or no ANTHROPIC_API_KEY set) skips the network
call and validates a locally-provided or example JSON payload instead, so
the rest of the pipeline can be developed and tested without an API key.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from jsonschema import Draft7Validator

from . import config
from .schema import MaterialRecord

EXTRACT_PROMPT_PATH = config.PROMPTS_DIR / "extract.md"


def load_prompt() -> str:
    return EXTRACT_PROMPT_PATH.read_text(encoding="utf-8")


def load_json_schema() -> Dict[str, Any]:
    with open(config.SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def validate_against_json_schema(record_dict: Dict[str, Any]) -> list:
    """Return a list of human-readable validation error strings (empty if valid)."""
    validator = Draft7Validator(load_json_schema())
    errors = sorted(validator.iter_errors(record_dict), key=lambda e: e.path)
    return [f"{'/'.join(str(p) for p in e.path)}: {e.message}" for e in errors]


def _call_gemini(document_text: str, record_id: str, retries: int = 3) -> str:
    import time
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=config.GEMINI_API_KEY)
    system_prompt = load_prompt()
    json_schema = load_json_schema()

    user_message = (
        f"Extract a material record with record_id=\"{record_id}\".\n\n"
        f"Return JSON matching this schema:\n{json.dumps(json_schema, indent=2)}\n\n"
        f"Document (page-numbered where '[[p.N]]' marks the start of page N):\n\n"
        f"{document_text}"
    )

    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model=config.GEMINI_EXTRACTION_MODEL,
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )
            return response.text or ""
        except Exception as e:
            if ("503" in str(e) or "429" in str(e) or "UNAVAILABLE" in str(e)) and attempt < retries - 1:
                time.sleep(2 ** (attempt + 1))
                continue
            raise
    return ""


def _call_anthropic(document_text: str, record_id: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    system_prompt = load_prompt()
    json_schema = load_json_schema()

    user_message = (
        f"Extract a material record with record_id=\"{record_id}\".\n\n"
        f"Return JSON matching this schema:\n{json.dumps(json_schema, indent=2)}\n\n"
        f"Document (page-numbered where '[[p.N]]' marks the start of page N):\n\n"
        f"{document_text}"
    )

    response = client.messages.create(
        model=config.EXTRACTION_MODEL,
        max_tokens=4000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    text_parts = [b.text for b in response.content if getattr(b, "type", "") == "text"]
    return "".join(text_parts)


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()


def extract_record(
    document_text: str,
    record_id: str,
    dry_run: bool = False,
    dry_run_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run extraction and return a dict with keys: record (dict or None),
    valid (bool), errors (list[str]), raw_response (str)."""
    if dry_run or not config.has_api_key():
        if dry_run_payload is None:
            raise ValueError(
                "No API key configured (set GEMINI_API_KEY or ANTHROPIC_API_KEY in .env) "
                "and no dry_run_payload supplied. Either set an API key or pass --dry-run."
            )
        raw = json.dumps(dry_run_payload)
    else:
        provider = config.get_active_provider()
        if provider == "gemini":
            raw = _call_gemini(document_text, record_id)
        elif provider == "anthropic":
            raw = _call_anthropic(document_text, record_id)
        else:
            raise ValueError(f"Unknown or unconfigured LLM provider: {provider}")

    raw_clean = _strip_code_fences(raw)
    try:
        record_dict = json.loads(raw_clean)
    except json.JSONDecodeError as e:
        return {"record": None, "valid": False, "errors": [f"Invalid JSON: {e}"], "raw_response": raw}

    schema_errors = validate_against_json_schema(record_dict)
    if schema_errors:
        return {"record": record_dict, "valid": False, "errors": schema_errors, "raw_response": raw}

    try:
        validated = MaterialRecord.model_validate(record_dict)
    except Exception as e:  # pydantic.ValidationError
        return {"record": record_dict, "valid": False, "errors": [str(e)], "raw_response": raw}

    return {"record": validated.model_dump(mode="json"), "valid": True, "errors": [], "raw_response": raw}


def save_record(record_dict: Dict[str, Any], out_dir: Path) -> Path:
    out_path = out_dir / f"{record_dict['record_id']}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(record_dict, f, ensure_ascii=False, indent=2)
    return out_path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run the extraction agent on a processed document")
    parser.add_argument("--text", required=True,
                         help="Path to a processed *.json file (from ingest_pdf.py) "
                              "or a *.chunks.json file")
    parser.add_argument("--record-id", default=None)
    parser.add_argument("--dry-run", action="store_true",
                         help="Skip the API call; validate a bundled example payload instead")
    parser.add_argument("--out-dir", default=str(config.EXTRACTED_DIR))
    args = parser.parse_args(argv)

    doc_path = Path(args.text)
    with open(doc_path, encoding="utf-8") as f:
        doc = json.load(f)

    if "pages" in doc:
        document_text = "\n".join(f"[[p.{p['page']}]]\n{p['text']}" for p in doc["pages"])
    else:
        document_text = "\n".join(c["text"] for c in doc.get("chunks", []))

    record_id = args.record_id or Path(doc.get("filename", doc_path.stem)).stem

    dry_run_payload = None
    if args.dry_run:
        example_path = config.EXTRACTED_DIR / "blastalloy160_concept_b.json"
        if example_path.exists():
            with open(example_path, encoding="utf-8") as f:
                dry_run_payload = json.load(f)
            dry_run_payload["record_id"] = record_id + "_dryrun"

    result = extract_record(document_text, record_id, dry_run=args.dry_run, dry_run_payload=dry_run_payload)

    if not result["valid"]:
        print("Extraction FAILED validation:")
        for err in result["errors"]:
            print(f"  - {err}")
        debug_path = Path(args.out_dir) / f"{record_id}.INVALID.raw.txt"
        debug_path.write_text(result["raw_response"], encoding="utf-8")
        print(f"Raw response saved for debugging: {debug_path}")
        return 1

    out_path = save_record(result["record"], Path(args.out_dir))
    print(f"Extracted and validated record: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

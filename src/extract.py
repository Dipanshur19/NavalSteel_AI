"""
Extraction Agent and Universal Materials Extractor.

Calls an LLM (Gemini or Claude) or deterministic physical metallurgy heuristics
to extract structured material records (composition wt% with balance Fe, heat
treatment schedules, tensile & Charpy properties, physical indices Pcm, Ms, Bs,
and military specification benchmarks) from any ingested file (.pdf, .csv, .tsv,
.txt, .md, .json).

Validated against both the Pydantic model (schema.py) and the portable JSON
Schema (schema/materials.schema.json).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from jsonschema import Draft7Validator

from . import config
from .optimize import calculate_raw_material_cost
from .physics import (
    calculate_bainite_start,
    calculate_carbon_equivalent_iiw,
    calculate_martensite_start,
    calculate_pcm,
    check_military_specifications,
)
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


def extract_metallurgy_info_from_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts structured metallurgical data (composition, properties, tables)
    from an ingested PDF document structure.
    """
    filename = doc.get("filename", "unknown.pdf")
    pages = doc.get("pages", [])
    num_pages = doc.get("num_pages", len(pages))
    doc_hash = doc.get("doc_hash", "unknown")
    
    all_tables = []
    for p in pages:
        p_num = p.get("page", 1)
        for t in p.get("tables", []):
            if t and len(t) > 1:
                all_tables.append({"page": p_num, "data": t})

    full_text = " ".join(p.get("text", "") for p in pages)
    
    # Heuristic composition detection (element wt%)
    elements = ["C", "Ni", "Cu", "Cr", "Mo", "Mn", "Si", "V", "B", "Co", "Fe"]
    compositions = []
    
    for tbl in all_tables:
        header = [str(cell).strip() for cell in tbl["data"][0] if cell]
        if any(el in header for el in ["C", "Ni", "Cu", "Cr", "Fe"]):
            for row in tbl["data"][1:6]:
                row_dict = {}
                for col_idx, cell in enumerate(row):
                    if col_idx < len(header):
                        h = header[col_idx]
                        if any(h == el or "wt" in h.lower() for el in elements):
                            row_dict[h] = str(cell).strip()
                if row_dict:
                    row_dict["Source Page"] = tbl["page"]
                    compositions.append(row_dict)

    # Heuristic properties detection
    properties = []
    ys_matches = re.findall(r'(?:yield\s+strength|0\.2%\s*offset\s*yield|ys)[\s:=]+(\d+(?:\.\d+)?)\s*(mpa|ksi)', full_text, re.IGNORECASE)
    for val, unit in ys_matches[:4]:
        properties.append({"Property": "Yield Strength", "Value": float(val), "Unit": unit.upper(), "Type": "Tensile"})

    uts_matches = re.findall(r'(?:ultimate\s+tensile\s+strength|tensile\s+strength|uts)[\s:=]+(\d+(?:\.\d+)?)\s*(mpa|ksi)', full_text, re.IGNORECASE)
    for val, unit in uts_matches[:4]:
        properties.append({"Property": "Tensile Strength (UTS)", "Value": float(val), "Unit": unit.upper(), "Type": "Tensile"})

    cvn_matches = re.findall(r'(?:charpy|impact\s+energy|cvn)[\s:=]+(\d+(?:\.\d+)?)\s*(j|joules|ft[- ]*lbs?|ft[- ]*lbf)', full_text, re.IGNORECASE)
    for val, unit in cvn_matches[:4]:
        properties.append({"Property": "Charpy Impact Energy", "Value": float(val), "Unit": unit.upper(), "Type": "Toughness"})

    unique_props = []
    seen = set()
    for p in properties:
        k = (p["Property"], p["Value"], p["Unit"])
        if k not in seen:
            seen.add(k)
            unique_props.append(p)

    return {
        "filename": filename,
        "num_pages": num_pages,
        "num_tables": len(all_tables),
        "doc_hash": doc_hash,
        "compositions": compositions,
        "properties": unique_props,
        "sample_tables": all_tables[:4]
    }


# ==============================================================================
# UNIVERSAL MATERIALS FILE EXTRACTOR (.PDF, .CSV, .TSV, .TXT, .MD, .JSON)
# ==============================================================================

STANDARD_ELEMENTS = ["C", "Mn", "Si", "Ni", "Cr", "Mo", "Cu", "V", "Nb", "Ti", "B", "Co", "Al", "Fe"]

ELEMENT_ALIASES: Dict[str, str] = {
    "carbon": "C", "c": "C",
    "manganese": "Mn", "mn": "Mn",
    "silicon": "Si", "si": "Si",
    "nickel": "Ni", "ni": "Ni",
    "chromium": "Cr", "cr": "Cr",
    "molybdenum": "Mo", "mo": "Mo",
    "copper": "Cu", "cu": "Cu",
    "vanadium": "V", "v": "V",
    "niobium": "Nb", "columbium": "Nb", "nb": "Nb", "cb": "Nb",
    "titanium": "Ti", "ti": "Ti",
    "boron": "B", "b": "B",
    "cobalt": "Co", "co": "Co",
    "aluminum": "Al", "aluminium": "Al", "al": "Al",
    "iron": "Fe", "fe": "Fe",
    "phosphorus": "P", "p": "P",
    "sulfur": "S", "s": "S"
}


def extract_from_any_file(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Universal materials data extractor for any file format:
    - .pdf : Parses text & tables across pages via pdfplumber
    - .csv / .tsv : Reads tabular chemistry & mechanical properties via pandas
    - .json : Parses structured metallurgical records or raw key-value dictionaries
    - .txt / .md : Extracts regex patterns, dashed chemistries, and markdown tables

    Computes:
    - Chemical composition (wt%) with automatic Fe balance
    - Heat treatment parameters (Austenitizing, Quenching, Tempering)
    - Mechanical properties (YS, UTS, CVN, Elongation, Hardness) in SI & Imperial
    - Physical metallurgy indices: Pcm, CE_IIW, Ms, Bs, commodity alloy cost
    - US Navy military specification compliance checks (MIL-S-24645A, MIL-S-16216K)
    - Session state payload for 1-click loading into Alloy Synthesizer
    """
    suffix = Path(filename).suffix.lower()
    doc_hash = hashlib.sha256(file_bytes).hexdigest()
    
    extracted_text = ""
    extracted_tables: List[Dict[str, Any]] = []
    num_pages = 1

    # 1. Parse File Content by Format
    if suffix == ".pdf":
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                num_pages = len(pdf.pages)
                text_chunks = []
                for idx, page in enumerate(pdf.pages[:80], start=1):
                    p_txt = page.extract_text() or ""
                    if p_txt:
                        text_chunks.append(f"[[Page {idx}]]\n" + p_txt)
                    p_tables = page.extract_tables() or []
                    for t_idx, tbl in enumerate(p_tables):
                        cleaned = [r for r in tbl if any(c for c in r)]
                        if len(cleaned) >= 2:
                            extracted_tables.append({
                                "source": f"PDF Page {idx} (Table {t_idx+1})",
                                "page": idx,
                                "data": cleaned
                            })
                extracted_text = "\n\n".join(text_chunks)
        except Exception as e:
            extracted_text = f"[PDF extraction warning: {str(e)}]"

    elif suffix in [".csv", ".tsv"]:
        sep = "\t" if suffix == ".tsv" else None
        text_str = file_bytes.decode("utf-8", errors="replace")
        extracted_text = text_str
        try:
            df = pd.read_csv(io.StringIO(text_str), sep=sep, engine="python")
            cleaned_rows = [df.columns.tolist()] + df.values.tolist()
            extracted_tables.append({
                "source": f"CSV Dataset: {Path(filename).stem}",
                "page": 1,
                "data": cleaned_rows,
                "dataframe": df
            })
        except Exception:
            pass

    elif suffix == ".json":
        text_str = file_bytes.decode("utf-8", errors="replace")
        extracted_text = text_str
        try:
            json_obj = json.loads(text_str)
            # Flatten or inspect
            if isinstance(json_obj, dict):
                extracted_tables.append({
                    "source": "JSON Document Object",
                    "page": 1,
                    "data": [["Key", "Value"]] + [[str(k), str(v)[:100]] for k, v in json_obj.items()]
                })
        except Exception:
            pass

    else:  # .txt, .md, and plain text
        text_str = file_bytes.decode("utf-8", errors="replace")
        extracted_text = text_str
        # Check for Markdown tables
        current_md_table = []
        for line in text_str.splitlines():
            sline = line.strip()
            if sline.startswith("|") and sline.endswith("|"):
                cells = [c.strip() for c in sline.split("|")[1:-1]]
                if not all(c.startswith("---") or c.startswith(":") for c in cells):
                    current_md_table.append(cells)
            else:
                if len(current_md_table) >= 2:
                    extracted_tables.append({
                        "source": f"Markdown Table ({len(current_md_table)} rows)",
                        "page": 1,
                        "data": current_md_table
                    })
                current_md_table = []
        if len(current_md_table) >= 2:
            extracted_tables.append({
                "source": f"Markdown Table ({len(current_md_table)} rows)",
                "page": 1,
                "data": current_md_table
            })

    # 2. Extract Chemical Composition
    comp: Dict[str, float] = {}
    
    # 2a. Check if parsed from JSON object
    if suffix == ".json":
        try:
            jobj = json.loads(extracted_text)
            # Schema 1: MaterialRecord steel.composition
            if "steel" in jobj and "composition" in jobj["steel"]:
                for c_item in jobj["steel"]["composition"]:
                    el = c_item.get("element", "")
                    val = c_item.get("value")
                    if el and val is not None:
                        comp[el] = float(val)
            # Schema 2: top-level composition / composition_wt_pct
            for k in ["composition_wt_pct", "composition", "chemistry", "elements"]:
                if k in jobj and isinstance(jobj[k], dict):
                    for el_raw, val in jobj[k].items():
                        el_clean = ELEMENT_ALIASES.get(el_raw.lower(), el_raw.capitalize())
                        if val is not None:
                            try:
                                comp[el_clean] = float(val)
                            except (ValueError, TypeError):
                                pass
            # Schema 3: direct keys
            for el_raw in STANDARD_ELEMENTS:
                if el_raw in jobj and jobj[el_raw] is not None:
                    try:
                        comp[el_raw] = float(jobj[el_raw])
                    except (ValueError, TypeError):
                        pass
        except Exception:
            pass

    # 2b. Check tables (CSV or extracted document tables)
    if not comp and extracted_tables:
        for tbl in extracted_tables:
            rows = tbl.get("data", [])
            if not rows or len(rows) < 2:
                continue
            header = [str(c).strip() for c in rows[0]]
            # Wide format: columns are elements
            matched_cols: Dict[str, int] = {}
            for idx, col_name in enumerate(header):
                cleaned_name = col_name.strip().replace("(wt%)", "").replace("wt%", "").replace("%", "").strip()
                el = ELEMENT_ALIASES.get(cleaned_name.lower())
                if el and el in STANDARD_ELEMENTS:
                    matched_cols[el] = idx
            
            if len(matched_cols) >= 3:
                # Extract first data row
                first_row = rows[1]
                for el, col_idx in matched_cols.items():
                    if col_idx < len(first_row):
                        raw_v = str(first_row[col_idx]).strip().replace("%", "")
                        try:
                            comp[el] = float(raw_v)
                        except (ValueError, TypeError):
                            pass
                if comp:
                    break
            
            # Long format: column 0 has element name, column 1 has value
            if len(header) >= 2:
                for row in rows[1:]:
                    if len(row) >= 2:
                        name_cell = str(row[0]).strip().replace("*", "").replace(":", "")
                        el = ELEMENT_ALIASES.get(name_cell.lower())
                        if el and el in STANDARD_ELEMENTS:
                            val_str = str(row[1]).strip().replace("%", "").replace("wt", "").strip()
                            try:
                                comp[el] = float(val_str)
                            except (ValueError, TypeError):
                                pass

    # Clean formatting markers for regex robustness across Markdown, logs, and tables
    clean_text_for_regex = re.sub(r'[*_#`]', '', extracted_text)

    # 2c. Check Regex in Text
    if not comp or len(comp) < 3:
        # Check hyphenated formula strings like: Fe-0.05C-6.5Ni-3.65Cu-1.84Cr-0.6Mo-0.1V
        formula_matches = re.findall(
            r'(?:Fe-)?((?:[0-9.]+[A-Za-z]+[- ]*)+)',
            clean_text_for_regex
        )
        for f_match in formula_matches:
            pairs = re.findall(r'([0-9.]+)\s*([A-Za-z]+)', f_match)
            if len(pairs) >= 3:
                for val, el_raw in pairs:
                    el = ELEMENT_ALIASES.get(el_raw.lower())
                    if el and el in STANDARD_ELEMENTS:
                        comp[el] = float(val)
                if len(comp) >= 3:
                    break

        # Explicit regex for standard elements
        for el in STANDARD_ELEMENTS:
            if el == "Fe":
                continue
            full_names = [k for k, v in ELEMENT_ALIASES.items() if v == el and len(k) > 2]
            name_pats = [rf"\b{el}\b"] + [rf"\b{fn.capitalize()}\b" for fn in full_names]
            el_group = "|".join(name_pats)
            pat = rf'(?:{el_group})(?:\s*\([A-Za-z]+\))?[\s:=]+([0-9.]+)\s*(?:wt%|%|\b)'
            m = re.search(pat, clean_text_for_regex, re.IGNORECASE)
            if m:
                try:
                    val = float(m.group(1))
                    if val < 30.0:  # Sanity check for alloying solutes
                        comp[el] = val
                except ValueError:
                    pass

    # Balance Fe calculation
    solutes_sum = sum(v for k, v in comp.items() if k != "Fe")
    if "Fe" not in comp or comp["Fe"] <= 50.0:
        comp["Fe"] = round(max(0.0, 100.0 - solutes_sum), 3)
        is_fe_balance = True
    else:
        is_fe_balance = False

    # 3. Extract Heat Treatment Parameters
    processing: Dict[str, Any] = {
        "austenitizing_temp_c": None,
        "austenitizing_time_h": None,
        "quench_medium": None,
        "tempering_temp_c": None,
        "tempering_time_h": None,
        "summary": "Standard thermal cycle"
    }

    # JSON processing check
    if suffix == ".json":
        try:
            jobj = json.loads(extracted_text)
            if "heat_treatment" in jobj and isinstance(jobj["heat_treatment"], dict):
                ht = jobj["heat_treatment"]
                processing["austenitizing_temp_c"] = ht.get("austenitizing_temp_c")
                processing["tempering_temp_c"] = ht.get("tempering_temp_c")
                processing["tempering_time_h"] = ht.get("tempering_time_h")
                processing["quench_medium"] = ht.get("quench")
            elif "processing" in jobj and isinstance(jobj["processing"], list):
                for step in jobj["processing"]:
                    s_name = str(step.get("step", "")).lower()
                    if "solution" in s_name or "austenit" in s_name:
                        processing["austenitizing_temp_c"] = step.get("temperature_C")
                    elif "temper" in s_name or "aging" in s_name:
                        if not processing["tempering_temp_c"]:
                            processing["tempering_temp_c"] = step.get("temperature_C")
                            t_str = str(step.get("time", ""))
                            tm = re.search(r'([0-9.]+)\s*(?:h|hr|hours?)', t_str)
                            if tm:
                                processing["tempering_time_h"] = float(tm.group(1))
        except Exception:
            pass

    # Regex for Austenitizing / Solution
    if processing["austenitizing_temp_c"] is None:
        m_aust = re.search(r'(?:austenitiz(?:ed|ing)?|solution\s+treatment)[\s\w]*?(?:at\s+)?([0-9]{3,4})\s*(?:°?C|deg\s*C)', extracted_text, re.IGNORECASE)
        if m_aust:
            processing["austenitizing_temp_c"] = float(m_aust.group(1))

    # Regex for Quenching
    if processing["quench_medium"] is None:
        m_quench = re.search(r'(water[\s-]?quench|oil[\s-]?quench|air[\s-]?cool|gas[\s-]?quench|liquid[\s-]?nitrogen)', extracted_text, re.IGNORECASE)
        if m_quench:
            processing["quench_medium"] = m_quench.group(1).lower().replace("-", " ")

    # Regex for Tempering / Aging
    if processing["tempering_temp_c"] is None:
        m_temp = re.search(r'(?:temper(?:ed|ing)?|ag(?:ed|ing)?)[\s\w]*?(?:at\s+)?([0-9]{3,4})\s*(?:°?C|deg\s*C)', extracted_text, re.IGNORECASE)
        if m_temp:
            processing["tempering_temp_c"] = float(m_temp.group(1))

    if processing["tempering_time_h"] is None:
        m_ttime = re.search(r'(?:temper(?:ed|ing)?|ag(?:ed|ing)?)[^.\n]*?([0-9.]+)\s*(?:h|hr|hours?)', extracted_text, re.IGNORECASE)
        if m_ttime:
            processing["tempering_time_h"] = float(m_ttime.group(1))

    # Build processing summary string
    proc_desc = []
    if processing["austenitizing_temp_c"]:
        proc_desc.append(f"Austenitized at {processing['austenitizing_temp_c']:.0f}°C")
    if processing["quench_medium"]:
        proc_desc.append(f"{processing['quench_medium'].title()}")
    if processing["tempering_temp_c"]:
        t_dur = f" for {processing['tempering_time_h']}h" if processing['tempering_time_h'] else ""
        proc_desc.append(f"Tempered at {processing['tempering_temp_c']:.0f}°C{t_dur}")
    processing["summary"] = " -> ".join(proc_desc) if proc_desc else "Thermal cycle: Austenitize 900°C -> Quench -> Temper"

    # 4. Extract Mechanical Properties
    props: Dict[str, Any] = {
        "yield_strength_mpa": None,
        "yield_strength_ksi": None,
        "tensile_strength_mpa": None,
        "tensile_strength_ksi": None,
        "charpy_toughness_j": None,
        "charpy_toughness_ft_lb": None,
        "charpy_temp_c": -40.0,
        "elongation_pct": None,
        "hardness_hrc": None,
        "raw_matches": []
    }

    # JSON mechanical properties
    if suffix == ".json":
        try:
            jobj = json.loads(extracted_text)
            if "mechanical_properties" in jobj and isinstance(jobj["mechanical_properties"], dict):
                mp = jobj["mechanical_properties"]
                if "yield_strength_mpa" in mp:
                    props["yield_strength_mpa"] = float(mp["yield_strength_mpa"])
                    props["yield_strength_ksi"] = round(props["yield_strength_mpa"] * 0.145038, 1)
                if "tensile_strength_mpa" in mp:
                    props["tensile_strength_mpa"] = float(mp["tensile_strength_mpa"])
                    props["tensile_strength_ksi"] = round(props["tensile_strength_mpa"] * 0.145038, 1)
                if "charpy_toughness_j" in mp:
                    props["charpy_toughness_j"] = float(mp["charpy_toughness_j"])
                    props["charpy_toughness_ft_lb"] = round(props["charpy_toughness_j"] * 0.737562, 1)
                if "elongation_pct" in mp:
                    props["elongation_pct"] = float(mp["elongation_pct"])
                if "hardness_hrc" in mp:
                    props["hardness_hrc"] = float(mp["hardness_hrc"])
            elif "properties" in jobj and isinstance(jobj["properties"], list):
                for p_item in jobj["properties"]:
                    p_name = p_item.get("property", "").lower()
                    val = p_item.get("value")
                    unit = p_item.get("unit", "").lower()
                    if val is not None:
                        if "yield" in p_name:
                            if "ksi" in unit:
                                props["yield_strength_ksi"] = float(val)
                                props["yield_strength_mpa"] = round(float(val) * 6.89476, 1)
                            else:
                                props["yield_strength_mpa"] = float(val)
                                props["yield_strength_ksi"] = round(float(val) * 0.145038, 1)
                        elif "charpy" in p_name or "toughness" in p_name:
                            if "ft-lb" in unit or "ft_lb" in unit:
                                props["charpy_toughness_ft_lb"] = float(val)
                                props["charpy_toughness_j"] = round(float(val) * 1.35582, 1)
                            else:
                                props["charpy_toughness_j"] = float(val)
                                props["charpy_toughness_ft_lb"] = round(float(val) * 0.737562, 1)
        except Exception:
            pass

    # CSV / DataFrame column detection for mechanical properties & thermal cycles
    if extracted_tables and "dataframe" in extracted_tables[0]:
        df_src = extracted_tables[0]["dataframe"]
        if len(df_src) > 0:
            row0 = df_src.iloc[0]
            for c in df_src.columns:
                cl = str(c).lower()
                val_c = row0[c]
                try:
                    vf = float(val_c)
                    if ("ys" in cl or "yield" in cl) and props["yield_strength_mpa"] is None:
                        if "ksi" in cl:
                            props["yield_strength_ksi"] = vf
                            props["yield_strength_mpa"] = round(vf * 6.89476, 1)
                        else:
                            props["yield_strength_mpa"] = vf
                            props["yield_strength_ksi"] = round(vf * 0.145038, 1)
                        props["raw_matches"].append({"property": "Yield Strength (CSV)", "val": vf, "unit": "MPa"})
                    elif ("uts" in cl or "tensile" in cl) and props["tensile_strength_mpa"] is None:
                        if "ksi" in cl:
                            props["tensile_strength_ksi"] = vf
                            props["tensile_strength_mpa"] = round(vf * 6.89476, 1)
                        else:
                            props["tensile_strength_mpa"] = vf
                            props["tensile_strength_ksi"] = round(vf * 0.145038, 1)
                        props["raw_matches"].append({"property": "UTS (CSV)", "val": vf, "unit": "MPa"})
                    elif ("cvn" in cl or "charpy" in cl or "impact" in cl) and props["charpy_toughness_j"] is None:
                        if "ft" in cl:
                            props["charpy_toughness_ft_lb"] = vf
                            props["charpy_toughness_j"] = round(vf * 1.35582, 1)
                        else:
                            props["charpy_toughness_j"] = vf
                            props["charpy_toughness_ft_lb"] = round(vf * 0.737562, 1)
                        props["raw_matches"].append({"property": "Charpy Toughness (CSV)", "val": vf, "unit": "J"})
                    elif ("elong" in cl or "ductil" in cl) and props["elongation_pct"] is None:
                        props["elongation_pct"] = vf
                    elif ("hard" in cl or "hrc" in cl) and props["hardness_hrc"] is None:
                        props["hardness_hrc"] = vf
                    elif "austeniti" in cl and processing["austenitizing_temp_c"] is None:
                        processing["austenitizing_temp_c"] = vf
                    elif "temper" in cl and "temp" in cl and processing["tempering_temp_c"] is None:
                        processing["tempering_temp_c"] = vf
                    elif "temper" in cl and "time" in cl and processing["tempering_time_h"] is None:
                        processing["tempering_time_h"] = vf
                except (ValueError, TypeError):
                    pass

    # Regex for Yield Strength
    if props["yield_strength_mpa"] is None:
        m_ys = re.findall(r'(?:yield\s+strength|0\.2%\s*offset\s*yield|ys|proof\s+stress)(?:\s*\([^)]*\))?[\s:=]+(\d+(?:\.\d+)?)\s*(mpa|ksi)', clean_text_for_regex, re.IGNORECASE)
        if m_ys:
            val, unit = m_ys[0]
            val_f = float(val)
            if unit.lower() == "ksi":
                props["yield_strength_ksi"] = val_f
                props["yield_strength_mpa"] = round(val_f * 6.89476, 1)
            else:
                props["yield_strength_mpa"] = val_f
                props["yield_strength_ksi"] = round(val_f * 0.145038, 1)
            props["raw_matches"].append({"property": "Yield Strength", "val": val_f, "unit": unit.upper()})

    # Regex for Tensile Strength (UTS)
    if props["tensile_strength_mpa"] is None:
        m_uts = re.findall(r'(?:ultimate\s+tensile\s+strength|tensile\s+strength|uts)(?:\s*\([^)]*\))?[\s:=]+(\d+(?:\.\d+)?)\s*(mpa|ksi)', clean_text_for_regex, re.IGNORECASE)
        if m_uts:
            val, unit = m_uts[0]
            val_f = float(val)
            if unit.lower() == "ksi":
                props["tensile_strength_ksi"] = val_f
                props["tensile_strength_mpa"] = round(val_f * 6.89476, 1)
            else:
                props["tensile_strength_mpa"] = val_f
                props["tensile_strength_ksi"] = round(val_f * 0.145038, 1)
            props["raw_matches"].append({"property": "UTS", "val": val_f, "unit": unit.upper()})

    # Regex for Charpy Toughness
    if props["charpy_toughness_j"] is None:
        m_cvn = re.findall(r'(?:charpy(?:\s+v-notch)?|impact\s+energy|cvn)(?:[^\n:=]*?)[\s:=]+(\d+(?:\.\d+)?)\s*(j|joules|ft[- ]*lbs?|ft[- ]*lbf)', clean_text_for_regex, re.IGNORECASE)
        if m_cvn:
            val, unit = m_cvn[0]
            val_f = float(val)
            if "ft" in unit.lower():
                props["charpy_toughness_ft_lb"] = val_f
                props["charpy_toughness_j"] = round(val_f * 1.35582, 1)
            else:
                props["charpy_toughness_j"] = val_f
                props["charpy_toughness_ft_lb"] = round(val_f * 0.737562, 1)
            props["raw_matches"].append({"property": "Charpy Toughness", "val": val_f, "unit": unit.upper()})

    # Regex for Elongation
    if props["elongation_pct"] is None:
        m_el = re.search(r'(?:elongation|ductility)[\s\w]*?[\s:=]+(\d+(?:\.\d+)?)\s*(?:%|pct)', clean_text_for_regex, re.IGNORECASE)
        if m_el:
            props["elongation_pct"] = float(m_el.group(1))

    # Regex for Hardness
    if props["hardness_hrc"] is None:
        m_hrc = re.search(r'(?:hardness|rockwell)[\s:=]+(\d+(?:\.\d+)?)\s*(?:hrc)?', clean_text_for_regex, re.IGNORECASE)
        if m_hrc:
            props["hardness_hrc"] = float(m_hrc.group(1))

    # 5. Compute Physical Metallurgy Indices
    pcm_val = calculate_pcm(comp)
    ce_iiw_val = calculate_carbon_equivalent_iiw(comp)
    ms_val = calculate_martensite_start(comp)
    bs_val = calculate_bainite_start(comp)
    cost_min, cost_max = calculate_raw_material_cost(comp)

    # Weldability Assessment
    if pcm_val <= 0.22:
        weld_status = "Optimal Field Weldability (Crack-free without preheat up to 50 mm plate)"
    elif pcm_val <= 0.28:
        weld_status = "Good Military Weldability (Preheat optional for thin plate < 25 mm, recommended for heavy armor)"
    else:
        weld_status = "High Cracking Susceptibility (Mandatory preheat > 100°C required to prevent hydrogen cold cracking)"

    # Military Specification Check
    prop_eval_dict = {}
    if props["yield_strength_mpa"]:
        prop_eval_dict["yield_strength"] = props["yield_strength_mpa"]
    if props["charpy_toughness_j"]:
        prop_eval_dict["charpy_toughness"] = props["charpy_toughness_j"]
    
    mil_results = check_military_specifications(comp, prop_eval_dict)

    # 6. Session Payload for 1-Click Injection into Studio 1 (Alloy Synthesizer)
    session_payload = {
        "st_c": float(comp.get("C", 0.05)),
        "st_ni": float(comp.get("Ni", 5.0)),
        "st_cu": float(comp.get("Cu", 1.5)),
        "st_cr": float(comp.get("Cr", 1.0)),
        "st_mo": float(comp.get("Mo", 0.5)),
        "st_mn": float(comp.get("Mn", 0.6)),
        "st_si": float(comp.get("Si", 0.25)),
        "st_v": float(comp.get("V", 0.08)),
        "st_b": float(comp.get("B", 0.001)),
        "st_temper_t": float(processing["tempering_temp_c"] or 480.0),
        "st_temper_time": float(processing["tempering_time_h"] or 4.0),
    }

    # Format sample preview text
    preview_snippet = extracted_text[:1200] if extracted_text else "No textual content available."

    return {
        "filename": filename,
        "file_type": suffix.replace(".", "").upper(),
        "file_size_kb": round(len(file_bytes) / 1024, 2),
        "doc_hash": doc_hash,
        "num_pages": num_pages,
        "steel_name": Path(filename).stem.replace("_", " ").title(),
        "composition": comp,
        "solutes_sum": round(solutes_sum, 3),
        "is_fe_balance": is_fe_balance,
        "processing": processing,
        "properties": props,
        "physics": {
            "pcm": round(pcm_val, 4),
            "ce_iiw": round(ce_iiw_val, 4),
            "martensite_start_c": round(ms_val, 1),
            "bainite_start_c": round(bs_val, 1),
            "raw_cost_usd_kg_min": round(cost_min, 2),
            "raw_cost_usd_kg_max": round(cost_max, 2),
            "weldability_assessment": weld_status,
            "mil_spec_compliance": mil_results
        },
        "tables": extracted_tables,
        "raw_text_preview": preview_snippet,
        "session_payload": session_payload
    }


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

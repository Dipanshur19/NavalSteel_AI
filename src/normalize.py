"""
Unit normalization and canonicalization engine for NavalSteel AI.

Converts metallurgical property units (ksi <-> MPa, ft-lb <-> J, F <-> C)
and standardizes elemental symbols, ensuring downstream ML models,
comparative queries, and evaluation tests have consistent, dual-unit ground truth.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

# Element lookup table
ELEMENT_NAME_TO_SYMBOL = {
    "iron": "Fe", "carbon": "C", "nickel": "Ni", "copper": "Cu",
    "chromium": "Cr", "molybdenum": "Mo", "vanadium": "V", "manganese": "Mn",
    "silicon": "Si", "niobium": "Nb", "titanium": "Ti", "cobalt": "Co",
    "aluminum": "Al", "boron": "B", "nitrogen": "N", "phosphorus": "P", "sulfur": "S"
}

# Unit conversion constants
KSI_TO_MPA = 6.89475729
MPA_TO_KSI = 1.0 / KSI_TO_MPA
FT_LB_TO_JOULE = 1.3558179483314
JOULE_TO_FT_LB = 1.0 / FT_LB_TO_JOULE


def canonical_element_symbol(name_or_symbol: str) -> str:
    """Returns canonical 1- or 2-letter element symbol (e.g. 'carbon' -> 'C', 'NI' -> 'Ni')."""
    cleaned = name_or_symbol.strip()
    lower = cleaned.lower()
    if lower in ELEMENT_NAME_TO_SYMBOL:
        return ELEMENT_NAME_TO_SYMBOL[lower]
    if len(cleaned) <= 2:
        return cleaned.capitalize()
    return cleaned


def normalize_pressure_or_strength(value: float, unit: str) -> Dict[str, float]:
    """Returns canonical values in both MPa and ksi."""
    u = unit.strip().lower()
    if u in ("mpa", "n/mm2", "n/mm^2"):
        mpa = value
        ksi = value * MPA_TO_KSI
    elif u in ("ksi", "kpsi"):
        ksi = value
        mpa = value * KSI_TO_MPA
    elif u in ("psi",):
        ksi = value / 1000.0
        mpa = ksi * KSI_TO_MPA
    elif u in ("gpa",):
        mpa = value * 1000.0
        ksi = mpa * MPA_TO_KSI
    else:
        mpa = value
        ksi = value * MPA_TO_KSI

    return {
        "mpa": round(mpa, 2),
        "ksi": round(ksi, 2),
    }


def normalize_impact_energy(value: float, unit: str) -> Dict[str, float]:
    """Returns canonical values in both Joules and ft-lb."""
    u = unit.strip().lower()
    if u in ("j", "joule", "joules"):
        joules = value
        ft_lb = value * JOULE_TO_FT_LB
    elif u in ("ft-lb", "ft-lbs", "ft lb", "ft.lb", "ft lbs", "ft_lb"):
        ft_lb = value
        joules = value * FT_LB_TO_JOULE
    elif u in ("kj",):
        joules = value * 1000.0
        ft_lb = joules * JOULE_TO_FT_LB
    else:
        joules = value
        ft_lb = value * JOULE_TO_FT_LB

    return {
        "joules": round(joules, 1),
        "ft_lb": round(ft_lb, 1),
    }


def normalize_temperature(value: float, unit: str) -> Dict[str, float]:
    """Returns temperature in both Celsius and Fahrenheit."""
    u = unit.strip().lower().replace("°", "").replace("deg", "")
    if "c" in u:
        celsius = value
        fahrenheit = (value * 9.0 / 5.0) + 32.0
    elif "f" in u:
        fahrenheit = value
        celsius = (value - 32.0) * 5.0 / 9.0
    elif "k" in u:
        celsius = value - 273.15
        fahrenheit = (celsius * 9.0 / 5.0) + 32.0
    else:
        celsius = value
        fahrenheit = (value * 9.0 / 5.0) + 32.0

    return {
        "celsius": round(celsius, 1),
        "fahrenheit": round(fahrenheit, 1),
    }


def enrich_text_with_normalized_units(text: str) -> str:
    """Enriches extracted text by appending dual-unit conversions where missing.
    For example: '130 ft-lb' -> '130 ft-lb (176 J)', '160 ksi' -> '160 ksi (1100 MPa)'.
    """
    def _replace_ft_lb(match):
        full = match.group(0)
        val_str = match.group(1)
        try:
            val = float(val_str)
            j = round(val * FT_LB_TO_JOULE)
            return f"{full} ({j} J)"
        except ValueError:
            return full

    def _replace_ksi(match):
        full = match.group(0)
        val_str = match.group(1)
        try:
            val = float(val_str)
            mpa = round(val * KSI_TO_MPA)
            return f"{full} ({mpa} MPa)"
        except ValueError:
            return full

    # Match ft-lb without (J) immediately following
    enriched = re.sub(r"\b(\d+(?:\.\d+)?)\s*(?:ft-lb|ft\s*lb|ft-lbs)\b(?!\s*\(\s*\d+\s*J)", _replace_ft_lb, text, flags=re.IGNORECASE)
    # Match ksi without (MPa) immediately following
    enriched = re.sub(r"\b(\d+(?:\.\d+)?)\s*ksi\b(?!\s*\(\s*\d+\s*MPa)", _replace_ksi, enriched, flags=re.IGNORECASE)
    return enriched

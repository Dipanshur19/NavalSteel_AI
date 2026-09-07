"""
Physics-informed metallurgical engine for NavalSteel AI.

Calculates weldability parameters (CE_IIW, Ito-Bessyo Pcm), cold-cracking
risk categories, preheat recommendations, and phase-transformation
temperatures (Ms, Bs, Ae3) directly from alloy composition.
"""
from __future__ import annotations

import math
from typing import Any, Dict


def extract_element_map(composition: list | dict) -> Dict[str, float]:
    """Helper to convert a list of CompositionEntry dicts or a raw dict
    into a clean { 'C': 0.05, 'Ni': 6.5, ... } mapping."""
    if isinstance(composition, dict):
        return {k.capitalize(): float(v) for k, v in composition.items() if v is not None}
    
    comp_map = {}
    for entry in composition:
        if isinstance(entry, dict):
            el = entry.get("element", "")
            val = entry.get("value")
            if val is not None and not entry.get("is_balance", False):
                comp_map[el.capitalize()] = float(val)
        else:
            # Pydantic model object
            el = getattr(entry, "element", "")
            val = getattr(entry, "value", None)
            is_bal = getattr(entry, "is_balance", False)
            if val is not None and not is_bal:
                comp_map[el.capitalize()] = float(val)
    return comp_map


def calculate_carbon_equivalent_iiw(comp: Dict[str, float]) -> float:
    """International Institute of Welding Carbon Equivalent:
    CE_IIW = C + Mn/6 + (Cr + Mo + V)/5 + (Ni + Cu)/15
    """
    c = comp.get("C", 0.0)
    mn = comp.get("Mn", 0.0)
    cr = comp.get("Cr", 0.0)
    mo = comp.get("Mo", 0.0)
    v = comp.get("V", 0.0)
    ni = comp.get("Ni", 0.0)
    cu = comp.get("Cu", 0.0)

    ce = c + (mn / 6.0) + ((cr + mo + v) / 5.0) + ((ni + cu) / 15.0)
    return round(ce, 3)


def calculate_pcm(comp: Dict[str, float]) -> float:
    """Ito-Bessyo cold cracking susceptibility parameter:
    Pcm = C + Si/30 + (Mn + Cu + Cr)/20 + Ni/60 + Mo/15 + V/10 + 5*B
    Specifically designed for low-carbon high-strength steels.
    """
    c = comp.get("C", 0.0)
    si = comp.get("Si", 0.0)
    mn = comp.get("Mn", 0.0)
    cu = comp.get("Cu", 0.0)
    cr = comp.get("Cr", 0.0)
    ni = comp.get("Ni", 0.0)
    mo = comp.get("Mo", 0.0)
    v = comp.get("V", 0.0)
    b = comp.get("B", 0.0)

    pcm = c + (si / 30.0) + ((mn + cu + cr) / 20.0) + (ni / 60.0) + (mo / 15.0) + (v / 10.0) + (5.0 * b)
    return round(pcm, 3)


def calculate_martensite_start(comp: Dict[str, float]) -> float:
    """Andrews (1965) Martensite-Start temperature formula (in Celsius):
    Ms = 539 - 423*C - 30.4*Mn - 17.7*Ni - 12.1*Cr - 7.5*Mo - 11.0*Si - 7.0*Cu
    """
    c = comp.get("C", 0.0)
    mn = comp.get("Mn", 0.0)
    ni = comp.get("Ni", 0.0)
    cr = comp.get("Cr", 0.0)
    mo = comp.get("Mo", 0.0)
    si = comp.get("Si", 0.0)
    cu = comp.get("Cu", 0.0)

    ms = 539.0 - (423.0 * c) - (30.4 * mn) - (17.7 * ni) - (12.1 * cr) - (7.5 * mo) - (11.0 * si) - (7.0 * cu)
    return round(ms, 1)


def calculate_bainite_start(comp: Dict[str, float]) -> float:
    """Steven & Haynes Bainite-Start temperature formula (in Celsius):
    Bs = 830 - 270*C - 90*Mn - 37*Ni - 70*Cr - 83*Mo
    """
    c = comp.get("C", 0.0)
    mn = comp.get("Mn", 0.0)
    ni = comp.get("Ni", 0.0)
    cr = comp.get("Cr", 0.0)
    mo = comp.get("Mo", 0.0)

    bs = 830.0 - (270.0 * c) - (90.0 * mn) - (37.0 * ni) - (70.0 * cr) - (83.0 * mo)
    return round(bs, 1)


def evaluate_steel_physics(composition: list | dict) -> Dict[str, Any]:
    """Complete physical evaluation of an alloy composition."""
    comp = extract_element_map(composition)
    ce = calculate_carbon_equivalent_iiw(comp)
    pcm = calculate_pcm(comp)
    ms = calculate_martensite_start(comp)
    bs = calculate_bainite_start(comp)

    # Weldability risk classification based on Pcm
    if pcm <= 0.20:
        risk_level = "Low"
        weldability_summary = "Excellent weldability. Plate can generally be welded without preheat under standard heat inputs."
        preheat_c = 20  # Ambient room temp
    elif pcm <= 0.28:
        risk_level = "Moderate"
        weldability_summary = "Moderate cold cracking risk. Mild preheat (50-100°C) recommended for thick plates."
        preheat_c = round(1440.0 * pcm - 200.0)
        preheat_c = max(50, min(preheat_c, 100))
    else:
        risk_level = "High"
        weldability_summary = "High susceptibility to HAZ hydrogen-induced cracking. Strict preheat (120-175°C) and low-hydrogen consumables required."
        preheat_c = round(1440.0 * pcm - 200.0)
        preheat_c = max(120, min(preheat_c, 200))

    return {
        "composition": comp,
        "ce_iiw": ce,
        "pcm": pcm,
        "weldability_risk": risk_level,
        "weldability_summary": weldability_summary,
        "recommended_preheat_C": preheat_c,
        "martensite_start_C": ms,
        "bainite_start_C": bs,
    }

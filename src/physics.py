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


MIL_SPECIFICATIONS: Dict[str, Dict[str, Any]] = {
    "MIL-S-24645A (HSLA-100)": {
        "standard": "MIL-S-24645A",
        "title": "High-Strength Low-Alloy Structural Steel (HSLA-100)",
        "yield_strength_min": 690.0,
        "yield_strength_max": 830.0,
        "tensile_strength_min": 795.0,
        "charpy_min_neg40c": 60.0,
        "pcm_max": 0.30,
        "carbon_max": 0.07,
        "chemistry": {
            "C": (0.00, 0.07),
            "Mn": (0.75, 1.15),
            "Ni": (3.25, 3.75),
            "Cu": (1.40, 1.80),
            "Cr": (0.40, 0.80),
            "Mo": (0.50, 0.70),
        },
        "description": "Copper precipitation hardened low-carbon bainitic/martensitic naval plate designed for welding with minimal preheat."
    },
    "MIL-S-24645A (HSLA-115)": {
        "standard": "MIL-S-24645A",
        "title": "High-Strength Low-Alloy Structural Steel (HSLA-115)",
        "yield_strength_min": 795.0,
        "yield_strength_max": 930.0,
        "tensile_strength_min": 860.0,
        "charpy_min_neg40c": 50.0,
        "pcm_max": 0.32,
        "carbon_max": 0.07,
        "chemistry": {
            "C": (0.00, 0.07),
            "Ni": (3.50, 4.20),
            "Cu": (1.40, 1.85),
            "Mo": (0.55, 0.85),
        },
        "description": "Enhanced high-yield naval plate with elevated Ni/Cu balance for high strength and low-temperature toughness."
    },
    "MIL-S-16216 (HY-80)": {
        "standard": "MIL-S-16216",
        "title": "High-Yield Quenched and Tempered Steel (HY-80)",
        "yield_strength_min": 550.0,
        "yield_strength_max": 690.0,
        "tensile_strength_min": 690.0,
        "charpy_min_neg40c": 47.0,
        "pcm_max": 0.40,
        "carbon_max": 0.18,
        "chemistry": {
            "C": (0.12, 0.18),
            "Ni": (2.00, 3.25),
            "Cr": (1.00, 1.80),
            "Mo": (0.20, 0.60),
        },
        "description": "Classic carbon-martensitic quenched and tempered submarine hull steel requiring mandatory preheat."
    },
    "MIL-S-16216 (HY-100)": {
        "standard": "MIL-S-16216",
        "title": "High-Yield Quenched and Tempered Steel (HY-100)",
        "yield_strength_min": 690.0,
        "yield_strength_max": 830.0,
        "tensile_strength_min": 795.0,
        "charpy_min_neg40c": 55.0,
        "pcm_max": 0.45,
        "carbon_max": 0.20,
        "chemistry": {
            "C": (0.14, 0.20),
            "Ni": (2.25, 3.50),
            "Cr": (1.40, 2.00),
            "Mo": (0.30, 0.60),
        },
        "description": "High-hardenability submarine plate steel with enhanced Ni-Cr alloying."
    },
    "ONR BlastAlloy 160": {
        "standard": "ONR Target",
        "title": "Office of Naval Research Ultra-High-Strength Blast-Resistant Plate",
        "yield_strength_min": 1100.0,
        "yield_strength_max": 1250.0,
        "tensile_strength_min": 1200.0,
        "charpy_min_neg40c": 60.0,
        "pcm_max": 0.24,
        "carbon_max": 0.07,
        "chemistry": {
            "C": (0.03, 0.07),
            "Ni": (3.50, 4.50),
            "Cu": (1.20, 1.80),
            "Cr": (0.20, 0.80),
            "Mo": (0.40, 0.90),
        },
        "description": "Next-generation naval plate combining nanoscale Cu precipitation, secondary M2C carbides, and retained austenite TRIP toughening."
    }
}


def check_military_specifications(
    composition: list | dict,
    predicted_properties: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """Evaluates an alloy composition and its predicted mechanical properties
    against landmark naval military specifications (MIL-S-24645A, MIL-S-16216, ONR).
    
    Returns a structured dictionary with compliance status, per-specification criteria checks,
    and the closest matching naval defense standard.
    """
    comp = extract_element_map(composition)
    physics = evaluate_steel_physics(comp)
    pcm = physics["pcm"]
    props = predicted_properties or {}
    
    ys = props.get("yield_strength_mpa") or props.get("ys") or props.get("yield_strength")
    cvn = props.get("charpy_impact_energy_j") or props.get("cvn") or props.get("charpy")
    uts = props.get("tensile_strength_mpa") or props.get("uts") or props.get("tensile_strength")
    
    results: Dict[str, Any] = {}
    best_match_name: Optional[str] = None
    best_match_score = -1.0
    
    for spec_name, spec in MIL_SPECIFICATIONS.items():
        checks = []
        total_checks = 0
        passed_checks = 0
        
        # Carbon constraint
        c_val = comp.get("C", 0.0)
        c_max = spec["carbon_max"]
        c_pass = c_val <= c_max
        checks.append({
            "parameter": "Carbon (wt%)",
            "required": f"<= {c_max:.2f}%",
            "actual": f"{c_val:.3f}%",
            "passed": c_pass
        })
        total_checks += 1
        if c_pass:
            passed_checks += 1
            
        # Pcm weldability constraint
        pcm_max = spec["pcm_max"]
        pcm_pass = pcm <= pcm_max
        checks.append({
            "parameter": "Pcm Weldability",
            "required": f"<= {pcm_max:.2f}",
            "actual": f"{pcm:.3f}",
            "passed": pcm_pass
        })
        total_checks += 1
        if pcm_pass:
            passed_checks += 1
            
        # Yield Strength (if predicted properties available)
        if ys is not None:
            ys_min = spec["yield_strength_min"]
            ys_max = spec["yield_strength_max"]
            ys_pass = ys_min <= ys <= ys_max
            checks.append({
                "parameter": "Yield Strength (MPa)",
                "required": f"{ys_min:.0f} - {ys_max:.0f} MPa",
                "actual": f"{ys:.1f} MPa",
                "passed": ys_pass
            })
            total_checks += 1
            if ys_pass:
                passed_checks += 1
                
        # Charpy Toughness at -40°C
        if cvn is not None:
            cvn_min = spec["charpy_min_neg40c"]
            cvn_pass = cvn >= cvn_min
            checks.append({
                "parameter": "CVN at -40°C (J)",
                "required": f">= {cvn_min:.0f} J",
                "actual": f"{cvn:.1f} J",
                "passed": cvn_pass
            })
            total_checks += 1
            if cvn_pass:
                passed_checks += 1
                
        # Chemistry tolerance bands
        for el, (el_min, el_max) in spec["chemistry"].items():
            actual_el = comp.get(el, 0.0)
            # Only strictly check if element is present or specified
            el_pass = el_min <= actual_el <= el_max
            checks.append({
                "parameter": f"{el} (wt%)",
                "required": f"{el_min:.2f} - {el_max:.2f}%",
                "actual": f"{actual_el:.2f}%",
                "passed": el_pass
            })
            total_checks += 1
            if el_pass:
                passed_checks += 1
                
        score_pct = round((passed_checks / max(1, total_checks)) * 100.0, 1)
        if score_pct == 100.0:
            status = "COMPLIANT"
        elif score_pct >= 70.0:
            status = "NEAR_COMPLIANT"
        else:
            status = "NON_COMPLIANT"
            
        if score_pct > best_match_score:
            best_match_score = score_pct
            best_match_name = spec_name
            
        results[spec_name] = {
            "title": spec["title"],
            "standard": spec["standard"],
            "description": spec["description"],
            "status": status,
            "compliance_score_pct": score_pct,
            "passed_checks": passed_checks,
            "total_checks": total_checks,
            "checks": checks,
        }
        
    return {
        "specifications": results,
        "best_match": best_match_name,
        "best_match_score_pct": best_match_score,
    }


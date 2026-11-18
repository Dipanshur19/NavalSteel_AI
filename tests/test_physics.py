"""Tests for the physics-informed metallurgical engine."""
from src.physics import (
    calculate_carbon_equivalent_iiw,
    calculate_pcm,
    calculate_martensite_start,
    calculate_bainite_start,
    evaluate_steel_physics,
    check_military_specifications,
)


def test_blastalloy160_physics():
    # Concept B composition: Fe - 0.05 C - 6.5 Ni - 3.65 Cu - 1.84 Cr - 0.60 Mo - 0.10 V
    comp = {"C": 0.05, "Ni": 6.5, "Cu": 3.65, "Cr": 1.84, "Mo": 0.60, "V": 0.10}
    eval_res = evaluate_steel_physics(comp)

    # Low carbon gives very low Pcm (~0.4-0.5 despite high Ni and Cu)
    assert eval_res["pcm"] < 0.5
    assert eval_res["martensite_start_C"] > 250  # Typically around 280-310C
    assert eval_res["bainite_start_C"] > 300


def test_hy80_physics():
    # HY-80: 0.15 C, 0.25 Mn, 0.25 Si, 2.75 Ni, 1.40 Cr, 0.40 Mo, 0.02 V
    comp = {"C": 0.15, "Mn": 0.25, "Si": 0.25, "Ni": 2.75, "Cr": 1.40, "Mo": 0.40, "V": 0.02}
    eval_res = evaluate_steel_physics(comp)

    # HY-80 has higher carbon and CE_IIW (~0.6-0.7)
    assert eval_res["ce_iiw"] >= 0.6
    assert eval_res["weldability_risk"] in ("Moderate", "High")
    assert eval_res["recommended_preheat_C"] >= 50


def test_check_military_specifications_hsla100():
    # Canonical HSLA-100 composition
    comp = {"C": 0.04, "Mn": 0.90, "Ni": 3.50, "Cu": 1.60, "Cr": 0.60, "Mo": 0.60, "Nb": 0.03}
    props = {"yield_strength_mpa": 750.0, "charpy_impact_energy_j": 85.0}
    res = check_military_specifications(comp, props)

    assert "MIL-S-24645A (HSLA-100)" in res["specifications"]
    hsla_res = res["specifications"]["MIL-S-24645A (HSLA-100)"]
    assert hsla_res["status"] == "COMPLIANT"
    assert hsla_res["compliance_score_pct"] == 100.0


def test_check_military_specifications_hy80():
    comp = {"C": 0.15, "Mn": 0.25, "Ni": 2.75, "Cr": 1.40, "Mo": 0.40}
    props = {"yield_strength_mpa": 600.0, "charpy_impact_energy_j": 65.0}
    res = check_military_specifications(comp, props)

    assert "MIL-S-16216 (HY-80)" in res["specifications"]
    hy80_res = res["specifications"]["MIL-S-16216 (HY-80)"]
    assert hy80_res["status"] == "COMPLIANT"

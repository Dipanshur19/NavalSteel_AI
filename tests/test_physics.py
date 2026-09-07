"""Tests for the physics-informed metallurgical engine."""
from src.physics import (
    calculate_carbon_equivalent_iiw,
    calculate_pcm,
    calculate_martensite_start,
    calculate_bainite_start,
    evaluate_steel_physics,
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

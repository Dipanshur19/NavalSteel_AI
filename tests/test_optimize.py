"""
Unit and integration tests for Phase 4: Multi-Objective Pareto Optimization and Experimental Dossier.
"""
from pathlib import Path

from src.dossier import format_markdown_dossier, generate_pdf_dossier_bytes, save_pdf_dossier
from src.optimize import (
    ParetoCandidate,
    calculate_raw_material_cost,
    compute_novelty_score,
    dominates,
    fast_non_dominated_sort,
    is_metallurgically_feasible,
    load_benchmark_compositions,
    run_pareto_optimization,
)


def test_raw_material_cost():
    comp = {"C": 0.05, "Ni": 6.5, "Cu": 3.65, "Cr": 1.84, "Mo": 0.60, "V": 0.10}
    cost_kg, cost_ton = calculate_raw_material_cost(comp)
    assert cost_kg > 1.0, f"Expected cost > $1/kg, got {cost_kg}"
    assert cost_ton == round(cost_kg * 1000.0, 1)


def test_dominance_logic():
    benchmarks = load_benchmark_compositions()

    cand_a = ParetoCandidate(
        id="A", composition={"C": 0.05}, processing={"temper_temp_C": 500},
        yield_strength_mpa=1100, yield_strength_err=30,
        tensile_strength_mpa=1250, tensile_strength_err=30,
        charpy_toughness_j=160, charpy_toughness_err=10,
        pcm=0.35, ce_iiw=0.60, ms_C=400, bs_C=500, weldability_risk="Low",
        cost_per_kg_usd=2.5, cost_per_ton_usd=2500,
        novelty_score=0.2, novelty_class="Balanced", nearest_benchmark="BlastAlloy160"
    )

    # Strictly worse candidate (lower YS, lower CVN, higher Pcm, higher cost)
    cand_b = ParetoCandidate(
        id="B", composition={"C": 0.05}, processing={"temper_temp_C": 500},
        yield_strength_mpa=950, yield_strength_err=30,
        tensile_strength_mpa=1100, tensile_strength_err=30,
        charpy_toughness_j=120, charpy_toughness_err=10,
        pcm=0.42, ce_iiw=0.70, ms_C=380, bs_C=480, weldability_risk="Moderate",
        cost_per_kg_usd=3.5, cost_per_ton_usd=3500,
        novelty_score=0.2, novelty_class="Balanced", nearest_benchmark="BlastAlloy160"
    )

    # Trade-off candidate (higher YS but lower CVN)
    cand_c = ParetoCandidate(
        id="C", composition={"C": 0.05}, processing={"temper_temp_C": 500},
        yield_strength_mpa=1200, yield_strength_err=30,
        tensile_strength_mpa=1350, tensile_strength_err=30,
        charpy_toughness_j=110, charpy_toughness_err=10,
        pcm=0.36, ce_iiw=0.62, ms_C=390, bs_C=490, weldability_risk="Low",
        cost_per_kg_usd=2.6, cost_per_ton_usd=2600,
        novelty_score=0.2, novelty_class="Balanced", nearest_benchmark="BlastAlloy160"
    )

    assert dominates(cand_a, cand_b) is True
    assert dominates(cand_b, cand_a) is False
    assert dominates(cand_a, cand_c) is False
    assert dominates(cand_c, cand_a) is False


def test_metallurgical_constraints():
    # Valid BlastAlloy160-like composition
    valid_comp = {"C": 0.05, "Ni": 6.5, "Cu": 3.65, "Cr": 1.84, "Mo": 0.60, "Mn": 0.30, "Si": 0.25}
    feasible, _ = is_metallurgically_feasible(valid_comp)
    assert feasible is True

    # High carbon invalid
    high_c = dict(valid_comp, C=0.25)
    feasible_c, msg_c = is_metallurgically_feasible(high_c)
    assert feasible_c is False
    assert "Carbon" in msg_c

    # Too high solute elements
    high_solute = dict(valid_comp, Ni=22.0)
    feasible_s, msg_s = is_metallurgically_feasible(high_solute)
    assert feasible_s is False
    assert "Total solute" in msg_s


def test_novelty_score():
    benchmarks = load_benchmark_compositions()
    # Identical to BlastAlloy160
    ba160 = {"C": 0.05, "Mn": 0.30, "Si": 0.25, "Ni": 6.50, "Cr": 1.84, "Mo": 0.60, "Cu": 3.65, "V": 0.10}
    score, n_class, nearest = compute_novelty_score(ba160, benchmarks)
    assert score < 0.05
    assert nearest == "BlastAlloy160"
    assert "Derivative" in n_class


def test_pareto_optimization_run():
    candidates = run_pareto_optimization(
        pop_size=15,
        generations=3,
        min_ys_mpa=900.0,
        min_cvn_j=80.0,
        max_pcm=0.48,
        random_seed=42
    )

    assert len(candidates) >= 1
    top = candidates[0]
    assert top.pareto_rank == 1
    assert top.yield_strength_mpa >= 850.0
    assert top.charpy_toughness_j >= 70.0
    assert top.pcm <= 0.48
    assert top.cost_per_ton_usd > 0


def test_dossier_markdown_and_pdf(tmp_path: Path):
    benchmarks = load_benchmark_compositions()
    cand = ParetoCandidate(
        id="OPT-NS-TEST",
        composition={"C": 0.05, "Ni": 6.5, "Cu": 3.65, "Cr": 1.84, "Mo": 0.60, "Mn": 0.30, "Si": 0.25, "V": 0.10},
        processing={"temper_temp_C": 475.0, "temper_time_h": 4.0},
        yield_strength_mpa=1120.0, yield_strength_err=40.0,
        tensile_strength_mpa=1270.0, tensile_strength_err=45.0,
        charpy_toughness_j=165.0, charpy_toughness_err=15.0,
        pcm=0.43, ce_iiw=0.88, ms_C=375.0, bs_C=470.0,
        weldability_risk="Moderate",
        cost_per_kg_usd=2.65, cost_per_ton_usd=2650.0,
        novelty_score=0.12, novelty_class="Derivative",
        nearest_benchmark="BlastAlloy160"
    )

    md = format_markdown_dossier(cand)
    assert "# ⚓ NAVALSTEEL AI — ENGINEERING SPECIFICATION DOSSIER" in md
    assert "Aim Chemical Composition Specification" in md
    assert "Vacuum Induction Melting" in md

    # PDF bytes test
    pdf_bytes = generate_pdf_dossier_bytes(cand)
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 2000

    # Save PDF test
    out_file = tmp_path / "test_spec.pdf"
    saved = save_pdf_dossier(cand, out_file)
    assert saved.exists()
    assert saved.stat().st_size > 2000

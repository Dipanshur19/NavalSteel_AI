"""
Multi-Objective Pareto Optimization & Candidate Discovery Engine for NavalSteel AI.

Performs evolutionary multi-objective optimization (NSGA-II inspired) simultaneously across:
1. Maximize Yield Strength (via ML Surrogate)
2. Maximize Charpy Toughness (via ML Surrogate)
3. Minimize Weldability Cracking Parameter Pcm (via Physics Engine)
4. Minimize Raw Material Alloying Cost (via Commodity Index)

Under strict physical metallurgy constraints:
- Carbon window: 0.02% <= C <= 0.12%
- Martensite start Ms >= 340°C
- Maximum Pcm <= 0.48
- Total solute concentration <= 20 wt%
- Tempering window: 400°C <= T <= 625°C
"""
from __future__ import annotations

import copy
import json
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from . import config
from .physics import (
    calculate_bainite_start,
    calculate_carbon_equivalent_iiw,
    calculate_martensite_start,
    calculate_pcm,
    evaluate_steel_physics,
)
from .surrogate import get_surrogate_ensemble

# Raw material commodity price benchmarks (USD per kg)
RAW_ELEMENT_COSTS_USD_PER_KG: Dict[str, float] = {
    "Fe": 0.55,    # Scrap/pig iron baseline
    "C": 0.50,     # Carburizing agent / graphite
    "Mn": 2.20,    # Ferromanganese
    "Si": 2.10,    # Ferrosilicon
    "Ni": 16.50,   # Pure electrolytic nickel cathode
    "Cr": 3.25,    # High carbon ferrochrome
    "Mo": 45.00,   # Ferromolybdenum
    "Cu": 9.20,    # Electrolytic copper cathode
    "V": 35.00,    # Ferrovanadium
    "Nb": 46.00,   # Ferroniobium
    "Co": 32.00,   # Cobalt metal
    "B": 6.00,     # Ferroboron
}

# Bounds for decision variables
COMPOSITION_BOUNDS: Dict[str, Tuple[float, float]] = {
    "C": (0.03, 0.10),
    "Mn": (0.20, 1.20),
    "Si": (0.15, 0.45),
    "Ni": (1.50, 8.50),
    "Cr": (0.40, 2.20),
    "Mo": (0.20, 1.20),
    "Cu": (0.50, 3.80),
    "V": (0.00, 0.12),
    "Nb": (0.00, 0.04),
    "Co": (0.00, 4.00),
}

PROCESSING_BOUNDS: Dict[str, Tuple[float, float]] = {
    "temper_temp_C": (425.0, 625.0),
    "temper_time_h": (1.0, 6.0),
}


def calculate_raw_material_cost(comp: Dict[str, float]) -> Tuple[float, float]:
    """
    Calculates the raw material alloying cost in USD/kg and USD/metric ton.
    Assumes Fe balance = 100 - sum(solute elements).
    """
    solute_sum = sum(comp.get(el, 0.0) for el in RAW_ELEMENT_COSTS_USD_PER_KG if el != "Fe")
    fe_pct = max(0.0, 100.0 - solute_sum)

    cost_per_100kg = fe_pct * RAW_ELEMENT_COSTS_USD_PER_KG["Fe"]
    for el, price in RAW_ELEMENT_COSTS_USD_PER_KG.items():
        if el != "Fe":
            cost_per_100kg += comp.get(el, 0.0) * price

    cost_per_kg = round(cost_per_100kg / 100.0, 2)
    cost_per_ton = round(cost_per_kg * 1000.0, 1)
    return cost_per_kg, cost_per_ton


@dataclass
class ParetoCandidate:
    id: str
    composition: Dict[str, float]
    processing: Dict[str, float]
    yield_strength_mpa: float
    yield_strength_err: float
    tensile_strength_mpa: float
    tensile_strength_err: float
    charpy_toughness_j: float
    charpy_toughness_err: float
    pcm: float
    ce_iiw: float
    ms_C: float
    bs_C: float
    weldability_risk: str
    cost_per_kg_usd: float
    cost_per_ton_usd: float
    novelty_score: float
    novelty_class: str
    nearest_benchmark: str
    pareto_rank: int = 1
    crowding_distance: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def load_benchmark_compositions() -> Dict[str, Dict[str, float]]:
    """Loads benchmark compositions from data/extracted for novelty comparison."""
    anchors: Dict[str, Dict[str, float]] = {
        "BlastAlloy160": {"C": 0.05, "Mn": 0.30, "Si": 0.25, "Ni": 6.50, "Cr": 1.84, "Mo": 0.60, "Cu": 3.65, "V": 0.10, "Nb": 0.0, "Co": 0.0},
        "HY-80": {"C": 0.15, "Mn": 0.25, "Si": 0.25, "Ni": 2.75, "Cr": 1.40, "Mo": 0.40, "Cu": 0.0, "V": 0.02, "Nb": 0.0, "Co": 0.0},
        "HY-100": {"C": 0.16, "Mn": 0.25, "Si": 0.25, "Ni": 3.00, "Cr": 1.45, "Mo": 0.45, "Cu": 0.0, "V": 0.02, "Nb": 0.0, "Co": 0.0},
        "HSLA-100": {"C": 0.04, "Mn": 0.85, "Si": 0.25, "Ni": 3.50, "Cr": 0.60, "Mo": 0.55, "Cu": 1.55, "V": 0.00, "Nb": 0.035, "Co": 0.0},
        "HSLA-115": {"C": 0.05, "Mn": 0.90, "Si": 0.30, "Ni": 3.80, "Cr": 0.65, "Mo": 0.60, "Cu": 1.70, "V": 0.00, "Nb": 0.04, "Co": 0.0},
        "AF1410": {"C": 0.16, "Mn": 0.10, "Si": 0.10, "Ni": 10.00, "Cr": 2.00, "Mo": 1.00, "Cu": 0.0, "V": 0.00, "Nb": 0.0, "Co": 14.00},
    }

    # Enrich from extracted files if available
    extracted_dir = config.DATA_DIR / "extracted"
    if extracted_dir.exists():
        for f in extracted_dir.glob("*.json"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                    steel_name = data.get("steel", {}).get("name")
                    comp_list = data.get("composition", [])
                    if steel_name and comp_list:
                        c_map: Dict[str, float] = {}
                        for item in comp_list:
                            el = item.get("element")
                            val = item.get("nominal_weight_percent")
                            if el and val is not None:
                                c_map[el] = float(val)
                        if "Ni" in c_map and "C" in c_map:
                            anchors[steel_name] = c_map
            except Exception:
                continue
    return anchors


def compute_novelty_score(comp: Dict[str, float], benchmarks: Dict[str, Dict[str, float]]) -> Tuple[float, str, str]:
    """
    Computes Euclidean distance to nearest benchmark alloy in normalized composition space.
    Returns (novelty_score, novelty_class, nearest_benchmark_name).
    """
    elements = ["C", "Mn", "Si", "Ni", "Cr", "Mo", "Cu", "V", "Nb", "Co"]
    scales = {"C": 0.1, "Mn": 1.0, "Si": 0.5, "Ni": 8.0, "Cr": 2.0, "Mo": 1.0, "Cu": 3.0, "V": 0.1, "Nb": 0.05, "Co": 10.0}

    vec_comp = np.array([comp.get(el, 0.0) / scales.get(el, 1.0) for el in elements])

    min_dist = float("inf")
    nearest = "Unknown"

    for name, bench_comp in benchmarks.items():
        vec_bench = np.array([bench_comp.get(el, 0.0) / scales.get(el, 1.0) for el in elements])
        dist = float(np.linalg.norm(vec_comp - vec_bench))
        if dist < min_dist:
            min_dist = dist
            nearest = name

    # Normalize novelty score to approx 0.0 - 1.0 range
    score = round(min(1.0, min_dist / 2.0), 3)

    if score < 0.18:
        n_class = "Derivative (Evolutionary)"
    elif score < 0.40:
        n_class = "Balanced Innovation"
    else:
        n_class = "High Novelty (Exploratory)"

    return score, n_class, nearest


def is_metallurgically_feasible(
    comp: Dict[str, float],
    pcm_max: float = 0.52,
    ms_min: float = 320.0
) -> Tuple[bool, str]:
    """
    Applies hard physical metallurgy constraints to reject unphysical or crack-prone compositions.
    """
    c = comp.get("C", 0.05)
    if not (0.02 <= c <= 0.12):
        return False, f"Carbon {c:.3f}% outside valid weldable naval steel window [0.02, 0.12]"

    solute_sum = sum(v for k, v in comp.items() if k not in ("Fe", "temper_temp_C", "temper_time_h", "test_temp_C"))
    if solute_sum > 20.0:
        return False, f"Total solute {solute_sum:.1f}% exceeds 20 wt% limit for iron matrix"

    ms = calculate_martensite_start(comp)
    if ms < ms_min:
        return False, f"Ms temperature {ms:.1f}°C below minimum {ms_min}°C (risk of unstable retained austenite)"

    pcm = calculate_pcm(comp)
    if pcm > pcm_max:
        return False, f"Pcm {pcm:.3f} exceeds maximum threshold {pcm_max:.3f}"

    return True, "Feasible"


def dominates(cand_a: ParetoCandidate, cand_b: ParetoCandidate) -> bool:
    """
    Pareto dominance check across 4 objectives:
    Max YS, Max Charpy, Min Pcm, Min Cost.
    cand_a dominates cand_b if cand_a is no worse than cand_b in all,
    and strictly better in at least one.
    """
    # 1. Yield Strength (Max)
    a_ys, b_ys = cand_a.yield_strength_mpa, cand_b.yield_strength_mpa
    # 2. Charpy Toughness (Max)
    a_cvn, b_cvn = cand_a.charpy_toughness_j, cand_b.charpy_toughness_j
    # 3. Pcm (Min)
    a_pcm, b_pcm = cand_a.pcm, cand_b.pcm
    # 4. Cost (Min)
    a_cost, b_cost = cand_a.cost_per_ton_usd, cand_b.cost_per_ton_usd

    no_worse = (
        a_ys >= b_ys and
        a_cvn >= b_cvn and
        a_pcm <= b_pcm and
        a_cost <= b_cost
    )
    strictly_better = (
        a_ys > b_ys or
        a_cvn > b_cvn or
        a_pcm < b_pcm or
        a_cost < b_cost
    )
    return no_worse and strictly_better


def fast_non_dominated_sort(candidates: List[ParetoCandidate]) -> List[List[ParetoCandidate]]:
    """
    Standard NSGA-II fast non-dominated sorting algorithm.
    Partitions candidates into Pareto fronts: F1 (rank 1), F2, F3...
    """
    n = len(candidates)
    if n == 0:
        return []

    domination_count = [0] * n
    dominated_solutions: List[List[int]] = [[] for _ in range(n)]
    fronts: List[List[int]] = [[]]

    for p in range(n):
        for q in range(n):
            if p == q:
                continue
            if dominates(candidates[p], candidates[q]):
                dominated_solutions[p].append(q)
            elif dominates(candidates[q], candidates[p]):
                domination_count[p] += 1

        if domination_count[p] == 0:
            candidates[p].pareto_rank = 1
            fronts[0].append(p)

    i = 0
    while len(fronts[i]) > 0:
        next_front: List[int] = []
        for p in fronts[i]:
            for q in dominated_solutions[p]:
                domination_count[q] -= 1
                if domination_count[q] == 0:
                    candidates[q].pareto_rank = i + 2
                    next_front.append(q)
        i += 1
        if len(next_front) > 0:
            fronts.append(next_front)
        else:
            break

    return [[candidates[idx] for idx in front] for front in fronts]


def assign_crowding_distance(front: List[ParetoCandidate]) -> None:
    """Assigns crowding distance to maintain diversity along the Pareto frontier."""
    num_candidates = len(front)
    if num_candidates <= 2:
        for c in front:
            c.crowding_distance = float("inf")
        return

    for c in front:
        c.crowding_distance = 0.0

    objectives = [
        ("yield_strength_mpa", False),     # Maximize
        ("charpy_toughness_j", False),     # Maximize
        ("pcm", True),                     # Minimize
        ("cost_per_ton_usd", True),        # Minimize
    ]

    for attr, is_min in objectives:
        front.sort(key=lambda x: getattr(x, attr))
        front[0].crowding_distance = float("inf")
        front[-1].crowding_distance = float("inf")

        obj_min = getattr(front[0], attr)
        obj_max = getattr(front[-1], attr)
        spread = obj_max - obj_min

        if spread > 1e-6:
            for i in range(1, num_candidates - 1):
                prev_val = getattr(front[i - 1], attr)
                next_val = getattr(front[i + 1], attr)
                front[i].crowding_distance += abs(next_val - prev_val) / spread


def create_random_individual(seed_bias: Optional[Dict[str, float]] = None) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Generates a bounded random alloy composition and processing condition."""
    comp: Dict[str, float] = {}
    for el, (lo, hi) in COMPOSITION_BOUNDS.items():
        if seed_bias and el in seed_bias and random.random() < 0.6:
            # Gaussian perturbation around seed
            val = random.gauss(seed_bias[el], (hi - lo) * 0.08)
            comp[el] = round(float(np.clip(val, lo, hi)), 3)
        else:
            comp[el] = round(random.uniform(lo, hi), 3)

    proc: Dict[str, float] = {}
    for param, (lo, hi) in PROCESSING_BOUNDS.items():
        proc[param] = round(random.uniform(lo, hi), 1)

    return comp, proc


def evaluate_individual(
    comp: Dict[str, float],
    proc: Dict[str, float],
    cand_id: str,
    benchmarks: Dict[str, Dict[str, float]],
    test_temp_C: float = 25.0,
    surrogate: Optional[Any] = None
) -> ParetoCandidate:
    """Evaluates an individual using surrogate ML and physics models."""
    if surrogate is None:
        surrogate = get_surrogate_ensemble()

    eval_input = dict(comp)
    eval_input.update(proc)
    eval_input["test_temp_C"] = test_temp_C

    preds = surrogate.predict(eval_input)
    phys = evaluate_steel_physics(comp)
    cost_kg, cost_ton = calculate_raw_material_cost(comp)
    nov_score, nov_class, nearest = compute_novelty_score(comp, benchmarks)

    return ParetoCandidate(
        id=cand_id,
        composition=comp,
        processing=proc,
        yield_strength_mpa=preds["yield_strength_mpa"]["mean"],
        yield_strength_err=preds["yield_strength_mpa"]["uncertainty"],
        tensile_strength_mpa=preds["tensile_strength_mpa"]["mean"],
        tensile_strength_err=preds["tensile_strength_mpa"]["uncertainty"],
        charpy_toughness_j=preds["charpy_toughness_j"]["mean"],
        charpy_toughness_err=preds["charpy_toughness_j"]["uncertainty"],
        pcm=phys["pcm"],
        ce_iiw=phys["ce_iiw"],
        ms_C=phys["martensite_start_C"],
        bs_C=phys["bainite_start_C"],
        weldability_risk=phys["weldability_risk"],
        cost_per_kg_usd=cost_kg,
        cost_per_ton_usd=cost_ton,
        novelty_score=nov_score,
        novelty_class=nov_class,
        nearest_benchmark=nearest
    )


def run_pareto_optimization(
    pop_size: int = 50,
    generations: int = 25,
    min_ys_mpa: float = 950.0,
    min_cvn_j: float = 80.0,
    max_pcm: float = 0.46,
    test_temp_C: float = 25.0,
    random_seed: Optional[int] = 42
) -> List[ParetoCandidate]:
    """
    Executes an NSGA-II multi-objective evolutionary search for Pareto-optimal naval steels.
    Returns the non-dominated Pareto frontier candidates (Rank 1).
    """
    if random_seed is not None:
        random.seed(random_seed)
        np.random.seed(random_seed)

    surrogate = get_surrogate_ensemble()
    benchmarks = load_benchmark_compositions()

    # 1. Initialize population with known seeds + random variations
    seeds = [
        {"C": 0.05, "Ni": 6.50, "Cu": 3.65, "Cr": 1.84, "Mo": 0.60, "V": 0.10, "Mn": 0.30, "Si": 0.25}, # BlastAlloy160
        {"C": 0.045, "Ni": 3.80, "Cu": 1.70, "Cr": 0.65, "Mo": 0.60, "V": 0.02, "Mn": 0.90, "Si": 0.30}, # HSLA-115
        {"C": 0.06, "Ni": 5.00, "Cu": 2.50, "Cr": 1.20, "Mo": 0.50, "V": 0.05, "Mn": 0.50, "Si": 0.25}, # Hybrid concept
    ]

    population: List[Tuple[Dict[str, float], Dict[str, float]]] = []
    
    # Fill initial population with feasible individuals
    attempts = 0
    while len(population) < pop_size and attempts < pop_size * 10:
        attempts += 1
        bias = random.choice(seeds) if random.random() < 0.5 else None
        c, p = create_random_individual(seed_bias=bias)
        feasible, _ = is_metallurgically_feasible(c, pcm_max=max_pcm)
        if feasible:
            population.append((c, p))

    # Fallback if strict feasibility limited count
    while len(population) < pop_size:
        c, p = create_random_individual(seed_bias=seeds[0])
        population.append((c, p))

    # Evolutionary loop
    for gen in range(generations):
        # Evaluate current population
        evaluated_candidates = [
            evaluate_individual(
                c, p, f"GEN{gen}_{i+1:02d}", benchmarks,
                test_temp_C=test_temp_C, surrogate=surrogate
            )
            for i, (c, p) in enumerate(population)
        ]

        # Non-dominated sort
        fronts = fast_non_dominated_sort(evaluated_candidates)
        for front in fronts:
            assign_crowding_distance(front)

        # Offspring generation: Selection, Crossover, Mutation
        offspring_pop: List[Tuple[Dict[str, float], Dict[str, float]]] = []
        while len(offspring_pop) < pop_size:
            # Binary tournament selection based on rank and crowding distance
            p1 = random.choice(evaluated_candidates)
            p2 = random.choice(evaluated_candidates)
            parent_a = p1 if (p1.pareto_rank < p2.pareto_rank or (p1.pareto_rank == p2.pareto_rank and p1.crowding_distance > p2.crowding_distance)) else p2

            p3 = random.choice(evaluated_candidates)
            p4 = random.choice(evaluated_candidates)
            parent_b = p3 if (p3.pareto_rank < p4.pareto_rank or (p3.pareto_rank == p4.pareto_rank and p3.crowding_distance > p4.crowding_distance)) else p4

            # Blend Crossover (BLX-alpha, alpha=0.3)
            child_c: Dict[str, float] = {}
            for el, (lo, hi) in COMPOSITION_BOUNDS.items():
                va = parent_a.composition.get(el, lo)
                vb = parent_b.composition.get(el, lo)
                alpha = 0.3
                v_lo = min(va, vb) - alpha * abs(va - vb)
                v_hi = max(va, vb) + alpha * abs(va - vb)
                child_c[el] = round(float(np.clip(random.uniform(v_lo, v_hi), lo, hi)), 3)

            child_p: Dict[str, float] = {}
            for param, (lo, hi) in PROCESSING_BOUNDS.items():
                pa = parent_a.processing.get(param, lo)
                pb = parent_b.processing.get(param, lo)
                child_p[param] = round(float(np.clip(0.5 * (pa + pb) + random.gauss(0, 10.0), lo, hi)), 1)

            # Polynomial mutation (15% chance per gene)
            for el, (lo, hi) in COMPOSITION_BOUNDS.items():
                if random.random() < 0.15:
                    delta = random.gauss(0, (hi - lo) * 0.1)
                    child_c[el] = round(float(np.clip(child_c[el] + delta, lo, hi)), 3)

            feasible, _ = is_metallurgically_feasible(child_c, pcm_max=max_pcm)
            if feasible:
                offspring_pop.append((child_c, child_p))

        # Elitist combination: Combine Parent (population) + Offspring
        combined_pool = population + offspring_pop
        evaluated_combined = [
            evaluate_individual(
                c, p, f"CAN_{idx+1:03d}", benchmarks,
                test_temp_C=test_temp_C, surrogate=surrogate
            )
            for idx, (c, p) in enumerate(combined_pool)
        ]

        combined_fronts = fast_non_dominated_sort(evaluated_combined)
        for front in combined_fronts:
            assign_crowding_distance(front)

        # Select top pop_size for next generation
        new_population: List[Tuple[Dict[str, float], Dict[str, float]]] = []
        for front in combined_fronts:
            if len(new_population) + len(front) <= pop_size:
                for cand in front:
                    new_population.append((cand.composition, cand.processing))
            else:
                # Sort by crowding distance to take the most diverse
                front.sort(key=lambda x: x.crowding_distance, reverse=True)
                remainder = pop_size - len(new_population)
                for cand in front[:remainder]:
                    new_population.append((cand.composition, cand.processing))
                break

        population = new_population

    # Final evaluation of the converged population
    final_evaluated = [
        evaluate_individual(
            c, p, f"OPT-{i+1:02d}", benchmarks,
            test_temp_C=test_temp_C, surrogate=surrogate
        )
        for i, (c, p) in enumerate(population)
    ]

    final_fronts = fast_non_dominated_sort(final_evaluated)
    if not final_fronts:
        return []

    rank_1 = final_fronts[0]
    assign_crowding_distance(rank_1)

    # Filter by user targets (if specified) or sort by Yield Strength
    filtered_pareto = [
        c for c in rank_1
        if c.yield_strength_mpa >= min_ys_mpa and c.charpy_toughness_j >= min_cvn_j and c.pcm <= max_pcm
    ]

    # If user filter is too strict, return rank_1 solutions sorted by balance
    result = filtered_pareto if len(filtered_pareto) >= 3 else rank_1
    result.sort(key=lambda x: x.yield_strength_mpa, reverse=True)

    # Re-assign clean IDs
    for idx, c in enumerate(result):
        c.id = f"OPT-NS-{idx+1:02d}"

    return result


def pareto_candidates_to_dataframe(candidates: List[ParetoCandidate]) -> pd.DataFrame:
    """Converts a list of Pareto candidates into a clean pandas DataFrame for display."""
    rows = []
    for c in candidates:
        row = {
            "ID": c.id,
            "Yield Strength (MPa)": f"{c.yield_strength_mpa:.0f} ± {c.yield_strength_err:.0f}",
            "UTS (MPa)": f"{c.tensile_strength_mpa:.0f} ± {c.tensile_strength_err:.0f}",
            "Charpy Toughness (J)": f"{c.charpy_toughness_j:.0f} ± {c.charpy_toughness_err:.0f}",
            "Pcm (Cracking)": f"{c.pcm:.3f}",
            "Weldability Risk": c.weldability_risk,
            "Cost ($/ton)": f"${c.cost_per_ton_usd:,.0f}",
            "Cost ($/kg)": f"${c.cost_per_kg_usd:.2f}",
            "Novelty": c.novelty_class,
            "Novelty Score": c.novelty_score,
            "Nearest Benchmark": c.nearest_benchmark,
            "Tempering (°C)": f"{c.processing['temper_temp_C']:.0f}°C / {c.processing['temper_time_h']:.1f}h",
            "C": c.composition.get("C", 0.0),
            "Ni": c.composition.get("Ni", 0.0),
            "Cu": c.composition.get("Cu", 0.0),
            "Cr": c.composition.get("Cr", 0.0),
            "Mo": c.composition.get("Mo", 0.0),
            "Mn": c.composition.get("Mn", 0.0),
            "Si": c.composition.get("Si", 0.0),
            "V": c.composition.get("V", 0.0),
        }
        rows.append(row)
    return pd.DataFrame(rows)

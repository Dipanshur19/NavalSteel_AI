"""Tests for the Design Agent and candidate alloy generator."""
from src.design import find_nearest_experimental_neighbors, generate_candidate_design


def test_find_nearest_experimental_neighbors():
    # Searching near BlastAlloy160 (1100 MPa, 176 J)
    neighbors = find_nearest_experimental_neighbors(target_ys_mpa=1100.0, target_charpy_j=176.0)
    assert len(neighbors) > 0
    # BlastAlloy160 should be among top neighbors
    names = [n["record"]["steel"]["name"] for n in neighbors]
    assert any("BlastAlloy160" in name for name in names)


def test_generate_candidate_design_dry_run():
    candidate = generate_candidate_design(
        target_ys_mpa=1100.0,
        target_charpy_j=130.0,
        candidate_id="Candidate NS-01",
        dry_run=True,
    )
    assert candidate["candidate_id"] == "Candidate NS-01"
    assert candidate["status"] == "COMPUTATIONAL HYPOTHESIS; NOT EXPERIMENTALLY VALIDATED"
    assert "composition_wt_pct" in candidate
    assert candidate["composition_wt_pct"]["C"] <= 0.06  # Low carbon constraint
    assert candidate["weldability"]["pcm"] < 0.50
    assert len(candidate["nearest_experimental_neighbors"]) > 0

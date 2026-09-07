"""Tests for the unit normalization engine."""
from src.normalize import (
    canonical_element_symbol,
    normalize_pressure_or_strength,
    normalize_impact_energy,
    normalize_temperature,
    enrich_text_with_normalized_units,
)


def test_canonical_element_symbol():
    assert canonical_element_symbol("carbon") == "C"
    assert canonical_element_symbol("nickel") == "Ni"
    assert canonical_element_symbol("copper") == "Cu"
    assert canonical_element_symbol("FE") == "Fe"
    assert canonical_element_symbol("Mo") == "Mo"


def test_normalize_pressure_or_strength():
    res = normalize_pressure_or_strength(160.0, "ksi")
    assert res["ksi"] == 160.0
    assert 1100 <= res["mpa"] <= 1105

    res2 = normalize_pressure_or_strength(1100.0, "MPa")
    assert res2["mpa"] == 1100.0
    assert 159 <= res2["ksi"] <= 160


def test_normalize_impact_energy():
    res = normalize_impact_energy(130.0, "ft-lb")
    assert res["ft_lb"] == 130.0
    assert 175 <= res["joules"] <= 177

    res2 = normalize_impact_energy(176.0, "J")
    assert res2["joules"] == 176.0
    assert 129 <= res2["ft_lb"] <= 130


def test_normalize_temperature():
    res = normalize_temperature(900.0, "C")
    assert res["celsius"] == 900.0
    assert res["fahrenheit"] == 1652.0

    res2 = normalize_temperature(-40.0, "C")
    assert res2["celsius"] == -40.0
    assert res2["fahrenheit"] == -40.0


def test_enrich_text_with_normalized_units():
    text = "Yield strength was 160 ksi and Charpy toughness was 130 ft-lb."
    enriched = enrich_text_with_normalized_units(text)
    assert "160 ksi (1103 MPa)" in enriched
    assert "130 ft-lb (176 J)" in enriched

"""Tests for the Machine Learning Surrogate Predictor Layer."""
from src.surrogate import get_surrogate_ensemble, extract_features_from_dict


def test_surrogate_training_and_metrics():
    surrogate = get_surrogate_ensemble()
    assert surrogate.is_trained
    assert "yield_strength_mpa" in surrogate.metrics
    assert "charpy_toughness_j" in surrogate.metrics

    # Check high R2 performance on naval steels dataset
    ys_r2 = surrogate.metrics["yield_strength_mpa"]["cv_r2"]
    cvn_r2 = surrogate.metrics["charpy_toughness_j"]["cv_r2"]
    assert ys_r2 > 0.80, f"YS R2 was {ys_r2}"
    assert cvn_r2 > 0.75, f"Charpy R2 was {cvn_r2}"


def test_surrogate_predict_blastalloy160():
    surrogate = get_surrogate_ensemble()
    comp = {
        "C": 0.05, "Ni": 6.5, "Cu": 3.65, "Cr": 1.84, "Mo": 0.60, "V": 0.10,
        "temper_temp_C": 475.0, "temper_time_h": 4.0, "test_temp_C": 25.0
    }
    preds = surrogate.predict(comp)

    # Concept B prototype achieves ~1100 MPa and 176 J
    ys_mean = preds["yield_strength_mpa"]["mean"]
    cvn_mean = preds["charpy_toughness_j"]["mean"]

    assert 1000 <= ys_mean <= 1200
    assert 120 <= cvn_mean <= 200
    assert preds["yield_strength_mpa"]["uncertainty"] > 0.0


def test_isochronal_tempering_curve():
    surrogate = get_surrogate_ensemble()
    comp = {"C": 0.05, "Ni": 6.5, "Cu": 3.65, "Cr": 1.84, "Mo": 0.60, "V": 0.10}
    df_curve = surrogate.predict_isochronal_tempering_curve(comp, temp_min_C=400.0, temp_max_C=650.0, step_C=50.0)

    assert len(df_curve) == 6
    assert "Yield Strength (MPa)" in df_curve.columns
    assert "Charpy Toughness (J)" in df_curve.columns

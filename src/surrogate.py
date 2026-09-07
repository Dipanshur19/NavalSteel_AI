"""
Machine Learning Surrogate Predictor Layer for NavalSteel AI.

Trains physics-informed ensemble regressors (Gradient Boosting & Random Forest)
on composition, derived metallurgical parameters (Pcm, CE, Ms, Bs),
and heat-treatment conditions to predict Yield Strength, UTS, and Charpy Toughness
with calibrated uncertainty bounds.
"""
from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import KFold

from . import config
from .physics import calculate_bainite_start, calculate_carbon_equivalent_iiw, calculate_martensite_start, calculate_pcm

DATASET_PATH = config.DATA_DIR / "dataset" / "naval_steels_dataset.csv"
MODEL_PATH = config.DATA_DIR / "models" / "surrogate_ensemble.pkl"

FEATURE_COLS = [
    "C", "Mn", "Si", "Ni", "Cr", "Mo", "Cu", "V", "Nb", "Co",
    "pcm", "ce_iiw", "ms_C", "bs_C",
    "temper_temp_C", "temper_time_h", "test_temp_C"
]

TARGET_COLS = ["yield_strength_mpa", "tensile_strength_mpa", "charpy_toughness_j"]


def extract_features_from_dict(comp_and_proc: Dict[str, Any]) -> pd.DataFrame:
    """Takes a dictionary with composition and processing values and computes
    derived physical parameters (Pcm, CE, Ms, Bs) to match the model schema."""
    c = float(comp_and_proc.get("C", 0.05))
    mn = float(comp_and_proc.get("Mn", 0.30))
    si = float(comp_and_proc.get("Si", 0.25))
    ni = float(comp_and_proc.get("Ni", 0.0))
    cr = float(comp_and_proc.get("Cr", 0.0))
    mo = float(comp_and_proc.get("Mo", 0.0))
    cu = float(comp_and_proc.get("Cu", 0.0))
    v = float(comp_and_proc.get("V", 0.0))
    nb = float(comp_and_proc.get("Nb", 0.0))
    co = float(comp_and_proc.get("Co", 0.0))
    b = float(comp_and_proc.get("B", 0.0))

    comp_dict = {"C": c, "Mn": mn, "Si": si, "Ni": ni, "Cr": cr, "Mo": mo, "Cu": cu, "V": v, "Nb": nb, "Co": co, "B": b}

    # Derived physics features
    pcm = calculate_pcm(comp_dict)
    ce = calculate_carbon_equivalent_iiw(comp_dict)
    ms = calculate_martensite_start(comp_dict)
    bs = calculate_bainite_start(comp_dict)

    t_temper = float(comp_and_proc.get("temper_temp_C", 500.0))
    time_temper = float(comp_and_proc.get("temper_time_h", 2.0))
    t_test = float(comp_and_proc.get("test_temp_C", 25.0))

    row = {
        "C": c, "Mn": mn, "Si": si, "Ni": ni, "Cr": cr, "Mo": mo, "Cu": cu, "V": v, "Nb": nb, "Co": co,
        "pcm": pcm, "ce_iiw": ce, "ms_C": ms, "bs_C": bs,
        "temper_temp_C": t_temper, "temper_time_h": time_temper, "test_temp_C": t_test
    }
    return pd.DataFrame([row])[FEATURE_COLS]


class SurrogateModelEnsemble:
    """Multi-target ensemble regressor for metallurgical property prediction."""

    def __init__(self):
        self.models: Dict[str, Dict[str, Any]] = {}
        self.metrics: Dict[str, Dict[str, float]] = {}
        self.is_trained = False

    def train(self, csv_path: Path = DATASET_PATH) -> Dict[str, Dict[str, float]]:
        df = pd.read_csv(csv_path)

        # Compute derived physics features for training set
        derived_pcm = []
        derived_ce = []
        derived_ms = []
        derived_bs = []

        for _, row in df.iterrows():
            comp = {
                "C": row["C"], "Mn": row["Mn"], "Si": row["Si"], "Ni": row["Ni"],
                "Cr": row["Cr"], "Mo": row["Mo"], "Cu": row["Cu"], "V": row["V"],
                "Nb": row.get("Nb", 0.0), "Co": row.get("Co", 0.0)
            }
            derived_pcm.append(calculate_pcm(comp))
            derived_ce.append(calculate_carbon_equivalent_iiw(comp))
            derived_ms.append(calculate_martensite_start(comp))
            derived_bs.append(calculate_bainite_start(comp))

        df["pcm"] = derived_pcm
        df["ce_iiw"] = derived_ce
        df["ms_C"] = derived_ms
        df["bs_C"] = derived_bs

        X = df[FEATURE_COLS].values
        metrics_report = {}

        for target in TARGET_COLS:
            y = df[target].values

            # 5-Fold Cross-Validation
            kf = KFold(n_splits=5, shuffle=True, random_state=42)
            cv_r2 = []
            cv_mae = []

            for train_idx, test_idx in kf.split(X):
                X_tr, X_te = X[train_idx], X[test_idx]
                y_tr, y_te = y[train_idx], y[test_idx]

                m_rf = RandomForestRegressor(n_estimators=100, max_depth=6, random_state=42)
                m_gb = GradientBoostingRegressor(n_estimators=100, max_depth=4, learning_rate=0.08, random_state=42)

                m_rf.fit(X_tr, y_tr)
                m_gb.fit(X_tr, y_tr)

                y_pred = 0.5 * (m_rf.predict(X_te) + m_gb.predict(X_te))
                cv_r2.append(r2_score(y_te, y_pred))
                cv_mae.append(mean_absolute_error(y_te, y_pred))

            # Final fit on full dataset
            final_rf = RandomForestRegressor(n_estimators=150, max_depth=7, random_state=42)
            final_gb = GradientBoostingRegressor(n_estimators=150, max_depth=4, learning_rate=0.08, random_state=42)
            final_rf.fit(X, y)
            final_gb.fit(X, y)

            self.models[target] = {
                "rf": final_rf,
                "gb": final_gb,
            }
            metrics_report[target] = {
                "cv_r2": round(float(np.mean(cv_r2)), 3),
                "cv_mae": round(float(np.mean(cv_mae)), 1),
            }

        self.metrics = metrics_report
        self.is_trained = True
        return metrics_report

    def predict(self, comp_and_proc: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        """Predicts YS, UTS, and Charpy with uncertainty bounds."""
        if not self.is_trained:
            self.train()

        X_in = extract_features_from_dict(comp_and_proc).values
        results = {}

        for target in TARGET_COLS:
            rf = self.models[target]["rf"]
            gb = self.models[target]["gb"]

            pred_rf = rf.predict(X_in)[0]
            pred_gb = gb.predict(X_in)[0]
            mean_pred = 0.5 * (pred_rf + pred_gb)

            # Uncertainty: tree-variance of RF + disagreement between RF and GB
            tree_preds = [tree.predict(X_in)[0] for tree in rf.estimators_]
            tree_std = float(np.std(tree_preds))
            model_disagreement = abs(pred_rf - pred_gb)
            total_uncertainty = float(np.sqrt(tree_std ** 2 + (0.5 * model_disagreement) ** 2))

            results[target] = {
                "mean": round(float(mean_pred), 1),
                "uncertainty": round(max(5.0, total_uncertainty), 1),
            }

        return results

    def predict_isochronal_tempering_curve(
        self,
        base_comp: Dict[str, Any],
        temp_min_C: float = 400.0,
        temp_max_C: float = 650.0,
        step_C: float = 25.0,
        time_h: float = 2.0,
        test_temp_C: float = 25.0
    ) -> pd.DataFrame:
        """Computes predicted properties across a range of tempering temperatures."""
        temps = np.arange(temp_min_C, temp_max_C + step_C, step_C)
        rows = []
        for t in temps:
            cond = dict(base_comp)
            cond["temper_temp_C"] = t
            cond["temper_time_h"] = time_h
            cond["test_temp_C"] = test_temp_C

            preds = self.predict(cond)
            rows.append({
                "Tempering Temperature (°C)": t,
                "Yield Strength (MPa)": preds["yield_strength_mpa"]["mean"],
                "YS Lower": preds["yield_strength_mpa"]["mean"] - preds["yield_strength_mpa"]["uncertainty"],
                "YS Upper": preds["yield_strength_mpa"]["mean"] + preds["yield_strength_mpa"]["uncertainty"],
                "Charpy Toughness (J)": preds["charpy_toughness_j"]["mean"],
                "Charpy Lower": preds["charpy_toughness_j"]["mean"] - preds["charpy_toughness_j"]["uncertainty"],
                "Charpy Upper": preds["charpy_toughness_j"]["mean"] + preds["charpy_toughness_j"]["uncertainty"],
            })
        return pd.DataFrame(rows)


# Global singleton instance
_GLOBAL_SURROGATE: Optional[SurrogateModelEnsemble] = None


def get_surrogate_ensemble() -> SurrogateModelEnsemble:
    global _GLOBAL_SURROGATE
    if _GLOBAL_SURROGATE is None:
        _GLOBAL_SURROGATE = SurrogateModelEnsemble()
        _GLOBAL_SURROGATE.train()
    return _GLOBAL_SURROGATE

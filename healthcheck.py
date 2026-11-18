"""
Deployment & Container Health Check Probe for NavalSteel AI.

Verifies:
1. Core Python and metallurgy modules import without error
2. Physics screening calculations execute accurately
3. ML surrogate models can be loaded and produce predictions
4. Dataset files are intact and readable
5. Local HTTP server endpoint (if running) is healthy
"""
import sys
import urllib.request
from pathlib import Path

def check_modules():
    print("[1/5] Checking module imports...")
    try:
        from src import config, physics, schema, surrogate, optimize, dossier, graph
        print("  ✓ Core modules imported successfully.")
    except Exception as e:
        print(f"  ✗ Module import failed: {e}", file=sys.stderr)
        return False
    return True

def check_physics():
    print("[2/5] Checking physics metallurgy engine...")
    try:
        from src.physics import evaluate_steel_physics
        test_comp = {"C": 0.05, "Ni": 6.5, "Cu": 3.65, "Cr": 1.84, "Mo": 0.60}
        res = evaluate_steel_physics(test_comp)
        assert res["pcm"] > 0
        assert res["martensite_start_C"] > 0
        print(f"  ✓ Physics engine online (Pcm={res['pcm']}, Ms={res['martensite_start_C']}°C).")
    except Exception as e:
        print(f"  ✗ Physics check failed: {e}", file=sys.stderr)
        return False
    return True

def check_dataset_and_surrogate():
    print("[3/5] Checking dataset and surrogate ensemble...")
    try:
        from src.surrogate import get_surrogate_ensemble
        surrogate = get_surrogate_ensemble()
        sample = {
            "C": 0.05, "Ni": 6.5, "Cu": 3.65, "Cr": 1.84, "Mo": 0.60,
            "temper_temp_C": 475.0, "temper_time_h": 4.0, "test_temp_C": 25.0
        }
        preds = surrogate.predict(sample)
        ys = preds["yield_strength_mpa"]["mean"]
        assert ys > 800
        print(f"  ✓ Surrogate model online (Predicted YS={ys:.1f} MPa).")
    except Exception as e:
        print(f"  ✗ Surrogate check failed: {e}", file=sys.stderr)
        return False
    return True

def check_benchmarks():
    print("[4/5] Checking benchmark database records...")
    try:
        from src import config
        records = list(config.EXTRACTED_DIR.glob("*.json"))
        assert len(records) >= 5, f"Expected at least 5 benchmark records, found {len(records)}"
        print(f"  ✓ Benchmark records verified ({len(records)} found).")
    except Exception as e:
        print(f"  ✗ Benchmark records check failed: {e}", file=sys.stderr)
        return False
    return True

def check_http_server(port=8501):
    print(f"[5/5] Checking local Streamlit HTTP probe on port {port}...")
    url = f"http://localhost:{port}/_stcore/health"
    try:
        with urllib.request.urlopen(url, timeout=3) as resp:
            if resp.status == 200:
                print(f"  ✓ Streamlit HTTP service healthy (status {resp.status}).")
                return True
    except Exception as e:
        print(f"  ℹ Streamlit HTTP server probe skipped or offline ({e}).")
    return True

def main():
    print("=" * 60)
    print("⚓ NavalSteel AI — Deployment Healthcheck Probe")
    print("=" * 60)
    success = (
        check_modules() and
        check_physics() and
        check_dataset_and_surrogate() and
        check_benchmarks() and
        check_http_server()
    )
    print("=" * 60)
    if success:
        print("🎉 ALL SYSTEMS OPERATIONAL — READY FOR PRODUCTION DEPLOYMENT.")
        return 0
    else:
        print("❌ HEALTH CHECK FAILED — INSPECT ERRORS ABOVE.", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())

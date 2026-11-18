---
last_mapped_commit: eb7001815a1b864d243a670b5efd231e49c272bf
last_mapped_at: 2026-11-18
---
# Testing Patterns

**Analysis Date:** 2026-11-18

## Test Framework

**Runner:**
- `pytest` (>=9.0.0) with standard Python virtual environment.

**Run Commands:**
```bash
# Run all tests verbosely
pytest tests/ -v

# Run a specific test suite
pytest tests/test_physics.py -v

# Run with short traceback on failure
pytest tests/ --tb=short
```

## Test File Organization

**Location:**
- Dedicated `tests/` directory at the repository root.

**Mapping:**
- `tests/test_physics.py` $\rightarrow$ verifies `src/physics.py`
- `tests/test_surrogate.py` $\rightarrow$ verifies `src/surrogate.py`
- `tests/test_optimize.py` $\rightarrow$ verifies `src/optimize.py` and `src/dossier.py`
- `tests/test_schema.py` $\rightarrow$ verifies `src/schema.py` and JSON schema compliance
- `tests/test_seed.py` $\rightarrow$ verifies `data/seed_records/*.json`
- `tests/test_design.py` $\rightarrow$ verifies `src/design.py`
- `tests/test_extract_and_rag.py` $\rightarrow$ verifies `src/extract.py` and `src/rag.py`
- `tests/test_graph.py` $\rightarrow$ verifies `src/graph.py`
- `tests/test_ingest.py` $\rightarrow$ verifies `src/ingest.py`
- `tests/test_chunk.py` $\rightarrow$ verifies `src/chunk.py`
- `tests/test_normalize.py` $\rightarrow$ verifies `src/normalize.py`

## Current Test Metrics

- **Total Test Cases:** 52
- **Pass Rate:** 100% (52/52 passing)
- **Execution Time:** ~15.5 seconds

## Health & Production Probes

**Probe Script:** [`healthcheck.py`](file:///c:/Users/dipan/Downloads/ugp_497/NavalSteel_AI/healthcheck.py)
- Evaluates 5 synthetic deployment checkpoints:
  1. Module import resolution
  2. Physical metallurgy engine calculation sanity
  3. Surrogate regressor warm-up and prediction
  4. Ground truth benchmark records integrity
  5. Local Streamlit HTTP 200 health response

---

*Testing analysis: 2026-11-18*

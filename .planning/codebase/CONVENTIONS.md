---
last_mapped_commit: eb7001815a1b864d243a670b5efd231e49c272bf
last_mapped_at: 2026-11-18
---
# Coding Conventions

**Analysis Date:** 2026-11-18

## Naming Patterns

**Files:**
- Snake case for all Python source modules: `physics.py`, `surrogate.py`, `literature_api.py`.
- Prefixed `test_*.py` for test suites in `tests/`.

**Functions:**
- Snake case: `calculate_pcm()`, `predict_properties()`, `run_nsga2_optimization()`.
- Private/internal helpers prefixed with leading underscore: `_call_gemini_rag()`, `_generate_prompt()`.

**Variables:**
- Snake case: `yield_strength_mpa`, `carbon_equiv`, `pareto_candidates`.
- Standard metallurgical abbreviations preserved where clear: `pcm`, `ceq`, `ms_temp`.

**Classes & Types:**
- PascalCase for Pydantic models and classes: `AlloyComposition`, `MechanicalProperties`, `MetallurgicalRecord`.

## Code Style

**Formatting:**
- Standard PEP 8 formatting with 4-space indentation.
- Explicit type hints (`float`, `str`, `dict[str, Any]`, `Optional[float]`) across all module boundaries.

**Docstrings & Provenance:**
- Every metallurgical formula function includes academic citation in its docstring:
  ```python
  def calculate_pcm(comp: dict[str, float]) -> float:
      """
      Calculate Ito-Bessyo cracking parameter Pcm (wt%).
      Formula: Pcm = C + Si/30 + (Mn+Cu+Cr)/20 + Ni/60 + Mo/15 + V/10 + 5B
      Reference: Ito & Bessyo, J. Jpn. Weld. Soc., 37 (1968) 983-991.
      """
  ```

## Error Handling

**Patterns:**
- Graceful degradation for network-dependent features (e.g. arXiv fallback on Semantic Scholar 429).
- Schema validation via Pydantic raising descriptive `ValidationError`.
- Clean UI error messaging avoiding raw stack traces in presentation layers.

## Defensive Design

**API Fallbacks:**
- External REST services must never hard-crash the application; catch `requests.RequestException` and fallback to in-memory datasets.
- Keyword arguments in utility functions accept `*args, **kwargs` defensively when module caches might otherwise desynchronize.

---

*Convention analysis: 2026-11-18*

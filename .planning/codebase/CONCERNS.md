---
last_mapped_commit: eb7001815a1b864d243a670b5efd231e49c272bf
last_mapped_at: 2026-11-18
---
# Codebase Concerns

**Analysis Date:** 2026-11-18

## Tech Debt

**1. Semantic Scholar Rate Limits:**
- Issue: Public calls to Semantic Scholar Graph API without paid API keys are aggressively rate-limited (HTTP 429).
- Files: `src/literature_api.py`
- Resolution: Multi-tier fallback to arXiv and the Curated Naval Metallurgy Library was implemented to prevent user disruption. Long-term, caching queries locally in a SQLite database is recommended.

**2. Plotly Deprecated Layout Properties:**
- Issue: Plotly 5.x+ deprecates `titlefont` in favor of nested dictionaries `title=dict(font=...)`.
- Files: `streamlit_app.py`
- Resolution: Deprecated properties have been cleaned up and replaced with modern dictionary syntax.

**3. Dataset Scale:**
- Issue: Seed dataset currently comprises 40 experimental heats. While highly accurate for naval steel chemistries near HSLA-100 and BlastAlloy 160, extrapolation to wildly exotic alloy systems (e.g., >10 wt% Ti or Co) will have higher uncertainty.
- Mitigation: Novelty distance score in `src/optimize.py` penalizes candidates that stray too far from known training heats.

---

*Concerns analysis: 2026-11-18*

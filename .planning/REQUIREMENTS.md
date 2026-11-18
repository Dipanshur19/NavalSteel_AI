# Requirements: NavalSteel AI

**Defined:** 2026-11-18  
**Core Value:** Accelerated, physically-constrained inverse design of weldable ultra-high-strength naval plate steels achieving $\ge 1100\text{ MPa}$ yield strength and $\ge 60\text{ J}$ at $-40^\circ\text{C}$ CVN toughness with non-preheat weldability ($P_{cm} \le 0.24$).

## Phase 1: Core Physical Metallurgy & Inverse Prediction (Completed)

- [x] **PHYS-01**: Implement Ito-Bessyo $P_{cm}$ formula for cold cracking susceptibility.
- [x] **PHYS-02**: Implement IIW carbon equivalent $C_{eq}$ formula.
- [x] **PHYS-03**: Implement Andrews linear equation for martensite start ($M_s$) temperature.
- [x] **PHYS-04**: Validate physical metallurgy constraints against experimental reference steels (BlastAlloy 160, HY-80, HY-100, HSLA-100).
- [x] **SURR-01**: Train multi-output Random Forest regressor predicting $R_{p0.2}$, $R_m$, $A_5$, and Charpy V-notch energy at $-40^\circ\text{C}$.
- [x] **SURR-02**: Compute isochronal tempering response curves showing secondary hardening peak ($450\text{--}550^\circ\text{C}$).

## Phase 2: Multi-Objective Pareto Optimization & Dossier Export (Completed)

- [x] **OPT-01**: Implement NSGA-II non-dominated sorting genetic algorithm.
- [x] **OPT-02**: Implement multi-objective formulation: Maximize Yield Strength, Maximize $-40^\circ\text{C}$ Toughness, Minimize $P_{cm}$, and Minimize Raw Material Cost.
- [x] **OPT-03**: Implement candidate novelty distance penalty against training heats to prevent unrealistic chemistry extrapolation.
- [x] **OPT-04**: Generate downloadable ReportLab PDF research certification dossier with composition tables and radar plots.

## Phase 3: Scholarly Literature Grounding & AI Assistant (Completed)

- [x] **RAG-01**: Ingest and chunk Northwestern University doctoral dissertation (Saha 2004) with page attribution.
- [x] **RAG-02**: Build TF-IDF vector retrieval engine for metallurgical Q&A.
- [x] **RAG-03**: Integrate Google Gemini 3.5 Flash zero-key AI Metallurgist with cascading fallback.
- [x] **LIT-01**: Multi-tier literature discovery engine (Semantic Scholar -> arXiv Open Access -> Curated Reference Archive) resilient to HTTP 429 rate limits.

## Phase 4: Production Polish & UI Unslop (Completed)

- [x] **UI-01**: Implement 5-studio layout in Streamlit (`Alloy Studio`, `Pareto Optimizer`, `Benchmark Steels`, `Knowledge Graph`, `Literature & AI`).
- [x] **UI-02**: Apply `unslop-ui` standards: strip decorative emojis, remove rainbow pill badges, establish slate/navy research instrument aesthetic.
- [x] **UI-03**: Modernize Plotly layouts, eliminate deprecated `titlefont` configurations.
- [x] **DEPL-01**: Containerize application with `Dockerfile` and `docker-compose.yml`.
- [x] **DEPL-02**: Build synthetic 5-point deployment healthcheck probe (`healthcheck.py`).

## Phase 5: Knowledge Graph Pathways & Military Spec Cross-Matching (Completed)

- [x] **GRAPH-01**: Causal NetworkX graph visualizer with topological metrics, density calculations, and multi-scale causal pathway tracing.
- [x] **SPEC-01**: Automated compliance cross-matcher against MIL-S-24645A (HSLA-100/115), MIL-S-16216 (HY-80/100), and ONR BlastAlloy 160 with tolerance checklists.

## Traceability

| Requirement | Phase | Status | Verification Method |
|---|---|---|---|
| PHYS-01..04 | Phase 1 | Complete | `tests/test_physics.py` (Passed) |
| SURR-01..02 | Phase 1 | Complete | `tests/test_surrogate.py` (Passed) |
| OPT-01..04 | Phase 2 | Complete | `tests/test_optimize.py` (Passed) |
| RAG-01..03 | Phase 3 | Complete | `tests/test_extract_and_rag.py` (Passed) |
| LIT-01 | Phase 3 | Complete | Healthcheck & Live App (Passed) |
| UI-01..03 | Phase 4 | Complete | Streamlit Server `http://localhost:8501` (Status 200) |
| DEPL-01..02 | Phase 4 | Complete | `python healthcheck.py` (5/5 Passed) |
| GRAPH-01 | Phase 5 | Complete | `tests/test_graph.py` (Passed) |
| SPEC-01 | Phase 5 | Complete | `tests/test_physics.py` & Live UI (Passed) |

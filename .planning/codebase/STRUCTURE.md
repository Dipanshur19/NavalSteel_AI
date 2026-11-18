---
last_mapped_commit: eb7001815a1b864d243a670b5efd231e49c272bf
last_mapped_at: 2026-11-18
---
# Codebase Structure

**Analysis Date:** 2026-11-18

## Directory Layout

```
NavalSteel_AI/
├── .planning/                  # GSD spec-driven project management & architecture maps
│   ├── codebase/               # 7 canonical architecture & convention documents
│   └── onboarding/             # Onboarding digests and summaries
├── .streamlit/                 # Streamlit server & visual theme configuration
│   └── config.toml             # Slate theme definition, port 8501, CORS settings
├── data/                       # Ground-truth datasets, benchmark records & vector index
│   ├── seed_records/           # Canonical JSON definitions of naval steel benchmarks
│   ├── vector_index/           # Pre-computed TF-IDF index for dissertation RAG
│   └── papers/                 # Grounding PDFs (e.g. Saha 2004 Northwestern dissertation)
├── src/                        # Core Python domain modules
│   ├── chunk.py                # Academic text chunking with overlap & citation preservation
│   ├── design.py               # Candidate perturbation & nearest experimental neighbor search
│   ├── dossier.py              # ReportLab PDF research certification dossier generator
│   ├── extract.py              # Structured LLM/schema extraction from unstructured texts
│   ├── graph.py                # Causal NetworkX metallurgical knowledge graph
│   ├── ingest.py               # Robust PDF document extractor
│   ├── literature_api.py       # Multi-tier literature query engine (S2 / arXiv / Curated)
│   ├── normalize.py            # Units normalization (MPa, ksi, °C, °F, J, ft-lb)
│   ├── optimize.py             # NSGA-II multi-objective genetic algorithm & Pareto sorting
│   ├── physics.py              # Empirical physical metallurgy equations (Pcm, Ceq, Ms)
│   ├── rag.py                  # Grounded retrieval-augmented generation & Gemini Flash agent
│   ├── schema.py               # Pydantic v2 data models for alloy definitions
│   └── surrogate.py            # Multi-output Random Forest regressor & tempering curves
├── tests/                      # Automated PyTest verification suite (52 tests)
│   ├── test_chunk.py
│   ├── test_design.py
│   ├── test_extract_and_rag.py
│   ├── test_graph.py
│   ├── test_ingest.py
│   ├── test_normalize.py
│   ├── test_optimize.py
│   ├── test_physics.py
│   ├── test_schema.py
│   ├── test_seed.py
│   └── test_surrogate.py
├── .dockerignore               # Docker build exclusion rules
├── .env                        # Local environment variables (GEMINI_API_KEY)
├── .gitignore                  # Git tracking exclusion rules
├── docker-compose.yml          # Multi-container orchestration definition
├── Dockerfile                  # Container build instructions for production deployment
├── healthcheck.py              # Standalone 5-probe system readiness verification script
├── requirements.txt            # Python package dependencies
└── streamlit_app.py            # Main interactive Streamlit application entry point
```

## Directory Purposes

**`src/`:**
- Purpose: All computational metallurgy algorithms, machine learning models, and data pipelines.
- Contains: Standalone, well-tested Python modules with zero circular dependencies.

**`data/`:**
- Purpose: Seed data for empirical benchmarking and literature grounding.
- Contains: Validated metallurgical records (`seed_records/*.json`) adhering to schema specifications.

**`tests/`:**
- Purpose: Comprehensive automated test coverage for continuous integration.
- Contains: Unit tests, edge cases, schema validations, and mock-assisted end-to-end runs.

## Key File Locations

**Entry Points:**
- `streamlit_app.py`: Web dashboard entry point running the 5 metallurgical studios.
- `healthcheck.py`: CLI health probe for deployment verification.

**Configuration:**
- `.streamlit/config.toml`: Dark theme styling, port, and security policies.
- `.env`: Environment secrets (`GEMINI_API_KEY`).

**Core Logic:**
- `src/physics.py`: Weldability and phase transformation calculations.
- `src/surrogate.py`: Random Forest mechanical property surrogate.
- `src/optimize.py`: NSGA-II multi-objective optimizer.
- `src/rag.py`: Gemini 3.5 Flash RAG agent.

## Where to Add New Code

**New Physical Model / Metallurgy Formula:**
- Implementation: Add function to `src/physics.py` with rigorous docstrings and citations (e.g., Ito-Bessyo, Andrews, Pickering).
- Tests: Add corresponding unit tests in `tests/test_physics.py`.

**New Benchmark Steel Specification:**
- Add JSON record to `data/seed_records/<steel_name>.json`.
- Validate against schema in `tests/test_schema.py`.

**New UI Studio / Visual Tool:**
- Add a dedicated studio function in `streamlit_app.py` or sub-module.
- Follow the established `unslop-ui` slate aesthetic.

---

*Structure analysis: 2026-11-18*

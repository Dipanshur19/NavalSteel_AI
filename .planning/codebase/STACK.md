---
last_mapped_commit: eb7001815a1b864d243a670b5efd231e49c272bf
last_mapped_at: 2026-11-18
---
# Technology Stack

**Analysis Date:** 2026-11-18

## Languages

**Primary:**
- Python 3.12 (`c:\Users\dipan\Downloads\ugp_497\NavalSteel_AI\.venv`) - Core application backend, machine learning surrogate, physics models, optimization engine, RAG pipeline, and Streamlit user interface.

**Secondary:**
- Markdown / HTML - Artifacts, technical documentation, ReportLab PDF styles, and custom UI styling.

## Runtime

**Environment:**
- Python 3.12.0 (Windows x86_64, Linux compatible via Docker)
- Node.js v24.15.0 / npm 11.17.0 - GSD Core automation tools and hooks runtime.

**Package Manager:**
- `pip` 24.x (`requirements.txt`)
- Virtual Environment: `.venv` in project root

## Frameworks

**Core Application & UI:**
- `streamlit` (>=1.32.0) - Reactive interactive web dashboard, state management, and multi-studio layout.
- `plotly` (>=5.19.0) - High-resolution interactive 3D Pareto frontier scatter charts, dual-axis isochronal tempering curves, radar plots.

**Machine Learning & Optimization:**
- `scikit-learn` (>=1.4.0) - Multi-output `RandomForestRegressor` surrogate engine for sub-35ms mechanical property inference.
- `numpy` (>=1.26.0) & `pandas` (>=2.2.0) - Vectorized metallurgical array computations and seed dataset management.
- Custom NSGA-II GA engine (`src/optimize.py`) - Non-dominated sorting genetic algorithm with crowding distance sorting.

**Materials Graph & Knowledge Representation:**
- `networkx` (>=3.2.0) - Causal metallurgical knowledge graph linking alloying elements, microstructures, and mechanical properties.
- `pydantic` (>=2.6.0) - Strict metallurgical schema validation, unit compliance, and evidence status tracking.

**Document Processing, Retrieval & LLM:**
- `pymupdf` (>=1.23.0) / `pypdf` - PDF literature extraction and chunking.
- `google-genai` (>=0.1.0) - Google Gemini 3.5 Flash integration for evidence-grounded AI metallurgist Q&A.
- `reportlab` (>=4.1.0) - Academic-grade PDF research dossier compilation.
- `requests` (>=2.31.0) - External scholarly REST APIs (Semantic Scholar, arXiv API).

**Testing & Diagnostics:**
- `pytest` (>=8.0.0) - Unit, property, and integration test suite (52 tests).
- `healthcheck.py` - Synthetic 5-point deployment readiness probe.

## Key Dependencies

**Critical:**
- `streamlit` - Primary delivery channel for computational metallurgy workbench.
- `scikit-learn` - Core surrogate modeling for sub-second inverse design iteration.
- `pydantic` - Enforces physical constraints and schema validity on alloy compositions.
- `google-genai` - Drives the embedded AI Metallurgist assistant without requiring user API keys.

**Infrastructure:**
- `docker` / `docker-compose` - Containerized production deployment.

## Configuration

**Environment:**
- Configured via `.env` in project root:
  - `GEMINI_API_KEY`: API key for Gemini Flash LLM backend.
  - `GEMINI_EXTRACTION_MODEL`: `gemini-3.5-flash-lite`
  - `GEMINI_RAG_MODEL`: `gemini-3.5-flash-lite`
  - `STREAMLIT_SERVER_PORT`: `8501`
  - `STREAMLIT_SERVER_HEADLESS`: `true`

**Build & UI Configuration:**
- `.streamlit/config.toml` - Theme settings (slate dark palette `#0F172A`, `#1E293B`, `#38BDF8`), CORS, and server binding.

## Platform Requirements

**Development:**
- Windows 10/11 or Linux with Python 3.10+ and Node.js 18+.

**Production:**
- Docker engine with Linux container host (`python:3.12-slim`), 2 CPU cores, 4GB RAM minimum.

---

*Stack analysis: 2026-11-18*

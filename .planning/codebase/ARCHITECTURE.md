---
last_mapped_commit: eb7001815a1b864d243a670b5efd231e49c272bf
last_mapped_at: 2026-11-18
---
<!-- refreshed: 2026-11-18 -->
# Architecture

**Analysis Date:** 2026-11-18

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                       STREAMLIT PRESENTATION LAYER                          │
│                               `streamlit_app.py`                            │
├─────────────────────┬─────────────────────┬─────────────────────────────────┤
│   Studio 1: Predict │  Studio 2: Optimize │   Studio 3: Benchmarks          │
│   Studio 4: Graph   │  Studio 5: RAG & AI │   Dossier PDF Generator         │
└──────────┬──────────┴──────────┬──────────┴──────────────┬──────────────────┘
           │                     │                         │
           ▼                     ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    METALLURGICAL CORE & MACHINE LEARNING                    │
├─────────────────────┬─────────────────────┬─────────────────────────────────┤
│  Empirical Physics  │ Surrogate Regressor │  NSGA-II Genetic Optimizer      │
│  `src/physics.py`   │ `src/surrogate.py`  │  `src/optimize.py`              │
├─────────────────────┼─────────────────────┼─────────────────────────────────┤
│  Knowledge Graph    │ Schema Validation   │  Nearest Neighbor Search        │
│  `src/graph.py`     │ `src/schema.py`     │  `src/design.py`                │
└──────────┬──────────┴──────────┬──────────┴──────────────┬──────────────────┘
           │                     │                         │
           ▼                     ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     LITERATURE, RAG & LLM INGESTION                         │
├─────────────────────┬─────────────────────┬─────────────────────────────────┤
│  PDF Ingestion      │ Text Chunking       │  Scholarly APIs (arXiv/S2)      │
│  `src/ingest.py`    │ `src/chunk.py`      │  `src/literature_api.py`        │
├─────────────────────┼─────────────────────┼─────────────────────────────────┤
│  RAG Engine         │ Gemini 3.5 Agent    │  ReportLab PDF Dossier          │
│  `src/rag.py`       │ `src/rag.py`        │  `src/dossier.py`               │
└─────────────────────┴─────────────────────┴─────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|---|---|---|
| **App Presentation** | Multi-studio reactive Streamlit user interface, tabs, controls, and Plotly visualizations. | [`streamlit_app.py`](file:///c:/Users/dipan/Downloads/ugp_497/NavalSteel_AI/streamlit_app.py) |
| **Physics Engine** | Empirical weldability ($P_{cm}, C_{eq}$), martensite start ($M_s$), and cracking risk calculations. | [`src/physics.py`](file:///c:/Users/dipan/Downloads/ugp_497/NavalSteel_AI/src/physics.py) |
| **Surrogate Regressor** | Multi-output Random Forest regression predicting $R_{p0.2}, R_m, A_5, CVN$ and isochronal curves. | [`src/surrogate.py`](file:///c:/Users/dipan/Downloads/ugp_497/NavalSteel_AI/src/surrogate.py) |
| **Pareto Optimizer** | NSGA-II non-dominated sorting multi-objective optimization for inverse alloy formulation. | [`src/optimize.py`](file:///c:/Users/dipan/Downloads/ugp_497/NavalSteel_AI/src/optimize.py) |
| **Inverse Design** | Latin hypercube perturbation and nearest experimental alloy neighbor identification. | [`src/design.py`](file:///c:/Users/dipan/Downloads/ugp_497/NavalSteel_AI/src/design.py) |
| **Knowledge Graph** | Causal NetworkX graph representation of elemental microstructural mechanisms. | [`src/graph.py`](file:///c:/Users/dipan/Downloads/ugp_497/NavalSteel_AI/src/graph.py) |
| **Literature Search** | Multi-tier literature query engine (Semantic Scholar -> arXiv Open Access -> Curated Library). | [`src/literature_api.py`](file:///c:/Users/dipan/Downloads/ugp_497/NavalSteel_AI/src/literature_api.py) |
| **RAG & AI Agent** | Evidence-grounded retrieval and Google Gemini 3.5 Flash zero-key AI Metallurgist. | [`src/rag.py`](file:///c:/Users/dipan/Downloads/ugp_497/NavalSteel_AI/src/rag.py) |
| **Dossier Compiler** | ReportLab PDF generator compiling candidate alloy technical specification sheets. | [`src/dossier.py`](file:///c:/Users/dipan/Downloads/ugp_497/NavalSteel_AI/src/dossier.py) |
| **Schema & Normalizer**| Pydantic v2 data models for alloy definitions and metallurgical unit normalization. | [`src/schema.py`](file:///c:/Users/dipan/Downloads/ugp_497/NavalSteel_AI/src/schema.py), [`src/normalize.py`](file:///c:/Users/dipan/Downloads/ugp_497/NavalSteel_AI/src/normalize.py) |

## Pattern Overview

**Overall:** Spec-Driven Materials Informatics Pipeline combining empirical physical metallurgy boundary constraints with machine learning surrogate models and genetic multi-objective optimization.

**Key Characteristics:**
- **Goal-Backward Verification:** Every predicted alloy is evaluated against physical metallurgy limits (Ito-Bessyo $P_{cm} \le 0.24$ for non-preheat weldability).
- **Sub-Second Feedback:** Fast Random Forest surrogate enables sub-35ms evaluation per candidate alloy, allowing 2,000+ population evaluations per optimization run.
- **Evidence Grounding:** AI suggestions in Studio 5 cite specific metallurgical literature references and experimental bounds.

## Layers

**UI Layer:**
- Purpose: Interactive research dashboard with 5 specialized studios.
- Location: `streamlit_app.py`
- Depends on: `src.*` modules.

**Computation & Model Layer:**
- Purpose: Real-time inference of physical and mechanical properties.
- Location: `src/physics.py`, `src/surrogate.py`, `src/optimize.py`, `src/design.py`.
- Depends on: `scikit-learn`, `numpy`, `pandas`.

**Data & Ingestion Layer:**
- Purpose: Data schemas, normalization, PDF processing, and vector search.
- Location: `src/schema.py`, `src/normalize.py`, `src/ingest.py`, `src/chunk.py`, `src/rag.py`.

## Data Flow

### Primary Request Path (Alloy Prediction)
1. User enters weight percentages for $C, Mn, Ni, Cr, Mo, Cu, V, Nb$ in Studio 1.
2. `src/physics.py` calculates $P_{cm}$, $C_{eq}$, $M_s$, and weldability envelope.
3. `src/surrogate.py` predicts Yield Strength, Tensile Strength, Elongation, and $-40^\circ\text{C}$ Charpy Toughness.
4. UI displays interactive metric gauges, radar comparison, and isochronal tempering response curve.

### Secondary Flow (Multi-Objective Optimization)
1. User sets target Yield Strength ($>1100\text{ MPa}$), minimum Charpy Toughness ($>60\text{ J}$), and $P_{cm}$ weldability cap ($<0.24$).
2. `src/optimize.py` executes NSGA-II genetic algorithm over 25 generations.
3. Non-dominated Pareto frontier is identified and rendered as an interactive 3D scatter hyper-surface.
4. User selects preferred candidate and exports an academic-grade ReportLab PDF certification dossier (`src/dossier.py`).

## Architectural Constraints

- **Single Process Streamlit Execution:** Streamlit reruns scripts upon widget interactions; compute-heavy operations (surrogate model training, graph building) MUST be cached using `@st.cache_resource`.
- **Plotly Deprecation Safety:** Avoid deprecated layout properties such as `titlefont`.
- **API Rate Resilience:** External API calls to literature databases must gracefully degrade to offline fallbacks without blocking the UI.

---

*Architecture analysis: 2026-11-18*

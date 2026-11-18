# Roadmap: NavalSteel AI

## Overview

NavalSteel AI transforms computational metallurgy research for high-performance naval plates by integrating empirical physical metallurgy, machine learning surrogate modeling, multi-objective Pareto optimization, and LLM-assisted scholarly literature retrieval into an intuitive, calm, and rigorous research workbench.

## Phases

- [x] **Phase 1: Core Physical Metallurgy & Predictive Surrogate** - Empirical cracking formulas ($P_{cm}, C_{eq}, M_s$) and Random Forest multi-output regressor with sub-35ms latency.
- [x] **Phase 2: NSGA-II Multi-Objective Optimization & Certification Dossiers** - 4D genetic trade-off exploration and ReportLab PDF dossier compiler.
- [x] **Phase 3: Scholarly Literature Ingestion & Zero-Config AI Metallurgist** - Evidence-grounded RAG, multi-tier search (Semantic Scholar / arXiv), and Google Gemini 3.5 Flash integration.
- [x] **Phase 4: Design Unslop & Production Deployment Infrastructure** - Professional research instrument aesthetic, Plotly cleanup, Dockerization, and 5-point deployment healthchecks.
- [x] **Phase 5: Interactive Knowledge Graph Visualizer & Specification Cross-Matching** - In-browser interactive force-directed graph rendering of strengthening mechanisms and MIL-DTL automated compliance checklists.

---

## Phase Details

### Phase 1: Core Physical Metallurgy & Predictive Surrogate
**Goal**: Ground all alloy evaluations in physical metallurgy laws and fast statistical surrogates.  
**Requirements**: PHYS-01, PHYS-02, PHYS-03, PHYS-04, SURR-01, SURR-02  
**Success Criteria**:
1. Empirical formulas compute $P_{cm}$, $C_{eq}$, and $M_s$ matching published literature for HY-80 and BlastAlloy 160 within $\pm 0.005\text{ wt\%}$ / $\pm 5^\circ\text{C}$.
2. Random forest surrogate model predicts $R_{p0.2}$, $R_m$, $A_5$, and $-40^\circ\text{C}$ Charpy toughness in $<35\text{ms}$.
3. Isochronal tempering curves demonstrate secondary hardening peak behavior around $450\text{--}500^\circ\text{C}$.

### Phase 2: NSGA-II Multi-Objective Optimization & Certification Dossiers
**Goal**: Enable inverse alloy formulation through non-dominated Pareto genetic search.  
**Requirements**: OPT-01, OPT-02, OPT-03, OPT-04  
**Success Criteria**:
1. Genetic algorithm explores multi-dimensional design space balancing strength, toughness, weldability, and cost.
2. Novelty penalty prevents unphysical chemical formulations far outside training heats.
3. User can export a multi-page ReportLab PDF certification dossier for any Pareto candidate.

### Phase 3: Scholarly Literature Ingestion & Zero-Config AI Metallurgist
**Goal**: Deliver instant literature grounding and expert metallurgical reasoning without API key hurdles.  
**Requirements**: RAG-01, RAG-02, RAG-03, LIT-01  
**Success Criteria**:
1. Literature queries automatically fall back to arXiv and curated libraries when Semantic Scholar rate-limits (HTTP 429).
2. Embedded Gemini 3.5 Flash provides instant, grounded answers citing specific dissertation chunks and experimental findings.
3. Zero API key configuration required for basic end-user workflows.

### Phase 4: Design Unslop & Production Deployment Infrastructure
**Goal**: Elevate interface to institutional research standards and ensure turnkey container deployment.  
**Requirements**: UI-01, UI-02, UI-03, DEPL-01, DEPL-02  
**Success Criteria**:
1. Clean slate/navy palette, 8px grid rhythm, zero decorative emojis or rainbow pills.
2. Plotly charts render smoothly without layout deprecation warnings.
3. `healthcheck.py` passes 5/5 probes and Docker container builds cleanly.

### Phase 5: Interactive Knowledge Graph Visualizer & Specification Cross-Matching
**Goal**: Deepen explanatory metallurgy capabilities with in-browser graph interaction and military specification compliance.  
**Requirements**: GRAPH-01, SPEC-01  
**Success Criteria**:
1. Causal NetworkX graph rendered interactively via HTML/JavaScript (vis.js/Cytoscape) inside Streamlit Studio 4.
2. Automated compliance badge checking candidate alloys against MIL-S-24645A (HSLA-100/115) and MIL-S-16216 (HY-80/100).

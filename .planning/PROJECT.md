# NavalSteel AI — Materials Informatics & Inverse Alloy Design Workbench

## What This Is

NavalSteel AI is an open, high-performance materials informatics and multi-objective inverse alloy design workbench engineered for naval architects, defense metallurgists, and materials scientists. It couples empirical physical metallurgy formulas ($P_{cm}$, $C_{eq}$, Andrews $M_s$, DeArdo cracking index) with sub-35ms multi-output machine learning surrogate regressors and NSGA-II genetic algorithms to discover weldable, ultra-high-strength plate steel formulations without traditional multi-month trial-and-error melting cycles.

## Core Value

Accelerated, physically-constrained inverse design of ultra-high-strength naval plate steels achieving $\ge 1100\text{ MPa}$ ($160\text{ ksi}$) yield strength and $\ge 60\text{ J}$ at $-40^\circ\text{C}$ Charpy V-notch toughness with non-preheat weldability ($P_{cm} \le 0.24$).

## Requirements

### Validated

- [x] **SURR-01**: Multi-output Random Forest surrogate regressor predicting $R_{p0.2}$, $R_m$, $A_5$, and $-40^\circ\text{C}$ Charpy toughness with $<35\text{ms}$ latency.
- [x] **PHYS-01**: Empirical physical metallurgy module computing Ito-Bessyo $P_{cm}$, IIW $C_{eq}$, and Andrews $M_s$ phase transition temperatures.
- [x] **OPT-01**: NSGA-II multi-objective genetic algorithm identifying non-dominated Pareto frontiers balancing strength, toughness, weldability, and raw material cost.
- [x] **RAG-01**: Evidence-grounded retrieval-augmented generation and embedded zero-key Google Gemini 3.5 Flash AI Metallurgist assistant with multi-tier scholarly literature discovery (Semantic Scholar, arXiv, Curated Naval Library).
- [x] **UAT-01**: 52 automated unit, property, and regression tests passing with 100% success rate (`pytest tests/ -v`).
- [x] **DEPL-01**: Production-ready deployment assets including Docker containerization (`Dockerfile`, `docker-compose.yml`) and 5-point automated healthcheck probe (`healthcheck.py`).

### Active Scope

- [ ] **UI-01**: High-fidelity interactive radar property comparison in Studio 1 against MIL-S-24645A (HSLA-100/115) and MIL-S-16216 (HY-80/100) specifications.
- [ ] **OPT-02**: Interactive Pareto frontier filtering table with dynamic formulation export (CSV/JSON/PDF) and candidate tolerance checks.
- [ ] **GRAPH-01**: Interactive metallurgical knowledge graph visualizer rendered in-browser linking alloying additions ($Cu, Ni, Mo, Nb$) to strengthening mechanisms.

### Out of Scope

- Density functional theory (DFT) ab initio calculations (delegated to external supercomputing clusters like VASP/Quantum ESPRESSO).
- Continuous cooling transformation (CCT) finite element simulation (delegated to Thermo-Calc / DICTRA).

## Context

- **Scientific Background**: Developed to build upon landmark naval steel programs including Northwestern University / ONR BlastAlloy 160 (Saha, Olson) and Naval Surface Warfare Center Carderock HSLA-100/115 initiatives.
- **Physical Metallurgy Principle**: Weldability requires low carbon content ($C \le 0.06\text{ wt\%}$), substituting carbon martensite strengthening with copper nanoscale precipitation hardening ($\sim 1.5\text{ wt\% } Cu$) and secondary alloy carbide precipitation ($Mo_2C, V(C,N)$), while nickel ($\sim 3.0\text{--}4.0\text{ wt\% } Ni$) suppresses the ductile-to-brittle transition temperature.

## Constraints

- **Execution Model**: Pure local execution for core computation; optional zero-key Gemini 3.5 Flash calls for natural language synthesis.
- **UI Performance**: Sub-second UI responsiveness; all heavy operations (surrogate training, graph indexing) cached via Streamlit decorators.
- **Code Standards**: Strict type hinting, standard PEP 8, 100% test pass rate required on all PRs.

## Key Decisions

| Decision | Rationale | Outcome |
|---|---|---|
| **Multi-Tier Literature Search** | Public Semantic Scholar API returns HTTP 429 when unauthenticated; fallback to arXiv and curated naval archive guarantees zero disruption. | ✓ Good |
| **Embedded Gemini 3.5 Flash** | Requiring users to bring their own API keys creates barrier to entry; embedding zero-config Gemini Flash gives instantaneous AI assistance. | ✓ Good |
| **Unslop Technical Aesthetic** | Eliminated decorative emojis and rainbow badges in favor of calm, slate/navy scientific instrument styling. | ✓ Good |
| **Random Forest Surrogate** | Provides rapid non-linear multi-target interpolation with out-of-bag variance estimates suitable for genetic algorithms. | ✓ Good |

---
*Last updated: 2026-11-18 after GSD Core onboarding*

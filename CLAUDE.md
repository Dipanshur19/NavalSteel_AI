# CLAUDE.md — NavalSteel AI Project Guide

## 1. Project Overview
**NavalSteel AI** is a materials informatics and computational inverse alloy design platform for high-performance naval defense steels (e.g., HSLA-100, HY-80/100, AF1410, and BlastAlloy160). 

- **Academic Context**: Undergraduate Project UGP 497, Department of Materials Science & Engineering, IIT Kanpur.
- **Author**: Dipanshu Raj (Roll No: 230375).
- **Project Mentor**: Prof. Amarendra Kumar Singh.
- **Scientific Foundation**: Dr. Arup Saha's 2004 Northwestern University PhD Dissertation (*"Systems Design of Transformation Toughened Blast Resistant Naval Steels"*), Olson metallurgical systems design approach, and US Navy Military Specifications (MIL-S-24645A, MIL-S-16216K).

---

## 2. Tech Stack & Dependencies
- **Language**: Python 3.10+ (tested on Python 3.12)
- **Frontend / Dashboard**: Streamlit
- **Visualizations**: Plotly (high-contrast dark engineering theme)
- **Machine Learning**: Scikit-learn (RandomForestRegressor, GradientBoostingRegressor surrogate ensemble)
- **Multi-Objective Optimization**: DEAP (NSGA-II evolutionary algorithm)
- **Knowledge Graph**: NetworkX, PyVis, Cytoscape-style layout
- **Document Extraction & RAG**: pdfplumber, pypdf, TF-IDF vectorizer, Sentence-Transformers (optional), Google Gemini Flash / Anthropic Claude APIs (with zero-key extractive fallback)
- **PDF Dossier & Reports**: ReportLab
- **Testing**: pytest (58 unit and integration tests)

---

## 3. Directory & Codebase Structure
```text
NavalSteel_AI/
├── streamlit_app.py             # Main entry point: 6 Studios Dashboard
├── healthcheck.py               # Production deployment healthcheck probe (5 stages)
├── generate_report_assets.py    # Generates benchmark figures for reports & thesis
├── build_ugp497_final_report.py # ReportLab generator for 11-page UGP final report
├── build_mentor_presentation_walkthrough.py # ReportLab generator for 7-page guide
├── requirements.txt             # Python dependencies
├── pyproject.toml               # Package configuration
├── Dockerfile & docker-compose  # Containerization configs
├── src/
│   ├── config.py                # Global paths, environment keys, and default hyperparameters
│   ├── physics.py               # Empirical formulas: Pcm, CE_IIW, Ms, Bs, alloy cost, MIL-SPECs
│   ├── surrogate.py             # Ensemble ML model: YS, UTS, Charpy Toughness (-40°C)
│   ├── optimize.py              # NSGA-II multi-objective genetic algorithm for inverse design
│   ├── graph.py                 # Causal Knowledge Graph (Chemistry -> Microstructure -> Mechanisms -> Properties)
│   ├── extract.py               # Universal materials extractor (.pdf, .csv, .json, .txt, .md)
│   ├── literature_api.py        # Semantic Scholar, arXiv, and curated literature search
│   ├── rag.py                   # RAG question answering pipeline & Gemini Flash agent
│   ├── design.py                # Composition generator, nearest-neighbor experimental heat lookups
│   ├── dossier.py               # Engineering dossier generator (Markdown & ReportLab PDF)
│   ├── chunk.py                 # Document semantic chunking for RAG
│   ├── embed.py                 # Vector embeddings and indexing (TF-IDF / SBERT)
│   ├── ingest_pdf.py            # PDF parsing and text/table extraction
│   └── validate.py              # Schema validation & acceptance tests
├── tests/                       # 58 comprehensive unit & integration tests
├── data/
│   ├── dataset/                 # 40 experimental heats CSV matrix
│   ├── sample_documents/        # Sample metallurgy docs (.txt, .csv, .md, .json)
│   ├── raw/                     # Source dissertation PDF (blastalloy160_saha_2004.pdf)
│   ├── processed/               # Chunked and parsed JSON files
│   └── index/                   # Serialized vector search indexes (.pkl)
├── reports/                     # UGP 497 PDF reports and generated publication figures
└── .planning/                   # Project state, roadmap, and GSD planning artifacts
```

---

## 4. Key CLI Commands

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run Streamlit Dashboard
```bash
streamlit run streamlit_app.py
```

### Run Test Suite (Always ensure all 58 tests pass)
```bash
pytest
```

### Run Deployment Healthcheck Probe
```bash
python healthcheck.py
```

### Regenerate Report Assets & Figures
```bash
python generate_report_assets.py
python build_ugp497_final_report.py
python build_mentor_presentation_walkthrough.py
```

---

## 5. Architectural Conventions & Guidelines for Claude

When making changes or adding features:

1. **Unslop Design Standard**:
   - **No emoji chrome**: Never add emojis to tab titles, button names, badges, or headers (e.g., use `Alloy Synthesizer`, NOT `⚡ Alloy Synthesizer`).
   - Keep styling in the clean, high-contrast dark engineering theme (`#07090e` base, `#0e1424` card background, `#38bdf8` cyan primary accent).
   - Write concise, technical, human-crafted descriptions. Avoid AI filler, buzzwords, and marketing fluff.

2. **Physical Metallurgy Integrity**:
   - Maintain metallurgical constraints:
     - $P_{cm} \le 0.30$ for low cold cracking susceptibility without heavy preheat.
     - $M_s \ge 300^\circ\text{C}$ for auto-tempered lath martensite matrix.
     - Mass conservation: $\text{Fe} = 100 - \sum \text{solutes}$.
   - Ensure units are consistent (SI: MPa, J, °C; Imperial conversions provided via `is_imperial` helper).

3. **Multi-Studio Structure in `streamlit_app.py`**:
   - **Studio 1: Alloy Synthesizer**: Formulation, thermal kinetics, property envelopes, radar chart.
   - **Studio 2: Pareto Optimization**: NSGA-II multi-objective frontier (YS vs. Toughness vs. Cost vs. $P_{cm}$).
   - **Studio 3: Benchmark Steels**: Standard naval grades (HY-80, HY-100, HSLA-100, AF1410, BlastAlloy160) and 40 experimental heats.
   - **Studio 4: Causal Network**: Hierarchical multiscale metallurgical graph visualizer.
   - **Studio 5: Document Extractor**: Universal extractor (.pdf, .csv, .json, .txt, .md) with 1-click loading into Studio 1.
   - **Studio 6: Literature Intelligence**: AI Metallurgist Agent (Gemini Flash), scholarly literature search, and dissertation RAG.

4. **Testing Protocol**:
   - Every physics formula or surrogate modification must be accompanied by/verified against tests in `tests/`.
   - Never break existing tests (`pytest` should always exit with code 0).

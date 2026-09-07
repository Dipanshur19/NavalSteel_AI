# ⚓ NavalSteel AI — Autonomous Materials Informatics & Alloy Optimization Platform

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Tests Passing](https://img.shields.io/badge/pytest-52%2F52%20passed%20(100%25)-success.svg)](tests/)
[![Dashboard](https://img.shields.io/badge/UI-Streamlit%20%7C%20Plotly%203D-orange.svg)](streamlit_app.py)
[![LLM Support](https://img.shields.io/badge/LLM-Gemini%203.6%20Flash%20%7C%20Claude-8A2BE2.svg)](src/rag.py)
[![Optimization](https://img.shields.io/badge/Algorithm-NSGA--II%20Pareto-brightgreen.svg)](src/optimize.py)

**NavalSteel AI** is an evidence-grounded computational materials informatics and autonomous alloy optimization platform designed for the discovery of high-strength, fracture-tough, and weldable naval hull plate steels. 

Built around the benchmark **BlastAlloy160** research (*Arup Saha, 2004, Northwestern University*) alongside US Navy naval steel standards (**HY-80, HY-100, HSLA-100, HSLA-115, AF1410**), NavalSteel AI bridges empirical physical metallurgy laws with machine learning surrogate models, multi-objective evolutionary algorithms, and agentic literature intelligence.

---

## 🚀 Key Architectural Capabilities

### 1. Physics-Informed ML Surrogate Predictor Layer ([`src/surrogate.py`](src/surrogate.py))
- **Multi-Target Ensemble Regressors**: Heterogeneous ensemble combining `RandomForestRegressor` and `GradientBoostingRegressor` trained on 40 experimental heats across 17 compositional, thermodynamic, and thermal processing features.
- **Calibrated Cross-Validation Benchmarks (5-Fold CV)**:
  - **Yield Strength**: $R^2 = 0.895$ (MAE: $45.5\text{ MPa}$ / $\approx 6.6\text{ ksi}$)
  - **Tensile Strength (UTS)**: $R^2 = 0.880$ (MAE: $51.6\text{ MPa}$ / $\approx 7.5\text{ ksi}$)
  - **Charpy Impact Toughness**: $R^2 = 0.779$ (MAE: $14.8\text{ J}$ / $\approx 10.9\text{ ft-lb}$)
- **Uncertainty Quantification (UQ)**: Combines intra-ensemble tree variance with inter-model residual disagreement ($\sigma_{\text{total}} = \sqrt{\sigma_{\text{trees}}^2 + 0.25\cdot\Delta_{\text{models}}^2}$) to detect out-of-distribution queries.
- **Dynamic Isochronal Tempering Curves**: Accurately reproduces the non-linear secondary hardening peak ($475^\circ\text{C}\text{--}520^\circ\text{C}$) driven by Cu nanoclusters and $M_2C$ alloy carbides, followed by overaging softening.

### 2. Multi-Objective Pareto Optimization Engine ([`src/optimize.py`](src/optimize.py))
- **NSGA-II Evolutionary Optimization**: Simultaneously optimizes 4 competing engineering objectives:
  $$\max \text{Yield Strength}, \quad \max \text{Charpy Toughness}, \quad \min P_{cm} \text{ (Weld Cracking)}, \quad \min \text{Raw Material Cost}$$
- **Hard Metallurgical Constraints**: Prunes unphysical or crack-prone compositions before ranking ($0.02\% \le C \le 0.12\%$, $M_s \ge 320^\circ\text{C}$, total solutes $\le 20\text{ wt\%}$, $P_{cm} \le 0.48$).
- **Economic Ingot Cost Index**: Real-world raw alloying commodity pricing benchmark ($\$/\text{kg}$ and $\$ / \text{ton}$) covering $Fe, C, Mn, Si, Ni, Cr, Mo, Cu, V, Nb, Co$.
- **Candidate Novelty Scoring**: Quantifies Euclidean distance in normalized feature space to nearest benchmark anchors (`Derivative`, `Balanced Innovation`, `High Novelty`).

### 3. Physics-Informed Screening Engine ([`src/physics.py`](src/physics.py))
- Calculates **Ito-Bessyo Cracking Parameter ($P_{cm}$)** and Carbon Equivalent ($CE_{IIW}$).
- Calculates **Andrews Martensite Start ($M_s$)** and **Steven-Haynes Bainite Start ($B_s$)** transformation temperatures.
- Computes recommended minimum preheat temperatures and heat-affected zone (HAZ) cold-cracking risk ratings.

### 4. Interactive Materials Knowledge Graph ([`src/graph.py`](src/graph.py))
- Force-directed 2D causal network visualization powered by `NetworkX` and `PyVis`.
- Maps non-linear metallurgy pathways:
  - 🔵 **Alloying Elements** ($\text{Ni}, \text{Cu}, \text{Mo}, \text{Cr}, \text{C}, \text{V}$)
  - 🟣 **Microstructural Phases** ($\text{Lath Martensite}, \text{Bainite}, \text{Cu nanoclusters}, M_2C\text{ Carbides}, \text{Retained Austenite}$)
  - 🟠 **Strengthening Mechanisms** ($\text{Orowan Bypass}, \text{Solid Solution}, \text{TRIP Transformation Toughening}, \text{Secondary Hardening}$)
  - 🟢 **Macroscopic Properties** ($\text{Yield Strength}, \text{Charpy Toughness}, \text{Weldability}$)

### 5. Automated Laboratory Dossier & PDF Synthesis ([`src/dossier.py`](src/dossier.py))
- Generates publication-grade **2-page PDF specification sheets** via `ReportLab`.
- Includes aim chemistry with tolerance windows ($\pm 0.005\%\text{--}0.15\%$), performance forecasts with 95% confidence intervals, and a **5-stage laboratory manufacturing schedule**:
  1. *Vacuum Induction Melting (VIM) + Vacuum Arc Remelting (VAR)* with strict gas limits.
  2. *High-Temperature Homogenization Soak* ($1200^\circ\text{C}$ for $8.0\text{ h}$).
  3. *Thermomechanical Forging / Rolling* (breakdown at $1150^\circ\text{C}$, finishing at $920^\circ\text{C}$, reduction $\ge 4:1$).
  4. *Austenitization & Quenching* ($910^\circ\text{C}$ for $1.0\text{ h}$ + water quench).
  5. *Isochronal Precipitation Tempering* (target secondary hardening hold).

### 6. Evidence-Grounded Literature Intelligence ([`src/rag.py`](src/rag.py), [`src/extract.py`](src/extract.py))
- Page-aware PDF parser and hierarchical chunker indexing 266 pages into 206 semantic chunks.
- Vector retrieval powered by local TF-IDF / SBERT vector embeddings.
- LLM synthesis via **Google Gemini 3.6 Flash** (free tier supported) or **Anthropic Claude**, with strict Pydantic schema validation enforcing scientific provenance (`MEASURED` vs. `TARGET` vs. `PREDICTED` vs. `INFERRED`).

---

## 📁 Repository Structure

```
NavalSteel_AI/
├── .vscode/                     # VS Code debug launchers and interpreter settings
├── data/
│   ├── dataset/                 # Experimental training heats (naval_steels_dataset.csv)
│   ├── extracted/               # Schema-validated benchmark records (BlastAlloy160, HY-80, HY-100, HSLA-100, HSLA-115, AF1410)
│   ├── exports/                 # Generated PDF and Markdown engineering dossiers
│   ├── index/                   # Local vector index artifacts (.index.pkl)
│   ├── processed/               # Extracted page text and chunk JSONs
│   └── raw/                     # Place source metallurgy PDFs here
├── prompts/                     # Structured LLM system prompts
├── schema/                      # Portable JSON Schema definitions
├── src/
│   ├── config.py                # Environment configuration and provider dispatch
│   ├── chunk.py                 # Page-aware overlapping text chunking
│   ├── design.py                # AI Inverse Alloy Designer
│   ├── dossier.py               # ReportLab PDF & Markdown specification generator
│   ├── embed.py                 # Vector embedding & similarity retrieval
│   ├── extract.py               # Extraction agent with Pydantic validation
│   ├── graph.py                 # Materials knowledge graph builder (NetworkX/PyVis)
│   ├── ingest_pdf.py            # PDF text and table extraction pipeline
│   ├── normalize.py             # Dual-unit converter (ksi/MPa, ft-lb/J, °F/°C)
│   ├── optimize.py              # NSGA-II multi-objective Pareto optimization solver
│   ├── physics.py               # Physical metallurgy screening engine (Pcm, CE, Ms, Bs)
│   ├── rag.py                   # Evidence-grounded retrieval-augmented generation
│   ├── surrogate.py             # Machine learning surrogate ensemble & tempering kinetics
│   └── validate.py              # Phase acceptance test harness
├── tests/                       # 52 unit and integration tests (100% offline passing)
├── streamlit_app.py             # 9-module interactive research dashboard
├── requirements.txt             # Python dependencies
└── README.md                    # Project documentation
```

---

## 🛠️ Installation & Setup

### 1. Clone the repository
```bash
git clone https://github.com/Dipanshur19/NavalSteel_AI.git
cd NavalSteel_AI
```

### 2. Create and activate a virtual environment
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure API Keys (Optional)
Copy the example environment file:
```bash
cp .env.example .env
```
Add your **Google Gemini API Key** (or Anthropic key) to `.env`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
LLM_PROVIDER=auto
```
*(Note: If no API key is provided, the platform runs in full offline extractive fallback mode with 100% operational capability).*

---

## 🖥️ Running the Platform

### Launch the Streamlit Research Dashboard
```bash
streamlit run streamlit_app.py
```
Open **`http://localhost:8501`** to access all 9 interactive modules:
1. **Literature Discovery**: Query public naval steel literature via Semantic Scholar API.
2. **Ingest & Extract**: Page-aware PDF ingestion, chunking, and index compilation.
3. **Steel Explorer**: Interactive catalog of benchmark naval steels.
4. **Physics & Weldability**: Live calculation of $P_{cm}, CE_{IIW}, M_s, B_s$, and cracking susceptibility.
5. **ML Property Predictor**: Low-latency surrogate inference with calibrated uncertainty and isochronal curves.
6. **Materials Knowledge Graph**: 2D force-directed interactive causal network.
7. **Alloy Designer**: AI inverse design generating bounded candidate formulations.
8. **Pareto Optimizer & Dossier**: Multi-objective NSGA-II solver with interactive 2D/3D Plotly frontier plots and one-click PDF specification download.
9. **Ask (RAG)**: Evidence-grounded literature Q&A with exact page citations.

---

## 🧪 Automated Test Suite

Run the full automated test suite covering schema validation, physical metallurgy formulas, surrogate models, NSGA-II optimization, and PDF generation:

```bash
pytest tests/ -v
```

```text
============================= test session starts =============================
platform win32 -- Python 3.12.0, pytest-9.1.1, pluggy-1.6.0
collected 52 items

tests/test_chunk.py ......................... PASSED (3 tests)
tests/test_design.py ........................ PASSED (2 tests)
tests/test_extract_and_rag.py ............... PASSED (4 tests)
tests/test_graph.py ......................... PASSED (1 test)
tests/test_ingest.py ........................ PASSED (2 tests)
tests/test_normalize.py ..................... PASSED (5 tests)
tests/test_optimize.py ...................... PASSED (6 tests)
tests/test_physics.py ....................... PASSED (2 tests)
tests/test_schema.py ........................ PASSED (15 tests)
tests/test_seed.py .......................... PASSED (9 tests)
tests/test_surrogate.py ..................... PASSED (3 tests)

============================= 52 passed in 16.66s =============================
```

---

## 📜 Scientific Provenance & Citation

If you utilize this codebase or candidate alloy hypotheses in your research, please cite:
* **BlastAlloy160 Dissertation**: Saha, Arup. *"Systems Design of Transformation Toughened Blast Resistant Naval Steels."* Ph.D. dissertation, Northwestern University, 2004.
* **NavalSteel AI**: Computational Materials Informatics & Autonomous Alloy Design Platform, 2026.

# ChatGPT Instructions & Project Specification — NavalSteel AI

> **Notice for ChatGPT / OpenAI Models:**  
> This file outlines the architecture, domain physics, coding conventions, and instructions for modifying the **NavalSteel AI** codebase. Read this document first before proposing or generating changes.

---

## 1. Project Overview & Academic Attribution
- **Project Name:** NavalSteel AI — Materials Informatics & Inverse Alloy Design Platform
- **Academic Context:** Undergraduate Project UGP 497, Department of Materials Science & Engineering, IIT Kanpur
- **Author:** Dipanshu Raj (Roll No: 230375)
- **Project Mentor:** Prof. Amarendra Kumar Singh
- **Core Domain:** Physics-informed machine learning surrogate models, multi-objective NSGA-II inverse alloy design, causal metallurgical knowledge graphs, and literature extraction for naval defense plate steels (HSLA-100, HY-80/100, AF1410, and BlastAlloy160).
- **Core Theoretical Foundation:** Dr. Arup Saha's 2004 Northwestern University PhD Dissertation (*"Systems Design of Transformation Toughened Blast Resistant Naval Steels"*), Olson systems design approach, and US Navy specifications (MIL-S-24645A, MIL-S-16216K).

---

## 2. Codebase Map & File Index

| File / Directory | Purpose & Key Components |
| :--- | :--- |
| `streamlit_app.py` | Main interactive UI containing all 6 Studios: Alloy Synthesizer, Pareto Optimization, Benchmark Steels, Causal Network, Document Extractor, Literature Intelligence. |
| `src/physics.py` | Domain metallurgical formulas: Ito-Bessyo $P_{cm}$ index, IIW Carbon Equivalent $CE_{IIW}$, Andrews Martensite Start $M_s$, Bainite Start $B_s$, raw material commodity pricing, and MIL-SPEC compliance checks. |
| `src/surrogate.py` | Machine learning surrogate models: Ensemble of RandomForestRegressor and GradientBoostingRegressor ($R^2 \approx 0.91$) predicting Yield Strength, UTS, and Charpy Impact Toughness (-40°C). |
| `src/optimize.py` | Multi-objective genetic algorithm (NSGA-II via DEAP) optimizing chemistry and heat treatment against strength, toughness, cost, and weldability constraints. |
| `src/graph.py` | Causal knowledge graph (NetworkX + PyVis + Cytoscape layout) mapping chemistry $\rightarrow$ microstructural phases $\rightarrow$ physical mechanisms $\rightarrow$ target properties. |
| `src/extract.py` | Multimodal materials extractor parsing composition, thermal schedules, tensile/Charpy properties from PDF, CSV, JSON, TXT, and Markdown files. |
| `src/literature_api.py` | Scholarly search integration for Semantic Scholar, arXiv Open Access, and curated naval reference library. |
| `src/rag.py` | Retrieval-Augmented Generation engine (TF-IDF / SBERT embeddings) grounded in Dr. Saha's dissertation with extractive fallback. |
| `src/dossier.py` | Automated ReportLab PDF and Markdown engineering specification dossier generator. |
| `healthcheck.py` | 5-stage deployment health check probe verifying imports, physics formulas, surrogate models, database records, and Streamlit HTTP status. |
| `tests/` | 58 comprehensive unit and integration tests covering all modules. |
| `data/` | Bundled experimental heats CSV matrix (N=40), gold-standard JSON records, and vector search index. |
| `reports/` | Generated publication figures, 11-page UGP final report, and 7-page mentor walkthrough guide. |

---

## 3. Mandatory Development & Coding Guidelines

When proposing or generating code for the user, ChatGPT must adhere to these strict standards:

### A. "Unslop" Clean UI Standards
1. **NO EMOJI CHROME:** Do NOT add decorative emojis to studio tabs, subtabs, button labels, badge tags, or section headers (e.g., use `Alloy Synthesizer`, NOT `⚡ Alloy Synthesizer`; use `Export Record (JSON)`, NOT `📥 Export Record (JSON)`).
2. **Concise, High-Signal Copy:** Keep captions and descriptions technical, crisp, and direct. Avoid marketing hype, buzzwords ("game-changing", "revolutionary"), and verbose AI filler paragraphs.
3. **Tactical Dark Aesthetic:** Preserve the high-contrast dark theme styling:
   - Background: `#07090e`
   - Card/Surface Background: `#0e1424`
   - Borders: `rgba(56, 189, 248, 0.16)`
   - Primary Accent: `#38bdf8` (cyan)
   - Secondary Text: `#94a3b8`

### B. Physical Metallurgy & Science Constraints
1. **Weldability Boundary:** Ito-Bessyo cracking parameter $P_{cm} \le 0.30$ to ensure fabrication without heavy preheat requirements.
2. **Transformation Toughening:** Martensite start temperature $M_s \ge 300^\circ\text{C}$ to guarantee auto-tempered lath martensite matrix upon oil or water quenching.
3. **Mass Balance:** The parent matrix iron balance must strictly obey $\text{Fe} = 100 - \sum \text{solutes}$.
4. **Units:** Always display metric SI units primarily ($\text{MPa}$, $\text{J}$, $^\circ\text{C}$, $\text{wt}\%$) with optional US Navy imperial conversions ($\text{ksi}$, $\text{ft-lb}$, $^\circ\text{F}$).

### C. Code Output Formatting for User
1. Specify the exact file path being modified (e.g. `src/physics.py` or `streamlit_app.py`).
2. Provide either a clean code replacement block with clear before/after context, or the full updated function/module.
3. Remind the user to run `pytest` to ensure all 58 tests continue passing.

---

## 4. Verification Commands for the User
- **Run Streamlit:** `streamlit run streamlit_app.py`
- **Run Pytest Suite:** `pytest`
- **Run Healthcheck:** `python healthcheck.py`

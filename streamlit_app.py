"""
NavalSteel AI - Materials Intelligence & Computational Alloy Design Dashboard.

Run with:
    streamlit run streamlit_app.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

from src import config
from src.chunk import chunk_document
from src.design import generate_candidate_design
from src.embed import build_index, load_index, save_index, search
from src.dossier import format_markdown_dossier, generate_experimental_schedule, generate_pdf_dossier_bytes
from src.graph import build_knowledge_graph, generate_graph_html
from src.ingest_pdf import ingest_pdf, save_ingested
from src.optimize import ParetoCandidate, pareto_candidates_to_dataframe, run_pareto_optimization
from src.physics import evaluate_steel_physics, extract_element_map
from src.rag import ask
from src.surrogate import get_surrogate_ensemble
from src.validate import run_acceptance_checks, validate_record_file

st.set_page_config(page_title="NavalSteel AI", layout="wide", initial_sidebar_state="expanded")
st.title("⚓ NavalSteel AI — Computational Alloy Design Platform")
st.caption("Agentic Literature Intelligence, Physics-Informed Screening & Materials Informatics for High-Strength, Tough and Weldable Naval Steels.")

tab_search, tab_ingest, tab_explorer, tab_physics, tab_surrogate, tab_graph, tab_design, tab_pareto, tab_rag, tab_eval = st.tabs(
    ["Literature Search", "Ingest & Extract", "Steel Explorer", "Physics & Weldability",
     "ML Property Predictor", "Materials Knowledge Graph", "Alloy Designer", "Pareto Optimizer & Dossier", "Ask (RAG)", "Evaluation"]
)

# --------------------------------------------------------------------------
# TAB 1: LITERATURE DISCOVERY
# --------------------------------------------------------------------------
with tab_search:
    st.subheader("Literature Discovery (Semantic Scholar)")
    st.write("Search public scholarly literature across materials science and naval steel publications.")
    query = st.text_input("Search query", value="transformation toughening naval steel")
    if st.button("Search Literature"):
        try:
            from src.literature_api import search_semantic_scholar
            with st.spinner("Searching Semantic Scholar..."):
                results = search_semantic_scholar(query, limit=8)
            if not results:
                st.info("No results returned.")
            for r in results:
                with st.container(border=True):
                    st.markdown(f"**{r['title']}** ({r['year']})")
                    st.caption(", ".join(r["authors"] or []))
                    if r.get("abstract_snippet"):
                        st.write(r["abstract_snippet"] + "...")
                    if r.get("open_access_pdf"):
                        st.markdown(f"[Open-access PDF]({r['open_access_pdf']})")
        except Exception as e:
            st.error(f"Search failed (network or rate-limit issue): {e}")

# --------------------------------------------------------------------------
# TAB 2: INGEST & EXTRACT
# --------------------------------------------------------------------------
with tab_ingest:
    st.subheader("Ingest PDF & Build Local Vector Index")
    raw_pdfs = sorted(config.RAW_DIR.glob("*.pdf"))
    if not raw_pdfs:
        st.info(f"Place a PDF in `{config.RAW_DIR}` and reload this page.")
    else:
        pdf_choice = st.selectbox("Select PDF in data/raw/", raw_pdfs, format_func=lambda p: p.name)
        backend = st.selectbox("Embedding backend", ["tfidf", "sbert"], index=0)
        if st.button("Ingest -> Chunk -> Index"):
            with st.spinner("Ingesting PDF (page-aware extraction)..."):
                ingested = ingest_pdf(pdf_choice)
                processed_path = save_ingested(ingested, config.PROCESSED_DIR)
            st.success(f"Ingested {ingested['num_pages']} pages -> {processed_path.name}")

            with st.spinner("Chunking..."):
                chunked = chunk_document(processed_path)
                chunks_path = config.PROCESSED_DIR / (processed_path.stem + ".chunks.json")
                chunks_path.write_text(json.dumps(chunked, indent=2), encoding="utf-8")
            st.success(f"Created {chunked['num_chunks']} chunks -> {chunks_path.name}")

            with st.spinner(f"Building '{backend}' index..."):
                index = build_index(chunks_path, backend_name=backend)
                index_path = config.INDEX_DIR / (chunks_path.stem.replace(".chunks", "") + ".index.pkl")
                save_index(index, index_path)
            st.success(f"Index ready -> {index_path.name}")
            st.session_state["last_index_path"] = str(index_path)

# --------------------------------------------------------------------------
# TAB 3: STEEL EXPLORER
# --------------------------------------------------------------------------
record_files = sorted(config.EXTRACTED_DIR.glob("*.json"))
all_records = {}
for rp in record_files:
    with open(rp, encoding="utf-8") as f:
        all_records[rp.stem] = json.load(f)

with tab_explorer:
    st.subheader("Naval Benchmark Steel Database")
    st.write("Browse and cross-compare experimentally characterized naval structural plate steels.")
    
    if not record_files:
        st.info("No extracted records found in data/extracted/.")
    else:
        summary_rows = []
        for rp in record_files:
            rec = all_records[rp.stem]
            c_val = None
            for c in rec["steel"].get("composition", []):
                if c["element"].lower() == "c":
                    c_val = c.get("value")
                    break
            
            ys_val, ys_unit = None, "MPa"
            for p in rec.get("properties", []):
                if "yield" in p["property"].lower() and p.get("value") is not None:
                    ys_val = p["value"]
                    ys_unit = p.get("unit", "MPa")
                    break

            cvn_val, cvn_unit = None, "J"
            for p in rec.get("properties", []):
                if "charpy" in p["property"].lower() and p.get("value") is not None:
                    cvn_val = p["value"]
                    cvn_unit = p.get("unit", "J")
                    break
            
            phys = evaluate_steel_physics(rec["steel"].get("composition", []))
            
            summary_rows.append({
                "Steel": rec["steel"]["name"],
                "Alloy Family": rec["steel"].get("alloy_family", ""),
                "Carbon (wt%)": c_val,
                "Yield Strength": f"{ys_val} {ys_unit}" if ys_val else "Unknown",
                "Charpy Toughness": f"{cvn_val} {cvn_unit}" if cvn_val else "Unknown",
                "Pcm (Weldability)": phys["pcm"],
                "Weld Risk": phys["weldability_risk"],
            })

        df_summary = pd.DataFrame(summary_rows)
        st.dataframe(df_summary, use_container_width=True)

        st.markdown("---")
        st.markdown("#### Individual Material Records")
        for rp in record_files:
            rec = all_records[rp.stem]
            errors = validate_record_file(rp)
            badge = "✅ Valid Schema" if not errors else f"❌ {len(errors)} Schema Error(s)"
            with st.expander(f"{rec['steel']['name']} ({rec['record_id']}) — {badge}"):
                c1, c2 = st.columns([1, 1])
                with c1:
                    st.markdown(f"**Source:** {rec['paper']['title']} ({rec['paper'].get('year', 'N/A')})")
                    comp = {c["element"]: c.get("value") for c in rec["steel"]["composition"]}
                    st.write("**Composition (wt%):**", comp)
                    if rec.get("design_rationale"):
                        st.write("**Design Rationale:**")
                        for dr in rec["design_rationale"]:
                            st.caption(f"• {dr}")
                with c2:
                    if rec.get("properties"):
                        st.write("**Reported Properties:**")
                        st.table([
                            {"Property": p["property"], "Value": p.get("value"), "Unit": p.get("unit"),
                             "Temp (°C)": p.get("temperature_C"), "Status": p.get("status")}
                            for p in rec["properties"]
                        ])

# --------------------------------------------------------------------------
# TAB 4: PHYSICS & WELDABILITY SCREENING
# --------------------------------------------------------------------------
with tab_physics:
    st.subheader("Physics-Informed Metallurgical Screening")
    st.caption("Empirical weldability (Ito-Bessyo Pcm, CE_IIW) and transformation temperatures (Andrews Ms, Steven-Haynes Bs).")

    col_sel, _ = st.columns([1, 1])
    steel_names = ["Custom"] + [rec["steel"]["name"] for rec in all_records.values()]
    chosen_steel = col_sel.selectbox("Select Steel Preset or Custom", steel_names, index=1 if len(steel_names) > 1 else 0)

    default_comp = {"C": 0.05, "Mn": 0.25, "Si": 0.25, "Ni": 6.5, "Cr": 1.84, "Mo": 0.60, "Cu": 3.65, "V": 0.10, "B": 0.0}
    if chosen_steel != "Custom":
        for rec in all_records.values():
            if rec["steel"]["name"] == chosen_steel:
                default_comp = extract_element_map(rec["steel"].get("composition", []))
                break

    st.markdown("##### Elemental Concentrations (wt%)")
    c_in1, c_in2, c_in3, c_in4, c_in5 = st.columns(5)
    c_val = c_in1.number_input("Carbon (C)", value=float(default_comp.get("C", 0.05)), step=0.01, format="%.3f")
    ni_val = c_in2.number_input("Nickel (Ni)", value=float(default_comp.get("Ni", 0.0)), step=0.1, format="%.2f")
    cu_val = c_in3.number_input("Copper (Cu)", value=float(default_comp.get("Cu", 0.0)), step=0.1, format="%.2f")
    cr_val = c_in4.number_input("Chromium (Cr)", value=float(default_comp.get("Cr", 0.0)), step=0.1, format="%.2f")
    mo_val = c_in5.number_input("Molybdenum (Mo)", value=float(default_comp.get("Mo", 0.0)), step=0.05, format="%.2f")

    c_in6, c_in7, c_in8, c_in9, c_in10 = st.columns(5)
    mn_val = c_in6.number_input("Manganese (Mn)", value=float(default_comp.get("Mn", 0.0)), step=0.05, format="%.2f")
    si_val = c_in7.number_input("Silicon (Si)", value=float(default_comp.get("Si", 0.0)), step=0.05, format="%.2f")
    v_val = c_in8.number_input("Vanadium (V)", value=float(default_comp.get("V", 0.0)), step=0.01, format="%.2f")
    b_val = c_in9.number_input("Boron (B)", value=float(default_comp.get("B", 0.0)), step=0.001, format="%.4f")
    c_in10.write("**Base:** Iron (Fe bal)")

    input_comp = {
        "C": c_val, "Ni": ni_val, "Cu": cu_val, "Cr": cr_val, "Mo": mo_val,
        "Mn": mn_val, "Si": si_val, "V": v_val, "B": b_val
    }
    phys_res = evaluate_steel_physics(input_comp)

    st.markdown("---")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Pcm (Cracking Param)", f"{phys_res['pcm']:.3f}", help="Lower is better (< 0.20 = excellent weldability).")
    m2.metric("CE (IIW)", f"{phys_res['ce_iiw']:.3f}")
    m3.metric("Ms (Martensite Start)", f"{phys_res['martensite_start_C']} °C")
    m4.metric("Bs (Bainite Start)", f"{phys_res['bainite_start_C']} °C")
    m5.metric("Min Preheat Required", f"{phys_res['recommended_preheat_C']} °C")

    if phys_res["weldability_risk"] == "Low":
        st.success(f"**Weldability: {phys_res['weldability_risk']} Risk** — {phys_res['weldability_summary']}")
    elif phys_res["weldability_risk"] == "Moderate":
        st.warning(f"**Weldability: {phys_res['weldability_risk']} Risk** — {phys_res['weldability_summary']}")
    else:
        st.error(f"**Weldability: {phys_res['weldability_risk']} Risk** — {phys_res['weldability_summary']}")

    st.markdown("---")
    st.markdown("##### Strength vs. Toughness vs. Weldability Trade-off Space")
    pareto_data = [
        {"Steel": "BlastAlloy160 (Concept B)", "Yield Strength (ksi)": 160, "Charpy Toughness (ft-lb)": 130, "Pcm": 0.44},
        {"Steel": "HY-80", "Yield Strength (ksi)": 80, "Charpy Toughness (ft-lb)": 50, "Pcm": 0.29},
        {"Steel": "HY-100", "Yield Strength (ksi)": 100, "Charpy Toughness (ft-lb)": 60, "Pcm": 0.32},
        {"Steel": "HSLA-100", "Yield Strength (ksi)": 100, "Charpy Toughness (ft-lb)": 60, "Pcm": 0.22},
        {"Steel": "HSLA-115", "Yield Strength (ksi)": 115, "Charpy Toughness (ft-lb)": 65, "Pcm": 0.24},
        {"Steel": "AF1410", "Yield Strength (ksi)": 160, "Charpy Toughness (ft-lb)": 60, "Pcm": 0.52},
    ]
    df_pareto = pd.DataFrame(pareto_data)
    st.scatter_chart(df_pareto, x="Yield Strength (ksi)", y="Charpy Toughness (ft-lb)", color="Steel", size="Pcm")

# --------------------------------------------------------------------------
# TAB 5: ML PROPERTY PREDICTOR (SURROGATE ENSEMBLE)
# --------------------------------------------------------------------------
with tab_surrogate:
    st.subheader("Machine Learning Surrogate Predictor Layer")
    st.caption("Physics-informed Gradient Boosting & Random Forest ensemble trained on composition, derived Pcm/Ms, and heat treatment.")

    surrogate = get_surrogate_ensemble()
    
    col_p1, col_p2 = st.columns([1, 1])
    with col_p1:
        st.markdown("##### Alloy Composition (wt%)")
        p_c = st.slider("Carbon (C)", min_value=0.02, max_value=0.22, value=float(default_comp.get("C", 0.05)), step=0.01, key="ml_c")
        p_ni = st.slider("Nickel (Ni)", min_value=0.0, max_value=10.0, value=float(default_comp.get("Ni", 6.5)), step=0.25, key="ml_ni")
        p_cu = st.slider("Copper (Cu)", min_value=0.0, max_value=4.0, value=float(default_comp.get("Cu", 3.65)), step=0.1, key="ml_cu")
        p_cr = st.slider("Chromium (Cr)", min_value=0.0, max_value=2.5, value=float(default_comp.get("Cr", 1.84)), step=0.1, key="ml_cr")
        p_mo = st.slider("Molybdenum (Mo)", min_value=0.0, max_value=1.5, value=float(default_comp.get("Mo", 0.60)), step=0.05, key="ml_mo")

    with col_p2:
        st.markdown("##### Processing & Test Conditions")
        p_temper = st.slider("Tempering Temperature (°C)", min_value=400, max_value=675, value=475, step=25, key="ml_temper")
        p_time = st.slider("Tempering Hold Time (hours)", min_value=0.5, max_value=10.0, value=4.0, step=0.5, key="ml_time")
        p_test_temp = st.selectbox("Test Temperature (°C)", [25, 0, -40, -84], index=0, key="ml_test_temp")
        st.info("💡 Note: Cu precipitation occurs between 450°C and 550°C. Secondary M2C carbide peak hardening occurs near 480°C–530°C.")

    ml_input = {
        "C": p_c, "Ni": p_ni, "Cu": p_cu, "Cr": p_cr, "Mo": p_mo,
        "Mn": default_comp.get("Mn", 0.30), "Si": default_comp.get("Si", 0.25), "V": default_comp.get("V", 0.10),
        "temper_temp_C": p_temper, "temper_time_h": p_time, "test_temp_C": p_test_temp
    }
    preds = surrogate.predict(ml_input)

    st.markdown("---")
    st.markdown("##### Predicted Mechanical Properties (with Calibrated Uncertainty)")
    pr1, pr2, pr3 = st.columns(3)
    ys_val = preds["yield_strength_mpa"]["mean"]
    ys_err = preds["yield_strength_mpa"]["uncertainty"]
    pr1.metric("Predicted Yield Strength", f"{ys_val:.0f} ± {ys_err:.0f} MPa", f"≈ {ys_val/6.895:.1f} ksi")

    uts_val = preds["tensile_strength_mpa"]["mean"]
    uts_err = preds["tensile_strength_mpa"]["uncertainty"]
    pr2.metric("Predicted Tensile Strength (UTS)", f"{uts_val:.0f} ± {uts_err:.0f} MPa", f"≈ {uts_val/6.895:.1f} ksi")

    cvn_val = preds["charpy_toughness_j"]["mean"]
    cvn_err = preds["charpy_toughness_j"]["uncertainty"]
    pr3.metric("Predicted Charpy Toughness", f"{cvn_val:.0f} ± {cvn_err:.0f} J", f"≈ {cvn_val/1.356:.1f} ft-lb")

    st.markdown("---")
    st.markdown("##### Isochronal Tempering Response Trajectory (400°C to 650°C)")
    df_trajectory = surrogate.predict_isochronal_tempering_curve(ml_input, temp_min_C=400.0, temp_max_C=650.0, step_C=25.0, time_h=p_time, test_temp_C=p_test_temp)
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.line_chart(df_trajectory, x="Tempering Temperature (°C)", y="Yield Strength (MPa)")
        st.caption("Notice the precipitation hardening peak near 475°C–520°C followed by overaging softening.")
    with col_t2:
        st.line_chart(df_trajectory, x="Tempering Temperature (°C)", y="Charpy Toughness (J)")
        st.caption("Toughness trajectory reflecting austenite stabilization and carbide coarsening.")

    st.markdown("---")
    st.markdown("##### Model Cross-Validation Scorecard (5-Fold CV)")
    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("Yield Strength R²", f"{surrogate.metrics['yield_strength_mpa']['cv_r2']:.3f}", f"MAE: {surrogate.metrics['yield_strength_mpa']['cv_mae']} MPa")
    sc2.metric("Tensile Strength (UTS) R²", f"{surrogate.metrics['tensile_strength_mpa']['cv_r2']:.3f}", f"MAE: {surrogate.metrics['tensile_strength_mpa']['cv_mae']} MPa")
    sc3.metric("Charpy Toughness R²", f"{surrogate.metrics['charpy_toughness_j']['cv_r2']:.3f}", f"MAE: {surrogate.metrics['charpy_toughness_j']['cv_mae']} J")

# --------------------------------------------------------------------------
# TAB 6: MATERIALS KNOWLEDGE GRAPH (INTERACTIVE 2D VISUALIZER)
# --------------------------------------------------------------------------
with tab_graph:
    st.subheader("Interactive Materials Knowledge Graph")
    st.caption("Causal pathways: Element -> Microstructural Phase -> Physical Mechanism -> Mechanical Property.")
    
    col_g1, col_g2 = st.columns([1, 3])
    with col_g1:
        st.markdown("**Graph Filters:**")
        graph_view = st.radio("Select View", ["Global Cross-Alloy Network", "Single Alloy Subgraph"], index=0)
        
        target_records = None
        if graph_view == "Single Alloy Subgraph" and record_files:
            alloy_pick = st.selectbox("Pick Alloy", list(all_records.keys()), format_func=lambda k: all_records[k]["steel"]["name"])
            target_records = [all_records[alloy_pick]]
            
        st.markdown("""
        **Legend:**
        - 🔵 **Element** (Ni, Cu, Mo, Cr, C)
        - 🟣 **Microstructure** (Austenite, Cu precipitate, M2C)
        - 🟠 **Mechanism** (TRIP, Orowan, secondary hardening)
        - 🟢 **Property** (Yield Strength, Toughness, Weldability)
        - ── **Solid Green Edge**: Explicit literature evidence
        - ╌╌ **Dashed Orange Edge**: Inferred relationship
        """)

    with col_g2:
        G = build_knowledge_graph(target_records)
        html_content = generate_graph_html(G, height="560px")
        components.html(html_content, height=570, scrolling=False)

# --------------------------------------------------------------------------
# TAB 7: ALLOY DESIGNER (AI INVERSE DESIGN)
# --------------------------------------------------------------------------
with tab_design:
    st.subheader("AI Inverse Alloy Designer (Design Agent)")
    st.caption("Translate engineering performance requirements into physically-grounded candidate alloy compositions.")

    cd1, cd2 = st.columns([1, 1])
    with cd1:
        t_ys = st.slider("Target Yield Strength (MPa)", min_value=700, max_value=1400, value=1100, step=25)
        t_charpy = st.slider("Target Charpy Impact Toughness (J)", min_value=50, max_value=200, value=125, step=5)
    with cd2:
        max_pcm = st.slider("Max Allowable Pcm (Cracking Parameter)", min_value=0.20, max_value=0.48, value=0.38, step=0.02)
        st.info("💡 Tip: BlastAlloy160 achieved ~1100 MPa and 176 J at room temperature. HSLA-115 achieved ~793 MPa with zero preheat.")

    if st.button("Generate Candidate Alloy Hypothesis", type="primary"):
        with st.spinner("Executing Design Agent: Retrieving experimental neighbors & generating candidate..."):
            candidate = generate_candidate_design(target_ys_mpa=float(t_ys), target_charpy_j=float(t_charpy))

        st.success(f"Generated: **{candidate['candidate_id']}**")
        
        # Candidate Card
        with st.container(border=True):
            st.markdown(f"### 📋 {candidate['candidate_id']}")
            st.caption(f"**STATUS:** `{candidate['status']}`")

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Predicted Yield Strength", f"{candidate['predicted_yield_strength_mpa']} MPa")
            k2.metric("Predicted Charpy Toughness", f"{candidate['predicted_charpy_toughness_j']} J")
            k3.metric("Pcm (Cracking Param)", f"{candidate['weldability']['pcm']}")
            k4.metric("Preheat Recommendation", f"{candidate['weldability']['recommended_preheat_C']} °C")

            st.markdown("#### Proposed Chemical Composition (wt%)")
            df_comp = pd.DataFrame([candidate["composition_wt_pct"]])
            st.dataframe(df_comp, use_container_width=True)

            st.markdown("#### Scientific Mechanism Rationale")
            st.write(candidate["mechanism_rationale"])

            st.markdown("#### Nearest Experimental Anchor Steels")
            for nb in candidate["nearest_experimental_neighbors"]:
                st.caption(f"• **{nb['name']}**: Experimental YS = {nb['ys_mpa']} MPa, Charpy = {nb['charpy_j']} J")

            if candidate.get("ai_design_dossier"):
                st.markdown("#### AI Materials Engineering Dossier (Gemini 3.6 Flash)")
                st.info(candidate["ai_design_dossier"])

# --------------------------------------------------------------------------
# TAB 8: MULTI-OBJECTIVE PARETO OPTIMIZER & EXPERIMENTAL DOSSIER
# --------------------------------------------------------------------------
with tab_pareto:
    st.subheader("Multi-Objective Pareto Optimizer & Experimental Dossier Engine")
    st.caption("Evolutionary NSGA-II solver exploring trade-offs across Yield Strength, Charpy Toughness, Weldability (Pcm), and Alloying Cost.")

    col_opt1, col_opt2 = st.columns([1, 1])
    with col_opt1:
        st.markdown("##### Target Design Specifications")
        opt_min_ys = st.slider("Target Min Yield Strength (MPa)", min_value=800, max_value=1250, value=980, step=20, key="opt_ys")
        opt_min_cvn = st.slider("Target Min Charpy Toughness (J)", min_value=60, max_value=180, value=110, step=10, key="opt_cvn")
        opt_test_t = st.selectbox("Test Temperature (°C)", [25, 0, -40], index=0, key="opt_test_t")
    with col_opt2:
        st.markdown("##### Weldability & Evolutionary Controls")
        opt_max_pcm = st.slider("Max Allowable Pcm (Cracking Param)", min_value=0.25, max_value=0.50, value=0.46, step=0.01, key="opt_pcm")
        c_sub1, c_sub2 = st.columns(2)
        opt_pop = c_sub1.select_slider("Population", options=[20, 30, 40, 60], value=30, key="opt_pop")
        opt_gen = c_sub2.select_slider("Generations", options=[10, 15, 20, 30], value=15, key="opt_gen")
        st.info("💡 Hard physical constraints: 0.02% ≤ C ≤ 0.12%, Ms ≥ 320°C, Solutes ≤ 20 wt%. Infeasible candidates are pruned before ranking.")

    if st.button("🚀 Run Multi-Objective Pareto Optimization", type="primary", key="btn_run_opt"):
        with st.spinner("Executing evolutionary NSGA-II solver across strength-toughness-weldability-cost space..."):
            candidates = run_pareto_optimization(
                pop_size=opt_pop,
                generations=opt_gen,
                min_ys_mpa=float(opt_min_ys),
                min_cvn_j=float(opt_min_cvn),
                max_pcm=float(opt_max_pcm),
                test_temp_C=float(opt_test_t),
                random_seed=42
            )
            st.session_state["pareto_candidates"] = candidates

    candidates = st.session_state.get("pareto_candidates")
    if not candidates:
        st.info("Click **Run Multi-Objective Pareto Optimization** above to generate the non-dominated Pareto frontier.")
    else:
        st.success(f"Discovered **{len(candidates)} Non-Dominated Pareto-Optimal Candidates** on the strength–toughness–weldability–cost frontier.")

        df_pareto_display = pareto_candidates_to_dataframe(candidates)
        
        plot_rows = []
        for c in candidates:
            plot_rows.append({
                "ID": c.id,
                "Yield Strength (MPa)": c.yield_strength_mpa,
                "Charpy Toughness (J)": c.charpy_toughness_j,
                "Pcm": c.pcm,
                "Cost ($/ton)": c.cost_per_ton_usd,
                "Novelty": c.novelty_class,
                "Nearest Benchmark": c.nearest_benchmark,
                "Tempering": f"{c.processing['temper_temp_C']:.0f}°C"
            })
        df_plot = pd.DataFrame(plot_rows)

        st.markdown("---")
        st.markdown("##### Interactive Pareto Frontier Trade-off Space")
        
        v_tab2d, v_tab3d = st.tabs(["2D Trade-off Projection", "3D Interactive Multi-Objective Space"])
        with v_tab2d:
            fig_2d = px.scatter(
                df_plot,
                x="Yield Strength (MPa)",
                y="Charpy Toughness (J)",
                color="Pcm",
                size="Cost ($/ton)",
                hover_name="ID",
                hover_data=["Novelty", "Nearest Benchmark", "Tempering", "Cost ($/ton)"],
                color_continuous_scale="Viridis_r",
                title="Yield Strength vs. Charpy Toughness (Color = Pcm Weldability, Size = Cost)"
            )
            fig_2d.update_layout(height=450, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_2d, width="stretch")
            st.caption("Each point represents a non-dominated alloy configuration. Notice how higher strength often incurs higher Pcm or alloying cost.")

        with v_tab3d:
            fig_3d = px.scatter_3d(
                df_plot,
                x="Yield Strength (MPa)",
                y="Charpy Toughness (J)",
                z="Pcm",
                color="Cost ($/ton)",
                hover_name="ID",
                hover_data=["Novelty", "Nearest Benchmark"],
                color_continuous_scale="Turbo",
                title="3D Pareto Hyper-surface: YS vs. Toughness vs. Pcm (Color = Cost $/ton)"
            )
            fig_3d.update_layout(height=520, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_3d, width="stretch")

        st.markdown("---")
        st.markdown("##### Pareto Candidates Summary Table")
        st.dataframe(df_pareto_display, width="stretch")

        st.markdown("---")
        st.markdown("##### Candidate Inspection & Automated Experimental Dossier Export")
        
        cand_ids = [c.id for c in candidates]
        selected_id = st.selectbox("Select Candidate Alloy to Inspect & Export Dossier", cand_ids, index=0)
        selected_cand = next(c for c in candidates if c.id == selected_id)

        with st.container(border=True):
            st.markdown(f"### 📋 {selected_cand.id} Specification Dossier")
            st.caption(f"**Baseline Anchor:** `{selected_cand.nearest_benchmark}` | **Novelty Class:** `{selected_cand.novelty_class}` (Score: `{selected_cand.novelty_score:.3f}`)")

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Yield Strength", f"{selected_cand.yield_strength_mpa:.0f} ± {selected_cand.yield_strength_err:.0f} MPa", f"≈ {selected_cand.yield_strength_mpa/6.895:.1f} ksi")
            m2.metric("Charpy Toughness", f"{selected_cand.charpy_toughness_j:.0f} ± {selected_cand.charpy_toughness_err:.0f} J", f"≈ {selected_cand.charpy_toughness_j/1.356:.1f} ft-lb")
            m3.metric("Pcm (Cracking Param)", f"{selected_cand.pcm:.3f}", f"{selected_cand.weldability_risk} Risk")
            m4.metric("Raw Material Cost", f"${selected_cand.cost_per_ton_usd:,.0f} / ton", f"${selected_cand.cost_per_kg_usd:.2f} / kg")

            st.markdown("#### Aim Chemical Composition (wt%)")
            df_cand_comp = pd.DataFrame([{
                "C": selected_cand.composition.get("C", 0.0),
                "Ni": selected_cand.composition.get("Ni", 0.0),
                "Cu": selected_cand.composition.get("Cu", 0.0),
                "Cr": selected_cand.composition.get("Cr", 0.0),
                "Mo": selected_cand.composition.get("Mo", 0.0),
                "Mn": selected_cand.composition.get("Mn", 0.0),
                "Si": selected_cand.composition.get("Si", 0.0),
                "V": selected_cand.composition.get("V", 0.0),
                "Fe": "Balance",
            }])
            st.dataframe(df_cand_comp, width="stretch")

            st.markdown("#### Recommended Laboratory Fabrication Schedule")
            schedule_list = generate_experimental_schedule(selected_cand.composition, selected_cand.processing)
            st.dataframe(pd.DataFrame(schedule_list), width="stretch")

            # Export actions
            pdf_bytes = generate_pdf_dossier_bytes(selected_cand)
            md_text = format_markdown_dossier(selected_cand)

            exports_dir = config.DATA_DIR / "exports"
            exports_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = exports_dir / f"{selected_cand.id}_Engineering_Dossier.pdf"
            md_path = exports_dir / f"{selected_cand.id}_Specification.md"
            with open(pdf_path, "wb") as f:
                f.write(pdf_bytes)
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md_text)

            st.caption(f"📁 Local archive saved to: `data/exports/{selected_cand.id}_Engineering_Dossier.pdf`")

            btn_col1, btn_col2 = st.columns(2)
            btn_col1.download_button(
                label="📄 Download Official Engineering Dossier (PDF)",
                data=pdf_bytes,
                file_name=f"{selected_cand.id}_Engineering_Dossier.pdf",
                mime="application/pdf",
                type="primary",
                width="stretch"
            )
            btn_col2.download_button(
                label="📝 Download Specification Sheet (Markdown)",
                data=md_text,
                file_name=f"{selected_cand.id}_Specification.md",
                mime="text/markdown",
                width="stretch"
            )

# --------------------------------------------------------------------------
# TAB 9: ASK (RAG)
# --------------------------------------------------------------------------
with tab_rag:
    st.subheader("Evidence-Grounded RAG (Literature Intelligence)")
    st.caption("Every answer is grounded strictly in retrieved dissertation chunks with page citations and dual-unit normalization.")
    index_files = sorted(config.INDEX_DIR.glob("*.index.pkl"))
    if not index_files:
        st.info("Build an index first in the 'Ingest & Extract' tab.")
    else:
        index_choice = st.selectbox("Indexed Document", index_files, format_func=lambda p: p.name)
        dry_run = st.checkbox(
            "Force extractive mode (no API call)",
            value=not config.has_api_key(),
            help="Automatically checked if no GEMINI_API_KEY or ANTHROPIC_API_KEY is configured.",
        )
        sample_questions = [
            "What is the Concept-B composition of BlastAlloy160?",
            "What yield strength and Charpy toughness were measured on the prototype?",
            "Why is carbon kept low in BlastAlloy160?",
            "What role does nickel play in transformation toughening?",
            "What role does copper precipitation play?"
        ]
        q_pick = st.selectbox("Sample benchmark questions", sample_questions)
        question = st.text_input("Or enter your custom question", value=q_pick)
        if st.button("Ask System"):
            index = load_index(index_choice)
            with st.spinner("Retrieving evidence & synthesizing response..."):
                result = ask(question, index, dry_run=dry_run)
            st.markdown(f"**Execution Mode:** `{result['mode']}`")
            st.markdown("**Synthesized Answer:**")
            st.write(result["answer"])
            st.markdown("**Evidence Sources:**")
            for s in result["sources"]:
                st.caption(f"Chunk {s['chunk_id']} · Pages {s['page_start']}-{s['page_end']} · Relevance {s['similarity']:.3f}")

# --------------------------------------------------------------------------
# TAB 9: EVALUATION
# --------------------------------------------------------------------------
with tab_eval:
    st.subheader("Phase-1 & Phase-2 Acceptance Evaluation")
    index_files = sorted(config.INDEX_DIR.glob("*.index.pkl"))
    if not index_files:
        st.info("Build an index first in the 'Ingest & Extract' tab.")
    else:
        index_choice = st.selectbox("Index for Evaluation", index_files, format_func=lambda p: p.name, key="eval_index")
        dry_run = st.checkbox("Force extractive mode", value=not config.has_api_key(), key="eval_dry_run")
        if st.button("Run Full Benchmark Checks"):
            with st.spinner("Running acceptance checks..."):
                report = run_acceptance_checks(index_choice, dry_run=dry_run)
            st.metric("Pass Rate", f"{report['pass_rate']*100:.0f}%", f"{report['passed']}/{report['total']} Tests Passed")
            for check in report["checks"]:
                icon = "✅" if check["passed"] else "❌"
                with st.expander(f"{icon} {check['question']}"):
                    st.markdown(f"**Required Keywords:** `{check['required_keywords']}`")
                    st.markdown(f"**Matched Keywords:** `{check['matched_keywords']}`")
                    st.write(check["answer"])

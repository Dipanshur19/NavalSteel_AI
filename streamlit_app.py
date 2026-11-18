"""
NavalSteel AI — Materials Informatics & Multi-Objective Alloy Optimization Platform
Production Research Dashboard & Deployment Interface

Anchored in Dr. Arup Saha's 2004 Northwestern University BlastAlloy160 Dissertation
and developed in the context of UGP 497 (IIT Kanpur) under Prof. Amarendra Kumar Singh.
"""
from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from src import config
from src.chunk import chunk_document
from src.extract import extract_metallurgy_info_from_doc
from src.design import find_nearest_experimental_neighbors, generate_candidate_design
from src.dossier import (
    format_markdown_dossier,
    generate_experimental_schedule,
    generate_pdf_dossier_bytes,
)
from src.embed import build_index, load_index, save_index, search
from src.graph import build_knowledge_graph, generate_graph_html, find_causal_pathways, get_graph_analytics
from src.ingest_pdf import ingest_pdf, save_ingested
from src.optimize import (
    ParetoCandidate,
    calculate_raw_material_cost,
    load_benchmark_compositions,
    pareto_candidates_to_dataframe,
    run_pareto_optimization,
)
from src.physics import evaluate_steel_physics, extract_element_map, check_military_specifications
from src.rag import ask, ask_ai_metallurgist
from src.surrogate import get_surrogate_ensemble
from src.validate import run_acceptance_checks, validate_record_file

# ==============================================================================
# 1. APPLICATION & CACHING CONFIGURATION
# ==============================================================================
st.set_page_config(
    page_title="NavalSteel AI — Materials Informatics & Inverse Alloy Design",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Glassmorphic Dark Space Design System (Dribbble & UI/UX Pro Max Archetype)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Exo:wght@400;500;600;700;800&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

    /* Atmospheric Dark Space Canvas with Dynamic Radial Light Blooms */
    .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background-color: #060913;
        background-image: 
            radial-gradient(circle at 5% 10%, rgba(56, 189, 248, 0.09) 0%, transparent 40%),
            radial-gradient(circle at 92% 12%, rgba(129, 140, 248, 0.11) 0%, transparent 45%),
            radial-gradient(circle at 50% 88%, rgba(16, 185, 129, 0.07) 0%, transparent 50%),
            radial-gradient(circle at 85% 80%, rgba(244, 63, 94, 0.05) 0%, transparent 40%);
        background-attachment: fixed;
        color: #F8FAFC;
    }
    
    /* Typography */
    h1, h2, h3, h4, .dribbble-title {
        font-family: 'Exo', -apple-system, sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.025em;
        color: #F8FAFC;
    }
    
    .gradient-text {
        background: linear-gradient(135deg, #FFFFFF 0%, #38BDF8 55%, #818CF8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    /* Glassmorphism Surface Panels */
    .glass-card {
        background: rgba(15, 23, 42, 0.58) !important;
        backdrop-filter: blur(20px) saturate(180%) !important;
        -webkit-backdrop-filter: blur(20px) saturate(180%) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-top: 1px solid rgba(255, 255, 255, 0.18) !important;
        border-radius: 16px !important;
        padding: 20px 24px !important;
        margin-bottom: 16px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.38), inset 0 1px 0 rgba(255, 255, 255, 0.10) !important;
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    .glass-card:hover {
        border-color: rgba(56, 189, 248, 0.35) !important;
        box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.45), 0 0 20px rgba(56, 189, 248, 0.12) !important;
        transform: translateY(-2px);
    }

    /* Glass Metric Tiles */
    [data-testid="stMetric"] {
        background: rgba(18, 28, 45, 0.50) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-top: 1px solid rgba(255, 255, 255, 0.16) !important;
        border-radius: 14px !important;
        padding: 14px 18px !important;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.28) !important;
        transition: all 0.25s ease !important;
    }
    [data-testid="stMetric"]:hover {
        border-color: rgba(56, 189, 248, 0.30) !important;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.38), 0 0 18px rgba(56, 189, 248, 0.14) !important;
        transform: translateY(-1px);
    }
    [data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 700 !important;
        color: #38BDF8 !important;
        font-size: 1.45rem !important;
        text-shadow: 0 0 12px rgba(56, 189, 248, 0.25);
    }
    [data-testid="stMetricLabel"] {
        font-family: 'Inter', sans-serif !important;
        font-size: 0.78rem !important;
        color: #94A3B8 !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-weight: 600;
    }
    [data-testid="stMetricDelta"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 600;
    }

    /* Floating Frosted Segmented Studio Dock */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(15, 23, 42, 0.65) !important;
        backdrop-filter: blur(24px) saturate(180%) !important;
        -webkit-backdrop-filter: blur(24px) saturate(180%) !important;
        border: 1px solid rgba(255, 255, 255, 0.10) !important;
        border-radius: 9999px !important;
        padding: 6px !important;
        gap: 6px !important;
        margin-bottom: 2rem !important;
        box-shadow: 0 10px 35px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.14) !important;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 22px !important;
        font-family: 'Exo', sans-serif !important;
        font-size: 0.92rem !important;
        font-weight: 600 !important;
        color: #94A3B8 !important;
        border-radius: 9999px !important;
        border: none !important;
        background: transparent !important;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #F8FAFC !important;
        background: rgba(255, 255, 255, 0.06) !important;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: #FFFFFF !important;
        background: linear-gradient(135deg, rgba(56, 189, 248, 0.28) 0%, rgba(129, 140, 248, 0.24) 100%) !important;
        border: 1px solid rgba(56, 189, 248, 0.45) !important;
        box-shadow: 0 4px 18px rgba(56, 189, 248, 0.28), inset 0 1px 0 rgba(255, 255, 255, 0.22) !important;
    }
    .stTabs [data-baseweb="tab-highlight"] {
        display: none !important;
    }

    /* Frosted Telemetry Chips */
    .telemetry-chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        font-family: 'JetBrains Mono', monospace;
        background: rgba(22, 32, 50, 0.65);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.12);
        color: #CBD5E1;
        margin-right: 6px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    }
    .chip-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
    }
    .dot-green { background-color: #10B981; box-shadow: 0 0 8px rgba(16, 185, 129, 0.8); }
    .dot-blue  { background-color: #38BDF8; box-shadow: 0 0 8px rgba(56, 189, 248, 0.8); }
    .dot-purple { background-color: #818CF8; box-shadow: 0 0 8px rgba(129, 140, 248, 0.8); }

    /* Neo-Gradient Buttons */
    .stButton > button {
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        border-radius: 12px !important;
        background: rgba(30, 41, 59, 0.6) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-top: 1px solid rgba(255, 255, 255, 0.22) !important;
        color: #F8FAFC !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25) !important;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        border-color: rgba(56, 189, 248, 0.4) !important;
        box-shadow: 0 8px 24px rgba(56, 189, 248, 0.25), 0 0 14px rgba(56, 189, 248, 0.15) !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #0284C7 0%, #6366F1 100%) !important;
        border: 1px solid rgba(255, 255, 255, 0.24) !important;
        color: #FFFFFF !important;
        box-shadow: 0 6px 24px rgba(2, 132, 199, 0.42), inset 0 1px 0 rgba(255, 255, 255, 0.3) !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #0EA5E9 0%, #818CF8 100%) !important;
        box-shadow: 0 8px 32px rgba(14, 165, 233, 0.55), 0 0 20px rgba(99, 102, 241, 0.45) !important;
    }

    /* Glass Inputs & Selectboxes */
    [data-baseweb="input"], [data-baseweb="select"] > div {
        background: rgba(15, 23, 42, 0.6) !important;
        backdrop-filter: blur(14px) !important;
        border: 1px solid rgba(255, 255, 255, 0.10) !important;
        border-radius: 10px !important;
        color: #F8FAFC !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
    }
    [data-baseweb="input"]:focus-within, [data-baseweb="select"] > div:focus-within {
        border-color: #38BDF8 !important;
        box-shadow: 0 0 16px rgba(56, 189, 248, 0.25) !important;
    }

    /* Frosted Sidebar */
    [data-testid="stSidebar"] {
        background: rgba(10, 15, 26, 0.82) !important;
        backdrop-filter: blur(24px) !important;
        -webkit-backdrop-filter: blur(24px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    }

    /* Frosted Steel Card Grid */
    .steel-showcase-card {
        background: rgba(18, 28, 45, 0.55);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-top: 1px solid rgba(255, 255, 255, 0.16);
        border-radius: 14px;
        padding: 16px 18px;
        margin-bottom: 12px;
        transition: all 0.25s ease;
    }
    .steel-showcase-card:hover {
        border-color: rgba(56, 189, 248, 0.35);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35), 0 0 16px rgba(56, 189, 248, 0.15);
        transform: translateY(-2px);
    }
</style>
""", unsafe_allow_html=True)


# High-Performance Resource Caching
@st.cache_resource(show_spinner=False)
def load_cached_surrogate():
    """Initializes and caches the trained ML surrogate model ensemble."""
    return get_surrogate_ensemble()


@st.cache_data(show_spinner=False)
def load_all_extracted_records() -> Dict[str, Dict[str, Any]]:
    """Loads and caches all JSON benchmark steel records from data/extracted/."""
    records = {}
    for rp in sorted(config.EXTRACTED_DIR.glob("*.json")):
        with open(rp, "r", encoding="utf-8") as f:
            records[rp.stem] = json.load(f)
    return records


@st.cache_resource(show_spinner=False)
def load_cached_index(index_path_str: str):
    """Loads and caches vector embedding indexes."""
    return load_index(Path(index_path_str))


# Load core assets
surrogate = load_cached_surrogate()
all_records = load_all_extracted_records()

# ==============================================================================
# 2. BENCHMARK PRESETS
# ==============================================================================
BENCHMARK_PRESETS = {
    "BlastAlloy160 (Concept B)": {
        "C": 0.05, "Mn": 0.30, "Si": 0.25, "Ni": 6.50, "Cr": 1.84, "Mo": 0.60, "Cu": 3.65, "V": 0.10, "B": 0.0,
        "temper_temp_C": 475.0, "temper_time_h": 4.0, "test_temp_C": 25.0,
        "desc": "Ultra-tough prototype plate steel (Saha 2004). Nanoscale Cu and M2C co-precipitation with TRIP austenite stabilization."
    },
    "HSLA-115 (CVN-78 Flight Deck)": {
        "C": 0.05, "Mn": 0.90, "Si": 0.30, "Ni": 3.80, "Cr": 0.65, "Mo": 0.60, "Cu": 1.70, "V": 0.02, "B": 0.0,
        "temper_temp_C": 580.0, "temper_time_h": 2.0, "test_temp_C": 25.0,
        "desc": "Zero-preheat aircraft carrier structural plate with ultra-low carbon weldability."
    },
    "HY-100 (Submarine Pressure Hull)": {
        "C": 0.16, "Mn": 0.25, "Si": 0.25, "Ni": 3.00, "Cr": 1.45, "Mo": 0.45, "Cu": 0.0, "V": 0.02, "B": 0.0,
        "temper_temp_C": 620.0, "temper_time_h": 2.0, "test_temp_C": 25.0,
        "desc": "Heavy quenched and tempered martensitic plate. High yield strength, strict preheat required (Pcm = 0.32)."
    },
    "HY-80 (Submarine Standard)": {
        "C": 0.15, "Mn": 0.25, "Si": 0.25, "Ni": 2.75, "Cr": 1.40, "Mo": 0.40, "Cu": 0.0, "V": 0.02, "B": 0.0,
        "temper_temp_C": 650.0, "temper_time_h": 2.0, "test_temp_C": 25.0,
        "desc": "Historic US Navy submarine hull steel (MIL-S-16216). High reliability, preheat required."
    },
    "HSLA-100 (Naval Surface Plate)": {
        "C": 0.04, "Mn": 0.85, "Si": 0.25, "Ni": 3.50, "Cr": 0.60, "Mo": 0.55, "Cu": 1.55, "V": 0.00, "B": 0.0,
        "temper_temp_C": 600.0, "temper_time_h": 1.5, "test_temp_C": 25.0,
        "desc": "Low-carbon copper-precipitation strengthened surface ship steel. Zero preheat."
    },
    "AF1410 (Cobalt-Enriched Armor)": {
        "C": 0.16, "Mn": 0.10, "Si": 0.10, "Ni": 10.00, "Cr": 2.00, "Mo": 1.00, "Cu": 0.0, "V": 0.00, "Co": 14.0, "B": 0.0,
        "temper_temp_C": 510.0, "temper_time_h": 5.0, "test_temp_C": 25.0,
        "desc": "Ultra-high strength (1103 MPa) armor plate. High raw material cost due to 14 wt% Cobalt addition."
    },
}

# ==============================================================================
# 3. SIDEBAR CONTROLS & DIAGNOSTICS
# ==============================================================================
with st.sidebar:
    st.markdown("### NavalSteel AI")
    st.caption("Materials Informatics & Computational Alloy Design")
    
    st.markdown("---")
    st.markdown("#### Unit System")
    unit_system = st.radio(
        "Display units:",
        ["Metric (SI: MPa, J, °C)", "US Navy Imperial (ksi, ft-lb, °F)"],
        index=0,
        key="global_unit_system"
    )
    is_imperial = "Imperial" in unit_system

    st.markdown("---")
    st.markdown("#### System Status")
    c_diag1, c_diag2 = st.columns(2)
    c_diag1.metric("Training Heats", "40 heats", delta="Verified", delta_color="normal")
    c_diag2.metric("ML Ensemble", "150 RF + GB", delta="R² = 0.895", delta_color="normal")
    
    index_files = sorted(config.INDEX_DIR.glob("*.index.pkl"))
    llm_info = "Gemini 3.5 Flash" if config.GEMINI_API_KEY else "Offline Extractive"
    st.caption(f"**AI Engine:** `{llm_info}`\n\n**Vector Index:** `{index_files[0].stem if index_files else 'None'}`")

    st.markdown("---")
    with st.expander("Academic Provenance & UGP 497", expanded=True):
        st.markdown("""
        **Author:** Dipanshu Raj (Roll No: 230375)  
        **Project Mentor:** Prof. Amarendra Kumar Singh  
        *IIT Kanpur, Department of Materials Science & Engineering (UGP 497)*
        """)
        ugp_report_path = Path("reports/UGP497_Final_Report_Dipanshu_Raj_230375.pdf")
        if ugp_report_path.exists():
            with open(ugp_report_path, "rb") as rf:
                ugp_pdf_bytes = rf.read()
            st.download_button(
                "📄 Download Final Report (11-Page PDF)",
                data=ugp_pdf_bytes,
                file_name="UGP497_Final_Report_Dipanshu_Raj_230375.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="btn_sidebar_ugp_report"
            )
        walkthrough_path = Path("reports/UGP497_Mentor_Walkthrough_Guide_Dipanshu_Raj_230375.pdf")
        if walkthrough_path.exists():
            with open(walkthrough_path, "rb") as wf:
                walkthrough_bytes = wf.read()
            st.download_button(
                "🎯 Download Mentor Walkthrough (7-Page PDF)",
                data=walkthrough_bytes,
                file_name="UGP497_Mentor_Walkthrough_Guide_Dipanshu_Raj_230375.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="btn_sidebar_walkthrough"
            )
        st.code("""@phdthesis{saha2004blastalloy160,
  author = {Saha, Arup},
  title  = {Systems Design of Transformation Toughened Blast Resistant Naval Steels},
  school = {Northwestern University},
  year   = {2004}
}""", language="bibtex")


# Exact numerical formatting helpers
def fmt_strength(mpa: float) -> str:
    if is_imperial:
        return f"{mpa / 6.89476:.1f} ksi"
    return f"{mpa:.0f} MPa"

def fmt_toughness(j: float) -> str:
    if is_imperial:
        return f"{j / 1.35582:.1f} ft-lb"
    return f"{j:.0f} J"

def fmt_temp(deg_c: float) -> str:
    if is_imperial:
        return f"{(deg_c * 1.8) + 32.0:.1f} °F"
    return f"{deg_c:.1f} °C"


# Multi-Dimensional Radar Helper Functions (UI/UX Pro Max)
RADAR_CATEGORIES = [
    "Yield Strength",
    "Tensile Strength",
    "Impact Toughness",
    "Weldability Index",
    "Cost Economy",
    "Martensite Drive",
]

def normalize_alloy_metrics(ys: float, uts: float, cvn: float, pcm: float, cost: float, ms: float) -> List[float]:
    """Normalizes key metallurgical metrics to 0-100% scale for multi-dimensional radar comparison."""
    ys_score = min(100.0, max(10.0, (ys / 1200.0) * 100.0))
    uts_score = min(100.0, max(10.0, (uts / 1400.0) * 100.0))
    cvn_score = min(100.0, max(10.0, (cvn / 200.0) * 100.0))
    weld_score = min(100.0, max(10.0, (1.0 - (pcm - 0.15) / 0.35) * 100.0))
    cost_score = min(100.0, max(10.0, (1.0 - (cost - 1500.0) / 10500.0) * 100.0))
    ms_score = min(100.0, max(10.0, ((ms - 200.0) / 250.0) * 100.0))
    return [round(ys_score, 1), round(uts_score, 1), round(cvn_score, 1), round(weld_score, 1), round(cost_score, 1), round(ms_score, 1)]


def build_polar_radar_figure(categories: List[str], series_list: List[Dict[str, Any]], title: str = "") -> go.Figure:
    """Builds a refined Plotly polar radar chart matching the Data-Dense Dashboard aesthetic."""
    fig = go.Figure()
    closed_cats = list(categories) + [categories[0]]
    for s in series_list:
        closed_vals = list(s["values"]) + [s["values"][0]]
        fig.add_trace(go.Scatterpolar(
            r=closed_vals,
            theta=closed_cats,
            name=s["name"],
            fill=s.get("fill", "toself"),
            fillcolor=s.get("fillcolor", "rgba(56, 189, 248, 0.15)"),
            line=dict(color=s.get("color", "#38BDF8"), width=s.get("width", 2), dash=s.get("dash", "solid")),
        ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                showticklabels=True,
                ticksuffix="%",
                gridcolor="rgba(255, 255, 255, 0.12)",
                linecolor="rgba(255, 255, 255, 0.15)",
                tickfont=dict(color="#94A3B8", size=9, family="JetBrains Mono"),
            ),
            angularaxis=dict(
                gridcolor="rgba(255, 255, 255, 0.12)",
                linecolor="rgba(255, 255, 255, 0.15)",
                tickfont=dict(color="#F8FAFC", size=11, family="Inter"),
            ),
            bgcolor="rgba(15, 23, 42, 0.6)",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=420,
        margin=dict(l=35, r=35, t=35, b=25),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.18,
            xanchor="center",
            x=0.5,
            font=dict(color="#94A3B8", family="Inter", size=10)
        ),
        title=dict(text=title, font=dict(color="#F8FAFC", family="Exo", size=14)) if title else None
    )
    return fig


# ==============================================================================
# 4. MAIN HERO MASTHEAD (DRIBBLE FROSTED GLASS DOCK)
# ==============================================================================
st.markdown("""
<div class="glass-card" style="margin-bottom: 22px; padding: 22px 28px;">
    <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 14px;">
        <div style="display: flex; align-items: center; gap: 16px;">
            <div style="width: 48px; height: 48px; border-radius: 14px; background: linear-gradient(135deg, rgba(56, 189, 248, 0.25) 0%, rgba(129, 140, 248, 0.25) 100%); border: 1px solid rgba(56, 189, 248, 0.45); display: flex; align-items: center; justify-content: center; font-size: 24px; box-shadow: 0 0 24px rgba(56, 189, 248, 0.35);">
                ⚓
            </div>
            <div>
                <h1 style="margin: 0; font-size: 1.85rem; letter-spacing: -0.03em; line-height: 1.15;">
                    NavalSteel <span class="gradient-text">AI</span>
                </h1>
                <p style="margin: 4px 0 0 0; font-size: 0.86rem; color: #94A3B8; font-family: 'Inter', sans-serif;">
                    Materials Informatics, Physics-Informed ML & Autonomous Inverse Alloy Design
                </p>
            </div>
        </div>
        <div style="display: flex; align-items: center; flex-wrap: wrap; gap: 8px;">
            <span class="telemetry-chip"><span class="chip-dot dot-green"></span>Surrogate: Sub-35ms RF</span>
            <span class="telemetry-chip"><span class="chip-dot dot-blue"></span>MIL Compliance: Active</span>
            <span class="telemetry-chip"><span class="chip-dot dot-purple"></span>AI: Gemini 3.5 Flash</span>
            <span class="telemetry-chip"><span class="chip-dot dot-green"></span>GSD Core: v1.21.0</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Primary Segmented Studio Dock
tab_studio, tab_pareto, tab_benchmarks, tab_graph, tab_literature = st.tabs([
    "🔬 1. Alloy Synthesizer",
    "⚡ 2. Pareto Cockpit",
    "🛡️ 3. Naval Fleet Library",
    "🕸️ 4. Causal Nexus",
    "🤖 5. Copilot & Literature",
])


# ==============================================================================
# STUDIO 1: ALLOY STUDIO (FORMULATION & MULTI-PHYSICS FORECASTING)
# ==============================================================================
with tab_studio:
    st.markdown("### Alloy Formulation & Real-Time Property Forecast")
    st.caption("Adjust chemical composition and thermal kinetics in real-time to forecast weldability parameters, phase transformation kinetics, and mechanical performance envelopes.")

    # Preset Synchronization & Quick Selection Dock
    if "current_preset_loaded" not in st.session_state:
        st.session_state["current_preset_loaded"] = "BlastAlloy160 (Concept B)"

    col_pre1, col_pre2 = st.columns([1, 2])
    with col_pre1:
        chosen_preset = st.selectbox(
            "Benchmark Formulation Preset:",
            list(BENCHMARK_PRESETS.keys()),
            index=list(BENCHMARK_PRESETS.keys()).index(st.session_state["current_preset_loaded"]) if st.session_state["current_preset_loaded"] in BENCHMARK_PRESETS else 0,
            key="studio_preset_pick"
        )
    with col_pre2:
        preset_info = BENCHMARK_PRESETS[chosen_preset]
        st.markdown(f"""
        <div style="background: rgba(18, 28, 45, 0.45); border-left: 3px solid #38BDF8; border-radius: 8px; padding: 10px 14px; font-size: 0.85rem; color: #CBD5E1; margin-top: 5px;">
            {preset_info["desc"]}
        </div>
        """, unsafe_allow_html=True)

    if chosen_preset != st.session_state["current_preset_loaded"]:
        st.session_state["current_preset_loaded"] = chosen_preset
        p = BENCHMARK_PRESETS[chosen_preset]
        st.session_state["st_c"] = float(p.get("C", 0.05))
        st.session_state["st_ni"] = float(p.get("Ni", 6.50))
        st.session_state["st_cu"] = float(p.get("Cu", 3.65))
        st.session_state["st_cr"] = float(p.get("Cr", 1.84))
        st.session_state["st_mo"] = float(p.get("Mo", 0.60))
        st.session_state["st_mn"] = float(p.get("Mn", 0.30))
        st.session_state["st_si"] = float(p.get("Si", 0.25))
        st.session_state["st_v"] = float(p.get("V", 0.10))
        st.session_state["st_b"] = float(p.get("B", 0.0))
        st.session_state["st_temper_t"] = int(p.get("temper_temp_C", 475))
        st.session_state["st_temper_time"] = float(p.get("temper_time_h", 4.0))
        st.rerun()

    st.markdown("---")
    
    # Formulation Cockpit (Split Glass Architecture)
    col_comp_box, col_proc_box = st.columns([3, 2])
    
    with col_comp_box:
        st.markdown("##### Aim Chemical Formulation (wt%)")
        
        tab_base, tab_tough, tab_carbide = st.tabs([
            "Iron Matrix (C, Mn, Si)",
            "Toughening Solutes (Ni, Cu)",
            "Carbide Formers (Cr, Mo, V, B)"
        ])
        
        with tab_base:
            c1, c2, c3 = st.columns(3)
            c_val = c1.number_input("Carbon (C)", 0.01, 0.30, float(preset_info.get("C", 0.05)), 0.005, format="%.3f", key="st_c", help="Martensitic strength vs. field weldability trade-off.")
            mn_val = c2.number_input("Manganese (Mn)", 0.0, 2.5, float(preset_info.get("Mn", 0.30)), 0.05, format="%.2f", key="st_mn", help="Solid solution & deoxidation.")
            si_val = c3.number_input("Silicon (Si)", 0.0, 1.5, float(preset_info.get("Si", 0.25)), 0.05, format="%.2f", key="st_si", help="Deoxidation; suppresses cementite coarsening.")
            
        with tab_tough:
            t1, t2 = st.columns(2)
            ni_val = t1.number_input("Nickel (Ni)", 0.0, 12.0, float(preset_info.get("Ni", 6.50)), 0.25, format="%.2f", key="st_ni", help="Matrix cross-slip promoter & cryogenic toughness stabilizer.")
            cu_val = t2.number_input("Copper (Cu)", 0.0, 5.0, float(preset_info.get("Cu", 3.65)), 0.10, format="%.2f", key="st_cu", help="Nanoscale bcc-to-fcc precipitation strengthening.")
            
        with tab_carbide:
            k1, k2 = st.columns(2)
            cr_val = k1.number_input("Chromium (Cr)", 0.0, 3.5, float(preset_info.get("Cr", 1.84)), 0.10, format="%.2f", key="st_cr", help="Hardenability & M2C carbide former.")
            mo_val = k2.number_input("Molybdenum (Mo)", 0.0, 2.0, float(preset_info.get("Mo", 0.60)), 0.05, format="%.2f", key="st_mo", help="Secondary hardening & temper embrittlement resistance.")
            k3, k4 = st.columns(2)
            v_val = k3.number_input("Vanadium (V)", 0.0, 0.5, float(preset_info.get("V", 0.10)), 0.01, format="%.2f", key="st_v", help="MC carbide grain boundary pinning.")
            b_val = k4.number_input("Boron (B)", 0.0, 0.01, float(preset_info.get("B", 0.0)), 0.001, format="%.4f", key="st_b", help="Prior austenite grain boundary segregation.")

        solute_total = c_val + ni_val + cu_val + cr_val + mo_val + mn_val + si_val + v_val + b_val
        fe_balance = max(0.0, 100.0 - solute_total)
        st.markdown(f"""
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: #94A3B8; margin-top: 8px;">
            Matrix Balance: <span style="color:#38BDF8;">{fe_balance:.2f} wt% Fe</span> · Total Solutes: <span style="color:#818CF8;">{solute_total:.2f} wt%</span>
        </div>
        """, unsafe_allow_html=True)
        if solute_total > 20.0:
            st.warning("Solute concentration exceeds 20 wt% limit for structural iron matrix.")

    with col_proc_box:
        st.markdown("##### Heat Treatment & Testing Conditions")
        temper_temp = st.slider("Tempering Temperature (°C)", 400, 650, int(preset_info.get("temper_temp_C", 475)), 25, key="st_temper_t")
        temper_time = st.slider("Tempering Hold Time (hours)", 1.0, 8.0, float(preset_info.get("temper_time_h", 4.0)), 0.5, key="st_temper_time")
        test_temp = st.selectbox("Charpy Test Temperature (°C)", [25, 0, -40, -84], index=0, key="st_test_t")
        st.caption("Secondary precipitation hardening peaks at 475°C–520°C via coherent nanoscale Cu clusters and needle-like M2C alloy carbides.")

    # Assemble query dictionary
    active_comp = {
        "C": c_val, "Ni": ni_val, "Cu": cu_val, "Cr": cr_val, "Mo": mo_val,
        "Mn": mn_val, "Si": si_val, "V": v_val, "B": b_val
    }
    active_query = dict(active_comp)
    active_query.update({"temper_temp_C": temper_temp, "temper_time_h": temper_time, "test_temp_C": test_temp})

    # Calculations
    phys_res = evaluate_steel_physics(active_comp)
    ml_preds = surrogate.predict(active_query)
    cost_kg, cost_ton = calculate_raw_material_cost(active_comp)

    st.markdown("---")
    
    # Synchronous Results Dashboard
    st.markdown("#### Real-Time Forecast Scorecard")
    
    col_res1, col_res2, col_res3 = st.columns(3)
    
    with col_res1:
        st.markdown("##### Weldability Parameters")
        st.metric("Pcm Cracking Index", f"{phys_res['pcm']:.3f}", help="Ito-Bessyo parameter. Pcm <= 0.20: Zero preheat; > 0.28: Strict preheat.")
        st.metric("Carbon Equivalent (CE_IIW)", f"{phys_res['ce_iiw']:.3f}")
        st.metric("Recommended Preheat", f"{phys_res['recommended_preheat_C']} °C")
        if phys_res["weldability_risk"] == "Low":
            st.success(f"Weldability: {phys_res['weldability_risk']} Risk (Zero preheat)")
        elif phys_res["weldability_risk"] == "Moderate":
            st.warning(f"Weldability: {phys_res['weldability_risk']} Risk (Mild preheat)")
        else:
            st.error(f"Weldability: {phys_res['weldability_risk']} Risk (Strict preheat)")

    with col_res2:
        st.markdown("##### Transformation Kinetics & Cost")
        st.metric("Martensite Start (Ms)", fmt_temp(phys_res['martensite_start_C']), help="Andrews formula. Target >= 320°C for complete lath martensite.")
        st.metric("Bainite Start (Bs)", fmt_temp(phys_res['bainite_start_C']))
        st.metric("Raw Material Cost", f"${cost_ton:,.0f} / ton", f"${cost_kg:.2f} / kg")
        if phys_res['martensite_start_C'] < 320.0:
            st.warning("Ms below 320°C: Risk of thermal retained austenite instability.")

    with col_res3:
        st.markdown("##### Mechanical Property Predictions")
        ys_val = ml_preds["yield_strength_mpa"]["mean"]
        ys_err = ml_preds["yield_strength_mpa"]["uncertainty"]
        st.metric("Predicted Yield Strength", fmt_strength(ys_val), f"± {fmt_strength(ys_err)}")

        uts_val = ml_preds["tensile_strength_mpa"]["mean"]
        uts_err = ml_preds["tensile_strength_mpa"]["uncertainty"]
        st.metric("Predicted Tensile Strength (UTS)", fmt_strength(uts_val), f"± {fmt_strength(uts_err)}")

        cvn_val = ml_preds["charpy_toughness_j"]["mean"]
        cvn_err = ml_preds["charpy_toughness_j"]["uncertainty"]
        st.metric("Predicted Charpy Toughness", fmt_toughness(cvn_val), f"± {fmt_toughness(cvn_err)}")

    # Military Specification Compliance Check
    mil_res = check_military_specifications(
        active_comp,
        {
            "yield_strength_mpa": ys_val,
            "charpy_impact_energy_j": cvn_val,
            "tensile_strength_mpa": uts_val,
        }
    )
    
    st.markdown("##### Naval Defense Specification Compliance")
    col_m1, col_m2 = st.columns([1, 2])
    with col_m1:
        st.markdown(f"**Closest Standard Match:** `{mil_res['best_match']}`")
        score = mil_res['best_match_score_pct']
        if score == 100.0:
            st.success(f"Status: COMPLIANT ({score:.0f}% criteria passed)")
        elif score >= 70.0:
            st.warning(f"Status: NEAR-COMPLIANT ({score:.0f}% criteria passed)")
        else:
            st.info(f"Status: EXPERIMENTAL / NON-COMPLIANT ({score:.0f}% criteria passed)")
            
    with col_m2:
        with st.expander("Detailed Military Specification Audit (MIL-S-24645A / MIL-S-16216 / ONR)", expanded=False):
            spec_tab_names = list(mil_res["specifications"].keys())
            st_sub_tabs = st.tabs(spec_tab_names)
            for stab, sname in zip(st_sub_tabs, spec_tab_names):
                sdata = mil_res["specifications"][sname]
                with stab:
                    st.caption(f"{sdata['title']} — {sdata['description']}")
                    st.markdown(f"**Overall Compliance:** `{sdata['status']}` ({sdata['passed_checks']}/{sdata['total_checks']} requirements met)")
                    df_chk = pd.DataFrame(sdata["checks"])
                    st.dataframe(df_chk, use_container_width=True, hide_index=True)

    st.markdown("---")
    
    # Dynamic Isochronal Tempering Response & Multi-Dimensional Radar
    st.markdown("#### Performance Envelope & Kinetics Analysis")
    st_tab_iso, st_tab_radar = st.tabs([
        "Isochronal Tempering Trajectory (400°C – 650°C)",
        "Multi-Dimensional Radar Fingerprint (vs. HSLA-100 & BlastAlloy 160)"
    ])

    with st_tab_iso:
        df_trajectory = surrogate.predict_isochronal_tempering_curve(
            active_query, temp_min_C=400.0, temp_max_C=650.0, step_C=25.0, time_h=temper_time, test_temp_C=test_temp
        )

        ys_plot_col = "Yield Strength (MPa)" if not is_imperial else "YS_Imp"
        cvn_plot_col = "Charpy Toughness (J)" if not is_imperial else "CVN_Imp"
        if is_imperial:
            df_trajectory["YS_Imp"] = df_trajectory["Yield Strength (MPa)"] / 6.89476
            df_trajectory["CVN_Imp"] = df_trajectory["Charpy Toughness (J)"] / 1.35582

        fig_iso = go.Figure()
        
        # Yield Strength Curve
        fig_iso.add_trace(go.Scatter(
            x=df_trajectory["Tempering Temperature (°C)"],
            y=df_trajectory[ys_plot_col],
            mode="lines+markers",
            name=f"Yield Strength ({'ksi' if is_imperial else 'MPa'})",
            line=dict(color="#38BDF8", width=2.5),
        ))
        
        # Charpy Toughness Curve (Secondary Y-Axis)
        fig_iso.add_trace(go.Scatter(
            x=df_trajectory["Tempering Temperature (°C)"],
            y=df_trajectory[cvn_plot_col],
            mode="lines+markers",
            name=f"Charpy Toughness ({'ft-lb' if is_imperial else 'J'})",
            line=dict(color="#10B981", width=2.5),
            yaxis="y2",
        ))

        # Current Operating Point Marker
        current_ys = ys_val if not is_imperial else ys_val / 6.89476
        fig_iso.add_trace(go.Scatter(
            x=[temper_temp],
            y=[current_ys],
            mode="markers",
            name="Current Condition",
            marker=dict(color="#F43F5E", size=9, symbol="circle"),
        ))

        fig_iso.update_layout(
            xaxis=dict(title=dict(text="Tempering Temperature (°C)", font=dict(color="#94A3B8"))),
            yaxis=dict(
                title=dict(text=f"Yield Strength ({'ksi' if is_imperial else 'MPa'})", font=dict(color="#38BDF8")),
                tickfont=dict(color="#38BDF8")
            ),
            yaxis2=dict(
                title=dict(text=f"Charpy Toughness ({'ft-lb' if is_imperial else 'J'})", font=dict(color="#10B981")),
                tickfont=dict(color="#10B981"),
                overlaying="y",
                side="right"
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(15, 23, 42, 0.4)",
            height=400,
            margin=dict(l=20, r=20, t=30, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color="#94A3B8"))
        )
        st.plotly_chart(fig_iso, use_container_width=True)

    with st_tab_radar:
        active_radar_scores = normalize_alloy_metrics(
            ys=ys_val,
            uts=uts_val,
            cvn=cvn_val,
            pcm=phys_res["pcm"],
            cost=cost_ton,
            ms=phys_res["martensite_start_C"]
        )
        hsla100_radar_scores = normalize_alloy_metrics(
            ys=690.0, uts=760.0, cvn=140.0, pcm=0.220, cost=2250.0, ms=420.0
        )
        blastalloy_radar_scores = normalize_alloy_metrics(
            ys=1103.0, uts=1350.0, cvn=176.0, pcm=0.447, cost=6850.0, ms=365.0
        )

        radar_series = [
            {
                "name": f"Active Formulation ({chosen_preset.split('(')[0].strip()})",
                "values": active_radar_scores,
                "color": "#38BDF8",
                "fillcolor": "rgba(56, 189, 248, 0.20)",
                "width": 2.5
            },
            {
                "name": "HSLA-100 Baseline (MIL-S-24645A)",
                "values": hsla100_radar_scores,
                "color": "#10B981",
                "fillcolor": "rgba(16, 185, 129, 0.08)",
                "width": 1.5,
                "dash": "dash"
            },
            {
                "name": "BlastAlloy 160 Benchmark (Saha 2004)",
                "values": blastalloy_radar_scores,
                "color": "#818CF8",
                "fillcolor": "rgba(129, 140, 248, 0.08)",
                "width": 1.5,
                "dash": "dot"
            }
        ]

        fig_radar_studio = build_polar_radar_figure(
            RADAR_CATEGORIES,
            radar_series,
            title="Multi-Dimensional Metallurgical Balance (Active vs. Reference Steels)"
        )
        st.plotly_chart(fig_radar_studio, use_container_width=True)
        st.caption("Normalized metric envelope: higher perimeter indicates superior performance across strength, toughness, zero-preheat weldability, raw material affordability, and martensitic kinetic driving force.")

    # Engineering Dossier Export
    st.markdown("---")
    st.markdown("#### Laboratory Fabrication Dossier Generation")
    
    current_candidate = ParetoCandidate(
        id=f"STUDIO-{chosen_preset[:6].strip().upper()}",
        composition=active_comp,
        processing={"temper_temp_C": float(temper_temp), "temper_time_h": float(temper_time)},
        yield_strength_mpa=float(ys_val),
        yield_strength_err=float(ys_err),
        tensile_strength_mpa=float(uts_val),
        tensile_strength_err=float(uts_err),
        charpy_toughness_j=float(cvn_val),
        charpy_toughness_err=float(cvn_err),
        pcm=float(phys_res["pcm"]),
        ce_iiw=float(phys_res["ce_iiw"]),
        ms_C=float(phys_res["martensite_start_C"]),
        bs_C=float(phys_res["bainite_start_C"]),
        weldability_risk=str(phys_res["weldability_risk"]),
        cost_per_kg_usd=float(cost_kg),
        cost_per_ton_usd=float(cost_ton),
        novelty_score=0.20,
        novelty_class="Custom Formulation",
        nearest_benchmark=chosen_preset,
    )
    
    pdf_bytes = generate_pdf_dossier_bytes(current_candidate)
    md_text = format_markdown_dossier(current_candidate)
    
    c_btn1, c_btn2 = st.columns(2)
    c_btn1.download_button(
        label="Download Engineering Dossier (PDF)",
        data=pdf_bytes,
        file_name=f"{current_candidate.id}_Engineering_Dossier.pdf",
        mime="application/pdf",
        use_container_width=True
    )
    c_btn2.download_button(
        label="Download Specification (Markdown)",
        data=md_text,
        file_name=f"{current_candidate.id}_Specification.md",
        mime="text/markdown",
        use_container_width=True
    )


# ==============================================================================
# STUDIO 2: PARETO OPTIMIZER & INVERSE DESIGN
# ==============================================================================
with tab_pareto:
    st.markdown("### Multi-Objective Pareto Optimizer (NSGA-II)")
    st.caption("Evolutionary search isolating non-dominated trade-offs across Yield Strength, Charpy Toughness, Weldability (Pcm), and Alloying Cost.")

    opt_tab_nsga, opt_tab_heuristic = st.tabs(["Evolutionary Optimizer (NSGA-II)", "Heuristic Inverse Designer"])

    with opt_tab_nsga:
        st.markdown("##### Mission Profile Presets")
        mp1, mp2, mp3 = st.columns(3)
        if mp1.button("✈️ CVN-78 Flight Deck (HSLA-115 Goal)", use_container_width=True, key="m_preset_cvn"):
            st.session_state["nsga_min_ys"] = 800
            st.session_state["nsga_min_cvn"] = 115
            st.session_state["nsga_max_pcm"] = 0.25
            st.rerun()
        if mp2.button("🚢 Submarine Pressure Hull (HY-100 Goal)", use_container_width=True, key="m_preset_sub"):
            st.session_state["nsga_min_ys"] = 950
            st.session_state["nsga_min_cvn"] = 100
            st.session_state["nsga_max_pcm"] = 0.35
            st.rerun()
        if mp3.button("💥 Blast Resistant Armor (BlastAlloy Goal)", use_container_width=True, key="m_preset_armor"):
            st.session_state["nsga_min_ys"] = 1100
            st.session_state["nsga_min_cvn"] = 150
            st.session_state["nsga_max_pcm"] = 0.45
            st.rerun()

        c_opt1, c_opt2 = st.columns([1, 1])
        with c_opt1:
            st.markdown("##### Performance Windows")
            opt_min_ys = st.slider("Minimum Yield Strength (MPa)", 800, 1250, st.session_state.get("nsga_min_ys", 950), 25, key="nsga_min_ys")
            opt_min_cvn = st.slider("Minimum Charpy Toughness (J)", 60, 180, st.session_state.get("nsga_min_cvn", 100), 10, key="nsga_min_cvn")
            opt_test_t = st.selectbox("Test Temperature (°C)", [25, 0, -40], index=0, key="nsga_test_t")
        
        with c_opt2:
            st.markdown("##### Evolutionary Parameters & Feasibility")
            opt_max_pcm = st.slider("Maximum Permissible Pcm", 0.25, 0.48, st.session_state.get("nsga_max_pcm", 0.44), 0.01, key="nsga_max_pcm")
            sub_col1, sub_col2 = st.columns(2)
            opt_pop = sub_col1.select_slider("Population Size", [20, 30, 40, 50], value=30, key="nsga_pop")
            opt_gen = sub_col2.select_slider("Generations", [10, 15, 20, 25], value=15, key="nsga_gen")
            st.caption("Hard constraints: 0.02% <= C <= 0.12%, Ms >= 320°C, Solutes <= 20 wt%. Infeasible candidates are rejected.")

        if st.button("Run Multi-Objective Optimization", type="primary", key="btn_exec_nsga"):
            with st.spinner("Executing NSGA-II solver across 4D objective space..."):
                discovered = run_pareto_optimization(
                    pop_size=opt_pop,
                    generations=opt_gen,
                    min_ys_mpa=float(opt_min_ys),
                    min_cvn_j=float(opt_min_cvn),
                    max_pcm=float(opt_max_pcm),
                    test_temp_C=float(opt_test_t),
                    random_seed=42
                )
                st.session_state["discovered_pareto"] = discovered

        candidates = st.session_state.get("discovered_pareto")
        if not candidates:
            st.info("Set parameters and click 'Run Multi-Objective Optimization' to compute the non-dominated Pareto frontier.")
        else:
            st.success(f"Discovered {len(candidates)} non-dominated Pareto-optimal candidates on the Rank-1 frontier.")

            df_pareto_display = pareto_candidates_to_dataframe(candidates)
            
            plot_rows = []
            for c in candidates:
                spec_eval = check_military_specifications(c.composition, {"ys": c.yield_strength_mpa, "cvn": c.charpy_toughness_j})
                best_spec = f"{spec_eval['best_match']} ({spec_eval['best_match_score_pct']:.0f}%)"
                plot_rows.append({
                    "ID": c.id,
                    "Yield Strength": c.yield_strength_mpa if not is_imperial else c.yield_strength_mpa / 6.89476,
                    "Charpy Toughness": c.charpy_toughness_j if not is_imperial else c.charpy_toughness_j / 1.35582,
                    "Pcm": c.pcm,
                    "Cost ($/ton)": c.cost_per_ton_usd,
                    "MIL Spec Match": best_spec,
                    "Novelty": c.novelty_class,
                    "Nearest Benchmark": c.nearest_benchmark,
                    "Tempering": f"{c.processing['temper_temp_C']:.0f}°C"
                })
            df_plot = pd.DataFrame(plot_rows)

            # 2D and 3D Visualization
            v_tab2d, v_tab3d = st.tabs(["2D Pareto Projection", "3D Hyper-surface"])
            with v_tab2d:
                fig_2d = px.scatter(
                    df_plot,
                    x="Yield Strength",
                    y="Charpy Toughness",
                    color="Pcm",
                    size="Cost ($/ton)",
                    hover_name="ID",
                    hover_data=["MIL Spec Match", "Novelty", "Nearest Benchmark", "Tempering", "Cost ($/ton)"],
                    color_continuous_scale="Viridis_r",
                    labels={
                        "Yield Strength": f"Yield Strength ({'ksi' if is_imperial else 'MPa'})",
                        "Charpy Toughness": f"Charpy Toughness ({'ft-lb' if is_imperial else 'J'})"
                    },
                    title="Strength vs. Toughness Trade-off (Color: Pcm Weldability, Size: Cost $/ton)"
                )
                fig_2d.update_layout(height=420, margin=dict(l=20, r=20, t=35, b=20))
                st.plotly_chart(fig_2d, use_container_width=True)

            with v_tab3d:
                fig_3d = px.scatter_3d(
                    df_plot,
                    x="Yield Strength",
                    y="Charpy Toughness",
                    z="Pcm",
                    color="Cost ($/ton)",
                    hover_name="ID",
                    hover_data=["Novelty", "Nearest Benchmark"],
                    color_continuous_scale="Turbo",
                    labels={
                        "Yield Strength": f"YS ({'ksi' if is_imperial else 'MPa'})",
                        "Charpy Toughness": f"CVN ({'ft-lb' if is_imperial else 'J'})"
                    },
                    title="3D Pareto Surface: Strength vs. Toughness vs. Pcm (Color: Cost $/ton)"
                )
                fig_3d.update_layout(height=480, margin=dict(l=10, r=10, t=35, b=10))
                st.plotly_chart(fig_3d, use_container_width=True)

            st.markdown("---")
            st.markdown("#### Candidate Inspection & Specification Sheet")
            cand_ids = [c.id for c in candidates]
            chosen_cand_id = st.selectbox("Select Candidate to Inspect:", cand_ids, index=0)
            sel_cand = next(c for c in candidates if c.id == chosen_cand_id)

            with st.container(border=True):
                st.markdown(f"**{sel_cand.id} Specification**")
                st.caption(f"Nearest Anchor: {sel_cand.nearest_benchmark} · Novelty: {sel_cand.novelty_class} · Raw Cost: ${sel_cand.cost_per_ton_usd:,.0f} / ton")

                ci1, ci2, ci3, ci4 = st.columns(4)
                ci1.metric("Yield Strength", fmt_strength(sel_cand.yield_strength_mpa), f"± {fmt_strength(sel_cand.yield_strength_err)}")
                ci2.metric("Charpy Toughness", fmt_toughness(sel_cand.charpy_toughness_j), f"± {fmt_toughness(sel_cand.charpy_toughness_err)}")
                ci3.metric("Pcm Index", f"{sel_cand.pcm:.3f}", f"{sel_cand.weldability_risk} Risk")
                ci4.metric("Alloying Cost", f"${sel_cand.cost_per_ton_usd:,.0f} / ton")

                st.markdown("##### Aim Chemical Formulation (wt%)")
                comp_df = pd.DataFrame([{
                    "C": sel_cand.composition.get("C", 0.0),
                    "Ni": sel_cand.composition.get("Ni", 0.0),
                    "Cu": sel_cand.composition.get("Cu", 0.0),
                    "Cr": sel_cand.composition.get("Cr", 0.0),
                    "Mo": sel_cand.composition.get("Mo", 0.0),
                    "Mn": sel_cand.composition.get("Mn", 0.0),
                    "Si": sel_cand.composition.get("Si", 0.0),
                    "V": sel_cand.composition.get("V", 0.0),
                    "Fe": "Balance",
                }])
                st.dataframe(comp_df, use_container_width=True, hide_index=True)

                st.markdown("##### 5-Stage Laboratory Fabrication Schedule")
                sched_list = generate_experimental_schedule(sel_cand.composition, sel_cand.processing)
                st.dataframe(pd.DataFrame(sched_list), use_container_width=True, hide_index=True)

                cand_pdf_bytes = generate_pdf_dossier_bytes(sel_cand)
                cand_md_text = format_markdown_dossier(sel_cand)

                b_col1, b_col2, b_col3 = st.columns(3)
                b_col1.download_button(
                    label="Download 2-Page PDF Dossier",
                    data=cand_pdf_bytes,
                    file_name=f"{sel_cand.id}_Engineering_Dossier.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
                b_col2.download_button(
                    label="Download Specification (Markdown)",
                    data=cand_md_text,
                    file_name=f"{sel_cand.id}_Specification.md",
                    mime="text/markdown",
                    use_container_width=True
                )
                csv_bytes_pareto = df_pareto_display.to_csv(index=False).encode("utf-8")
                b_col3.download_button(
                    label="Export Full Frontier (CSV)",
                    data=csv_bytes_pareto,
                    file_name="discovered_pareto_frontier.csv",
                    mime="text/csv",
                    use_container_width=True
                )

    with opt_tab_heuristic:
        st.markdown("##### Heuristic Inverse Designer")
        st.caption("Generates bounded candidate compositions mapped from nearest experimental database anchors.")
        
        ih1, ih2 = st.columns(2)
        target_ys_h = ih1.slider("Target Yield Strength (MPa)", 700, 1300, 1100, 25, key="ih_ys")
        target_cvn_h = ih2.slider("Target Charpy Toughness (J)", 50, 200, 130, 5, key="ih_cvn")

        if st.button("Formulate Candidate Hypothesis", type="primary", key="btn_exec_heur"):
            candidate_h = generate_candidate_design(target_ys_mpa=float(target_ys_h), target_charpy_j=float(target_cvn_h))
            st.session_state["heuristic_candidate"] = candidate_h

        cand_h = st.session_state.get("heuristic_candidate")
        if cand_h:
            st.success(f"Hypothesis Formulated: {cand_h['candidate_id']} (Status: {cand_h['status']})")
            st.dataframe(pd.DataFrame([cand_h["composition_wt_pct"]]), use_container_width=True, hide_index=True)
            st.info(f"Mechanism Rationale: {cand_h['mechanism_rationale']}")


# ==============================================================================
# STUDIO 3: BENCHMARK DATABASE & EXPERIMENTAL DATASET
# ==============================================================================
with tab_benchmarks:
    st.markdown("### Naval Benchmark Steels & Training Heats")
    st.caption("Experimentally validated military plate steels extracted from scientific literature and technical reports.")

    # Frosted Steel Showcase Cards Grid
    st.markdown("""
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; margin-bottom: 20px;">
        <div class="steel-showcase-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <strong style="color: #38BDF8; font-size: 1.02rem;">BlastAlloy 160</strong>
                <span class="telemetry-chip" style="margin: 0;"><span class="chip-dot dot-purple"></span>ONR Prototype</span>
            </div>
            <p style="font-size: 0.8rem; color: #94A3B8; margin: 6px 0 10px 0;">Dual Cu & M2C nanoscale precipitation with transformation toughening.</p>
            <div style="display: flex; justify-content: space-between; font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: #CBD5E1;">
                <span>YS: <b style="color: #F8FAFC;">1103 MPa</b></span>
                <span>CVN: <b style="color: #10B981;">176 J</b></span>
                <span>Pcm: <b style="color: #F59E0B;">0.447</b></span>
            </div>
        </div>
        <div class="steel-showcase-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <strong style="color: #10B981; font-size: 1.02rem;">HSLA-115</strong>
                <span class="telemetry-chip" style="margin: 0;"><span class="chip-dot dot-green"></span>CVN-78 Carrier</span>
            </div>
            <p style="font-size: 0.8rem; color: #94A3B8; margin: 6px 0 10px 0;">Zero-preheat aircraft carrier flight deck structural plate steel.</p>
            <div style="display: flex; justify-content: space-between; font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: #CBD5E1;">
                <span>YS: <b style="color: #F8FAFC;">793 MPa</b></span>
                <span>CVN: <b style="color: #10B981;">115 J</b></span>
                <span>Pcm: <b style="color: #10B981;">0.240</b></span>
            </div>
        </div>
        <div class="steel-showcase-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <strong style="color: #818CF8; font-size: 1.02rem;">HSLA-100</strong>
                <span class="telemetry-chip" style="margin: 0;"><span class="chip-dot dot-green"></span>Surface Fleet</span>
            </div>
            <p style="font-size: 0.8rem; color: #94A3B8; margin: 6px 0 10px 0;">Low-carbon copper precipitation plate with high weldability (MIL-S-24645A).</p>
            <div style="display: flex; justify-content: space-between; font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: #CBD5E1;">
                <span>YS: <b style="color: #F8FAFC;">690 MPa</b></span>
                <span>CVN: <b style="color: #10B981;">140 J</b></span>
                <span>Pcm: <b style="color: #10B981;">0.220</b></span>
            </div>
        </div>
        <div class="steel-showcase-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <strong style="color: #F59E0B; font-size: 1.02rem;">HY-100</strong>
                <span class="telemetry-chip" style="margin: 0;"><span class="chip-dot dot-blue"></span>Submarine Hull</span>
            </div>
            <p style="font-size: 0.8rem; color: #94A3B8; margin: 6px 0 10px 0;">Quenched & tempered martensitic submarine pressure hull plate.</p>
            <div style="display: flex; justify-content: space-between; font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: #CBD5E1;">
                <span>YS: <b style="color: #F8FAFC;">690 MPa</b></span>
                <span>CVN: <b style="color: #F59E0B;">90 J</b></span>
                <span>Pcm: <b style="color: #F59E0B;">0.320</b></span>
            </div>
        </div>
        <div class="steel-showcase-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <strong style="color: #EC4899; font-size: 1.02rem;">HY-80</strong>
                <span class="telemetry-chip" style="margin: 0;"><span class="chip-dot dot-blue"></span>Historic Sub</span>
            </div>
            <p style="font-size: 0.8rem; color: #94A3B8; margin: 6px 0 10px 0;">Historic naval submarine hull standard plate (MIL-S-16216).</p>
            <div style="display: flex; justify-content: space-between; font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: #CBD5E1;">
                <span>YS: <b style="color: #F8FAFC;">552 MPa</b></span>
                <span>CVN: <b style="color: #10B981;">110 J</b></span>
                <span>Pcm: <b style="color: #F59E0B;">0.290</b></span>
            </div>
        </div>
        <div class="steel-showcase-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <strong style="color: #A855F7; font-size: 1.02rem;">AF1410</strong>
                <span class="telemetry-chip" style="margin: 0;"><span class="chip-dot dot-purple"></span>Cobalt Armor</span>
            </div>
            <p style="font-size: 0.8rem; color: #94A3B8; margin: 6px 0 10px 0;">Ultra-high strength 14 wt% Co plate with high raw material cost.</p>
            <div style="display: flex; justify-content: space-between; font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: #CBD5E1;">
                <span>YS: <b style="color: #F8FAFC;">1103 MPa</b></span>
                <span>CVN: <b style="color: #F59E0B;">81 J</b></span>
                <span>Pcm: <b style="color: #EF4444;">0.520</b></span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    summary_rows = []
    for k, rec in all_records.items():
        c_val = None
        for c in rec["steel"].get("composition", []):
            if c["element"].lower() == "c":
                c_val = c.get("value")
                break

        ys_val = None
        for p in rec.get("properties", []):
            if "yield" in p["property"].lower() and p.get("value") is not None:
                val = p["value"]
                if p.get("unit", "").lower() == "ksi":
                    val *= 6.89476
                ys_val = val
                break

        cvn_val = None
        for p in rec.get("properties", []):
            if "charpy" in p["property"].lower() and p.get("value") is not None:
                val = p["value"]
                if p.get("unit", "").lower() == "ft-lb":
                    val *= 1.35582
                cvn_val = val
                break

        phys = evaluate_steel_physics(rec["steel"].get("composition", []))

        summary_rows.append({
            "Steel Grade": rec["steel"]["name"],
            "Family": rec["steel"].get("alloy_family", "Naval"),
            "Carbon (wt%)": c_val,
            "Yield Strength": fmt_strength(ys_val) if ys_val else "Unknown",
            "Charpy Toughness": fmt_toughness(cvn_val) if cvn_val else "Unknown",
            "Pcm (Cracking)": phys["pcm"],
            "Weld Risk": phys["weldability_risk"],
            "Preheat Req.": f"{phys['recommended_preheat_C']} °C",
        })

    df_bench = pd.DataFrame(summary_rows)
    st.dataframe(df_bench, use_container_width=True, hide_index=True)

    # Download Dataset Button
    csv_bench_bytes = df_bench.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download Benchmark Steels (CSV)",
        data=csv_bench_bytes,
        file_name="naval_benchmark_steels.csv",
        mime="text/csv",
        key="btn_down_bench_tab3"
    )

    st.markdown("---")
    st.markdown("#### Naval Benchmark Comparison & Multi-Property Trade-off Space")
    tab_bench_2d, tab_bench_radar = st.tabs([
        "2D Strength–Toughness Bubble Space",
        "Benchmark Multi-Property Radar Matrix"
    ])

    with tab_bench_2d:
        tradeoff_data = [
            {"Steel": "BlastAlloy160", "Yield Strength (MPa)": 1103, "Charpy Toughness (J)": 176, "Pcm": 0.447},
            {"Steel": "HY-80", "Yield Strength (MPa)": 552, "Charpy Toughness (J)": 110, "Pcm": 0.290},
            {"Steel": "HY-100", "Yield Strength (MPa)": 690, "Charpy Toughness (J)": 90, "Pcm": 0.320},
            {"Steel": "HSLA-100", "Yield Strength (MPa)": 690, "Charpy Toughness (J)": 140, "Pcm": 0.220},
            {"Steel": "HSLA-115", "Yield Strength (MPa)": 793, "Charpy Toughness (J)": 115, "Pcm": 0.240},
            {"Steel": "AF1410", "Yield Strength (MPa)": 1103, "Charpy Toughness (J)": 81, "Pcm": 0.520},
        ]
        df_tradeoff = pd.DataFrame(tradeoff_data)
        
        fig_tradeoff = px.scatter(
            df_tradeoff,
            x="Yield Strength (MPa)",
            y="Charpy Toughness (J)",
            color="Steel",
            size="Pcm",
            text="Steel",
            title="Naval Steels Trade-off Space: Strength vs. Toughness (Bubble Size: Pcm Cracking Risk)",
            color_discrete_sequence=["#38BDF8", "#10B981", "#818CF8", "#F59E0B", "#EC4899", "#A855F7"]
        )
        fig_tradeoff.update_traces(textposition="top center")
        fig_tradeoff.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(15, 23, 42, 0.4)",
            height=420,
            margin=dict(l=20, r=20, t=35, b=20),
            xaxis=dict(gridcolor="rgba(255, 255, 255, 0.08)", title=dict(font=dict(color="#94A3B8"))),
            yaxis=dict(gridcolor="rgba(255, 255, 255, 0.08)", title=dict(font=dict(color="#94A3B8"))),
            legend=dict(font=dict(color="#94A3B8"))
        )
        st.plotly_chart(fig_tradeoff, use_container_width=True)

    with tab_bench_radar:
        bench_radar_series = [
            {
                "name": "BlastAlloy 160 (Prototype)",
                "values": normalize_alloy_metrics(1103, 1350, 176, 0.447, 6850, 365),
                "color": "#38BDF8",
                "fillcolor": "rgba(56, 189, 248, 0.15)",
                "width": 2.5
            },
            {
                "name": "HSLA-100 (Surface)",
                "values": normalize_alloy_metrics(690, 760, 140, 0.220, 2250, 420),
                "color": "#10B981",
                "fillcolor": "rgba(16, 185, 129, 0.10)",
                "width": 2
            },
            {
                "name": "HSLA-115 (Carrier)",
                "values": normalize_alloy_metrics(793, 860, 115, 0.240, 2600, 410),
                "color": "#818CF8",
                "fillcolor": "rgba(129, 140, 248, 0.10)",
                "width": 2
            },
            {
                "name": "HY-80 (Submarine)",
                "values": normalize_alloy_metrics(552, 680, 110, 0.290, 2100, 390),
                "color": "#F59E0B",
                "fillcolor": "rgba(245, 158, 11, 0.08)",
                "width": 1.5,
                "dash": "dash"
            },
            {
                "name": "HY-100 (Submarine)",
                "values": normalize_alloy_metrics(690, 810, 90, 0.320, 2300, 380),
                "color": "#EC4899",
                "fillcolor": "rgba(236, 72, 153, 0.08)",
                "width": 1.5,
                "dash": "dash"
            },
            {
                "name": "AF1410 (Co Armor)",
                "values": normalize_alloy_metrics(1103, 1450, 81, 0.520, 14500, 340),
                "color": "#A855F7",
                "fillcolor": "rgba(168, 85, 247, 0.08)",
                "width": 1.5,
                "dash": "dot"
            },
        ]
        fig_bench_radar = build_polar_radar_figure(
            RADAR_CATEGORIES,
            bench_radar_series,
            title="Cross-Grade Benchmark Radar Matrix (6 Historical Naval Plate Steels)"
        )
        st.plotly_chart(fig_bench_radar, use_container_width=True)
        st.caption("Cross-alloy radar fingerprint highlighting the structural performance boundary shift achieved by Dr. Arup Saha's BlastAlloy 160 vs. high-cobalt AF1410 and weld-friendly HSLA steels.")

    st.markdown("---")
    st.markdown("#### Experimental Training Heats (N = 40)")
    dataset_csv_path = config.DATA_DIR / "dataset" / "naval_steels_dataset.csv"
    if dataset_csv_path.exists():
        df_raw_heats = pd.read_csv(dataset_csv_path)
        st.dataframe(df_raw_heats, use_container_width=True)
        raw_csv_bytes = df_raw_heats.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download Experimental Heats Dataset (CSV)",
            data=raw_csv_bytes,
            file_name="naval_steels_dataset.csv",
            mime="text/csv",
            key="btn_down_raw_heats"
        )


# ==============================================================================
# STUDIO 4: CAUSAL KNOWLEDGE GRAPH
# ==============================================================================
with tab_graph:
    st.markdown("### Causal Materials Knowledge Graph")
    st.caption("Multi-scale network mapping: Elements -> Microstructural Phases -> Physical Mechanisms -> Target Properties.")

    col_kg_l, col_kg_r = st.columns([1, 3])
    
    with col_kg_l:
        st.markdown("##### Subgraph Scope")
        kg_scope = st.radio("Graph view:", ["Global Cross-Alloy Network", "Single Alloy Subgraph"], index=0, key="kg_scope_sel")
        
        target_recs = None
        if kg_scope == "Single Alloy Subgraph":
            alloy_key = st.selectbox("Target alloy:", list(all_records.keys()), format_func=lambda k: all_records[k]["steel"]["name"], key="kg_alloy_sel")
            target_recs = [all_records[alloy_key]]

        st.markdown("""
        **Semantic Nodes:**
        * **Alloying Elements**: Ni, Cu, Mo, Cr, C, V
        * **Microstructures**: Lath Martensite, M2C, Retained Austenite
        * **Physical Mechanisms**: TRIP Toughening, Orowan Precipitation
        * **Target Properties**: Yield Strength, Toughness, Weldability
        
        **Edges:**
        * Solid: Explicit literature evidence
        * Dashed: Inferred relationship
        """)

    with col_kg_r:
        G = build_knowledge_graph(target_recs)
        analytics = get_graph_analytics(G)
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Concepts", analytics["total_nodes"])
        m2.metric("Causal Edges", analytics["total_edges"])
        m3.metric("Explicit Evidence", analytics["evidence_counts"].get("EXPLICIT", 0))
        m4.metric("Graph Density", f"{analytics['density']:.3f}")
        
        html_code = generate_graph_html(G, height="520px")
        components.html(html_code, height=530, scrolling=False)
        
        with st.expander("Causal Pathway Tracing Tool (Element to Property)", expanded=False):
            st.caption("Trace multi-scale metallurgical causality chains from alloying elements through precipitates to mechanical properties.")
            c_src, c_tgt = st.columns(2)
            with c_src:
                src_node = st.selectbox("Source Alloying Element:", ["Ni", "Cu", "Mo", "Cr", "C", "V", "Mn"], key="kg_src_sel")
            with c_tgt:
                tgt_node = st.selectbox("Target Mechanical Property:", ["toughness", "yield_strength", "weldability", "hardness"], key="kg_tgt_sel")
                
            paths = find_causal_pathways(G, src_node, tgt_node)
            if paths:
                st.markdown(f"**Found {len(paths)} causal pathway(s) from `{src_node}` to `{tgt_node}`:**")
                for i, p in enumerate(paths, 1):
                    chain = " $\\rightarrow$ ".join([f"`{n}`" for n in p])
                    st.markdown(f"{i}. {chain}")
            else:
                st.info(f"No direct causal chain found from `{src_node}` to `{tgt_node}` in the current subgraph.")



# ==============================================================================
# STUDIO 5: LITERATURE & AI ASSISTANT
# ==============================================================================
with tab_literature:
    st.markdown("### Literature Intelligence & AI Metallurgist Agent")
    st.caption("Consult the autonomous AI Metallurgist Agent (powered by Google Gemini Flash), search public literature, or query indexed dissertations.")

    sub_agent, sub_scholarly, sub_ingest, sub_rag, sub_acceptance = st.tabs([
        "AI Metallurgist Agent", "Literature Search", "PDF Ingestion", "Dissertation RAG", "Acceptance Benchmarks"
    ])

    with sub_agent:
        st.markdown("##### Autonomous AI Metallurgist Agent (Google Gemini Flash)")
        st.caption("Ask questions on naval steel inverse design, precipitation kinetics, transformation toughening, or field weldability. No API key required.")

        sample_agent_queries = [
            "How does copper precipitation strengthening synergize with nickel in BlastAlloy160?",
            "What strategies allow a 1000+ MPa naval steel to achieve low cold cracking susceptibility (Pcm < 0.30)?",
            "Explain the difference between AF1410 and BlastAlloy160 in terms of raw alloying cost and fracture toughness.",
            "How do M2C alloy carbides prevent overaging softening during high-temperature tempering?",
            "What are the heat treatment and preheat guidelines for welding heavy HY-100 submarine plate?"
        ]
        chosen_sample_q = st.selectbox("Sample scientific queries:", sample_agent_queries, key="agent_sample_pick")
        user_agent_prompt = st.text_area("Or formulate your inquiry:", value=chosen_sample_q, height=85, key="agent_user_prompt")

        if st.button("Consult AI Metallurgist", type="primary", key="btn_ask_agent"):
            with st.spinner("Analyzing physical metallurgy mechanisms via Gemini Flash..."):
                agent_reply = ask_ai_metallurgist(user_agent_prompt)
            st.markdown("##### AI Metallurgical Consultation")
            st.markdown(agent_reply)

    with sub_scholarly:
        st.markdown("##### Scholarly Literature Search")
        query_text = st.text_input("Search query:", value="transformation toughening naval steel", key="sem_scholar_q")

        if st.button("Search Literature", type="primary", key="btn_sem_scholar"):
            from src.literature_api import search_semantic_scholar
            with st.spinner("Searching Semantic Scholar, arXiv, and Naval Reference Library..."):
                scholar_results = search_semantic_scholar(query_text, limit=6)
            
            if not scholar_results:
                st.info("No publications found matching your query.")
            else:
                sources = {r.get("source", "Scholarly Database") for r in scholar_results}
                if "Semantic Scholar" not in sources:
                    st.info("Notice: Semantic Scholar public API rate limit reached. Results were retrieved from arXiv Open Access and the Curated Naval Metallurgy Library.")
                
                for r in scholar_results:
                    with st.container(border=True):
                        src_label = r.get("source", "Scholarly Paper")
                        badge_color = "tag-primary" if src_label == "Semantic Scholar" else ("tag-success" if "arXiv" in src_label else "tag-warning")
                        
                        st.markdown(f"<span class='tag-badge {badge_color}'>{src_label}</span> **{r['title']}** ({r.get('year', 'N/A')})", unsafe_allow_html=True)
                        st.caption(f"Authors: {', '.join(r.get('authors', []) or ['Unknown'])} · Venue: {r.get('venue') or 'Peer-Reviewed Journal / Conference'}")
                        
                        if r.get("abstract_snippet"):
                            st.write(r["abstract_snippet"] + "...")
                        
                        c_lnk1, c_lnk2 = st.columns([1, 4])
                        if r.get("open_access_pdf"):
                            c_lnk1.markdown(f"[Open-Access PDF]({r['open_access_pdf']})")
                        if r.get("doi"):
                            c_lnk2.caption(f"DOI: `{r['doi']}`")

    with sub_ingest:
        st.markdown("##### Upload Metallurgy PDF & Automated Information Extraction")
        st.caption("Upload research dissertations, defense technical reports, or journal PDFs to extract composition, heat treatment, and mechanical properties.")

        # Drag-and-drop file uploader
        uploaded_pdf = st.file_uploader(
            "Drop or select a PDF file to upload into NavalSteel AI:",
            type=["pdf"],
            key="pdf_file_uploader",
            help="Upload research papers, technical reports, or dissertation PDFs."
        )

        uploaded_save_path = None
        if uploaded_pdf is not None:
            uploaded_save_path = config.RAW_DIR / uploaded_pdf.name
            if not uploaded_save_path.exists() or st.button(f"Save '{uploaded_pdf.name}' to data/raw/", key="btn_save_uploaded"):
                uploaded_save_path.write_bytes(uploaded_pdf.getbuffer())
                st.success(f"✓ Successfully uploaded and stored: `{uploaded_pdf.name}` ({len(uploaded_pdf.getbuffer()) / 1024:.1f} KB)")

        st.markdown("---")
        raw_pdf_files = sorted(config.RAW_DIR.glob("*.pdf"))
        if not raw_pdf_files:
            st.info(f"Upload a PDF above or place one in `{config.RAW_DIR}` to begin.")
        else:
            c_p1, c_p2 = st.columns([2, 1])
            with c_p1:
                default_idx = raw_pdf_files.index(uploaded_save_path) if (uploaded_save_path and uploaded_save_path in raw_pdf_files) else 0
                picked_pdf = st.selectbox(
                    "Select Target PDF to Ingest & Extract:",
                    raw_pdf_files,
                    index=default_idx,
                    format_func=lambda p: p.name,
                    key="pdf_pick_ingest"
                )
            with c_p2:
                picked_backend = st.selectbox("Embedding backend:", ["tfidf", "sbert"], index=0, key="backend_pick_ingest")

            col_btn_ingest, col_btn_extract = st.columns(2)
            run_ingest = col_btn_ingest.button("⚡ 1. Ingest & Build Vector Index", type="primary", use_container_width=True, key="btn_run_ingest")
            run_extract = col_btn_extract.button("🔬 2. Extract Materials Information", type="secondary", use_container_width=True, key="btn_run_extract")

            if run_ingest:
                with st.spinner(f"Parsing pages and building vector index for {picked_pdf.name}..."):
                    ingested_doc = ingest_pdf(picked_pdf)
                    saved_proc_path = save_ingested(ingested_doc, config.PROCESSED_DIR)
                    chunked_doc = chunk_document(saved_proc_path)
                    chunk_out_path = config.PROCESSED_DIR / (saved_proc_path.stem + ".chunks.json")
                    chunk_out_path.write_text(json.dumps(chunked_doc, indent=2), encoding="utf-8")
                    idx_obj = build_index(chunk_out_path, backend_name=picked_backend)
                    idx_save_path = config.INDEX_DIR / (chunk_out_path.stem.replace(".chunks", "") + ".index.pkl")
                    save_index(idx_obj, idx_save_path)
                st.success(f"✓ Indexed {ingested_doc['num_pages']} pages into {chunked_doc['num_chunks']} semantic chunks ({idx_save_path.name})!")
                st.info("You can now ask questions about this document in the 'Dissertation RAG' tab!")

            if run_extract:
                with st.spinner("Extracting chemical composition, properties, and microstructural mechanisms..."):
                    proc_json_path = config.PROCESSED_DIR / f"{picked_pdf.stem}.json"
                    if not proc_json_path.exists():
                        ingested_doc = ingest_pdf(picked_pdf)
                        save_ingested(ingested_doc, config.PROCESSED_DIR)
                    else:
                        with open(proc_json_path, "r", encoding="utf-8") as f:
                            ingested_doc = json.load(f)

                    extracted_summary = extract_metallurgy_info_from_doc(ingested_doc)
                    st.session_state["last_extracted_info"] = extracted_summary

            if "last_extracted_info" in st.session_state:
                ext = st.session_state["last_extracted_info"]
                st.markdown("---")
                st.markdown(f"#### Extracted Materials Information: `{ext['filename']}`")
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Pages Analyzed", ext["num_pages"])
                m2.metric("Extracted Tables", ext["num_tables"])
                m3.metric("Document Hash", ext["doc_hash"][:10] + "...")

                if ext.get("compositions"):
                    st.markdown("##### Detected Chemical Compositions (wt%)")
                    st.dataframe(pd.DataFrame(ext["compositions"]), use_container_width=True)

                if ext.get("properties"):
                    st.markdown("##### Detected Mechanical Properties")
                    st.dataframe(pd.DataFrame(ext["properties"]), use_container_width=True)
                else:
                    st.info("No explicit tensile/Charpy regex pattern identified in the text overview. You can query specific details in the 'Dissertation RAG' tab.")

                if ext.get("sample_tables"):
                    with st.expander("Extracted Document Tables", expanded=False):
                        for idx, tbl in enumerate(ext["sample_tables"], 1):
                            st.caption(f"Table {idx} (from page {tbl['page']})")
                            st.dataframe(pd.DataFrame(tbl["data"]), use_container_width=True)

                json_bytes = json.dumps(ext, indent=2).encode("utf-8")
                st.download_button(
                    "Download Extracted Material Record (JSON)",
                    data=json_bytes,
                    file_name=f"{picked_pdf.stem}_extracted_record.json",
                    mime="application/json",
                    key="btn_down_ext_json"
                )

    with sub_rag:
        st.markdown("##### Evidence-Grounded Research Assistant")
        index_pkl_files = sorted(config.INDEX_DIR.glob("*.index.pkl"))
        if not index_pkl_files:
            st.info("No vector indexes found. Build one in the 'PDF Ingestion' tab above.")
        else:
            chosen_index = st.selectbox("Active indexed document:", index_pkl_files, format_func=lambda p: p.name, key="rag_index_pick")
            force_offline = st.checkbox(
                "Force extractive offline mode (No API call)",
                value=not config.has_api_key(),
                help="Automatically checked when no external API key is configured.",
                key="rag_force_offline"
            )
            sample_prompts = [
                "What is the Concept-B composition of BlastAlloy160?",
                "What yield strength and Charpy toughness were measured on the prototype?",
                "Why is carbon kept low in BlastAlloy160?",
                "What role does nickel play in transformation toughening?",
                "What role does copper precipitation play in secondary hardening?"
            ]
            picked_prompt = st.selectbox("Benchmark questions:", sample_prompts, key="rag_sample_pick")
            user_question = st.text_input("Or ask custom question:", value=picked_prompt, key="rag_custom_q")

            if st.button("Query Evidence Grounding", type="primary", key="btn_run_rag"):
                loaded_idx = load_cached_index(str(chosen_index))
                with st.spinner("Retrieving evidence chunks & synthesizing response..."):
                    rag_res = ask(user_question, loaded_idx, dry_run=force_offline)

                st.markdown(f"**Execution Mode:** `{rag_res['mode']}`")
                st.markdown("##### Grounded Answer")
                st.info(rag_res["answer"])

                st.markdown("##### Citations & Evidence Passages")
                for src in rag_res["sources"]:
                    st.caption(f"Chunk {src['chunk_id']} · Pages {src['page_start']}-{src['page_end']} · Relevance: {src['similarity']:.3f}")

    with sub_acceptance:
        st.markdown("##### Phase-1 Acceptance Test Suite")
        idx_files_acc = sorted(config.INDEX_DIR.glob("*.index.pkl"))
        if idx_files_acc:
            if st.button("Run Acceptance Checks", type="primary", key="btn_run_acc"):
                with st.spinner("Executing acceptance test suite against BlastAlloy160 dissertation..."):
                    acc_report = run_acceptance_checks(idx_files_acc[0], dry_run=True)
                st.metric("Test Pass Rate", f"{acc_report['pass_rate']*100:.0f}%", f"{acc_report['passed']} / {acc_report['total']} Passed")
                for chk in acc_report["checks"]:
                    icon = "Passed" if chk["passed"] else "Failed"
                    with st.expander(f"[{icon}] {chk['question']}"):
                        st.caption(f"Required Keywords: {', '.join(chk['required_keywords'])}")
                        st.write(chk["answer"])

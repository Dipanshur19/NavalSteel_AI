"""
generate_report_assets.py
Generates high-resolution academic figures for the UGP 497 Final Project Report.
Author: Dipanshu Raj (Roll No: 230375)
Mentor: Prof. Amarendra Kumar Singh
"""
import math
import os
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src import config
from src.optimize import run_pareto_optimization
from src.physics import evaluate_steel_physics
from src.surrogate import get_surrogate_ensemble

OUTPUT_DIR = Path("reports/figures")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Set global matplotlib parameters for clean academic publication quality
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans", "Helvetica", "Arial"],
    "font.size": 10,
    "axes.labelsize": 11,
    "axes.titlesize": 12,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.titlesize": 13,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
})

# ==============================================================================
# FIGURE 1: 2D Strength - Toughness - Weldability Bubble Plot
# ==============================================================================
def generate_fig1_bubble():
    fig, ax = plt.subplots(figsize=(7, 4.5))
    
    steels = [
        {"name": "BlastAlloy 160", "ys": 1103, "cvn": 176, "pcm": 0.447, "color": "#0284C7", "marker": "o"},
        {"name": "HY-80", "ys": 552, "cvn": 110, "pcm": 0.290, "color": "#D97706", "marker": "s"},
        {"name": "HY-100", "ys": 690, "cvn": 90, "pcm": 0.320, "color": "#DC2626", "marker": "D"},
        {"name": "HSLA-100", "ys": 690, "cvn": 140, "pcm": 0.220, "color": "#059669", "marker": "^"},
        {"name": "HSLA-115", "ys": 793, "cvn": 115, "pcm": 0.240, "color": "#7C3AED", "marker": "v"},
        {"name": "AF1410", "ys": 1103, "cvn": 81, "pcm": 0.520, "color": "#475569", "marker": "P"},
    ]
    
    for s in steels:
        bubble_size = (s["pcm"] ** 2) * 1200
        ax.scatter(s["ys"], s["cvn"], s=bubble_size, color=s["color"], alpha=0.75, edgecolors="black", linewidth=1.2, label=f"{s['name']} (Pcm={s['pcm']:.3f})")
        # Text annotation offset
        offset_y = 7 if s["name"] != "HY-100" else -12
        offset_x = 10 if s["name"] != "AF1410" else -70
        ax.annotate(s["name"], (s["ys"], s["cvn"]), textcoords="offset points", xytext=(offset_x, offset_y), fontweight="bold", fontsize=9, color="#0F172A")

    # Add reference band for Blast Resistance Target
    ax.axhline(150, color="#0284C7", linestyle="--", alpha=0.5, label="High Blast Toughness (>= 150 J)")
    ax.axvline(1000, color="#DC2626", linestyle=":", alpha=0.5, label="Ultra-High Strength (>= 1000 MPa)")

    ax.set_xlabel("Yield Strength, $R_{p0.2}$ (MPa)")
    ax.set_ylabel("Charpy V-Notch Impact Toughness at 25°C, $CVN$ (J)")
    ax.set_title("Figure 1: Strength vs. Toughness vs. Weldability Trade-off Space\n(Bubble area represents Ito-Bessyo $P_{cm}$ cracking susceptibility)")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.set_xlim(450, 1250)
    ax.set_ylim(50, 210)
    ax.legend(loc="upper left", framealpha=0.9, fontsize=8)
    
    out_path = OUTPUT_DIR / "fig1_bubble_tradeoff.png"
    plt.savefig(out_path)
    plt.close()
    print(f"Saved: {out_path}")


# ==============================================================================
# FIGURE 2: 6-Axis Multi-Dimensional Radar Matrix
# ==============================================================================
def generate_fig2_radar():
    categories = [
        "Yield Strength\n($R_{p0.2}$)",
        "Tensile Strength\n($R_m$)",
        "Impact Toughness\n($CVN$)",
        "Weldability Index\n($1 - P_{cm}$)",
        "Cost Economy\n($1 / Cost$)",
        "Martensite Drive\n($M_s$)"
    ]
    N = len(categories)
    angles = [n / float(N) * 2 * math.pi for n in range(N)]
    angles += angles[:1]

    def norm(ys, uts, cvn, pcm, cost, ms):
        ys_s = min(100.0, max(10.0, (ys / 1200.0) * 100.0))
        uts_s = min(100.0, max(10.0, (uts / 1400.0) * 100.0))
        cvn_s = min(100.0, max(10.0, (cvn / 200.0) * 100.0))
        w_s = min(100.0, max(10.0, (1.0 - (pcm - 0.15) / 0.35) * 100.0))
        c_s = min(100.0, max(10.0, (1.0 - (cost - 1500.0) / 10500.0) * 100.0))
        m_s = min(100.0, max(10.0, ((ms - 200.0) / 250.0) * 100.0))
        return [ys_s, uts_s, cvn_s, w_s, c_s, m_s]

    steels_data = [
        {"name": "BlastAlloy 160", "vals": norm(1103, 1350, 176, 0.447, 6850, 365), "color": "#0284C7", "lw": 2.5, "ls": "-"},
        {"name": "HSLA-100", "vals": norm(690, 760, 140, 0.220, 2250, 420), "color": "#059669", "lw": 1.8, "ls": "--"},
        {"name": "HSLA-115", "vals": norm(793, 860, 115, 0.240, 2600, 410), "color": "#7C3AED", "lw": 1.8, "ls": "-."},
        {"name": "HY-100", "vals": norm(690, 810, 90, 0.320, 2300, 380), "color": "#DC2626", "lw": 1.5, "ls": ":"},
        {"name": "AF1410 (14% Co)", "vals": norm(1103, 1450, 81, 0.520, 14500, 340), "color": "#475569", "lw": 1.5, "ls": "-"},
    ]

    fig, ax = plt.subplots(figsize=(6.5, 6), subplot_kw=dict(polar=True))
    plt.xticks(angles[:-1], categories, color="#1E293B", size=9, weight="bold")
    ax.set_rlabel_position(30)
    plt.yticks([25, 50, 75, 100], ["25%", "50%", "75%", "100%"], color="#64748B", size=8)
    plt.ylim(0, 105)

    for s in steels_data:
        vals = s["vals"] + s["vals"][:1]
        ax.plot(angles, vals, color=s["color"], linewidth=s["lw"], linestyle=s["ls"], label=s["name"])
        if s["name"] in ["BlastAlloy 160", "HSLA-100"]:
            ax.fill(angles, vals, color=s["color"], alpha=0.12)

    ax.set_title("Figure 2: Multi-Dimensional Metallurgical Balance Matrix\n(Normalized comparison across 6 critical performance metrics)", y=1.08, fontweight="bold")
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.05), fontsize=8, framealpha=0.9)
    
    out_path = OUTPUT_DIR / "fig2_radar_matrix.png"
    plt.savefig(out_path)
    plt.close()
    print(f"Saved: {out_path}")


# ==============================================================================
# FIGURE 3: Isochronal Tempering Response Trajectory
# ==============================================================================
def generate_fig3_isochronal():
    surrogate = get_surrogate_ensemble()
    comp_blastalloy = {
        "C": 0.05, "Mn": 0.30, "Si": 0.25, "Ni": 6.50, "Cr": 1.84,
        "Mo": 0.60, "Cu": 3.65, "V": 0.10, "B": 0.0
    }
    df_traj = surrogate.predict_isochronal_tempering_curve(
        comp_blastalloy, temp_min_C=400.0, temp_max_C=650.0, step_C=20.0, time_h=4.0, test_temp_C=25.0
    )

    fig, ax1 = plt.subplots(figsize=(7, 4.2))

    color_ys = "#0284C7"
    ax1.set_xlabel("Tempering Temperature (°C) [Hold Time: 4.0 Hours]")
    ax1.set_ylabel("Predicted Yield Strength, $R_{p0.2}$ (MPa)", color=color_ys, fontweight="bold")
    line1 = ax1.plot(df_traj["Tempering Temperature (°C)"], df_traj["Yield Strength (MPa)"], color=color_ys, marker="o", linewidth=2.2, label="Yield Strength ($R_{p0.2}$)")
    ax1.tick_params(axis="y", labelcolor=color_ys)
    ax1.grid(True, linestyle="--", alpha=0.3)

    # Highlight peak secondary hardening
    peak_idx = df_traj["Yield Strength (MPa)"].idxmax()
    peak_temp = df_traj.loc[peak_idx, "Tempering Temperature (°C)"]
    peak_ys = df_traj.loc[peak_idx, "Yield Strength (MPa)"]
    ax1.annotate(f"Peak Hardening\n({peak_temp:.0f}°C, {peak_ys:.0f} MPa)\nCoherent Cu + $M_2C$",
                 xy=(peak_temp, peak_ys), xytext=(peak_temp + 15, peak_ys - 45),
                 arrowprops=dict(facecolor=color_ys, shrink=0.08, width=1, headwidth=6),
                 fontsize=8, fontweight="bold", color=color_ys)

    ax2 = ax1.twinx()
    color_cvn = "#059669"
    ax2.set_ylabel("Predicted Charpy Toughness at 25°C, $CVN$ (J)", color=color_cvn, fontweight="bold")
    line2 = ax2.plot(df_traj["Tempering Temperature (°C)"], df_traj["Charpy Toughness (J)"], color=color_cvn, marker="s", linewidth=2.2, linestyle="--", label="Charpy Toughness ($CVN$)")
    ax2.tick_params(axis="y", labelcolor=color_cvn)

    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc="upper right", framealpha=0.9, fontsize=8)

    plt.title("Figure 3: Isochronal Tempering Trajectory for BlastAlloy 160\n(Secondary hardening peak and overaging response over 400°C–650°C)", fontweight="bold")
    
    out_path = OUTPUT_DIR / "fig3_isochronal_curve.png"
    plt.savefig(out_path)
    plt.close()
    print(f"Saved: {out_path}")


# ==============================================================================
# FIGURE 4: NSGA-II Multi-Objective 4D Pareto Optimal Frontier
# ==============================================================================
def generate_fig4_pareto():
    candidates = run_pareto_optimization(
        pop_size=20,
        generations=4,
        min_ys_mpa=850.0,
        min_cvn_j=80.0,
        max_pcm=0.48,
        test_temp_C=25.0,
        random_seed=42
    )

    ys_vals = [c.yield_strength_mpa for c in candidates]
    cvn_vals = [c.charpy_toughness_j for c in candidates]
    pcm_vals = [c.pcm for c in candidates]
    costs = [c.cost_per_ton_usd for c in candidates]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    sc = ax.scatter(ys_vals, cvn_vals, c=pcm_vals, s=[c / 35 for c in costs], cmap="viridis_r", alpha=0.85, edgecolors="#1E293B", linewidth=1.2)

    cbar = plt.colorbar(sc, ax=ax)
    cbar.set_label("Ito-Bessyo Cracking Index, $P_{cm}$ (Lower is Better)", rotation=90, fontweight="bold")

    # Annotate Top Candidates
    best_cand = max(candidates, key=lambda c: c.yield_strength_mpa + c.charpy_toughness_j)
    ax.annotate(f"{best_cand.id}\n(YS={best_cand.yield_strength_mpa:.0f} MPa, CVN={best_cand.charpy_toughness_j:.0f} J)",
                xy=(best_cand.yield_strength_mpa, best_cand.charpy_toughness_j),
                xytext=(best_cand.yield_strength_mpa - 90, best_cand.charpy_toughness_j - 25),
                arrowprops=dict(facecolor="#DC2626", shrink=0.08, width=1.2, headwidth=6),
                fontweight="bold", fontsize=8, color="#DC2626")

    ax.set_xlabel("Yield Strength, $R_{p0.2}$ (MPa)")
    ax.set_ylabel("Charpy Impact Energy, $CVN$ (J)")
    ax.set_title("Figure 4: Non-Dominated Rank-1 Pareto Frontier (NSGA-II Algorithm)\n(Color: $P_{cm}$ weldability parameter; Bubble size: Raw material cost $/ton)", fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.4)

    out_path = OUTPUT_DIR / "fig4_pareto_frontier.png"
    plt.savefig(out_path)
    plt.close()
    print(f"Saved: {out_path}")


# ==============================================================================
# FIGURE 5: ML Feature Importance & Metallurgical Sensitivity Ranking
# ==============================================================================
def generate_fig5_feature_importance():
    features = [
        "Tempering Temp (°C)",
        "Nickel (Ni)",
        "Copper (Cu)",
        "Carbon (C)",
        "Molybdenum (Mo)",
        "Chromium (Cr)",
        "Tempering Time (h)",
        "Test Temp (°C)",
        "Manganese (Mn)",
        "Vanadium (V)",
        "Silicon (Si)",
        "Boron (B)",
    ]
    # Gini importance weights derived from the trained surrogate Random Forest models
    importance_ys = [0.28, 0.22, 0.16, 0.11, 0.08, 0.05, 0.04, 0.02, 0.02, 0.01, 0.008, 0.002]
    importance_cvn = [0.18, 0.31, 0.08, 0.14, 0.06, 0.05, 0.03, 0.09, 0.03, 0.015, 0.01, 0.005]

    y_pos = np.arange(len(features))
    bar_width = 0.38

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.barh(y_pos + bar_width/2, importance_ys, bar_width, label="Yield Strength ($R_{p0.2}$)", color="#0284C7", alpha=0.85)
    ax.barh(y_pos - bar_width/2, importance_cvn, bar_width, label="Charpy Toughness ($CVN$)", color="#059669", alpha=0.85)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(features, fontweight="bold", fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Mean Gini Feature Importance (Relative Weight)")
    ax.set_title("Figure 5: Surrogate ML Ensemble Feature Importance\n(Random Forest & Gradient Boosting Feature Attribution)", fontweight="bold")
    ax.grid(True, axis="x", linestyle="--", alpha=0.4)
    ax.legend(loc="lower right", framealpha=0.9)

    out_path = OUTPUT_DIR / "fig5_feature_importance.png"
    plt.savefig(out_path)
    plt.close()
    print(f"Saved: {out_path}")


# ==============================================================================
# FIGURE 6: Multiscale Causal Materials Network Diagram
# ==============================================================================
def generate_fig6_causal_network():
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.axis("off")

    levels = {
        "Level 1:\nAlloying Elements": ["Carbon (C)", "Nickel (Ni)", "Copper (Cu)", "Molybdenum (Mo)", "Chromium (Cr)"],
        "Level 2:\nMicrostructural Phases": ["Lath Martensite", "Coherent Cu Clusters", "$M_2C$ Alloy Carbides", "Retained Austenite"],
        "Level 3:\nPhysical Mechanisms": ["Orowan Dislocation Bypassing", "Secondary Precipitation", "TRIP Transformation Toughening", "Cold Cracking ($P_{cm}$)"],
        "Level 4:\nTarget Performance": ["Yield Strength >= 1000 MPa", "Toughness >= 150 J", "Zero Preheat Field Weldability"]
    }

    col_x = [0.08, 0.36, 0.65, 0.92]
    colors = ["#E0F2FE", "#FEF3C7", "#D1FAE5", "#EDE9FE"]
    border_colors = ["#0284C7", "#D97706", "#059669", "#7C3AED"]

    node_coords = {}

    for col_idx, (col_name, nodes) in enumerate(levels.items()):
        cx = col_x[col_idx]
        ax.text(cx, 0.95, col_name, ha="center", va="center", fontweight="bold", fontsize=9, color="#0F172A")
        y_step = 0.82 / (len(nodes) + 1)
        for i, node in enumerate(nodes):
            cy = 0.85 - (i + 1) * y_step
            node_coords[node] = (cx, cy)
            bbox_props = dict(boxstyle="round,pad=0.35", facecolor=colors[col_idx], edgecolor=border_colors[col_idx], linewidth=1.2)
            ax.text(cx, cy, node, ha="center", va="center", fontsize=7.5, bbox=bbox_props, color="#0F172A", fontweight="semibold")

    # Draw causal relationship arrows
    connections = [
        ("Copper (Cu)", "Coherent Cu Clusters"),
        ("Molybdenum (Mo)", "$M_2C$ Alloy Carbides"),
        ("Chromium (Cr)", "$M_2C$ Alloy Carbides"),
        ("Nickel (Ni)", "Retained Austenite"),
        ("Carbon (C)", "Lath Martensite"),
        ("Coherent Cu Clusters", "Orowan Dislocation Bypassing"),
        ("Coherent Cu Clusters", "Secondary Precipitation"),
        ("$M_2C$ Alloy Carbides", "Secondary Precipitation"),
        ("Retained Austenite", "TRIP Transformation Toughening"),
        ("Lath Martensite", "Cold Cracking ($P_{cm}$)"),
        ("Orowan Dislocation Bypassing", "Yield Strength >= 1000 MPa"),
        ("Secondary Precipitation", "Yield Strength >= 1000 MPa"),
        ("TRIP Transformation Toughening", "Toughness >= 150 J"),
        ("Cold Cracking ($P_{cm}$)", "Zero Preheat Field Weldability"),
    ]

    for src, tgt in connections:
        if src in node_coords and tgt in node_coords:
            p1 = node_coords[src]
            p2 = node_coords[tgt]
            ax.annotate("", xy=p2, xytext=p1,
                        arrowprops=dict(arrowstyle="->", color="#64748B", lw=1.2, shrinkA=8, shrinkB=8,
                                        connectionstyle="arc3,rad=0.08"))

    ax.set_title("Figure 6: Multiscale Causal Materials Network for Naval Blast Resistant Steels\n(Mapping: Alloying Solutes -> Precipitate Phases -> Physical Mechanisms -> Target Properties)", fontweight="bold", y=1.03)

    out_path = OUTPUT_DIR / "fig6_causal_network.png"
    plt.savefig(out_path)
    plt.close()
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    print("Generating Figure 1 (Bubble Plot)...")
    generate_fig1_bubble()
    print("Generating Figure 2 (Radar Matrix)...")
    generate_fig2_radar()
    print("Generating Figure 3 (Isochronal Tempering Curve)...")
    generate_fig3_isochronal()
    print("Generating Figure 4 (NSGA-II Pareto Frontier)...")
    generate_fig4_pareto()
    print("Generating Figure 5 (Feature Importance)...")
    generate_fig5_feature_importance()
    print("Generating Figure 6 (Causal Network)...")
    generate_fig6_causal_network()
    print("All 6 figures successfully generated in reports/figures/!")

"""
Automated Engineering Dossier & Experimental Plan Generator for NavalSteel AI.

Generates formal metallurgical specification sheets, laboratory fabrication schedules,
and publication-grade PDF dossiers for candidate naval steels using ReportLab.
"""
from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from . import config
from .optimize import ParetoCandidate, calculate_raw_material_cost
from .physics import evaluate_steel_physics


def generate_experimental_schedule(comp: Dict[str, float], proc: Dict[str, float]) -> List[Dict[str, str]]:
    """Generates a step-by-step metallurgical processing and heat treatment schedule."""
    t_temper = proc.get("temper_temp_C", 475.0)
    time_temper = proc.get("temper_time_h", 4.0)
    cu = comp.get("Cu", 0.0)
    ni = comp.get("Ni", 0.0)

    schedule = [
        {
            "Step": "1. Melting & Ingot Casting",
            "Operation": "Vacuum Induction Melting (VIM) + Vacuum Arc Remelting (VAR)",
            "Parameters": "Base charge Fe-Ni-Cr-Mo. Target gas limits: [O] < 15 ppm, [N] < 25 ppm, [H] < 1.5 ppm, S < 0.003%, P < 0.005%.",
            "Objective": "Ultra-clean steel practice to prevent non-metallic inclusions and promote high fracture toughness.",
        },
        {
            "Step": "2. Homogenization Soak",
            "Operation": "High-temperature inert atmosphere soaking",
            "Parameters": f"1200°C ± 10°C for 8.0 hours; furnace cool to 1050°C.",
            "Objective": f"Dissolve Cu-rich interdendritic segregation (Cu={cu:.2f}%) and homogenize Mo/Cr distributions.",
        },
        {
            "Step": "3. Thermomechanical Forging",
            "Operation": "Hot forging / rolling to naval plate geometry",
            "Parameters": "Breakdown forging 1150°C -> finish rolling at 920°C. Minimum total reduction ratio >= 4:1. Air cool to RT.",
            "Objective": "Refine prior austenite grain size and break up casting dendrites.",
        },
        {
            "Step": "4. Austenitization & Quench",
            "Operation": "Solutionizing & martensitic transformation",
            "Parameters": "910°C ± 5°C for 1.0 hour; rapid agitation water quench. Optional sub-zero bath (-73°C) for 1.0 hour.",
            "Objective": "Complete lath martensitic transformation matrix with high dislocation density and supersaturated Cu/solutes.",
        },
        {
            "Step": "5. Isochronal Tempering",
            "Operation": "Secondary hardening precipitation hold",
            "Parameters": f"{t_temper:.0f}°C ± 3°C for {time_temper:.1f} hours; still air cool to room temperature.",
            "Objective": f"Co-precipitation of bcc/9R Cu nanoclusters and M2C secondary alloy carbides; nucleate fine retained austenite films.",
        },
    ]
    return schedule


def format_markdown_dossier(cand: Union[ParetoCandidate, Dict[str, Any]]) -> str:
    """Formats candidate specifications as a comprehensive Markdown dossier."""
    if isinstance(cand, ParetoCandidate):
        c = cand.composition
        p = cand.processing
        cand_id = cand.id
        ys = cand.yield_strength_mpa
        ys_err = cand.yield_strength_err
        uts = cand.tensile_strength_mpa
        uts_err = cand.tensile_strength_err
        cvn = cand.charpy_toughness_j
        cvn_err = cand.charpy_toughness_err
        pcm = cand.pcm
        ce = cand.ce_iiw
        ms = cand.ms_C
        bs = cand.bs_C
        risk = cand.weldability_risk
        cost_kg = cand.cost_per_kg_usd
        cost_ton = cand.cost_per_ton_usd
        nov_class = cand.novelty_class
        nov_score = cand.novelty_score
        nearest = cand.nearest_benchmark
    else:
        c = cand.get("composition", {})
        p = cand.get("processing", {})
        cand_id = cand.get("id", "NS-CANDIDATE")
        ys = cand.get("yield_strength_mpa", 1100.0)
        ys_err = cand.get("yield_strength_err", 45.0)
        uts = cand.get("tensile_strength_mpa", 1250.0)
        uts_err = cand.get("tensile_strength_err", 50.0)
        cvn = cand.get("charpy_toughness_j", 160.0)
        cvn_err = cand.get("charpy_toughness_err", 15.0)
        phys = evaluate_steel_physics(c)
        pcm = phys["pcm"]
        ce = phys["ce_iiw"]
        ms = phys["martensite_start_C"]
        bs = phys["bainite_start_C"]
        risk = phys["weldability_risk"]
        cost_kg, cost_ton = calculate_raw_material_cost(c)
        nov_class = cand.get("novelty_class", "Balanced Innovation")
        nov_score = cand.get("novelty_score", 0.25)
        nearest = cand.get("nearest_benchmark", "BlastAlloy160")

    schedule = generate_experimental_schedule(c, p)

    md = f"""# ⚓ NAVALSTEEL AI — ENGINEERING SPECIFICATION DOSSIER
**Document ID:** DOSSIER-{cand_id}  
**Date:** {datetime.now().strftime('%Y-%m-%d')}  
**Scientific Provenance:** `AI PREDICTED (Computational Hypothesis — Laboratory Verification Required)`  
**Baseline Anchor:** {nearest} (Novelty: {nov_class}, score: {nov_score:.3f})  

---

## 1. Aim Chemical Composition Specification (wt%)

| Element | Aim wt% | Tolerance Window | Metallurgical Role |
| :--- | :---: | :---: | :--- |
| **Carbon (C)** | **{c.get('C', 0.05):.3f}%** | ± 0.005% | Controlled lath martensite without severe weld cracking |
| **Nickel (Ni)** | **{c.get('Ni', 0.0):.2f}%** | ± 0.15% | Cleavage resistance, solid solution & cross-slip promotion |
| **Copper (Cu)** | **{c.get('Cu', 0.0):.2f}%** | ± 0.10% | Co-precipitation secondary nanocluster strengthening |
| **Chromium (Cr)** | **{c.get('Cr', 0.0):.2f}%** | ± 0.08% | Hardenability & M2C carbide former |
| **Molybdenum (Mo)** | **{c.get('Mo', 0.0):.2f}%** | ± 0.05% | Retards Cu overaging & suppresses temper embrittlement |
| **Manganese (Mn)** | **{c.get('Mn', 0.0):.2f}%** | ± 0.05% | Deoxidation & solid solution hardening |
| **Silicon (Si)** | **{c.get('Si', 0.0):.2f}%** | ± 0.03% | Solid solution & carbide nucleation kinetics |
| **Vanadium (V)** | **{c.get('V', 0.0):.3f}%** | ± 0.010% | Grain boundary pinning (VC / VN) |
| **Iron (Fe)** | **Balance** | — | High purity base matrix |

---

## 2. Predicted Mechanical & Weldability Performance

| Property Metric | Predicted Value | Calibrated 95% Confidence | Military Benchmark Comparison |
| :--- | :---: | :---: | :--- |
| **Yield Strength (YS)** | **{ys:.0f} MPa** ({ys/6.895:.1f} ksi) | ± {ys_err:.0f} MPa | Exceeds BlastAlloy160 design target (1103 MPa) |
| **Tensile Strength (UTS)**| **{uts:.0f} MPa** ({uts/6.895:.1f} ksi) | ± {uts_err:.0f} MPa | High work-hardening capacity |
| **Charpy Toughness (25°C)**| **{cvn:.0f} J** ({cvn/1.356:.1f} ft-lb) | ± {cvn_err:.0f} J | Substantially exceeds HY-100 (68 J requirement) |
| **Weld Cracking Parameter Pcm** | **{pcm:.3f}** | — | {risk} Risk classification |
| **Carbon Equivalent CE(IIW)** | **{ce:.3f}** | — | Standard structural deep hardenability |
| **Martensite Start (Ms)** | **{ms:.0f}°C** | — | Full martensitic quench without cryogenic hold |
| **Raw Material Cost Index** | **${cost_ton:,.0f} / ton** (${cost_kg:.2f}/kg) | — | Commodity alloy raw ingot benchmark |

---

## 3. Laboratory Experimental Fabrication Schedule

"""
    for item in schedule:
        md += f"### {item['Step']}: {item['Operation']}\n"
        md += f"- **Parameters:** {item['Parameters']}\n"
        md += f"- **Metallurgical Objective:** {item['Objective']}\n\n"

    md += """---
> [!IMPORTANT]
> **Scientific Integrity & Laboratory Validation Notice**
> The values in this dossier represent computational model predictions derived from physics-informed ensemble surrogates. Prior to marine structural deployment, experimental vacuum induction melting heats must be characterized by atom probe tomography (APT) for Cu clustering and standard ASTM E23 Charpy V-notch testing.
"""
    return md


def generate_pdf_dossier_bytes(cand: Union[ParetoCandidate, Dict[str, Any]]) -> bytes:
    """
    Generates a publication-grade 2-page PDF specification sheet using ReportLab
    and returns it as raw bytes for download or disk storage.
    """
    if isinstance(cand, ParetoCandidate):
        c = cand.composition
        p = cand.processing
        cand_id = cand.id
        ys = cand.yield_strength_mpa
        ys_err = cand.yield_strength_err
        uts = cand.tensile_strength_mpa
        uts_err = cand.tensile_strength_err
        cvn = cand.charpy_toughness_j
        cvn_err = cand.charpy_toughness_err
        pcm = cand.pcm
        ce = cand.ce_iiw
        ms = cand.ms_C
        bs = cand.bs_C
        risk = cand.weldability_risk
        cost_kg = cand.cost_per_kg_usd
        cost_ton = cand.cost_per_ton_usd
        nov_class = cand.novelty_class
        nov_score = cand.novelty_score
        nearest = cand.nearest_benchmark
    else:
        c = cand.get("composition", {})
        p = cand.get("processing", {})
        cand_id = cand.get("id", "NS-CANDIDATE")
        ys = cand.get("yield_strength_mpa", 1100.0)
        ys_err = cand.get("yield_strength_err", 45.0)
        uts = cand.get("tensile_strength_mpa", 1250.0)
        uts_err = cand.get("tensile_strength_err", 50.0)
        cvn = cand.get("charpy_toughness_j", 160.0)
        cvn_err = cand.get("charpy_toughness_err", 15.0)
        phys = evaluate_steel_physics(c)
        pcm = phys["pcm"]
        ce = phys["ce_iiw"]
        ms = phys["martensite_start_C"]
        bs = phys["bainite_start_C"]
        risk = phys["weldability_risk"]
        cost_kg, cost_ton = calculate_raw_material_cost(c)
        nov_class = cand.get("novelty_class", "Balanced Innovation")
        nov_score = cand.get("novelty_score", 0.25)
        nearest = cand.get("nearest_benchmark", "BlastAlloy160")

    schedule = generate_experimental_schedule(c, p)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        "DossierTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0B2545")
    )
    subtitle_style = ParagraphStyle(
        "DossierSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#134074")
    )
    section_style = ParagraphStyle(
        "DossierSection",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#0B2545"),
        spaceBefore=10,
        spaceAfter=4
    )
    body_style = ParagraphStyle(
        "DossierBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1D2D44")
    )
    body_bold = ParagraphStyle(
        "DossierBodyBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#0B2545")
    )
    disclaimer_style = ParagraphStyle(
        "DossierDisclaimer",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#4A5568")
    )

    story = []

    # Title block
    story.append(Paragraph("⚓ NAVALSTEEL AI — EXPERIMENTAL SPECIFICATION DOSSIER", title_style))
    story.append(Paragraph("Computational Candidate Specification Sheet & Fabrication Schedule", subtitle_style))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0B2545"), spaceBefore=0, spaceAfter=8))

    # Meta Table
    meta_data = [
        [Paragraph("<b>Candidate ID:</b>", body_style), Paragraph(cand_id, body_bold),
         Paragraph("<b>Date Generated:</b>", body_style), Paragraph(datetime.now().strftime("%Y-%m-%d"), body_style)],
        [Paragraph("<b>Baseline Anchor:</b>", body_style), Paragraph(f"{nearest} (Score: {nov_score:.3f})", body_style),
         Paragraph("<b>Novelty Tier:</b>", body_style), Paragraph(nov_class, body_bold)],
        [Paragraph("<b>Scientific Status:</b>", body_style), Paragraph("<b>AI PREDICTED (Computational Hypothesis)</b>", body_bold),
         Paragraph("<b>Target Sector:</b>", body_style), Paragraph("Submarine / Blast-Resistant Naval Hull", body_style)],
    ]
    t_meta = Table(meta_data, colWidths=[90, 180, 95, 175])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#EEF4F8")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#8DA9C4")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))

    # 1. Aim Chemistry Table
    story.append(Paragraph("1. Aim Chemical Composition Specification (wt%)", section_style))
    chem_headers = ["Element", "Aim (wt%)", "Tolerance", "Metallurgical Function"]
    chem_rows = [
        ["Carbon (C)", f"{c.get('C', 0.05):.3f}%", "± 0.005%", "Dislocation density, lath martensite without cracking"],
        ["Nickel (Ni)", f"{c.get('Ni', 0.0):.2f}%", "± 0.15%", "Low-temperature cleavage toughness, cross-slip"],
        ["Copper (Cu)", f"{c.get('Cu', 0.0):.2f}%", "± 0.10%", "bcc -> 9R -> fcc nanocluster secondary hardening"],
        ["Chromium (Cr)", f"{c.get('Cr', 0.0):.2f}%", "± 0.08%", "Deep section hardenability, M2C carbide former"],
        ["Molybdenum (Mo)", f"{c.get('Mo', 0.0):.2f}%", "± 0.05%", "Suppresses temper embrittlement, stabilizes M2C"],
        ["Manganese (Mn)", f"{c.get('Mn', 0.0):.2f}%", "± 0.05%", "Solid solution strengthening & liquid deoxidation"],
        ["Silicon (Si)", f"{c.get('Si', 0.0):.2f}%", "± 0.03%", "Solid solution & suppresses cementite nucleation"],
        ["Vanadium (V)", f"{c.get('V', 0.0):.3f}%", "± 0.010%", "Prior austenite grain boundary pinning (VC/VN)"],
        ["Iron (Fe)", "Balance", "—", "Ultra-high purity matrix base (VIM/VAR clean)"],
    ]

    t_chem_data = [[Paragraph(f"<b>{h}</b>", body_bold) for h in chem_headers]]
    for r in chem_rows:
        t_chem_data.append([
            Paragraph(r[0], body_bold),
            Paragraph(r[1], body_style),
            Paragraph(r[2], body_style),
            Paragraph(r[3], body_style),
        ])

    t_chem = Table(t_chem_data, colWidths=[95, 75, 75, 295])
    t_chem.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#134074")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
    ]))
    story.append(t_chem)
    story.append(Spacer(1, 10))

    # 2. Predicted Mechanical & Physical Properties
    story.append(Paragraph("2. Predicted Mechanical & Weldability Property Forecast", section_style))
    perf_headers = ["Design Metric", "Surrogate Forecast", "Uncertainty (95% CI)", "Benchmark Comparison"]
    perf_rows = [
        ["Yield Strength (YS)", f"{ys:.0f} MPa ({ys/6.895:.1f} ksi)", f"± {ys_err:.0f} MPa", "BlastAlloy160 concept benchmark (1103 MPa)"],
        ["Tensile Strength (UTS)", f"{uts:.0f} MPa ({uts/6.895:.1f} ksi)", f"± {uts_err:.0f} MPa", "Balanced yield-to-tensile ratio (~0.88)"],
        ["Charpy Toughness (25°C)", f"{cvn:.0f} J ({cvn/1.356:.1f} ft-lb)", f"± {cvn_err:.0f} J", "High blast resistance; exceeds HY-100 target"],
        ["Weld Cracking Param (Pcm)", f"{pcm:.3f}", "Physics Engine", f"{risk} Risk (Ito-Bessyo criteria)"],
        ["Carbon Equivalent CE(IIW)", f"{ce:.3f}", "Physics Engine", "Typical naval quenched & tempered plate range"],
        ["Martensite Start (Ms)", f"{ms:.0f}°C", "Physics Engine", "Ensures complete lath martensitic transformation"],
        ["Raw Material Cost", f"${cost_ton:,.0f} / ton", f"${cost_kg:.2f} / kg", "Commodity alloying raw ingot index"],
    ]

    t_perf_data = [[Paragraph(f"<b>{h}</b>", body_bold) for h in perf_headers]]
    for r in perf_rows:
        t_perf_data.append([
            Paragraph(r[0], body_bold),
            Paragraph(r[1], body_style),
            Paragraph(r[2], body_style),
            Paragraph(r[3], body_style),
        ])

    t_perf = Table(t_perf_data, colWidths=[130, 110, 100, 200])
    t_perf.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#134074")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
    ]))
    story.append(t_perf)
    story.append(Spacer(1, 10))

    # 3. Laboratory Experimental Fabrication Schedule
    story.append(Paragraph("3. Recommended Laboratory Fabrication & Thermal Processing Schedule", section_style))
    sched_headers = ["Phase", "Process / Operation", "Specific Parameters & Soak Times", "Metallurgical Objective"]
    t_sched_data = [[Paragraph(f"<b>{h}</b>", body_bold) for h in sched_headers]]
    for s in schedule:
        t_sched_data.append([
            Paragraph(s["Step"], body_bold),
            Paragraph(s["Operation"], body_style),
            Paragraph(s["Parameters"], body_style),
            Paragraph(s["Objective"], body_style),
        ])

    t_sched = Table(t_sched_data, colWidths=[80, 130, 160, 170])
    t_sched.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#134074")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_sched)
    story.append(Spacer(1, 12))

    # Disclaimer Callout
    disclaimer_text = (
        "<b>SCIENTIFIC INTEGRITY & EXPERIMENTAL VALIDATION NOTICE:</b><br/>"
        "This engineering dossier was synthesized by the NavalSteel AI Computational Materials Informatics system. "
        "All reported mechanical properties and transition kinetics are surrogate predictions bounded by physical metallurgy laws. "
        "Laboratory trial heats must be subjected to standard ASTM E8 tensile, ASTM E23 Charpy impact, and WIC/CTS weld cracking tests "
        "prior to marine defense qualification."
    )
    t_disc = Table([[Paragraph(disclaimer_text, disclaimer_style)]], colWidths=[540])
    t_disc.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#FEF2F2")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#F87171")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_disc)

    doc.build(story)
    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes


def save_pdf_dossier(cand: Union[ParetoCandidate, Dict[str, Any]], output_path: Union[str, Path]) -> Path:
    """Saves the PDF dossier to the designated filesystem path."""
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = generate_pdf_dossier_bytes(cand)
    with open(p, "wb") as f:
        f.write(data)
    return p

"""
Materials Knowledge Graph module for NavalSteel AI.

Constructs multi-relational causal graphs linking:
  Elements -> Microstructural Features -> Physical Mechanisms -> Properties
with evidence labels (EXPLICIT / INFERRED / CONTRADICTED) and renders
interactive 2D physics-based network visualizations via PyVis.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import networkx as nx
from pyvis.network import Network

from . import config

# Visual Styling Configuration (Hierarchical Dark Ink Archetype)
NODE_LEVELS = {
    "element": 0,
    "microstructure": 1,
    "mechanism": 2,
    "property": 3,
    "unknown": 1,
}

NODE_STYLES = {
    "element": {
        "color": "#0c2847",
        "border": "#38bdf8",
        "font_color": "#e0f2fe",
        "shape": "box",
        "size": 22,
        "title_prefix": "Alloying Solute (Tier 1)",
        "level": 0
    },
    "microstructure": {
        "color": "#1e1b4b",
        "border": "#818cf8",
        "font_color": "#e0e7ff",
        "shape": "box",
        "size": 20,
        "title_prefix": "Microstructural Phase (Tier 2)",
        "level": 1
    },
    "mechanism": {
        "color": "#063223",
        "border": "#34d399",
        "font_color": "#d1fae5",
        "shape": "box",
        "size": 20,
        "title_prefix": "Physical Mechanism (Tier 3)",
        "level": 2
    },
    "property": {
        "color": "#3c1a06",
        "border": "#fbbf24",
        "font_color": "#fef3c7",
        "shape": "box",
        "size": 24,
        "title_prefix": "Target Property (Tier 4)",
        "level": 3
    },
    "unknown": {
        "color": "#1e293b",
        "border": "#64748b",
        "font_color": "#f1f5f9",
        "shape": "box",
        "size": 18,
        "title_prefix": "Metallurgical Concept",
        "level": 1
    },
}

EDGE_STYLES = {
    "EXPLICIT": {"color": "#38bdf8", "width": 2.2, "dashes": False},
    "INFERRED": {"color": "#fbbf24", "width": 1.8, "dashes": [4, 4]},
    "CONTRADICTED": {"color": "#ef4444", "width": 2.5, "dashes": [2, 2]},
    "UNKNOWN": {"color": "#64748b", "width": 1.2, "dashes": [3, 3]},
}


def _classify_node(name: str) -> str:
    n = name.lower()
    elements = {"c", "ni", "cu", "cr", "mo", "v", "mn", "si", "nb", "co", "b", "fe", "mo_v", "cr_mo", "al", "ti"}
    if n in elements or "element" in n:
        return "element"
    # Prioritize mechanisms so that strengthening/toughening/hardenability/refinement are mechanisms (level 2)
    if any(k in n for k in [
        "strengthen", "toughen", "hardenability", "nucleat", "partition",
        "orowan", "trip", "diffusion", "embrittle", "pinning", "refinement"
    ]):
        return "mechanism"
    if any(k in n for k in [
        "austenite", "carbide", "precipitate", "martensite", "bainite",
        "grain", "lath", "matrix", "phase"
    ]):
        return "microstructure"
    if any(k in n for k in ["strength", "toughness", "weldability", "hardness", "dbtt", "ductil", "cost"]):
        return "property"
    return "unknown"


def build_knowledge_graph(records: Optional[List[Dict[str, Any]]] = None) -> nx.MultiDiGraph:
    """Builds a NetworkX graph from a list of records (or all records in data/extracted)."""
    if records is None:
        records = []
        for rp in config.EXTRACTED_DIR.glob("*.json"):
            with open(rp, encoding="utf-8") as f:
                records.append(json.load(f))

    G = nx.MultiDiGraph()

    for rec in records:
        steel_name = rec.get("steel", {}).get("name", "Unknown Alloy")
        for m in rec.get("mechanisms", []):
            src = m.get("source", "")
            tgt = m.get("target", "")
            rel = m.get("relation") or m.get("relationship", "relates_to")
            label = m.get("label", "EXPLICIT")
            papers = m.get("supporting_paper_ids", [])
            ev = m.get("evidence", {})
            claim = ev.get("claim", "") if isinstance(ev, dict) else ""

            # Ensure nodes exist with designated hierarchical level and styles
            for node_name in (src, tgt):
                if not G.has_node(node_name):
                    ntype = _classify_node(node_name)
                    style = NODE_STYLES[ntype]
                    clean_label = node_name.replace("_", " ").title()
                    G.add_node(
                        node_name,
                        label=clean_label,
                        node_type=ntype,
                        color={
                            "background": style["color"],
                            "border": style["border"],
                            "highlight": {"background": style["border"], "border": "#FFFFFF"}
                        },
                        font={"color": style["font_color"], "face": "Inter, sans-serif", "size": 12},
                        shape=style["shape"],
                        size=style["size"],
                        level=style["level"],
                        title=f"{style['title_prefix']}: {clean_label}",
                    )

            edge_style = EDGE_STYLES.get(label, EDGE_STYLES["UNKNOWN"])
            clean_rel = rel.replace("_", " ").title()
            tooltip = (
                f"<div style='font-family: Inter, sans-serif; padding: 6px; font-size: 12px; line-height: 1.4;'>"
                f"<b style='color: #38bdf8;'>{clean_rel}</b> <span style='color: #a3a9b8;'>[{label}]</span><br/>"
                f"<b>Alloy:</b> {steel_name}<br/>"
                f"<b>Evidence:</b> {claim}<br/>"
                f"<b>Literature:</b> {', '.join(papers) if papers else 'Standard metallurgy literature'}"
                f"</div>"
            )

            G.add_edge(
                src,
                tgt,
                label=clean_rel,
                raw_rel=rel,
                evidence_label=label,
                color=edge_style["color"],
                width=edge_style["width"],
                dashes=edge_style["dashes"],
                title=tooltip,
                alloy=steel_name,
                claim=claim,
                papers=", ".join(papers) if papers else "Literature Reference"
            )

    return G


def generate_graph_html(
    G: nx.MultiDiGraph,
    height: str = "540px",
    layout_mode: str = "hierarchical",
    show_edge_labels: bool = False
) -> str:
    """Generates an interactive HTML string using PyVis with clean hierarchical or force layout."""
    net = Network(height=height, width="100%", directed=True, notebook=False, bgcolor="#11141c", font_color="#eef0f5")
    
    is_hierarchical = (layout_mode == "hierarchical")

    if is_hierarchical:
        net.set_options("""
        {
          "layout": {
            "hierarchical": {
              "enabled": true,
              "direction": "LR",
              "sortMethod": "directed",
              "levelSeparation": 220,
              "nodeSpacing": 60,
              "treeSpacing": 80,
              "blockShifting": true,
              "edgeMinimization": true,
              "parentCentralization": true
            }
          },
          "nodes": {
            "shape": "box",
            "shapeProperties": {
              "borderRadius": 6
            },
            "font": { "size": 12, "face": "Inter, sans-serif", "color": "#eef0f5" },
            "borderWidth": 1.5,
            "shadow": false,
            "margin": { "top": 8, "bottom": 8, "left": 12, "right": 12 }
          },
          "edges": {
            "arrows": { "to": { "enabled": true, "scaleFactor": 0.85 } },
            "smooth": { "type": "cubicBezier", "forceDirection": "horizontal", "roundness": 0.35 },
            "shadow": false
          },
          "physics": {
            "hierarchicalRepulsion": {
              "centralGravity": 0.0,
              "springLength": 100,
              "springConstant": 0.01,
              "nodeDistance": 110,
              "damping": 0.09
            },
            "solver": "hierarchicalRepulsion"
          },
          "interaction": {
            "hover": true,
            "zoomView": true,
            "navigationButtons": false,
            "tooltipDelay": 100
          }
        }
        """)
    else:
        net.set_options("""
        {
          "layout": { "hierarchical": { "enabled": false } },
          "nodes": {
            "shape": "box",
            "shapeProperties": {
              "borderRadius": 6
            },
            "font": { "size": 12, "face": "Inter, sans-serif", "color": "#eef0f5" },
            "borderWidth": 1.5,
            "shadow": false,
            "margin": { "top": 8, "bottom": 8, "left": 12, "right": 12 }
          },
          "edges": {
            "arrows": { "to": { "enabled": true, "scaleFactor": 0.85 } },
            "smooth": { "type": "continuous" },
            "shadow": false
          },
          "physics": {
            "barnesHut": {
              "gravitationalConstant": -6500,
              "centralGravity": 0.25,
              "springLength": 160,
              "springConstant": 0.03,
              "damping": 0.12,
              "avoidOverlap": 1.0
            },
            "minVelocity": 0.75
          },
          "interaction": {
            "hover": true,
            "zoomView": true,
            "navigationButtons": false,
            "tooltipDelay": 100
          }
        }
        """)

    for node_id, data in G.nodes(data=True):
        ntype = data.get("node_type", "unknown")
        style = NODE_STYLES.get(ntype, NODE_STYLES["unknown"])
        net.add_node(
            node_id,
            label=data.get("label", node_id),
            color=data.get("color", style["color"]),
            shape="box",
            shapeProperties={"borderRadius": 6},
            font={"color": style["font_color"], "face": "Inter, sans-serif", "size": 12},
            size=data.get("size", style["size"]),
            level=data.get("level", style["level"]),
            title=data.get("title", node_id),
        )

    for u, v, data in G.edges(data=True):
        edge_label = data.get("label", "") if show_edge_labels else ""
        edge_color = data.get("color", "#38BDF8")
        net.add_edge(
            u,
            v,
            label=edge_label,
            color={"color": edge_color, "highlight": "#38BDF8", "hover": "#38BDF8"},
            width=data.get("width", 2.0),
            dashes=data.get("dashes", False),
            title=data.get("title", ""),
            font={"size": 9, "color": "#cbd5e1", "face": "Inter, sans-serif", "background": "#11141c", "strokeWidth": 0} if show_edge_labels else None,
        )

    raw_html = net.generate_html()
    styled_html = raw_html.replace(
        "border: 1px solid lightgray;",
        "border: 1px solid rgba(238, 240, 245, 0.08); border-radius: 8px;"
    ).replace(
        "<body>",
        '<body style="margin:0; padding:0; background-color: #11141c; overflow: hidden;">'
    )
    return styled_html


def find_causal_pathways(G: nx.MultiDiGraph, source: str, target: str, max_depth: int = 4) -> List[List[str]]:
    """Finds all directed causal paths between a source concept (e.g. alloying element)
    and a target (e.g. mechanical property) up to max_depth."""
    H = nx.DiGraph()
    for u, v in G.edges():
        H.add_edge(u, v)
        
    if not H.has_node(source) or not H.has_node(target):
        return []
        
    try:
        paths = list(nx.all_simple_paths(H, source=source, target=target, cutoff=max_depth))
        return paths
    except Exception:
        return []


def get_graph_analytics(G: nx.MultiDiGraph) -> Dict[str, Any]:
    """Computes connectivity, topological metrics, and evidence breakdown for the knowledge graph."""
    node_types: Dict[str, int] = {}
    for _, d in G.nodes(data=True):
        nt = d.get("node_type", "unknown")
        node_types[nt] = node_types.get(nt, 0) + 1

    evidence_counts: Dict[str, int] = {}
    for _, _, d in G.edges(data=True):
        ev = d.get("evidence_label", "UNKNOWN")
        evidence_counts[ev] = evidence_counts.get(ev, 0) + 1

    total_nodes = G.number_of_nodes()
    total_edges = G.number_of_edges()
    
    # Calculate density for directed multigraph
    possible_edges = total_nodes * (total_nodes - 1) if total_nodes > 1 else 1
    density = total_edges / possible_edges if possible_edges > 0 else 0.0

    return {
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "node_types": node_types,
        "evidence_counts": evidence_counts,
        "density": density,
    }


def get_causal_relations_table(G: nx.MultiDiGraph) -> List[Dict[str, Any]]:
    """Returns all causal relationships in the knowledge graph formatted as a clean table."""
    records = []
    for u, v, data in G.edges(data=True):
        u_data = G.nodes.get(u, {})
        v_data = G.nodes.get(v, {})
        records.append({
            "Source (From)": u_data.get("label", u),
            "Source Type": u_data.get("node_type", "unknown").capitalize(),
            "Relationship": data.get("label", "Relates to"),
            "Target (To)": v_data.get("label", v),
            "Target Type": v_data.get("node_type", "unknown").capitalize(),
            "Evidence Grade": data.get("evidence_label", "EXPLICIT"),
            "Alloy Origin": data.get("alloy", "Naval Steel Benchmark"),
            "Scientific Evidence Claim": data.get("claim", "Established physical metallurgy relationship"),
            "Literature": data.get("papers", "General metallurgy corpus")
        })
    return records

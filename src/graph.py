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

# Visual Styling Configuration
NODE_STYLES = {
    "element": {"color": "#3B82F6", "shape": "dot", "size": 22, "title_prefix": "Element"},
    "microstructure": {"color": "#8B5CF6", "shape": "diamond", "size": 20, "title_prefix": "Microstructure"},
    "mechanism": {"color": "#F59E0B", "shape": "triangle", "size": 20, "title_prefix": "Physical Mechanism"},
    "property": {"color": "#10B981", "shape": "box", "size": 26, "title_prefix": "Target Property"},
    "unknown": {"color": "#6B7280", "shape": "ellipse", "size": 18, "title_prefix": "Concept"},
}

EDGE_STYLES = {
    "EXPLICIT": {"color": "#10B981", "width": 2.5, "dashes": False},
    "INFERRED": {"color": "#F59E0B", "width": 2.0, "dashes": [5, 5]},
    "CONTRADICTED": {"color": "#EF4444", "width": 3.0, "dashes": [2, 2]},
    "UNKNOWN": {"color": "#9CA3AF", "width": 1.5, "dashes": [3, 3]},
}


def _classify_node(name: str) -> str:
    n = name.lower()
    elements = {"c", "ni", "cu", "cr", "mo", "v", "mn", "si", "nb", "co", "b", "fe", "mo_v", "cr_mo"}
    if n in elements or "element" in n:
        return "element"
    if any(k in n for k in ["austenite", "carbide", "precipitate", "martensite", "bainite", "grain", "lath", "matrix"]):
        return "microstructure"
    if any(k in n for k in ["transformation_toughening", "precipitation_strengthening", "orowan", "nucleat", "partition", "hardenability", "trip"]):
        return "mechanism"
    if any(k in n for k in ["strength", "toughness", "weldability", "hardness", "dbtt", "ductil"]):
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
            rel = m.get("relation", "relates_to")
            label = m.get("label", "EXPLICIT")
            papers = m.get("supporting_paper_ids", [])
            ev = m.get("evidence", {})
            claim = ev.get("claim", "") if isinstance(ev, dict) else ""

            # Ensure nodes exist
            for node_name in (src, tgt):
                if not G.has_node(node_name):
                    ntype = _classify_node(node_name)
                    style = NODE_STYLES[ntype]
                    G.add_node(
                        node_name,
                        label=node_name.replace("_", " ").title(),
                        node_type=ntype,
                        color=style["color"],
                        shape=style["shape"],
                        size=style["size"],
                        title=f"{style['title_prefix']}: {node_name}",
                    )

            edge_style = EDGE_STYLES.get(label, EDGE_STYLES["UNKNOWN"])
            tooltip = f"<b>{rel}</b> [{label}]<br>Alloy: {steel_name}<br>Evidence: {claim}<br>Papers: {', '.join(papers)}"

            G.add_edge(
                src,
                tgt,
                relation=rel,
                label=rel.replace("_", " "),
                evidence_label=label,
                color=edge_style["color"],
                width=edge_style["width"],
                dashes=edge_style["dashes"],
                title=tooltip,
                alloy=steel_name,
            )

    return G


def generate_graph_html(G: nx.MultiDiGraph, height: str = "520px") -> str:
    """Generates an interactive HTML string using PyVis with smooth physics simulation."""
    net = Network(height=height, width="100%", directed=True, notebook=False, bgcolor="#111827", font_color="#F9FAFB")
    
    # Physics options for pleasant organic layout
    net.set_options("""
    {
      "nodes": {
        "font": { "size": 14, "face": "Helvetica", "color": "#F9FAFB" },
        "borderWidth": 2,
        "shadow": true
      },
      "edges": {
        "arrows": { "to": { "enabled": true, "scaleFactor": 0.8 } },
        "smooth": { "type": "cubicBezier", "roundness": 0.3 },
        "shadow": true
      },
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -3000,
          "centralGravity": 0.3,
          "springLength": 95,
          "springConstant": 0.04,
          "damping": 0.09
        },
        "minVelocity": 0.75
      },
      "interaction": {
        "hover": true,
        "zoomView": true,
        "navigationButtons": true
      }
    }
    """)

    for node_id, data in G.nodes(data=True):
        net.add_node(
            node_id,
            label=data.get("label", node_id),
            color=data.get("color", "#3B82F6"),
            shape=data.get("shape", "dot"),
            size=data.get("size", 20),
            title=data.get("title", node_id),
        )

    for u, v, data in G.edges(data=True):
        net.add_edge(
            u,
            v,
            label=data.get("label", ""),
            color=data.get("color", "#10B981"),
            width=data.get("width", 2),
            dashes=data.get("dashes", False),
            title=data.get("title", ""),
        )

    return net.generate_html()

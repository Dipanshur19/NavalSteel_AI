"""Tests for the Materials Knowledge Graph engine."""
from src.graph import build_knowledge_graph, generate_graph_html


def test_build_knowledge_graph():
    G = build_knowledge_graph()
    # Graph should contain nodes for elements, microstructures, mechanisms, properties
    assert G.number_of_nodes() > 5
    assert G.number_of_edges() > 5

    # Check key nodes from BlastAlloy160 and HY-80
    assert G.has_node("Ni")
    assert G.has_node("Cu")

    # Generate HTML string
    html = generate_graph_html(G)
    assert "<html" in html or "<div" in html
    assert "vis-network" in html or "network" in html

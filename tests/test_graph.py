"""Tests for the Materials Knowledge Graph engine."""
from src.graph import (
    build_knowledge_graph,
    generate_graph_html,
    find_causal_pathways,
    get_graph_analytics,
)


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


def test_graph_analytics_and_pathways():
    G = build_knowledge_graph()
    analytics = get_graph_analytics(G)
    assert analytics["total_nodes"] > 5
    assert analytics["total_edges"] > 5
    assert "element" in analytics["node_types"]

    # Test causal pathway finding
    paths = find_causal_pathways(G, "Ni", "toughness")
    assert isinstance(paths, list)

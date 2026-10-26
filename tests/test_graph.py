import pandas as pd
import pytest

import graph
from conftest import CLICKSTREAM_ROWS

DF = pd.DataFrame(CLICKSTREAM_ROWS, columns=["prev", "curr", "type", "n"])


def test_normalize():
    assert graph.normalize("Élection_présidentielle") == "election presidentielle"


@pytest.mark.parametrize("title, theme", [
    ("Emmanuel_Macron", "Personnalités"),
    ("Rassemblement_national", "Partis et mouvements"),
    ("Motion_de_censure", "Institutions"),
    ("Réforme_des_retraites_en_France", "Débats publics"),
    ("Sondage_en_France", "Élections"),          # générique + marqueur France
    ("Sondage", None),                           # générique sans marqueur France
    ("Miss_France_2026", None),                  # exclusion
    ("other-search", None),
    ("Pain_au_chocolat", None),
])
def test_match_theme(title, theme):
    assert graph.match_theme(title) == theme


def test_theme_mask_keeps_rows_touching_theme():
    kept = DF[graph.theme_mask(DF)]
    assert ("Pain_au_chocolat", "Croissant") not in set(zip(kept["prev"], kept["curr"]))
    assert ("Emmanuel_Macron", "Brigitte_Macron") in set(zip(kept["prev"], kept["curr"]))
    assert ("other-search", "Miss_France_2026") not in set(zip(kept["prev"], kept["curr"]))


def test_create_graph():
    G = graph.create_graph(DF)
    assert G.has_edge("Emmanuel_Macron", "Marine_Le_Pen")
    assert G["Emmanuel_Macron"]["Marine_Le_Pen"]["n"] == 300
    assert not any(n.startswith("other-") for n in G.nodes)
    assert G.nodes["Emmanuel_Macron"]["entrees_search"] == 1000
    assert G.nodes["Emmanuel_Macron"]["entrees_empty"] == 400
    assert G.nodes["Brigitte_Macron"]["theme"] == "hors_theme"
    assert G.nodes["Marine_Le_Pen"]["in_theme"]


def test_create_graph_core_only():
    G = graph.create_graph(DF, core_only=True)
    assert "Brigitte_Macron" not in G
    assert all(d["in_theme"] for _, d in G.nodes(data=True))


def test_graph_metrics():
    m = graph.graph_metrics(graph.create_graph(DF))
    assert m["in_theme"].all()
    assert list(m["rang"]) == list(range(1, len(m) + 1))
    assert m["pagerank"].is_monotonic_decreasing
    macron = m.set_index("page").loc["Emmanuel_Macron"]
    assert macron["entrees_externes"] == 1400
    assert macron["audience_estimee"] == macron["clics_entrants"] + 1400


def test_graph_metrics_empty():
    import networkx as nx
    assert graph.graph_metrics(nx.DiGraph()).empty


def test_save_load_roundtrip(tmp_path):
    G = graph.create_graph(DF)
    path = tmp_path / "g.json"
    graph.save_graph(G, str(path))
    H = graph.load_graph(str(path))
    assert H.is_directed()
    assert set(H.edges) == set(G.edges)
    assert H.nodes["Emmanuel_Macron"]["theme"] == "Personnalités"

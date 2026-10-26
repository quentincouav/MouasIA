import json
import unicodedata

import networkx as nx
import pandas as pd

THEMES = {
    "Institutions": {
        "forts": [
            "Président de la République française", "Premier ministre (France)",
            "Assemblée nationale (France)", "Sénat (France)",
            "Conseil constitutionnel (France)", "Cinquième République",
            "Constitution française", "Article 49 de la Constitution",
            "Motion de censure", "Dissolution de l'Assemblée nationale",
            "Palais de l'Élysée", "Hôtel de Matignon",
        ],
        "generiques": ["Gouvernement", "Ministre", "Ministère", "Assemblée",
                       "Sénat", "Président", "Député", "Sénateur", "Constitution"],
    },
    "Élections": {
        "forts": ["Élection présidentielle française", "Élections législatives françaises",
                  "Élections municipales françaises", "Élections européennes de 2024 en France",
                  "Élections sénatoriales françaises", "Élections régionales françaises"],
        "generiques": ["Élection", "Élections", "Scrutin", "Sondage", "Primaire",
                       "Référendum", "Campagne présidentielle"],
    },
    "Partis et mouvements": {
        "forts": [
            "Rassemblement national", "La France insoumise", "Renaissance (parti",
            "Les Républicains", "Parti socialiste (France)", "Les Écologistes",
            "Europe Écologie Les Verts", "Mouvement démocrate (France)",
            "Horizons (parti", "Reconquête (parti", "Parti communiste français",
            "Nouveau Front populaire", "Ensemble (coalition",
            "Union des droites pour la République",
        ],
        "generiques": ["Parti politique", "Coalition", "Gauche", "Droite"],
    },
    "Personnalités": {
        "forts": [
            "Emmanuel Macron", "Marine Le Pen", "Jordan Bardella", "Jean-Luc Mélenchon",
            "Édouard Philippe", "Gabriel Attal", "Bruno Retailleau", "Laurent Wauquiez",
            "Raphaël Glucksmann", "Marine Tondelier", "François Ruffin", "Fabien Roussel",
            "Éric Zemmour", "Marion Maréchal", "François Bayrou", "Olivier Faure",
            "Sébastien Lecornu", "Michel Barnier", "Xavier Bertrand",
            "Dominique de Villepin", "Gérald Darmanin", "Élisabeth Borne",
        ],
        "generiques": [],
    },
    "Débats publics": {
        "forts": ["Réforme des retraites en France", "Dette publique de la France",
                  "Budget de l'État français", "Laïcité en France", "Immigration en France"],
        "generiques": ["Réforme", "Loi", "Budget", "Dette publique", "Immigration",
                       "Retraites", "Fiscalité", "Pouvoir d'achat", "Insécurité"],
    },
}

MARQUEURS_FRANCE = ["france", "francais", "francaise"]
EXCLUSIONS = ["miss france", "football", "rugby", "jeu video", "serie televisee",
              "(film", "(album", "(chanson", "eurovision", "telerealite"]


def normalize(title) -> str:
    s = str(title).replace("_", " ").lower()
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def _compile(themes):
    return {
        name: ([normalize(k) for k in cfg.get("forts", [])],
               [normalize(k) for k in cfg.get("generiques", [])])
        for name, cfg in themes.items()
    }


def match_theme(title, themes=THEMES, _compiled=None):
    """Renvoie le nom du sous-thème du titre, ou None s'il est hors thème."""
    compiled = _compiled or _compile(themes)
    t = normalize(title)
    if t.startswith("other-") or any(x in t for x in EXCLUSIONS):
        return None
    for name, (forts, _) in compiled.items():     
        if any(k in t for k in forts):
            return name
    if any(m in t for m in MARQUEURS_FRANCE):      
        for name, (_, generiques) in compiled.items():
            if any(k in t for k in generiques):
                return name
    return None


def is_in_theme(title, themes=THEMES):
    return match_theme(title, themes) is not None


def theme_mask(df: pd.DataFrame, themes=THEMES) -> pd.Series:
    """
    Masque des lignes à garder.
    """
    compiled = _compile(themes)
    titles = pd.unique(pd.concat([df["prev"], df["curr"]], ignore_index=True))
    mapping = {t: match_theme(t, themes, compiled) for t in titles}
    curr_in = df["curr"].map(mapping).notna()
    prev_in = df["prev"].map(mapping).notna()
    return curr_in | prev_in

def create_graph(data: pd.DataFrame, themes=THEMES, core_only: bool = False) -> nx.DiGraph:
    """
    data : lignes clickstream.
    core_only : si True, ne garde que les articles du thème.
    """
    compiled = _compile(themes)
    df = data[theme_mask(data, themes)] if len(data) else data

    is_external = df["prev"].str.startswith("other-")
    internal = df[~is_external]
    external = df[is_external]

    edges = internal.groupby(["prev", "curr"], as_index=False).agg(
        n=("n", "sum"), type=("type", "first"))

    G = nx.from_pandas_edgelist(edges, source="prev", target="curr",
                                edge_attr=["n", "type"], create_using=nx.DiGraph())

    ext = external.pivot_table(index="curr", columns="prev", values="n",
                               aggfunc="sum", fill_value=0)
    for page, row in ext.iterrows():
        if page not in G:
            G.add_node(page)
        for source, val in row.items():
            G.nodes[page]["entrees_" + source.replace("other-", "")] = int(val)

    for node in G.nodes:
        theme = match_theme(node, themes, compiled)
        G.nodes[node]["theme"] = theme or "hors_theme"
        G.nodes[node]["in_theme"] = theme is not None

    if core_only:
        G = G.subgraph([n for n, d in G.nodes(data=True) if d["in_theme"]]).copy()
    return G


def graph_metrics(G: nx.DiGraph, only_theme: bool = True) -> pd.DataFrame:
    """Tableau d'indicateurs par article."""
    if G.number_of_nodes() == 0:
        return pd.DataFrame()

    pagerank = nx.pagerank(G, weight="n")
    in_s = dict(G.in_degree(weight="n"))
    out_s = dict(G.out_degree(weight="n"))

    communities = nx.community.louvain_communities(G.to_undirected(), weight="n", seed=42)
    community = {node: i for i, comm in enumerate(communities) for node in comm}

    rows = []
    for node, d in G.nodes(data=True):
        externes = sum(v for k, v in d.items() if k.startswith("entrees_"))
        rows.append({
            "page": node,
            "theme": d.get("theme"),
            "in_theme": d.get("in_theme", False),
            "pagerank": pagerank.get(node, 0.0),
            "clics_entrants": in_s.get(node, 0),
            "clics_sortants": out_s.get(node, 0),
            "entrees_externes": externes,
            "entrees_search": d.get("entrees_search", 0),
            "audience_estimee": in_s.get(node, 0) + externes,
            "communaute": community.get(node, -1),
        })
    df = pd.DataFrame(rows)
    if only_theme:
        df = df[df["in_theme"]]
    df = df.sort_values("pagerank", ascending=False).reset_index(drop=True)
    df["rang"] = df.index + 1
    return df


def graph_info(G: nx.DiGraph, k: int = 10):
    print(f"Noeuds : {G.number_of_nodes():,} | Arêtes : {G.number_of_edges():,}")
    n_theme = sum(1 for _, d in G.nodes(data=True) if d.get("in_theme"))
    print(f"Articles du thème : {n_theme:,}")
    pagerank = nx.pagerank(G, weight="n")
    top_pr = sorted(((n, s) for n, s in pagerank.items() if G.nodes[n].get("in_theme")),
                    key=lambda x: x[1], reverse=True)[:k]
    print(f"Top {k} PageRank :")
    for node, score in top_pr:
        print(f"- {node} [{G.nodes[node]['theme']}]: {score:.5f}")


def graph_to_dict(G: nx.DiGraph) -> dict:
    try:
        return nx.node_link_data(G, edges="links")
    except TypeError:
        return nx.node_link_data(G)


def save_graph(G: nx.DiGraph, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(graph_to_dict(G), f, ensure_ascii=False)


def load_graph(path: str) -> nx.DiGraph:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    try:
        return nx.node_link_graph(data, directed=True, edges="links")
    except TypeError:
        return nx.node_link_graph(data, directed=True)
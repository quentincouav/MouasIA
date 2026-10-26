"""
Pages "politiques" trouvées par le crawler find_relevant_wiki_pages (submodule).

Le fichier politic_related_pages.json a la forme
    {"politic_related_pages": {<chemin de page>: <score du modèle>}}
Les clés sont des chemins du dump .zim (titre avec des "_"), sauf les pages de
départ qui sont restées sous forme d'URL complète. Le run du 2026-10-08
(commit bf882b8) a été fait avec tev1:0.8b, seuil 0.75, profondeur 2.
"""
import json
import os
import re
from urllib.parse import unquote

from extrate import PROJECT_ROOT

DEFAULT_PAGES_FILE = os.environ.get(
    "MAOUSS_PAGES_FILE",
    os.path.join(PROJECT_ROOT, "external", "find_relevant_wiki_pages",
                 "politic_related_pages.json"))
DEFAULT_MIN_SCORE = float(os.environ.get("MAOUSS_MIN_SCORE", "0.9"))

_MOIS = "janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre"
# Pages de dates : le crawler les note haut car elles citent des événements politiques
DATE_RE = re.compile(
    rf"^(-?\d{{1,4}}"                                  # 1949, -52
    rf"|(1er|\d{{1,2}})_({_MOIS})"                      # 16_mai (pas 8_mai_1945)
    rf"|({_MOIS})_\d{{3,4}}"                            # Novembre_1944 (pas Mai_68)
    rf"|années_\d{{1,4}}"                               # Années_1990
    rf"|[IVXLC]+e_(siècle|millénaire)(_av\._J\.-C\.)?"  # XXe_siècle
    rf")$", re.IGNORECASE)


def normalize_title(raw: str) -> str:
    """URL, chemin /wiki/ ou titre -> titre au format clickstream (Titre_avec_underscores)."""
    t = str(raw).strip()
    if "/wiki/" in t:
        t = t[t.find("/wiki/") + len("/wiki/"):]
    t = unquote(t).replace(" ", "_")
    return t[:1].upper() + t[1:]


def is_date_title(title: str) -> bool:
    return bool(DATE_RE.match(title))


def load_relevant_pages(path: str = DEFAULT_PAGES_FILE, min_score: float = DEFAULT_MIN_SCORE,
                        drop_dates: bool = True) -> dict:
    """Renvoie {titre normalisé: score}. Un titre présent plusieurs fois garde son meilleur score."""
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)["politic_related_pages"]
    pages = {}
    for key, score in raw.items():
        score = float(score)
        title = normalize_title(key)
        if score < min_score or (drop_dates and is_date_title(title)):
            continue
        pages[title] = max(score, pages.get(title, 0.0))
    return pages


def load_seed_pages(data_dir: str) -> dict:
    """
    Pages de départ du crawler (data/*.csv, colonne Url), hors catégories, portails
    et pages témoins.
    Score 1.0 : elles sont dans le périmètre par construction. Nécessaire car le
    crawler ne décode pas les URL (%C3%A9...) : Mélenchon, Zemmour, É. Philippe et
    Asselineau sont absents de politic_related_pages.json.
    """
    import pandas as pd
    pages = {}
    if not os.path.isdir(data_dir):
        return pages
    for name in sorted(os.listdir(data_dir)):
        if not name.endswith(".csv"):
            continue
        df = pd.read_csv(os.path.join(data_dir, name), sep=";", dtype=str,
                         keep_default_na=False, on_bad_lines="skip")
        if "Type" in df.columns:
            df = df[df["Type"] != "Unrelated"]  # pages témoins hors sujet (Pain_au_chocolat)
        for url in df.get("Url", []):
            title = normalize_title(url) if url else ""
            if title and not title.startswith(("Catégorie:", "Portail:")):
                pages[title] = 1.0
    return pages


def default_pages(min_score: float = DEFAULT_MIN_SCORE) -> dict:
    """Liste du submodule + ses pages de départ, ou {} (mots-clés seuls) s'il n'est pas initialisé."""
    if not os.path.exists(DEFAULT_PAGES_FILE):
        print(f"[pages] {DEFAULT_PAGES_FILE} absent (git submodule update --init ?) "
              "-> filtrage par mots-clés seulement")
        return {}
    pages = load_relevant_pages(DEFAULT_PAGES_FILE, min_score)
    pages.update(load_seed_pages(os.path.join(os.path.dirname(DEFAULT_PAGES_FILE), "data")))
    return pages

import argparse
import json
import os
from datetime import datetime

import pandas as pd

from extrate import (DATA_DIR, download_clickstream, info_data, latest_available_month,
                     months_between, read_data)
from graph import THEMES, create_graph, graph_info, graph_metrics, save_graph, theme_mask
from relevant_pages import DEFAULT_MIN_SCORE, default_pages

PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
HISTORY_FILE = os.path.join(PROCESSED_DIR, "history.csv")


def month_dir(month: str) -> str:
    return os.path.join(PROCESSED_DIR, month)


def is_processed(month: str) -> bool:
    return os.path.exists(os.path.join(month_dir(month), "summary.json"))


def update_history(month: str, metrics: pd.DataFrame):
    cols = ["month", "page", "theme", "rang", "pagerank", "clics_entrants",
            "entrees_externes", "audience_estimee", "pertinence"]
    new = metrics.assign(month=month)[cols]
    if os.path.exists(HISTORY_FILE):
        old = pd.read_csv(HISTORY_FILE, keep_default_na=False)
        old = old[old["month"] != month]       
        new = pd.concat([old, new], ignore_index=True)
    new.sort_values(["month", "rang"]).to_csv(HISTORY_FILE, index=False)


def run_month(month: str, local_file: str = None, keep_raw: bool = True,
              force: bool = False, themes=THEMES, verbose: bool = True,
              pages: dict = None, min_score: float = DEFAULT_MIN_SCORE) -> dict:
    """pages : {titre: score} à ajouter aux mots-clés (défaut : liste du submodule)."""
    if is_processed(month) and not force:
        print(f"[pipeline] {month} déjà traité (utiliser --force pour refaire)")
        with open(os.path.join(month_dir(month), "summary.json"), encoding="utf-8") as f:
            return json.load(f)

    if pages is None:
        pages = default_pages(min_score)

    path = local_file or download_clickstream(month)

    data = read_data(path, filter_fn=lambda chunk: theme_mask(chunk, themes, pages))
    if verbose:
        info_data(data)

    G = create_graph(data, themes, pages=pages)
    if verbose:
        graph_info(G)
    metrics = graph_metrics(G)

    out = month_dir(month)
    os.makedirs(out, exist_ok=True)
    data.to_csv(os.path.join(out, "edges.csv.gz"), index=False)
    save_graph(G, os.path.join(out, "graph.json"))
    metrics.to_csv(os.path.join(out, "metrics.csv"), index=False)

    summary = {
        "month": month,
        "processed_at": datetime.now().isoformat(timespec="seconds"),
        "rows": int(len(data)),
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "pages_theme": int(len(metrics)),
        "perimetre": {"pages_crawler": len(pages), "score_min": min_score},
        "pages_par_theme": metrics["theme"].value_counts().to_dict() if len(metrics) else {},
        "top10": metrics.head(10)[["page", "theme", "pagerank"]].to_dict("records"),
    }
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    update_history(month, metrics)
    latest = max(m for m in os.listdir(PROCESSED_DIR) if is_processed(m))
    with open(os.path.join(PROCESSED_DIR, "latest.txt"), "w") as f:
        f.write(latest)

    if not keep_raw and local_file is None:
        os.remove(path) 
    print(f"[pipeline] {month} terminé -> {out}")
    return summary


def main():
    p = argparse.ArgumentParser(description="Mise à jour de l'Observatoire Wikipédia France 2027")
    p.add_argument("--month", help="mois AAAA-MM (défaut : dernier disponible)")
    p.add_argument("--from", dest="first", help="premier mois d'un rattrapage")
    p.add_argument("--to", dest="last", help="dernier mois d'un rattrapage")
    p.add_argument("--local", help="fichier clickstream local (.tsv ou .tsv.gz)")
    p.add_argument("--force", action="store_true", help="retraiter un mois déjà traité")
    p.add_argument("--no-keep-raw", action="store_true", help="supprimer le dump après traitement")
    p.add_argument("--min-score", type=float, default=DEFAULT_MIN_SCORE,
                   help="score minimal des pages du crawler (défaut : %(default)s)")
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args()

    if args.first:
        months = months_between(args.first, args.last or latest_available_month())
    elif args.month:
        months = [args.month]
    elif args.local:
        p.error("--local nécessite --month")
    else:
        months = [latest_available_month()]

    pages = default_pages(args.min_score)  # chargée une fois pour tous les mois
    for m in months:
        try:
            run_month(m, local_file=args.local, keep_raw=not args.no_keep_raw,
                      force=args.force, verbose=not args.quiet,
                      pages=pages, min_score=args.min_score)
        except Exception as e:
            print(f"[pipeline] ERREUR {m} : {e}")


if __name__ == "__main__":
    main()
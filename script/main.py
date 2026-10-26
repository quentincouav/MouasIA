from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from extrate import read_data,info_data
from functools import lru_cache
from graph import THEMES, graph_to_dict, load_graph
from pipeline import HISTORY_FILE, PROCESSED_DIR, is_processed, month_dir, run_month
import pandas as pd
import os

import json


app = FastAPI(title="Observatoire Wikipédia France 2027",
              description="Navigation des lecteurs de Wikipédia FR autour de l'actualité politique")

def clear_cache():
    get_edges.cache_clear(); get_metrics.cache_clear(); get_graph.cache_clear()

def available_months():
    if not os.path.isdir(PROCESSED_DIR):
        return []
    return sorted(m for m in os.listdir(PROCESSED_DIR) if is_processed(m))

@lru_cache(maxsize=4)
def get_edges(month):
    return pd.read_csv(os.path.join(month_dir(month), "edges.csv.gz"), keep_default_na=False)


@lru_cache(maxsize=4)
def get_metrics(month):
    return pd.read_csv(os.path.join(month_dir(month), "metrics.csv"), keep_default_na=False)


@lru_cache(maxsize=4)
def get_graph(month):
    return load_graph(os.path.join(month_dir(month), "graph.json"))

def resolve_month(month):
    months = available_months()
    if not months:
        raise HTTPException(404, "Aucune donnée : lancer d'abord `python pipeline.py`")
    if month is None:
        return months[-1]
    if month not in months:
        raise HTTPException(404, f"Mois {month} non traité. Disponibles : {months}")
    return month

@app.get("/")
def home():
    return {"observatoire": "Wikipédia France 2027", "mois_disponibles": available_months(),
            "routes": ["/months", "/themes", "/summary", "/data/{n}", "/graph", "/top",
                       "/page/{title}", "/evolution/{title}", "/update"]}

@app.get("/months")
def months():
    return available_months()

@app.get("/themes")
def themes():
    return THEMES

@app.get("/summary")
def summary(month: str = None):
    month = resolve_month(month)
    with open(os.path.join(month_dir(month), "summary.json"), encoding="utf-8") as f:
        return json.load(f)
    
@app.get("/data/{n}")
def get_n_row_data(n: int, month: str = None):
    """Les n premières transitions (triées par nombre de clics)."""
    month = resolve_month(month)
    df = get_edges(month).sort_values("n", ascending=False).head(n)
    return df.to_dict(orient="records")


@app.get("/graph")
def get_graph_json(month: str = None, min_clics: int = Query(50, ge=0),
                   core_only: bool = True):
    """Graphe au format node-link (filtré pour rester affichable)."""
    month = resolve_month(month)
    G = get_graph(month)
    keep_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get("n", 0) >= min_clics]
    H = G.edge_subgraph(keep_edges).copy()
    if core_only:
        H = H.subgraph([x for x, d in H.nodes(data=True) if d.get("in_theme")]).copy()
    return graph_to_dict(H)

@app.post("/update")
def update(background_tasks: BackgroundTasks, month: str = None, force: bool = False):
    """Lance le pipeline en tâche de fond (dernier mois disponible par défaut)."""
    def job():
        from extrate import latest_available_month
        run_month(month or latest_available_month(), force=force, verbose=False)
        clear_cache()
    background_tasks.add_task(job)
    return {"status": "mise à jour lancée", "month": month or "dernier disponible"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
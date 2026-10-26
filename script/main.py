from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from functools import lru_cache
from extrate import latest_available_month
from graph import THEMES, graph_to_dict, load_graph
from jobs import UpdatePool, start_poller
from pipeline import is_processed, month_dir, run_month
import pipeline
import pandas as pd
import os

import json

# 0 désactive la vérification automatique des nouveaux dumps
POLL_HOURS = float(os.environ.get("MAOUSS_POLL_HOURS", "12"))


def clear_cache():
    get_edges.cache_clear(); get_metrics.cache_clear(); get_graph.cache_clear()

def run_update(month, force):
    return run_month(month, force=force, verbose=False)

pool = UpdatePool(runner=run_update, on_done=clear_cache)

@asynccontextmanager
async def lifespan(app):
    stop = None
    if POLL_HOURS > 0:
        stop = start_poller(pool, latest_available_month, is_processed, POLL_HOURS * 3600)
    yield
    if stop:
        stop.set()
    pool.shutdown()

app = FastAPI(title="Observatoire Wikipédia France 2027",
              description="Navigation des lecteurs de Wikipédia FR autour de l'actualité politique",
              lifespan=lifespan)

def available_months():
    if not os.path.isdir(pipeline.PROCESSED_DIR):
        return []
    return sorted(m for m in os.listdir(pipeline.PROCESSED_DIR) if is_processed(m))

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
            "routes": ["/months", "/themes", "/summary", "/data/{n}", "/graph",
                       "POST /update", "/update/jobs", "/update/jobs/{job_id}"]}

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

@app.post("/update", status_code=202)
def update(month: str = Query(None, pattern=r"^\d{4}-\d{2}$"), force: bool = False):
    """Met le pipeline en file d'attente (dernier mois disponible par défaut).
    Une demande pour un mois déjà en attente ou en cours renvoie le job existant."""
    if month is None:
        try:
            month = latest_available_month()
        except RuntimeError as e:
            raise HTTPException(503, str(e))
    return pool.submit(month, force=force)

@app.get("/update/jobs")
def update_jobs():
    return pool.list()

@app.get("/update/jobs/{job_id}")
def update_job(job_id: str):
    job = pool.get(job_id)
    if job is None:
        raise HTTPException(404, f"Job {job_id} inconnu")
    return job

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)

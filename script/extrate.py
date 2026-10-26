import csv
import os
import shutil
import urllib.error
import urllib.request
from datetime import date

import pandas as pd

BASE_URL = "https://dumps.wikimedia.org/other/clickstream"
WIKI = "frwiki"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("MAOUSS_DATA_DIR", os.path.join(PROJECT_ROOT, "data"))
RAW_DIR = os.path.join(DATA_DIR, "raw")
COLUMNS = ["prev", "curr", "type", "n"]

# Wikimedia renvoie 403 au User-Agent par défaut de urllib
# https://meta.wikimedia.org/wiki/User-Agent_policy
USER_AGENT = os.environ.get("MAOUSS_USER_AGENT",
                            "MaoussIA-observatoire/0.1 (projet etudiant EPITA)")
HEADERS = {"User-Agent": USER_AGENT}

READ_OPTIONS = dict(
    sep="\t",
    header=None,
    names=COLUMNS,
    quoting=csv.QUOTE_NONE,
    dtype={"prev": str, "curr": str, "type": str, "n": "int64"},
    keep_default_na=False,
    na_filter=False,
    on_bad_lines="skip",
    compression="infer",
)

def clickstream_url(month: str, wiki: str = WIKI) -> str:
    return f"{BASE_URL}/{month}/clickstream-{wiki}-{month}.tsv.gz"


def month_is_available(month: str, wiki: str = WIKI) -> bool:
    req = urllib.request.Request(clickstream_url(month, wiki), method="HEAD", headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status == 200
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        raise  # 403, 5xx... : ne pas confondre avec un mois non publié


def previous_months(start: date, count: int):
    """Génère les mois précédant `start` au format AAAA-MM."""
    y, m = start.year, start.month
    for _ in range(count):
        m -= 1
        if m == 0:
            y, m = y - 1, 12
        yield f"{y}-{m:02d}"


def months_between(first: str, last: str):
    """Liste des mois de `first` à `last` inclus (AAAA-MM)."""
    y, m = map(int, first.split("-"))
    ly, lm = map(int, last.split("-"))
    out = []
    while (y, m) <= (ly, lm):
        out.append(f"{y}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def latest_available_month(wiki: str = WIKI, max_back: int = 6) -> str:
    """Dernier mois publié."""
    for month in previous_months(date.today(), max_back):
        if month_is_available(month, wiki):
            return month
    raise RuntimeError(f"Aucun dump {wiki} trouvé sur les {max_back} derniers mois")


def download_clickstream(month: str, wiki: str = WIKI, raw_dir: str = RAW_DIR,
                         force: bool = False) -> str:
    """Télécharge le dump et renvoie son chemin local."""
    os.makedirs(raw_dir, exist_ok=True)
    path = os.path.join(raw_dir, f"clickstream-{wiki}-{month}.tsv.gz")
    if os.path.exists(path) and not force:
        print(f"[extraction] déjà présent : {path}")
        return path

    url = clickstream_url(month, wiki)
    print(f"[extraction] téléchargement {url}")
    tmp = path + ".part"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=120) as resp, open(tmp, "wb") as f:
        shutil.copyfileobj(resp, f, length=1 << 20)
    os.replace(tmp, path) 
    return path

def read_data(file_name: str, filter_fn=None, chunksize: int = 2_000_000) -> pd.DataFrame:
    """
    Lit un fichier clickstream (.tsv ou .tsv.gz).

    filter_fn : fonction(DataFrame) -> masque booléen.
    """
    if filter_fn is None:
        return pd.read_csv(file_name, **READ_OPTIONS)

    kept, total = [], 0
    for chunk in pd.read_csv(file_name, chunksize=chunksize, **READ_OPTIONS):
        total += len(chunk)
        kept.append(chunk[filter_fn(chunk)])
    data = pd.concat(kept, ignore_index=True) if kept else pd.DataFrame(columns=COLUMNS)
    print(f"[extraction] {total:,} lignes lues, {len(data):,} retenues")
    return data


def info_data(data: pd.DataFrame):
    print("First value :")
    print(data.head())
    print("--------------------------------------------")
    print("Shape :", data.shape)
    if len(data):
        print("Répartition par type :")
        print(data.groupby("type")["n"].agg(["count", "sum"]))
        print("Pages les plus atteintes :")
        print(data.groupby("curr")["n"].sum().sort_values(ascending=False).head(10))

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "script"))

# Pas de poller réseau pendant les tests
os.environ["MAOUSS_POLL_HOURS"] = "0"

# Extrait de clickstream frwiki (prev, curr, type, n)
CLICKSTREAM_ROWS = [
    ("other-search", "Emmanuel_Macron", "external", 1000),
    ("other-empty", "Emmanuel_Macron", "external", 400),
    ("other-search", "Rassemblement_national", "external", 300),
    ("Emmanuel_Macron", "Marine_Le_Pen", "link", 300),
    ("Marine_Le_Pen", "Rassemblement_national", "link", 200),
    ("Rassemblement_national", "Jordan_Bardella", "link", 150),
    ("Jordan_Bardella", "Marine_Le_Pen", "link", 120),
    ("Emmanuel_Macron", "Brigitte_Macron", "link", 90),
    ("Pain_au_chocolat", "Croissant", "link", 50),
    ("other-search", "Miss_France_2026", "external", 500),
    ("Miss_France_2026", "Emmanuel_Macron", "link", 10),
]


@pytest.fixture
def clickstream_file(tmp_path):
    path = tmp_path / "clickstream-frwiki-2026-01.tsv"
    path.write_text("".join(f"{p}\t{c}\t{t}\t{n}\n" for p, c, t, n in CLICKSTREAM_ROWS),
                    encoding="utf-8")
    return str(path)


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Redirige data/processed vers un dossier temporaire."""
    import pipeline
    processed = tmp_path / "processed"
    monkeypatch.setattr(pipeline, "PROCESSED_DIR", str(processed))
    monkeypatch.setattr(pipeline, "HISTORY_FILE", str(processed / "history.csv"))
    return processed

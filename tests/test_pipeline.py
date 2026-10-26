import json
import os

import pandas as pd

import pipeline


def test_run_month_writes_outputs(clickstream_file, data_dir):
    summary = pipeline.run_month("2026-01", local_file=clickstream_file, verbose=False)

    out = data_dir / "2026-01"
    for name in ["edges.csv.gz", "graph.json", "metrics.csv", "summary.json"]:
        assert (out / name).exists(), name
    assert summary["month"] == "2026-01"
    assert summary["pages_theme"] > 0
    assert summary["top10"][0]["page"]
    assert (data_dir / "latest.txt").read_text() == "2026-01"
    assert pipeline.is_processed("2026-01")
    assert os.path.exists(clickstream_file)  # un fichier local n'est jamais supprimé


def test_run_month_skips_processed(clickstream_file, data_dir, monkeypatch):
    first = pipeline.run_month("2026-01", local_file=clickstream_file, verbose=False)
    monkeypatch.setattr(pipeline, "read_data", lambda *a, **k: (_ for _ in ()).throw(AssertionError))
    assert pipeline.run_month("2026-01", local_file=clickstream_file, verbose=False) == first


def test_history_replaces_month(clickstream_file, data_dir):
    pipeline.run_month("2026-01", local_file=clickstream_file, verbose=False)
    pipeline.run_month("2026-02", local_file=clickstream_file, verbose=False)
    pipeline.run_month("2026-01", local_file=clickstream_file, verbose=False, force=True)

    hist = pd.read_csv(pipeline.HISTORY_FILE)
    per_month = hist.groupby("month").size()
    assert list(per_month.index) == ["2026-01", "2026-02"]
    assert per_month["2026-01"] == per_month["2026-02"]
    assert (data_dir / "latest.txt").read_text() == "2026-02"


def test_run_month_with_crawler_pages(clickstream_file, data_dir):
    summary = pipeline.run_month("2026-01", local_file=clickstream_file, verbose=False,
                                 pages={"Brigitte_Macron": 0.95}, min_score=0.9)
    assert summary["perimetre"] == {"pages_crawler": 1, "score_min": 0.9}
    assert summary["pages_par_theme"]["Autres sujets politiques"] == 1
    hist = pd.read_csv(pipeline.HISTORY_FILE)
    assert hist.set_index("page").loc["Brigitte_Macron", "pertinence"] == 0.95


def test_summary_json_is_valid(clickstream_file, data_dir):
    pipeline.run_month("2026-01", local_file=clickstream_file, verbose=False)
    with open(data_dir / "2026-01" / "summary.json", encoding="utf-8") as f:
        s = json.load(f)
    assert s["nodes"] >= s["pages_theme"]
    assert sum(s["pages_par_theme"].values()) == s["pages_theme"]

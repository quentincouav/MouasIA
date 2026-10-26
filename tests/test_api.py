import pytest
from fastapi.testclient import TestClient

import main
import pipeline
from jobs import UpdatePool


@pytest.fixture
def client(data_dir, monkeypatch):
    main.clear_cache()
    pool = UpdatePool(lambda m, f: {"month": m}, on_done=main.clear_cache)
    monkeypatch.setattr(main, "pool", pool)
    monkeypatch.setattr(main, "latest_available_month", lambda: "2026-01")
    yield TestClient(main.app)
    pool.shutdown()
    main.clear_cache()


@pytest.fixture
def processed(client, clickstream_file):
    pipeline.run_month("2026-01", local_file=clickstream_file, verbose=False)
    return client


def test_no_data(client):
    assert client.get("/months").json() == []
    assert client.get("/summary").status_code == 404


def test_home_and_themes(client):
    assert "POST /update" in client.get("/").json()["routes"]
    assert "Personnalités" in client.get("/themes").json()


def test_summary(processed):
    assert processed.get("/months").json() == ["2026-01"]
    assert processed.get("/summary").json()["month"] == "2026-01"
    assert processed.get("/summary", params={"month": "2025-01"}).status_code == 404


def test_data_sorted(processed):
    rows = processed.get("/data/3").json()
    assert len(rows) == 3
    assert [r["n"] for r in rows] == sorted((r["n"] for r in rows), reverse=True)


def test_graph_filters(processed):
    g = processed.get("/graph", params={"min_clics": 150}).json()
    edges = {(e["source"], e["target"]) for e in g["links"]}
    assert ("Emmanuel_Macron", "Marine_Le_Pen") in edges
    assert ("Jordan_Bardella", "Marine_Le_Pen") not in edges          # 120 < 150
    assert all(n["in_theme"] for n in g["nodes"])
    assert processed.get("/graph", params={"min_clics": -1}).status_code == 422


def test_update_queues_job(client):
    r = client.post("/update", params={"month": "2026-03"})
    assert r.status_code == 202
    job = r.json()
    assert job["month"] == "2026-03"
    main.pool.wait(job["id"])
    status = client.get(f"/update/jobs/{job['id']}").json()
    assert status["status"] == "done"
    assert any(j["id"] == job["id"] for j in client.get("/update/jobs").json())


def test_update_defaults_to_latest(client):
    assert client.post("/update").json()["month"] == "2026-01"


def test_update_rejects_bad_month(client):
    assert client.post("/update", params={"month": "janvier"}).status_code == 422


def test_update_no_dump_available(client, monkeypatch):
    def none():
        raise RuntimeError("Aucun dump")
    monkeypatch.setattr(main, "latest_available_month", none)
    assert client.post("/update").status_code == 503


def test_unknown_job(client):
    assert client.get("/update/jobs/inconnu").status_code == 404

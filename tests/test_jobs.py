import threading

import pytest

from jobs import UpdatePool, poll_once


@pytest.fixture
def blocking_pool():
    """Pool dont le runner attend un signal : permet d'observer les états."""
    release = threading.Event()
    calls = []

    def runner(month, force):
        calls.append(month)
        release.wait(5)
        return {"month": month}

    pool = UpdatePool(runner)
    yield pool, release, calls
    release.set()
    pool.shutdown()


def test_job_lifecycle():
    done = []
    pool = UpdatePool(lambda m, f: {"month": m, "force": f}, on_done=lambda: done.append(1))
    job = pool.submit("2026-01", force=True)
    assert job["status"] in ("queued", "running")
    finished = pool.wait(job["id"])
    assert finished["status"] == "done"
    assert finished["summary"] == {"month": "2026-01", "force": True}
    assert finished["started_at"] and finished["finished_at"]
    assert done == [1]
    pool.shutdown()


def test_same_month_is_deduplicated(blocking_pool):
    pool, release, calls = blocking_pool
    a = pool.submit("2026-01")
    b = pool.submit("2026-01")
    assert a["id"] == b["id"]
    release.set()
    pool.wait(a["id"])
    assert calls == ["2026-01"]
    # une fois terminé, le mois peut être redemandé
    c = pool.submit("2026-01")
    assert c["id"] != a["id"]
    pool.wait(c["id"])


def test_jobs_run_one_at_a_time(blocking_pool):
    pool, release, calls = blocking_pool
    a = pool.submit("2026-01")
    b = pool.submit("2026-02")
    pool_states = {j["month"]: j["status"] for j in pool.list()}
    assert pool_states["2026-02"] == "queued"
    release.set()
    pool.wait(a["id"]); pool.wait(b["id"])
    assert calls == ["2026-01", "2026-02"]


def test_failed_job_is_reported():
    def boom(month, force):
        raise RuntimeError("dump introuvable")
    done = []
    pool = UpdatePool(boom, on_done=lambda: done.append(1))
    job = pool.wait(pool.submit("2026-01")["id"])
    assert job["status"] == "failed"
    assert job["error"] == "RuntimeError: dump introuvable"
    assert done == []
    # un échec libère le mois
    assert pool.submit("2026-01")["id"] != job["id"]
    pool.shutdown()


def test_get_unknown_and_list_order():
    pool = UpdatePool(lambda m, f: {})
    assert pool.get("nope") is None
    a = pool.wait(pool.submit("2026-01")["id"])
    b = pool.wait(pool.submit("2026-02")["id"])
    assert [j["id"] for j in pool.list()] == [b["id"], a["id"]]
    pool.shutdown()


def test_finished_jobs_are_pruned():
    pool = UpdatePool(lambda m, f: {}, keep=2)
    ids = []
    for m in ["2026-01", "2026-02", "2026-03", "2026-04"]:
        ids.append(pool.wait(pool.submit(m)["id"])["id"])
    assert len(pool.list()) <= 3
    assert pool.get(ids[-1]) is not None
    pool.shutdown()


def test_poll_once():
    pool = UpdatePool(lambda m, f: {})
    assert poll_once(pool, lambda: "2026-01", lambda m: True) is None
    job = poll_once(pool, lambda: "2026-02", lambda m: False)
    assert job["month"] == "2026-02"

    def offline():
        raise RuntimeError("réseau")
    assert poll_once(pool, offline, lambda m: False) is None
    pool.shutdown()

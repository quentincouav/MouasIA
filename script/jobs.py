import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class UpdatePool:
    """
    File d'attente des mises à jour du pipeline.

    - une demande pour un mois déjà en attente ou en cours renvoie le job existant ;
    - max_workers=1 par défaut : run_month réécrit history.csv, deux runs en
      parallèle se marcheraient dessus.
    """

    def __init__(self, runner, max_workers: int = 1, keep: int = 50, on_done=None):
        self.runner = runner            # runner(month, force) -> summary (dict)
        self.on_done = on_done          # appelé après chaque job réussi
        self.keep = keep                # nombre de jobs terminés conservés
        self._executor = ThreadPoolExecutor(max_workers=max_workers,
                                            thread_name_prefix="update")
        self._lock = threading.Lock()
        self._jobs = {}                 # id -> job (dict), ordre d'insertion
        self._active = {}               # mois -> id du job en attente / en cours

    def submit(self, month: str, force: bool = False) -> dict:
        with self._lock:
            if month in self._active:
                return dict(self._jobs[self._active[month]])
            job = {"id": uuid.uuid4().hex[:12], "month": month, "force": force,
                   "status": "queued", "created_at": _now(), "started_at": None,
                   "finished_at": None, "error": None, "summary": None}
            self._jobs[job["id"]] = job
            self._active[month] = job["id"]
            self._prune()
            snapshot = dict(job)
        self._executor.submit(self._run, job["id"])
        return snapshot

    def _run(self, job_id: str):
        with self._lock:
            job = self._jobs[job_id]
            job["status"], job["started_at"] = "running", _now()
        try:
            summary = self.runner(job["month"], job["force"])
            status, error = "done", None
        except Exception as e:
            summary, status, error = None, "failed", f"{type(e).__name__}: {e}"
        with self._lock:
            job.update(status=status, error=error, summary=summary, finished_at=_now())
            self._active.pop(job["month"], None)
        if status == "done" and self.on_done:
            self.on_done()

    def _prune(self):
        finished = [i for i, j in self._jobs.items() if j["status"] in ("done", "failed")]
        for i in finished[:max(0, len(finished) - self.keep)]:
            del self._jobs[i]

    def get(self, job_id: str):
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None

    def list(self) -> list:
        with self._lock:
            return [dict(j) for j in reversed(self._jobs.values())]

    def wait(self, job_id: str, timeout: float = 10.0) -> dict:
        """Attend la fin d'un job (utile pour les tests et les scripts)."""
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            job = self.get(job_id)
            if job and job["status"] in ("done", "failed"):
                return job
            time.sleep(0.02)
        raise TimeoutError(job_id)

    def shutdown(self):
        self._executor.shutdown(wait=False, cancel_futures=True)


def poll_once(pool: UpdatePool, latest_fn, is_processed_fn):
    """Soumet le dernier mois publié s'il n'est pas encore traité. Renvoie le job ou None."""
    try:
        month = latest_fn()
    except Exception as e:
        print(f"[poller] impossible de trouver le dernier mois : {e}")
        return None
    if is_processed_fn(month):
        return None
    return pool.submit(month)


def start_poller(pool: UpdatePool, latest_fn, is_processed_fn, interval_s: float):
    """Vérifie périodiquement si un nouveau dump est publié. Renvoie un Event pour l'arrêter."""
    stop = threading.Event()

    def loop():
        while not stop.is_set():
            poll_once(pool, latest_fn, is_processed_fn)
            stop.wait(interval_s)

    threading.Thread(target=loop, name="poller", daemon=True).start()
    return stop

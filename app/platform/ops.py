from __future__ import annotations

import json
import os
import sqlite3
import threading
import urllib.request
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MetadataStore:
    """Small durable metadata store; replaceable with PostgreSQL without changing API contracts."""

    def __init__(self, path: str | None = None):
        default = Path(__file__).resolve().parents[2] / "app" / "artifacts" / "platform.db"
        self.path = Path(path or os.getenv("QUALITY_DB_PATH", str(default)))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS job_runs (
                    job_id TEXT PRIMARY KEY,
                    job_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL,
                    payload TEXT NOT NULL,
                    result TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

    def audit(self, event_type: str, actor: str, payload: dict[str, Any]) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO audit_events(event_type, actor, payload, created_at) VALUES (?, ?, ?, ?)",
                (event_type, actor, json.dumps(payload, default=str), utc_now()),
            )

    def recent_audit(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, event_type, actor, payload, created_at FROM audit_events ORDER BY id DESC LIMIT ?",
                (max(1, min(limit, 500)),),
            ).fetchall()
        return [{**dict(row), "payload": json.loads(row["payload"])} for row in rows]

    def save_job(self, job: dict[str, Any]) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO job_runs
                (job_id, job_type, status, attempts, payload, result, error, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job["job_id"], job["job_type"], job["status"], job["attempts"],
                    json.dumps(job.get("payload", {}), default=str),
                    json.dumps(job["result"], default=str) if job.get("result") is not None else None,
                    job.get("error"), job.get("created_at", utc_now()), utc_now(),
                ),
            )

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM job_runs WHERE job_id = ?", (job_id,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["payload"] = json.loads(result["payload"])
        result["result"] = json.loads(result["result"]) if result["result"] else None
        return result


class JobManager:
    def __init__(self, store: MetadataStore):
        self.store = store
        self.executor = ThreadPoolExecutor(max_workers=int(os.getenv("QUALITY_JOB_WORKERS", "2")))

    def submit(self, job_type: str, payload: dict[str, Any], worker: Callable[[], Any]) -> str:
        job_id = f"job-{uuid.uuid4().hex[:12]}"
        job = {
            "job_id": job_id, "job_type": job_type, "status": "queued", "attempts": 0,
            "payload": payload, "result": None, "error": None, "created_at": utc_now(),
        }
        self.store.save_job(job)
        self.executor.submit(self._run, job, worker)
        return job_id

    def _run(self, job: dict[str, Any], worker: Callable[[], Any]) -> None:
        max_attempts = int(os.getenv("QUALITY_JOB_MAX_ATTEMPTS", "3"))
        for attempt in range(1, max_attempts + 1):
            job["attempts"] = attempt
            job["status"] = "running"
            self.store.save_job(job)
            try:
                job["result"] = worker()
                job["status"] = "succeeded"
                self.store.save_job(job)
                return
            except Exception as error:  # Persist failure and retry; never hide final failure.
                job["error"] = str(error)
                job["status"] = "retrying" if attempt < max_attempts else "failed"
                self.store.save_job(job)
        return


def notify_webhook(event: dict[str, Any]) -> dict[str, Any]:
    url = os.getenv("QUALITY_WEBHOOK_URL")
    if not url:
        return {"status": "skipped", "reason": "QUALITY_WEBHOOK_URL is not configured"}
    request = urllib.request.Request(
        url,
        data=json.dumps(event, default=str).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return {"status": "sent", "http_status": response.status}
    except Exception as error:
        return {"status": "failed", "error": str(error)}

from pathlib import Path

from app.platform.ops import JobManager, MetadataStore


def test_metadata_store_persists_audit_and_job(tmp_path: Path) -> None:
    store = MetadataStore(str(tmp_path / "platform.db"))
    store.audit("test_event", "pytest", {"ok": True})
    assert store.recent_audit(1)[0]["event_type"] == "test_event"

    jobs = JobManager(store)
    job_id = jobs.submit("test", {"value": 1}, lambda: {"completed": True})
    import time
    for _ in range(20):
        job = store.get_job(job_id)
        if job and job["status"] == "succeeded":
            break
        time.sleep(0.02)
    assert store.get_job(job_id)["result"] == {"completed": True}
    jobs.executor.shutdown(wait=True)

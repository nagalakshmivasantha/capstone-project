from __future__ import annotations

import json
from pathlib import Path

from app.storage.minio_adapter import MinioAdapter


ROOT = Path(__file__).resolve().parents[1]


def setup_minio_simulation() -> dict:
    adapter = MinioAdapter()
    adapter.list_buckets()
    files = [
        ("features", str(ROOT / "tests" / "fixtures" / "features.csv")),
        ("features", str(ROOT / "tests" / "fixtures" / "features.parquet")),
        ("quality-events", str(ROOT / "tests" / "fixtures" / "events.csv")),
        ("quality-events", str(ROOT / "tests" / "fixtures" / "events.parquet")),
    ]
    uploads = adapter.simulate_uploads(files)
    return {"endpoint": adapter.endpoint, "buckets": adapter.list_buckets()["buckets"], "uploads": uploads}


if __name__ == "__main__":
    print(json.dumps(setup_minio_simulation(), indent=2))

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any


def create_lineage_manifest(**kwargs: Any) -> Dict[str, Any]:
    payload = {
        "dataset_id": kwargs.get("dataset_id"),
        "source": kwargs.get("source"),
        "source_version": kwargs.get("source_version"),
        "schema_version": kwargs.get("schema_version"),
        "configuration_version": kwargs.get("configuration_version"),
        "query_id": kwargs.get("query_id"),
        "software_version": kwargs.get("software_version", "local-dev"),
        "retrieval_timestamp": kwargs.get("retrieval_timestamp", datetime.now(timezone.utc).isoformat()),
        "transformation": kwargs.get("transformation", "raw"),
        "result_hash": None,
    }
    payload["result_hash"] = "sha256:" + hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return payload

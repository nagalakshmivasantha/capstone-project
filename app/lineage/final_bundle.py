from __future__ import annotations

from typing import Any, Dict

from app.lineage.evidence import write_evidence_manifest


def final_evidence_bundle() -> Dict[str, Any]:
    payload = {
        "dataset_id": "demo-dataset",
        "source": "minio://features/historical_features.csv",
        "source_version": "sha256:demo",
        "schema_version": "v1",
        "configuration_version": "v1",
        "query_id": "q-demo",
        "software_version": "local-dev",
        "result_hash": "sha256:demo-output",
    }
    return write_evidence_manifest(payload)

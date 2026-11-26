from __future__ import annotations

import hashlib
import json
from typing import Any, Dict


class DeterministicCache:
    def __init__(self) -> None:
        self._store: Dict[str, Any] = {}

    def build_key(self, dataset_version: str, query: Dict[str, Any], entity_set: Any, time_range: Any, feature_set: Any, configuration_version: str, schema_version: str) -> str:
        payload = {
            "dataset_version": dataset_version,
            "query": query,
            "entity_set": entity_set,
            "time_range": time_range,
            "feature_set": feature_set,
            "configuration_version": configuration_version,
            "schema_version": schema_version,
        }
        serialized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Any:
        return self._store.get(key)

    def put(self, key: str, value: Any) -> None:
        self._store[key] = value

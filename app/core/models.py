from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


def ensure_timezone_aware(value: datetime, field_name: str) -> datetime:
    if value is None:
        raise ValueError(f"{field_name} cannot be None")
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if value.tzinfo is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value


@dataclass
class FeatureRecord:
    entity_id: str
    event_timestamp: datetime
    created_timestamp: datetime
    feature_name: str
    feature_value: Any
    source_id: str = "unknown"
    source_version: str = "unknown"
    partition_id: str = "default"

    def __post_init__(self):
        self.event_timestamp = ensure_timezone_aware(self.event_timestamp, "event_timestamp")
        self.created_timestamp = ensure_timezone_aware(self.created_timestamp, "created_timestamp")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "event_timestamp": self.event_timestamp.isoformat(),
            "created_timestamp": self.created_timestamp.isoformat(),
            "feature_name": self.feature_name,
            "feature_value": self.feature_value,
            "source_id": self.source_id,
            "source_version": self.source_version,
            "partition_id": self.partition_id,
        }


@dataclass
class QuerySpec:
    entity_id: str
    event_time: datetime
    feature_names: Optional[List[str]] = None
    include_metadata: bool = True

    def __post_init__(self):
        self.event_time = ensure_timezone_aware(self.event_time, "event_time")

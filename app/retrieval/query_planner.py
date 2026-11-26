from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


class QueryPlan:
    def __init__(self, source_format: str, source_location: str, estimated_rows: int, total_partitions: int, relevant_partitions: int):
        self.source_format = source_format
        self.source_location = source_location
        self.estimated_rows = estimated_rows
        self.total_partitions = total_partitions
        self.relevant_partitions = relevant_partitions

    def diagnostics(self) -> Dict[str, Any]:
        pruned = max(self.total_partitions - self.relevant_partitions, 0)
        return {
            "source_format": self.source_format,
            "source_location": self.source_location,
            "estimated_rows": self.estimated_rows,
            "partitions_considered": self.total_partitions,
            "partitions_scanned": self.relevant_partitions,
            "partitions_skipped": pruned,
            "pruning_ratio": round(pruned / max(self.total_partitions, 1), 4),
            "join_strategy": "point_in_time",
        }


def build_query_plan(source_format: str, source_location: str, estimated_rows: int, total_partitions: int = 10, relevant_partitions: int = 4) -> Dict[str, Any]:
    return QueryPlan(source_format, source_location, estimated_rows, total_partitions, relevant_partitions).diagnostics()

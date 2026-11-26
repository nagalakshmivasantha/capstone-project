from __future__ import annotations

from typing import Any, Dict


def build_diagnostics(**kwargs: Any) -> Dict[str, Any]:
    return {
        "source_format": kwargs.get("source_format", "unknown"),
        "source_location": kwargs.get("source_location", "unknown"),
        "estimated_rows": kwargs.get("estimated_rows", 0),
        "partitions_considered": kwargs.get("partitions_considered", 0),
        "partitions_scanned": kwargs.get("partitions_scanned", 0),
        "partitions_skipped": kwargs.get("partitions_skipped", 0),
        "cache_hit": kwargs.get("cache_hit", False),
        "join_strategy": kwargs.get("join_strategy", "point_in_time"),
        "execution_time_ms": kwargs.get("execution_time_ms", 0),
        "memory_usage_mb": kwargs.get("memory_usage_mb", 0),
    }


def partition_pruning(total_partitions: int, relevant_partitions: int) -> Dict[str, Any]:
    considered = max(total_partitions, 1)
    scanned = max(relevant_partitions, 0)
    pruned = max(considered - scanned, 0)
    ratio = 0.0 if considered == 0 else round(pruned / considered, 4)
    return {
        "partitions_considered": considered,
        "partitions_scanned": scanned,
        "partitions_pruned": pruned,
        "pruning_ratio": ratio,
    }

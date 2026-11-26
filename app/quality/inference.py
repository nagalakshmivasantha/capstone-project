from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd


def canonicalize_column_name(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_").replace("/", "_")


def infer_schema(df: pd.DataFrame) -> Dict[str, Any]:
    """Heuristically infer column semantics and confidence levels."""
    schema: List[Dict[str, Any]] = []
    for column in df.columns:
        series = df[column]
        lowered = canonicalize_column_name(str(column))
        if any(token in lowered for token in ["user", "entity", "customer", "account", "id"]):
            semantic_type = "entity_id"
            confidence = 0.95
        elif any(token in lowered for token in ["event", "time", "date", "timestamp", "created"]):
            semantic_type = "timestamp"
            confidence = 0.9
        elif pd.api.types.is_numeric_dtype(series):
            semantic_type = "numeric"
            confidence = 0.85
        elif pd.api.types.is_bool_dtype(series):
            semantic_type = "boolean"
            confidence = 0.8
        else:
            non_null = series.dropna()
            unique_ratio = 1.0 if non_null.empty else (non_null.nunique() / len(non_null))
            if unique_ratio < 0.1:
                semantic_type = "categorical"
                confidence = 0.8
            else:
                semantic_type = "string"
                confidence = 0.6

        if "feature" in lowered and semantic_type == "string":
            semantic_type = "feature_value"
            confidence = 0.75

        if confidence < 0.55:
            semantic_type = "AMBIGUOUS"

        schema.append({
            "column": column,
            "canonical_name": lowered,
            "semantic_type": semantic_type,
            "confidence": round(confidence, 2),
            "nullability": float(series.isna().mean()),
        })

    return {"columns": schema}


def detect_schema_drift(old_schema: Dict[str, Any], new_schema: Dict[str, Any]) -> Dict[str, Any]:
    old_map = {entry["column"]: entry for entry in old_schema.get("columns", [])}
    new_map = {entry["column"]: entry for entry in new_schema.get("columns", [])}

    added = [column for column in new_map if column not in old_map]
    removed = [column for column in old_map if column not in new_map]
    type_changes: List[Dict[str, Any]] = []
    nullability_changes: List[Dict[str, Any]] = []

    for column in set(old_map) & set(new_map):
        old_entry = old_map[column]
        new_entry = new_map[column]
        if old_entry.get("semantic_type") != new_entry.get("semantic_type"):
            type_changes.append({"column": column, "old": old_entry.get("semantic_type"), "new": new_entry.get("semantic_type")})
        if old_entry.get("nullability") != new_entry.get("nullability"):
            nullability_changes.append({"column": column, "old": old_entry.get("nullability"), "new": new_entry.get("nullability")})

    severity = "WARNING"
    if type_changes or removed:
        severity = "CRITICAL"
    return {
        "severity": severity,
        "added": added,
        "removed": removed,
        "type_changes": type_changes,
        "nullability_changes": nullability_changes,
        "pass": not (added or removed or type_changes),
    }

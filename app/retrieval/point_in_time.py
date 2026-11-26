from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd


def _normalise_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True, errors="coerce")


def retrieve_point_in_time(events_df: pd.DataFrame, features_df: pd.DataFrame) -> pd.DataFrame:
    """Retrieve the latest feature row available at or before each event timestamp."""
    if events_df.empty:
        return pd.DataFrame(columns=["entity_id", "event_time", "feature_name", "feature_value", "source_version"])

    base = events_df.copy()
    base["event_time"] = _normalise_datetime(base["event_time"])
    features = features_df.copy()
    features["event_timestamp"] = _normalise_datetime(features["event_timestamp"])
    features["created_timestamp"] = _normalise_datetime(features["created_timestamp"])

    results: List[Dict[str, Any]] = []
    for _, event in base.iterrows():
        entity_id = str(event["entity_id"])
        event_time = event["event_time"]
        valid = features[
            (features["entity_id"].astype(str) == entity_id)
            & (features["event_timestamp"] <= event_time)
            & (features["created_timestamp"] <= event_time)
        ]
        if valid.empty:
            continue
        latest = valid.sort_values("event_timestamp").tail(1)
        for _, feature in latest.iterrows():
            results.append(
                {
                    "entity_id": entity_id,
                    "event_time": event_time,
                    "feature_name": feature.get("feature_name", "feature_value"),
                    "feature_value": feature.get("feature_value"),
                    "source_version": feature.get("source_version", "unknown"),
                    "partition_id": feature.get("partition_id", "default"),
                }
            )

    return pd.DataFrame(results)


def oracle_point_in_time(events_df: pd.DataFrame, features_df: pd.DataFrame) -> pd.DataFrame:
    """Independent oracle implementation used for validation and tests."""
    results: List[Dict[str, Any]] = []
    features = features_df.copy()
    features["event_timestamp"] = _normalise_datetime(features["event_timestamp"])
    features["created_timestamp"] = _normalise_datetime(features["created_timestamp"])
    for _, event in events_df.iterrows():
        candidate = None
        entity_id = str(event["entity_id"])
        event_time = pd.Timestamp(event["event_time"], tz="UTC") if isinstance(event["event_time"], str) else pd.Timestamp(event["event_time"])
        for _, feature in features.iterrows():
            if str(feature["entity_id"]) != entity_id:
                continue
            feature_time = feature["event_timestamp"]
            created_time = feature["created_timestamp"]
            if pd.isna(feature_time) or pd.isna(created_time):
                continue
            if feature_time <= event_time and created_time <= event_time:
                if candidate is None or feature_time > candidate["event_timestamp"]:
                    candidate = feature.to_dict()
        if candidate is not None:
            results.append(
                {
                    "entity_id": entity_id,
                    "event_time": event_time,
                    "feature_name": candidate.get("feature_name", "feature_value"),
                    "feature_value": candidate.get("feature_value"),
                    "source_version": candidate.get("source_version", "unknown"),
                }
            )
    return pd.DataFrame(results)


def detect_leakage(events_df: pd.DataFrame, features_df: pd.DataFrame) -> Dict[str, Any]:
    """Return a structured leakage report for future data, timestamp drift, and malformed inputs."""
    issues: List[Dict[str, Any]] = []

    events = events_df.copy()
    events["event_time"] = pd.to_datetime(events["event_time"], utc=True, errors="coerce")

    features = features_df.copy()
    features["event_timestamp"] = pd.to_datetime(features["event_timestamp"], utc=True, errors="coerce")
    features["created_timestamp"] = pd.to_datetime(features["created_timestamp"], utc=True, errors="coerce")

    for idx, row in features.iterrows():
        event_ts = row.get("event_timestamp")
        created_ts = row.get("created_timestamp")
        if pd.isna(event_ts):
            issues.append({"test_id": f"leakage-{idx}-missing-event", "kind": "missing_event_timestamp", "severity": "CRITICAL", "row": idx})
        if pd.isna(created_ts):
            issues.append({"test_id": f"leakage-{idx}-missing-created", "kind": "missing_created_timestamp", "severity": "CRITICAL", "row": idx})
        if not pd.isna(event_ts) and not pd.isna(created_ts) and created_ts > event_ts:
            issues.append({"test_id": f"leakage-{idx}-created-after-event", "kind": "created_after_event", "severity": "CRITICAL", "row": idx})

    for _, event in events.iterrows():
        entity = str(event["entity_id"])
        event_time = event["event_time"]
        for _, feature in features[features["entity_id"].astype(str) == entity].iterrows():
            if pd.isna(feature["event_timestamp"]):
                continue
            if feature["event_timestamp"] > event_time:
                issues.append({
                    "test_id": f"leakage-{entity}-{feature.name}",
                    "kind": "future_feature_timestamp",
                    "severity": "CRITICAL",
                    "row": int(feature.name),
                    "entity_id": entity,
                    "event_time": str(event_time),
                    "feature_time": str(feature["event_timestamp"]),
                })

    return {"issues": issues, "pass": not issues, "issue_count": len(issues)}

from __future__ import annotations

import pandas as pd

from app.retrieval.point_in_time import detect_leakage, oracle_point_in_time, retrieve_point_in_time


def test_point_in_time_retrieval() -> None:
    events = pd.DataFrame(
        {
            "entity_id": ["A", "A", "B"],
            "event_time": [
                pd.Timestamp("2024-01-01T00:00:00Z"),
                pd.Timestamp("2024-01-08T00:00:00Z"),
                pd.Timestamp("2024-01-05T00:00:00Z"),
            ],
        }
    )
    features = pd.DataFrame(
        {
            "entity_id": ["A", "A", "B"],
            "event_timestamp": [
                pd.Timestamp("2023-12-29T00:00:00Z"),
                pd.Timestamp("2024-01-07T00:00:00Z"),
                pd.Timestamp("2024-01-04T00:00:00Z"),
            ],
            "created_timestamp": [
                pd.Timestamp("2023-12-29T00:00:00Z"),
                pd.Timestamp("2024-01-07T00:00:00Z"),
                pd.Timestamp("2024-01-04T00:00:00Z"),
            ],
            "feature_name": ["score", "score", "score"],
            "feature_value": [10, 20, 30],
            "source_version": ["v1", "v2", "v1"],
        }
    )

    result = retrieve_point_in_time(events, features)
    assert result["feature_value"].tolist() == [10, 20, 30]
    assert len(oracle_point_in_time(events, features)) == len(result)


def test_leakage_and_schema_inference() -> None:
    events = pd.DataFrame({"entity_id": ["A"], "event_time": [pd.Timestamp("2024-01-01T00:00:00Z")]})
    features = pd.DataFrame(
        {
            "entity_id": ["A"],
            "event_timestamp": [pd.Timestamp("2024-01-02T00:00:00Z")],
            "created_timestamp": [pd.Timestamp("2024-01-03T00:00:00Z")],
            "feature_name": ["score"],
            "feature_value": [999],
            "source_version": ["v3"],
        }
    )
    issues = detect_leakage(events, features)
    assert issues["pass"] is False
    assert issues["issue_count"] > 0

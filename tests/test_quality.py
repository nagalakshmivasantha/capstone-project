from __future__ import annotations

import pandas as pd

from app.quality.inference import infer_schema
from app.quality.profiling import profile_dataset
from app.quality.rules import assess_ml_safety, evaluate_quality_rules


def test_schema_inference_labels_entity_and_timestamp() -> None:
    df = pd.DataFrame(
        {
            "user_id": ["u1", "u2", "u3"],
            "event_time": [
                pd.Timestamp("2024-01-01T00:00:00Z"),
                pd.Timestamp("2024-01-02T00:00:00Z"),
                pd.Timestamp("2024-01-03T00:00:00Z"),
            ],
            "feature_value": [10.2, 11.8, 12.0],
        }
    )
    inferred = infer_schema(df)
    types = {entry["column"]: entry["semantic_type"] for entry in inferred["columns"]}
    assert types["user_id"] == "entity_id"
    assert types["event_time"] == "timestamp"
    assert types["feature_value"] in {"numeric", "feature_value"}


def test_quality_profile_score_is_reasonable() -> None:
    df = pd.DataFrame(
        {
            "entity_id": ["u1", "u2", "u3"],
            "event_time": [
                pd.Timestamp("2024-01-01T00:00:00Z"),
                pd.Timestamp("2024-01-02T00:00:00Z"),
                pd.Timestamp("2024-01-03T00:00:00Z"),
            ],
            "feature_value": [1.0, 2.0, 3.0],
        }
    )
    profile = profile_dataset(df)
    assert profile["rows"] == 3
    assert profile["quality_score"] > 80


def test_ml_safety_recommends_segment_median_for_segmented_missingness() -> None:
    df = pd.DataFrame(
        {
            "segment": ["a", "a", "a", "b", "b", "b", "b", "b", "b", "b"],
            "income": [10.0, None, 12.0, 100.0, 110.0, None, None, None, None, None],
        }
    )
    schema = infer_schema(df)
    profile = profile_dataset(df)
    rules = evaluate_quality_rules(df, schema)
    assessment = assess_ml_safety(df, profile, rules)

    assert assessment["decision"] == "BLOCK_PENDING_REPAIR"
    issue = next(item for item in assessment["issues"] if item["column"] == "income")
    assert issue["recommended"] == "Segment-level median"
    assert "Missingness correlated with segment" in issue["characteristics"]

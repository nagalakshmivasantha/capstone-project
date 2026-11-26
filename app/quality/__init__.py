from __future__ import annotations

import pandas as pd

from app.quality.inference import infer_schema
from app.quality.profiling import profile_dataset
from app.retrieval.point_in_time import detect_leakage, oracle_point_in_time, retrieve_point_in_time


def make_demo_dataset() -> tuple[pd.DataFrame, pd.DataFrame]:
    events = pd.DataFrame(
        {
            "entity_id": ["A", "A", "B"],
            "event_time": [
                pd.Timestamp("2024-01-01 00:00:00", tz="UTC"),
                pd.Timestamp("2024-01-08 00:00:00", tz="UTC"),
                pd.Timestamp("2024-01-05 00:00:00", tz="UTC"),
            ],
        }
    )
    features = pd.DataFrame(
        {
            "entity_id": ["A", "A", "B"],
            "event_timestamp": [
                pd.Timestamp("2023-12-29 00:00:00", tz="UTC"),
                pd.Timestamp("2024-01-07 00:00:00", tz="UTC"),
                pd.Timestamp("2024-01-04 00:00:00", tz="UTC"),
            ],
            "created_timestamp": [
                pd.Timestamp("2023-12-29 00:00:00", tz="UTC"),
                pd.Timestamp("2024-01-07 00:00:00", tz="UTC"),
                pd.Timestamp("2024-01-04 00:00:00", tz="UTC"),
            ],
            "feature_name": ["score", "score", "score"],
            "feature_value": [10, 20, 30],
            "source_version": ["v1", "v2", "v1"],
        }
    )
    return events, features


def run_demo_validation() -> dict:
    events, features = make_demo_dataset()
    return {
        "schema": infer_schema(events),
        "profile": profile_dataset(features),
        "leakage": detect_leakage(events, features),
        "retrieval": retrieve_point_in_time(events, features).to_dict(orient="records"),
        "oracle": oracle_point_in_time(events, features).to_dict(orient="records"),
    }

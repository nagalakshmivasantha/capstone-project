from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def generate_parquet_fixtures() -> dict:
    events = pd.read_csv(ROOT / "tests" / "fixtures" / "events.csv")
    features = pd.read_csv(ROOT / "tests" / "fixtures" / "features.csv")

    events_path = ROOT / "tests" / "fixtures" / "events.parquet"
    features_path = ROOT / "tests" / "fixtures" / "features.parquet"
    events.to_parquet(events_path, index=False)
    features.to_parquet(features_path, index=False)

    partitioned_events = ROOT / "tests" / "fixtures" / "partitioned" / "events" / "2024" / "01"
    partitioned_features = ROOT / "tests" / "fixtures" / "partitioned" / "features" / "2024" / "01"
    partitioned_events.mkdir(parents=True, exist_ok=True)
    partitioned_features.mkdir(parents=True, exist_ok=True)

    events.to_parquet(partitioned_events / "events_snapshot.parquet", index=False)
    features.to_parquet(partitioned_features / "features_snapshot.parquet", index=False)

    return {
        "events": str(events_path),
        "features": str(features_path),
        "partitioned_events": str(partitioned_events / "events_snapshot.parquet"),
        "partitioned_features": str(partitioned_features / "features_snapshot.parquet"),
    }


if __name__ == "__main__":
    print(json.dumps(generate_parquet_fixtures(), indent=2))

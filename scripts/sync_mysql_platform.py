from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

from app.gateways import DataQualityGateway


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=False)


def main() -> None:
    connection = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "capstone"),
        connection_timeout=int(os.getenv("MYSQL_CONNECTION_TIMEOUT", "3")),
    )
    gateway = DataQualityGateway()
    cursor = connection.cursor()
    datasets = [
        ("events", ROOT / "tests" / "fixtures" / "events.csv"),
        ("features", ROOT / "tests" / "fixtures" / "features.csv"),
    ]
    for dataset_id, path in datasets:
        result = gateway.register_dataset(str(path), dataset_id)
        cursor.execute(
            """
            INSERT INTO platform_datasets(dataset_id, dataset_path, dataset_format, row_count, registered_at)
            VALUES (%s, %s, %s, %s, UTC_TIMESTAMP())
            ON DUPLICATE KEY UPDATE
              dataset_path=VALUES(dataset_path),
              dataset_format=VALUES(dataset_format),
              row_count=VALUES(row_count),
              registered_at=VALUES(registered_at)
            """,
            (dataset_id, str(path), "csv", result["rows"]),
        )
        validation = gateway.validate_dataset(str(path))
        profile = validation["quality"]
        cursor.execute(
            """
            INSERT INTO quality_runs(run_id, dataset_id, status, quality_score, result_json)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                f"run-{uuid.uuid4().hex[:12]}",
                dataset_id,
                validation["status"],
                profile["quality_score"],
                json.dumps(validation, default=str),
            ),
        )
    connection.commit()
    cursor.execute("SELECT COUNT(*) FROM platform_datasets")
    datasets_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM quality_runs")
    runs_count = cursor.fetchone()[0]
    cursor.close()
    connection.close()
    print(f"platform_datasets={datasets_count}")
    print(f"quality_runs={runs_count}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
import os
import uuid
from typing import Any

import mysql.connector
from mysql.connector import Error


def mysql_config() -> dict[str, Any]:
    return {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DATABASE", "capstone"),
        "connection_timeout": int(os.getenv("MYSQL_CONNECTION_TIMEOUT", "3")),
    }


def database_health() -> dict[str, Any]:
    connection = None
    try:
        connection = mysql.connector.connect(**mysql_config())
        cursor = connection.cursor()
        cursor.execute("SELECT DATABASE(), VERSION()")
        database, version = cursor.fetchone()
        return {
            "status": "connected",
            "database": database,
            "server_version": version,
        }
    except Error as error:
        return {
            "status": "unavailable",
            "database": mysql_config()["database"],
            "error": str(error),
        }
    finally:
        if connection is not None and connection.is_connected():
            connection.close()


def list_tables() -> dict[str, Any]:
    connection = None
    try:
        connection = mysql.connector.connect(**mysql_config())
        cursor = connection.cursor()
        cursor.execute("SHOW TABLES")
        return {"status": "connected", "tables": [row[0] for row in cursor.fetchall()]}
    except Error as error:
        return {"status": "unavailable", "error": str(error)}
    finally:
        if connection is not None and connection.is_connected():
            connection.close()


def database_snapshot() -> dict[str, Any]:
    connection = None
    try:
        connection = mysql.connector.connect(**mysql_config())
        cursor = connection.cursor()
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        counts: dict[str, int] = {}
        for table in tables:
            if table.replace("_", "").isalnum():
                cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                counts[table] = int(cursor.fetchone()[0])
        return {
            "status": "connected",
            "database": mysql_config()["database"],
            "tables": tables,
            "row_counts": counts,
        }
    except Error as error:
        return {"status": "unavailable", "database": mysql_config()["database"], "error": str(error)}
    finally:
        if connection is not None and connection.is_connected():
            connection.close()


def persist_dashboard_registration(
    registration: dict[str, Any],
    quality_result: dict[str, Any],
    actor: str,
) -> dict[str, Any]:
    connection = None
    try:
        connection = mysql.connector.connect(**mysql_config())
        cursor = connection.cursor()
        dataset_id = registration["dataset_id"]
        cursor.execute(
            """
            INSERT INTO platform_datasets
              (dataset_id, dataset_path, dataset_format, row_count, registered_at)
            VALUES (%s, %s, %s, %s, UTC_TIMESTAMP())
            ON DUPLICATE KEY UPDATE
              dataset_path=VALUES(dataset_path),
              dataset_format=VALUES(dataset_format),
              row_count=VALUES(row_count),
              registered_at=UTC_TIMESTAMP()
            """,
            (
                dataset_id,
                quality_result["dataset"],
                registration["format"],
                registration["rows"],
            ),
        )
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        cursor.execute(
            """
            INSERT INTO quality_runs
              (run_id, dataset_id, status, quality_score, result_json)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                run_id,
                dataset_id,
                quality_result["status"],
                quality_result["quality"]["quality_score"],
                json.dumps(quality_result, default=str),
            ),
        )
        cursor.execute(
            """
            INSERT INTO audit_events (event_type, actor, payload_json)
            VALUES (%s, %s, %s)
            """,
            (
                "dashboard_dataset_registered",
                actor,
                json.dumps({"dataset_id": dataset_id, "run_id": run_id}),
            ),
        )
        connection.commit()
        return {"dataset_id": dataset_id, "run_id": run_id, "status": "persisted"}
    except Error:
        if connection is not None:
            connection.rollback()
        raise
    finally:
        if connection is not None and connection.is_connected():
            connection.close()

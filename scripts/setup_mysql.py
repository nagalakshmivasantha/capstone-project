from __future__ import annotations

import csv
import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=False)


def config(include_database: bool = True) -> dict:
    values = {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "connection_timeout": int(os.getenv("MYSQL_CONNECTION_TIMEOUT", "3")),
    }
    if include_database:
        values["database"] = os.getenv("MYSQL_DATABASE", "capstone")
    return values


def identifier(value: str) -> str:
    if not value or not value.replace("_", "").isalnum():
        raise ValueError("MYSQL_DATABASE must be a simple database identifier")
    return value


def read_rows(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        return columns, [[row.get(column, "") for column in columns] for row in reader]


def create_tables(connection: mysql.connector.MySQLConnection, database: str) -> None:
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS platform_datasets (
            dataset_id VARCHAR(255) PRIMARY KEY,
            dataset_path TEXT NOT NULL,
            dataset_format VARCHAR(32) NOT NULL,
            row_count BIGINT NOT NULL,
            registered_at TIMESTAMP NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS quality_runs (
            run_id VARCHAR(64) PRIMARY KEY,
            dataset_id VARCHAR(255) NOT NULL,
            status VARCHAR(32) NOT NULL,
            quality_score DECIMAL(8, 3) NULL,
            result_json JSON NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_events (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            event_type VARCHAR(128) NOT NULL,
            actor VARCHAR(255) NOT NULL,
            payload_json JSON NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS job_runs (
            job_id VARCHAR(64) PRIMARY KEY,
            job_type VARCHAR(128) NOT NULL,
            status VARCHAR(32) NOT NULL,
            attempts INT NOT NULL,
            payload_json JSON NOT NULL,
            result_json JSON NULL,
            error_text TEXT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
        """
    )
    connection.commit()
    cursor.close()


def replace_fixture_table(connection: mysql.connector.MySQLConnection, table: str, path: Path) -> int:
    columns, rows = read_rows(path)
    if not columns:
        raise ValueError(f"Fixture has no columns: {path}")
    safe_columns = [identifier(column) for column in columns]
    definitions = ", ".join(f"`{column}` TEXT NULL" for column in safe_columns)
    cursor = connection.cursor()
    cursor.execute(f"CREATE TABLE IF NOT EXISTS `{table}` ({definitions})")
    cursor.execute(f"TRUNCATE TABLE `{table}`")
    placeholders = ", ".join(["%s"] * len(columns))
    column_sql = ", ".join(f"`{column}`" for column in safe_columns)
    cursor.executemany(
        f"INSERT INTO `{table}` ({column_sql}) VALUES ({placeholders})",
        rows,
    )
    connection.commit()
    cursor.close()
    return len(rows)


def main() -> None:
    database = identifier(os.getenv("MYSQL_DATABASE", "capstone"))
    server = mysql.connector.connect(**config(include_database=False))
    server_cursor = server.cursor()
    server_cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database}`")
    server.commit()
    server_cursor.close()
    server.close()

    connection = mysql.connector.connect(**config())
    create_tables(connection, database)
    events_count = replace_fixture_table(connection, "events", ROOT / "tests" / "fixtures" / "events.csv")
    features_count = replace_fixture_table(connection, "features", ROOT / "tests" / "fixtures" / "features.csv")
    cursor = connection.cursor()
    cursor.execute("SHOW TABLES")
    tables = sorted(row[0] for row in cursor.fetchall())
    cursor.close()
    connection.close()

    print(f"database={database}")
    print(f"events_rows={events_count}")
    print(f"features_rows={features_count}")
    print(f"tables={','.join(tables)}")


if __name__ == "__main__":
    main()

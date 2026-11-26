from typing import Any

from app.platform import mysql


class FakeCursor:
    def __init__(self) -> None:
        self.statements: list[tuple[str, Any]] = []

    def execute(self, statement: str, parameters: Any = None) -> None:
        self.statements.append((statement, parameters))

    def close(self) -> None:
        pass


class FakeConnection:
    def __init__(self) -> None:
        self.cursor_instance = FakeCursor()
        self.committed = False
        self.rolled_back = False

    def cursor(self) -> FakeCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def is_connected(self) -> bool:
        return True

    def close(self) -> None:
        pass


def test_persist_dashboard_registration_commits_mysql_records(monkeypatch) -> None:
    connection = FakeConnection()
    monkeypatch.setattr(mysql.mysql.connector, "connect", lambda **kwargs: connection)

    result = mysql.persist_dashboard_registration(
        {
            "dataset_id": "new-features",
            "format": "csv",
            "rows": 4,
        },
        {
            "dataset": "C:\\data\\new-features.csv",
            "status": "accept",
            "quality": {"quality_score": 97.5},
        },
        "dashboard",
    )

    assert result["dataset_id"] == "new-features"
    assert result["status"] == "persisted"
    assert connection.committed is True
    assert connection.rolled_back is False
    assert len(connection.cursor_instance.statements) == 3

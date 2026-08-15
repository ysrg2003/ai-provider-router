import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence


class RouterStore:
    """Persistent state for project-aware key rotation and cooldowns."""

    def __init__(self, path: str | Path = "data/ai_router.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    @staticmethod
    def _create_provider_state(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS provider_state (
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                key_id TEXT NOT NULL,
                project TEXT NOT NULL,
                consecutive_failures INTEGER NOT NULL DEFAULT 0,
                total_calls INTEGER NOT NULL DEFAULT 0,
                total_successes INTEGER NOT NULL DEFAULT 0,
                cooldown_until TEXT,
                last_error TEXT,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (provider, model, key_id, project)
            )
            """
        )

    def _migrate_provider_state_if_needed(self, connection: sqlite3.Connection) -> None:
        row = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'provider_state'"
        ).fetchone()
        if not row:
            self._create_provider_state(connection)
            return
        columns = connection.execute("PRAGMA table_info(provider_state)").fetchall()
        primary_key_columns = {str(column[1]) for column in columns if int(column[5]) > 0}
        expected = {"provider", "model", "key_id", "project"}
        if primary_key_columns == expected:
            return
        connection.execute("ALTER TABLE provider_state RENAME TO provider_state_legacy")
        self._create_provider_state(connection)
        connection.execute(
            """
            INSERT OR IGNORE INTO provider_state
                (provider, model, key_id, project, consecutive_failures,
                 total_calls, total_successes, cooldown_until, last_error, updated_at)
            SELECT provider, model, key_id, COALESCE(project, 'default'),
                   consecutive_failures, total_calls, total_successes,
                   cooldown_until, last_error, updated_at
            FROM provider_state_legacy
            """
        )
        connection.execute("DROP TABLE provider_state_legacy")

    def _init_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS provider_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    key_id TEXT NOT NULL,
                    project TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_class TEXT,
                    error_message TEXT,
                    status_code INTEGER,
                    usage_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS provider_calls_created_idx ON provider_calls (created_at DESC);
                CREATE TABLE IF NOT EXISTS rotation_state (
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    next_project_index INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (provider, model)
                );
                """
            )
            self._migrate_provider_state_if_needed(connection)

    def get_state(self, provider: str, model: str, key_id: str, project: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT provider, model, key_id, project, consecutive_failures, total_calls, total_successes, cooldown_until, last_error, updated_at FROM provider_state WHERE provider = ? AND model = ? AND key_id = ? AND project = ?",
                (provider, model, key_id, project),
            ).fetchone()
        return dict(row) if row else None

    def is_cooling(self, provider: str, model: str, key_id: str, project: str) -> bool:
        state = self.get_state(provider, model, key_id, project)
        if not state or not state.get("cooldown_until"):
            return False
        try:
            return datetime.fromisoformat(state["cooldown_until"]) > datetime.now(timezone.utc)
        except ValueError:
            return False

    def reserve_project_order(self, provider: str, model: str, projects: Sequence[str]) -> list[str]:
        """Return projects in round-robin order and persist the next cursor atomically."""
        unique_projects = list(dict.fromkeys(str(project or "default") for project in projects))
        if not unique_projects:
            return []
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT next_project_index FROM rotation_state WHERE provider = ? AND model = ?",
                (provider, model),
            ).fetchone()
            start = int(row[0]) % len(unique_projects) if row else 0
            ordered = unique_projects[start:] + unique_projects[:start]
            next_index = (start + 1) % len(unique_projects)
            connection.execute(
                """
                INSERT INTO rotation_state (provider, model, next_project_index, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(provider, model) DO UPDATE SET
                    next_project_index = excluded.next_project_index,
                    updated_at = excluded.updated_at
                """,
                (provider, model, next_index, now),
            )
        return ordered

    def record_success(self, *, provider: str, model: str, key_id: str, project: str, operation: str, usage: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO provider_calls (provider, model, key_id, project, operation, status, usage_json, created_at) VALUES (?, ?, ?, ?, ?, 'success', ?, ?)",
                (provider, model, key_id, project, operation, json.dumps(usage, ensure_ascii=False), now),
            )
            connection.execute(
                """
                INSERT INTO provider_state (provider, model, key_id, project, consecutive_failures, total_calls, total_successes, cooldown_until, last_error, updated_at)
                VALUES (?, ?, ?, ?, 0, 1, 1, NULL, NULL, ?)
                ON CONFLICT(provider, model, key_id, project) DO UPDATE SET
                    consecutive_failures = 0,
                    total_calls = provider_state.total_calls + 1,
                    total_successes = provider_state.total_successes + 1,
                    cooldown_until = NULL,
                    last_error = NULL,
                    updated_at = excluded.updated_at
                """,
                (provider, model, key_id, project, now),
            )

    def record_failure(self, *, provider: str, model: str, key_id: str, project: str, operation: str, error_class: str, message: str, status_code: int | None, cooldown_seconds: int) -> None:
        now = datetime.now(timezone.utc)
        cooldown_until = (now + timedelta(seconds=max(0, cooldown_seconds))).isoformat() if cooldown_seconds else None
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO provider_calls (provider, model, key_id, project, operation, status, error_class, error_message, status_code, created_at) VALUES (?, ?, ?, ?, ?, 'failed', ?, ?, ?, ?)",
                (provider, model, key_id, project, operation, error_class, message[:2000], status_code, now.isoformat()),
            )
            connection.execute(
                """
                INSERT INTO provider_state (provider, model, key_id, project, consecutive_failures, total_calls, total_successes, cooldown_until, last_error, updated_at)
                VALUES (?, ?, ?, ?, 1, 1, 0, ?, ?, ?)
                ON CONFLICT(provider, model, key_id, project) DO UPDATE SET
                    consecutive_failures = provider_state.consecutive_failures + 1,
                    total_calls = provider_state.total_calls + 1,
                    cooldown_until = excluded.cooldown_until,
                    last_error = excluded.last_error,
                    updated_at = excluded.updated_at
                """,
                (provider, model, key_id, project, cooldown_until, message[:2000], now.isoformat()),
            )

    def stats(self) -> dict[str, int]:
        with self._connect() as connection:
            calls = connection.execute("SELECT COUNT(*) FROM provider_calls").fetchone()[0]
            states = connection.execute("SELECT COUNT(*) FROM provider_state").fetchone()[0]
            projects = connection.execute("SELECT COUNT(DISTINCT project) FROM provider_state").fetchone()[0]
        return {"calls": calls, "provider_states": states, "projects": projects}

    def checkpoint(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")

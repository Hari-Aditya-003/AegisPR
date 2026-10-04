from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

from app.schemas.verification import VerificationRun


class VerificationStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.lock = threading.RLock()
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS verification_runs (id TEXT PRIMARY KEY, payload TEXT NOT NULL, updated_at TEXT NOT NULL)"
            )

    def save(self, run: VerificationRun) -> None:
        payload = run.model_dump_json()
        with self.lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO verification_runs(id, payload, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
                "ON CONFLICT(id) DO UPDATE SET payload=excluded.payload, updated_at=CURRENT_TIMESTAMP",
                (run.id, payload),
            )

    def get(self, run_id: str) -> VerificationRun | None:
        with self.lock, self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM verification_runs WHERE id = ?", (run_id,)
            ).fetchone()
        return VerificationRun.model_validate(json.loads(row[0])) if row else None

    def list(self, limit: int = 20) -> list[VerificationRun]:
        with self.lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM verification_runs ORDER BY updated_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [VerificationRun.model_validate(json.loads(row[0])) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=10)


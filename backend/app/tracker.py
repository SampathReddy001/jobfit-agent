"""SQLite-backed job application tracker."""

from __future__ import annotations

import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

STATUSES = ("interested", "applied", "interviewing", "offer", "rejected")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS applications (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    company      TEXT NOT NULL,
    role         TEXT NOT NULL,
    job_url      TEXT,
    fit_score    INTEGER,
    status       TEXT NOT NULL DEFAULT 'interested',
    notes        TEXT,
    cover_letter TEXT,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Tracker:
    def __init__(self, path: str):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(_SCHEMA)

    def _row(self, app_id: int) -> dict[str, Any] | None:
        row = self._conn.execute("SELECT * FROM applications WHERE id = ?", (app_id,)).fetchone()
        return dict(row) if row else None

    def add(
        self,
        company: str,
        role: str,
        job_url: str | None = None,
        fit_score: int | None = None,
        status: str = "interested",
        notes: str | None = None,
    ) -> dict[str, Any]:
        status = status.lower()
        if status not in STATUSES:
            raise ValueError(f"status must be one of {', '.join(STATUSES)}")
        now = _now()
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO applications (company, role, job_url, fit_score, status, notes, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (company.strip(), role.strip(), job_url, fit_score, status, notes, now, now),
            )
            self._conn.commit()
            return self._row(cur.lastrowid)  # type: ignore[return-value]

    def list(self, status: str | None = None) -> list[dict[str, Any]]:
        query, args = "SELECT * FROM applications", ()
        if status:
            query, args = query + " WHERE status = ?", (status.lower(),)
        rows = self._conn.execute(query + " ORDER BY updated_at DESC, id DESC", args).fetchall()
        return [dict(r) for r in rows]

    def get(self, app_id: int) -> dict[str, Any] | None:
        return self._row(app_id)

    def update(self, app_id: int, **fields: Any) -> dict[str, Any]:
        allowed = {"status", "notes", "cover_letter", "fit_score"}
        fields = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if "status" in fields:
            fields["status"] = str(fields["status"]).lower()
            if fields["status"] not in STATUSES:
                raise ValueError(f"status must be one of {', '.join(STATUSES)}")
        if self._row(app_id) is None:
            raise KeyError(f"No application with id {app_id}")
        if fields:
            assignments = ", ".join(f"{k} = ?" for k in fields)
            with self._lock:
                self._conn.execute(
                    f"UPDATE applications SET {assignments}, updated_at = ? WHERE id = ?",
                    (*fields.values(), _now(), app_id),
                )
                self._conn.commit()
        return self._row(app_id)  # type: ignore[return-value]

    def delete(self, app_id: int) -> bool:
        with self._lock:
            cur = self._conn.execute("DELETE FROM applications WHERE id = ?", (app_id,))
            self._conn.commit()
            return cur.rowcount > 0

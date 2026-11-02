from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def job_key(job: Mapping[str, Any]) -> str:
    adzuna_id = str(job.get("id") or "").strip()
    if adzuna_id:
        return f"adzuna:{adzuna_id}"
    url = str(job.get("url") or "").strip()
    if url:
        return f"url:{url}"
    company = str(job.get("company") or "").strip().lower()
    title = str(job.get("title") or "").strip().lower()
    location = str(job.get("location") or "").strip().lower()
    return f"tuple:{company}|{title}|{location}"


class SeenStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen (
                job_key TEXT PRIMARY KEY,
                adzuna_id TEXT,
                url TEXT,
                title TEXT,
                company TEXT,
                first_seen_at TEXT NOT NULL,
                alerted_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def is_seen(self, job: Mapping[str, Any]) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM seen WHERE job_key = ?", (job_key(job),)
        ).fetchone()
        return row is not None

    def unseen(self, jobs: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
        return [job for job in jobs if not self.is_seen(job)]

    def mark_alerted(self, jobs: Iterable[Mapping[str, Any]]) -> None:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        rows = [
            (
                job_key(job),
                str(job.get("id") or ""),
                str(job.get("url") or ""),
                str(job.get("title") or ""),
                str(job.get("company") or ""),
                now,
                now,
            )
            for job in jobs
        ]
        self._conn.executemany(
            """
            INSERT OR IGNORE INTO seen (
                job_key, adzuna_id, url, title, company, first_seen_at, alerted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self._conn.commit()

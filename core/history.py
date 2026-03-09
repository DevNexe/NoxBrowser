"""
core/history.py — История навигации (SQLite)
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

_SKIP_URLS = {
    "about:blank", "about:newtab", "", "nox://newtab/", "nox://newtab",
    "nox://history/", "nox://history", "nox://bookmarks/", "nox://bookmarks",
    "nox://downloads/", "nox://downloads",
}


@dataclass
class HistoryEntry:
    url: str
    title: str
    visited_at: str


def _db_path() -> Path:
    return Path(os.environ.get("APPDATA", Path.home())) / "NoxBrowser" / "nox.db"


class HistoryManager:
    MAX_ENTRIES: int = 10_000

    def __init__(self) -> None:
        self._path = _db_path()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._con = sqlite3.connect(str(self._path), check_same_thread=False)
        self._con.row_factory = sqlite3.Row
        self._migrate()

    def _migrate(self) -> None:
        self._con.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                url        TEXT NOT NULL,
                title      TEXT NOT NULL DEFAULT '',
                visited_at TEXT NOT NULL
            )
        """)
        self._con.execute("CREATE INDEX IF NOT EXISTS idx_history_visited ON history(visited_at)")
        self._con.commit()

    def add(self, url: str, title: str = "") -> None:
        url = (url or "").strip()
        if not url:
            return
        if url in _SKIP_URLS:
            return
        if url.startswith("data:"):
            return
        if url.startswith("nox://"):
            return
        self._con.execute(
            "INSERT INTO history (url, title, visited_at) VALUES (?, ?, ?)",
            (url, title or url, datetime.now().isoformat()),
        )
        self._con.commit()
        self._trim()

    def search(self, query: str, limit: int = 50) -> list[HistoryEntry]:
        q = f"%{query.lower()}%"
        rows = self._con.execute(
            "SELECT url, title, visited_at FROM history "
            "WHERE lower(url) LIKE ? OR lower(title) LIKE ? "
            "ORDER BY visited_at DESC LIMIT ?",
            (q, q, limit),
        ).fetchall()
        return [HistoryEntry(**dict(r)) for r in rows]

    def get_recent(self, limit: int = 100) -> list[HistoryEntry]:
        rows = self._con.execute(
            "SELECT url, title, visited_at FROM history ORDER BY visited_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [HistoryEntry(**dict(r)) for r in rows]

    def delete_by_url(self, url: str) -> None:
        self._con.execute("DELETE FROM history WHERE url = ?", (url,))
        self._con.commit()

    def clear(self) -> None:
        self._con.execute("DELETE FROM history")
        self._con.commit()

    def __len__(self) -> int:
        return self._con.execute("SELECT COUNT(*) FROM history").fetchone()[0]

    def _trim(self) -> None:
        count = len(self)
        if count > self.MAX_ENTRIES:
            self._con.execute("""
                DELETE FROM history WHERE id IN (
                    SELECT id FROM history ORDER BY visited_at ASC LIMIT ?
                )
            """, (count - self.MAX_ENTRIES,))
            self._con.commit()
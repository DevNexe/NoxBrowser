"""
core/bookmarks.py — Менеджер закладок (SQLite)
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class Bookmark:
    url: str
    title: str
    folder: str
    created_at: str


def _db_path() -> Path:
    return Path(os.environ.get("APPDATA", Path.home())) / "NoxBrowser" / "nox.db"


class BookmarkManager:
    def __init__(self) -> None:
        self._path = _db_path()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._con = sqlite3.connect(str(self._path), check_same_thread=False)
        self._con.row_factory = sqlite3.Row
        self._migrate()

    def _migrate(self) -> None:
        self._con.execute("""
            CREATE TABLE IF NOT EXISTS bookmarks (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                url        TEXT NOT NULL UNIQUE,
                title      TEXT NOT NULL DEFAULT '',
                folder     TEXT NOT NULL DEFAULT 'Без папки',
                created_at TEXT NOT NULL
            )
        """)
        self._con.commit()

    def add(self, url: str, title: str, folder: str = "Без папки") -> Bookmark:
        self._con.execute(
            "INSERT OR REPLACE INTO bookmarks (url, title, folder, created_at) VALUES (?, ?, ?, ?)",
            (url, title, folder, datetime.now().isoformat()),
        )
        self._con.commit()
        return Bookmark(url=url, title=title, folder=folder, created_at=datetime.now().isoformat())

    def remove(self, url: str) -> bool:
        cur = self._con.execute("DELETE FROM bookmarks WHERE url = ?", (url,))
        self._con.commit()
        return cur.rowcount > 0

    def is_bookmarked(self, url: str) -> bool:
        row = self._con.execute("SELECT 1 FROM bookmarks WHERE url = ?", (url,)).fetchone()
        return row is not None

    def get_all(self) -> list[Bookmark]:
        rows = self._con.execute(
            "SELECT url, title, folder, created_at FROM bookmarks ORDER BY created_at DESC"
        ).fetchall()
        return [Bookmark(**dict(r)) for r in rows]

    def search(self, query: str) -> list[Bookmark]:
        q = f"%{query.lower()}%"
        rows = self._con.execute(
            "SELECT url, title, folder, created_at FROM bookmarks WHERE lower(url) LIKE ? OR lower(title) LIKE ? ORDER BY created_at DESC",
            (q, q),
        ).fetchall()
        return [Bookmark(**dict(r)) for r in rows]

    def __len__(self) -> int:
        return self._con.execute("SELECT COUNT(*) FROM bookmarks").fetchone()[0]
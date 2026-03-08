"""
core/history.py — История навигации
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Iterator


@dataclass
class HistoryEntry:
    url: str
    title: str
    visited_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "HistoryEntry":
        return cls(**data)


class HistoryManager:
    MAX_ENTRIES: int = 10_000

    def __init__(self, storage_dir: str | None = None) -> None:
        self._entries: list[HistoryEntry] = []
        self._storage_path = self._resolve_path(storage_dir)
        self._load()

    def add(self, url: str, title: str = "") -> None:
        if not url or url in ("about:blank", ""):
            return
        self._entries.append(HistoryEntry(url=url, title=title or url))
        if len(self._entries) > self.MAX_ENTRIES:
            self._entries = self._entries[-self.MAX_ENTRIES:]
        self._save()

    def search(self, query: str, limit: int = 50) -> list[HistoryEntry]:
        q = query.lower()
        return [e for e in reversed(self._entries)
                if q in e.url.lower() or q in e.title.lower()][:limit]

    def get_recent(self, limit: int = 100) -> list[HistoryEntry]:
        return list(reversed(self._entries[-limit:]))

    def clear(self) -> None:
        self._entries.clear()
        self._save()

    def __iter__(self) -> Iterator[HistoryEntry]:
        return iter(reversed(self._entries))

    def __len__(self) -> int:
        return len(self._entries)

    def _load(self) -> None:
        if not self._storage_path.exists():
            return
        try:
            data = json.loads(self._storage_path.read_text(encoding="utf-8"))
            self._entries = [HistoryEntry.from_dict(e) for e in data]
        except Exception:
            self._entries = []

    def _save(self) -> None:
        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            self._storage_path.write_text(
                json.dumps([e.to_dict() for e in self._entries], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass

    @staticmethod
    def _resolve_path(storage_dir: str | None) -> Path:
        if storage_dir:
            return Path(storage_dir) / "history.json"
        return Path.home() / ".nox_browser" / "history.json"

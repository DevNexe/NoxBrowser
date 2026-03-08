"""
core/bookmarks.py — Менеджер закладок
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Iterator


@dataclass
class Bookmark:
    url: str
    title: str
    folder: str = "Без папки"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Bookmark":
        return cls(**data)


class BookmarkManager:
    def __init__(self, storage_dir: str | None = None) -> None:
        self._bookmarks: list[Bookmark] = []
        self._storage_path = self._resolve_path(storage_dir)
        self._load()

    def add(self, url: str, title: str, folder: str = "Без папки") -> Bookmark:
        bm = Bookmark(url=url, title=title, folder=folder)
        self._bookmarks.append(bm)
        self._save()
        return bm

    def remove(self, url: str) -> bool:
        before = len(self._bookmarks)
        self._bookmarks = [b for b in self._bookmarks if b.url != url]
        if len(self._bookmarks) < before:
            self._save()
            return True
        return False

    def is_bookmarked(self, url: str) -> bool:
        return any(b.url == url for b in self._bookmarks)

    def get_all(self) -> list[Bookmark]:
        return list(self._bookmarks)

    def search(self, query: str) -> list[Bookmark]:
        q = query.lower()
        return [b for b in self._bookmarks if q in b.url.lower() or q in b.title.lower()]

    def __iter__(self) -> Iterator[Bookmark]:
        return iter(self._bookmarks)

    def __len__(self) -> int:
        return len(self._bookmarks)

    def _load(self) -> None:
        if not self._storage_path.exists():
            return
        try:
            data = json.loads(self._storage_path.read_text(encoding="utf-8"))
            self._bookmarks = [Bookmark.from_dict(b) for b in data]
        except Exception:
            pass

    def _save(self) -> None:
        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            self._storage_path.write_text(
                json.dumps([b.to_dict() for b in self._bookmarks], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass

    @staticmethod
    def _resolve_path(storage_dir: str | None) -> Path:
        if storage_dir:
            return Path(storage_dir) / "bookmarks.json"
        return Path.home() / ".nox_browser" / "bookmarks.json"

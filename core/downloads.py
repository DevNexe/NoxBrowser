"""
core/downloads.py — система загрузок (SQLite)
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List

from core.profile import get_profile
from PySide6.QtCore import QObject, Signal, QUrl, QStandardPaths
from PySide6.QtWidgets import QFileDialog
from PySide6.QtWebEngineCore import QWebEngineDownloadRequest


@dataclass
class DownloadEntry:
    url: str
    path: str
    status: str = "in-progress"
    progress: int = 0
    bytesReceived: int = 0
    bytesTotal: int = 0
    id: int = -1


def _db_path() -> Path:
    return Path(os.environ.get("APPDATA", Path.home())) / "NoxBrowser" / "nox.db"


class DownloadManager(QObject):
    downloadAdded = Signal(object)
    downloadUpdated = Signal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._path = _db_path()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._con = sqlite3.connect(str(self._path), check_same_thread=False)
        self._con.row_factory = sqlite3.Row
        self._migrate()

        # активные загрузки текущей сессии (в памяти)
        self._active: List[DownloadEntry] = []

        get_profile().downloadRequested.connect(self._on_download_requested)

    def _migrate(self) -> None:
        self._con.execute("""
            CREATE TABLE IF NOT EXISTS downloads (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                url           TEXT NOT NULL,
                path          TEXT NOT NULL,
                status        TEXT NOT NULL DEFAULT 'in-progress',
                bytesReceived INTEGER NOT NULL DEFAULT 0,
                bytesTotal    INTEGER NOT NULL DEFAULT 0
            )
        """)
        self._con.commit()

    def entries(self) -> List[DownloadEntry]:
        """Возвращает все загрузки из БД (для отображения в UI)."""
        rows = self._con.execute(
            "SELECT id, url, path, status, bytesReceived, bytesTotal FROM downloads ORDER BY id DESC"
        ).fetchall()
        result = []
        for r in rows:
            e = DownloadEntry(
                id=r["id"],
                url=r["url"],
                path=r["path"],
                status=r["status"],
                bytesReceived=r["bytesReceived"],
                bytesTotal=r["bytesTotal"],
                progress=int(r["bytesReceived"] / r["bytesTotal"] * 100) if r["bytesTotal"] > 0 else (100 if r["status"] == "finished" else 0),
            )
            # подменяем на живой объект если загрузка активна
            active = next((a for a in self._active if a.id == e.id), None)
            result.append(active if active else e)
        return result

    def _on_download_requested(self, req: QWebEngineDownloadRequest) -> None:
        suggested_name = req.suggestedFileName() or Path(QUrl(req.url()).fileName()).name
        downloads_dir = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation) or ""
        default_path = str(Path(downloads_dir) / suggested_name) if downloads_dir else suggested_name
        dest, _ = QFileDialog.getSaveFileName(None, "Save File", default_path)
        if not dest:
            req.cancel()
            return

        path_obj = Path(dest)
        req.setDownloadDirectory(str(path_obj.parent))
        req.setDownloadFileName(path_obj.name)
        req.accept()

        cur = self._con.execute(
            "INSERT INTO downloads (url, path, status) VALUES (?, ?, 'in-progress')",
            (req.url().toString(), dest),
        )
        self._con.commit()

        entry = DownloadEntry(id=cur.lastrowid, url=req.url().toString(), path=dest)
        self._active.append(entry)
        self.downloadAdded.emit(entry)

        req.receivedBytesChanged.connect(lambda r, e=entry, rqt=req: self._update_entry(e, rqt))
        req.totalBytesChanged.connect(lambda t, e=entry, rqt=req: self._update_entry(e, rqt))
        req.stateChanged.connect(lambda s, e=entry, rqt=req: self._on_finished(e, rqt))

    def _update_entry(self, entry: DownloadEntry, req: QWebEngineDownloadRequest) -> None:
        entry.bytesReceived = req.receivedBytes()
        entry.bytesTotal = req.totalBytes()
        entry.progress = int(entry.bytesReceived / entry.bytesTotal * 100) if entry.bytesTotal > 0 else 0
        self.downloadUpdated.emit(entry)

    def _on_finished(self, entry: DownloadEntry, req: QWebEngineDownloadRequest) -> None:
        state = req.state()
        if state == QWebEngineDownloadRequest.DownloadInterrupted:
            entry.status = "interrupted"
        elif state == QWebEngineDownloadRequest.DownloadCancelled:
            entry.status = "cancelled"
        elif state == QWebEngineDownloadRequest.DownloadCompleted:
            entry.status = "finished"
        else:
            entry.status = "unknown"
        entry.progress = 100

        self._con.execute(
            "UPDATE downloads SET status = ?, bytesReceived = ?, bytesTotal = ? WHERE id = ?",
            (entry.status, entry.bytesReceived, entry.bytesTotal, entry.id),
        )
        self._con.commit()
        self._active = [a for a in self._active if a.id != entry.id]
        self.downloadUpdated.emit(entry)
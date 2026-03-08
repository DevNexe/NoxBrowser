"""
core/downloads.py — простая система загрузок
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from PySide6.QtCore import QObject, Signal, QUrl, QStandardPaths
from PySide6.QtWidgets import QFileDialog
from PySide6.QtWebEngineCore import QWebEngineDownloadRequest, QWebEngineProfile


@dataclass
class DownloadEntry:
    url: str
    path: str
    status: str = "in-progress"  # in-progress / finished / cancelled / interrupted
    progress: int = 0
    bytesReceived: int = 0
    bytesTotal: int = 0


class DownloadManager(QObject):
    downloadAdded = Signal(object)    # DownloadEntry
    downloadUpdated = Signal(object)  # DownloadEntry

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._entries: List[DownloadEntry] = []

        # hook default profile so we catch downloads from any page
        profile = QWebEngineProfile.defaultProfile()
        profile.downloadRequested.connect(self._on_download_requested)

    def entries(self) -> List[DownloadEntry]:
        return list(self._entries)

    def _on_download_requested(self, req: QWebEngineDownloadRequest) -> None:  # noqa: N802
        # ask user where to save
        suggested_name = req.suggestedFileName() or Path(QUrl(req.url()).fileName()).name
        downloads_dir = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation) or ""
        default_path = str(Path(downloads_dir) / suggested_name) if downloads_dir else suggested_name
        dest, _ = QFileDialog.getSaveFileName(None, "Save File", default_path)
        if not dest:
            req.cancel()
            return

        # split into directory + filename
        path_obj = Path(dest)
        req.setDownloadDirectory(str(path_obj.parent))
        req.setDownloadFileName(path_obj.name)
        req.accept()

        entry = DownloadEntry(url=req.url().toString(), path=dest)
        self._entries.append(entry)
        self.downloadAdded.emit(entry)

        # connect progress signals
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
        self.downloadUpdated.emit(entry)

"""
ui/downloads_dialog.py — окно управления загрузками
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
    QWidget,
    QLabel,
    QProgressBar,
    QHBoxLayout,
    QPushButton,
)
from PySide6.QtCore import Qt
from core.downloads import DownloadManager, DownloadEntry
from pathlib import Path
import webbrowser


class DownloadListItem(QWidget):
    def __init__(self, entry: DownloadEntry, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.entry = entry
        self._build_ui()
        self.update()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        self._label = QLabel(self)
        self._progress = QProgressBar(self)
        self._progress.setFixedWidth(120)
        self._button = QPushButton("Open", self)
        self._button.setEnabled(False)
        self._button.clicked.connect(self._open_file)

        layout.addWidget(self._label, 1)
        layout.addWidget(self._progress)
        layout.addWidget(self._button)

    def update(self) -> None:
        self._label.setText(f"{Path(self.entry.path).name} ({self.entry.status})")
        self._progress.setValue(self.entry.progress)
        self._button.setEnabled(self.entry.status == "finished")

    def _open_file(self) -> None:
        try:
            # open parent folder if not finished
            import os
            if os.path.exists(self.entry.path):
                os.startfile(self.entry.path)
        except Exception:
            pass


class DownloadsDialog(QDialog):
    def __init__(self, manager: DownloadManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._manager = manager
        self.setWindowTitle("Downloads")
        self.resize(600, 400)
        self._setup_ui()

        # initial entries
        for e in self._manager.entries():
            self._add_entry(e)

        self._manager.downloadAdded.connect(self._add_entry)
        self._manager.downloadUpdated.connect(self._update_entry)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        self._list = QListWidget(self)
        layout.addWidget(self._list)

    def _add_entry(self, entry: DownloadEntry) -> None:
        item = QListWidgetItem(self._list)
        widget = DownloadListItem(entry)
        item.setSizeHint(widget.sizeHint())
        self._list.addItem(item)
        self._list.setItemWidget(item, widget)

    def _update_entry(self, entry: DownloadEntry) -> None:
        for i in range(self._list.count()):
            item = self._list.item(i)
            widget = self._list.itemWidget(item)
            if isinstance(widget, DownloadListItem) and widget.entry is entry:
                widget.update()
                break

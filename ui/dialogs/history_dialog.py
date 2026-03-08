"""
ui/dialogs/history_dialog.py
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton, QLabel,
)
from PySide6.QtCore import Signal, Qt

from core.history import HistoryManager


class HistoryDialog(QDialog):
    url_selected = Signal(str)

    def __init__(self, history: HistoryManager, parent=None) -> None:
        super().__init__(parent)
        self._history = history
        self.setWindowTitle("История")
        self.resize(600, 450)
        self._setup_ui()
        self._refresh()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        row = QHBoxLayout()
        row.addWidget(QLabel("Поиск:"))
        self._search = QLineEdit()
        self._search.setPlaceholderText("URL или заголовок...")
        self._search.textChanged.connect(self._refresh)
        row.addWidget(self._search)
        layout.addLayout(row)

        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self._on_activate)
        layout.addWidget(self._list)

        btns = QHBoxLayout()
        for text, slot in [("Открыть", self._on_open), ("Очистить всё", self._on_clear), ("Закрыть", self.reject)]:
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            btns.addWidget(btn)
        layout.addLayout(btns)

    def _refresh(self, query: str = "") -> None:
        self._list.clear()
        entries = self._history.search(query) if query else self._history.get_recent(200)
        for e in entries:
            item = QListWidgetItem(f"{e.title}\n{e.url}")
            item.setData(Qt.ItemDataRole.UserRole, e.url)
            item.setToolTip(e.visited_at)
            self._list.addItem(item)

    def _on_activate(self, item: QListWidgetItem) -> None:
        url = item.data(Qt.ItemDataRole.UserRole)
        if url:
            self.url_selected.emit(url)
            self.accept()

    def _on_open(self) -> None:
        item = self._list.currentItem()
        if item:
            self._on_activate(item)

    def _on_clear(self) -> None:
        self._history.clear()
        self._refresh()

"""
ui/dialogs/bookmarks_dialog.py
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton, QLabel,
)
from PySide6.QtCore import Signal, Qt

from core.bookmarks import BookmarkManager


class BookmarksDialog(QDialog):
    url_selected = Signal(str)

    def __init__(self, bookmarks: BookmarkManager, parent=None) -> None:
        super().__init__(parent)
        self._bookmarks = bookmarks
        self.setWindowTitle("Закладки")
        self.resize(600, 450)
        self._setup_ui()
        self._refresh()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        row = QHBoxLayout()
        row.addWidget(QLabel("Поиск:"))
        self._search = QLineEdit()
        self._search.setPlaceholderText("Поиск по закладкам...")
        self._search.textChanged.connect(self._refresh)
        row.addWidget(self._search)
        layout.addLayout(row)

        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self._on_activate)
        layout.addWidget(self._list)

        btns = QHBoxLayout()
        for text, slot in [("Открыть", self._on_open), ("Удалить", self._on_delete), ("Закрыть", self.reject)]:
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            btns.addWidget(btn)
        layout.addLayout(btns)

    def _refresh(self, query: str = "") -> None:
        self._list.clear()
        entries = self._bookmarks.search(query) if query else self._bookmarks.get_all()
        for b in reversed(entries):
            item = QListWidgetItem(f"{b.title}\n{b.url}")
            item.setData(Qt.ItemDataRole.UserRole, b.url)
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

    def _on_delete(self) -> None:
        item = self._list.currentItem()
        if item:
            self._bookmarks.remove(item.data(Qt.ItemDataRole.UserRole))
            self._refresh(self._search.text())

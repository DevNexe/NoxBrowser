"""
ui/devtools_window.py — Окно инструментов разработчика
"""

from __future__ import annotations

from PySide6.QtWidgets import QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QSize


class DevToolsWindow(QMainWindow):
    def __init__(self, inspected_view: QWebEngineView) -> None:
        super().__init__()
        self.setWindowTitle("DevTools — NoxBrowser")
        self.resize(QSize(1000, 600))

        dev_view = QWebEngineView(self)
        inspected_view.page().setDevToolsPage(dev_view.page())
        self.setCentralWidget(dev_view)

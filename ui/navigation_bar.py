"""
ui/navigation_bar.py - Chrome-like navigation bar
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QMenu,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class MaterialIcon:
    ARROW_BACK = "\ue5c4"
    ARROW_FORWARD = "\ue5c8"
    REFRESH = "\ue5d5"
    # use same fallback as tab bar in case the font glyph is missing
    CLOSE = "\ue5cd"
    LOCK = "\ue897"
    LOCK_OPEN = "\ue898"
    STAR = "\ue838"
    STAR_BORDER = "\ue838"
    PERSON = "\ue7fd"
    MORE_VERT = "\ue5d4"
    DOWNLOAD = "\uf090"
    SYNC = "\ue627"


class NavigationBar(QWidget):
    url_submitted = Signal(str)
    back_clicked = Signal()
    forward_clicked = Signal()
    reload_clicked = Signal()
    stop_clicked = Signal()
    home_clicked = Signal()
    bookmark_clicked = Signal()
    menu_action = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._is_loading = False
        self._setup_ui()
        self._apply_style()
        self.setStyleSheet("""
            QPushButton {
                font-family: "Material Symbols Rounded";
            }
            #navBtn {
                font-size: 20px;
            }
            #lockBtn {
                font-size: 20px;
            }
            #bookmarkBtn {
                font-size: 20px;
            }
            #downloadBtn {
                font-size: 20px;
            }
        """)

    def set_url(self, url: str) -> None:
        if not self._url_bar.hasFocus():
            u = (url or "")
            if u.startswith("nox://newtab") or u.startswith("data:text/html"):
                self._url_bar.setText("")
                self._lock_btn.setText(MaterialIcon.LOCK_OPEN)
                return
            display = url
            for prefix in ("https://", "http://"):
                if display.startswith(prefix):
                    display = display[len(prefix):]
                    break
            self._url_bar.setText(display)
            self._url_bar.setCursorPosition(0)
            self._lock_btn.setText(MaterialIcon.LOCK if url.startswith("https://") else MaterialIcon.LOCK_OPEN)

    def set_loading(self, loading: bool) -> None:
        self._is_loading = loading
        if loading:
            self._reload_stop_btn.setText(MaterialIcon.CLOSE)
            self._reload_stop_btn.setToolTip("Stop loading")
            self._progress_bar.setVisible(True)
        else:
            self._reload_stop_btn.setText(MaterialIcon.REFRESH)
            self._reload_stop_btn.setToolTip("Reload (F5)")
            self._progress_bar.setVisible(False)

    def set_progress(self, value: int) -> None:
        if 0 < value < 100:
            self._progress_bar.setValue(value)
            self._progress_bar.setVisible(True)
        else:
            self._progress_bar.setVisible(False)

    def set_download_progress(self, value: int) -> None:
        """Update download button appearance based on progress."""
        self._download_progress = value
        if value > 0 and value < 100:
            # show orange color during download
            self._download_btn.setText(MaterialIcon.DOWNLOAD)
            self._download_btn.setStyleSheet(
                "QPushButton { border: none; background: transparent; font-size: 26px; color: #fbbc04; }"
                "QPushButton:hover { background: #3c4043; border-radius: 8px; }"
            )
        elif value >= 100:
            # highlight on completion
            self._download_btn.setText(MaterialIcon.DOWNLOAD)
            self._download_btn.setStyleSheet(
                "QPushButton { border: none; background: transparent; font-size: 26px; color: #fbbc04; font-weight: bold; }"
                "QPushButton:hover { background: #3c4043; border-radius: 8px; }"
            )
            # reset color after 1 second
            QTimer.singleShot(1000, lambda: self._reset_download_btn())
        else:
            self._reset_download_btn()

    def _reset_download_btn(self) -> None:
        """Reset download button to default state."""
        self._download_btn.setText(MaterialIcon.DOWNLOAD)
        self._download_btn.setStyleSheet(
            "QPushButton { border: none; background: transparent; font-size: 26px; color: #9aa0a6; }"
            "QPushButton:hover { background: #3c4043; border-radius: 8px; }"
        )


    def set_can_go_back(self, can: bool) -> None:
        self._back_btn.setEnabled(can)

    def set_can_go_forward(self, can: bool) -> None:
        self._forward_btn.setEnabled(can)

    def set_bookmarked(self, bookmarked: bool) -> None:
        self._bookmark_btn.setText(MaterialIcon.STAR if bookmarked else MaterialIcon.STAR_BORDER)
        color = "#fbbc04" if bookmarked else "#5f6368"
        self._bookmark_btn.setStyleSheet(
            f"QPushButton {{ border: none; background: transparent; font-size: 16px; color: {color}; }}"
            "QPushButton:hover { color: #1a73e8; }"
        )

    def focus_url_bar(self) -> None:
        self._url_bar.setFocus()
        self._url_bar.selectAll()

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        toolbar = QWidget(self)
        toolbar.setObjectName("toolbar")
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(2)

        self._back_btn = self._nav_btn(MaterialIcon.ARROW_BACK, "Back (Alt+Left)")
        self._back_btn.setEnabled(False)
        self._back_btn.clicked.connect(self.back_clicked)
        layout.addWidget(self._back_btn)

        self._forward_btn = self._nav_btn(MaterialIcon.ARROW_FORWARD, "Forward (Alt+Right)")
        self._forward_btn.setEnabled(False)
        self._forward_btn.clicked.connect(self.forward_clicked)
        layout.addWidget(self._forward_btn)

        self._reload_stop_btn = self._nav_btn(MaterialIcon.REFRESH, "Reload (F5)")
        self._reload_stop_btn.clicked.connect(self._on_reload_stop)
        layout.addWidget(self._reload_stop_btn)

        layout.addSpacing(6)

        # url_wrap will contain url row + its own download bar below
        url_wrap = QWidget(toolbar)
        url_wrap.setObjectName("urlWrap")
        url_vlayout = QVBoxLayout(url_wrap)
        url_vlayout.setContentsMargins(0, 0, 0, 0)
        url_vlayout.setSpacing(2)

        row = QWidget(url_wrap)
        row.setStyleSheet("""border-radius: 20px;border: none;""")
        url_layout = QHBoxLayout(row)
        url_layout.setContentsMargins(10, 0, 6, 0)
        url_layout.setSpacing(4)

        self._lock_btn = QPushButton(MaterialIcon.LOCK, row)
        self._lock_btn.setObjectName("lockBtn")
        self._lock_btn.setFixedSize(44, 44)
        self._lock_btn.setFlat(True)
        self._lock_btn.setToolTip("Site information")
        url_layout.addWidget(self._lock_btn)

        self._url_bar = QLineEdit(row)
        self._url_bar.setObjectName("urlBar")
        self._url_bar.setPlaceholderText("Search with Google or type URL")
        self._url_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._url_bar.returnPressed.connect(self._on_url_entered)
        self._url_bar.focusInEvent = self._url_focus_in
        self._url_bar.focusOutEvent = self._url_focus_out
        url_layout.addWidget(self._url_bar)

        self._bookmark_btn = QPushButton(MaterialIcon.STAR_BORDER, row)
        self._bookmark_btn.setObjectName("bookmarkBtn")
        self._bookmark_btn.setFixedSize(44, 44)
        self._bookmark_btn.setFlat(True)
        self._bookmark_btn.setToolTip("Bookmark (Ctrl+D)")
        self._bookmark_btn.clicked.connect(self.bookmark_clicked)
        url_layout.addWidget(self._bookmark_btn)

        url_vlayout.addWidget(row)

        url_wrap.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(url_wrap)

        layout.addSpacing(6)

        self._download_btn = QPushButton(MaterialIcon.DOWNLOAD, row)
        self._download_btn.setObjectName("downloadBtn")
        self._download_btn.setFixedSize(44, 44)
        self._download_btn.setFlat(True)
        self._download_btn.setToolTip("Downloads (Ctrl+J)")
        self._download_btn.setCursor(Qt.PointingHandCursor)
        self._download_progress = 0
        layout.addWidget(self._download_btn)

        self._menu_btn = self._nav_btn(MaterialIcon.MORE_VERT, "Menu")
        self._menu_btn.clicked.connect(self._show_hamburger_menu)
        layout.addWidget(self._menu_btn)

        outer.addWidget(toolbar)

        self._progress_bar = QProgressBar(self)
        self._progress_bar.setObjectName("progressBar")
        self._progress_bar.setMaximumHeight(3)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setVisible(False)
        self._progress_bar.setTextVisible(False)
        outer.addWidget(self._progress_bar)


    def _apply_style(self) -> None:
        pass

    @staticmethod
    def _nav_btn(text: str, tooltip: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("navBtn")
        btn.setToolTip(tooltip)
        btn.setFixedSize(44, 44)
        return btn

    def _show_hamburger_menu(self) -> None:
        menu = QMenu(self)

        items = [
            ("New Tab", "new_tab"),
            ("Bookmarks", "bookmarks"),
            ("History", "history"),
            ("Downloads", "downloads"),
            None,
            ("Zoom In", "zoom_in"),
            ("Zoom Out", "zoom_out"),
            ("Reset Zoom", "zoom_reset"),
            None,
            ("Developer Tools", "devtools"),
            None,
            ("About NoxBrowser", "about"),
        ]

        for item in items:
            if item is None:
                menu.addSeparator()
            else:
                label, action_id = item
                action = QAction(label, self)
                action.triggered.connect(lambda checked=False, aid=action_id: self.menu_action.emit(aid))
                menu.addAction(action)

        pos = self._menu_btn.mapToGlobal(self._menu_btn.rect().bottomRight())
        menu.exec(pos)

    def _on_url_entered(self) -> None:
        url = self._url_bar.text().strip()
        if url:
            self.url_submitted.emit(url)

    def _on_reload_stop(self) -> None:
        if self._is_loading:
            self.stop_clicked.emit()
        else:
            self.reload_clicked.emit()

    def _url_focus_in(self, event) -> None:
        QLineEdit.focusInEvent(self._url_bar, event)
        self._url_bar.selectAll()

    def _url_focus_out(self, event) -> None:
        QLineEdit.focusOutEvent(self._url_bar, event)

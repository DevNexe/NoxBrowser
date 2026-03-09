"""
ui/main_window.py - Main browser window with native window frame.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QEvent, QPoint, QRect, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabBar,
    QVBoxLayout,
    QWidget,
)

from qframelesswindow import FramelessWindow

from ui.tab_bar import TabBar, CustomTabBar
from core.bookmarks import BookmarkManager
from core.browser_widget import BrowserWidget
from core.history import HistoryManager
from plugins.plugin_manager import PluginManager
from ui.navigation_bar import NavigationBar
from ui.tab_bar import TabBar
from utils.logger import get_logger

logger = get_logger(__name__)


class MaterialIcon:
    ADD = "\uf3dd"
    MINIMIZE = "\ue15b"
    MAXIMIZE = "\ue3c6"
    RESTORE = "\uf4c8"
    CLOSE = "\ue5cd"


class EdgeGrip(QWidget):
    def __init__(self, parent: QWidget, edges: Qt.Edges) -> None:
        super().__init__(parent)
        self._edges = edges
        self.setMouseTracking(True)
        self.setCursor(self._cursor_for_edges(edges))
        self.setStyleSheet("background: transparent;")

    @staticmethod
    def _cursor_for_edges(edges: Qt.Edges):
        if edges in (Qt.LeftEdge | Qt.TopEdge, Qt.RightEdge | Qt.BottomEdge):
            return Qt.SizeFDiagCursor
        if edges in (Qt.RightEdge | Qt.TopEdge, Qt.LeftEdge | Qt.BottomEdge):
            return Qt.SizeBDiagCursor
        if edges in (Qt.LeftEdge, Qt.RightEdge):
            return Qt.SizeHorCursor
        return Qt.SizeVerCursor

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            handle = self.window().windowHandle()
            if handle and handle.startSystemResize(self._edges):
                event.accept()
                return
        super().mousePressEvent(event)


class NoxTitleBar(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(34)
        self._tabs_controller = None
        self._syncing_tabs = False
        self._build_ui()

    def _build_ui(self) -> None:
        self.setStyleSheet(
            """
            NoxTitleBar {
                background-color: #202124;
                border-bottom: 1px solid #404040;
            }
            QPushButton {
                background: transparent;
                border: none;
                color: #e8eaed;
                min-width: 26px;
                max-width: 26px;
                min-height: 26px;
                max-height: 26px;
                border-radius: 8px;
                font-size: 13px;
                margin: 4px 4px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.15);
            }
            QPushButton#closeBtn:hover { background-color: #f1707a; }
            QPushButton#closeBtn:pressed { background-color: #f1707a; }
            QPushButton#maximizeBtn:hover,
            QPushButton#maximizeBtn[hover="true"] {
                background-color: rgba(255, 255, 255, 0.18);
                color: #ffffff;
                border-radius: 8px;
            }
            QPushButton#maximizeBtn:pressed {
                background-color: rgba(255, 255, 255, 0.26);
                border-radius: 8px;
            }
            QPushButton#maximizeBtn {
                font-family: "Material Symbols Rounded";
                font-size: 16px;
            }
            QPushButton#minimizeBtn,
            QPushButton#closeBtn {
                font-family: "Material Symbols Rounded";
                font-size: 20px;
            }
            QTabBar {
                background: transparent;
                border: none;
                border-bottom: none;
            }
            QTabBar::tab {
                background: #202124;
                color: #9aa0a6;
                padding: 0px 10px;
                min-width: 46px;
                max-width: 240px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
                margin-top: 0px;
                height: 34px;
                line-height: 34px;
                text-align: left;
                padding-left: 12px;
            }
            QTabBar::tab:selected { background: #35363a; color: #e8eaed; }
            QTabBar::tab:hover:!selected {
                background: #2d2e30;
                color: #e8eaed;
            }
            QTabBar::close-button { subcontrol-position: right; }
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs_bar = CustomTabBar(self)
        self.tabs_bar.close_clicked.connect(self._on_title_tab_closed)
        self.tabs_bar.tab_detach_requested.connect(self._on_title_tab_detach)
        self.tabs_bar.tabMoved.connect(self._on_title_tab_moved)
        self.tabs_bar.new_tab_clicked.connect(self._on_title_new_tab)
        self.tabs_bar.setDocumentMode(True)
        self.tabs_bar.setMovable(True)
        self.tabs_bar.setExpanding(False)
        self.tabs_bar.setUsesScrollButtons(True)
        self.tabs_bar.setDrawBase(False)
        self.tabs_bar.setElideMode(Qt.ElideRight)
        self.tabs_bar.installEventFilter(self)
        self.tabs_bar.currentChanged.connect(self._on_title_tab_changed)
        layout.addWidget(self.tabs_bar, 1)

        self.minimize_btn = QPushButton(MaterialIcon.MINIMIZE, self)
        self.maximize_btn = QPushButton(MaterialIcon.MAXIMIZE, self)
        self.close_btn = QPushButton(MaterialIcon.CLOSE, self)
        self.minimize_btn.setObjectName("minimizeBtn")
        self.maximize_btn.setObjectName("maximizeBtn")
        self.close_btn.setObjectName("closeBtn")
        self.minimize_btn.setFont(QFont("Material Symbols Rounded", 20))
        self.maximize_btn.setFont(QFont("Material Symbols Rounded", 18))
        self.close_btn.setFont(QFont("Material Symbols Rounded", 20))

        self.minimize_btn.clicked.connect(self.window().showMinimized)
        self.maximize_btn.clicked.connect(self.toggle_maximize)
        self.close_btn.clicked.connect(self.window().close)

        layout.addWidget(self.minimize_btn)
        layout.addWidget(self.maximize_btn)
        layout.addWidget(self.close_btn)

    def bind_tabs(self, tabs_controller) -> None:
        self._tabs_controller = tabs_controller
        self._tabs_controller.tabs_updated.connect(self._refresh_tabs_from_controller)
        self._refresh_tabs_from_controller()
        # устанавливаем фейковую вкладку + после первичной синхронизации
        QTimer.singleShot(0, self.tabs_bar.install_add_tab)

    def _on_title_tab_detach(self, index: int, global_pos: QPoint) -> None:
        if not self._tabs_controller:
            return
        self._tabs_controller.detach_tab(index, global_pos)

    def _on_title_tab_moved(self, from_index: int, to_index: int) -> None:
        if self._syncing_tabs or not self._tabs_controller:
            return
        # не синкаем перемещение фейковой вкладки +
        add_idx = self.tabs_bar._add_index()
        if from_index == add_idx or to_index == add_idx:
            return
        self._tabs_controller._syncing_move = True
        self._tabs_controller._tabs.tabBar().moveTab(from_index, to_index)
        self._tabs_controller._syncing_move = False
        QTimer.singleShot(0, self._tabs_controller._sync_all_icons)

    def _refresh_tabs_from_controller(self) -> None:
        if not self._tabs_controller:
            return
        self._syncing_tabs = True
        self.tabs_bar.blockSignals(True)

        # удаляем все реальные вкладки (не +)
        add_idx = self.tabs_bar._add_index()
        # удаляем с конца чтобы не сбивать индексы
        indices = list(range(self.tabs_bar.count()))
        for i in reversed(indices):
            if i != add_idx:
                self.tabs_bar.removeTab(i)

        for i in range(self._tabs_controller.tab_count()):
            self.tabs_bar.insertTab(i, self._tabs_controller.tab_title(i))

        self.tabs_bar.setCurrentIndex(self._tabs_controller.current_index())
        self.tabs_bar.blockSignals(False)
        self._syncing_tabs = False

    def _on_title_tab_changed(self, index: int) -> None:
        if self._syncing_tabs or not self._tabs_controller:
            return
        # игнорируем выбор фейковой вкладки +
        if self.tabs_bar._has_add_tab and index == self.tabs_bar._add_index():
            return
        self._tabs_controller.set_current_index(index)

    def _on_title_tab_closed(self, index: int) -> None:
        if not self._tabs_controller:
            return
        self._tabs_controller.close_tab_at(index)

    def _on_title_new_tab(self) -> None:
        if not self._tabs_controller:
            return
        self._tabs_controller.new_tab_requested.emit("")

    def eventFilter(self, obj, event):
        if obj is self.tabs_bar and event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton and self.window().windowHandle():
                if self.tabs_bar.tabAt(event.pos()) == -1:
                    self.window().windowHandle().startSystemMove()
                    return True
                return False
        return super().eventFilter(obj, event)

    def toggle_maximize(self) -> None:
        win = self.window()
        if sys.platform == "win32":
            try:
                import ctypes
                hwnd = int(win.winId())
                SW_MAXIMIZE = 3
                SW_RESTORE = 9
                cmd = SW_RESTORE if win.isMaximized() else SW_MAXIMIZE
                ctypes.windll.user32.ShowWindow(hwnd, cmd)
            except Exception:
                if win.isMaximized():
                    win.showNormal()
                else:
                    win.showMaximized()
        else:
            if win.isMaximized():
                win.showNormal()
            else:
                win.showMaximized()

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.toggle_maximize()
        event.accept()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton and self.window().windowHandle():
            self.window().windowHandle().startSystemMove()
        super().mousePressEvent(event)


class MainWindow(FramelessWindow):
    def __init__(self) -> None:
        super().__init__()
        self._native_snap_styles_applied = False
        self._nc_max_btn_pressed = False
        self._dwm_update_timer = QTimer(self)
        self._dwm_update_timer.setSingleShot(True)
        self._dwm_update_timer.timeout.connect(self._apply_windows_dwm_preferences)

        self._history = HistoryManager()
        self._bookmarks = BookmarkManager()
        from core.downloads import DownloadManager
        self._downloads = DownloadManager()
        self._downloads.downloadUpdated.connect(lambda e: self._nav_bar.set_download_progress(e.progress))
        self._plugin_manager = PluginManager(browser_window=self)

        self._setup_window()
        self._setup_ui()
        self._init_resize_grips()
        self._setup_shortcuts()

        self._plugin_manager.load_all()
        logger.info("NoxBrowser started")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def open_url(self, url: str) -> None:
        self._current_browser().load_url(url)

    def open_new_tab(self, url: str = "") -> None:
        self._tab_bar.add_tab(url or "")

    def get_current_url(self) -> str:
        return self._current_browser().get_url()

    def get_history(self) -> HistoryManager:
        return self._history

    def get_bookmarks(self) -> BookmarkManager:
        return self._bookmarks

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_window(self) -> None:
        self.setWindowTitle("NoxBrowser")
        self.setMinimumWidth(500)
        self.setMinimumHeight(35)
        self.resize(1280, 800)
        old_title_bar = getattr(self, "titleBar", None)
        if old_title_bar is not None:
            try:
                self.removeEventFilter(old_title_bar)
            except Exception:
                pass
        self.custom_title_bar = NoxTitleBar(self)
        self.setTitleBar(self.custom_title_bar)
        if old_title_bar is not None:
            try:
                old_title_bar.hide()
                old_title_bar.setParent(None)
                from shiboken6 import delete as shiboken_delete
                shiboken_delete(old_title_bar)
            except Exception:
                pass
        if sys.platform == "win32":
            self._apply_windows_dwm_preferences()
            QTimer.singleShot(0, self._enable_native_snap_styles)

    def _apply_windows_dwm_preferences(self) -> None:
        if sys.platform != "win32":
            return
        try:
            import ctypes
            hwnd = int(self.winId())
            dwmapi = ctypes.windll.dwmapi
            dark_mode = ctypes.c_int(1)
            dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark_mode), ctypes.sizeof(dark_mode))
            square_needed = self.isMaximized() or self.isFullScreen() or self._is_snapped_to_edge()
            corner_pref = ctypes.c_int(1 if square_needed else 2)
            dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(corner_pref), ctypes.sizeof(corner_pref))
            border_none = ctypes.c_uint(0xFFFFFFFE)
            dwmapi.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(border_none), ctypes.sizeof(border_none))
            if hasattr(self, "windowEffect"):
                if square_needed:
                    self.windowEffect.removeShadowEffect(self.winId())
                else:
                    self.windowEffect.addShadowEffect(self.winId())
        except Exception:
            pass

    def _is_snapped_to_edge(self) -> bool:
        try:
            handle = self.windowHandle()
            if not handle or not handle.screen():
                return False
            avail = handle.screen().availableGeometry()
            frame = self.frameGeometry()
            eps = 2
            full_height = abs(frame.top() - avail.top()) <= eps and abs(frame.bottom() - avail.bottom()) <= eps
            left_docked = abs(frame.left() - avail.left()) <= eps
            right_docked = abs(frame.right() - avail.right()) <= eps
            not_full_width = frame.width() < (avail.width() - 20)
            return full_height and (left_docked or right_docked) and not_full_width
        except Exception:
            return False

    def _enforce_maximized_workarea_bounds(self) -> None:
        if sys.platform != "win32" or not self.isMaximized():
            return
        try:
            import ctypes
            handle = self.windowHandle()
            if not handle or not handle.screen():
                return
            avail = handle.screen().availableGeometry()
            user32 = ctypes.windll.user32
            SM_CXSIZEFRAME = 32
            SM_CYSIZEFRAME = 33
            SM_CXPADDEDBORDER = 92
            frame_x = int(user32.GetSystemMetrics(SM_CXSIZEFRAME) + user32.GetSystemMetrics(SM_CXPADDEDBORDER))
            frame_y = int(user32.GetSystemMetrics(SM_CYSIZEFRAME) + user32.GetSystemMetrics(SM_CXPADDEDBORDER))
            SWP_NOZORDER = 0x0004
            SWP_NOACTIVATE = 0x0010
            user32.SetWindowPos(
                int(self.winId()), 0,
                int(avail.x() - frame_x), int(avail.y() - frame_y),
                int(avail.width() + frame_x * 2), int(avail.height() + frame_y * 2),
                SWP_NOZORDER | SWP_NOACTIVATE,
            )
        except Exception:
            pass

    def _enable_native_snap_styles(self) -> None:
        if sys.platform != "win32":
            return
        try:
            import ctypes
            GWL_STYLE = -16
            WS_THICKFRAME = 0x00040000
            WS_MAXIMIZEBOX = 0x00010000
            WS_MINIMIZEBOX = 0x00020000
            WS_SYSMENU = 0x00080000
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOZORDER = 0x0004
            SWP_NOACTIVATE = 0x0010
            SWP_FRAMECHANGED = 0x0020
            hwnd = int(self.winId())
            user32 = ctypes.windll.user32
            style = user32.GetWindowLongW(hwnd, GWL_STYLE)
            wanted = WS_THICKFRAME | WS_MAXIMIZEBOX | WS_MINIMIZEBOX | WS_SYSMENU
            new_style = style | wanted
            if new_style != style:
                user32.SetWindowLongW(hwnd, GWL_STYLE, new_style)
                user32.SetWindowPos(
                    hwnd, 0, 0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
                )
            self._native_snap_styles_applied = True
        except Exception:
            pass

    def _init_resize_grips(self) -> None:
        self._grip_thickness = 8
        self._resize_grips = [
            EdgeGrip(self, Qt.LeftEdge),
            EdgeGrip(self, Qt.RightEdge),
            EdgeGrip(self, Qt.TopEdge),
            EdgeGrip(self, Qt.BottomEdge),
            EdgeGrip(self, Qt.LeftEdge | Qt.TopEdge),
            EdgeGrip(self, Qt.RightEdge | Qt.TopEdge),
            EdgeGrip(self, Qt.LeftEdge | Qt.BottomEdge),
            EdgeGrip(self, Qt.RightEdge | Qt.BottomEdge),
        ]
        self._update_resize_grips()

    def _setup_ui(self) -> None:
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._nav_bar = NavigationBar(container)
        self._nav_bar.url_submitted.connect(self.open_url)
        self._nav_bar.back_clicked.connect(lambda: self._current_browser().go_back())
        self._nav_bar.forward_clicked.connect(lambda: self._current_browser().go_forward())
        self._nav_bar.reload_clicked.connect(lambda: self._current_browser().reload())
        self._nav_bar.stop_clicked.connect(lambda: self._current_browser().stop_loading())
        self._nav_bar.bookmark_clicked.connect(self._on_toggle_bookmark)
        self._nav_bar.menu_action.connect(self._on_menu_action)
        self._nav_bar._download_btn.clicked.connect(self._show_downloads)
        layout.addWidget(self._nav_bar)

        self._tab_bar = TabBar(self._history, parent=container)
        self._tab_bar.current_url_changed.connect(self._on_current_url_changed)
        self._tab_bar.current_title_changed.connect(self._on_current_title_changed)
        self._tab_bar.loading_state_changed.connect(self._nav_bar.set_loading)
        self._tab_bar.load_progress.connect(self._nav_bar.set_progress)
        self._tab_bar.new_tab_requested.connect(self.open_new_tab)
        self._tab_bar.set_tab_header_visible(False)
        self.custom_title_bar.bind_tabs(self._tab_bar)
        self._tab_bar.register_external_tab_bar(self.custom_title_bar.tabs_bar)
        layout.addWidget(self._tab_bar)

        self._content_container = container
        self.setContentWidget(container)
        self._sync_nav_with_current_tab()

    def setContentWidget(self, widget: QWidget) -> None:
        if not hasattr(self, "main_layout"):
            self.main_layout = QVBoxLayout(self)
            self.main_layout.setContentsMargins(0, 0, 0, 0)
            self.main_layout.setSpacing(0)
            self.main_layout.addWidget(self.custom_title_bar)
            separator = QFrame(self)
            separator.setFixedHeight(1)
            separator.setStyleSheet("background-color: #404040;")
            self.main_layout.addWidget(separator)
            self.main_layout.addWidget(widget)
        else:
            old_widget = self.main_layout.itemAt(2).widget()
            self.main_layout.replaceWidget(old_widget, widget)
            old_widget.deleteLater()

    def _setup_shortcuts(self) -> None:
        shortcuts = [
            ("Ctrl+L", self._nav_bar.focus_url_bar),
            ("F5", lambda: self._current_browser().reload()),
            ("Ctrl+T", self.open_new_tab),
            ("Ctrl+W", self._tab_bar.close_current_tab),
            ("Ctrl+H", self._show_history),
            ("Ctrl+D", self._add_bookmark),
            ("Ctrl+Shift+B", self._show_bookmarks),
            ("Ctrl++", lambda: self._current_browser().zoom_in()),
            ("Ctrl+-", lambda: self._current_browser().zoom_out()),
            ("Ctrl+0", lambda: self._current_browser().zoom_reset()),
            ("F12", lambda: self._current_browser().show_devtools()),
            ("Ctrl+J", self._show_downloads),
            ("Ctrl+Q", self.close),
        ]
        for key, slot in shortcuts:
            sc = QShortcut(QKeySequence(key), self)
            sc.activated.connect(slot)

    # ------------------------------------------------------------------
    # Browser state
    # ------------------------------------------------------------------

    def _current_browser(self) -> BrowserWidget:
        return self._tab_bar.current_browser_widget

    def _sync_nav_with_current_tab(self) -> None:
        browser = self._current_browser()
        url = browser.get_url()
        self._nav_bar.set_url(url)
        self._nav_bar.set_bookmarked(self._bookmarks.is_bookmarked(url))
        self._nav_bar.set_can_go_back(browser.can_go_back())
        self._nav_bar.set_can_go_forward(browser.can_go_forward())

    def _on_current_url_changed(self, url: str) -> None:
        self._nav_bar.set_url(url)
        self._nav_bar.set_bookmarked(self._bookmarks.is_bookmarked(url))
        browser = self._current_browser()
        self._nav_bar.set_can_go_back(browser.can_go_back())
        self._nav_bar.set_can_go_forward(browser.can_go_forward())
        self._plugin_manager.notify_url_changed(url)

    def _on_current_title_changed(self, title: str) -> None:
        self.setWindowTitle(f"{title} - NoxBrowser" if title else "NoxBrowser")

    # ------------------------------------------------------------------
    # Menu and actions
    # ------------------------------------------------------------------

    def _on_menu_action(self, action_id: str) -> None:
        handlers = {
            "new_tab": self.open_new_tab,
            "history": self._show_history,
            "bookmarks": self._show_bookmarks,
            "downloads": self._show_downloads,
            "zoom_in": lambda: self._current_browser().zoom_in(),
            "zoom_out": lambda: self._current_browser().zoom_out(),
            "zoom_reset": lambda: self._current_browser().zoom_reset(),
            "devtools": lambda: self._current_browser().show_devtools(),
            "about": self._about,
        }
        handler = handlers.get(action_id)
        if handler:
            handler()

    def _on_toggle_bookmark(self) -> None:
        url = self.get_current_url()
        if not url or url == "about:blank":
            return
        if self._bookmarks.is_bookmarked(url):
            self._bookmarks.remove(url)
            self._nav_bar.set_bookmarked(False)
        else:
            title = self._current_browser().get_title() or url
            self._bookmarks.add(url, title)
            self._nav_bar.set_bookmarked(True)

    def _add_bookmark(self) -> None:
        url = self.get_current_url()
        if not url or url == "about:blank":
            return
        if not self._bookmarks.is_bookmarked(url):
            title = self._current_browser().get_title() or url
            self._bookmarks.add(url, title)
            self._nav_bar.set_bookmarked(True)

    def _show_history(self) -> None:
        self.open_new_tab("nox://history/")

    def _show_bookmarks(self) -> None:
        self.open_new_tab("nox://bookmarks/")

    def _show_downloads(self) -> None:
        self.open_new_tab("nox://downloads/")

    def _about(self) -> None:
        QMessageBox.about(
            self,
            "About NoxBrowser",
            "<h3>NoxBrowser v1.0</h3>"
            "<p>Modular browser on Python + PySide6 + Chromium</p>"
            "<p>Engine: QtWebEngine</p>",
        )

    # ------------------------------------------------------------------
    # Qt events
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:  # noqa: N802
        self._tab_bar.close_all_tabs()
        super().closeEvent(event)

    def changeEvent(self, event) -> None:  # noqa: N802
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange and hasattr(self, "custom_title_bar"):
            if self.isMaximized():
                self.custom_title_bar.maximize_btn.setText(MaterialIcon.RESTORE)
                if sys.platform == "win32":
                    QTimer.singleShot(0, self._enforce_maximized_workarea_bounds)
            else:
                self.custom_title_bar.maximize_btn.setText(MaterialIcon.MAXIMIZE)
            self._update_resize_grips()
            if sys.platform == "win32":
                self._apply_windows_dwm_preferences()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._update_resize_grips()
        if sys.platform == "win32":
            self._dwm_update_timer.start(30)
        if hasattr(self, "_tab_bar"):
            if self.height() < 50:
                self._tab_bar.setMaximumHeight(0)
            else:
                self._tab_bar.setMaximumHeight(16777215)

    def moveEvent(self, event) -> None:  # noqa: N802
        super().moveEvent(event)
        if sys.platform == "win32":
            self._dwm_update_timer.start(30)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if sys.platform == "win32" and not self._native_snap_styles_applied:
            self._enable_native_snap_styles()
        if sys.platform == "win32":
            self._apply_windows_dwm_preferences()

    def nativeEvent(self, eventType, message):  # noqa: N802
        if sys.platform == "win32":
            try:
                import ctypes
                import win32con
                from ctypes.wintypes import MSG

                msg = MSG.from_address(int(message))
                if msg.message == win32con.WM_NCHITTEST and hasattr(self, "custom_title_bar"):
                    btn = getattr(self.custom_title_bar, "maximize_btn", None)
                    if (
                        btn is not None
                        and btn.isVisible()
                        and btn.isEnabled()
                        and not self.isMaximized()
                    ):
                        top_left = btn.mapToGlobal(QPoint(0, 0))
                        rect = QRect(top_left, btn.size())
                        if rect.contains(QCursor.pos()):
                            if QApplication.mouseButtons() == Qt.NoButton:
                                return True, win32con.HTMAXBUTTON
                            return True, win32con.HTCLIENT

                if msg.message == win32con.WM_NCLBUTTONDOWN and int(msg.wParam) == win32con.HTMAXBUTTON:
                    self._nc_max_btn_pressed = True
                    return True, 0
                if msg.message == win32con.WM_NCLBUTTONUP:
                    if int(msg.wParam) == win32con.HTMAXBUTTON or self._nc_max_btn_pressed:
                        self._nc_max_btn_pressed = False
                        if hasattr(self, "custom_title_bar"):
                            self.custom_title_bar.toggle_maximize()
                        return True, 0

                if msg.message in (win32con.WM_CREATE, win32con.WM_ACTIVATE, win32con.WM_STYLECHANGED):
                    self._apply_windows_dwm_preferences()

                if msg.message in (win32con.WM_NCMOUSEMOVE, 0x02A0):
                    btn = getattr(self.custom_title_bar, "maximize_btn", None)
                    if btn is not None:
                        top_left = btn.mapToGlobal(QPoint(0, 0))
                        rect = QRect(top_left, btn.size())
                        hovered = rect.contains(QCursor.pos())
                        btn.setProperty("hover", hovered)
                        btn.style().unpolish(btn)
                        btn.style().polish(btn)
                if msg.message == win32con.WM_NCMOUSELEAVE:
                    btn = getattr(self.custom_title_bar, "maximize_btn", None)
                    if btn is not None:
                        btn.setProperty("hover", False)
                        btn.style().unpolish(btn)
                        btn.style().polish(btn)
            except Exception:
                pass
        return super().nativeEvent(eventType, message)

    def _update_resize_grips(self) -> None:
        if not hasattr(self, "_resize_grips"):
            return
        visible = not self.isMaximized() and not self.isFullScreen()
        for grip in self._resize_grips:
            grip.setVisible(visible)
        if not visible:
            return
        t = self._grip_thickness
        w = self.width()
        h = self.height()
        left, right, top, bottom, tl, tr, bl, br = self._resize_grips
        left.setGeometry(0, t, t, max(0, h - 2 * t))
        right.setGeometry(max(0, w - t), t, t, max(0, h - 2 * t))
        top.setGeometry(t, 0, max(0, w - 2 * t), t)
        bottom.setGeometry(t, max(0, h - t), max(0, w - 2 * t), t)
        tl.setGeometry(0, 0, t, t)
        tr.setGeometry(max(0, w - t), 0, t, t)
        bl.setGeometry(0, max(0, h - t), t, t)
        br.setGeometry(max(0, w - t), max(0, h - t), t, t)
        for grip in self._resize_grips:
            grip.raise_()
        if hasattr(self, "custom_title_bar"):
            self.custom_title_bar.raise_()
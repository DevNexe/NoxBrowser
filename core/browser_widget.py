"""
core/browser_widget.py

BrowserWidget — Qt-виджет с встроенным Chromium через PySide6 WebEngine.
"""

from __future__ import annotations

from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Signal, QUrl, Qt
from PySide6.QtGui import QKeySequence

from utils.logger import get_logger

logger = get_logger(__name__)


class BrowserPage(QWebEnginePage):
    """
    Кастомная страница — перехватывает создание новых окон
    и превращает их в сигнал для открытия новой вкладки.
    """

    new_window_requested = Signal(str)
    def createWindow(self, window_type: QWebEnginePage.WebWindowType) -> QWebEnginePage | None:  # noqa: N802
        # Вместо нового окна — эмитируем сигнал
        self.new_window_requested.emit("")
        return None

    def javaScriptConsoleMessage(self, level, message, line, source):  # noqa: N802
        # Suppress noisy page-side console logs in normal runs.
        return


class BrowserWidget(QWidget):
    """
    Виджет браузера на основе QWebEngineView.

    Signals:
        url_changed(str)
        title_changed(str)
        loading_state_changed(bool)
        load_progress(int)
        new_window_requested(str)
    """

    url_changed = Signal(str)
    title_changed = Signal(str)
    loading_state_changed = Signal(bool)
    load_progress = Signal(int)
    new_window_requested = Signal(str)
    icon_changed = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._is_new_tab_page = False
        self._setup_ui()
        self._connect_signals()

    # ------------------------------------------------------------------
    # Публичный API навигации
    # ------------------------------------------------------------------

    def load_url(self, url: str) -> None:
        if self._is_new_tab_request(url):
            self._load_new_tab_page()
            return

        self._is_new_tab_page = False
        url = self._normalize_url(url)
        self._view.setUrl(QUrl(url))

    def go_back(self) -> None:
        self._view.back()

    def go_forward(self) -> None:
        self._view.forward()

    def reload(self, ignore_cache: bool = False) -> None:
        if ignore_cache:
            self._view.reloadAndBypassCache()
        else:
            self._view.reload()

    def stop_loading(self) -> None:
        self._view.stop()

    def execute_javascript(self, js: str) -> None:
        self._view.page().runJavaScript(js)

    def can_go_back(self) -> bool:
        return self._view.history().canGoBack()

    def can_go_forward(self) -> bool:
        return self._view.history().canGoForward()

    def is_loading(self) -> bool:
        return self._view.isLoading() if hasattr(self._view, 'isLoading') else False

    def get_url(self) -> str:
        raw = self._view.url().toString()
        if self._is_new_tab_page and raw.startswith("data:text/html"):
            return "nox://newtab/"
        return raw

    def get_title(self) -> str:
        return self._view.title()

    def zoom_in(self) -> None:
        self._view.setZoomFactor(self._view.zoomFactor() + 0.1)

    def zoom_out(self) -> None:
        self._view.setZoomFactor(max(0.1, self._view.zoomFactor() - 0.1))

    def zoom_reset(self) -> None:
        self._view.setZoomFactor(1.0)

    def show_devtools(self) -> None:
        from ui.devtools_window import DevToolsWindow
        self._devtools = DevToolsWindow(self._view)
        self._devtools.show()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Профиль — можно настроить кэш, куки и т.д.
        profile = QWebEngineProfile.defaultProfile()
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)

        # Страница с кастомным обработчиком
        page = BrowserPage(profile, self)

        self._view = QWebEngineView(self)
        self._view.setPage(page)

        # Настройки WebEngine
        settings = self._view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)

        layout.addWidget(self._view)

    def _connect_signals(self) -> None:
        self._view.iconChanged.connect(self.icon_changed.emit)
        self._view.urlChanged.connect(self._on_view_url_changed)
        self._view.titleChanged.connect(self.title_changed.emit)
        self._view.loadStarted.connect(lambda: self.loading_state_changed.emit(True))
        self._view.loadFinished.connect(lambda _: self.loading_state_changed.emit(False))
        self._view.loadProgress.connect(self.load_progress.emit)
        self._view.page().new_window_requested.connect(self.new_window_requested.emit)

    # ------------------------------------------------------------------
    # Утилиты
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_url(url: str) -> str:
        url = url.strip()
        if not url:
            return "about:blank"
        if url.startswith("about:") or url.startswith("file://"):
            return url
        if "://" not in url:
            if " " in url or "." not in url:
                return f"https://www.google.com/search?q={url.replace(' ', '+')}"
            return f"https://{url}"
        return url

    @staticmethod
    def _is_new_tab_request(url: str) -> bool:
        u = (url or "").strip().lower()
        return u in ("", "about:blank", "about:newtab", "nox://newtab", "nox://newtab/")

    def _on_view_url_changed(self, url: QUrl) -> None:
        s = url.toString()
        if self._is_new_tab_page and (not s or s == "about:blank" or s.startswith("data:text/html")):
            self.url_changed.emit("nox://newtab/")
            return
        self._is_new_tab_page = False
        self.url_changed.emit(s)

    def _load_new_tab_page(self) -> None:
        self._is_new_tab_page = True
        html = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>New Tab</title>
  <style>
    :root { color-scheme: dark; }
    html, body { margin: 0; height: 100%; font-family: "Segoe UI", Arial, sans-serif; background: #202124; color: #e8eaed; }
    .wrap { height: 100%; display: grid; place-items: center; }
    .content { width: min(92vw, 720px); text-align: center; transform: translateY(-7vh); }
    .logo { font-size: 64px; font-weight: 600; letter-spacing: -1px; margin-bottom: 26px; user-select: none; }
    .search { display: flex; align-items: center; gap: 10px; background: #303134; border: 1px solid #5f6368; border-radius: 28px; padding: 0 4px 0 8px; height: 44px; }
    .search input { flex: 1; background: transparent; border: none; outline: none; color: #e8eaed; font-size: 17px; }
    .search button { border: none; background: #8ab4f8; color: #202124; font-weight: 600; border-radius: 18px; height: 36px; padding: 0 16px; cursor: pointer; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="content">
      <div class="logo">NoxBrowser</div>
      <form class="search" method="get" action="https://www.google.com/search">
        <input type="text" name="q" placeholder="Search Google or type a URL" autocomplete="off" />
        <button type="submit">Search</button>
      </form>
    </div>
  </div>
</body>
</html>
"""
        self._view.setHtml(html)
        self.title_changed.emit("New Tab")
        self.url_changed.emit("nox://newtab/")

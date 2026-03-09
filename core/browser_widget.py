"""
core/browser_widget.py

BrowserWidget — Qt-виджет с встроенным Chromium через PySide6 WebEngine.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from urllib.parse import urlparse, parse_qs, quote, unquote

from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Signal, QUrl, Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont

from utils.logger import get_logger

logger = get_logger(__name__)

_PAGE_STYLE = """
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: "Segoe UI", Arial, sans-serif; background: #202124; color: #e8eaed; padding: 32px; }
  h1 { font-size: 24px; font-weight: 500; margin-bottom: 20px; color: #e8eaed; }
  .toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }
  .search-bar { flex: 1; max-width: 500px; background: #303134; border: 1px solid #5f6368;
    border-radius: 8px; padding: 9px 14px; color: #e8eaed; font-size: 14px; outline: none; }
  .search-bar:focus { border-color: #8ab4f8; }
  .btn { background: #3c4043; color: #e8eaed; border: none; border-radius: 6px;
    padding: 8px 16px; font-size: 13px; cursor: pointer; white-space: nowrap; }
  .btn:hover { background: #5f6368; }
  .btn-danger { background: #5c2020; color: #f28b82; }
  .btn-danger:hover { background: #7c2e2e; }
  table { width: 100%; border-collapse: collapse; }
  th { text-align: left; padding: 8px 12px; color: #9aa0a6; font-size: 12px;
    font-weight: 500; border-bottom: 1px solid #3c4043; }
  td { padding: 10px 12px; border-bottom: 1px solid #2d2e30; font-size: 13px; vertical-align: middle; }
  tr:hover td { background: #2d2e30; }
  a.page-link { color: #8ab4f8; text-decoration: none; cursor: pointer; }
  a.page-link:hover { text-decoration: underline; }
  .url-text { color: #9aa0a6; font-size: 12px; }
  .del-btn { background: none; border: none; color: #9aa0a6; cursor: pointer; font-size: 15px;
    padding: 2px 8px; border-radius: 4px; }
  .del-btn:hover { color: #ea4335; background: #3c2020; }
  .status { font-size: 12px; padding: 2px 8px; border-radius: 4px; display: inline-block; }
  .status.finished { background: #1e3a2f; color: #34a853; }
  .status.in-progress { background: #1a2e4a; color: #8ab4f8; }
  .status.interrupted, .status.cancelled { background: #3c2020; color: #ea4335; }
  .empty { color: #9aa0a6; text-align: center; padding: 48px; }
</style>
"""

_FILTER_JS = """
<script>
function filterTable(q) {
  q = q.toLowerCase();
  document.querySelectorAll('#tbl tbody tr').forEach(tr => {
    tr.style.display = tr.innerText.toLowerCase().includes(q) ? '' : 'none';
  });
}
</script>
"""

# Иконки для системных страниц (Material Symbols codepoints)
_NOX_ICONS = {
    "nox://newtab/":    ("\uf710", "#ffffff"),  # tab
    "nox://history/":   ("\ue889", "#ffffff"),  # history
    "nox://bookmarks/": ("\ue838", "#ffffff"),  # star
    "nox://downloads/": ("\uf090", "#ffffff"),  # download
}


def _make_nox_icon(glyph: str, color: str) -> QIcon:
    size = 16
    px = QPixmap(size, size)
    px.fill(Qt.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.Antialiasing)
    p.setFont(QFont("Material Symbols Rounded", 11))
    p.setPen(QColor(color))
    p.drawText(px.rect(), Qt.AlignCenter, glyph)
    p.end()
    return QIcon(px)


def _db_path() -> str:
    return str(Path(os.environ.get("APPDATA", Path.home())) / "NoxBrowser" / "nox.db")


def _render_history() -> str:
    rows = []
    try:
        con = sqlite3.connect(_db_path())
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT url, title, visited_at FROM history ORDER BY visited_at DESC LIMIT 500"
        ).fetchall()
        con.close()
    except Exception:
        pass

    items = ""
    for r in rows:
        title = r["title"] or r["url"]
        url = r["url"]
        dt = r["visited_at"][:19].replace("T", " ") if r["visited_at"] else ""
        enc_url = quote(url, safe="")
        items += f"""
        <tr>
          <td>
            <a class="page-link" href="{url}">{title}</a><br>
            <span class="url-text">{url}</span>
          </td>
          <td style="white-space:nowrap;color:#9aa0a6;font-size:12px">{dt}</td>
          <td>
            <button class="del-btn" title="Удалить"
              onclick="location.href='nox://action/history-delete?url={enc_url}'">✕</button>
          </td>
        </tr>"""

    if not items:
        items = '<tr><td colspan="3" class="empty">История пуста</td></tr>'

    return f"""<!doctype html><html><head><meta charset="utf-8"><title>История</title>{_PAGE_STYLE}</head>
<body>
<h1>История</h1>
<div class="toolbar">
  <input class="search-bar" placeholder="Поиск по истории..." oninput="filterTable(this.value)" />
  <button class="btn btn-danger"
    onclick="if(confirm('Очистить всю историю?'))location.href='nox://action/history-clear'">
    Очистить всё
  </button>
</div>
<table id="tbl">
  <thead><tr><th>Страница</th><th>Дата</th><th></th></tr></thead>
  <tbody>{items}</tbody>
</table>
{_FILTER_JS}
</body></html>"""


def _render_bookmarks() -> str:
    rows = []
    try:
        con = sqlite3.connect(_db_path())
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT url, title, folder, created_at FROM bookmarks ORDER BY created_at DESC"
        ).fetchall()
        con.close()
    except Exception:
        pass

    items = ""
    for r in rows:
        title = r["title"] or r["url"]
        url = r["url"]
        folder = r["folder"] or "Без папки"
        enc_url = quote(url, safe="")
        items += f"""
        <tr>
          <td>
            <a class="page-link" href="{url}">{title}</a><br>
            <span class="url-text">{url}</span>
          </td>
          <td style="color:#9aa0a6;font-size:12px">{folder}</td>
          <td>
            <button class="del-btn" title="Удалить"
              onclick="location.href='nox://action/bookmark-delete?url={enc_url}'">✕</button>
          </td>
        </tr>"""

    if not items:
        items = '<tr><td colspan="3" class="empty">Нет закладок</td></tr>'

    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Закладки</title>{_PAGE_STYLE}</head>
<body>
<h1>Закладки</h1>
<div class="toolbar">
  <input class="search-bar" placeholder="Поиск по закладкам..." oninput="filterTable(this.value)" />
</div>
<table id="tbl">
  <thead><tr><th>Страница</th><th>Папка</th><th></th></tr></thead>
  <tbody>{items}</tbody>
</table>
{_FILTER_JS}
</body></html>"""


def _render_downloads() -> str:
    rows = []
    try:
        con = sqlite3.connect(_db_path())
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT url, path, status, bytesReceived, bytesTotal FROM downloads ORDER BY id DESC LIMIT 200"
        ).fetchall()
        con.close()
    except Exception:
        pass

    items = ""
    for r in rows:
        name = Path(r["path"]).name
        url = r["url"]
        status = r["status"]
        total = r["bytesTotal"]
        received = r["bytesReceived"]
        size = f"{received // 1024} / {total // 1024} KB" if total > 0 else ""
        items += f"""
        <tr>
          <td>{name}<br><span class="url-text">{url}</span></td>
          <td style="color:#9aa0a6;font-size:12px">{r["path"]}</td>
          <td style="color:#9aa0a6;font-size:12px;white-space:nowrap">{size}</td>
          <td><span class="status {status}">{status}</span></td>
        </tr>"""

    if not items:
        items = '<tr><td colspan="4" class="empty">Нет загрузок</td></tr>'

    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Загрузки</title>{_PAGE_STYLE}</head>
<body>
<h1>Загрузки</h1>
<div class="toolbar">
  <input class="search-bar" placeholder="Поиск..." oninput="filterTable(this.value)" />
</div>
<table id="tbl">
  <thead><tr><th>Файл</th><th>Путь</th><th>Размер</th><th>Статус</th></tr></thead>
  <tbody>{items}</tbody>
</table>
{_FILTER_JS}
</body></html>"""


class BrowserPage(QWebEnginePage):
    nox_action = Signal(str)
    new_window_requested = Signal(str)

    def acceptNavigationRequest(self, url, nav_type, is_main_frame):  # noqa: N802
        s = url.toString() if isinstance(url, QUrl) else str(url)
        if s.startswith("nox://action/"):
            self.nox_action.emit(s)
            return False
        return True

    def createWindow(self, window_type):  # noqa: N802
        self.new_window_requested.emit("")
        return None

    def javaScriptConsoleMessage(self, level, message, line, source):  # noqa: N802
        return


class BrowserWidget(QWidget):
    url_changed = Signal(str)
    title_changed = Signal(str)
    loading_state_changed = Signal(bool)
    load_progress = Signal(int)
    new_window_requested = Signal(str)
    icon_changed = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._is_new_tab_page = False
        self._nox_page: str | None = None
        self._setup_ui()
        self._connect_signals()

    # ------------------------------------------------------------------
    # Публичный API навигации
    # ------------------------------------------------------------------

    def load_url(self, url: str) -> None:
        if self._is_new_tab_request(url):
            self._load_new_tab_page()
            return
        nox = self._nox_page_type(url)
        if nox:
            self._load_nox_page(nox)
            return
        self._is_new_tab_page = False
        self._nox_page = None
        self._view.setUrl(QUrl(self._normalize_url(url)))

    def go_back(self) -> None:
        self._view.back()

    def go_forward(self) -> None:
        self._view.forward()

    def reload(self, ignore_cache: bool = False) -> None:
        if self._nox_page:
            self._load_nox_page(self._nox_page)
            return
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
        return self._view.isLoading() if hasattr(self._view, "isLoading") else False

    def get_url(self) -> str:
        if self._nox_page:
            return self._nox_page
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

        from core.profile import get_profile
        profile = get_profile()
        page = BrowserPage(profile, self)

        self._view = QWebEngineView(self)
        self._view.setMinimumSize(0, 0)
        self._view.setPage(page)

        settings = self._view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)

        layout.addWidget(self._view)

    def _connect_signals(self) -> None:
        self._view.iconChanged.connect(self._on_icon_changed)
        self._view.urlChanged.connect(self._on_view_url_changed)
        self._view.titleChanged.connect(self.title_changed.emit)
        self._view.loadStarted.connect(lambda: self.loading_state_changed.emit(True))
        self._view.loadFinished.connect(lambda _: self.loading_state_changed.emit(False))
        self._view.loadProgress.connect(self.load_progress.emit)
        self._view.page().new_window_requested.connect(self.new_window_requested.emit)
        self._view.page().nox_action.connect(self._handle_nox_action)

    def _on_icon_changed(self, icon: QIcon) -> None:
        if not self._nox_page:
            self.icon_changed.emit(icon)

    # ------------------------------------------------------------------
    # nox:// страницы и действия
    # ------------------------------------------------------------------

    @staticmethod
    def _nox_page_type(url: str) -> str | None:
        u = (url or "").strip().rstrip("/").lower()
        if u in ("nox://history", "nox://bookmarks", "nox://downloads"):
            return u + "/"
        return None

    def _load_nox_page(self, page_id: str) -> None:
        self._is_new_tab_page = False
        self._nox_page = page_id

        if "history" in page_id:
            html, title = _render_history(), "История"
        elif "bookmarks" in page_id:
            html, title = _render_bookmarks(), "Закладки"
        elif "downloads" in page_id:
            html, title = _render_downloads(), "Загрузки"
        else:
            return

        self._view.setHtml(html)
        self.title_changed.emit(title)
        self.url_changed.emit(page_id)

        nox_icon_data = _NOX_ICONS.get(page_id)
        if nox_icon_data:
            self.icon_changed.emit(_make_nox_icon(*nox_icon_data))

    def _handle_nox_action(self, url: str) -> None:
        parsed = urlparse(url)
        action = parsed.path.lstrip("/")
        params = parse_qs(parsed.query)

        if action == "history-clear":
            try:
                from core.history import HistoryManager
                HistoryManager().clear()
            except Exception as e:
                logger.error("history-clear: %s", e)
            self._load_nox_page("nox://history/")

        elif action == "history-delete":
            target = unquote(params.get("url", [""])[0])
            if target:
                try:
                    from core.history import HistoryManager
                    HistoryManager().delete_by_url(target)
                except Exception as e:
                    logger.error("history-delete: %s", e)
            self._load_nox_page("nox://history/")

        elif action == "bookmark-delete":
            target = unquote(params.get("url", [""])[0])
            if target:
                try:
                    from core.bookmarks import BookmarkManager
                    BookmarkManager().remove(target)
                except Exception as e:
                    logger.error("bookmark-delete: %s", e)
            self._load_nox_page("nox://bookmarks/")

    # ------------------------------------------------------------------
    # Утилиты
    # ------------------------------------------------------------------

    def _load_new_tab_page(self) -> None:
        self._is_new_tab_page = True
        self._nox_page = None
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
        nox_icon_data = _NOX_ICONS.get("nox://newtab/")
        if nox_icon_data:
            self.icon_changed.emit(_make_nox_icon(*nox_icon_data))

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
        if self._nox_page:
            return
        s = url.toString()
        if self._is_new_tab_page and (not s or s == "about:blank" or s.startswith("data:text/html")):
            self.url_changed.emit("nox://newtab/")
            return
        if s and not s.startswith("data:text/html"):
            self._nox_page = None
            self._is_new_tab_page = False
        self.url_changed.emit(s)
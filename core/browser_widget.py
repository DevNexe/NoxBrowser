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

_BASE_STYLE = """
<style>
:root { color-scheme: dark; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: "Segoe UI", Arial, sans-serif; background: #202124; color: #e8eaed; display: flex; height: 100vh; overflow: hidden; }

/* Sidebar */
.sidebar { width: 256px; min-width: 256px; background: #202124; padding: 16px 0; display: flex; flex-direction: column; border-right: 1px solid #2d2e30; }
.sidebar-title { display: flex; align-items: center; gap: 12px; padding: 8px 20px 20px; font-size: 22px; font-weight: 400; color: #e8eaed; }
.sidebar-title svg { width: 28px; height: 28px; }
.sidebar-item { display: flex; align-items: center; gap: 14px; padding: 10px 20px; font-size: 14px; color: #e8eaed; cursor: pointer; border-radius: 0 24px 24px 0; margin-right: 16px; text-decoration: none; }
.sidebar-item:hover { background: #2d2e30; }
.sidebar-item.active { background: #394457; color: #8ab4f8; }
.sidebar-item svg { width: 20px; height: 20px; fill: currentColor; opacity: 0.8; }
.sidebar-sep { height: 1px; background: #2d2e30; margin: 8px 0; }

/* Main */
.main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.topbar { display: flex; align-items: center; gap: 16px; padding: 12px 24px; border-bottom: 1px solid #2d2e30; }
.topbar h1 { font-size: 22px; font-weight: 400; flex: none; }
.search-wrap { flex: 1; max-width: 640px; position: relative; }
.search-wrap input { width: 100%; background: #303134; border: none; border-radius: 24px; padding: 10px 16px 10px 42px; color: #e8eaed; font-size: 14px; outline: none; }
.search-wrap input:focus { background: #3c4043; }
.search-wrap svg { position: absolute; left: 14px; top: 50%; transform: translateY(-50%); width: 18px; height: 18px; fill: #9aa0a6; }
.btn-danger { background: transparent; border: 1px solid #8ab4f8; color: #8ab4f8; border-radius: 20px; padding: 8px 20px; font-size: 13px; cursor: pointer; margin-left: auto; }
.btn-danger:hover { background: rgba(138,180,248,0.1); }

.content { flex: 1; overflow-y: auto; padding: 16px 24px; }

/* History */
.date-group { margin-bottom: 24px; }
.date-label { font-size: 13px; font-weight: 500; color: #9aa0a6; padding: 8px 0 4px; border-bottom: 1px solid #2d2e30; margin-bottom: 4px; }
.hist-row { display: flex; align-items: center; gap: 12px; padding: 8px 12px; border-radius: 8px; cursor: pointer; }
.hist-row:hover { background: #2d2e30; }
.hist-row:hover .del-btn { opacity: 1; }
.hist-time { color: #9aa0a6; font-size: 12px; min-width: 44px; }
.hist-favicon { width: 16px; height: 16px; border-radius: 2px; flex: none; }
.hist-favicon-placeholder { width: 16px; height: 16px; background: #3c4043; border-radius: 2px; flex: none; }
.hist-info { flex: 1; min-width: 0; }
.hist-title { font-size: 13px; color: #e8eaed; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.hist-url { font-size: 12px; color: #9aa0a6; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.del-btn { opacity: 0; background: none; border: none; color: #9aa0a6; cursor: pointer; padding: 4px 8px; border-radius: 4px; font-size: 16px; }
.del-btn:hover { color: #ea4335; background: rgba(234,67,53,0.1); }

/* Bookmarks */
.bm-row { display: flex; align-items: center; gap: 12px; padding: 10px 12px; border-radius: 8px; cursor: pointer; }
.bm-row:hover { background: #2d2e30; }
.bm-row:hover .del-btn { opacity: 1; }
.bm-favicon { width: 20px; height: 20px; border-radius: 3px; flex: none; }
.bm-favicon-placeholder { width: 20px; height: 20px; background: #3c4043; border-radius: 3px; flex: none; display: flex; align-items: center; justify-content: center; font-size: 11px; color: #9aa0a6; }
.bm-info { flex: 1; min-width: 0; }
.bm-title { font-size: 13px; color: #e8eaed; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.bm-url { font-size: 12px; color: #9aa0a6; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.folder-item { display: flex; align-items: center; gap: 10px; padding: 8px 20px; font-size: 13px; color: #e8eaed; cursor: pointer; border-radius: 0 24px 24px 0; margin-right: 16px; }
.folder-item:hover { background: #2d2e30; }
.folder-item.active { background: #394457; color: #8ab4f8; }
.folder-item svg { width: 18px; height: 18px; fill: currentColor; opacity: 0.7; }

/* Downloads */
.dl-group-label { font-size: 13px; color: #9aa0a6; padding: 12px 0 6px; }
.dl-card { background: #2d2e30; border-radius: 12px; padding: 14px 18px; margin-bottom: 8px; display: flex; align-items: center; gap: 14px; }
.dl-card:hover { background: #35363a; }
.dl-icon { width: 40px; height: 40px; background: #3c4043; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 20px; flex: none; }
.dl-info { flex: 1; min-width: 0; }
.dl-name { font-size: 14px; color: #e8eaed; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.dl-name.cancelled { text-decoration: line-through; color: #9aa0a6; }
.dl-meta { font-size: 12px; color: #9aa0a6; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.dl-status { font-size: 11px; padding: 2px 8px; border-radius: 10px; flex: none; }
.dl-status.finished { background: #1e3a2f; color: #34a853; }
.dl-status.in-progress { background: #1a2e4a; color: #8ab4f8; }
.dl-status.interrupted, .dl-status.cancelled { background: #3c2020; color: #ea4335; }
.dl-actions { display: flex; gap: 8px; flex: none; }
.dl-btn { background: none; border: none; color: #9aa0a6; cursor: pointer; padding: 6px; border-radius: 6px; font-size: 18px; }
.dl-btn:hover { background: #3c4043; color: #e8eaed; }

.empty { color: #9aa0a6; text-align: center; padding: 80px 20px; font-size: 15px; }

/* scrollbar */
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #3c4043; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #5f6368; }
</style>
"""

_FILTER_JS = """
<script>
function filterRows(q) {
  q = q.toLowerCase();
  document.querySelectorAll('[data-search]').forEach(el => {
    el.style.display = el.dataset.search.toLowerCase().includes(q) ? '' : 'none';
  });
  document.querySelectorAll('.date-group, .dl-group').forEach(g => {
    const visible = Array.from(g.querySelectorAll('[data-search]')).some(el => el.style.display !== 'none');
    g.style.display = visible ? '' : 'none';
  });
}
</script>
"""

_NOX_ICONS = {
    "nox://newtab/":    ("\uf710", "#ffffff"),
    "nox://history/":   ("\ue889", "#ffffff"),
    "nox://bookmarks/": ("\ue838", "#ffffff"),
    "nox://downloads/": ("\uf090", "#ffffff"),
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

    from datetime import date, datetime as dt
    from collections import defaultdict
    groups = defaultdict(list)
    today = date.today()

    def _fmt_date(d):
        return f"{d.day} {d.strftime('%B %Y г.')}"

    for r in rows:
        try:
            d = dt.fromisoformat(r["visited_at"]).date()
        except Exception:
            d = today
        if d == today:
            label = f"Сегодня — {_fmt_date(today)}"
        elif (today - d).days == 1:
            label = f"Вчера — {_fmt_date(d)}"
        else:
            label = _fmt_date(d)
        groups[label].append(r)

    groups_html = ""
    for label, items in groups.items():
        rows_html = ""
        for r in items:
            title = r["title"] or r["url"]
            url = r["url"]
            try:
                time_str = dt.fromisoformat(r["visited_at"]).strftime("%H:%M")
            except Exception:
                time_str = ""
            enc_url = quote(url, safe="")
            domain = url.split("/")[2] if "://" in url else ""
            rows_html += f"""
<div class="hist-row" data-search="{title} {url}" onclick="location.href='nox://action/navigate?url={enc_url}'">
  <span class="hist-time">{time_str}</span>
  <img class="hist-favicon" src="https://www.google.com/s2/favicons?domain={domain}&sz=16" onerror="this.style.display='none'" />
  <div class="hist-info">
    <div class="hist-title">{title}</div>
    <div class="hist-url">{url}</div>
  </div>
  <button class="del-btn" title="Удалить" onclick="event.stopPropagation();location.href='nox://action/history-delete?url={enc_url}'">✕</button>
</div>"""
        groups_html += f'<div class="date-group"><div class="date-label">{label}</div>{rows_html}</div>'

    if not groups_html:
        groups_html = '<div class="empty">История пуста</div>'

    return f"""<!doctype html><html><head><meta charset="utf-8"><title>История</title>{_BASE_STYLE}</head>
<body>
<div class="sidebar">
  <div class="sidebar-title">
    История
  </div>
  <a class="sidebar-item active" href="nox://history/">
    История NoxBrowser
  </a>
</div>
<div class="main">
  <div class="topbar">
    <div class="search-wrap">
      <svg viewBox="0 0 24 24"><path d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" stroke="#9aa0a6" stroke-width="2" fill="none"/></svg>
      <input type="text" placeholder="История поиска" oninput="filterRows(this.value)" />
    </div>
    <button class="btn-danger" onclick="if(confirm('Очистить всю историю?'))location.href='nox://action/history-clear'">Очистить историю</button>
  </div>
  <div class="content">{groups_html}</div>
</div>
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

    from collections import defaultdict
    folders = defaultdict(list)
    all_items = []
    for r in rows:
        folders[r["folder"] or "Без папки"].append(r)
        all_items.append(r)

    def make_rows(items):
        html = ""
        for r in items:
            title = r["title"] or r["url"]
            url = r["url"]
            enc_url = quote(url, safe="")
            domain = url.split("/")[2] if "://" in url else ""
            html += f"""
<div class="bm-row" data-search="{title} {url}" onclick="location.href='nox://action/navigate?url={enc_url}'">
  <img class="bm-favicon" src="https://www.google.com/s2/favicons?domain={domain}&sz=32" onerror="this.style.display='none'" />
  <div class="bm-info">
    <div class="bm-title">{title}</div>
    <div class="bm-url">{url}</div>
  </div>
  <button class="del-btn" title="Удалить" onclick="event.stopPropagation();location.href='nox://action/bookmark-delete?url={enc_url}'">✕</button>
</div>"""
        return html

    folder_links = ""
    for fname in folders:
        folder_links += f'<div class="folder-item" onclick="filterFolder(\'{fname}\')">' \
                        f'<svg viewBox="0 0 24 24"><path d="M10 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/></svg>{fname}</div>'

    content_html = make_rows(all_items) if all_items else '<div class="empty">Нет закладок</div>'

    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Закладки</title>{_BASE_STYLE}
<style>
.folder-filter {{ display: none; }}
</style>
</head>
<body>
<div class="sidebar">
  <div class="sidebar-title">
    Закладки
  </div>
  <div class="folder-item active" onclick="showAll()">
    <svg viewBox="0 0 24 24"><path d="M10 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/></svg>
    Все закладки
  </div>
  {folder_links}
</div>
<div class="main">
  <div class="topbar">
    <div class="search-wrap">
      <svg viewBox="0 0 24 24"><path d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" stroke="#9aa0a6" stroke-width="2" fill="none"/></svg>
      <input type="text" placeholder="Искать в закладках" oninput="filterRows(this.value)" />
    </div>
  </div>
  <div class="content" id="bm-content">{content_html}</div>
</div>
{_FILTER_JS}
<script>
function showAll() {{
  document.getElementById('bm-content').innerHTML = `{content_html.replace('`','\\`')}`;
  document.querySelectorAll('.folder-item,.sidebar-item').forEach(el=>el.classList.remove('active'));
  event.currentTarget.classList.add('active');
}}
function filterFolder(name) {{
  document.querySelectorAll('.folder-item,.sidebar-item').forEach(el=>el.classList.remove('active'));
  event.currentTarget.classList.add('active');
  document.querySelectorAll('[data-search]').forEach(el => {{
    el.style.display = '';
  }});
}}
</script>
</body></html>"""


def _render_downloads() -> str:
    rows = []
    try:
        con = sqlite3.connect(_db_path())
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT id, url, path, status, bytesReceived, bytesTotal FROM downloads ORDER BY id DESC LIMIT 200"
        ).fetchall()
        con.close()
    except Exception:
        pass

    from datetime import date
    from collections import defaultdict
    # группируем просто по статусу/дате — у нас нет даты в downloads, добавим условно
    # разобьём на "Сегодня" и всё остальное по id (новые сверху)
    items_html = ""
    for r in rows:
        name = Path(r["path"]).name
        status = r["status"]
        total = r["bytesTotal"]
        received = r["bytesReceived"]
        if total > 0:
            size = f"{received // 1024:,} / {total // 1024:,} KB"
        else:
            size = ""
        ext = Path(r["path"]).suffix.lower()
        icon = {"pdf":"📄","zip":"🗜","exe":"⚙","mp4":"🎬","mp3":"🎵","jpg":"🖼","png":"🖼","gif":"🖼"}.get(ext.lstrip("."), "📁")
        name_class = "dl-name cancelled" if status in ("cancelled","interrupted") else "dl-name"
        status_label = {"finished":"Завершено","in-progress":"Загрузка","interrupted":"Прервано","cancelled":"Отменено"}.get(status, status)
        items_html += f"""
<div class="dl-card" data-search="{name} {r['url']}">
  <div class="dl-icon">{icon}</div>
  <div class="dl-info">
    <div class="{name_class}">{name}</div>
    <div class="dl-meta">{size or r['url']}</div>
  </div>
  <span class="dl-status {status}">{status_label}</span>
  <div class="dl-actions">
    <button class="dl-btn" title="Скопировать ссылку" onclick="navigator.clipboard&&navigator.clipboard.writeText('{r['url']}')">🔗</button>
  </div>
</div>"""

    if not items_html:
        items_html = '<div class="empty">Нет загрузок</div>'

    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Загрузки</title>{_BASE_STYLE}</head>
<body>
<div class="sidebar">
  <div class="sidebar-title">
    Загрузки
  </div>
  <a class="sidebar-item active" href="nox://downloads/">
    История загрузок
  </a>
</div>
<div class="main">
  <div class="topbar">
    <div class="search-wrap">
      <svg viewBox="0 0 24 24"><path d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" stroke="#9aa0a6" stroke-width="2" fill="none"/></svg>
      <input type="text" placeholder="Поиск в истории загрузок" oninput="filterRows(this.value)" />
    </div>
  </div>
  <div class="content">{items_html}</div>
</div>
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

        elif action == "navigate":
            target = unquote(params.get("url", [""])[0])
            if target:
                self._nox_page = None
                self._is_new_tab_page = False
                self._view.setUrl(QUrl(self._normalize_url(target)))

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
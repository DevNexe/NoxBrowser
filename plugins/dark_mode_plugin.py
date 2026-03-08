"""
plugins/dark_mode_plugin.py — Тёмный режим
"""

from __future__ import annotations
from typing import TYPE_CHECKING
from plugins.plugin_manager import BasePlugin

if TYPE_CHECKING:
    from ui.main_window import MainWindow

INJECT_JS = """
(function() {
    if (document.getElementById('__nox_dark__')) return;
    var s = document.createElement('style');
    s.id = '__nox_dark__';
    s.textContent = 'html{filter:invert(1) hue-rotate(180deg)} img,video,canvas{filter:invert(1) hue-rotate(180deg)}';
    document.head.appendChild(s);
})();
"""

REMOVE_JS = "var e=document.getElementById('__nox_dark__'); if(e) e.remove();"


class DarkModePlugin(BasePlugin):
    @property
    def plugin_id(self) -> str:
        return "dark_mode"

    @property
    def name(self) -> str:
        return "Тёмный режим"

    def activate(self, browser_window: "MainWindow") -> None:
        self._window = browser_window

    def deactivate(self) -> None:
        if hasattr(self, "_window"):
            try:
                self._window._tab_bar.current_browser_widget.execute_javascript(REMOVE_JS)
            except Exception:
                pass

    def on_page_loaded(self, url: str) -> None:
        if hasattr(self, "_window"):
            try:
                self._window._tab_bar.current_browser_widget.execute_javascript(INJECT_JS)
            except Exception:
                pass

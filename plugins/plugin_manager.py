"""
plugins/plugin_manager.py — Система плагинов
"""

from __future__ import annotations

import importlib.util
import os
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from utils.logger import get_logger

if TYPE_CHECKING:
    from ui.main_window import MainWindow

logger = get_logger(__name__)


class BasePlugin(ABC):
    @property
    @abstractmethod
    def plugin_id(self) -> str: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    def description(self) -> str:
        return ""

    @property
    def version(self) -> str:
        return "1.0.0"

    def activate(self, browser_window: "MainWindow") -> None:
        pass

    def deactivate(self) -> None:
        pass

    def on_url_changed(self, url: str) -> None:
        pass

    def on_page_loaded(self, url: str) -> None:
        pass

    @property
    def is_enabled(self) -> bool:
        return getattr(self, "_enabled", False)

    def _set_enabled(self, value: bool) -> None:
        self._enabled = value


class PluginManager:
    PLUGINS_DIR = os.path.dirname(__file__)

    def __init__(self, browser_window: "MainWindow") -> None:
        self._window = browser_window
        self._plugins: dict[str, BasePlugin] = {}

    def load_all(self) -> None:
        for filename in os.listdir(self.PLUGINS_DIR):
            if filename.endswith(".py") and not filename.startswith("_") and filename != "plugin_manager.py":
                self._load_module(filename[:-3])
        logger.info("Загружено плагинов: %d", len(self._plugins))

    def _load_module(self, module_name: str) -> None:
        try:
            spec = importlib.util.spec_from_file_location(
                f"plugins.{module_name}",
                os.path.join(self.PLUGINS_DIR, f"{module_name}.py"),
            )
            if not spec or not spec.loader:
                return
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore

            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, BasePlugin) and attr is not BasePlugin:
                    inst = attr()
                    self._plugins[inst.plugin_id] = inst
                    inst.activate(self._window)
                    inst._set_enabled(True)
                    logger.info("Плагин: %s v%s", inst.name, inst.version)
        except Exception as exc:
            logger.error("Ошибка плагина %s: %s", module_name, exc)

    def toggle(self, plugin_id: str, enabled: bool) -> None:
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return
        if enabled and not plugin.is_enabled:
            plugin.activate(self._window)
            plugin._set_enabled(True)
        elif not enabled and plugin.is_enabled:
            plugin.deactivate()
            plugin._set_enabled(False)

    def get_all(self) -> list[BasePlugin]:
        return list(self._plugins.values())

    def get(self, plugin_id: str) -> BasePlugin | None:
        return self._plugins.get(plugin_id)

    def notify_url_changed(self, url: str) -> None:
        for p in self._plugins.values():
            if p.is_enabled:
                try:
                    p.on_url_changed(url)
                except Exception as exc:
                    logger.error("Плагин %s: %s", p.plugin_id, exc)

    def notify_page_loaded(self, url: str) -> None:
        for p in self._plugins.values():
            if p.is_enabled:
                try:
                    p.on_page_loaded(url)
                except Exception as exc:
                    logger.error("Плагин %s: %s", p.plugin_id, exc)

"""
core/handlers.py

CEF Handler классы — реализуют коллбэки Chromium.

CEF использует pattern "handler objects": при определённых событиях
(загрузка страницы, изменение заголовка, создание новых окон и т.д.)
CEF вызывает методы соответствующих handler-объектов.

Все вызовы CEF происходят из CEF-потока, поэтому для взаимодействия
с Qt используем сигналы (они thread-safe через Qt::QueuedConnection).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from utils.logger import get_logger

if TYPE_CHECKING:
    from core.browser_widget import BrowserWidget

logger = get_logger(__name__)


class LoadHandler:
    """
    Обрабатывает события загрузки страниц.

    OnLoadStart, OnLoadEnd, OnLoadError — основные события жизненного
    цикла загрузки ресурса.
    """

    def __init__(self, widget: "BrowserWidget") -> None:
        self._widget = widget

    def OnLoadStart(  # noqa: N802
        self,
        browser: Any,
        frame: Any,
        transition_type: int,
    ) -> None:
        """Вызывается при начале загрузки фрейма."""
        if frame.IsMain():
            url = browser.GetUrl()
            logger.debug("Загрузка начата: %s", url)
            self._widget.loading_state_changed.emit(True)
            self._widget.url_changed.emit(url)

    def OnLoadEnd(  # noqa: N802
        self,
        browser: Any,
        frame: Any,
        http_status_code: int,
    ) -> None:
        """Вызывается при завершении загрузки фрейма."""
        if frame.IsMain():
            url = browser.GetUrl()
            logger.debug("Загрузка завершена: %s (HTTP %d)", url, http_status_code)
            self._widget.loading_state_changed.emit(False)
            self._widget.url_changed.emit(url)

    def OnLoadError(  # noqa: N802
        self,
        browser: Any,
        frame: Any,
        error_code: int,
        error_text: str,
        failed_url: str,
    ) -> None:
        """Вызывается при ошибке загрузки."""
        if frame.IsMain():
            logger.warning("Ошибка загрузки %s: %s", failed_url, error_text)
            self._widget.loading_state_changed.emit(False)
            self._widget.load_error.emit(failed_url, error_text)


class DisplayHandler:
    """
    Обрабатывает изменения отображения: заголовок, favicon,
    адресная строка, статус.
    """

    def __init__(self, widget: "BrowserWidget") -> None:
        self._widget = widget

    def OnTitleChange(self, browser: Any, title: str) -> None:  # noqa: N802
        """Вызывается при изменении заголовка страницы."""
        logger.debug("Заголовок изменён: %s", title)
        self._widget.title_changed.emit(title)

    def OnAddressChange(  # noqa: N802
        self,
        browser: Any,
        frame: Any,
        url: str,
    ) -> None:
        """Вызывается при изменении URL (включая редиректы)."""
        if frame.IsMain():
            self._widget.url_changed.emit(url)

    def OnStatusMessage(self, browser: Any, value: str) -> None:  # noqa: N802
        """Вызывается при изменении статусной строки."""
        pass  # Можно подключить статус-бар в будущем


class LifespanHandler:
    """
    Управляет жизненным циклом браузеров: создание/закрытие окон,
    popup-окна.
    """

    def __init__(self, widget: "BrowserWidget") -> None:
        self._widget = widget

    def OnBeforePopup(  # noqa: N802
        self,
        browser: Any,
        frame: Any,
        target_url: str,
        target_frame_name: str,
        target_disposition: Any,
        user_gesture: bool,
        popup_features: Any,
        window_info: Any,
        client: Any,
        browser_settings: Any,
        extra_info: Any,
        no_javascript_access: Any,
    ) -> bool:
        """
        Перехватываем popup-окна и открываем их как новые вкладки.
        Возврат True = отменяем создание popup CEF-ом.
        """
        logger.debug("Запрос popup: %s", target_url)
        self._widget.new_window_requested.emit(target_url)
        return True  # Отменяем нативный popup

    def DoClose(self, browser: Any) -> bool:  # noqa: N802
        """Вызывается при закрытии браузера."""
        return False


class KeyboardHandler:
    """
    Перехватывает клавиатурные события CEF для передачи Qt.
    """

    def __init__(self, widget: "BrowserWidget") -> None:
        self._widget = widget

    def OnPreKeyEvent(  # noqa: N802
        self,
        browser: Any,
        event: Any,
        os_event: Any,
        is_keyboard_shortcut: Any,
    ) -> bool:
        """
        Вызывается до обработки клавиши браузером.
        Возврат True = клавиша обработана, CEF её игнорирует.
        """
        return False  # Позволяем CEF обрабатывать все клавиши


class RequestHandler:
    """
    Перехватывает сетевые запросы.
    Используется для блокировки рекламы, proxy и т.д.
    """

    def __init__(self, widget: "BrowserWidget") -> None:
        self._widget = widget

    def OnBeforeBrowse(  # noqa: N802
        self,
        browser: Any,
        frame: Any,
        request: Any,
        user_gesture: bool,
        is_redirect: bool,
    ) -> bool:
        """
        Вызывается перед навигацией.
        Возврат True = отменить навигацию.
        """
        return False  # Разрешаем все запросы

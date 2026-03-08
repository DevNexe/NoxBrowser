"""
ui/tab_bar.py — Менеджер вкладок
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QTabBar
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QFont, QPainter, QColor
from PySide6.QtCore import QRect

from core.browser_widget import BrowserWidget
from core.history import HistoryManager
from utils.logger import get_logger

logger = get_logger(__name__)


class MaterialIcon:
    # "CLOSE" glyph from Material Symbols often fails to render on some systems,
    # fallback to a simple multiplication sign which is always available.
    CLOSE = "\ue5cd"  # U+2715 heavy multiplication x
    ADD = "\ue145"


class CustomTabBar(QTabBar):
    """Custom QTabBar with Material Symbols Rounded close button."""
    
    close_clicked = Signal(int)  # Сигнал для нажатия на кнопку закрытия
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._close_font = QFont("Material Symbols Rounded", 18)
        self._close_font.setBold(True)
        self._close_rects = {}
        # спрячем штатный элемент
        self.setStyleSheet("""
            QTabBar::close-button {
                image: none;
                width: 0px;
                height: 0px;
            }
        """)
        
    def tabSizeHint(self, index: int) -> QSize:
        size = super().tabSizeHint(index)
        # Добавляем место для кастомной кнопки закрытия (24px)
        size.setWidth(size.width() + 28)
        return size
    
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setFont(self._close_font)
        self._close_rects.clear()
        for i in range(self.count()):
            # не рисуем если кто-то поставил собственный виджет по правой стороне
            if self.tabButton(i, QTabBar.RightSide) is not None:
                continue
            tab_rect = self.tabRect(i)
            # расширим область для клика и чтобы было место под фон
            btn_size = 24
            close_button_rect = QRect(
                tab_rect.right() - btn_size - 4,
                tab_rect.top() + (tab_rect.height() - btn_size) // 2,
                btn_size,
                btn_size,
            )
            self._close_rects[i] = close_button_rect

            # рисуем фон (чтобы кнопка была видимой на любом фоне)
            painter.save()
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(60, 64, 67, 150))  # тёмно-серый полупрозрачный
            painter.drawEllipse(close_button_rect)
            painter.restore()

            # выбираем цвет и рисуем символ
            if i in getattr(self, '_hover_tab', []):
                painter.setPen(QColor("#ea4335"))
            else:
                painter.setPen(QColor("#9aa0a6"))
            painter.drawText(close_button_rect, Qt.AlignCenter, MaterialIcon.CLOSE)
        painter.end()
    
    def mousePressEvent(self, event):
        for tab_index, rect in self._close_rects.items():
            if rect.contains(event.pos()):
                self.close_clicked.emit(tab_index)
                self.tabCloseRequested.emit(tab_index)
                return
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        self._hover_tab = []
        for tab_index, rect in self._close_rects.items():
            if rect.contains(event.pos()):
                self._hover_tab = [tab_index]
                self.update()
                break
        super().mouseMoveEvent(event)


class TabBar(QWidget):
    current_url_changed = Signal(str)
    current_title_changed = Signal(str)
    loading_state_changed = Signal(bool)
    load_progress = Signal(int)
    new_tab_requested = Signal(str)
    tabs_updated = Signal()

    def __init__(
        self,
        history: HistoryManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._history = history
        self._setup_ui()

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------

    @property
    def current_browser_widget(self) -> BrowserWidget:
        widget = self._tabs.currentWidget()
        if isinstance(widget, BrowserWidget):
            return widget
        raise RuntimeError("Нет активной вкладки")

    def add_tab(self, url: str = "", title: str = "Новая вкладка") -> BrowserWidget:
        bw = BrowserWidget(parent=self)

        bw.url_changed.connect(lambda u, w=bw: self._on_url_changed(w, u))
        bw.title_changed.connect(lambda t, w=bw: self._on_title_changed(w, t))
        bw.loading_state_changed.connect(lambda l, w=bw: self._on_loading(w, l))
        bw.load_progress.connect(lambda p, w=bw: self._on_progress(w, p))
        bw.new_window_requested.connect(lambda u: self.new_tab_requested.emit(u))

        idx = self._tabs.addTab(bw, title)
        self._tabs.setTabsClosable(False)  # штатная кнопка скрыта, мы рисуем свою
        self._tabs.setCurrentIndex(idx)

        bw.load_url(url or "")

        self.tabs_updated.emit()
        return bw

    def close_current_tab(self) -> None:
        self._close_tab(self._tabs.currentIndex())

    def close_tab_at(self, index: int) -> None:
        self._close_tab(index)

    def close_all_tabs(self) -> None:
        while self._tabs.count() > 0:
            widget = self._tabs.widget(0)
            self._tabs.removeTab(0)
            if widget:
                widget.deleteLater()
        self.tabs_updated.emit()

    def set_current_index(self, index: int) -> None:
        if 0 <= index < self._tabs.count():
            self._tabs.setCurrentIndex(index)

    def current_index(self) -> int:
        return self._tabs.currentIndex()

    def tab_count(self) -> int:
        return self._tabs.count()

    def tab_title(self, index: int) -> str:
        if 0 <= index < self._tabs.count():
            return self._tabs.tabText(index)
        return ""

    def set_tab_header_visible(self, visible: bool) -> None:
        self._tabs.tabBar().setVisible(visible)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tabs = QTabWidget(self)
        # Отключаем встроенные кнопки QTabWidget ДО добавления табов
        self._tabs.setTabsClosable(False)
        # Заменяем стандартный tab bar на кастомный с Material Symbols иконкой
        custom_tab_bar = CustomTabBar(self)
        custom_tab_bar.close_clicked.connect(self._close_tab)
        self._tabs.setTabBar(custom_tab_bar)
        self._tabs.setMovable(True)
        self._tabs.setDocumentMode(True)
        # tabCloseRequested не используется, наши кнопки сами вызывают _close_tab
        self._tabs.currentChanged.connect(self._on_tab_changed)

        layout.addWidget(self._tabs)
        self.add_tab()

    # ------------------------------------------------------------------
    # Слоты
    # ------------------------------------------------------------------

    def _close_tab(self, index: int) -> None:
        if self._tabs.count() <= 1:
            self.current_browser_widget.load_url("about:blank")
            self.tabs_updated.emit()
            return
        widget = self._tabs.widget(index)
        self._tabs.removeTab(index)
        if widget:
            widget.deleteLater()
        self.tabs_updated.emit()



    def _on_tab_changed(self, index: int) -> None:
        widget = self._tabs.widget(index)
        if isinstance(widget, BrowserWidget):
            self.current_url_changed.emit(widget.get_url())
            self.current_title_changed.emit(widget.get_title())
        self.tabs_updated.emit()

    def _on_url_changed(self, widget: BrowserWidget, url: str) -> None:
        if self._is_current(widget):
            self.current_url_changed.emit(url)
        self._history.add(url, widget.get_title())

    def _on_title_changed(self, widget: BrowserWidget, title: str) -> None:
        idx = self._tabs.indexOf(widget)
        if idx >= 0:
            short = (title[:20] + "…") if len(title) > 20 else title
            self._tabs.setTabText(idx, short or "Загрузка…")
            self._tabs.setTabToolTip(idx, title)
        if self._is_current(widget):
            self.current_title_changed.emit(title)
        self.tabs_updated.emit()

    def _on_loading(self, widget: BrowserWidget, loading: bool) -> None:
        if self._is_current(widget):
            self.loading_state_changed.emit(loading)

    def _on_progress(self, widget: BrowserWidget, progress: int) -> None:
        if self._is_current(widget):
            self.load_progress.emit(progress)

    def _is_current(self, widget: BrowserWidget) -> bool:
        try:
            return widget is self.current_browser_widget
        except RuntimeError:
            return False

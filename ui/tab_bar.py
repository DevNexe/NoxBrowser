from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QTabBar, QStyle, QStylePainter, QStyleOptionTab, QApplication
from PySide6.QtCore import Signal, Qt, QSize, QRect, QTimer, QPoint
from PySide6.QtGui import QFont, QPainter, QColor, QIcon, QCursor

from core.browser_widget import BrowserWidget
from core.history import HistoryManager
from utils.logger import get_logger

logger = get_logger(__name__)

DETACH_THRESHOLD = 30

_ADD_TAB_TEXT = "＋"


class MaterialIcon:
    CLOSE = "\ue5cd"
    ADD = "\ue145"


class CustomTabBar(QTabBar):
    close_clicked = Signal(int)
    tab_detach_requested = Signal(int, QPoint)
    new_tab_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._close_font = QFont("Material Symbols Rounded", 12)
        self._close_font.setBold(True)
        self._close_rects = {}
        self._icons: dict[int, QIcon] = {}
        self._drag_tab_index: int = -1
        self._has_add_tab: bool = False
        self._hover_index: int = -1
        self.setMouseTracking(True)
        self.setStyleSheet("""
            QTabBar::close-button {
                image: none;
                width: 0px;
                height: 0px;
            }
        """)
        self.setElideMode(Qt.ElideRight)
        self.setLayoutDirection(Qt.LeftToRight)

    def _add_index(self) -> int:
        return self.count() - 1 if self._has_add_tab else -1

    def _real_count(self) -> int:
        return self.count() - 1 if self._has_add_tab else self.count()

    def install_add_tab(self) -> None:
        if self._has_add_tab:
            return
        self._has_add_tab = True
        self.addTab("")
        idx = self.count() - 1
        self.setTabEnabled(idx, True)

    def _ensure_add_tab_last(self) -> None:
        if not self._has_add_tab:
            return
        last = self.count() - 1
        add_idx = self._add_index()
        if add_idx != last:
            self.moveTab(add_idx, last)

    def set_icon(self, index: int, icon: QIcon) -> None:
        self._icons[index] = icon
        self.update()

    def clear_icons(self) -> None:
        self._icons.clear()

    def shift_icons_after_close(self, closed_index: int) -> None:
        new_icons = {}
        for k, v in self._icons.items():
            if k < closed_index:
                new_icons[k] = v
            elif k > closed_index:
                new_icons[k - 1] = v
        self._icons = new_icons

    def tabSizeHint(self, index: int) -> QSize:
        if self._has_add_tab and index == self._add_index():
            return QSize(36, super().tabSizeHint(index).height())
        size = super().tabSizeHint(index)
        real = max(1, self._real_count())
        available = max(1, self.width() - 8 - 36)
        target = min(240, max(36, available // real))
        size.setWidth(target)
        return size

    def paintEvent(self, event):
        painter = QStylePainter(self)
        add_idx_ = self._add_index()
        for i in range(self.count()):
            if self._has_add_tab and i == add_idx_:
                continue  # фон + рисуем сами ниже
            opt = QStyleOptionTab()
            self.initStyleOption(opt, i)
            opt.text = ""
            opt.icon = QIcon()
            painter.drawControl(QStyle.CE_TabBarTabShape, opt)
        painter.end()

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        self._close_rects.clear()

        add_idx = self._add_index()
        current = self.currentIndex()

        for i in range(self.count()):
            tab_rect = self.tabRect(i)

            # фейковая вкладка +
            if self._has_add_tab and i == add_idx:
                last_real = add_idx - 1
                # линия скрыта если: последняя реальная вкладка активна или под курсором
                if last_real >= 0 and current != last_real and self._hover_index != last_real:
                    p.setPen(QColor("#3c4043"))
                    p.drawLine(tab_rect.left(), tab_rect.top() + 8, tab_rect.left(), tab_rect.bottom() - 8)
                is_hover = (self._hover_index == i)
                p.setPen(Qt.NoPen)
                p.setBrush(QColor("#2d2e30") if is_hover else QColor("#202124"))
                r = tab_rect.adjusted(4, 4, -4, -4)  # margin: 4px
                p.drawRoundedRect(r, 8, 8)  # border-radius: 8px
                p.setPen(QColor("#e8eaed") if is_hover else QColor("#9aa0a6"))
                p.setFont(QFont("Material Symbols Rounded", 14))
                p.drawText(tab_rect, Qt.AlignCenter, MaterialIcon.ADD)
                continue

            # разделитель между соседними неактивными вкладками
            next_i = i + 1
            is_add_next = self._has_add_tab and next_i == add_idx
            if (
                i != current
                and next_i < self.count()
                and next_i != current
                and not is_add_next
                and self._hover_index != i
                and self._hover_index != next_i
            ):
                sep_x = tab_rect.right()
                sep_top = tab_rect.top() + 8
                sep_bottom = tab_rect.bottom() - 8
                p.setPen(QColor("#3c4043"))
                p.drawLine(sep_x, sep_top, sep_x, sep_bottom)

            btn_size = 16
            close_button_rect = QRect(
                tab_rect.right() - btn_size - 8,
                tab_rect.top() + (tab_rect.height() - btn_size) // 2,
                btn_size,
                btn_size,
            )
            self._close_rects[i] = close_button_rect

            icon_size = 16
            icon_x = tab_rect.left() + 8
            icon_y = tab_rect.top() + (tab_rect.height() - icon_size) // 2
            icon_rect = QRect(icon_x, icon_y, icon_size, icon_size)
            icon = self._icons.get(i)
            if icon and not icon.isNull():
                icon.paint(p, icon_rect)
                text_left = icon_x + icon_size + 6
            else:
                text_left = icon_x

            text_rect = QRect(
                text_left,
                tab_rect.top(),
                close_button_rect.left() - text_left - 4,
                tab_rect.height(),
            )
            color = "#e8eaed" if i == current else "#9aa0a6"
            p.setPen(QColor(color))
            p.setFont(QFont("Segoe UI", 9))
            p.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, self.tabText(i))

            p.setFont(self._close_font)
            p.save()
            if i in getattr(self, '_hover_tab', []):
                # фон-пилюля за крестиком
                p.setPen(Qt.NoPen)
                p.setBrush(QColor("#3c4043"))
                cr = close_button_rect.adjusted(-3, -3, 3, 3)
                p.drawRoundedRect(cr, 4, 4)
            p.setPen(QColor("#e8eaed") if i in getattr(self, '_hover_tab', []) else QColor("#9aa0a6"))
            p.drawText(close_button_rect, Qt.AlignCenter, MaterialIcon.CLOSE)
            p.restore()

        p.end()

    def mousePressEvent(self, event):
        add_idx = self._add_index()

        if self._has_add_tab and add_idx >= 0:
            if self.tabRect(add_idx).contains(event.pos()):
                self.new_tab_clicked.emit()
                return

        for tab_index, rect in self._close_rects.items():
            if rect.contains(event.pos()):
                self.close_clicked.emit(tab_index)
                self.tabCloseRequested.emit(tab_index)
                return

        if event.button() == Qt.LeftButton:
            clicked = self.tabAt(event.pos())
            if self._has_add_tab and clicked == add_idx:
                return
            self._drag_tab_index = clicked

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self._hover_tab = []
        for tab_index, rect in self._close_rects.items():
            if rect.contains(event.pos()):
                self._hover_tab = [tab_index]
                break
        self._hover_index = self.tabAt(event.pos())
        self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hover_index = -1
        self._hover_tab = []
        self.update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._drag_tab_index >= 0:
            global_pos = event.globalPosition().toPoint()
            local_pos = self.mapFromGlobal(global_pos)
            if (
                local_pos.y() < -DETACH_THRESHOLD
                or local_pos.y() > self.height() + DETACH_THRESHOLD
                or local_pos.x() < -50
                or local_pos.x() > self.width() + 50
            ):
                idx = self._drag_tab_index
                self._drag_tab_index = -1
                self.tab_detach_requested.emit(idx, global_pos)
                return

        self._drag_tab_index = -1
        super().mouseReleaseEvent(event)

    def tabInserted(self, index: int) -> None:
        super().tabInserted(index)
        QTimer.singleShot(0, self._ensure_add_tab_last)

    def tabRemoved(self, index: int) -> None:
        super().tabRemoved(index)
        QTimer.singleShot(0, self._ensure_add_tab_last)


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
        self._external_tab_bars: list[CustomTabBar] = []
        self._widget_icons: dict[BrowserWidget, QIcon] = {}
        self._syncing_move = False
        self._setup_ui()

    def register_external_tab_bar(self, tab_bar: CustomTabBar) -> None:
        if tab_bar not in self._external_tab_bars:
            self._external_tab_bars.append(tab_bar)

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
        bw.icon_changed.connect(lambda icon, w=bw: self._on_icon_changed(w, icon))

        idx = self._tabs.addTab(bw, title)
        self._tabs.setTabsClosable(False)
        self._tabs.setCurrentIndex(idx)

        bw.load_url(url or "")

        self.tabs_updated.emit()
        return bw

    def detach_tab(self, index: int, global_pos: QPoint) -> None:
        if self._tabs.count() <= 1:
            return

        widget = self._tabs.widget(index)
        if not isinstance(widget, BrowserWidget):
            return

        url = widget.get_url()

        self._tabs.removeTab(index)
        self._widget_icons.pop(widget, None)
        widget.deleteLater()
        self._sync_all_icons()
        self.tabs_updated.emit()

        from ui.main_window import MainWindow
        new_window = MainWindow()
        new_window.resize(1280, 800)
        new_window.move(global_pos - QPoint(640, 20))
        new_window.show()
        new_window.open_url(url)

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

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tabs = QTabWidget(self)
        self._tabs.setTabsClosable(False)
        self._custom_tab_bar = CustomTabBar(self)
        self._custom_tab_bar.close_clicked.connect(self._close_tab)
        self._custom_tab_bar.tabMoved.connect(self._on_internal_tab_moved)
        self._custom_tab_bar.tab_detach_requested.connect(self.detach_tab)
        self._custom_tab_bar.new_tab_clicked.connect(lambda: self.new_tab_requested.emit(""))
        self._tabs.setTabBar(self._custom_tab_bar)
        self._tabs.setMovable(True)
        self._tabs.setDocumentMode(True)
        self._tabs.currentChanged.connect(self._on_tab_changed)

        layout.addWidget(self._tabs)
        self.add_tab()

    def _on_internal_tab_moved(self, from_index: int, to_index: int) -> None:
        if self._syncing_move:
            return
        QTimer.singleShot(0, self._sync_all_icons)

    def _sync_all_icons(self) -> None:
        self._custom_tab_bar.clear_icons()
        for tb in self._external_tab_bars:
            tb.clear_icons()
        for i in range(self._tabs.count()):
            w = self._tabs.widget(i)
            if isinstance(w, BrowserWidget):
                icon = self._widget_icons.get(w)
                if icon and not icon.isNull():
                    self._custom_tab_bar.set_icon(i, icon)
                    for tb in self._external_tab_bars:
                        tb.set_icon(i, icon)

    def _close_tab(self, index: int) -> None:
        if self._tabs.count() <= 1:
            self.window().close()
            return
        widget = self._tabs.widget(index)
        self._tabs.removeTab(index)
        if isinstance(widget, BrowserWidget):
            self._widget_icons.pop(widget, None)
            widget.deleteLater()
        self._sync_all_icons()
        self.tabs_updated.emit()

    def _on_icon_changed(self, widget: BrowserWidget, icon: QIcon) -> None:
        if not icon.isNull():
            self._widget_icons[widget] = icon
            self._sync_all_icons()

    def _on_tab_changed(self, index: int) -> None:
        if self._custom_tab_bar._has_add_tab and index == self._custom_tab_bar._add_index():
            return
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
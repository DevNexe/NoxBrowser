"""
main.py - Точка входа NoxBrowser
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# GPU compatibility mode for legacy adapters (prefer ANGLE D3D11 + GLES2).
_required_chromium_flags = [
    "--use-gl=angle",
    "--use-angle=d3d11",
    "--disable-es3-gl-context",
    "--disable-vulkan",
    "--ignore-gpu-blocklist",
]
_blocked_exact = {
    "--disable-gpu",
    "--disable-gpu-compositing",
    "--use-angle=d3d9",
    "--use-angle=d3d10",
}
_existing_flags = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "").strip()
_flags_set = set()
if _existing_flags:
    for _flag in _existing_flags.split():
        if _flag in _blocked_exact:
            continue
        if _flag.startswith("--use-angle="):
            continue
        _flags_set.add(_flag)

for _flag in _required_chromium_flags:
    _flags_set.add(_flag)

os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = " ".join(sorted(_flags_set))
os.environ.pop("QTWEBENGINE_DISABLE_GPU", None)

APP_STYLE = """
* { font-family: "Segoe UI", Arial, sans-serif; font-size: 13px; }
QMainWindow, QWidget { background-color: #202124; color: #e8eaed; }
QWidget#toolbar { background-color: #35363a; border-bottom: 1px solid #5f6368; }
QWidget#urlWrap { background-color: #202124; border-radius: 20px; border: 2px solid transparent; min-height: 36px; max-height: 36px; }
QWidget#urlWrap:hover { border: 2px solid #5f6368; }
QPushButton#navBtn { font-family: "Material Symbols Rounded"; }
QLineEdit#urlBar { background: transparent; border: none; color: #e8eaed; font-size: 14px; selection-background-color: #3c4043; }
QPushButton#lockBtn { border: none; background: transparent; color: #9aa0a6; font-size: 12px; font-family: "Material Symbols Rounded"; min-width: 22px; max-width: 22px; min-height: 22px; max-height: 22px; border-radius: 11px; }
QPushButton#bookmarkBtn { border: none; background: transparent; font-size: 16px; font-family: "Material Symbols Rounded"; color: #9aa0a6; min-width: 28px; max-width: 28px; min-height: 28px; max-height: 28px; border-radius: 14px; }
QPushButton#bookmarkBtn:hover { background: #3c4043; color: #e8eaed; }
QPushButton { border: none; border-radius: 16px; background: transparent; color: #e8eaed; font-size: 16px; min-width: 32px; min-height: 32px; max-width: 32px; max-height: 32px; }
QPushButton:hover { background-color: #3c4043; }
QPushButton:pressed { background-color: #5f6368; }
QPushButton:disabled { color: #5f6368; }
QTabBar { background: #202124; }
QTabBar::close-button { image: none; width: 0px; height: 0px; margin: 0px; }
QTabBar::tab { background: #2d2e30; color: #9aa0a6; padding: 6px 12px 6px 12px; padding-right: 40px; min-width: 100px; max-width: 220px; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 2px; font-size: 12px; }
QTabWidget::pane { border: none; }
QTabWidget QTabBar::close-button { image: none; width: 0px; height: 0px; margin: 0px; }
QTabBar::tab:selected { background: #35363a; color: #e8eaed; }
QTabBar::tab:hover:!selected { background: #3c4043; color: #e8eaed; }
QProgressBar#progressBar { background: #3c4043; border: none; max-height: 3px; }
QProgressBar#progressBar::chunk { background: #8ab4f8; }
QPushButton#downloadBtn { border: none; background: transparent; font-size: 16px; color: #9aa0a6; }
QPushButton#downloadBtn:hover { background: #3c4043; border-radius: 8px; }
QStatusBar { background: #35363a; color: #9aa0a6; font-size: 11px; border-top: 1px solid #5f6368; }
QMenu { background: #292a2d; border: 1px solid #5f6368; border-radius: 8px; padding: 4px 0; color: #e8eaed; font-size: 13px; min-width: 220px; }
QMenu::item { padding: 8px 20px; border-radius: 4px; }
QMenu::item:selected { background: #3c4043; }
QMenu::separator { height: 1px; background: #5f6368; margin: 4px 8px; }
QDialog { background: #292a2d; color: #e8eaed; }
QListWidget { background: #202124; border: 1px solid #5f6368; border-radius: 4px; color: #e8eaed; }
QListWidget::item:selected { background: #3c4043; }
QListWidget::item:hover { background: #2d2e30; }
QLineEdit { background: #202124; border: 1px solid #5f6368; border-radius: 4px; color: #e8eaed; padding: 4px 8px; }
QLineEdit:focus { border: 1px solid #8ab4f8; }
QLabel { color: #e8eaed; background: transparent; }
QScrollBar:vertical { background: #2d2e30; width: 8px; border-radius: 4px; }
QScrollBar::handle:vertical { background: #5f6368; border-radius: 4px; min-height: 20px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""


def main() -> int:
    # ВСЕ Qt импорты строго внутри main() — до этой точки Qt не инициализирован
    from PySide6.QtCore import qInstallMessageHandler
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtWidgets import QApplication

    def _qt_message_filter(msg_type, context, message):
        # Known noisy warnings when combining frameless + Aero Snap on Windows.
        if message.startswith("QPainter::") and (
            "Paint device returned engine == 0" in message
            or "Painter not active" in message
        ):
            return
        print(message)

    qInstallMessageHandler(_qt_message_filter)
    app = QApplication(sys.argv)
    material_font = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "MaterialSymbolsRounded.ttf")
    if os.path.exists(material_font):
        QFontDatabase.addApplicationFont(material_font)
    app.setApplicationName("NoxBrowser")
    app.setApplicationVersion("1.0.0")
    app.setStyleSheet(APP_STYLE)

    from ui.main_window import MainWindow
    window = MainWindow()
    window.show()
    window.open_url("")

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

<div align="center">

# NoxBrowser

**A modular, Chromium-powered desktop browser built entirely in Python**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/PySide6-QtWebEngine-41CD52?style=flat-square&logo=qt&logoColor=white)](https://doc.qt.io/qtforpython/)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D4?style=flat-square&logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

*A full-featured browser you can actually read, understand, and extend.*

</div>

---

## Overview

**NoxBrowser** is a desktop web browser written in pure Python on top of **PySide6 + QtWebEngine** (Chromium). It ships with a custom frameless window, a Chrome-style tab bar integrated into the title bar, persistent history/bookmarks/downloads via SQLite, and a plugin system — all wrapped in a clean dark UI.

```
┌──────────────────────────────────────────────────────────────────┐
│  [Tab 1: Google]  [Tab 2: GitHub]  [+]          —  □  ✕         │
├──────────────────────────────────────────────────────────────────┤
│  ← → ↻  │  🔒 google.com                        ☆  ⬇  ⋮        │
├══════════════════════════════════════════════════════════════════╡
│                                                                  │
│                      [ Chromium WebView ]                        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Features

### Browsing
- Full Chromium engine via **QtWebEngine** — JavaScript, cookies, local storage, plugins
- Smart URL bar: auto-detects searches vs URLs, strips `https://` for display
- Back / Forward / Reload / Stop with loading progress bar
- Zoom in/out/reset and keyboard shortcuts throughout

### Tabs
- Tabs live **in the title bar** — no wasted vertical space
- Drag-and-drop tab reordering
- Tab **detach** — drag a tab out to spawn a new independent window
- Favicons per tab, truncated titles with tooltips

### History, Bookmarks & Downloads
- All data stored in **SQLite** at `%APPDATA%/NoxBrowser/nox.db`
- Built-in pages: `nox://history/`, `nox://bookmarks/`, `nox://downloads/`
- Chrome-style sidebar layout with live search and per-item delete
- Download manager with file picker, progress tracking, and status badges

### Window
- Fully **frameless window** (`qframelesswindow`) with a custom title bar
- Native Windows **Snap** support (Aero Snap, maximize/restore via Win32)
- DWM integration — dark title bar, rounded corners, no border
- Custom resize grips on all 8 edges/corners

### Plugin System
- `BasePlugin` ABC with lifecycle hooks: `activate`, `deactivate`, `on_url_changed`, `on_page_loaded`
- Auto-discovers `.py` files in `plugins/` at startup — no registration needed
- Ships with a **Dark Mode** plugin (CSS `invert + hue-rotate` injection)

---

## Installation

### Prerequisites

```bash
pip install PySide6 qframelesswindow
```

> A `Material Symbols Rounded` font file is expected at `fonts/MaterialSymbolsRounded.ttf` for icon rendering in the toolbar and tab bar.

### Clone & Run

```bash
git clone https://github.com/devnexe-alt/NoxBrowser.git
cd NoxBrowser
python main.py
```

---

## Project Structure

```
NoxBrowser/
├── main.py                        # Entry point, app stylesheet, Chromium flags
│
├── core/
│   ├── browser_widget.py          # BrowserWidget + BrowserPage (QWebEngineView wrapper)
│   ├── history.py                 # HistoryManager — SQLite, 10k entry cap, skip-list
│   ├── bookmarks.py               # BookmarkManager — SQLite, folder support
│   ├── downloads.py               # DownloadManager — QWebEngineDownloadRequest handler
│   ├── profile.py                 # Persistent QWebEngineProfile (cookies, cache)
│   └── handlers.py                # Legacy CEF-style handler stubs
│
├── ui/
│   ├── main_window.py             # MainWindow (FramelessWindow + NoxTitleBar + TabBar)
│   ├── navigation_bar.py          # NavigationBar (URL bar, nav buttons, hamburger menu)
│   ├── tab_bar.py                 # TabBar widget + CustomTabBar (fully custom paint)
│   ├── devtools_window.py         # DevTools window (F12)
│   ├── downloads_dialog.py        # Downloads dialog
│   └── dialogs/
│       ├── history_dialog.py      # History dialog
│       └── bookmarks_dialog.py    # Bookmarks dialog
│
├── plugins/
│   ├── plugin_manager.py          # PluginManager + BasePlugin ABC
│   └── dark_mode_plugin.py        # Dark Mode plugin (CSS injection)
│
├── utils/
│   └── logger.py                  # Centralized logging (stdout + rotating file)
│
└── fonts/
    └── MaterialSymbolsRounded.ttf # Icon font for UI glyphs
```

---

## Built-in Pages

| URL | Content |
|---|---|
| `nox://newtab/` | New tab with Google search bar |
| `nox://history/` | Browsing history grouped by date |
| `nox://bookmarks/` | Bookmarks with folder sidebar |
| `nox://downloads/` | Download history with status badges |

---

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+L` | Focus URL bar |
| `Ctrl+T` | New tab |
| `Ctrl+W` | Close current tab |
| `Ctrl+H` | Open history |
| `Ctrl+D` | Bookmark current page |
| `Ctrl+Shift+B` | Open bookmarks |
| `Ctrl+J` | Open downloads |
| `F5` | Reload page |
| `F12` | Developer tools |
| `Ctrl++` / `Ctrl+-` / `Ctrl+0` | Zoom in / out / reset |
| `Ctrl+Q` | Quit |

---

## Writing a Plugin

Drop a `.py` file into the `plugins/` folder — NoxBrowser will auto-load it on next startup:

```python
from plugins.plugin_manager import BasePlugin

class MyPlugin(BasePlugin):
    @property
    def plugin_id(self) -> str:
        return "my_plugin"

    @property
    def name(self) -> str:
        return "My Plugin"

    def activate(self, browser_window) -> None:
        self._window = browser_window

    def on_page_loaded(self, url: str) -> None:
        self._window._tab_bar.current_browser_widget.execute_javascript(
            "console.log('Hello from MyPlugin');"
        )
```

---

## Data Storage

All user data lives at `%APPDATA%\NoxBrowser\`:

| Path | Contents |
|---|---|
| `nox.db` | SQLite database: history, bookmarks, downloads |
| `profile/` | WebEngine persistent storage (cookies, IndexedDB, etc.) |
| `cache/` | HTTP disk cache |

---

## Requirements

- **OS:** Windows (Win32 APIs used for Snap/DWM; other platforms work without those features)
- **Python:** 3.10+
- **Dependencies:** `PySide6`, `qframelesswindow`

---

<div align="center">

Made by [DevNexe](https://github.com/devnexe)

</div>

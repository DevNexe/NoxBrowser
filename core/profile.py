from __future__ import annotations
import os
from pathlib import Path
from PySide6.QtWebEngineCore import QWebEngineProfile

_profile: QWebEngineProfile | None = None

def get_profile() -> QWebEngineProfile:
    global _profile
    if _profile is None:
        app_data = Path(os.environ.get("APPDATA", Path.home())) / "NoxBrowser"
        _profile = QWebEngineProfile("NoxBrowser")
        _profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )
        _profile.setPersistentStoragePath(str(app_data / "profile"))
        _profile.setCachePath(str(app_data / "cache"))
        _profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
    return _profile
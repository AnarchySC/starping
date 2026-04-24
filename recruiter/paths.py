"""Cross-platform user-data directory resolution.

Installed on Windows, StarPing lives in Program Files (read-only for the
user) but needs a writable location for the SQLite DB, the Playwright
browser profile, and logs. This module returns that location.

Dev convention: if a `data/` directory exists next to this repo (i.e. the
developer is running from source), use it. That preserves the older
working-tree behavior for local work.

Production (packaged .exe):
  Windows:  %APPDATA%\\StarPing
  macOS:    ~/Library/Application Support/StarPing
  Linux:    $XDG_DATA_HOME/starping  (fallback ~/.local/share/starping)
"""
import os
import sys
from pathlib import Path

APP_NAME = "StarPing"


def _dev_data_dir() -> Path | None:
    """If running from a source checkout that has a `data/` folder alongside
    the code, prefer it. This lets local development keep its existing DB."""
    # Walk up from this file to find the project root (where data/ might live)
    here = Path(__file__).resolve().parent.parent
    candidate = here / "data"
    if candidate.exists() and not getattr(sys, "frozen", False):
        return candidate
    return None


def _platform_data_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / APP_NAME
        return Path.home() / "AppData" / "Roaming" / APP_NAME
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        base = os.environ.get("XDG_DATA_HOME")
        if base:
            return Path(base) / APP_NAME.lower()
        return Path.home() / ".local" / "share" / APP_NAME.lower()


def data_dir() -> Path:
    """Return the writable user-data directory, creating it if needed."""
    dev = _dev_data_dir()
    target = dev if dev is not None else _platform_data_dir()
    target.mkdir(parents=True, exist_ok=True)
    return target


def db_path() -> Path:
    return data_dir() / "recruiter.sqlite3"


def browser_profile_dir() -> Path:
    p = data_dir() / "browser"
    p.mkdir(parents=True, exist_ok=True)
    return p


def logs_dir() -> Path:
    p = data_dir() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p

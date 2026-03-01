"""Persistent display configuration.

Saves per-display settings (most importantly user-assigned labels) to a
JSON file in the OS-appropriate app-data directory.

Screen keys use the format  "name|WxH|@(x,y)"  which is stable across
reboots as long as the monitor appears at the same logical position on
the desktop.  If the user rearranges their monitors the key changes and
the label falls back to the default, but the old entry is preserved in
the file so renaming the same monitor twice doesn't lose the first label.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QStandardPaths


# ────────────────────────────────────────────────────────────────── helpers

def _config_dir() -> Path:
    """Return (and create if needed) the platform app-data directory."""
    locs = QStandardPaths.standardLocations(
        QStandardPaths.StandardLocation.AppDataLocation
    )
    base = Path(locs[0]) if locs else Path.home() / ".vlcshow"
    base.mkdir(parents=True, exist_ok=True)
    return base


def make_screen_key(name: str, width: int, height: int, x: int, y: int) -> str:
    """Build a stable identifier for a physical display.

    Example: ``"DELL U2723D|2560x1440|@(1920,0)"``
    """
    return f"{name}|{width}x{height}|@({x},{y})"


# ──────────────────────────────────────────────────────────── DisplayConfig

class DisplayConfig:
    """Load / save per-display settings keyed by :func:`make_screen_key`.

    Usage::

        cfg = DisplayConfig()
        label = cfg.get_label(key) or "My Output"
        cfg.set_label(key, "Main Stage")   # persisted immediately
    """

    _FILENAME = "display_config.json"

    def __init__(self) -> None:
        self._path = _config_dir() / self._FILENAME
        self._data: dict = self._load()

    # ----------------------------------------------------------------- I/O

    def _load(self) -> dict:
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {"outputs": {}}

    def save(self) -> None:
        self._path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ----------------------------------------------------------------- API

    def get_label(self, key: str) -> Optional[str]:
        """Return the user-assigned label for *key*, or ``None`` if not set."""
        entry = self._data.get("outputs", {}).get(key, {})
        label = entry.get("label")
        return label if label else None  # treat empty string as unset

    def set_label(self, key: str, label: str) -> None:
        """Persist a new label for *key* immediately."""
        entry = self._data.setdefault("outputs", {}).setdefault(key, {})
        entry["label"] = label.strip()
        entry["last_seen"] = str(date.today())
        self.save()

    def touch(self, key: str, default_label: Optional[str] = None) -> None:
        """Record that this display was seen today without changing its label.

        If *default_label* is given and no label is stored yet, save it.
        """
        entry = self._data.setdefault("outputs", {}).setdefault(key, {})
        entry["last_seen"] = str(date.today())
        if default_label and not entry.get("label"):
            entry["label"] = default_label
        # No save() here — avoid I/O churn on every startup scan.
        # Label-setting paths call save() explicitly.

    def flush(self) -> None:
        """Write buffered touch() calls to disk."""
        self.save()

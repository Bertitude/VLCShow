"""Display / monitor discovery.

Uses Qt's QScreen API so we get cross-platform screen enumeration with no
OS-specific code.  In Phase 2 this module will also own the mapping between
ScreenInfo objects and active ProjectionWindow instances.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QRect


@dataclass
class ScreenInfo:
    """Lightweight description of one physical display."""

    index:      int
    name:       str
    geometry:   QRect
    is_primary: bool

    @property
    def width(self) -> int:
        return self.geometry.width()

    @property
    def height(self) -> int:
        return self.geometry.height()

    @property
    def short_label(self) -> str:
        """e.g. 'Screen 0 (primary)  1920×1080'"""
        tag = " (primary)" if self.is_primary else ""
        return f"Screen {self.index}{tag}  {self.width}×{self.height}"

    def __str__(self) -> str:
        origin = f"@({self.geometry.x()},{self.geometry.y()})"
        return f"Screen {self.index}: {self.name}  {self.width}×{self.height} {origin}"


class DisplayManager:
    """Static helpers for querying connected displays via QApplication."""

    @staticmethod
    def get_screens() -> List[ScreenInfo]:
        """Return a ScreenInfo list for every connected display."""
        app = QApplication.instance()
        if app is None:
            return []
        primary = app.primaryScreen()
        result: List[ScreenInfo] = []
        for i, screen in enumerate(app.screens()):
            result.append(
                ScreenInfo(
                    index=i,
                    name=screen.name() or f"Screen {i}",
                    geometry=screen.geometry(),
                    is_primary=(screen is primary),
                )
            )
        return result

    @staticmethod
    def get_primary() -> Optional[ScreenInfo]:
        screens = DisplayManager.get_screens()
        for s in screens:
            if s.is_primary:
                return s
        return screens[0] if screens else None

    @staticmethod
    def get_secondary_screens() -> List[ScreenInfo]:
        return [s for s in DisplayManager.get_screens() if not s.is_primary]

    @staticmethod
    def count() -> int:
        return len(DisplayManager.get_screens())

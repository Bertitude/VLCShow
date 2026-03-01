"""ProjectionWindow — fullscreen output window for a secondary display.

Phase 2 — NOT YET IMPLEMENTED.

This module will provide a borderless fullscreen QWindow that:
  • Is positioned on a specific QScreen (projector / secondary monitor).
  • Hosts a VideoWidget whose native handle is given to a VLCPlayer instance.
  • Accepts signals from MainWindow to show/hide, toggle fullscreen, and
    route a loaded media file to the correct player instance.

Placeholder class is defined so imports don't fail during Phase 1.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QScreen

if TYPE_CHECKING:
    from vlcshow.core.player import VLCPlayer
    from vlcshow.core.display_manager import ScreenInfo


class ProjectionWindow(QWidget):
    """Fullscreen output window targeted at a specific display.

    Instantiate one per output channel (secondary screen / projector).

    Args:
        screen_info:  The target display.
        player:       The VLCPlayer instance whose output will be routed here.
        parent:       Optional Qt parent.
    """

    def __init__(
        self,
        screen_info: "ScreenInfo",
        player: "VLCPlayer",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._screen_info = screen_info
        self._player = player

        # Phase 2 TODO: move window to target screen and embed VideoWidget
        self.setWindowTitle(f"VLCShow — {screen_info.short_label}")
        self.setStyleSheet("background: #000;")

        layout = QVBoxLayout(self)
        placeholder = QLabel(
            f"[Phase 2] Projection output\n{screen_info.short_label}"
        )
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: #30363d; font-size: 16px;")
        layout.addWidget(placeholder)

    def go_fullscreen(self) -> None:
        """Move to target screen and enter fullscreen mode."""
        # Phase 2 implementation:
        #   screen = QApplication.screens()[self._screen_info.index]
        #   self.windowHandle().setScreen(screen)
        #   self.setGeometry(screen.geometry())
        #   self.showFullScreen()
        raise NotImplementedError("Phase 2")

    def exit_fullscreen(self) -> None:
        """Leave fullscreen and restore windowed mode."""
        raise NotImplementedError("Phase 2")

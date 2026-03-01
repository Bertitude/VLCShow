"""ProjectionWindow — fullscreen output window on a specific display.

One instance per active output channel.  It holds a VideoWidget whose
native handle is given to the channel's VLCPlayer, so VLC renders
directly into it on the target monitor.

Fullscreen flow
───────────────
1.  show_on_screen()   – open as a normal window on the target display
2.  go_fullscreen()    – move & resize to fill the target screen
3.  exit_fullscreen()  – return to windowed mode
4.  toggle_fullscreen() – flip between the two

Pressing Escape while fullscreen also calls exit_fullscreen().
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QApplication
from PyQt6.QtCore import Qt

from vlcshow.ui.video_widget import VideoWidget

if TYPE_CHECKING:
    from vlcshow.core.player import VLCPlayer
    from vlcshow.core.display_manager import ScreenInfo


class ProjectionWindow(QWidget):
    """Borderless output window that renders on a specific display."""

    def __init__(
        self,
        screen_info: "ScreenInfo",
        player: "VLCPlayer",
        parent: Optional[QWidget] = None,
    ) -> None:
        # Window flag: top-level window without a taskbar entry
        super().__init__(parent, Qt.WindowType.Window)
        self._screen_info = screen_info
        self._player = player
        self._is_fullscreen = False
        self._player_attached = False

        self.setWindowTitle(screen_info.short_label)
        self.setStyleSheet("background: #000000;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._video = VideoWidget()
        self._video.set_media_active(True)   # hide "no media" placeholder
        layout.addWidget(self._video)

    # ────────────────────────────────────────────────────────── public API

    def show_on_screen(self) -> None:
        """Open as a standard window positioned on the target display."""
        self._is_fullscreen = False
        geo = self._screen_info.geometry
        # Offset slightly from top-left so it's clearly a separate window
        self.setGeometry(geo.x() + 40, geo.y() + 40, 960, 540)
        self.show()
        self._attach_player()

    def go_fullscreen(self) -> None:
        """Fill the target display with borderless fullscreen."""
        app = QApplication.instance()
        screens = app.screens()
        idx = self._screen_info.index

        # Ensure the native window handle exists
        if not self.isVisible():
            self.show()

        # Move to the correct screen before entering fullscreen
        if idx < len(screens):
            handle = self.windowHandle()
            if handle:
                handle.setScreen(screens[idx])
            self.setGeometry(screens[idx].geometry())

        self.showFullScreen()
        self._is_fullscreen = True
        self._attach_player()

    def exit_fullscreen(self) -> None:
        """Leave fullscreen and restore a normal windowed view."""
        geo = self._screen_info.geometry
        self.showNormal()
        self.setGeometry(geo.x() + 40, geo.y() + 40, 960, 540)
        self._is_fullscreen = False

    def toggle_fullscreen(self) -> None:
        if self._is_fullscreen:
            self.exit_fullscreen()
        else:
            self.go_fullscreen()

    @property
    def is_fullscreen(self) -> bool:
        return self._is_fullscreen

    # ─────────────────────────────────────────────────── snapshot (preview)

    def take_snapshot(self, path: str) -> bool:
        """Delegate to the player's snapshot API."""
        return self._player.take_snapshot(path)

    # ──────────────────────────────────────────────────────────── internals

    def _attach_player(self) -> None:
        """Attach the VLC player to the VideoWidget (safe to call repeatedly)."""
        if not self._player_attached:
            self._player.attach_to_widget(self._video)
            self._player_attached = True

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape and self._is_fullscreen:
            self.exit_fullscreen()
        super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        self._player.stop()
        event.accept()

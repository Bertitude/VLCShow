"""OutputCard — per-output channel card widget.

Phase 2 — NOT YET IMPLEMENTED.

Each OutputCard will represent one active output channel and display:
  • Channel label  (e.g. "Output 1 — Screen 1  1920×1080")
  • Live thumbnail preview (updated every ~1–2 s via VLC snapshot)
  • Mini transport controls (play/pause/stop for that channel)
  • Fullscreen toggle button
  • A "route media" button to assign the currently loaded file to this output

Cards are arranged in a scrollable column in the right-hand panel of
MainWindow (Phase 2 layout).
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

if TYPE_CHECKING:
    from vlcshow.core.player import VLCPlayer
    from vlcshow.core.display_manager import ScreenInfo


class OutputCard(QFrame):
    """Card widget representing one projection output channel.

    Args:
        screen_info:  Display this channel targets.
        player:       Dedicated VLCPlayer for this channel.
        channel_idx:  Zero-based channel number (for labelling).
        parent:       Optional Qt parent.
    """

    def __init__(
        self,
        screen_info: "ScreenInfo",
        player: "VLCPlayer",
        channel_idx: int = 0,
        parent: Optional[QFrame] = None,
    ) -> None:
        super().__init__(parent)
        self._screen_info = screen_info
        self._player = player
        self._channel_idx = channel_idx

        self.setObjectName("OutputCard")
        self.setStyleSheet(
            "#OutputCard {"
            "  background: #161b22;"
            "  border: 1px solid #30363d;"
            "  border-radius: 8px;"
            "}"
        )
        self.setMinimumHeight(220)

        layout = QVBoxLayout(self)

        # ── Header ────────────────────────────────────────────────────
        title = QLabel(
            f"Output {channel_idx + 1}  —  {screen_info.short_label}"
        )
        title.setStyleSheet(
            "font-weight: 700; font-size: 13px; color: #58a6ff;"
            "padding: 4px 0;"
        )
        layout.addWidget(title)

        # ── Thumbnail placeholder ─────────────────────────────────────
        self._thumb = QLabel("[Phase 2] Thumbnail preview")
        self._thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumb.setMinimumHeight(120)
        self._thumb.setStyleSheet(
            "background: #000; color: #30363d; font-size: 13px;"
            "border-radius: 4px;"
        )
        layout.addWidget(self._thumb, stretch=1)

        # Phase 2 TODO: add mini controls, fullscreen button, route button

    def update_thumbnail(self) -> None:
        """Refresh the thumbnail from the player's latest snapshot."""
        # Phase 2 implementation:
        #   path = capture_snapshot(self._player)
        #   pixmap = QPixmap(path).scaled(...)
        #   self._thumb.setPixmap(pixmap)
        raise NotImplementedError("Phase 2")

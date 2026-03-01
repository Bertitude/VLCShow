"""PreviewPanel — scrollable column of OutputCard widgets.

Phase 2 — NOT YET IMPLEMENTED.

The PreviewPanel will sit on the right side of MainWindow and display
one OutputCard per active output channel.  A QTimer fires every 1–2 s
to trigger thumbnail refreshes on each card.

Thumbnail capture strategy (to be implemented in Phase 2):
  Option A — VLC snapshot API
      media_player.video_take_snapshot(0, path, 0, 0)
      Load the saved file into a QPixmap and display it.
      Pro: zero-dependency, works across platforms.
      Con: brief disk I/O; tempfile cleanup required.

  Option B — Qt screen capture
      QScreen.grabWindow(projection_window.winId())
      Pro: no disk I/O, always in sync with actual output.
      Con: may fail on Wayland or when window is behind other windows.

  Recommended: Option A (VLC snapshot) with a shared temp directory,
  cleaned up on app exit.
"""

from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
from PyQt6.QtCore import Qt

if TYPE_CHECKING:
    from vlcshow.ui.output_card import OutputCard


class PreviewPanel(QScrollArea):
    """Scrollable list of per-output OutputCard widgets.

    Phase 2 TODO:
      • Accept a list of (ScreenInfo, VLCPlayer) pairs.
      • Instantiate one OutputCard per pair.
      • Start a QTimer(interval=1500) that calls update_thumbnail() on
        each card.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setMinimumWidth(280)

        container = QWidget()
        self._layout = QVBoxLayout(container)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(10)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        placeholder = QLabel(
            "Output channels\nappear here\n\n[Phase 2]"
        )
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet(
            "color: #30363d; font-size: 14px; padding: 24px;"
        )
        self._layout.addWidget(placeholder)

        self.setWidget(container)
        self.setStyleSheet(
            "background: #0d1117; border-left: 1px solid #21262d;"
        )

    def add_card(self, card: "OutputCard") -> None:
        """Append an OutputCard to the panel."""
        self._layout.addWidget(card)

    def clear_cards(self) -> None:
        """Remove all cards (e.g. when re-scanning displays)."""
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

"""VideoWidget — the black QFrame that hosts VLC's native render surface.

VLC draws directly into this widget's native OS window handle, bypassing
Qt's paint system entirely.  We therefore:
  • Force a solid black background so the idle state looks clean.
  • Show a centred placeholder label when no media is loaded.
  • Expose set_media_active() so MainWindow can hide the placeholder.
"""

from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor


class VideoWidget(QFrame):
    """Native render surface for VLC video output."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(640, 360)
        self._force_black_background()
        self._setup_placeholder()

    # ------------------------------------------------------------------ setup

    def _force_black_background(self) -> None:
        """Make the widget paint black so it looks correct in idle state."""
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#000000"))
        self.setPalette(palette)
        self.setAutoFillBackground(True)
        # Belt-and-braces: also via stylesheet (covers child widgets)
        self.setStyleSheet("background: #000000;")

    def _setup_placeholder(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._placeholder = QLabel(
            "No media loaded\n\nOpen a video file to begin"
        )
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet(
            "color: #30363d;"
            "font-size: 18px;"
            "background: transparent;"
            "line-height: 1.6;"
        )
        layout.addWidget(self._placeholder)

    # ------------------------------------------------------------------- API

    def set_media_active(self, active: bool) -> None:
        """Show or hide the 'no media' placeholder."""
        self._placeholder.setVisible(not active)

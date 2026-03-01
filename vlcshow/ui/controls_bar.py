"""ControlsBar — transport controls widget.

Layout (three rows):

  ┌────────────────────────────────────────────────────────┐
  │ ░░░░░░░░░░░░░░░░░░▓▓▓▓▓▓▓▓▓▓▓▓▓▒░░░░░░░░░░░░░░░░░░░░  │  seek bar
  ├────────────────────────────────────────────────────────┤
  │  📂 Open   ⏹ Stop   ▶ Play/Pause            0:00/5:23 │  transport
  ├────────────────────────────────────────────────────────┤
  │  🔊  ════════▒══  (volume)                             │  volume
  └────────────────────────────────────────────────────────┘

All buttons meet the 52 px touch-target minimum.

Signals emitted
---------------
open_file_requested   – user tapped Open
play_pause_requested  – user tapped Play/Pause
stop_requested        – user tapped Stop
seek_requested(float) – user finished dragging/clicking seek bar (0–1)
volume_changed(int)   – user moved volume slider (0–100)

Public update slots
-------------------
set_playing(bool)     – flip Play ↔ Pause label
set_position(float)   – move seek bar without triggering seek_requested
set_time(int)         – update current time display (ms)
set_duration(int)     – update total time display (ms) + enable controls
set_controls_enabled(bool) – enable/disable transport controls
get_volume() -> int   – read current volume slider value
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QSlider,
)
from PyQt6.QtCore import Qt, pyqtSignal

from vlcshow.utils.time_format import format_ms


# ────────────────────────────────────────────────────────────────────────────
# SeekBar
# ────────────────────────────────────────────────────────────────────────────

class SeekBar(QSlider):
    """Horizontal seek bar with click-to-seek (not just drag-handle) support.

    Emits ``seek_requested(float)`` in [0, 1] only on user interaction,
    never when ``set_position`` is called programmatically.
    """

    seek_requested = pyqtSignal(float)

    _STEPS = 10_000  # internal resolution

    def __init__(self, parent=None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setRange(0, self._STEPS)
        self.setSingleStep(50)
        self.setPageStep(500)
        self.setFixedHeight(40)
        self._user_seeking = False

    # ── input events ──────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._user_seeking = True
            self.setValue(self._x_to_value(event.pos().x()))
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._user_seeking:
            self.setValue(self._x_to_value(event.pos().x()))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._user_seeking:
            self._user_seeking = False
            self.seek_requested.emit(self.value() / self._STEPS)
        super().mouseReleaseEvent(event)

    def _x_to_value(self, x: int) -> int:
        """Convert a pixel x-coordinate to a slider value."""
        # Approximate: account for ~11 px left/right margins from handle radius
        margin = 11
        effective = max(1, self.width() - 2 * margin)
        ratio = max(0.0, min(1.0, (x - margin) / effective))
        return int(ratio * self._STEPS)

    # ── programmatic update ───────────────────────────────────────────────

    def set_position(self, pos: float) -> None:
        """Update the bar from a player poll without emitting seek_requested."""
        if not self._user_seeking:
            self.blockSignals(True)
            self.setValue(int(pos * self._STEPS))
            self.blockSignals(False)


# ────────────────────────────────────────────────────────────────────────────
# ControlsBar
# ────────────────────────────────────────────────────────────────────────────

class ControlsBar(QWidget):
    """Full transport-controls panel."""

    open_file_requested  = pyqtSignal()
    play_pause_requested = pyqtSignal()
    stop_requested       = pyqtSignal()
    seek_requested       = pyqtSignal(float)
    volume_changed       = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._duration_ms: int = 0
        self._setup_ui()
        # Disable transport controls until media is loaded
        self.set_controls_enabled(False)

    # ─────────────────────────────────────────────────────────── setup

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 10, 16, 12)
        root.setSpacing(10)

        # ── Row 1: seek bar ─────────────────────────────────────────
        self._seek = SeekBar()
        self._seek.seek_requested.connect(self.seek_requested)
        root.addWidget(self._seek)

        # ── Row 2: transport buttons + time label ────────────────────
        row2 = QHBoxLayout()
        row2.setSpacing(8)

        self._btn_open  = _make_button("📂  Open",        accent=True)
        self._btn_stop  = _make_button("⏹  Stop")
        self._btn_play  = _make_button("▶  Play",         min_width=110)

        self._time_label = QLabel("0:00 / –:––")
        self._time_label.setStyleSheet(
            "font-size: 15px;"
            "color: #8b949e;"
            "min-width: 130px;"
            "background: transparent;"
        )
        self._time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        row2.addWidget(self._btn_open)
        row2.addWidget(self._btn_stop)
        row2.addWidget(self._btn_play)
        row2.addStretch(1)
        row2.addWidget(self._time_label)
        root.addLayout(row2)

        # ── Row 3: volume ────────────────────────────────────────────
        row3 = QHBoxLayout()
        row3.setSpacing(10)

        vol_icon = QLabel("🔊")
        vol_icon.setStyleSheet("font-size: 20px; background: transparent;")
        vol_icon.setFixedWidth(28)

        self._vol_slider = QSlider(Qt.Orientation.Horizontal)
        self._vol_slider.setRange(0, 100)
        self._vol_slider.setValue(80)
        self._vol_slider.setFixedHeight(40)
        self._vol_slider.setMaximumWidth(200)
        self._vol_slider.setToolTip("Volume")
        self._vol_slider.valueChanged.connect(self.volume_changed)

        self._vol_pct = QLabel("80 %")
        self._vol_pct.setStyleSheet("color: #8b949e; min-width: 46px; background: transparent;")
        self._vol_slider.valueChanged.connect(
            lambda v: self._vol_pct.setText(f"{v} %")
        )

        row3.addWidget(vol_icon)
        row3.addWidget(self._vol_slider)
        row3.addWidget(self._vol_pct)
        row3.addStretch(1)
        root.addLayout(row3)

        # ── Wire buttons ─────────────────────────────────────────────
        self._btn_open.clicked.connect(self.open_file_requested)
        self._btn_stop.clicked.connect(self.stop_requested)
        self._btn_play.clicked.connect(self.play_pause_requested)

    # ─────────────────────────────────────────────────────────── public slots

    def set_controls_enabled(self, enabled: bool) -> None:
        self._btn_stop.setEnabled(enabled)
        self._btn_play.setEnabled(enabled)
        self._seek.setEnabled(enabled)

    def set_playing(self, playing: bool) -> None:
        self._btn_play.setText("⏸  Pause" if playing else "▶  Play")

    def set_position(self, pos: float) -> None:
        self._seek.set_position(pos)

    def set_time(self, ms: int) -> None:
        total = format_ms(self._duration_ms) if self._duration_ms > 0 else "–:––"
        self._time_label.setText(f"{format_ms(ms)} / {total}")

    def set_duration(self, ms: int) -> None:
        self._duration_ms = ms
        self.set_time(0)
        self.set_controls_enabled(True)

    def get_volume(self) -> int:
        return self._vol_slider.value()


# ────────────────────────────────────────────────────────────────────────────
# Helper
# ────────────────────────────────────────────────────────────────────────────

def _make_button(
    text: str,
    accent: bool = False,
    min_width: int = 90,
) -> QPushButton:
    btn = QPushButton(text)
    btn.setMinimumWidth(min_width)
    # Accent style is handled by the global stylesheet via a dynamic property
    if accent:
        btn.setProperty("accent", True)
        btn.style().unpolish(btn)
        btn.style().polish(btn)
    return btn

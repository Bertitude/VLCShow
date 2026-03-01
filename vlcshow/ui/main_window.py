"""MainWindow — primary control surface for VLCShow.

Phase 1 layout
──────────────
┌──────────────────────────────────────────────────────────────┐
│  🎬 VLCShow                          Screen 0 (primary) 1920×1080 … │  header
├──────────────────────────────────────────────────────────────┤
│                                                              │
│                    VideoWidget                               │  expands
│              (black / VLC render surface)                    │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  seek bar                                                    │
│  📂 Open   ⏹ Stop   ▶ Play/Pause               0:00 / 5:23  │  controls
│  🔊 ══════▒══  80 %                                          │
├──────────────────────────────────────────────────────────────┤
│  Status: Ready — open a video file to begin                  │  status bar
└──────────────────────────────────────────────────────────────┘

Phase 2 will add an output-management panel on the right side and a
preview thumbnail strip.
"""

from __future__ import annotations

import os
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QLabel, QFileDialog, QStatusBar,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor

from vlcshow.core.player import VLCPlayer
from vlcshow.core.display_manager import DisplayManager
from vlcshow.ui.video_widget import VideoWidget
from vlcshow.ui.controls_bar import ControlsBar


# Video file types shown in the file-open dialog
_VIDEO_FILTER = (
    "Video files "
    "(*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm "
    "*.m4v *.mpg *.mpeg *.ts *.mts *.vob *.ogv);;"
    "All files (*)"
)


class MainWindow(QMainWindow):
    """Main application window (Phase 1 — single-output player)."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("VLCShow")
        self.resize(1200, 720)
        self.setMinimumSize(900, 580)

        self._player = VLCPlayer(self)
        self._player_attached = False

        self._setup_palette()
        self._setup_ui()
        self._connect_signals()

        # Initialise volume from the slider's default value
        self._player.volume = self._controls.get_volume()

    # ──────────────────────────────────────────────────────────── setup

    def _setup_palette(self) -> None:
        """Apply the dark colour palette to the window and its children."""
        p = QPalette()
        p.setColor(QPalette.ColorRole.Window,          QColor("#0d1117"))
        p.setColor(QPalette.ColorRole.WindowText,      QColor("#e6edf3"))
        p.setColor(QPalette.ColorRole.Base,            QColor("#161b22"))
        p.setColor(QPalette.ColorRole.AlternateBase,   QColor("#21262d"))
        p.setColor(QPalette.ColorRole.Text,            QColor("#e6edf3"))
        p.setColor(QPalette.ColorRole.BrightText,      QColor("#ffffff"))
        p.setColor(QPalette.ColorRole.Button,          QColor("#21262d"))
        p.setColor(QPalette.ColorRole.ButtonText,      QColor("#e6edf3"))
        p.setColor(QPalette.ColorRole.Highlight,       QColor("#1f6feb"))
        p.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        p.setColor(QPalette.ColorRole.ToolTipBase,     QColor("#161b22"))
        p.setColor(QPalette.ColorRole.ToolTipText,     QColor("#e6edf3"))
        self.setPalette(p)

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header bar ────────────────────────────────────────────────
        self._header = QLabel("🎬  VLCShow")
        self._header.setStyleSheet(
            "background: #0d1117;"
            "color: #58a6ff;"
            "font-size: 17px;"
            "font-weight: 700;"
            "padding: 10px 16px;"
            "border-bottom: 1px solid #21262d;"
        )
        layout.addWidget(self._header)

        # ── Video surface ─────────────────────────────────────────────
        self._video = VideoWidget()
        layout.addWidget(self._video, stretch=1)

        # ── Transport controls ────────────────────────────────────────
        self._controls = ControlsBar()
        self._controls.setStyleSheet(
            "background: #161b22;"
            "border-top: 1px solid #21262d;"
        )
        layout.addWidget(self._controls)

        # ── Status bar ────────────────────────────────────────────────
        status = QStatusBar()
        status.setStyleSheet(
            "background: #0d1117;"
            "color: #8b949e;"
            "font-size: 12px;"
        )
        self.setStatusBar(status)
        self._status = status
        self._status.showMessage("Ready — open a video file to begin")

    def _connect_signals(self) -> None:
        c = self._controls

        # UI → player
        c.open_file_requested.connect(self._open_file)
        c.play_pause_requested.connect(self._player.toggle_play_pause)
        c.stop_requested.connect(self._on_stop)
        c.seek_requested.connect(self._player.seek)
        c.volume_changed.connect(lambda v: setattr(self._player, "volume", v))

        # Player → UI
        p = self._player
        p.position_changed.connect(c.set_position)
        p.time_changed.connect(c.set_time)
        p.duration_changed.connect(c.set_duration)
        p.state_changed.connect(self._on_state_changed)
        p.media_loaded.connect(self._on_media_loaded)

    # ──────────────────────────────────────────────── Qt lifecycle hooks

    def showEvent(self, event) -> None:
        """Attach VLC to the video widget the first time the window appears."""
        super().showEvent(event)
        if not self._player_attached:
            self._player.attach_to_widget(self._video)
            self._player_attached = True
            self._refresh_screen_info()

    def closeEvent(self, event) -> None:
        self._player.cleanup()
        event.accept()

    # ──────────────────────────────────────────────────────────── slots

    def _open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Video File",
            "",
            _VIDEO_FILTER,
        )
        if path:
            self._player.load(path)
            self._player.play()

    def _on_stop(self) -> None:
        self._player.stop()
        self._controls.set_position(0.0)
        self._controls.set_time(0)

    def _on_state_changed(self, state: str) -> None:
        self._controls.set_playing(state == "playing")
        messages = {
            "playing": "Playing",
            "paused":  "Paused",
            "stopped": "Stopped",
            "ended":   "Playback complete",
            "error":   "Error during playback",
        }
        self._status.showMessage(messages.get(state, "Ready"))

    def _on_media_loaded(self, path: str) -> None:
        name = os.path.basename(path)
        self.setWindowTitle(f"VLCShow — {name}")
        self._status.showMessage(f"Loaded: {name}")
        self._video.set_media_active(True)

    # ─────────────────────────────────────────────────────────── helpers

    def _refresh_screen_info(self) -> None:
        screens = DisplayManager.get_screens()
        if not screens:
            return
        parts = []
        for s in screens:
            tag = "  ★" if s.is_primary else ""
            parts.append(f"Screen {s.index}{tag}  {s.width}×{s.height}")
        self._header.setText("🎬  VLCShow        " + "   |   ".join(parts))
        self._status.showMessage(
            f"{len(screens)} display(s) detected — ready"
        )

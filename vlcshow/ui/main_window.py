"""MainWindow — primary control surface for VLCShow.

Phase 3 layout
──────────────
┌──────────────────────────────────────────────────────────────────────────┐
│  🎬 VLCShow   Screen 0 ★ 1920×1080  |  Screen 1 1920×1080               │  header
├──────────────────────────────────────┬───────────────────────────────────┤
│                                      │  Outputs                          │
│          VideoWidget                 │  ┌─────────────────────────────┐  │
│      (source / cue preview)          │  │  ● Main Stage    1920×1080  │  │
│                                      │  │  [thumbnail]                │  │
├──────────────────────────────────────┤  │  ▶  ⏸  ⏹          ⛶ Full  │  │
│  ControlsBar (source player)         │  │  📂 Send current media here  │  │
├──────────────────────────────────────┤  └─────────────────────────────┘  │
│  PlaylistPanel (drag-reorderable)    │  ＋ Add Output                    │
└──────────────────────────────────────┴───────────────────────────────────┘

The source (left) player is a local cue/preview player.  Loading a file
here does NOT automatically send it to outputs — the operator clicks
"Send current media here" on each OutputCard to route it explicitly.
"""

from __future__ import annotations

import os
from typing import Optional, List

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFileDialog, QStatusBar, QSplitter,
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QPalette, QColor

from vlcshow.core.display_manager import DisplayManager, ScreenInfo
from vlcshow.core.output_manager import OutputManager
from vlcshow.core.player import VLCPlayer
from vlcshow.ui.output_card import OutputCard
from vlcshow.ui.playlist_panel import PlaylistPanel
from vlcshow.ui.preview_panel import PreviewPanel
from vlcshow.ui.projection_window import ProjectionWindow
from vlcshow.ui.video_widget import VideoWidget
from vlcshow.ui.controls_bar import ControlsBar
from vlcshow.workers.thumbnail_worker import ThumbnailWorkerThread


_VIDEO_FILTER = (
    "Video files "
    "(*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm "
    "*.m4v *.mpg *.mpeg *.ts *.mts *.vob *.ogv);;"
    "All files (*)"
)


def _sidebar_urls() -> List[QUrl]:
    """Build the list of sidebar shortcuts for the non-native file dialog.

    Includes Qt's standard locations (Home, Desktop, Documents, Movies,
    Music, Downloads) plus the OneDrive root if the env-var is set.
    """
    from PyQt6.QtCore import QStandardPaths

    locations = [
        QStandardPaths.StandardLocation.HomeLocation,
        QStandardPaths.StandardLocation.DesktopLocation,
        QStandardPaths.StandardLocation.DocumentsLocation,
        QStandardPaths.StandardLocation.MoviesLocation,
        QStandardPaths.StandardLocation.MusicLocation,
        QStandardPaths.StandardLocation.DownloadLocation,
    ]

    urls: List[QUrl] = []
    seen: set[str] = set()

    def _add(path: str) -> None:
        if not path:
            return
        norm = os.path.normcase(os.path.abspath(path))
        if norm not in seen and os.path.isdir(path):
            seen.add(norm)
            urls.append(QUrl.fromLocalFile(path))

    for loc in locations:
        paths = QStandardPaths.standardLocations(loc)
        for p in paths:
            _add(p)

    # OneDrive (Windows env-var; may point to Personal or Business folder)
    for env_key in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        _add(os.environ.get(env_key, ""))

    return urls


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("VLCShow")
        self.resize(1440, 860)
        self.setMinimumSize(960, 640)

        # Source / cue player (drives the left VideoWidget)
        self._player = VLCPlayer(self)
        self._player_attached = False

        # Multi-output manager
        self._output_manager = OutputManager()

        # Tracks the most recently loaded file path so OutputCards can
        # "receive" it with one button press
        self._current_media_path: Optional[str] = None

        # Background thumbnail extractor
        self._thumb_worker = ThumbnailWorkerThread(self)
        self._thumb_worker.result_ready.connect(self._on_thumbnail_ready)
        self._thumb_worker.start()

        self._setup_palette()
        self._setup_ui()
        self._connect_signals()
        self._player.volume = self._controls.get_volume()

    # ────────────────────────────────────────────────────────── setup

    def _setup_palette(self) -> None:
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
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────
        self._header = QLabel("🎬  VLCShow")
        self._header.setStyleSheet(
            "background: #0d1117; color: #58a6ff;"
            "font-size: 17px; font-weight: 700;"
            "padding: 10px 16px;"
            "border-bottom: 1px solid #21262d;"
        )
        outer.addWidget(self._header)

        # ── Main body (horizontal splitter) ───────────────────────────
        h_splitter = QSplitter(Qt.Orientation.Horizontal)
        h_splitter.setHandleWidth(1)
        h_splitter.setStyleSheet("QSplitter::handle { background: #21262d; }")

        # ── Left pane: video + controls + playlist (vertical splitter) ─
        left_outer = QWidget()
        left_outer.setStyleSheet("background: #0d1117;")
        left_outer_layout = QVBoxLayout(left_outer)
        left_outer_layout.setContentsMargins(0, 0, 0, 0)
        left_outer_layout.setSpacing(0)

        v_splitter = QSplitter(Qt.Orientation.Vertical)
        v_splitter.setHandleWidth(1)
        v_splitter.setStyleSheet("QSplitter::handle { background: #21262d; }")

        # Top portion: video + controls
        top_widget = QWidget()
        top_widget.setStyleSheet("background: #0d1117;")
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)

        self._video = VideoWidget()
        top_layout.addWidget(self._video, stretch=1)

        self._controls = ControlsBar()
        self._controls.setStyleSheet(
            "background: #161b22; border-top: 1px solid #21262d;"
        )
        top_layout.addWidget(self._controls)

        # Bottom portion: playlist
        self._playlist = PlaylistPanel()

        v_splitter.addWidget(top_widget)
        v_splitter.addWidget(self._playlist)
        v_splitter.setSizes([520, 220])
        v_splitter.setStretchFactor(0, 1)
        v_splitter.setStretchFactor(1, 0)

        left_outer_layout.addWidget(v_splitter, stretch=1)

        # ── Right pane: outputs panel ──────────────────────────────────
        self._preview_panel = PreviewPanel(self._output_manager, self)

        h_splitter.addWidget(left_outer)
        h_splitter.addWidget(self._preview_panel)
        h_splitter.setSizes([1100, 320])
        h_splitter.setStretchFactor(0, 1)
        h_splitter.setStretchFactor(1, 0)

        outer.addWidget(h_splitter, stretch=1)

        # ── Status bar ────────────────────────────────────────────────
        status = QStatusBar()
        status.setStyleSheet(
            "background: #0d1117; color: #8b949e; font-size: 12px;"
        )
        self.setStatusBar(status)
        self._status = status
        self._status.showMessage("Ready — open a video file to begin")

    def _connect_signals(self) -> None:
        c = self._controls
        c.open_file_requested.connect(self._open_file)
        c.play_pause_requested.connect(self._player.toggle_play_pause)
        c.stop_requested.connect(self._on_stop)
        c.seek_requested.connect(self._player.seek)
        c.volume_changed.connect(lambda v: setattr(self._player, "volume", v))

        p = self._player
        p.position_changed.connect(c.set_position)
        p.time_changed.connect(c.set_time)
        p.duration_changed.connect(c.set_duration)
        p.state_changed.connect(self._on_state_changed)
        p.media_loaded.connect(self._on_media_loaded)

        self._preview_panel.output_requested.connect(self._add_output)

        # Playlist
        self._playlist.play_requested.connect(self._load_and_play)
        self._playlist.add_files_requested.connect(self._add_files_to_playlist)

    # ──────────────────────────────────────────────── Qt lifecycle hooks

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._player_attached:
            self._player.attach_to_widget(self._video)
            self._player_attached = True
            self._refresh_header()

    def closeEvent(self, event) -> None:
        self._thumb_worker.stop()
        self._thumb_worker.wait(3000)
        self._player.cleanup()
        self._output_manager.cleanup()
        event.accept()

    # ─────────────────────────────────────────────────── source player slots

    def _open_file_dialog(self, multi: bool = False) -> List[str]:
        """Open a non-native file dialog with sidebar shortcuts.

        Returns a list of selected paths (empty if cancelled).
        Uses DontUseNativeDialog so Qt's own picker is used, which avoids
        triggering OneDrive placeholder hydration.
        """
        dlg = QFileDialog(self, "Open Video File")
        dlg.setNameFilter(_VIDEO_FILTER)
        dlg.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dlg.setSidebarUrls(_sidebar_urls())
        if multi:
            dlg.setFileMode(QFileDialog.FileMode.ExistingFiles)
        else:
            dlg.setFileMode(QFileDialog.FileMode.ExistingFile)

        if dlg.exec():
            return dlg.selectedFiles()
        return []

    def _open_file(self) -> None:
        """Open button handler — load a single file into the source player."""
        paths = self._open_file_dialog(multi=False)
        if paths:
            path = paths[0]
            self._load_and_play(path)
            # Also add to playlist if not already there
            self._add_to_playlist(path)

    def _add_files_to_playlist(self) -> None:
        """Add files button — opens multi-select dialog, adds all to playlist."""
        paths = self._open_file_dialog(multi=True)
        for path in paths:
            self._add_to_playlist(path)

    def _add_to_playlist(self, path: str) -> None:
        """Add *path* to the playlist and queue thumbnail extraction."""
        self._playlist.add_item(path)
        self._thumb_worker.enqueue(path)

    def _load_and_play(self, path: str) -> None:
        """Load *path* into the source player and start playback."""
        self._player.load(path)
        self._player.play()
        self._playlist.select_path(path)

    def _on_stop(self) -> None:
        self._player.stop()
        self._controls.set_position(0.0)
        self._controls.set_time(0)

    def _on_state_changed(self, state: str) -> None:
        self._controls.set_playing(state == "playing")
        messages = {
            "playing": "Playing (source)",
            "paused":  "Paused (source)",
            "stopped": "Stopped",
            "ended":   "Playback complete",
            "error":   "Error during playback",
        }
        self._status.showMessage(messages.get(state, "Ready"))

    def _on_media_loaded(self, path: str) -> None:
        self._current_media_path = path
        name = os.path.basename(path)
        self.setWindowTitle(f"VLCShow — {name}")
        self._status.showMessage(f"Loaded: {name}")
        self._video.set_media_active(True)

    def _on_thumbnail_ready(
        self,
        path: str,
        thumb_path: str,
        width: int,
        height: int,
        duration_ms: int,
    ) -> None:
        """Slot called (on main thread) when the worker finishes a thumbnail."""
        self._playlist.update_item_metadata(path, thumb_path, width, height, duration_ms)

    # ──────────────────────────────────────────────── output management

    def _add_output(self, screen_info: ScreenInfo) -> None:
        """Create a new OutputChannel + ProjectionWindow for *screen_info*."""
        channel = self._output_manager.add(screen_info, parent=self)

        # Create and show the projection window on the target display
        win = ProjectionWindow(screen_info, channel.player, parent=None)
        channel.window = win
        win.show_on_screen()

        # Build the card
        card = OutputCard(channel, self._output_manager, self)
        card.send_media_requested.connect(
            lambda ch=channel: self._send_media_to_output(ch)
        )
        card.remove_requested.connect(
            lambda ch=channel, c=card: self._remove_output(ch, c)
        )
        self._preview_panel.add_card(card)

        n = len(self._output_manager.channels)
        self._status.showMessage(
            f"Output '{channel.label}' added — {n} output(s) active"
        )

    def _send_media_to_output(self, channel) -> None:
        """Load the current source file into *channel* and start playing."""
        if not self._current_media_path:
            self._status.showMessage("No media loaded — open a file first")
            return
        self._output_manager.send_media(self._current_media_path, channel)
        channel.player.play()
        self._status.showMessage(
            f"Sent to '{channel.label}': {os.path.basename(self._current_media_path)}"
        )

    def _remove_output(self, channel, card: OutputCard) -> None:
        label = channel.label
        self._preview_panel.remove_card(card)
        self._output_manager.remove(channel)
        self._status.showMessage(f"Output '{label}' removed")

    # ──────────────────────────────────────────────────────── helpers

    def _refresh_header(self) -> None:
        screens = DisplayManager.get_screens()
        if not screens:
            return
        parts = []
        for s in screens:
            tag = " ★" if s.is_primary else ""
            parts.append(f"Screen {s.index}{tag}  {s.width}×{s.height}")
        self._header.setText("🎬  VLCShow        " + "   |   ".join(parts))
        n = len(screens)
        self._status.showMessage(f"{n} display(s) detected — ready")

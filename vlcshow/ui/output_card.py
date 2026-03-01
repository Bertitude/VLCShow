"""OutputCard — card widget for one projection output channel.

Layout
──────
┌─────────────────────────────────────────────────────────────┐
│  ● Main Stage                          Screen 1  1920×1080  │  ← header
│                                                   [✏ Rename]│
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                  [thumbnail / placeholder]                  │  ← 150 px
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  [▶ Play]  [⏸ Pause]  [⏹ Stop]              [⛶ Fullscreen] │  ← controls
│  [📂  Send current media to this output]                    │
└─────────────────────────────────────────────────────────────┘

The ● indicator colour reflects playback state:
  green  = playing   orange = paused   grey = stopped / idle

Signals
───────
send_media_requested     – user wants to load the current source file here
remove_requested         – user wants to close this output channel
"""

from __future__ import annotations

import os
import tempfile
from typing import TYPE_CHECKING, Optional

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QInputDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QColor

if TYPE_CHECKING:
    from vlcshow.core.output_manager import OutputChannel, OutputManager


# Thumbnail temp directory shared by all cards
_THUMB_DIR = os.path.join(tempfile.gettempdir(), "vlcshow_thumbs")
os.makedirs(_THUMB_DIR, exist_ok=True)

# State → indicator colour
_STATE_COLOUR: dict[str, str] = {
    "playing": "#3fb950",   # green
    "paused":  "#d29922",   # amber
    "stopped": "#484f58",   # grey
    "ended":   "#484f58",
    "idle":    "#484f58",
    "error":   "#f85149",   # red
}


class OutputCard(QFrame):
    """Card widget representing one active projection output."""

    send_media_requested = pyqtSignal()
    remove_requested     = pyqtSignal()

    def __init__(
        self,
        channel: "OutputChannel",
        manager: "OutputManager",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._channel = channel
        self._manager = manager

        # Unique temp file for this channel's thumbnails
        self._thumb_path = os.path.join(_THUMB_DIR, f"thumb_{id(channel)}.png")
        self._last_thumb_mtime: float = 0.0

        self.setObjectName("OutputCard")
        self.setStyleSheet("""
            OutputCard {
                background: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
        """)
        self.setMinimumWidth(260)

        self._setup_ui()
        self._connect_player_signals()

    # ─────────────────────────────────────────────────────────────── setup

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 12)
        root.setSpacing(8)

        # ── Header row ────────────────────────────────────────────────
        header = QHBoxLayout()
        header.setSpacing(6)

        self._state_dot = QLabel("●")
        self._state_dot.setFixedWidth(14)
        self._state_dot.setStyleSheet("color: #484f58; font-size: 14px; background: transparent;")

        self._name_label = QLabel(self._channel.label)
        self._name_label.setStyleSheet(
            "font-size: 14px; font-weight: 700; color: #e6edf3; background: transparent;"
        )
        self._name_label.setWordWrap(False)

        self._screen_label = QLabel(
            f"{self._channel.screen_info.width}×{self._channel.screen_info.height}"
        )
        self._screen_label.setStyleSheet(
            "font-size: 11px; color: #8b949e; background: transparent;"
        )
        self._screen_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        rename_btn = QPushButton("✏")
        rename_btn.setFixedSize(QSize(36, 36))
        rename_btn.setToolTip("Rename output")
        rename_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none;
                color: #8b949e; font-size: 16px;
                min-height: 36px; min-width: 36px;
            }
            QPushButton:hover { color: #e6edf3; }
        """)
        rename_btn.clicked.connect(self._rename)

        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(QSize(36, 36))
        remove_btn.setToolTip("Remove output")
        remove_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none;
                color: #8b949e; font-size: 14px;
                min-height: 36px; min-width: 36px;
            }
            QPushButton:hover { color: #f85149; }
        """)
        remove_btn.clicked.connect(self.remove_requested)

        header.addWidget(self._state_dot)
        header.addWidget(self._name_label, stretch=1)
        header.addWidget(self._screen_label)
        header.addWidget(rename_btn)
        header.addWidget(remove_btn)
        root.addLayout(header)

        # Screen index sub-label
        screen_sub = QLabel(f"Screen {self._channel.screen_info.index}")
        screen_sub.setStyleSheet(
            "font-size: 11px; color: #484f58; background: transparent; margin-left: 20px;"
        )
        root.addWidget(screen_sub)

        # ── Thumbnail ─────────────────────────────────────────────────
        self._thumb = QLabel()
        self._thumb.setFixedHeight(150)
        self._thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumb.setStyleSheet(
            "background: #0d1117; border-radius: 4px; color: #30363d; font-size: 12px;"
        )
        self._thumb.setText("No preview")
        root.addWidget(self._thumb)

        # ── Playback controls ─────────────────────────────────────────
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(6)

        self._btn_play   = _card_btn("▶")
        self._btn_pause  = _card_btn("⏸")
        self._btn_stop   = _card_btn("⏹")
        self._btn_full   = _card_btn("⛶", accent=True)
        self._btn_full.setToolTip("Toggle fullscreen on this display")

        ctrl_row.addWidget(self._btn_play)
        ctrl_row.addWidget(self._btn_pause)
        ctrl_row.addWidget(self._btn_stop)
        ctrl_row.addStretch(1)
        ctrl_row.addWidget(self._btn_full)
        root.addLayout(ctrl_row)

        # ── Send button ───────────────────────────────────────────────
        self._btn_send = QPushButton("📂  Send current media here")
        self._btn_send.setMinimumHeight(48)
        self._btn_send.setStyleSheet("""
            QPushButton {
                background: #21262d; color: #e6edf3;
                border: 1px solid #30363d; border-radius: 6px;
                font-size: 13px; font-weight: 600;
                min-height: 48px; padding: 8px 12px;
            }
            QPushButton:hover { background: #30363d; border-color: #8b949e; }
            QPushButton:pressed { background: #161b22; }
            QPushButton:disabled { color: #484f58; }
        """)
        root.addWidget(self._btn_send)

        # Wire controls
        self._btn_play.clicked.connect(self._channel.player.play)
        self._btn_pause.clicked.connect(self._channel.player.pause)
        self._btn_stop.clicked.connect(self._channel.player.stop)
        self._btn_full.clicked.connect(self._toggle_fullscreen)
        self._btn_send.clicked.connect(self.send_media_requested)

        # Disabled until media is sent to this output
        self._set_transport_enabled(False)

    def _connect_player_signals(self) -> None:
        p = self._channel.player
        p.state_changed.connect(self._on_state_changed)
        p.media_loaded.connect(lambda _: self._set_transport_enabled(True))

    # ──────────────────────────────────────────────────────── public slots

    def refresh_thumbnail(self) -> None:
        """Load the last snapshot image and request a fresh one.

        Call this on every timer tick (≥1 s interval).  VLC's snapshot
        write is async so we always display the *previous* snapshot while
        queuing the next one — result is ~1 tick of latency, which is fine.
        """
        # Display whatever was saved last tick
        if os.path.isfile(self._thumb_path):
            mtime = os.path.getmtime(self._thumb_path)
            if mtime != self._last_thumb_mtime:
                px = QPixmap(self._thumb_path)
                if not px.isNull():
                    self._thumb.setPixmap(
                        px.scaled(
                            self._thumb.width(),
                            self._thumb.height(),
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    )
                    self._last_thumb_mtime = mtime
                    self._thumb.setText("")

        # Queue a fresh snapshot for next tick (no-op if not playing)
        if self._channel.window:
            self._channel.window.take_snapshot(self._thumb_path)

    def update_label(self, label: str) -> None:
        """Sync the displayed name after an external rename."""
        self._name_label.setText(label)

    # ─────────────────────────────────────────────────────────── internals

    def _on_state_changed(self, state: str) -> None:
        colour = _STATE_COLOUR.get(state, "#484f58")
        self._state_dot.setStyleSheet(
            f"color: {colour}; font-size: 14px; background: transparent;"
        )

    def _set_transport_enabled(self, enabled: bool) -> None:
        self._btn_play.setEnabled(enabled)
        self._btn_pause.setEnabled(enabled)
        self._btn_stop.setEnabled(enabled)

    def _rename(self) -> None:
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Output",
            "Output name:",
            text=self._channel.label,
        )
        if ok and new_name.strip():
            self._manager.rename(self._channel, new_name.strip())
            self._name_label.setText(self._channel.label)

    def _toggle_fullscreen(self) -> None:
        if self._channel.window:
            self._channel.window.toggle_fullscreen()
            fs = self._channel.window.is_fullscreen
            self._btn_full.setText("⊡" if fs else "⛶")
            self._btn_full.setToolTip(
                "Exit fullscreen" if fs else "Toggle fullscreen on this display"
            )


# ────────────────────────────────────────────────────────────────── helpers

def _card_btn(text: str, accent: bool = False) -> QPushButton:
    btn = QPushButton(text)
    bg = "#1f6feb" if accent else "#21262d"
    border = "#388bfd" if accent else "#30363d"
    btn.setFixedSize(QSize(48, 48))
    btn.setStyleSheet(f"""
        QPushButton {{
            background: {bg}; color: #e6edf3;
            border: 1px solid {border}; border-radius: 6px;
            font-size: 18px;
            min-height: 48px; min-width: 48px;
        }}
        QPushButton:hover {{ background: {'#388bfd' if accent else '#30363d'}; }}
        QPushButton:pressed {{ background: #161b22; }}
        QPushButton:disabled {{ background: #161b22; color: #484f58; border-color: #21262d; }}
    """)
    return btn

"""PreviewPanel — scrollable column of OutputCard widgets.

Sits in the right pane of MainWindow.  It owns:
  • The list of OutputCards (one per active output channel)
  • A 1.5 s thumbnail-refresh timer
  • An "Add Output" button that lets the user pick an available display

Signals
───────
output_requested(ScreenInfo)   – user picked a screen to add as an output

The actual OutputChannel + ProjectionWindow creation is handled by
MainWindow so this panel stays decoupled from the player/window layer.
"""

from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING

from PyQt6.QtWidgets import (
    QScrollArea, QWidget, QVBoxLayout,
    QPushButton, QLabel, QInputDialog, QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from vlcshow.core.display_manager import DisplayManager, ScreenInfo
from vlcshow.ui.output_card import OutputCard

if TYPE_CHECKING:
    from vlcshow.core.output_manager import OutputManager


class PreviewPanel(QScrollArea):
    """Scrollable panel listing every active output as an OutputCard."""

    output_requested = pyqtSignal(object)   # emits ScreenInfo

    def __init__(self, output_manager: "OutputManager", parent=None) -> None:
        super().__init__(parent)
        self._manager = output_manager
        self._cards: List[OutputCard] = []

        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setMinimumWidth(290)
        self.setMaximumWidth(400)
        self.setStyleSheet(
            "QScrollArea { background: #0d1117; border: none; border-left: 1px solid #21262d; }"
        )

        # Inner container
        container = QWidget()
        container.setStyleSheet("background: #0d1117;")
        self._layout = QVBoxLayout(container)
        self._layout.setContentsMargins(10, 10, 10, 10)
        self._layout.setSpacing(10)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ── Panel header ──────────────────────────────────────────────
        header = QLabel("Outputs")
        header.setStyleSheet(
            "color: #8b949e; font-size: 11px; font-weight: 700;"
            "letter-spacing: 1px; text-transform: uppercase;"
            "background: transparent; padding-bottom: 4px;"
        )
        self._layout.addWidget(header)

        # ── Add Output button ─────────────────────────────────────────
        self._btn_add = QPushButton("＋  Add Output")
        self._btn_add.setMinimumHeight(52)
        self._btn_add.setStyleSheet("""
            QPushButton {
                background: #21262d; color: #58a6ff;
                border: 1px dashed #30363d; border-radius: 6px;
                font-size: 14px; font-weight: 600;
                min-height: 52px;
            }
            QPushButton:hover { background: #30363d; border-color: #58a6ff; }
            QPushButton:pressed { background: #161b22; }
        """)
        self._btn_add.clicked.connect(self._on_add_clicked)
        self._layout.addWidget(self._btn_add)

        # Spacer at the bottom so cards stack from the top
        self._layout.addStretch(1)

        self.setWidget(container)

        # ── Thumbnail refresh timer (1.5 s) ───────────────────────────
        self._thumb_timer = QTimer(self)
        self._thumb_timer.setInterval(1500)
        self._thumb_timer.timeout.connect(self._refresh_thumbnails)
        self._thumb_timer.start()

    # ───────────────────────────────────────────────────── card management

    def add_card(self, card: OutputCard) -> None:
        """Insert a new card just above the bottom stretch."""
        # Insert before the stretch item (always the last item)
        insert_idx = max(0, self._layout.count() - 1)
        self._layout.insertWidget(insert_idx, card)
        self._cards.append(card)

    def remove_card(self, card: OutputCard) -> None:
        """Remove and destroy a card."""
        if card in self._cards:
            self._cards.remove(card)
            self._layout.removeWidget(card)
            card.deleteLater()

    # ─────────────────────────────────────────────────────── add-output UI

    def _on_add_clicked(self) -> None:
        """Pick an available display and emit output_requested."""
        all_screens = DisplayManager.get_screens()
        used_indices = {ch.screen_info.index for ch in self._manager.channels}
        available = [s for s in all_screens if s.index not in used_indices]

        if not available:
            QMessageBox.information(
                self,
                "No displays available",
                "All connected displays already have an output assigned.\n\n"
                "Connect an additional monitor and try again.",
            )
            return

        if len(available) == 1:
            self.output_requested.emit(available[0])
            return

        # Multiple screens — let the user choose
        items = [s.short_label for s in available]
        choice, ok = QInputDialog.getItem(
            self,
            "Add Output",
            "Select a display to use as an output:",
            items,
            currentItem=0,
            editable=False,
        )
        if ok:
            idx = items.index(choice)
            self.output_requested.emit(available[idx])

    # ──────────────────────────────────────────────── thumbnail refresh

    def _refresh_thumbnails(self) -> None:
        for card in self._cards:
            card.refresh_thumbnail()

"""PlaylistPanel — drag-reorderable video queue with thumbnail previews.

Each row displays:
  ┌──────────────────────────────────────────────────────────────┐
  │ ⋮⋮ [192×108 thumb]  Title.mp4                               │
  │                      1920×1080  •  1:23:45              drag │
  └──────────────────────────────────────────────────────────────┘

Rows can be reordered by dragging.  Double-clicking (or pressing Enter)
fires play_requested.

Signals
───────
play_requested(str)      – user wants to load + play this path in the source player
add_files_requested      – user clicked "＋ Add files" (main window opens the dialog)
"""

from __future__ import annotations

import os
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem,
    QAbstractItemView, QStyledItemDelegate, QStyleOptionViewItem,
    QApplication,
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QSize, QRect, QPoint,
)
from PyQt6.QtGui import (
    QPainter, QPixmap, QColor, QFont, QPen, QBrush,
)

from vlcshow.utils.time_format import format_ms
from vlcshow.workers.thumbnail_worker import _thumb_path_for


# ─────────────────────────────────────────────────────────── data roles
_ROLE_PATH     = Qt.ItemDataRole.UserRole + 1
_ROLE_WIDTH    = Qt.ItemDataRole.UserRole + 2
_ROLE_HEIGHT   = Qt.ItemDataRole.UserRole + 3
_ROLE_DURATION = Qt.ItemDataRole.UserRole + 4
_ROLE_THUMB    = Qt.ItemDataRole.UserRole + 5   # QPixmap (scaled)

# Row geometry
_THUMB_W  = 128
_THUMB_H  = 72
_ROW_H    = _THUMB_H + 16          # 8 px padding top + bottom
_GRIP_W   = 20
_PAD      = 8


# ─────────────────────────────────────────────────────── custom delegate

class _PlaylistDelegate(QStyledItemDelegate):
    """Paints thumbnail + title + metadata for each playlist row."""

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        return QSize(option.rect.width(), _ROW_H)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index,
    ) -> None:
        painter.save()

        # ── Background ────────────────────────────────────────────────
        is_selected = bool(option.state & option.state.Selected)  # type: ignore[attr-defined]
        if is_selected:
            painter.fillRect(option.rect, QColor("#1c2128"))
        else:
            painter.fillRect(option.rect, QColor("#0d1117"))

        # Subtle bottom separator
        sep_pen = QPen(QColor("#21262d"))
        sep_pen.setWidth(1)
        painter.setPen(sep_pen)
        painter.drawLine(
            option.rect.left(), option.rect.bottom(),
            option.rect.right(), option.rect.bottom(),
        )

        x = option.rect.left()
        y = option.rect.top()

        # ── Drag grip dots ────────────────────────────────────────────
        painter.setPen(QColor("#484f58"))
        dot_x = x + 6
        for row in range(3):
            for col in range(2):
                painter.drawEllipse(
                    QPoint(dot_x + col * 4, y + _ROW_H // 2 - 4 + row * 4),
                    1, 1,
                )

        # ── Thumbnail ─────────────────────────────────────────────────
        thumb_x = x + _GRIP_W
        thumb_y = y + (_ROW_H - _THUMB_H) // 2
        thumb_rect = QRect(thumb_x, thumb_y, _THUMB_W, _THUMB_H)

        pixmap: Optional[QPixmap] = index.data(_ROLE_THUMB)  # type: ignore[assignment]
        if pixmap and not pixmap.isNull():
            painter.drawPixmap(thumb_rect, pixmap)
        else:
            # Placeholder
            painter.fillRect(thumb_rect, QColor("#161b22"))
            painter.setPen(QColor("#30363d"))
            painter.drawRect(thumb_rect)
            painter.setPen(QColor("#484f58"))
            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(thumb_rect, Qt.AlignmentFlag.AlignCenter, "…")

        # ── Text block ────────────────────────────────────────────────
        text_x = thumb_x + _THUMB_W + _PAD
        text_w = option.rect.right() - text_x - _PAD
        if text_w < 20:
            painter.restore()
            return

        # Title
        title = index.data(Qt.ItemDataRole.DisplayRole) or ""
        title_font = QFont("Segoe UI", 11)
        title_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(title_font)
        painter.setPen(QColor("#e6edf3" if not is_selected else "#ffffff"))
        title_rect = QRect(text_x, y + 10, text_w, 20)
        fm = painter.fontMetrics()
        elided = fm.elidedText(title, Qt.TextElideMode.ElideRight, text_w)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided)

        # Metadata line
        w = index.data(_ROLE_WIDTH) or 0
        h = index.data(_ROLE_HEIGHT) or 0
        dur = index.data(_ROLE_DURATION) or 0
        parts: list[str] = []
        if w and h:
            parts.append(f"{w}×{h}")
        if dur:
            parts.append(format_ms(int(dur)))
        meta = "  •  ".join(parts) if parts else "Loading…"

        meta_font = QFont("Segoe UI", 9)
        painter.setFont(meta_font)
        painter.setPen(QColor("#8b949e"))
        meta_rect = QRect(text_x, y + _ROW_H - 32, text_w, 20)
        painter.drawText(meta_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, meta)

        painter.restore()


# ──────────────────────────────────────────────────────── PlaylistPanel

class PlaylistPanel(QWidget):
    """Drag-reorderable playlist with thumbnail previews."""

    play_requested   = pyqtSignal(str)   # video path
    add_files_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(120)
        self._setup_ui()

    # ─────────────────────────────────────────────────── UI construction

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header bar ────────────────────────────────────────────────
        bar = QWidget()
        bar.setStyleSheet("background: #161b22; border-top: 1px solid #21262d;")
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(10, 6, 10, 6)
        bar_layout.setSpacing(8)

        lbl = QLabel("Playlist")
        lbl.setStyleSheet(
            "color: #8b949e; font-size: 11px; font-weight: 700;"
            "letter-spacing: 1px; text-transform: uppercase;"
            "background: transparent;"
        )
        bar_layout.addWidget(lbl)
        bar_layout.addStretch(1)

        btn_add = QPushButton("＋  Add files")
        btn_add.setFixedHeight(32)
        btn_add.setStyleSheet("""
            QPushButton {
                background: #21262d; color: #58a6ff;
                border: 1px solid #30363d; border-radius: 5px;
                font-size: 12px; font-weight: 600;
                min-height: 32px; padding: 2px 10px;
            }
            QPushButton:hover { background: #30363d; border-color: #58a6ff; }
            QPushButton:pressed { background: #161b22; }
        """)
        btn_add.clicked.connect(self.add_files_requested)
        bar_layout.addWidget(btn_add)

        self._btn_clear = QPushButton("Clear")
        self._btn_clear.setFixedHeight(32)
        self._btn_clear.setStyleSheet("""
            QPushButton {
                background: transparent; color: #8b949e;
                border: 1px solid #30363d; border-radius: 5px;
                font-size: 12px; font-weight: 600;
                min-height: 32px; padding: 2px 10px;
            }
            QPushButton:hover { color: #f85149; border-color: #f85149; }
            QPushButton:pressed { background: #161b22; }
        """)
        self._btn_clear.clicked.connect(self._clear)
        bar_layout.addWidget(self._btn_clear)

        root.addWidget(bar)

        # ── List widget ───────────────────────────────────────────────
        self._list = QListWidget()
        self._list.setStyleSheet("""
            QListWidget {
                background: #0d1117;
                border: none;
                outline: none;
            }
            QListWidget::item { border: none; }
            QListWidget::item:selected {
                background: #1c2128;
            }
        """)
        self._list.setItemDelegate(_PlaylistDelegate(self._list))
        self._list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.setSpacing(0)
        self._list.setUniformItemSizes(True)

        self._list.itemDoubleClicked.connect(self._on_double_click)
        self._list.activated.connect(self._on_activated)    # Enter key

        root.addWidget(self._list, stretch=1)

    # ──────────────────────────────────────────────────── public API

    def add_item(self, path: str) -> QListWidgetItem:
        """Add *path* to the playlist and return the new item.

        If the path is already in the playlist the existing item is returned
        instead (no duplicates).
        """
        existing = self._find_item(path)
        if existing:
            return existing

        title = os.path.basename(path)
        item = QListWidgetItem(title)
        item.setData(_ROLE_PATH, path)
        item.setData(_ROLE_WIDTH, 0)
        item.setData(_ROLE_HEIGHT, 0)
        item.setData(_ROLE_DURATION, 0)
        item.setSizeHint(QSize(self._list.width(), _ROW_H))

        # Load thumb from disk if already extracted in a previous session
        thumb_path = _thumb_path_for(path)
        if os.path.isfile(thumb_path):
            px = QPixmap(thumb_path)
            if not px.isNull():
                item.setData(_ROLE_THUMB, px.scaled(
                    _THUMB_W, _THUMB_H,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                ))

        self._list.addItem(item)
        return item

    def update_item_metadata(
        self,
        path: str,
        thumb_path: str,
        width: int,
        height: int,
        duration_ms: int,
    ) -> None:
        """Called when the worker thread finishes extracting a thumbnail."""
        item = self._find_item(path)
        if not item:
            return

        item.setData(_ROLE_WIDTH, width)
        item.setData(_ROLE_HEIGHT, height)
        item.setData(_ROLE_DURATION, duration_ms)

        px = QPixmap(thumb_path)
        if not px.isNull():
            item.setData(_ROLE_THUMB, px.scaled(
                _THUMB_W, _THUMB_H,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
        self._list.update()

    def path_is_queued(self, path: str) -> bool:
        return self._find_item(path) is not None

    def select_path(self, path: str) -> None:
        """Highlight the row for *path* if present."""
        item = self._find_item(path)
        if item:
            self._list.setCurrentItem(item)

    def current_path(self) -> Optional[str]:
        item = self._list.currentItem()
        return item.data(_ROLE_PATH) if item else None

    # ──────────────────────────────────────────────────── internals

    def _find_item(self, path: str) -> Optional[QListWidgetItem]:
        norm = os.path.normcase(os.path.abspath(path))
        for i in range(self._list.count()):
            it = self._list.item(i)
            p = it.data(_ROLE_PATH) if it else None
            if p and os.path.normcase(os.path.abspath(p)) == norm:
                return it
        return None

    def _on_double_click(self, item: QListWidgetItem) -> None:
        path = item.data(_ROLE_PATH)
        if path:
            self.play_requested.emit(path)

    def _on_activated(self, index) -> None:
        item = self._list.item(index.row())
        if item:
            path = item.data(_ROLE_PATH)
            if path:
                self.play_requested.emit(path)

    def _clear(self) -> None:
        self._list.clear()

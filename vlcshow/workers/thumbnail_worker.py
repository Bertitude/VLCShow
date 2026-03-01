"""ThumbnailWorkerThread — background VLC-based thumbnail extractor.

Uses a headless VLC instance (--vout=dummy, --no-audio) to seek to 10 %
of each file and capture a 192×108 snapshot.  Work items are queued and
processed one at a time so the thread never opens more than one VLC
instance concurrently.

Signals
───────
result_ready(path, thumb_path, width, height, duration_ms)
    Emitted on the worker thread; connect with Qt.ConnectionType.QueuedConnection
    (the default for cross-thread) so slot runs on the main thread.
"""

from __future__ import annotations

import os
import sys
import time
import tempfile
from queue import Queue, Empty
from typing import Optional, Tuple

from PyQt6.QtCore import QThread, pyqtSignal


# Shared thumbnail directory (same one OutputCard uses for live snapshots)
_THUMB_DIR = os.path.join(tempfile.gettempdir(), "vlcshow_thumbs")
os.makedirs(_THUMB_DIR, exist_ok=True)

_THUMB_W = 192
_THUMB_H = 108


def _thumb_path_for(video_path: str) -> str:
    """Deterministic temp filename derived from the video path."""
    # Use the absolute path hash to avoid collisions across directories
    key = str(abs(hash(os.path.abspath(video_path))))
    return os.path.join(_THUMB_DIR, f"pl_{key}.png")


class ThumbnailWorkerThread(QThread):
    """QThread that extracts thumbnails and metadata using a headless VLC.

    Usage::

        worker = ThumbnailWorkerThread()
        worker.result_ready.connect(my_slot)
        worker.start()
        worker.enqueue("/path/to/video.mp4")
        ...
        worker.stop()
        worker.wait()
    """

    # (video_path, thumb_path, width, height, duration_ms)
    result_ready: pyqtSignal = pyqtSignal(str, str, int, int, int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._queue: Queue[Optional[str]] = Queue()
        self._seen: set[str] = set()     # paths already extracted this session

    # ──────────────────────────────────────────────────────── public API

    def enqueue(self, video_path: str) -> None:
        """Add *video_path* to the extraction queue (no-op if already queued)."""
        norm = os.path.normcase(os.path.abspath(video_path))
        if norm in self._seen:
            return
        self._seen.add(norm)
        self._queue.put(video_path)

    def stop(self) -> None:
        """Signal the run-loop to exit after the current item finishes."""
        self._queue.put(None)   # sentinel

    # ──────────────────────────────────────────────────────── QThread.run

    def run(self) -> None:
        # Import vlc on the worker thread — the DLL path was already
        # registered by player.py's module-level _register_vlc_dll_path().
        try:
            import vlc  # type: ignore[import]
        except Exception:
            return

        # Headless VLC instance: no window, no audio
        args = [
            "--quiet",
            "--no-audio",
            "--vout=dummy",
            "--no-osd",
            "--no-spu",
            "--no-sub-autodetect-file",
        ]
        instance: Optional[object] = None
        try:
            instance = vlc.Instance(args)
        except Exception:
            return

        while True:
            try:
                path = self._queue.get(timeout=1.0)
            except Empty:
                continue

            if path is None:          # stop sentinel
                break

            try:
                self._extract(vlc, instance, path)
            except Exception:
                pass                  # never crash the worker thread

        try:
            instance.release()
        except Exception:
            pass

    # ──────────────────────────────────────────────────────── internals

    def _extract(self, vlc, instance, video_path: str) -> None:
        """Open *video_path*, read metadata + grab a thumbnail frame."""
        thumb = _thumb_path_for(video_path)

        player = instance.media_player_new()
        media  = instance.media_new(video_path)
        media.parse_with_options(vlc.MediaParseFlag.local, -1)

        player.set_media(media)
        player.audio_set_volume(0)

        # Play briefly to prime the pipeline, then snapshot
        player.play()
        _wait_for_state(player, vlc.State.Playing, timeout=4.0)

        # Seek to 10 % for a representative frame (skip black intro)
        duration_ms = media.get_duration()   # may be -1 initially
        # Give media a moment to report duration
        for _ in range(20):
            duration_ms = player.get_length()
            if duration_ms and duration_ms > 0:
                break
            time.sleep(0.1)

        if duration_ms and duration_ms > 0:
            seek_ms = max(0, min(int(duration_ms * 0.10), duration_ms - 500))
            player.set_time(seek_ms)
            time.sleep(0.3)   # let VLC decode the seek target

        # Take the snapshot
        player.video_take_snapshot(0, thumb, _THUMB_W, _THUMB_H)
        # Give VLC up to 2 s to write the file
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            if os.path.isfile(thumb) and os.path.getsize(thumb) > 0:
                break
            time.sleep(0.05)

        # Collect video dimensions from the media track
        width, height = _get_video_dimensions(media)

        # Final duration check
        if duration_ms is None or duration_ms <= 0:
            duration_ms = media.get_duration()
        if duration_ms is None or duration_ms < 0:
            duration_ms = 0

        player.stop()
        player.release()
        media.release()

        if os.path.isfile(thumb) and os.path.getsize(thumb) > 0:
            self.result_ready.emit(
                video_path, thumb,
                width or 0, height or 0,
                int(duration_ms),
            )


def _wait_for_state(player, target_state, timeout: float = 3.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if player.get_state() == target_state:
            return
        time.sleep(0.05)


def _get_video_dimensions(media) -> Tuple[int, int]:
    """Extract width×height from the first video track descriptor."""
    try:
        tracks = media.tracks_get()
        for t in tracks:
            if t.type == 1:   # VIDEO track
                return t.video.contents.width, t.video.contents.height
    except Exception:
        pass
    return 0, 0

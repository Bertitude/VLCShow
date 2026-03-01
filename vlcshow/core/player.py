"""VLC player wrapper.

Wraps a single vlc.MediaPlayer and surfaces Qt signals so the UI can
bind to playback state without touching VLC internals directly.

Polling strategy: a QTimer fires every 250 ms and emits position / time
/ state signals.  This avoids cross-thread signal issues that arise when
using VLC's own event callbacks.
"""

import os
import sys
from typing import Optional


def _register_vlc_dll_path() -> None:
    """Work around the Python 3.8+ Windows DLL-loading change.

    Since Python 3.8, ctypes no longer searches PATH for DLLs.  We must
    explicitly call os.add_dll_directory() with VLC's installation folder
    so that libvlc.dll (and its dependencies) can be found.
    """
    if sys.platform != "win32":
        return

    # Check env var first so the user can override if VLC is in an odd place
    env_path = os.environ.get("PYTHON_VLC_MODULE_PATH", "")
    candidates = [
        env_path,
        r"C:\Program Files\VideoLAN\VLC",
        r"C:\Program Files (x86)\VideoLAN\VLC",
    ]

    for path in candidates:
        if path and os.path.isfile(os.path.join(path, "libvlc.dll")):
            # Prepend to PATH for any indirect LoadLibrary calls inside VLC
            os.environ["PATH"] = path + os.pathsep + os.environ.get("PATH", "")
            # Required on Python 3.8+ for ctypes.CDLL to resolve the DLL
            os.add_dll_directory(path)
            return

    # VLC not found in standard locations — let python-vlc raise its own error
    # with a clearer message than a raw FileNotFoundError.
    raise FileNotFoundError(
        "libvlc.dll not found.  Install VLC from https://www.videolan.org "
        "or set the PYTHON_VLC_MODULE_PATH environment variable to the folder "
        "containing libvlc.dll."
    )


_register_vlc_dll_path()

import vlc
from PyQt6.QtCore import QObject, QTimer, pyqtSignal


# Map VLC states to simple string tokens used throughout the UI
_STATE_MAP: dict[vlc.State, str] = {
    vlc.State.NothingSpecial: "idle",
    vlc.State.Opening:        "idle",
    vlc.State.Buffering:      "idle",
    vlc.State.Playing:        "playing",
    vlc.State.Paused:         "paused",
    vlc.State.Stopped:        "stopped",
    vlc.State.Ended:          "ended",
    vlc.State.Error:          "error",
}


class VLCPlayer(QObject):
    """Single-channel VLC media player with a Qt signal interface."""

    # ------------------------------------------------------------------ signals
    position_changed = pyqtSignal(float)   # normalised 0.0 – 1.0
    time_changed     = pyqtSignal(int)     # current playback time in ms
    duration_changed = pyqtSignal(int)     # total media duration in ms
    state_changed    = pyqtSignal(str)     # token from _STATE_MAP
    media_loaded     = pyqtSignal(str)     # absolute file path

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        # VLC instance – suppress noisy console output and title overlay
        self._instance: vlc.Instance = vlc.Instance(
            "--no-video-title-show",
            "--no-stats",
            "--quiet",
        )
        self._player: vlc.MediaPlayer = self._instance.media_player_new()
        self._media:  Optional[vlc.Media] = None

        self._last_state:    str = "idle"
        self._last_duration: int = -1
        self._attached:      bool = False

        # Polling timer – all signal emissions happen on the Qt main thread
        self._timer = QTimer(self)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._poll)
        self._timer.start()

    # ------------------------------------------------------------------ attach

    def attach_to_widget(self, widget) -> None:
        """Point VLC video output at *widget*'s native window handle.

        Call this after the widget has been shown at least once so that its
        native handle is valid.
        """
        wid = int(widget.winId())
        if sys.platform == "win32":
            self._player.set_hwnd(wid)
        elif sys.platform == "darwin":
            self._player.set_nsobject(wid)
        else:
            self._player.set_xwindow(wid)
        self._attached = True

    # ------------------------------------------------------------------ load

    def load(self, path: str) -> None:
        """Load *path* into the player (does not auto-play)."""
        self._media = self._instance.media_new(path)
        self._player.set_media(self._media)
        self._last_duration = -1
        self.media_loaded.emit(path)

    # ------------------------------------------------------------ transport

    def play(self) -> None:
        self._player.play()

    def pause(self) -> None:
        self._player.pause()

    def stop(self) -> None:
        self._player.stop()

    def toggle_play_pause(self) -> None:
        if self._player.is_playing():
            self.pause()
        else:
            self.play()

    # ------------------------------------------------------------------- seek

    def seek(self, position: float) -> None:
        """Seek to normalised position in [0.0, 1.0]."""
        self._player.set_position(float(max(0.0, min(1.0, position))))

    def seek_ms(self, ms: int) -> None:
        """Seek to absolute time *ms* (milliseconds)."""
        self._player.set_time(int(ms))

    # ----------------------------------------------------------------- volume

    @property
    def volume(self) -> int:
        return self._player.audio_get_volume()

    @volume.setter
    def volume(self, value: int) -> None:
        self._player.audio_set_volume(max(0, min(100, int(value))))

    # ------------------------------------------------------------ read-only props

    @property
    def is_playing(self) -> bool:
        return bool(self._player.is_playing())

    @property
    def duration_ms(self) -> int:
        """Total media duration in milliseconds, or -1 if not yet known."""
        return self._player.get_length()

    @property
    def time_ms(self) -> int:
        """Current playback time in milliseconds."""
        return self._player.get_time()

    @property
    def position(self) -> float:
        """Current normalised playback position 0.0 – 1.0."""
        return float(self._player.get_position())

    def get_state(self) -> str:
        """Return current state token (e.g. 'playing', 'paused')."""
        return _STATE_MAP.get(self._player.get_state(), "idle")

    # --------------------------------------------------------------- internals

    def _poll(self) -> None:
        """Emit position / state signals.  Called every 250 ms by QTimer."""
        if self._media is None:
            return

        state = self.get_state()
        if state != self._last_state:
            self._last_state = state
            self.state_changed.emit(state)

        if state == "playing":
            self.position_changed.emit(float(self._player.get_position()))
            self.time_changed.emit(self._player.get_time())

        dur = self._player.get_length()
        if dur > 0 and dur != self._last_duration:
            self._last_duration = dur
            self.duration_changed.emit(dur)

    # --------------------------------------------------------------- lifecycle

    def cleanup(self) -> None:
        """Stop the player and release VLC resources."""
        self._timer.stop()
        self._player.stop()
        self._player.release()
        self._instance.release()

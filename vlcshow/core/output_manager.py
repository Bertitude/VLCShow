"""OutputManager — owns the collection of active projection output channels.

Each channel bundles:
  • ScreenInfo         — the target display
  • VLCPlayer          — dedicated player instance for this output
  • label              — user-assigned name (persisted via DisplayConfig)
  • key                — stable screen identifier for config lookup
  • window             — the ProjectionWindow shown on that display
                         (set by MainWindow after construction)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional

from vlcshow.core.config import DisplayConfig, make_screen_key
from vlcshow.core.display_manager import ScreenInfo
from vlcshow.core.player import VLCPlayer

if TYPE_CHECKING:
    from vlcshow.ui.projection_window import ProjectionWindow


@dataclass
class OutputChannel:
    """Everything associated with one active projection output."""

    screen_info: ScreenInfo
    player:      VLCPlayer
    label:       str
    key:         str

    # Assigned by MainWindow once the ProjectionWindow is created
    window: Optional["ProjectionWindow"] = field(default=None, repr=False)


class OutputManager:
    """Create, track, rename, and tear down OutputChannels."""

    def __init__(self) -> None:
        self._config = DisplayConfig()
        self._channels: List[OutputChannel] = []

    # ---------------------------------------------------------------- query

    @property
    def channels(self) -> List[OutputChannel]:
        return list(self._channels)

    def channel_for_screen(self, index: int) -> Optional[OutputChannel]:
        """Return the channel assigned to screen *index*, or None."""
        for ch in self._channels:
            if ch.screen_info.index == index:
                return ch
        return None

    # --------------------------------------------------------------- mutate

    def add(self, screen_info: ScreenInfo, parent=None) -> OutputChannel:
        """Create a new OutputChannel for *screen_info* and register it.

        The VLCPlayer is created here; the caller is responsible for creating
        the ProjectionWindow and assigning it to ``channel.window``.
        """
        key = make_screen_key(
            screen_info.name,
            screen_info.width,
            screen_info.height,
            screen_info.geometry.x(),
            screen_info.geometry.y(),
        )
        # Restore persisted label, or fall back to the screen's short label
        label = self._config.get_label(key) or screen_info.short_label
        self._config.touch(key, default_label=label)
        self._config.flush()

        player = VLCPlayer(parent)
        channel = OutputChannel(
            screen_info=screen_info,
            player=player,
            label=label,
            key=key,
        )
        self._channels.append(channel)
        return channel

    def remove(self, channel: OutputChannel) -> None:
        """Stop and destroy an output channel."""
        if channel in self._channels:
            channel.player.cleanup()
            if channel.window is not None:
                channel.window.close()
            self._channels.remove(channel)

    def rename(self, channel: OutputChannel, new_label: str) -> None:
        """Give *channel* a new display name and persist it."""
        new_label = new_label.strip()
        if new_label:
            channel.label = new_label
            self._config.set_label(channel.key, new_label)

    # ------------------------------------------------------------ media ops

    def send_media(self, path: str, channel: OutputChannel) -> None:
        """Load *path* into *channel*'s player (does not auto-play)."""
        channel.player.load(path)

    def send_media_all(self, path: str) -> None:
        """Load *path* into every active channel's player."""
        for ch in self._channels:
            ch.player.load(path)

    # ------------------------------------------------------------- lifecycle

    def cleanup(self) -> None:
        """Stop all players, close all windows, and clear the channel list."""
        for ch in list(self._channels):
            self.remove(ch)
